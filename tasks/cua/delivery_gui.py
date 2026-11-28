from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,time
ROOT=Path(__file__).resolve().parent

def smoke(task):
    directory=ROOT/task
    evidence=ROOT/'delivery-audit-20261128'/task/'gui-smoke'
    evidence.mkdir(exist_ok=True)
    def command(args,name,timeout=120):
        p=subprocess.run(list(map(str,args)),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
        (evidence/(name+'.log')).write_bytes(p.stdout)
        print(task,name,p.returncode,flush=True)
        return p
    p=command(['python3',directory/'run.py','start','--out',evidence/'output'],'start')
    if p.returncode: return
    name='delivery-'+task
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        p=command(['docker','exec',name,'xdotool','search','--onlyvisible','--class','blender'],'window')
        if p.returncode==0: break
        time.sleep(2)
    time.sleep(4)
    command(['docker','exec',name,'scrot','/tmp/gui-initial.png'],'screenshot')
    command(['docker','cp',name+':/tmp/gui-initial.png',evidence/'initial.png'],'collect-screenshot')
    command(['docker','exec',name,'bash','-c','test -s /app/materials/LICENSE.txt && test -z "$(ls -A /app/out)" && test ! -e /tests && test ! -e /solution && blender --version'],'isolation')
    command(['docker','image','inspect',f'delivery-{task}-env:20261128'],'image')

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(smoke,['banner-stand','drawer-cabinet']))
