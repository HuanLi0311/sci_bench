import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import time
import resource
import socket
import struct
import numpy as np
from kinematics import replay, errors

class CandidateError(Exception): pass
def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise ValueError('duplicate key')
        result[k]=v
    return result
def read(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size>8_000_000: raise CandidateError('missing, symlink or oversized: '+str(path))
    try: return json.loads(path.read_text(),object_pairs_hook=unique,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    except (ValueError,UnicodeError) as e: raise CandidateError('malformed JSON: '+str(path)) from e
def reproduction(out,p):
    """Execute submitted code with no access to trusted fixtures or other users."""
    base=Path(tempfile.mkdtemp(prefix='pose-repro-',dir='/tmp'));base.chmod(0o755)
    src=base/'solution';src.mkdir();dest=base/'out';dest.mkdir();dest.chmod(0o777)
    files=list((out/'solution').rglob('*'))
    if len(files)>64:raise CandidateError('solution file count >64')
    for file in files:
        if file.is_symlink():raise CandidateError('solution symlink')
        if file.is_file():
            if file.stat().st_size>2_000_000:raise CandidateError('solution file >2 MB')
            rel=file.relative_to(out/'solution');target=src/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target);target.chmod(0o444)
    fresh=base/'evidence';fresh.mkdir()
    env={**os.environ,'EVIDENCE_DIR':str(fresh),'PORT':'8091'}
    server=subprocess.Popen(['node','/tests/service/server.cjs'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for _ in range(100):
            if server.poll() is not None:raise RuntimeError('replay service failed')
            try:
                with socket.create_connection(('127.0.0.1',8091),timeout=.1):break
            except OSError:time.sleep(.05)
        else:raise RuntimeError('replay service startup timed out')
        def limit():
            os.setgroups([]);os.setgid(65534);os.setuid(65534)
            resource.setrlimit(resource.RLIMIT_CPU,(90,90));resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3));resource.setrlimit(resource.RLIMIT_NOFILE,(64,64));resource.setrlimit(resource.RLIMIT_NPROC,(64,64))
        r=subprocess.run(['node',str(src/'fitter.cjs'),str(dest)],cwd=src,env={'PATH':'/usr/bin:/bin','POSE_SERVICE':'http://127.0.0.1:8091','HOME':str(dest)},preexec_fn=limit,capture_output=True,timeout=120)
        passed=r.returncode==0
        results={}
        for k in 'abc':
            v=read(dest/f'controls_case_{k}.json')
            valid=type(v) is list and len(v)==24 and all(type(x) in (int,float) and math.isfinite(x) and -1<=x<=1 for x in v)
            if not valid:return False,{'error':'invalid reproduced controls'}
            e=errors(p,v,p['targets'][k]);results[k]=e;passed &= e[0]<=.02 and e[1]<=5
        rows=[json.loads(x) for x in (fresh/'ledger.jsonl').read_text().splitlines()]
        passed &= not any(x['kind']=='denied' for x in rows)
        passed &= all(sum(x.get('case')==k for x in rows)<=1200 for k in 'abc')
        return passed,results
    except (CandidateError,subprocess.TimeoutExpired) as e:return False,{'error':str(e)}
    finally:
        server.terminate();server.wait(timeout=10)
def main():
    # Fixture corruption is infrastructure failure, outside candidate handling.
    p=json.loads(Path('/tests/fixture.json').read_text())
    assert len(p['matrix'])==24 and all(len(r)==24 for r in p['matrix'])
    assert np.linalg.cond(np.array(p['matrix']))<10
    glb=Path('/original/avatar.glb').read_bytes()
    assert struct.unpack_from('<I',glb)[0]==0x46546c67
    doc=json.loads(glb[20:20+struct.unpack_from('<I',glb,12)[0]])
    assert doc['skins'][0]['joints']==list(range(8))
    parents=[-1]*8
    for i,node in enumerate(doc['nodes'][:8]):
        for child in node.get('children',[]):parents[child]=i
        assert node['translation']==(p['offsets'][i] if i else [0,0,.9])
    assert parents==p['parents']
    for k in 'abc': assert errors(p,p['targets'][k],p['targets'][k])==(0.,0.) or errors(p,p['targets'][k],p['targets'][k])[1]<1e-5
    ledger=Path('/service-evidence/ledger.jsonl')
    if not ledger.is_file(): raise RuntimeError('trusted service ledger absent')
    rows=[json.loads(x) for x in ledger.read_text().splitlines()]
    counts={k:sum(r.get('kind')=='query' and r.get('case')==k for r in rows) for k in 'abc'}
    for k in 'abc':
        seq=[r['index'] for r in rows if r.get('kind')=='query' and r.get('case')==k]
        if seq!=list(range(1,len(seq)+1)): raise RuntimeError('trusted ledger inconsistent')
    checks=[]
    def check(cid,level,ok,detail=''):
        checks.append(dict(id=cid,level=level,pass_=bool(ok),detail=detail))
    out=Path(sys.argv[1] if len(sys.argv)>1 else '/app/out')
    try:
        u={k:read(out/f'controls_case_{k}.json') for k in 'abc'}
        replay_config=read(out/'replay.json'); reported=read(out/'query_counts.json')
        if (out/'report.md').is_symlink():raise CandidateError('report symlink')
        report=(out/'report.md').read_text()
        if not report.strip(): raise CandidateError('empty report')
        check('R01','must', (out/'solution/fitter.cjs').is_file() and type(replay_config.get('schemaVersion')) is int and replay_config==dict(schemaVersion=1,scene='avatar.glb',cases=[f'controls_case_{k}.json' for k in 'abc']))
        valid=all(type(v) is list and len(v)==24 and all(type(x) in (int,float) and math.isfinite(x) and -1<=x<=1 for x in v) for v in u.values())
        check('R02','must',valid)
        if not valid: raise CandidateError('24 finite bounded real controls required')
        check('R03','must',all(counts[k]<=1200 for k in 'abc'),counts)
        pe={k:errors(p,u[k],p['targets'][k]) for k in 'abc'}
        check('R04','must',all(e[0]<=.02 for e in pe.values()),pe)
        check('R05','must',all(e[1]<=5 for e in pe.values()),pe)
        lengths=[]
        for k in 'abc':
            pos,rot=replay(p,u[k])
            lengths.extend(abs(np.linalg.norm(pos[i]-pos[parent])-np.linalg.norm(p['offsets'][i])) for i,parent in enumerate(p['parents']) if parent>=0)
        check('R06','must',max(lengths)<=1e-6)
        expected=json.loads(Path('/tests/public-hashes.json').read_text())
        check('R07','must', all(hashlib.sha256(Path('/original',name).read_bytes()).hexdigest()==h for name,h in expected.items()))
        check('R08','critical',not any(r['kind']=='denied' for r in rows))
        check('R09','critical',all(np.max(np.abs(replay(p,u[k])[0]-replay(p,u[k])[0]))<=1e-4 for k in 'abc'))
        reproduce_ok,details=reproduction(out,p)
        check('R10','critical',reproduce_ok,details)
        check('R11','must',all(e[0]<=.02 and e[1]<=5 for e in pe.values()))
        check('R12','normal',reported==counts and all(type(reported[k]) is int and f'"{k}":{counts[k]}' in report.replace(' ','') for k in 'abc'))
        check('R13','normal',sum(counts.values())/3<=800)
        check('R14','normal', 'node /app/out/solution/fitter.cjs /app/out' in report and reproduce_ok)
    except (CandidateError,FileNotFoundError,UnicodeError,ValueError,TypeError) as e:
        check('submission','must',False,str(e))
    normals=[c for c in checks if c['level']=='normal']
    reward=int(all(c['pass_'] for c in checks if c['level']!='normal') and (not normals or sum(c['pass_'] for c in normals)/len(normals)>=.8))
    result=dict(reward=reward,checks=[{**{k:v for k,v in c.items() if k!='pass_'},'pass':c['pass_']} for c in checks])
    print(json.dumps(result,allow_nan=False))
    return reward
if __name__=='__main__': main()
