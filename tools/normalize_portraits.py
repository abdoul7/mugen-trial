"""Bound MUGEN portrait sprites 9000,0/1 without changing combat sprite payloads.

Operate only on generated build copies. Preserve indexed palettes, sprite order,
all other records, and linked combat sprites. SFF v1 PCX and v2 raw/RLE8/LZ5/PNG
are read; replacements use PCX (v1) or raw indices/PNG32 (v2). Nearest-neighbour
contain keeps pixel edges and aspect ratio. No palette remapping or combat edits.
"""
import io
from pathlib import Path
import struct

from PIL import Image, ImageOps

TARGETS = {(9000, 0): (25, 25), (9000, 1): (120, 140)}


def take(data, offset, length):
    if offset < 0 or length < 0 or offset + length > len(data):
        raise ValueError('SFF offset/length outside file')
    return data[offset:offset+length]


def decode(data, fmt, expected):
    if fmt == 0:
        if len(data) != expected:
            raise ValueError('Raw sprite length mismatch')
        return data
    if len(data) < 4 or struct.unpack_from('<I', data)[0] != expected:
        raise ValueError('Compressed sprite length mismatch')
    src, out, pos = data[4:], bytearray(), 0
    recycled = count = 0
    def byte():
        nonlocal pos
        if pos >= len(src):
            raise ValueError('Truncated compressed sprite')
        value = src[pos]
        pos += 1
        return value
    def repeat(value, length):
        if len(out)+length > expected:
            raise ValueError('Compressed run exceeds sprite dimensions')
        out.extend([value]*length)
    while len(out) < expected:
        if fmt == 2:
            value = byte()
            repeat(byte(), value & 63) if value & 192 == 64 else repeat(value, 1)
        elif fmt == 4:
            control = byte()
            for bit in range(8):
                if len(out) == expected:
                    break
                value = byte()
                if not control & (1 << bit):
                    repeat(value & 31, value >> 5 if value & 224 else byte()+8)
                    continue
                if value & 63:
                    recycled |= (value & 192) >> (count*2)
                    count += 1
                    if count == 4:
                        distance = recycled+1
                        recycled = count = 0
                    else:
                        distance = byte()+1
                    length = (value & 63)+1
                else:
                    distance = ((value & 192) << 2) + byte()+1
                    length = byte()+3
                if distance > len(out) or len(out)+length > expected:
                    raise ValueError('Invalid LZ5 back reference')
                for _ in range(length):
                    out.append(out[-distance])
        else:
            raise ValueError(f'Unsupported indexed sprite encoding: {fmt}')
    return bytes(out)


def fit(im, size):
    scaled = ImageOps.contain(im, size, Image.Resampling.NEAREST)
    out = Image.new(im.mode, size, 0 if im.mode == 'P' else (0,0,0,0))
    if im.mode == 'P':
        out.putpalette(im.getpalette())
    out.paste(scaled, ((size[0]-scaled.width)//2, (size[1]-scaled.height)//2))
    return out


class SpriteFile:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        if self.data[:12] != b'ElecbyteSpr\0':
            raise ValueError('Not an SFF file')
        self.version = self.data[15]
        self.records, self.palettes = [], []
        if self.version == 1:
            count, offset = struct.unpack_from('<II', self.data, 20)
            palette, seen = None, set()
            for _ in range(count):
                if offset in seen:
                    raise ValueError('Cyclic v1 sprite chain')
                seen.add(offset)
                header = bytearray(take(self.data,offset,32))
                nxt, length, ax, ay, group, num, link, shared = struct.unpack_from('<IIhhHHHB',header)
                raw = take(self.data,offset+32,length)
                if length and not shared:
                    if len(raw)<769 or raw[-769]!=12:
                        raise ValueError('Missing PCX palette')
                    palette=raw[-768:]
                self.records.append({'header':header,'raw':raw,'key':(group,num),'axis':(ax,ay),
                                     'link':link if not length else None,'palette':palette,'shared':shared})
                offset=nxt
            if offset:
                raise ValueError('SFF count disagrees with chain')
        elif self.version == 2:
            so,n,po,np,self.lo,self.ll,self.to,self.tl = struct.unpack_from('<8I',self.data,36)
            self.palette_table=take(self.data,po,np*16)
            for i in range(np):
                _,_,colors,link,off,length=struct.unpack_from('<4H2I',self.palette_table,i*16)
                self.palettes.append((colors,link,off,length))
            for i in range(n):
                values=list(struct.unpack('<HHHHhhHBBIIHH',take(self.data,so+i*28,28)))
                g,num,w,h,ax,ay,link,fmt,depth,off,length,pal,flags=values
                raw=take(self.data,(self.to if flags else self.lo)+off,length)
                self.records.append({'values':values,'raw':raw,'key':(g,num),'axis':(ax,ay),
                                     'link':link if not length else None,'size':(w,h)})
        else:
            raise ValueError(f'Unsupported SFF version {self.version}')

    def image(self, index, seen=None):
        seen=set() if seen is None else seen
        if index in seen or not 0<=index<len(self.records):
            raise ValueError('Invalid/cyclic linked sprite')
        seen.add(index)
        r=self.records[index]
        if r['link'] is not None:
            return self.image(r['link'],seen)
        raw=r['raw']
        if self.version==1:
            if r['shared']:
                if r['palette'] is None:
                    raise ValueError('Missing inherited PCX palette')
                if len(raw)>=769 and raw[-769]==12:
                    raw=raw[:-769]
                raw+=bytes([12])+r['palette']
            im=Image.open(io.BytesIO(raw))
            im.load()
            return im
        g,num,w,h,ax,ay,link,fmt,depth,off,length,pal,flags=r['values']
        if fmt in (10,11,12):
            im=Image.open(io.BytesIO(raw[4:]))
            im.load()
            return im.convert('RGBA')
        indices=decode(raw,fmt,w*h)
        im=Image.frombytes('P',(w,h),indices)
        visited=set()
        while True:
            if pal in visited or pal>=len(self.palettes):
                raise ValueError('Invalid palette link')
            visited.add(pal)
            colors,link,off,length=self.palettes[pal]
            if length:
                break
            pal=link
        rgba=take(self.data,self.lo+off,length)
        rgb=bytes(c for i,c in enumerate(rgba) if i%4!=3)[:768]
        im.putpalette(rgb+bytes(768-len(rgb)))
        return im

    def normalize(self):
        changed=[]
        # A portrait reused by a combat sprite cannot be replaced silently.
        linked={r['link'] for r in self.records if r['link'] is not None}
        for i,r in enumerate(self.records):
            if r['key'] not in TARGETS:
                continue
            original=self.image(i)
            target=TARGETS[r['key']]
            if original.size==target and r['axis']==(0,0):
                continue
            if i in linked:
                raise ValueError(f'Portrait {r["key"]} is referenced by another sprite; rebuild required')
            im=fit(original,target)
            if self.version==1:
                stream=io.BytesIO()
                im.save(stream,format='PCX')
                r['raw']=stream.getvalue()
                struct.pack_into('<hh',r['header'],8,0,0)
                r['header'][18]=0
                r['header'][19]=0
                r['header'][20]=0
            else:
                values=r['values']
                values[2:7]=[target[0],target[1],0,0,0]
                if im.mode=='P':
                    values[7:9]=[0,8]
                    r['new_raw']=im.tobytes()
                else:
                    stream=io.BytesIO()
                    im.save(stream,format='PNG')
                    values[7:9]=[12,32]
                    r['new_raw']=struct.pack('<HH',*target)+stream.getvalue()
                values[12]=0
            changed.append({'sprite':r['key'],'before':original.size,'after':target,'axis_before':r['axis']})
        if not changed:
            return changed
        if self.version==1:
            out=bytearray(self.data[:512])
            for i,r in enumerate(self.records):
                header=r['header']
                nxt=len(out)+32+len(r['raw']) if i+1<len(self.records) else 0
                struct.pack_into('<II',header,0,nxt,len(r['raw']))
                out+=header+r['raw']
            struct.pack_into('<I',out,24,512)
        else:
            ldata=bytearray(take(self.data,self.lo,self.ll))
            for r in self.records:
                if 'new_raw' in r:
                    r['values'][9:11]=[len(ldata),len(r['new_raw'])]
                    ldata+=r['new_raw']
            stable=bytearray().join(struct.pack('<HHHHhhHBBIIHH',*r['values']) for r in self.records)
            so=512
            po=so+len(stable)
            lo=po+len(self.palette_table)
            to=lo+len(ldata)
            out=bytearray(self.data[:512])
            struct.pack_into('<8I',out,36,so,len(self.records),po,len(self.palettes),lo,len(ldata),to,self.tl)
            out+=stable+self.palette_table+ldata+take(self.data,self.to,self.tl)
        tmp=self.path.with_name(self.path.name+'.portrait-tmp')
        tmp.write_bytes(out)
        # Parse and decode the result before replacing the build copy.
        verified=SpriteFile(tmp)
        for i,r in enumerate(verified.records):
            if r['key'] in TARGETS and (verified.image(i).size!=TARGETS[r['key']] or r['axis']!=(0,0)):
                raise ValueError(f'Portrait verification failed: {r["key"]}')
            if r['key'] not in TARGETS and r['raw']!=self.records[i]['raw']:
                raise ValueError(f'Combat payload changed: {r["key"]}')
        tmp.replace(self.path)
        return changed


def portrait(path, number=1):
    sff=SpriteFile(path)
    for i,r in enumerate(sff.records):
        if r['key']==(9000,number):
            im=sff.image(i)
            if im.mode=='P':
                alpha=Image.frombytes('L',im.size,bytes(0 if p==0 else 255 for p in im.tobytes()))
                im=im.convert('RGBA')
                im.putalpha(alpha)
            return im
    return None
