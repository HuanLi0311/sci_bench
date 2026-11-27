"""Direct-Docker sanity for README questions 3 and 4, without model inference.

Run inside WSL: python3 tasks/cua/tools/sanity_animation_web3d.py pose-repair
Images must first be built as sci-{fight,pose}-{env,tests}:dev and
sci-pose-service:dev. This does not claim a Harbor scheduler trial.
"""
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys,time,uuid
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def digest(root):
    return {p.relative_to(root).as_posix():dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.blend1','.inspect.ndjson','.pyc'))}
def run_task(name):
    task=ROOT/name;kind='pose' if name=='pose-repair' else 'fight';stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');tag='sci-'+kind
    root=task/'authoring/runs';root.mkdir(exist_ok=True,parents=True)
    sequence=['oracle','nop','zero-controls','nan-controls','boolean-controls','duplicate-json','wrong-case','over-budget','private-route','fixture-corrupt'] if kind=='pose' else ['oracle','nop','render-substitution','malformed-image','floating-feet','static-action','camera-away','fixture-corrupt','metrics-omitted']
    good=None
    summary=[]
    for probe in sequence:
        trial=root/f'{stamp}-final-{probe}';trial.mkdir();out=trial/'submission';out.mkdir();logs=trial/'verifier';logs.mkdir();evidence=trial/'service-evidence';evidence.mkdir()
        commands=[]
        def command(argv,label,allow_failure=False):
            start=time.monotonic();r=subprocess.run([str(x) for x in argv],capture_output=True,text=True,timeout=1850)
            commands.append(dict(argv=[str(x) for x in argv],exit_code=r.returncode,seconds=time.monotonic()-start,stdout=label+'.stdout.txt',stderr=label+'.stderr.txt'))
            (trial/(label+'.stdout.txt')).write_text(r.stdout);(trial/(label+'.stderr.txt')).write_text(r.stderr)
            if r.returncode and not allow_failure:raise RuntimeError(f'{label} failed: {r.stderr[-600:]}')
            return r
        network=tag+'-'+uuid.uuid4().hex[:10];server=None
        try:
            if kind=='pose' and probe in ['oracle','nop','over-budget','private-route']:
                command(['docker','network','create','--internal',network],'network')
                server=network+'-service'
                command(['docker','run','-d','--name',server,'--network',network,'--network-alias','pose-service','sci-pose-service:dev'],'service')
            if probe=='oracle':
                command(['docker','run','--rm','--cpus','4','--memory','8g','--network',network if kind=='pose' else 'none','-v',str(task/'solution')+':/solution:ro','-v',str(out)+':/app/out',tag+'-env:dev','bash','/solution/solve.sh'],'agent')
                good=out
            elif probe=='nop':
                command(['docker','run','--rm','--network',network if kind=='pose' else 'none','-v',str(out)+':/app/out',tag+'-env:dev','/bin/true'],'agent')
            else:
                shutil.copytree(good,out,dirs_exist_ok=True)
                if kind=='pose':
                    if probe in ['zero-controls','nan-controls','boolean-controls','wrong-case']:
                        v=[0]*24 if probe=='zero-controls' else json.loads((out/'controls_case_a.json').read_text())
                        if probe=='nan-controls':v[3]=float('nan')
                        if probe=='boolean-controls':v[3]=True
                        (out/'controls_case_c.json').write_text(json.dumps(v))
                    elif probe=='duplicate-json':(out/'query_counts.json').write_text('{"a":105,"a":105,"b":105,"c":105}')
                    elif probe in ['over-budget','private-route']:
                        script="const c=require('/app/materials/client.cjs');(async()=>{for(let i=0;i<1201;i++)try{await c.query('a',Array(24).fill(0))}catch(e){}})();" if probe=='over-budget' else "require('http').get('http://pose-service:8090/private/fixture.json',r=>{r.resume();r.on('end',()=>process.exit(r.statusCode===403?0:1))})"
                        command(['docker','run','--rm','--network',network,tag+'-env:dev','node','-e',script],'negative-query')
                else:
                    script={
                        'floating-feet':"bpy.data.objects['rig_left'].location.z+=.05",
                        'static-action':"bpy.data.objects['rig_left'].animation_data_clear()",
                        'camera-away':"bpy.data.objects['cam_fixed'].rotation_euler=(0,0,0)",
                    }.get(probe)
                    if probe=='render-substitution':shutil.copyfile(out/'render_key_01.png',out/'render_key_02.png')
                    elif probe=='malformed-image':(out/'render_key_01.png').write_bytes(b'not an image')
                    elif script:
                        code="import bpy; "+script+"; bpy.ops.wm.save_as_mainfile(filepath='/app/out/fight.blend')"
                        command(['docker','run','--rm','--network','none','--cpus','4','--memory','8g','-v',str(out)+':/app/out',tag+'-tests:dev','blender','--disable-autoexec','-b','/app/out/fight.blend','--python-expr',code],'mutation')
                command(['docker','run','--rm','--network','none',tag+'-env:dev','/bin/true'],'agent')
            if kind=='pose':
                if server:command(['docker','cp',server+':/service-evidence/.',str(evidence)],'collect-service')
                else:shutil.copytree(root/f'{stamp}-final-oracle/service-evidence',evidence,dirs_exist_ok=True)
                if not (evidence/'ledger.jsonl').exists():raise RuntimeError('missing trusted ledger')
            argv=['docker','run','--rm','--network','none','--cpus','4','--memory','8g','--pids-limit','256','-v',str(out)+':/app/out:ro','-v',str(logs)+':/logs/verifier']
            if kind=='pose':argv+=['-v',str(evidence)+':/service-evidence:ro']
            argv+=[tag+'-tests:dev']
            if probe=='fixture-corrupt':argv+=['bash','-c',f"echo invalid > /tests/{'fixture' if kind=='pose' else 'spec'}.json; echo 1 > /logs/verifier/reward.txt; exec bash /tests/test.sh"]
            elif probe=='metrics-omitted':argv+=['bash','-c',"echo pass > /tests/check_scene.py; echo 1 > /logs/verifier/reward.txt; exec bash /tests/test.sh"]
            else:argv+=['bash','/tests/test.sh']
            r=command(argv,'verifier',allow_failure=probe in ['fixture-corrupt','metrics-omitted'])
            if probe in ['fixture-corrupt','metrics-omitted']:
                assert r.returncode!=0 and not (logs/'reward.txt').exists(),'infrastructure failure became reward'
                reward=None
            else:
                metrics=json.loads((logs/'metrics.json').read_text());reward=int((logs/'reward.txt').read_text())
                assert reward==metrics['reward']==(1 if probe=='oracle' else 0),(probe,metrics)
                if probe=='oracle':assert all(c['pass'] for c in metrics['checks'])
            meta=dict(task=name,kind=probe,validation='direct Docker; artifact replay' if kind=='fight' and probe=='oracle' else 'direct Docker',reward=reward,verifier_exit_code=r.returncode,agent_exit_code=0,model_steps=0,gui_compliant=None,commands=commands,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),grader_source=digest(task/'tests'),solution_source=digest(task/'solution'),submission=digest(out),images={role:json.loads(subprocess.check_output(['docker','image','inspect',tag+'-'+role+':dev']))[0]['Id'] for role in ['env','tests']})
            snapshot=trial/'grader-source';shutil.copytree(task/'tests',snapshot,ignore=shutil.ignore_patterns('__pycache__'))
            (trial/'run.json').write_text(json.dumps(meta,indent=2));summary.append(dict(probe=probe,reward=reward,exit_code=r.returncode,evidence=trial.relative_to(task).as_posix()))
            print(name,probe,reward,r.returncode,flush=True)
        finally:
            if server:
                subprocess.run(['docker','rm','-f',server],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                subprocess.run(['docker','network','rm',network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    (task/'authoring/calibration/sanity.json').write_text(json.dumps(summary,indent=2))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('task',choices=['fight-retarget','pose-repair']);args=ap.parse_args();run_task(args.task)
