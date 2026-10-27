"""Windows visual smoke for the native arcade preview, independent of roster.json.

python tools/verify_arcade.py --seconds 75
python tools/verify_arcade.py --interactive --seconds 180

Interactive mode holds the title for manual navigation. Captures only this
process's game window. Always restores active motif and selection after testing.
"""
import argparse
import csv
from pathlib import Path
import subprocess
import time

import psutil
import arcade_motif
import soak_test

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--seconds',type=int,default=75)
    ap.add_argument('--interactive',action='store_true')
    ap.add_argument('--fighter',default='pupa/Pupa.def')
    args=ap.parse_args()
    game=ROOT/'build/arcade-preview'
    system=game/'assets/data/arcade/system.def'
    select=game/'assets/data/select.def'
    original,original_select=arcade_motif.read(system),arcade_motif.read(select)
    label='interactive' if args.interactive else Path(args.fighter).stem.lower()
    out=ROOT/'reports/arcade-smoke'/label
    out.mkdir(parents=True,exist_ok=True)
    process=None
    captures,errors,peak=[],[],0
    try:
        if not args.interactive:
            entries=[line for line in original_select.splitlines() if line.split(',')[0].strip()==args.fighter]
            if len(entries)!=1:
                raise ValueError(f'Expected one fixture entry for {args.fighter}')
            arcade_motif.write(select,'[Characters]\n'+entries[0]+'\n[Options]\narcade.maxmatches = 1,0,0,0,0,0,0,0,0,0\n')
            demo={'enabled':1,'select.enabled':0,'vsscreen.enabled':1,'title.waittime':180,
                  'fight.endtime':3600,'fight.playbgm':0,'fight.bars.display':1,'intro.waitcycles':99}
            arcade_motif.write(system,arcade_motif.patch(original,'Demo Mode',demo))
        process=subprocess.Popen([str(game/'Dolmexica Infinite for Windows.exe')],cwd=game)
        print(f'PID {process.pid}; {label}',flush=True)
        proc=psutil.Process(process.pid)
        start=time.monotonic()
        due=2
        while time.monotonic()-start<args.seconds and process.poll() is None:
            peak=max(peak,proc.memory_info().rss)
            elapsed=time.monotonic()-start
            if elapsed>=due:
                path=out/f'{int(elapsed):03d}s.png'
                if soak_test.shot(process.pid,str(path)):
                    captures.append(path.name)
                    if soak_test.is_error_screen(str(path)):
                        errors.append(path.name)
                print(f'{int(elapsed)}s alive; {len(captures)} captures',flush=True)
                due+=4 if args.interactive else 10
            time.sleep(.25)
        alive=process.poll() is None
        result={'fixture':label,'seconds':round(time.monotonic()-start),'process_alive':alive,
                'peak_mb':round(peak/2**20),'captures':len(captures),'error_screens':';'.join(errors),
                'vita_tested':False,'full_roster_tested':False}
        with (out/'result.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=result)
            w.writeheader()
            w.writerow(result)
        print(result,flush=True)
        if not alive or not captures or errors:
            raise SystemExit('Smoke failed; inspect the window captures.')
    finally:
        if process and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        arcade_motif.write(system,original)
        arcade_motif.write(select,original_select)


if __name__=='__main__':
    main()
