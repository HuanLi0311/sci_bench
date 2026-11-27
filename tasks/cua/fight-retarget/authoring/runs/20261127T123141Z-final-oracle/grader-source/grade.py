import json,sys,subprocess,tempfile,math
from pathlib import Path
import numpy as np
from PIL import Image

class CandidateError(Exception):pass
def run(cmd,timeout=90):
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout)
    with open('/logs/verifier/processes.jsonl','a') as f:f.write(json.dumps(dict(command=cmd,exit_code=r.returncode,stdout=r.stdout[-2000:],stderr=r.stderr[-2000:]))+'\n')
    return r
def ssim(a,b):
    # Windowed per-channel SSIM; gradient separately rejects flat substitutions.
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    def box(x):return x.reshape(90,8,160,8,3).mean(axis=(1,3))
    ma,mb=box(a),box(b);va=box(a*a)-ma*ma;vb=box(b*b)-mb*mb;co=box(a*b)-ma*mb
    score=((2*ma*mb+6.5025)*(2*co+58.5225))/((ma*ma+mb*mb+6.5025)*(va+vb+58.5225))
    return score.mean(axis=(0,1)).tolist()
def image(p,trusted=False):
    try:
        with Image.open(p) as im:
            if im.size!=(1280,720):raise CandidateError('wrong image dimensions')
            return np.asarray(im.convert('RGB'),dtype=float)
    except (OSError,Image.DecompressionBombError) as e:
        if trusted:raise RuntimeError('trusted render unreadable: '+str(p)) from e
        raise CandidateError('submitted image unreadable: '+str(p)) from e
def finite_fields(value):
    if isinstance(value,float) and not math.isfinite(value):raise CandidateError('non-finite evaluated scene state')
    if isinstance(value,dict):
        for v in value.values():finite_fields(v)
    if isinstance(value,list):
        for v in value:finite_fields(v)
def finish(checks):
    normals=[c for c in checks if c['level']=='normal'];reward=int(all(c['pass'] for c in checks if c['level']!='normal') and (not normals or sum(c['pass'] for c in normals)/len(normals)>=.8))
    print(json.dumps(dict(reward=reward,checks=checks),allow_nan=False))
def main():
    # Check trusted code and fixture before considering the candidate.
    spec=json.loads(Path('/tests/spec.json').read_text());assert len(spec['parents'])==22 and len(spec['events'])==4
    r=run(['blender','-b','--factory-startup','--python-expr',"import bpy; assert bpy.app.version[:3]==(4,2,3)"])
    if r.returncode:raise RuntimeError('Blender dependency failed')
    out=Path(sys.argv[1] if len(sys.argv)>1 else '/app/out');checks=[]
    def check(cid,level,ok,detail=''):checks.append(dict(id=cid,level=level,**{'pass':bool(ok)},detail=detail))
    def require(name,size=150_000_000):
        p=out/name
        if p.is_symlink() or not p.is_file() or p.stat().st_size>size:raise CandidateError('missing, symlink or oversized '+name)
        return p
    try:
        blend=require('fight.blend');work=Path(tempfile.mkdtemp(prefix='replay-',dir='/logs/verifier'))
        for i in range(1,5):image(require(f'render_key_{i:02d}.png',20_000_000))
        cmd=['blender','--threads','4','--disable-autoexec','--python-exit-code','2','-b',str(blend),'--python','/tests/check_scene.py','--',str(work)]
        r=run(cmd+['--no-render'],300)
        if r.returncode:raise CandidateError('scene could not be inspected: '+r.stderr[-300:])
        if not (work/'scene.json').is_file():raise RuntimeError('successful trusted extractor omitted scene metrics')
        try:scene=json.loads((work/'scene.json').read_text())
        except ValueError as e:raise RuntimeError('trusted scene metrics malformed') from e
        finite_fields(scene)
        check('R01','must',scene['version'].startswith('4.2.3'))
        rigs=scene['rigs'];check('R02','must',scene['armature_count']==2 and set(rigs)=={'left','right'} and all({n:b['parent'] for n,b in r['bones'].items()}==spec['parents'] for r in rigs.values()))
        required=set(spec['parents'])-{'root','pelvis','clavicle.L','clavicle.R'}
        check('R03','must',scene['range']==[1,300] and scene['fps']==30 and all({w+'_'+n for n in required}<={s['name'] for s in r['skin']} and r['action']=='Fight_'+w.title() and r['action_range']==[1,300] and r['curves']>=22*4 and r['drivers']==0 and all(s['unweighted']==0 and s['max_weights']<=4 and not s['shape_keys'] and s['visible'] and s['vertices']>=8 and s['armatures']==['rig_'+w] for s in r['skin']) for w,r in rigs.items()))
        check('R04','must',all(abs(rigs[w]['height']-h)<=.02 and all(abs(rigs[w]['bones'][n]['length']-v)<=.001 for n,v in spec['lengths'][w].items()) for w,h in [('left',1.7),('right',1.9)]),{w:r['height'] for w,r in rigs.items()})
        roots=[rigs[w]['root'] for w in ['left','right']];check('R05','must',abs(math.dist(*roots)-2.4)<=.05 and rigs['left']['forward'][0]>=math.cos(math.radians(2)) and rigs['right']['forward'][0]<=-math.cos(math.radians(2)))
        timing={};reachable=True
        for e in spec['events']:
            f=e['frame'];dist=[(x['contacts'][str(f)],x['frame']) for x in scene['frames'] if abs(x['frame']-f)<=10];minimum,frame=min(dist)
            timing[str(f)]=dict(frame=frame,distance=minimum)
            reachable &= min(x['contacts'][str(f)] for x in scene['frames'] if abs(x['frame']-f)<=2)<=.03
        check('R06','must',all(abs(timing[str(e['frame'])]['frame']-e['frame'])<=2 for e in spec['events']),timing)
        check('R07','must',reachable)
        bad=[dict(frame=x['frame'],collisions=x['collisions'][:5]) for x in scene['frames'] if x['collisions']]
        check('R08','must',not bad,bad[:12])
        check('R09','normal',max(x['penetration'] for x in scene['frames'])<=.01)
        drift=[];ground=[]
        for w in ['left','right']:
            for side,ranges in spec['supports'].items():
                for lo,hi in ranges:
                    points=[x['feet'][w+'_'+side] for x in scene['frames'] if lo<=x['frame']<=hi]
                    drift.append(max(math.dist(p['center'][:2],points[0]['center'][:2]) for p in points));ground.extend(p['bottom'] for p in points)
        check('R10','normal',max(drift)<=.005,max(drift));check('R11','must',min(ground)>=-.001 and max(ground)<=.002,[min(ground),max(ground)])
        check('R12','must',all(x['bounds_ok'] for x in scene['frames']))
        if any(not c['pass'] for c in checks if c['level']!='normal'):finish(checks);return
        c=scene['camera'];target=np.array([0,0,.9])-np.array(c.get('location',[0,0,0]));target/=np.linalg.norm(target)
        camera_ok=c.get('type')=='ORTHO' and abs(c.get('scale',0)-3.8)<.01 and math.dist(c.get('location',[]),[0,-5.8,2.25])<.01 and np.dot(target,c['direction'])>.999
        if not camera_ok:raise CandidateError('fixed camera contract violated')
        r=run(cmd,1100)
        if r.returncode:raise CandidateError('scene re-render failed: '+r.stderr[-300:])
        expected=['swapped.json','shifted.png']+[f'{prefix}_{i:02d}.png' for prefix in ['render_key','video_key'] for i in range(1,5)]
        if not all((work/f).is_file() for f in expected):raise RuntimeError('successful trusted extractor omitted required metrics/renders')
        image_scores=[];gradients=[]
        for i in range(1,5):
            a=image(require(f'render_key_{i:02d}.png',20_000_000));b=image(work/f'render_key_{i:02d}.png',True)
            if a.shape!=(720,1280,3):raise CandidateError('wrong image shape')
            image_scores.append(ssim(a,b));gradients.append(float(np.mean(np.abs(np.diff(a,axis=0)-np.diff(b,axis=0)))))
        video=require('playblast.mp4');v=run(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,r_frame_rate,nb_read_frames,codec_name,duration','-of','json',str(video)],15)
        info=json.loads(v.stdout)['streams'][0] if v.returncode==0 else {}
        video_scores=[]
        if info.get('width')==1280 and info.get('height')==720:
            for i,f in enumerate(spec['keys'],1):
                dest=work/f'decoded_key_{i:02d}.png'
                r=run(['ffmpeg','-v','error','-i',str(video),'-vf',f'select=eq(n\\,{f-1})','-frames:v','1',str(dest)],20)
                video_scores.append(ssim(image(dest),image(work/f'video_key_{i:02d}.png',True)) if r.returncode==0 and dest.is_file() else [0]*3)
        check('R13','must',all(min(s)>=.94 for s in image_scores) and max(gradients)<3 and camera_ok and len(video_scores)==4 and all(min(s)>=.92 for s in video_scores) and info.get('nb_read_frames')=='300' and info.get('r_frame_rate')=='30/1' and info.get('codec_name')=='h264',dict(ssim=image_scores,gradient=gradients,video=info,video_ssim=video_scores))
        fbxs=[]
        for w in ['left','right']:
            p=require('fight_'+w+'.fbx');dest=work/(w+'.json');r=run(['blender','--threads','4','--disable-autoexec','--python-exit-code','2','-b','--factory-startup','--python','/tests/check_fbx.py','--',str(p),str(dest)],90)
            fbxs.append(json.loads(dest.read_text()) if r.returncode==0 else [])
        check('R14','must',all(len(x)==1 and x[0]['bones']==22 and x[0]['has_animation'] and any(abs(a-1)<.01 and abs(b-300)<.01 for a,b in x[0]['ranges']) for x in fbxs),fbxs)
        shifted=ssim(image(work/'shifted.png',True),image(work/'render_key_02.png',True))
        check('R15','critical',sum(shifted)/3<=.98,shifted)
        try:swapped=json.loads((work/'swapped.json').read_text())
        except ValueError as e:raise RuntimeError('trusted swapped metrics malformed') from e
        check('R16','critical',any(v>.03 for v in swapped),swapped)
        manifest=json.loads(require('manifest.json').read_text());check('R17','must',not scene['external'] and manifest.get('units')=='meters' and manifest.get('schemaVersion')==1 and manifest.get('assets') and all(a.get('license') in ['CC0-1.0','CC-BY-4.0'] and a.get('source') for a in manifest['assets']) and all(r['triangles']<=150000 for r in rigs.values()))
    except (CandidateError,FileNotFoundError,ValueError,KeyError,TypeError,IndexError,subprocess.TimeoutExpired) as e:check('submission','must',False,str(e))
    finish(checks)
if __name__=='__main__':main()
