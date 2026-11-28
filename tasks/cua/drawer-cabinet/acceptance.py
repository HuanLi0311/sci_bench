"""Delivery regression suite: real containers, no test framework. Linux/WSL2."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import run as runtime


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs',type=Path,default=ROOT/'acceptance-logs')
    parser.add_argument('--security-only',action='store_true')
    args=parser.parse_args()
    logs=args.logs.resolve();logs.mkdir(parents=True,exist_ok=True)
    if (logs/'results.json').exists():
        raise SystemExit('Choose a new --logs directory to preserve prior evidence')
    results=[]

    def record(case,cmd,expected):
        directory=logs/case;directory.mkdir(exist_ok=True)
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (directory/'runner.log').open('w') as stream:
            p=subprocess.run(cmd,stdout=stream,stderr=subprocess.STDOUT,timeout=3700)
        metrics=directory/'verifier/metrics.json'
        data=json.loads(metrics.read_text()) if metrics.exists() else {}
        passed=data.get('reward') == expected and p.returncode == (0 if expected == 1 or case=='nop' else 1)
        results.append({'case':case,'expected_reward':expected,'reward':data.get('reward'),
                        'exit_code':p.returncode,'pass':passed,'started_utc':start,
                        'failed_checks':[c['id'] for c in data.get('checks',[]) if not c['pass']],
                        'argv':list(map(str,cmd))})
        (logs/'results.json').write_text(json.dumps(results,indent=2))
        print(case,'PASS' if passed else 'FAIL',flush=True)

    if not args.security_only:
        for mode in ['oracle','nop']:
            record(mode,[sys.executable,ROOT/'run.py',mode,'--out',logs/mode/'submission','--logs',logs/mode/'verifier'],1 if mode=='oracle' else 0)
        record('oracle-repeat',[sys.executable,ROOT/'run.py','grade','--out',logs/'oracle/submission','--logs',logs/'oracle-repeat/verifier'],1)
    banner=ROOT.name=='banner-stand'
    cases=['unused-materials','hidden-part']+(['uv-tiling'] if banner else ['static-door','coupled-slides'])
    blend='banner_stand.blend' if banner else 'drawer_cabinet.blend'
    for case in cases+['manifest-omission','corrupt-render']:
        directory=logs/case;directory.mkdir(exist_ok=True)
        out=directory/'submission'
        shutil.copytree(ROOT/'solution',out,ignore=shutil.ignore_patterns('*.blend1'))
        if case=='manifest-omission':
            path=out/'manifest.json';man=json.loads(path.read_text());man['assets'][0]['path']='textures/unrelated.png'
            path.write_text(json.dumps(man))
        elif case=='corrupt-render':
            (out/next(iter(runtime.RENDERS if hasattr(runtime,'RENDERS') else {'render_front.png' if banner else 'render_day.png':None}))).write_bytes(b'not a png')
        else:
            with (directory/'mutation.log').open('w') as stream:
                subprocess.run(['docker','run','--rm','--network','none','--entrypoint','blender',
                                '--mount',f'type=bind,src={out},dst=/submission',
                                '--mount',f'type=bind,src={ROOT/"authoring/make_negative.py"},dst=/mutation.py,readonly',
                                runtime.TESTS,'--disable-autoexec','--python-exit-code','2','-b',f'/submission/{blend}',
                                '-P','/mutation.py','--',case,f'/submission/{blend}'],stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=120)
        record(case,[sys.executable,ROOT/'run.py','grade','--out',out,'--logs',directory/'verifier'],0)
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT/'tests').iterdir() if p.is_file()}
    (logs/'grader-hashes.json').write_text(json.dumps(hashes,indent=2))
    return 0 if all(r['pass'] for r in results) else 1


if __name__=='__main__':
    sys.exit(main())
