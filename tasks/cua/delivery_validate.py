"""Run independent Docker validation and retain exact current-source evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess, json, hashlib, datetime, shutil

ROOT=Path(__file__).resolve().parent
AUDIT=ROOT/'delivery-audit-20261128'

def run(args,path,timeout=3700):
    path.parent.mkdir(parents=True,exist_ok=True)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with path.open('w') as log:
        try:
            rc=subprocess.run(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            rc=124
    (path.with_suffix('.command.json')).write_text(json.dumps({'argv':list(map(str,args)),'exit_code':rc,'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()},indent=2))
    print(path.name,rc,flush=True)
    if rc not in (0,1): print(path.read_text()[-1500:],flush=True)
    return rc

def validate(task):
    directory=ROOT/task; evidence=AUDIT/task/'validation-final';evidence.mkdir(exist_ok=True)
    frozen=evidence/'grader-source'
    shutil.copytree(directory/'tests',frozen,ignore=shutil.ignore_patterns('__pycache__'))
    hashes={str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file() and (p.parent.name=='tests' or p.name in ('instruction.md','run.py','task.toml'))}
    (evidence/'source-hashes.json').write_text(json.dumps(hashes,indent=2))
    for suffix,context in [('env',directory/'environment'),('tests',frozen)]:
        tag=f'delivery-{task}-{suffix}:20261128'
        rc=run(['docker','build','-t',tag,context],evidence/f'build-{suffix}.log',2400)
        if rc: return
    # Check the actual Blender report before committing to rendering.
    rc=run(['docker','run','--rm','--network','none','--entrypoint','blender',
            '-v',f'{directory}/tests:/tests:ro','-v',f'{directory}/solution:/solution:ro',
            '-v',f'{evidence}:/evidence',f'delivery-{task}-tests:20261128',
            '--disable-autoexec','--python-exit-code','2','-b',f'/solution/{"banner_stand" if task=="banner-stand" else "drawer_cabinet"}.blend',
            '-P','/tests/check_scene.py','--','/evidence/oracle-scene.json'],evidence/'scene-check.log')
    if rc: return
    for mode in ['oracle','nop']:
        rc=run(['python3',directory/'run.py',mode,'--out',evidence/f'{mode}-submission','--logs',evidence/mode],evidence/f'{mode}.log')
        if rc: print((evidence/f'{mode}.log').read_text()[-5000:],flush=True)
    for submission in sorted((directory/'authoring/runs').glob('*-mutation-*/submission')):
        name=submission.parent.name.split('-mutation-',1)[1]
        run(['python3',directory/'run.py','grade','--out',submission,'--logs',evidence/('negative-'+name)],evidence/f'negative-{name}.log')
    if task=='drawer-cabinet':
        run(['python3',directory/'run.py','grade','--out',AUDIT/'static-door','--logs',evidence/'negative-static-door'],evidence/'negative-static-door.log')

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(validate,['banner-stand','drawer-cabinet']))
