"""Direct Docker acceptance; not a Harbor/model run. Run from any task cwd."""
import datetime,hashlib,json,pathlib,shutil,subprocess,tempfile,time,tomllib,os
T=pathlib.Path(__file__).resolve().parents[1]; RUNS=T/'authoring/runs';RUNS.mkdir(exist_ok=True)
ENV='cua-qc-microscope-focus-env';TEST='cua-qc-microscope-focus-tests'
def hashes(root):return {p.relative_to(root).as_posix():{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
def run(argv,timeout=650):
 p=subprocess.run(argv,capture_output=True,text=True,timeout=timeout);return p
def record(kind,source=None,mutate=None,fault=False):
 d=RUNS/('20261127-final-'+kind);d.mkdir(exist_ok=True)
 for folder in ['verifier','submission']:
  p=d/folder
  if p.exists():shutil.rmtree(p)
  p.mkdir()
 commands=[]
 def cmd(argv):
  p=run(argv);commands.append({'argv':argv,'exit_code':p.returncode});return p
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();beg=time.monotonic()
 if source is None:
  name='microscope-agent-'+kind
  cmd(['docker','rm','-f',name])
  argv=['docker','create','--name',name,'--network','none','--cpus','4','--memory','8192m','--pids-limit','512',ENV]
  argv+=['/bin/true'] if kind=='nop' else ['bash','/solution/solve.sh']
  p=cmd(argv);assert p.returncode==0,p.stderr
  if kind!='nop':assert cmd(['docker','cp',str(T/'solution'),name+':/solution']).returncode==0
  p=cmd(['docker','start','-a',name]);agent_exit=p.returncode
  (d/'agent.stdout.txt').write_text(p.stdout+'\n'+p.stderr)
  assert p.returncode==0,p.stderr
  assert cmd(['docker','cp',name+':/app/out/.',str(d/'submission')]).returncode==0
  cmd(['docker','rm',name])
 else:
  shutil.copytree(source,d/'submission',dirs_exist_ok=True);agent_exit=0;(d/'agent.stdout.txt').write_text('Mutation of freshly executed oracle; no model solving.\n')
 if mutate:mutate(d/'submission')
 cdir=d/'grader-source'
 if cdir.exists():shutil.rmtree(cdir)
 shutil.copytree(T/'tests',cdir,ignore=shutil.ignore_patterns('__pycache__'))
 argv=['docker','run','--rm','--network','none','--cpus','4','--memory','8192m','--pids-limit','512','--ulimit','nofile=1024:1024','-v',str(d/'submission')+':/app/out:ro','-v',str(d/'verifier')+':/logs/verifier']
 if fault:
  (d/'verifier/reward.txt').write_text('1\n')  # stale success must be removed
  (d/'bad-truth.json').write_text('{}');argv+=['-v',str(d/'bad-truth.json')+':/tests/fixtures/truth.json:ro']
 argv+=[TEST];p=cmd(argv);(d/'verifier.stdout.txt').write_text(p.stdout+'\n'+p.stderr)
 reward=int((d/'verifier/reward.txt').read_text()) if (d/'verifier/reward.txt').exists() else None
 meta={'kind':kind,'started_at':start,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'backend':'direct Docker, WSL2','agent_exit_code':agent_exit,'verifier_exit_code':p.returncode,'reward':reward,'outcome':'graded' if p.returncode==0 else 'infrastructure-error','model_steps':0,'gui_compliant':None,'submission':hashes(d/'submission'),'grader_source':hashes(T/'tests'),'solution_source':hashes(T/'solution'),'commands':commands,'elapsed_sec':time.monotonic()-beg}
 if kind=='nop':assert meta['submission']=={}
 (d/'run.json').write_text(json.dumps(meta,indent=2));print(kind,'exit',p.returncode,'reward',reward,flush=True)
 if fault:assert p.returncode!=0 and reward is None
 else:
  assert p.returncode==0,p.stderr+(d/'verifier.stdout.txt').read_text()[-2000:]
  assert reward==(1 if kind.startswith('oracle') else 0),str(d)
 return d/'submission'
def edit_json(path,fn):
 v=json.loads(path.read_text());fn(v);path.write_text(json.dumps(v))
def textedit(root,old,new):
 p=root/'microscope/optics.js';s=p.read_text();assert old in s;p.write_text(s.replace(old,new))
def main():
 config=tomllib.loads((T/'task.toml').read_text());assert config['verifier']['environment_mode']=='separate';assert config['artifacts']==['/app/out']
 assert config['environment']['network_mode']==config['verifier']['environment']['network_mode']=='no-network'
 assert (T/'instruction.md').read_text().rstrip().endswith('You have 7200 seconds to complete this task.')
 assert all(b'\r\n' not in p.read_bytes() for p in T.rglob('*.sh'))
 for f in ['environment','tests']:
  assert all(not p.name=='__pycache__' for p in (T/f).rglob('*'))
  with (RUNS/(f+'-build.log')).open('w') as build_log:
   p=subprocess.run(['docker','build','-t',ENV if f=='environment' else TEST,str(T/f)],stdout=build_log,stderr=subprocess.STDOUT,timeout=1800)
  assert p.returncode==0,(RUNS/(f+'-build.log')).read_text()[-2000:]
 ids={tag:json.loads(run(['docker','image','inspect',tag]).stdout)[0] for tag in [ENV,TEST]}
 (RUNS/'image-ids.json').write_text(json.dumps({tag:{k:v[k] for k in ['Id','RepoDigests','Size','Created']} for tag,v in ids.items()},indent=2))
 p=run(['docker','run','--rm','--network','none',ENV,'bash','-lc','test -d /app/materials && test -z "$(ls -A /app/out)" && test ! -e /tests && test ! -e /solution && test ! -e /app/solution']);assert p.returncode==0,p.stderr
 # Actual runtime egress denial and artifact-only verifier isolation.
 p=run(['docker','run','--rm','--network','none',TEST,'python3','-c','import socket,pathlib; assert not pathlib.Path("/solution").exists(); assert not pathlib.Path("/authoring").exists(); s=socket.socket(); s.settimeout(2); result=s.connect_ex(("1.1.1.1",443)); assert result!=0; print("egress blocked",result)']);assert p.returncode==0,p.stderr
 (RUNS/'isolation.log').write_text(p.stdout+p.stderr)
 oracle=record('oracle');record('oracle-repeat');record('nop')
 record('negative-wrong-sign',oracle,lambda r:textedit(r,'m:v/s','m:-v/s'))
 record('negative-static-optics',oracle,lambda r:textedit(r,'const objective=lens(stageY-objectiveY,4);','const objective=lens(-4.12,4);'))
 def frozen(r):
  p=r/'microscope/app.js';s=p.read_text();s=s.replace('stage.position.y+=current.stageOffset;objective.position.y+=current.objectiveOffset;eyepiece.position.y+=current.eyepieceOffset;','stage.position.y+=0;objective.position.y+=0;eyepiece.position.y+=0;');p.write_text(s)
 record('negative-frozen-focus',oracle,frozen)
 def sample(r):
  p=r/'microscope/app.js';s=p.read_text().replace('img.src=url;','img.src="./assets/sample_a.png";');p.write_text(s)
 record('negative-fixed-sample',oracle,sample)
 record('negative-nan',oracle,lambda r:(r/'state.json').write_text((r/'state.json').read_text().replace('"stageOffset": 0,','"stageOffset": NaN,',1)))
 record('negative-bool',oracle,lambda r:edit_json(r/'state.json',lambda s:s['settings'][0].update(stageOffset=True)))
 record('negative-duplicate-key',oracle,lambda r:(r/'state.json').write_text((r/'state.json').read_text().replace('"units": "mm",','"units":"mm","units":"mm",',1)))
 record('negative-wrong-version',oracle,lambda r:edit_json(r/'state.json',lambda s:s.update(schemaVersion=2)))
 def symlink(r):(r/'link').symlink_to('state.json')
 record('negative-symlink',oracle,symlink)
 record('fixture-fault',oracle,fault=True)
 # Map scientific negatives to decisive criteria, not merely any zero reward.
 targets={'wrong-sign':'R05','static-optics':'R13','frozen-focus':'R04','fixed-sample':'R14'}
 for name,id in targets.items():
  m=json.loads((RUNS/('20261127-final-negative-'+name)/'verifier/metrics.json').read_text());assert any(c['id']==id and not c['pass'] for c in m['checks']),(name,id)
 source=hashes(T/'tests');(RUNS/'current-source.json').write_text(json.dumps({'baseline_commit':run(['git','-C',str(T),'rev-parse','HEAD']).stdout.strip(),'tests':source,'solution':hashes(T/'solution'),'task_config':hashes(T)['task.toml'],'mode':'direct Docker cold-start reference, no model inference'},indent=2))
 print('SANITY PASS: two oracles, NOP, nine negatives, trusted fixture fault, isolation.',flush=True)
if __name__=='__main__':main()
