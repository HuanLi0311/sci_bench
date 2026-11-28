from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,sys,time
ROOT=Path(__file__).resolve().parent

def act(task):
    directory=ROOT/'delivery-audit-20261128'/task/'gui-smoke'
    name='delivery-'+task
    actions=[]
    def command(args):
        actions.append(list(map(str,args)))
        return subprocess.run(list(map(str,args)),capture_output=True,timeout=90,check=True)
    def key(*keys): command(['docker','exec',name,'xdotool','key','--clearmodifiers',*keys])
    def type_text(value): command(['docker','exec',name,'xdotool','type','--clearmodifiers','--delay','80',value])
    stage=sys.argv[1]
    if stage=='edit':
        command(['docker','exec',name,'xdotool','mousemove','800','520'])
        key('g','x');type_text('1');key('Return')
        time.sleep(1)
        key('F3');type_text('Save As');key('Return')
        time.sleep(3)
    elif stage=='path':
        # File browser address and filename fields observed in dialog.png.
        command(['docker','exec',name,'xdotool','mousemove','950','295','click','1'])
        key('ctrl+a');type_text('/app/out/');key('Return')
        time.sleep(1)
        command(['docker','exec',name,'xdotool','mousemove','925','886','click','1'])
        key('ctrl+a');type_text('gui_smoke.blend')
        command(['docker','exec',name,'xdotool','mousemove','1416','886','click','1'])
        time.sleep(3)
    elif stage=='confirm':
        key('Return');time.sleep(2)
    elif stage=='reopen':
        command(['docker','exec',name,'xdotool','mousemove','800','520'])
        key('F3');type_text('Revert');key('Return');time.sleep(1);key('Return');time.sleep(5)
    command(['docker','exec',name,'scrot','/tmp/gui-'+stage+'.png'])
    command(['docker','cp',name+':/tmp/gui-'+stage+'.png',directory/(stage+'.png')])
    (directory/(stage+'-actions.json')).write_text(json.dumps(actions,indent=2))

with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(act,['banner-stand','drawer-cabinet']))
