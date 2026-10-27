"""Build Legends card art/UI authoring kit, previews and bounded runtime atlases.

python tools/build_legends_kit.py --out <deliverable directory>
python tools/build_legends_kit.py --fetch --out <deliverable directory>

Fetches only recorded Higgsfield outputs when explicitly requested. No game
source/roster mutation, engine launch or paid generation. Requires Pillow.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import textwrap
import urllib.request

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
NAVY='#111C2B'
DARK='#080D16'
CREAM='#EDDDBB'
MUTED='#A7ABB0'
GOLD='#EAC577'
ART_BOXES={'common':(8,42,120,114),'rare':(5,35,123,142),
           'epic':(3,37,125,181),'legendary':(0,0,128,192)}
FOCAL_Y={'my_ninja_way':.15,'saiyan_pride':.10,'scarlet_resolve':.05,
         'chidori':.15,'spirit_gun':.1,'bungee_gum':0,
         'kaio_ken':.1,'bankai':0,'plus_ultra':.12,
         'za_warudo':.5,'senzu_bean':.45,'pot_of_greed':.2}


def font(size,bold=False):
    paths=['C:/Windows/Fonts/consolab.ttf' if bold else 'C:/Windows/Fonts/consola.ttf',
           '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf']
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p,size)
    return ImageFont.load_default(size=size)


def label(im,xy,value,size=8,color=CREAM,bold=False):
    f=font(size,bold or size<=8)
    box=f.getbbox(value)
    mask=Image.new('L',(max(1,box[2]-box[0]+2),max(1,box[3]-box[1]+2)))
    ImageDraw.Draw(mask).text((-box[0],-box[1]),value,font=f,fill=255)
    mask=mask.point(lambda p:255 if p>=75 else 0)
    im.paste(color,xy,mask)


def family_icon(family,size=16,color=CREAM):
    im=Image.new('RGBA',(16,16))
    d=ImageDraw.Draw(im)
    if family=='resolve':
        d.polygon([(3,2),(12,2),(12,9),(8,14),(3,9)],outline=color,width=2)
        d.line((8,4,8,10),fill=color,width=2)
    elif family=='secret_arts':
        d.polygon([(12,1),(15,1),(5,14),(1,14)],fill=color)
        d.line((2,3,5,6),fill=color,width=1)
    elif family=='awakenings':
        d.polygon([(8,0),(11,6),(13,4),(14,10),(11,14),(4,14),(1,10),(4,4),(5,8)],fill=color)
        d.polygon([(8,6),(10,11),(8,13),(6,11)],fill=NAVY)
    else:
        d.line((2,1,13,1),fill=color,width=2)
        d.line((2,14,13,14),fill=color,width=2)
        d.line((4,3,11,11,11,12),fill=color,width=2)
        d.line((11,3,4,11,4,12),fill=color,width=2)
    return im.resize((size,size),Image.Resampling.NEAREST)


def panel(size,accent=CREAM,alpha=255):
    im=Image.new('RGBA',size,(8,13,22,alpha))
    d=ImageDraw.Draw(im)
    w,h=size
    d.rectangle((0,0,w-1,h-1),outline=DARK,width=1)
    d.line((1,h-2,1,1,w-2,1),fill=accent,width=1)
    d.line((w-2,1,w-2,h-2,1,h-2),fill='#4D4C50',width=1)
    return im


def frame(family,rarity,catalog):
    accent=catalog['families'][family]['color']
    tier=catalog['rarities'][rarity]
    im=Image.new('RGBA',(128,192))
    d=ImageDraw.Draw(im)
    trim={'common':'#8B8B85','rare':'#BDC6CB','epic':'#D4AD6D','legendary':'#F0D294'}[rarity]
    if rarity in ('common','rare'):
        d.rectangle((0,0,127,191),fill=NAVY)
        d.rectangle(ART_BOXES[rarity],fill=(0,0,0,0))
    else:
        # Full/extended art stays visible beneath translucent information bands.
        d.rectangle((4,4,123,36),fill=(8,13,22,210))
        d.rectangle((4,151,123,187),fill=(8,13,22,218))
    d.rectangle((0,0,127,191),outline=DARK,width=2)
    d.rectangle((2,2,125,189),outline=trim,width=1)
    if rarity in ('common','rare'):
        d.rectangle((5,5,122,34),fill=DARK)
        d.rectangle((6,122,121,169),fill='#0A111D')
        d.line((6,120,121,120),fill='#4D4C50')
    d.line((7,36,120,36),fill=accent,width=2)
    d.rectangle((6,174,121,185),fill=(8,13,22,230))
    for p in range(tier['pips']):
        x=9+p*7
        d.polygon([(x,178),(x+2,176),(x+4,178),(x+2,180)],fill=trim)
    im.alpha_composite(family_icon(family,10,accent),(8,23))
    # Distinct family corner motif is visible on every rarity, not just color.
    for x,y in [(3,3),(120,3),(3,184),(120,184)]:
        d.rectangle((x,y,x+4,y+4),fill=accent)
    if rarity=='legendary':
        for y in range(12,181,9):
            d.point((3,y),fill=CREAM)
            d.point((124,y+2),fill=GOLD)
        d.polygon([(113,38),(124,38),(124,49)],fill=GOLD)
    return im


def card_base(art,family,rarity,catalog,focal_y=.36):
    im=Image.new('RGBA',(128,192))
    box=ART_BOXES[rarity]
    crop=ImageOps.fit(art,(box[2]-box[0],box[3]-box[1]),Image.Resampling.NEAREST,centering=(.5,focal_y))
    im.paste(crop,(box[0],box[1]))
    im.alpha_composite(frame(family,rarity,catalog))
    return im


def card_face(base,card,catalog):
    im=base.copy()
    title=card['name']
    size=11
    while font(size,True).getlength(title)>111 and size>7:
        size-=1
    label(im,(8,9),title,size,bold=True)
    label(im,(22,25),catalog['families'][card['family']]['label'].upper(),7)
    y=128 if card['rarity'] in ('common','rare') else 155
    lines=textwrap.wrap(card['short_text'],width=21)
    for line in lines[:3]:
        label(im,(9,y),line,8)
        y+=10
    act={'equip':'EQUIP','legal_action':'NEXT OPENING','buff':'POWER UP',
         'world':'WORLD EFFECT','recovery':'RECOVERY','draw':'DRAW'}[card['activation']]
    label(im,(46,177),act,7)
    label(im,(112,25),catalog['rarities'][card['rarity']]['glyph'],7,GOLD,True)
    return im


def hand_tile(art,card,catalog):
    accent=catalog['families'][card['family']]['color']
    im=panel((86,26),accent)
    im.alpha_composite(ImageOps.fit(art,(22,22),Image.Resampling.NEAREST),(3,2))
    im.alpha_composite(family_icon(card['family'],8,accent),(27,4))
    name=card['short_name']
    label(im,(38,5),name,6)
    label(im,(28,15),card['activation'].replace('_',' ').upper()[:13],6,MUTED)
    return im


def button(name):
    im=Image.new('RGBA',(12,12))
    d=ImageDraw.Draw(im)
    if name=='square': d.rectangle((2,2,9,9),outline='#DFA0C6')
    elif name=='triangle': d.polygon([(6,1),(11,10),(1,10)],outline='#A3D7AC')
    elif name=='circle': d.ellipse((2,2,10,10),outline='#E5A18D')
    elif name=='cross':
        d.line((2,2,10,10),fill='#96B9E3',width=2)
        d.line((10,2,2,10),fill='#96B9E3',width=2)
    else: label(im,(3,2),name,8)
    return im


def ui_sprites(catalog):
    out={}
    for family,data in catalog['families'].items():
        out['family_'+family]=family_icon(family,16,data['color'])
    for name in ['square','triangle','circle','cross','L','R']:
        out['button_'+name]=button(name)
    out['hand_empty']=panel((86,26),'#696C71')
    for state,color in [('ready','#85BBA3'),('armed','#F0C368'),('blocked','#C07578'),('cooldown','#7D8CA5')]:
        im=Image.new('RGBA',(86,26))
        d=ImageDraw.Draw(im)
        d.rectangle((0,0,85,25),outline=color,width=1)
        if state in ('blocked','cooldown'):
            d.rectangle((2,2,83,23),fill=(8,13,22,160))
        out['hand_'+state]=im
    for i in range(6):
        im=Image.new('RGBA',(90,30))
        d=ImageDraw.Draw(im)
        shade=(180+i*12,145+i*11,76+i*8,255)
        for x,y in [(0,0),(84,0),(0,24),(84,24)]:
            d.rectangle((x,y,x+5,y+5),outline=shade,width=1)
        out[f'focus_{i}']=im
    out['hype_track']=panel((150,5),'#6E8F9B')
    out['hype_fill']=Image.new('RGBA',(146,1),'#79CAB8')
    out['hype_ready']=Image.new('RGBA',(146,1),'#F0D294')
    out['resolve_socket']=panel((22,22),catalog['families']['resolve']['color'])
    out['awakening_timer']=panel((52,5),catalog['families']['awakenings']['color'])
    out['time_lock_badge']=family_icon('plot_twists',18,GOLD)
    for state,color in [('active',CREAM),('reserve','#697B91'),('ko','#6E434A')]:
        im=panel((38,24),color)
        if state=='ko':
            d=ImageDraw.Draw(im)
            d.line((3,3,34,20),fill='#BB7272',width=2)
            d.line((34,3,3,20),fill='#BB7272',width=2)
        out['squad_'+state]=im
    for state in ['draw','queued','lock','target']:
        im=panel((14,14),'#B69A70')
        d=ImageDraw.Draw(im)
        if state=='draw':
            d.rectangle((3,3,9,11),outline=CREAM)
            d.line((6,2,11,2,11,9),fill=CREAM)
        elif state=='queued':
            d.rectangle((3,3,8,9),outline=CREAM)
            d.rectangle((6,6,11,12),outline=GOLD)
        elif state=='lock':
            d.rectangle((4,6,10,11),fill=MUTED)
            d.arc((4,2,10,9),180,360,fill=MUTED)
        else:
            d.ellipse((3,3,11,11),outline=GOLD)
            d.line((7,2,7,12),fill=GOLD)
            d.line((2,7,12,7),fill=GOLD)
        out['icon_'+state]=im
    out['relay_panel']=panel((228,44),'#B69A70')
    out['deal_panel']=panel((284,52),'#7E9EAA')
    out['results_panel']=panel((250,100),'#B69A70')
    # Atlas contains compact primitives only, not sixteen full-size card templates.
    return out


def vfx_sprites():
    out={}
    for i in range(6):
        im=Image.new('RGBA',(32,16))
        d=ImageDraw.Draw(im)
        r=4+i%3
        d.polygon([(0,8),(22-r,3),(27,8),(22-r,13)],fill='#356D9D')
        d.ellipse((20-r,8-r,20+r,8+r),fill='#94D8E8')
        d.rectangle((18,6,23,9),fill='#FFF1CE')
        out[f'spirit_shot_{i}']=im
    for i in range(4):
        im=Image.new('RGBA',(48,32))
        d=ImageDraw.Draw(im)
        d.line([(0,16),(10,8+i),(16,21),(28,5+i),(34,18),(47,13)],fill='#A9DCEB',width=2)
        d.line((8,26,39,5),fill=CREAM,width=1)
        out[f'lightning_{i}']=im
        heal=Image.new('RGBA',(16,16))
        hd=ImageDraw.Draw(heal)
        rr=2+i
        hd.line((8-rr,8,8+rr,8),fill='#C8E1A9')
        hd.line((8,8-rr,8,8+rr),fill='#C8E1A9')
        out[f'heal_{i}']=heal
        gum=Image.new('RGBA',(16,4))
        gd=ImageDraw.Draw(gum)
        gd.line((0,1,15,1+i%2),fill='#D994C0',width=2)
        out[f'tether_{i}']=gum
    for name,color in [('red','#C95359'),('teal','#69B9A4')]:
        for i in range(4):
            im=Image.new('RGBA',(64,96))
            d=ImageDraw.Draw(im)
            for x in range(4,61,8):
                h=14+((x*3+i*7)%30)
                d.polygon([(x-3,88),(x,88-h),(x+3,88)],fill=color)
            d.arc((8,16+i,56,94-i),185,355,fill=CREAM,width=1)
            out[f'aura_{name}_{i}']=im
    for i in range(6):
        im=Image.new('RGBA',(64,64))
        d=ImageDraw.Draw(im)
        r=14+i*3
        d.ellipse((32-r,32-r,32+r,32+r),outline=GOLD,width=1)
        for a in range(0,360,45):
            rad=math.radians(a+i*5)
            x,y=round(32+math.cos(rad)*r),round(32+math.sin(rad)*r)
            d.rectangle((x-1,y-1,x+1,y+1),fill=CREAM)
        out[f'time_ring_{i}']=im
        spark=Image.new('RGBA',(16,16))
        sd=ImageDraw.Draw(spark)
        rr=2+i%4
        sd.line((8-rr,8,8+rr,8),fill=GOLD,width=1)
        sd.line((8,8-rr,8,8+rr),fill=CREAM,width=1)
        out[f'draw_spark_{i}']=spark
        edge=Image.new('RGBA',(40,60))
        ed=ImageDraw.Draw(edge)
        ww=3+i*6
        ed.rectangle(((40-ww)//2,0,(40+ww)//2,59),outline=GOLD,width=1)
        out[f'reveal_edge_{i}']=edge
    # Translate and clip this small strip in native code; don't store full-face frames.
    sheen=Image.new('RGBA',(12,64))
    sh=ImageDraw.Draw(sheen)
    sh.polygon([(0,0),(4,0),(11,63),(7,63)],fill=(255,235,180,90))
    out['foil_sheen_strip']=sheen
    return out


def atlas(sprites,width):
    # Non-rotating maximal rectangles with a transparent 1px gutter. Avoid a
    # tall aura making an entire shelf of tiny UI sprites unnecessarily tall.
    ordered=sorted(sprites.items(),key=lambda p:(-p[1].width*p[1].height,p[0]))
    area=sum((im.width+2)*(im.height+2) for _,im in ordered)
    needed=max(max(im.height+2 for _,im in ordered),math.ceil(area/width))
    height=2**math.ceil(math.log2(max(1,needed)))
    while True:
        entries={}
        free=[(0,0,width,height)]
        failed=False
        for key,im in ordered:
            w,h=im.width+2,im.height+2
            if w>width: raise ValueError(f'Sprite too wide: {key}')
            fits=[(min(rw-w,rh-h),max(rw-w,rh-h),y,x) for x,y,rw,rh in free if rw>=w and rh>=h]
            if not fits:
                failed=True
                break
            _,_,y,x=min(fits)
            entries[key]={'x':x+1,'y':y+1,'width':im.width,'height':im.height}
            remaining=[]
            for fx,fy,fw,fh in free:
                if x>=fx+fw or x+w<=fx or y>=fy+fh or y+h<=fy:
                    remaining.append((fx,fy,fw,fh))
                    continue
                if x>fx: remaining.append((fx,fy,x-fx,fh))
                if x+w<fx+fw: remaining.append((x+w,fy,fx+fw-x-w,fh))
                if y>fy: remaining.append((fx,fy,fw,y-fy))
                if y+h<fy+fh: remaining.append((fx,y+h,fw,fy+fh-y-h))
            unique=list(dict.fromkeys(remaining))
            free=[r for i,r in enumerate(unique) if not any(i!=j and q[0]<=r[0] and q[1]<=r[1]
                  and q[0]+q[2]>=r[0]+r[2] and q[1]+q[3]>=r[1]+r[3] for j,q in enumerate(unique))]
        if not failed: break
        height*=2
        if height>4096: raise ValueError('Atlas packing failed')
    out=Image.new('RGBA',(width,height))
    for key,im in sprites.items():
        p=entries[key]
        out.alpha_composite(im,(p['x'],p['y']))
    return out,entries


def contact_sheet(cards,catalog):
    cols=4
    w,h=cols*144+16,3*218+50
    im=Image.new('RGBA',(w,h),NAVY)
    label(im,(16,12),'LEGENDS / STARTER SET',18,bold=True)
    label(im,(16,34),'12 CARDS / 4 FAMILIES / ART AND DESIGN KIT',8,MUTED)
    for i,card in enumerate(catalog['cards']):
        x,y=16+(i%cols)*144,58+(i//cols)*218
        im.alpha_composite(cards[card['id']],(x,y))
        label(im,(x,y+197),card['family'].replace('_',' ').upper(),7,MUTED)
    return im


def render(out,source,fetch=False):
    catalog=json.loads((ROOT/'tools/legends/catalog.json').read_text())
    provenance=json.loads((ROOT/'tools/legends/art_sources.json').read_text())
    if len(catalog['families'])!=4 or len({c['id'] for c in catalog['cards']})!=len(catalog['cards']):
        raise ValueError('Catalog family/ID invariant failed')
    for p in ['illustrations','frames','cards','runtime','ui','vfx','previews','data']:
        (out/p).mkdir(parents=True,exist_ok=True)
    source.mkdir(parents=True,exist_ok=True)
    sheets={}
    hashes={}
    for item in provenance['sheets']:
        path=source/(item['key']+'.png')
        if not path.exists() and fetch:
            urllib.request.urlretrieve(item['url'],path)
        if not path.exists():
            raise FileNotFoundError(f'{path}: run with --fetch or supply the recorded source')
        hashes[item['key']]=hashlib.sha256(path.read_bytes()).hexdigest()
        if item.get('sha256')!=hashes[item['key']]:
            raise ValueError(f'Source sheet SHA-256 mismatch: {path}')
        sheets[item['key']]=Image.open(path).convert('RGB')
    arts,bases,faces,hand_previews={}, {}, {}, {}
    for card in catalog['cards']:
        sheet=sheets[card['art']['sheet']]
        idx=card['art']['panel']
        # Tool coerced 2:1 to 16:9; exact third boundaries are recorded here.
        crop=sheet.crop((round(idx*sheet.width/3),0,round((idx+1)*sheet.width/3),sheet.height))
        art=ImageOps.fit(crop,(128,192),Image.Resampling.NEAREST,centering=(.5,.42))
        # Uniform native illustration pixel density; keep fine sprite shade ramps.
        art=art.quantize(colors=96).convert('RGBA')
        arts[card['id']]=art
        art.save(out/'illustrations'/f'{card["id"]}.png')
        base=card_base(art,card['family'],card['rarity'],catalog,FOCAL_Y[card['id']])
        bases[card['id']]=base
        face=card_face(base,card,catalog)
        faces[card['id']]=face
        face.save(out/'cards'/f'{card["id"]}.png')
    for family in catalog['families']:
        for rarity in catalog['rarities']:
            frame(family,rarity,catalog).save(out/'frames'/f'{family}_{rarity}.png')
    back=panel((128,192),'#AF8D5B')
    d=ImageDraw.Draw(back)
    for y in range(9,184,8):
        for x in range(9,120,8):
            d.point((x,y),fill='#344653')
    back.alpha_composite(family_icon('resolve',48,GOLD),(40,66))
    back.save(out/'frames/card_back.png')
    ui=ui_sprites(catalog)
    ui['card_back_small']=back.resize((40,60),Image.Resampling.NEAREST)
    for card in catalog['cards']:
        hand_previews[card['id']]=hand_tile(arts[card['id']],card,catalog)
        hand_previews[card['id']].save(out/'cards'/f'hand_{card["id"]}.png')
        obsolete=out/'ui'/f'hand_{card["id"]}.png'
        if obsolete.exists(): obsolete.unlink()
        ui['thumb_'+card['id']]=ImageOps.fit(arts[card['id']],(22,22),Image.Resampling.NEAREST)
    for key,im in ui.items(): im.save(out/'ui'/f'{key}.png')
    effects=vfx_sprites()
    for key,im in effects.items(): im.save(out/'vfx'/f'{key}.png')
    atlases={}
    for name,sprites in [('cards_base',bases),('ui',ui),('vfx',effects)]:
        packed,rects=atlas(sprites,512)
        packed.save(out/'runtime'/f'{name}.png')
        atlases[name]={'file':f'runtime/{name}.png','size':list(packed.size),'rgba_bytes':packed.width*packed.height*4,'sprites':rects}
    decoded=sum(a['rgba_bytes'] for a in atlases.values())
    if decoded>4*1024*1024:
        raise ValueError(f'Runtime atlas budget exceeded: {decoded}')
    manifest={'kit_version':'0.1','mode_implemented':False,'native_card_size':[128,192],
              'runtime_rgba_bytes':decoded,'runtime_load_only':list(atlases),
              'atlases':atlases,'source_sheet_sha256':hashes,
              'animations':{'focus':{'atlas':'ui','frames':[f'focus_{i}' for i in range(6)],'ticks_per_frame':2,'loop':True},
                            'time_ring':{'atlas':'vfx','frames':[f'time_ring_{i}' for i in range(6)],'ticks_per_frame':3,'loop':True},
                            'draw_spark':{'atlas':'vfx','frames':[f'draw_spark_{i}' for i in range(6)],'ticks_per_frame':2,'loop':False},
                            'reveal_edge':{'atlas':'vfx','frames':[f'reveal_edge_{i}' for i in range(6)],'ticks_per_frame':2,'loop':False}},
              'audio_cues':['focus','draw','commit','blocked','expiry','legendary_reveal'],
              'audio_files_included':False,
              'note':'Runtime base faces have no rules/title text. Authoring previews and templates must not also be loaded into runtime.'}
    (out/'data/assets.json').write_text(json.dumps(manifest,indent=2))
    shutil.copy2(ROOT/'tools/legends/catalog.json',out/'data/catalog.json')
    shutil.copy2(ROOT/'tools/legends/art_sources.json',out/'data/art_sources.json')
    sheet=contact_sheet(faces,catalog)
    sheet.resize((sheet.width*2,sheet.height*2),Image.Resampling.NEAREST).save(out/'previews/CARDS-PREVIEW.png')
    compare=Image.new('RGBA',(592,238),NAVY)
    label(compare,(16,10),'RARITY TREATMENT / VISUAL TEMPLATE COMPARISON',9,bold=True)
    za=next(c for c in catalog['cards'] if c['id']=='za_warudo')
    for i,rarity in enumerate(catalog['rarities']):
        variant=dict(za,rarity=rarity)
        img=card_face(card_base(arts['za_warudo'],'plot_twists',rarity,catalog),variant,catalog)
        compare.alpha_composite(img,(16+i*144,30))
        label(compare,(16+i*144,225),rarity.upper(),8,MUTED)
    compare.resize((1184,476),Image.Resampling.NEAREST).save(out/'previews/RARITY-COMPARISON.png')
    # Transparent overlay and clearly labelled layout concept; not engine footage.
    overlay=Image.new('RGBA',(320,240))
    for i,key in enumerate(['squad_active','squad_reserve','squad_reserve']):
        overlay.alpha_composite(ui[key],(8+i*40,8))
    for i,key in enumerate(['squad_active','squad_reserve','squad_ko']):
        overlay.alpha_composite(ui[key],(194+i*40,8))
    overlay.alpha_composite(ui['resolve_socket'],(8,37))
    overlay.alpha_composite(ui['hype_track'],(85,199))
    overlay.alpha_composite(ui['hype_fill'].crop((0,0,95,1)),(87,201))
    sample=['my_ninja_way','spirit_gun','za_warudo']
    for i,key in enumerate(sample):
        x=14+i*103
        overlay.alpha_composite(hand_previews[key],(x,207))
        overlay.alpha_composite(ui['button_'+['square','triangle','circle'][i]],(x+70,220))
    overlay.save(out/'ui/hud_overlay.png')
    concept=Image.new('RGBA',(320,240),NAVY)
    cd=ImageDraw.Draw(concept)
    cd.rectangle((0,65,319,190),fill='#192936')
    label(concept,(67,103),'COMBAT AREA',14,bold=True)
    label(concept,(45,125),'LAYOUT ONLY / NOT ENGINE FOOTAGE',8,MUTED)
    concept.alpha_composite(overlay)
    concept.resize((960,720),Image.Resampling.NEAREST).save(out/'previews/HUD-LAYOUT.png')
    # UI inventory review is not a runtime atlas.
    x,y,row=16,55,0
    positions={}
    for key,img in ui.items():
        w=max(img.width,110)
        if x+w+16>720: x,y,row=16,y+row+24,0
        positions[key]=(x,y)
        x+=w+14
        row=max(row,img.height+12)
    review=Image.new('RGBA',(720,y+row+24),NAVY)
    label(review,(16,12),'LEGENDS / UI COMPONENTS',18,bold=True)
    for key,img in ui.items():
        x,y=positions[key]
        review.alpha_composite(img,(x,y))
        label(review,(x,y+img.height+3),key[:22],7,MUTED)
    review.save(out/'previews/UI-COMPONENTS.png')
    reveal=[]
    for i in range(18):
        canvas=Image.new('RGBA',(176,224),NAVY)
        y=16+max(0,8-i)*3
        card=faces['za_warudo'].copy()
        if i>=5:
            shine=Image.new('RGBA',card.size)
            sd=ImageDraw.Draw(shine)
            x=-50+(i-5)*18
            sd.polygon([(x,0),(x+8,0),(x+70,192),(x+62,192)],fill=(255,235,185,50))
            card.alpha_composite(shine)
        canvas.alpha_composite(card,(24,y))
        reveal.append(canvas.convert('RGB').resize((352,448),Image.Resampling.NEAREST))
    reveal[0].save(out/'previews/LEGENDARY-REVEAL.gif',save_all=True,append_images=reveal[1:],duration=85,loop=0)
    (out/'README.md').write_text('# Legends art kit v0.1\n\n'
      'Original Higgsfield illustrations plus original code-authored UI sprites. '
      'This kit does not implement the mode.\n\n'
      '- `cards/`: composed review cards with text; not dynamic battle UI.\n'
      '- `illustrations/`, `frames/`: standalone authoring layers.\n'
      '- `runtime/`: load only these three atlas pages; overlay labels at runtime.\n'
      '- `data/assets.json`: exact sprite rectangles, animation references and memory.\n'
      '- `data/catalog.json`: starter card rules and capability requirements.\n'
      '- `ui/`, `vfx/`: individually exported primitives; do not load alongside equivalent atlases.\n'
      '- `previews/`: presentation sheets and a labelled HUD layout concept.\n\n'
      f'Runtime atlas RGBA pixels: {decoded:,} bytes ({decoded/2**20:.2f} MiB). '
      'This excludes native texture padding/mips, fonts and engine overhead; measure Vita uploads.\n\n'
      'No finished audio files or game-engine effect implementation are included. '
      'Full art is assigned to Legendary; rarity template comparisons do not create extra gameplay variants.\n\n'
      'The delivered archive also includes source-sheets/, docs/, reports/ and the original tools. '
      'From that archive root, rebuild with `python tools/build_legends_kit.py --source source-sheets --out rebuilt-kit`. '
      'Requires Pillow and the documented system font fallback. Rebuilds may differ across font versions.\n\n'
      'For game integration, import only the runtime pages and relevant data; keep review sheets and authoring layers out of runtime.\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--source',type=Path,default=ROOT/'source/legends-art')
    p.add_argument('--fetch',action='store_true')
    a=p.parse_args()
    result=render(a.out.resolve(),a.source.resolve(),a.fetch)
    print(json.dumps({'runtime_rgba_bytes':result['runtime_rgba_bytes'],
                      'atlases':{k:v['size'] for k,v in result['atlases'].items()},
                      'source_sha256':result['source_sheet_sha256']},indent=2))


if __name__=='__main__': main()
