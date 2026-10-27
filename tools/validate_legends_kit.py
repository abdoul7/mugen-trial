"""Validate the delivered Legends art/data kit; does not validate gameplay."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import textwrap

from PIL import Image, ImageChops


def validate(root):
    catalog=json.loads((root/'data/catalog.json').read_text())
    assets=json.loads((root/'data/assets.json').read_text())
    cards=catalog['cards']
    assert set(catalog['families'])=={'resolve','secret_arts','awakenings','plot_twists'}
    assert len({c['id'] for c in cards})==len(cards)
    assert sum(x['draw_weight'] for x in catalog['rarities'].values())==100
    assert all(n>0 for n in Counter(c['family'] for c in cards).values())
    required={'id','revision','name','short_name','reference','family','rarity','short_text',
              'rules_text','activation','target','conditions','required_capabilities',
              'reservation_ticks','windup_ticks','interruptible','duration_ticks','effect','limits','art'}
    checks=[]
    for c in cards:
        assert required<=c.keys(),c['id']
        assert c['family'] in catalog['families'] and c['rarity'] in catalog['rarities'],c['id']
        assert c['required_capabilities'] and c['effect']['handler'],c['id']
        assert c['reservation_ticks']>=0 and c['windup_ticks']>=0,c['id']
        assert len(textwrap.wrap(c['short_text'],width=21))<=3,c['id']
        for folder in ['cards','illustrations']:
            im=Image.open(root/folder/(c['id']+'.png'))
            assert im.size==(128,192),(folder,c['id'])
        assert c['id'] in assets['atlases']['cards_base']['sprites'],c['id']
    assert catalog['rarities']['legendary']['art_treatment']=='full_art'
    assert assets['mode_implemented'] is False
    for family in catalog['families']:
        for rarity in catalog['rarities']:
            assert Image.open(root/'frames'/f'{family}_{rarity}.png').size==(128,192)
    checks.append('Card IDs/schema, four families, all rarity templates and all card outputs')
    total=0
    for name,a in assets['atlases'].items():
        im=Image.open(root/a['file']).convert('RGBA')
        assert list(im.size)==a['size'],name
        assert all(n>0 and n&(n-1)==0 for n in im.size),name
        total+=im.width*im.height*4
        rects=[]
        for key,p in a['sprites'].items():
            x,y,w,h=p['x'],p['y'],p['width'],p['height']
            assert x>=1 and y>=1 and x+w<im.width and y+h<im.height,(name,key)
            assert not any(x<xx+ww and x+w>xx and y<yy+hh and y+h>yy for xx,yy,ww,hh in rects),(name,key)
            rects.append((x,y,w,h))
            path=root/name/(key+'.png') if name in ('ui','vfx') else None
            if path and path.exists():
                source=Image.open(path).convert('RGBA')
                assert source.size==(w,h),key
                extracted=im.crop((x,y,x+w,y+h))
                # Compare visible pixels over both dark and light backgrounds.
                for bg in ['black','white']:
                    first=Image.new('RGBA',source.size,bg)
                    second=first.copy()
                    first.alpha_composite(source)
                    second.alpha_composite(extracted)
                    assert ImageChops.difference(first.convert('RGB'),second.convert('RGB')).getbbox() is None,(name,key)
        checks.append(f'{name}: {len(rects)} bounded, non-overlapping sprite regions')
    assert total==assets['runtime_rgba_bytes'] and total<=4*1024*1024,total
    for anim in assets['animations'].values():
        available=assets['atlases'][anim['atlas']]['sprites']
        assert anim['frames'] and all(key in available for key in anim['frames'])
        assert anim['ticks_per_frame']>0
    checks.append('Animation references resolve; runtime atlas RGBA pixels <=4 MiB')
    gif=Image.open(root/'previews/LEGENDARY-REVEAL.gif')
    assert getattr(gif,'n_frames',1)>1
    manifest={str(p.relative_to(root)).replace('\\','/'):
              {'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
              for p in sorted(root.rglob('*')) if p.is_file() and p.name not in ('file-manifest.json','validation.json')}
    (root/'data/file-manifest.json').write_text(json.dumps(manifest,indent=2))
    report={'status':'PASS','cards':len(cards),'families':len(catalog['families']),
            'runtime_rgba_bytes':total,'checks':checks,'native_gameplay_tested':False,
            'vita_texture_uploads_measured':False,'audio_files_included':False}
    (root/'data/validation.json').write_text(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('kit',type=Path)
    args=p.parse_args()
    print(json.dumps(validate(args.kit.resolve()),indent=2))
