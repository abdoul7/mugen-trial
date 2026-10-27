"""Native 320x240 arcade screenpack, built from the installed game's own art.

python tools/arcade_motif.py build/game/assets
python tools/arcade_motif.py --preview

No roster edits, online downloads, or shipped assets. --preview assembles the
available demo characters in an isolated fixture; missing AK1 characters are
reported, never silently presented as tested. Requires Pillow.
"""
import argparse
import io
import json
import math
from pathlib import Path
import re
import shutil
import struct

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'engine/Dolmexica Infinite 1.8'
NAVY = '#172332'
CREAM = '#E9D8AF'
ORANGE = '#D77139'
CYAN = '#6EACA7'
EDGE = '#080C12'


def read(path):
    return Path(path).read_text(encoding='latin1')


def write(path, body):
    Path(path).write_text(body, encoding='latin1')


def patch(body, section, values, remove=()):
    match = re.search(rf'(?ims)^\[{re.escape(section)}\][^\n]*\n(.*?)(?=^\[|\Z)', body)
    if not match:
        return body + f'\n[{section}]\n' + ''.join(f'{k} = {v}\n' for k, v in values.items())
    block = match.group(1)
    for key in remove:
        block = re.sub(rf'(?im)^\s*{re.escape(key)}\s*=.*\n?', '', block)
    for key, value in values.items():
        pattern = rf'(?im)^\s*{re.escape(key)}\s*=[^\n]*'
        line = f'{key} = {value}'
        block = re.sub(pattern, lambda _: line, block) if re.search(pattern, block) else block + line + '\n'
    return body[:match.start(1)] + block + body[match.end(1):]


def strip_sections(body, pattern):
    return re.sub(rf'(?ims)^\[(?:{pattern})\][^\n]*\n.*?(?=^\[|\Z)', '', body)


def indexed(im):
    rgb = im.convert('RGB').quantize(colors=254)
    palette = rgb.getpalette()[:762]
    out = rgb.point(lambda n: n + 1)
    out.putpalette([255, 0, 255] + palette + [0] * (765-len(palette)))
    if im.mode == 'RGBA':
        out.paste(0, mask=im.getchannel('A').point(lambda a: 255 if a < 128 else 0))
    return out


def write_sff(path, sprites):
    """SFF v1 with bounded native-size PCX sprites and independent palettes."""
    header = bytearray(512)
    header[:12] = b'ElecbyteSpr\0'
    header[12:16] = bytes((0, 1, 0, 1))
    struct.pack_into('<4I', header, 16, len({s[0] for s in sprites}), len(sprites), 512, 32)
    data = bytearray(header)
    for i, (group, number, im, ax, ay) in enumerate(sprites):
        stream = io.BytesIO()
        indexed(im).save(stream, format='PCX')
        payload = stream.getvalue()
        sub = bytearray(32)
        nxt = len(data)+32+len(payload) if i+1 < len(sprites) else 0
        struct.pack_into('<IIhhHHHB', sub, 0, nxt, len(payload), ax, ay, group, number, 0, 0)
        data += sub + payload
    path.write_bytes(data)


def portrait_v1(path):
    """Extract only 9000,1 for title decoration. Engine handles all gameplay art.

    V2/unsupported portraits are skipped, not decoded with a guessed codec.
    Preserve palette-index transparency and linked/shared-palette v1 sprites.
    """
    data = Path(path).read_bytes()
    if data[:12] != b'ElecbyteSpr\0' or data[15] != 1:
        return None
    count, offset = struct.unpack_from('<II', data, 20)
    images, palette, visited = [], None, set()
    for _ in range(count):
        if offset in visited or offset + 32 > len(data):
            raise ValueError(f'Malformed SFF chain: {path}')
        visited.add(offset)
        nxt, length, ax, ay, group, num, link, shared = struct.unpack_from('<IIhhHHHB', data, offset)
        if length:
            raw = data[offset+32:offset+32+length]
            if len(raw) != length:
                raise ValueError(f'Truncated sprite in {path}')
            if shared:
                if palette is None:
                    raise ValueError(f'Missing shared palette in {path}')
                # Shared PCXs omit the 769-byte palette trailer.
                if len(raw) < 769 or raw[-769] != 12:
                    raw += bytes([12]) + palette
            elif len(raw) >= 769 and raw[-769] == 12:
                palette = raw[-768:]
            images.append(raw)
        else:
            if link >= len(images):
                raise ValueError(f'Invalid SFF link in {path}')
            raw = images[link]
            images.append(raw)
        if (group, num) == (9000, 1):
            im = Image.open(io.BytesIO(raw))
            # Use indices directly; transparent index 0 may have any RGB value.
            alpha = Image.frombytes('L', im.size, bytes(0 if p == 0 else 255 for p in im.tobytes()))
            rgba = im.convert('RGBA')
            rgba.putalpha(alpha)
            return rgba
        if not nxt:
            break
        offset = nxt
    return None


def typeface(size):
    for name in ['C:/Windows/Fonts/impact.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf']:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    raise FileNotFoundError('Install Impact (Windows) or DejaVu Sans Condensed Bold to build the logo.')


def lettering(label, size, colors=(CREAM, ORANGE)):
    """Rasterize at game resolution, with a stepped arcade-metal fill and outline."""
    face = typeface(size)
    bounds = face.getbbox(label)
    mask = Image.new('L', (bounds[2]+12, bounds[3]-bounds[1]+10))
    ImageDraw.Draw(mask).text((4, 3-bounds[1]), label, font=face, fill=255)
    mask = mask.point(lambda p: 255 if p >= 100 else 0)
    # Slanted arcade display type, sampled at integer pixels.
    mask = mask.transform((mask.width+10, mask.height), Image.Transform.AFFINE,
                          (1, .18, -mask.height*.18, 0, 1, 0), Image.Resampling.NEAREST)
    outline = mask.filter(ImageFilter.MaxFilter(5))
    result = Image.new('RGBA', mask.size, (0, 0, 0, 0))
    result.paste(EDGE, mask=outline)
    fill = Image.new('RGB', mask.size, colors[0])
    d = ImageDraw.Draw(fill)
    d.rectangle((0, mask.height//2, mask.width, mask.height), fill=colors[1])
    d.line((0,mask.height//2,mask.width,mask.height//2), fill='#FFF0CB')
    result.paste(fill, mask=mask)
    return result


def stamp(im, xy, label, size, colors=(CREAM, ORANGE)):
    layer = lettering(label, size, colors)
    im.paste(layer, xy, layer)


def backdrop():
    im = Image.new('RGB', (320, 240), NAVY)
    d = ImageDraw.Draw(im)
    # Restrained textile/metal dithering at the same pixel scale as the fighters.
    for y in range(240):
        for x in range(320):
            if (x + y) % 7 == 0:
                d.point((x,y), fill='#1D2A39')
    for x in [-150, 80, 310]:
        d.polygon([(x,0),(x+45,0),(x-75,240),(x-120,240)], fill='#202F41')
        d.line((x+45,0,x-75,240), fill='#344251')
    d.rectangle((0,0,319,6), fill=EDGE)
    d.line((0,7,319,7), fill=ORANGE)
    d.rectangle((0,226,319,239), fill=EDGE)
    d.line((0,225,319,225), fill='#8D7356')
    return im


def frame(im, box, color=CREAM):
    d = ImageDraw.Draw(im)
    d.rectangle(box, fill='#101923', outline=EDGE)
    x,y,r,b = box
    d.line((x+1,b-1,x+1,y+1,r-1,y+1), fill=color)
    d.line((r-1,y+1,r-1,b-1,x+1,b-1), fill='#5A5147')


def make_screens(portraits, slots):
    title = backdrop()
    stamp(title, (7,18), 'JUMP', 46)
    stamp(title, (43,57), 'RIFT', 44, ('#F8EACA','#AD4D2F'))
    d = ImageDraw.Draw(title)
    d.line((15,104,151,104), fill=CREAM)
    # Use real installed portrait pixels, at their original sampling density.
    for i, portrait in enumerate(portraits[:3]):
        y = 18+i*66
        frame(title, (181, y, 309, y+63), CYAN if i%2==0 else ORANGE)
        canvas = Image.new('RGBA',(124,59))
        # Crop the face at native resolution; never invent/repaint a character.
        top = min(portrait.height//6, max(0,portrait.height-59))
        crop = portrait.crop((0,top,min(portrait.width,124),min(portrait.height,top+59)))
        canvas.alpha_composite(crop, ((124-crop.width)//2,0))
        title.paste(canvas,(183,y+2),canvas)
    if not portraits:
        stamp(title,(185,57),'1 VS 1',22)
    select = backdrop()
    stamp(select,(73,9),'CHARACTER SELECT',17)
    rows = math.ceil(slots/10)
    cell = min(25, 116//max(rows,1)-2)
    grid_y = 222-rows*(cell+2)
    grid_x = (320-10*(cell+2)+2)//2
    portrait_bottom = min(177, grid_y-16)
    frame(select,(10,35,125,portrait_bottom),CYAN)
    frame(select,(195,35,310,portrait_bottom),ORANGE)
    stamp(select,(136,52),'VS',26)
    versus = backdrop()
    stamp(versus,(97,9),'GET READY',20)
    frame(versus,(10,41,139,200),CYAN)
    frame(versus,(181,41,310,200),ORANGE)
    # VS is a foreground sprite below so portraits cannot cover it.
    options = backdrop()
    # The engine draws its own options heading and inner panel at fixed coordinates.
    victory = backdrop()
    stamp(victory,(9,15),'WINNER',40)
    frame(victory,(163,29,310,195),CYAN)
    stamp(victory,(12,78),'YOU WIN',20)
    gameover = backdrop()
    stamp(gameover,(56,85),'GAME OVER',34)
    return [title,select,versus,options,victory,gameover], (rows,cell,grid_x,grid_y)


def roster_entries(assets):
    body = read(assets/'data/select.def')
    match = re.search(r'(?ims)^\[characters\](.*?)(?=^\[|\Z)',body)
    entries = []
    for line in (match.group(1) if match else '').splitlines():
        name = line.split(';')[0].split(',')[0].strip()
        if name:
            entries.append(name)
    return entries


def title_portraits(assets, entries):
    images, notes = [], []
    for name in entries:
        if name.lower() == 'randomselect':
            continue
        path = assets/'chars'/name
        definition = path if path.suffix.lower()=='.def' else path/(path.name+'.def')
        if not definition.exists():
            notes.append(f'{name}: no DEF for title portrait')
            continue
        match = re.search(r'(?im)^\s*sprite\s*=\s*([^;\r\n]+)',read(definition))
        if not match:
            continue
        try:
            portrait = portrait_v1(definition.parent/match.group(1).strip().replace('\\','/'))
        except (ValueError,OSError) as exc:
            notes.append(f'{name}: title decoration skipped ({exc})')
            continue
        if portrait is not None:
            images.append(portrait)
        else:
            notes.append(f'{name}: no supported v1 title portrait; engine portrait unaffected')
    # Spread the title across the installed roster, rather than favour one series.
    if len(images)>3:
        images = [images[round(i*(len(images)-1)/2)] for i in range(3)]
    return images,notes


def build(assets):
    assets = Path(assets).resolve()
    data = assets/'data'
    if (data/'480p/fight.def').exists():
        raise ValueError('Existing data/480p/fight.def would override this HUD. Rebuild with stock motif before applying arcade.')
    entries = roster_entries(assets)
    if not 1 <= len(entries) <= 60:
        raise ValueError('Expected 1..60 select entries, including randomselect')
    portraits,notes = title_portraits(assets,entries)
    screens, (rows,cell,gx,gy) = make_screens(portraits,len(entries))
    dst = data/'arcade'
    dst.mkdir(exist_ok=True)
    sprites = [(900,n,im,0,0) for n,im in enumerate(screens)]
    for group,color in [(150,CREAM),(151,ORANGE),(160,CYAN),(161,CYAN),(170,ORANGE),(171,ORANGE)]:
        im = Image.new('RGBA',(cell,cell),(0,0,0,0))
        d = ImageDraw.Draw(im)
        if group in (150,151):
            frame(im,(0,0,cell-1,cell-1),color)
            if group==151:
                stamp(im,(max(0,cell//2-6),0),'?',cell-2)
        else:
            d.rectangle((0,0,cell-1,cell-1),outline=EDGE,width=3)
            d.rectangle((1,1,cell-2,cell-2),outline=color,width=2)
            d.rectangle((0,0,3,3),fill=CREAM)
            d.rectangle((cell-4,cell-4,cell-1,cell-1),fill=CREAM)
        sprites.append((group,0,im,0,0))
    vs = lettering('VS',38)
    sprites.append((901,0,vs,vs.width//2,vs.height//2))
    write_sff(dst/'system.sff',sprites)
    body = read(data/'system.def')
    body = strip_sections(body,r'(?:Title|Select|Versus|Option|Netplay|Victory|Win)BG[^\]]*|Begin Action [^\]]*')
    body = patch(body,'Info',{'name':'"Jump Rift / Arcade"','author':'"Jump Force Vita project"','localcoord':'320,240'})
    body = patch(body,'Files',{'spr':'system.sff','snd':'../system.snd','select':'../select.def','fight':'fight.def','logo.storyboard':'','intro.storyboard':'','font1':'font/f4x6.fnt','font2':'font/f6x9.fnt','font3':'font/jg.fnt'})
    menu = {'menu.pos':'22,124','menu.item.font':'2,0,1','menu.item.active.font':'2,5,1','menu.item.spacing':'0,15','menu.window.visibleitems':6,'menu.window.margins.y':'12,8','menu.boxcursor.visible':1,'menu.boxcursor.coords':'-5,-10,126,2','fadein.time':12,'fadeout.time':10}
    for key in ['arcade','versus','training','watch','options','exit']:
        menu['menu.itemname.'+key] = '"'+key.upper()+'"'
    for key in ['netplay','freeplay','teamarcade','teamversus','teamcoop','survival','survivalcoop','credits','story','osu','superwatch','randomwatch']:
        menu['menu.itemname.'+key] = '""'
    body = patch(body,'Title Info',menu)
    faceheight = min(177,gy-16)-38
    fs = min(.70,faceheight/140)
    values = {'rows':rows,'columns':10,'pos':f'{gx},{gy}','cell.size':f'{cell},{cell}','cell.spacing':'2,2','showemptyboxes':0,'moveoveremptyboxes':0,'portrait.scale':f'{(cell-2)/25:.3f},{(cell-2)/25:.3f}','portrait.offset':'1,1','p1.cursor.startcell':'0,0','p2.cursor.startcell':f'0,{min(9,len(entries)-1)}','title.font':-1,'p1.face.offset':'28,38','p2.face.offset':'292,38','p1.face.scale':f'{fs},{fs}','p2.face.scale':f'{fs},{fs}','p1.name.offset':f'12,{gy-4}','p2.name.offset':f'308,{gy-4}','p1.name.font':'1,0,1','p2.name.font':'1,0,-1','stage.pos':'160,235','stage.active.font':'1,0,0','stage.active2.font':'1,5,0','stage.done.font':'1,0,0'}
    body = patch(body,'Select Info',values)
    body = patch(body,'VS Screen',{'time':150,'p1.pos':'15,46','p2.pos':'305,46','p1.scale':'1,1','p2.scale':'1,1','p1.name.pos':'12,215','p2.name.pos':'308,215','p1.name.font':'2,0,1','p2.name.font':'2,0,-1'})
    body = patch(body,'Victory Screen',{'enabled':1,'time':300,'p1.spr':'9000,1','p1.offset':'177,40','p1.scale':'1,1','p1.window':'164,30,309,194','p1.name.offset':'12,117','p1.name.font':'2,0,1','winquote.offset':'12,139','winquote.font':'1,0,1','winquote.window':'12,130,153,212','winquote.textwrap':'w'})
    body = patch(body,'Win Screen',{'wintext.text':'ARCADE COMPLETE','wintext.font':'3,0,0','wintext.offset':'160,80'})
    body = patch(body,'Demo Mode',{'enabled':0})
    body = patch(body,'Game Over Screen',{'enabled':1,'storyboard':'gameover.def'})
    for name,n in [('Title',0),('Select',1),('Versus',2),('Option',3),('Victory',4),('Win',4)]:
        body += f'\n[{name}BGdef]\nbgclearcolor = 8,12,18\n[{name}BG 0]\ntype = normal\nspriteno = 900,{n}\nstart = -160,0\nmask = 0\n'
    body += '\n[VersusBG emblem]\ntype = normal\nspriteno = 901,0\nstart = 0,123\nlayerno = 1\nmask = 1\n'
    write(dst/'system.def',body)
    write(dst/'gameover.def','[Info]\nlocalcoord = 320,240\n[SceneDef]\nspr = system.sff\nstartscene = 0\n[Scene 0]\nend.time = 180\nfadein.time = 15\nfadeout.time = 15\nlayer0.anim = 0\nlayer0.offset = 0,0\n[Begin Action 0]\n900,5,0,0,-1\n')
    hudsprites = fight(data,dst)
    cfg = data/'mugen.cfg'
    write(cfg,re.sub(r'(?im)^(\s*motif\s*=)[^\n]*',r'\1 data/arcade/system.def',read(cfg)))
    estimate = sum(im.width*im.height*4 for _,_,im,_,_ in sprites+hudsprites)
    report = {'slots':len(entries),'rows':rows,'columns':10,'cell_px':cell,'native_resolution':[320,240],'system_sff_bytes':(dst/'system.sff').stat().st_size,'fight_sff_bytes':(dst/'fight.sff').stat().st_size,'uncompressed_rgba_bytes':estimate,'title_portraits':len(portraits),'notes':notes}
    (dst/'build-report.json').write_text(json.dumps(report,indent=2))
    for n,im in enumerate(screens):
        im.save(dst/f'preview-{n}.png')
    print(json.dumps(report,indent=2))
    return report


def fight(data,dst):
    body = read(data/'fight.def')
    body = strip_sections(body,r'(?:Simul|Turns) [^\]]*|Osu|Begin Action [^\]]*')
    body = patch(body,'Files',{'sff':'fight.sff','snd':'../fight.snd','font1':'jg.fnt','font2':'num1.fnt','font3':'name1.fnt','fightfx.sff':'../fightfx.sff','fightfx.air':'../fightfx.air','common.snd':'../common.snd'},['osu.sff','osu.air','osu.snd'])
    sprites = []
    for group, width, height, colors in [(10,122,11,('#B4B9B5','#42484A')),(11,122,11,('#B4B9B5','#42484A')),(12,118,7,('#C96839','#6B2526')),(13,118,7,('#F3E8AD','#AB762E')),(40,95,7,('#B4B9B5','#42484A')),(41,95,7,('#B4B9B5','#42484A')),(43,91,3,('#A9DDD2','#3B7A83'))]:
        im = Image.new('RGB',(width,height),EDGE)
        d = ImageDraw.Draw(im)
        if group in (10,11,40,41):
            d.rectangle((0,0,width-1,height-1),outline=colors[1])
            d.line((0,height-1,0,0,width-1,0),fill=colors[0])
        else:
            d.rectangle((0,0,width-1,height-1),fill=colors[1])
            d.rectangle((0,0,width-1,max(0,height//2-1)),fill=colors[0])
            for x in range(8,width,9):
                d.line((x,height-2,x,height-1),fill='#735C39' if group<40 else '#28515E')
        sprites.append((group,0,im,width-1,0))
    im = Image.new('RGBA',(29,29),(0,0,0,0))
    ImageDraw.Draw(im).rectangle((0,0,28,28),outline=CREAM,width=1)
    sprites.append((50,0,im,0,0))
    for group in [100,101,102,103,104,105,106,107,110]:
        im = Image.new('RGBA',(7,7),(0,0,0,0))
        d = ImageDraw.Draw(im)
        d.polygon([(3,0),(6,3),(3,6),(0,3)],fill=ORANGE,outline=EDGE)
        d.line((1,3,3,1,4,2),fill=CREAM)
        sprites.append((group,0,im,0,0))
    for group,label in [(80,'FIGHT!'),(200,'K.O.')]:
        im = lettering(label,39)
        sprites.append((group,0,im,im.width//2,im.height//2))
        body += f'\n[Begin Action {group}]\n{group},0,0,0,45\n'
    life = {'p1.pos':'137,16','p2.pos':'183,16','p1.bg0.spr':'10,0','p2.bg0.spr':'10,0','p1.range.x':'-2,-119','p2.range.x':'2,119','p1.front.offset':'-2,2','p2.front.offset':'2,2','p1.mid.offset':'-2,2','p2.mid.offset':'2,2'}
    body=patch(body,'Lifebar',life,['p1.bg0.anim','p2.bg0.anim'])
    body=patch(body,'Powerbar',{'p1.pos':'112,224','p2.pos':'208,224','p1.bg0.spr':'40,0','p2.bg0.spr':'40,0','p1.front.offset':'-2,2','p2.front.offset':'2,2','p1.range.x':'-2,-92','p2.range.x':'2,92','p1.counter.offset':'8,6','p2.counter.offset':'-8,6'},['p1.bg0.anim','p2.bg0.anim'])
    body=patch(body,'Face',{'p1.pos':'16,30','p2.pos':'304,30','p1.face.offset':'2,2','p2.face.offset':'-2,2','p1.face.scale':'1,1','p2.face.scale':'1,1'})
    body=patch(body,'Name',{'p1.pos':'16,12','p2.pos':'304,12'})
    body=patch(body,'WinIcon',{'p1.pos':'51,32','p2.pos':'269,32','p1.iconoffset':'9,0','p2.iconoffset':'-9,0'})
    body=patch(body,'Combo',{'team1.text.text':'HIT COMBO','team2.text.text':'HIT COMBO','team1.pos':'12,85','team2.pos':'308,85'})
    body=patch(body,'Continue',{'continue.text':'"CONTINUE?"'})
    write_sff(dst/'fight.sff',sprites)
    write(dst/'fight.def',body)
    return sprites


def preview():
    """Assemble an isolated fixture using existing pipeline helpers, no roster edits."""
    import build_assets as pipeline
    game = ROOT/'build/arcade-preview'
    if game.exists():
        raise FileExistsError(f'{game} exists; reapply to its assets directory instead.')
    game.mkdir(parents=True)
    for name in ['assets','Dolmexica Infinite for Windows.exe','fmod.dll']:
        src=ENGINE/name
        (shutil.copytree if src.is_dir() else shutil.copy2)(src,game/name)
    assets=game/'assets'
    cfg=json.loads((ROOT/'roster.json').read_text())
    demo=ROOT/cfg['demo_root']
    entries,skipped=[],[]
    for char in cfg['characters']:
        if char.get('source')=='stock':
            entries.append((char.get('def',char['id']),'stages/kfm.def'))
            continue
        source=ROOT/char['root']/char['folder'] if 'root' in char else demo/'Chars'/char['folder']
        if not source.is_dir():
            skipped.append(char['id'])
            continue
        dest=assets/'chars'/char['id']
        shutil.copytree(source,dest)
        for src,dst in char.get('copy_files',[]):
            shutil.copy2(demo/pipeline.exact_case(str(demo),src),dest/dst)
        pipeline.patch_char_def(str(dest/char['def']),char.get('localcoord',pipeline.KEEP),char.get('def_overrides'))
        stage='stages/kfm.def'
        st=char.get('stage',{})
        if 'id' in st:
            sdir=demo/'Stages'
            original=sdir/pipeline.exact_case(str(sdir),st['def'])
            spr=re.search(r'(?im)^\s*spr\s*=\s*([^;\r\n]+)',read(original)).group(1).strip()
            source_sff=original.parent/pipeline.exact_case(str(original.parent),spr)
            shutil.copy2(source_sff,assets/'stages'/f'{st["id"]}.sff')
            stage=f'stages/{st["id"]}.def'
            pipeline.patch_stage_def(str(original),str(assets/stage),st['id'],'')
        entries.append((char['id']+'/'+char['def'],stage))
    stages=list(dict.fromkeys(stage for _,stage in entries))
    write(assets/'data/select.def','[Characters]\n'+'\n'.join(e+', '+stage for e,stage in entries)+'\nrandomselect\n[ExtraStages]\n'+'\n'.join(stages)+'\n[Options]\narcade.maxmatches = 1,0,0,0,0,0,0,0,0,0\n')
    (game/'fixture.json').write_text(json.dumps({'included':entries,'missing_sources':skipped,'bgm':'disabled in fixture; original stage sprites retained'},indent=2))
    print('Preview fixture missing sources: '+', '.join(skipped))
    return assets


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('assets',nargs='?',default=str(ROOT/'build/game/assets'))
    parser.add_argument('--preview',action='store_true')
    args=parser.parse_args()
    build(preview() if args.preview else args.assets)


if __name__=='__main__':
    main()
