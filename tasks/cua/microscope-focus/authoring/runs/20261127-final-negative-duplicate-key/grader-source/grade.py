"""Binary rubric. Trusted failures exit nonzero; candidate failures write 0."""
import functools,http.server,json,math,os,pathlib,subprocess,threading,traceback
from check_scene import optical,selftest
from rerender import decode,expected_image,similarity,mapping_ok
ROOT=pathlib.Path('/app/out'); LOG=pathlib.Path('/logs/verifier'); TEST=pathlib.Path('/tests')
CHECKS=[]
def check(id,level,ok,detail=''):
    CHECKS.append({'id':id,'level':level,'pass':bool(ok),'detail':str(detail)[:2000]})
def finish():
    normal=[x for x in CHECKS if x['level']=='normal']; reward=int(all(x['pass'] for x in CHECKS if x['level']!='normal') and (not normal or sum(x['pass'] for x in normal)/len(normal)>=.8))
    data={'schemaVersion':1,'reward':reward,'checks':CHECKS}
    (LOG/'metrics.json').write_text(json.dumps(data,indent=2,allow_nan=False))
    (LOG/'ctrf.json').write_text(json.dumps({'results':{'tool':{'name':'microscope-focus'},'summary':{'tests':len(CHECKS),'passed':sum(x['pass'] for x in CHECKS),'failed':sum(not x['pass'] for x in CHECKS),'pending':0,'skipped':0,'other':0,'start':0,'stop':0},'tests':[{'name':x['id'],'status':'passed' if x['pass'] else 'failed','duration':0,'message':x['detail']} for x in CHECKS]}}))
    # Validate trusted metrics before writing the sole reward.
    assert data['checks'] and all(type(x['pass']) is bool for x in data['checks'])
    (LOG/'reward.txt').write_text(str(reward)+'\n');print(json.dumps(data));return reward
def pairs(items):
    d={}
    for k,v in items:
        if k in d:raise ValueError('duplicate JSON key: '+k)
        d[k]=v
    return d
def load(path):return json.loads(path.read_text(),object_pairs_hook=pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
def number(v):return type(v) in (int,float) and math.isfinite(v)
def close(a,b,rel=.01,abs_=1e-6):return a is None if b is None else number(a) and abs(a-b)<=max(abs_,rel*abs(b))
def optics_match(a,b,rel=.01):
    try:return all(a[k]['kind']==b[k]['kind'] and all(close(a[k][v],b[k][v],rel) for v in ['s','v','m']) for k in ['objective','eyepiece']) and all(close(a[k],b[k],.02) for k in ['total','height']) and a['orientation']==b['orientation']
    except (KeyError,TypeError):return False
def geometry(q,expected,tol=2):
    try:return all(p and p['mesh'] and p['vertices']>=12 and p['visible'] and p['bounds'] and min(p['bounds'][1][i]-p['bounds'][0][i] for i in range(3))>.1 and math.dist(p['position'],expected[n])<=tol and max(abs(v) for v in p['rotation'])<=math.pi/180 and p['parent']=='microscope' for n,p in q['parts'].items()) and len(q['parts'])==5 and q['rendered']>20
    except (KeyError,TypeError,ValueError):return False
def ray_check(q):
    try:
        for prefix,lensname in [('objective','objective'),('eyepiece','eyepiece')]:
            r=q['optics'][prefix];ly=q['parts'][lensname]['position'][1]
            if r['v'] is None:continue
            for i in range(2):
                ray=next(x for x in q['rays'] if x['name']==prefix+'_'+str(i))['points'];p=ray[1];end=ray[2]
                if abs(p[1]-ly)>.001 or abs(p[0])>(7 if prefix=='objective' else 12) or abs(p[2])>.001:return False
                t=r['v']/(end[1]-p[1]);x=p[0]+t*(end[0]-p[0]);h=.05*(q['optics']['objective']['m'] if prefix=='eyepiece' else 1)*r['m']
                if abs(x-h)>1:return False
                if r['v']<0:
                    ext=next(x for x in q['rays'] if x['name']==prefix+'_virtual_'+str(i))['points'][-1]
                    if math.dist(ext,[h,ly+r['v'],0])>1:return False
        return len(q['rays'])>=4
    except (KeyError,StopIteration,ZeroDivisionError,TypeError):return False
class Server(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
    def log_message(self,*a):pass
    def do_GET(self):
        if self.path=='/__health':self.send_response(200);self.end_headers();self.wfile.write(b'<html>trusted browser health</html>');return
        if self.path.startswith('/__probe/'):
            if self.path!='/__probe/checker.png':self.send_error(404);return
            p=TEST/'fixtures'/pathlib.Path(self.path).name
            if not p.is_file():self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type','image/png');self.end_headers();self.wfile.write(p.read_bytes());return
        super().do_GET()
def main():
    selftest()
    fixtures=load(TEST/'fixtures'/'truth.json')
    assert fixtures['version']==1 and len(fixtures['assembly'])==5
    for n in ['sample_a.png','sample_b.png','checker.png']:
        from PIL import Image
        with Image.open(TEST/'fixtures'/n) as im:assert im.size==(1024,1024)
    try:
        files=list(ROOT.rglob('*'));assert len(files)<=500 and sum(p.stat().st_size for p in files if p.is_file())<=32*1024**2,'submission exceeds 32 MiB / 500 files'
        assert all(not p.is_symlink() and (not p.is_file() or p.stat().st_nlink==1) for p in files),'symlink/hardlink prohibited'
        assert all(p.is_dir() or p.is_file() for p in files),'regular files only'
        for n in ['microscope/index.html','state.json','replay.json','report.md','manifest.json']:assert (ROOT/n).is_file(),'missing '+n
        s=load(ROOT/'state.json');r=load(ROOT/'replay.json');manifest=load(ROOT/'manifest.json')
        assert isinstance(manifest,dict) and isinstance(manifest.get('assets'),list) and all(isinstance(a,dict) for a in manifest['assets']),'manifest object/assets list required'
        assert r=={'schemaVersion':1,'entry':'microscope/index.html','state':'state.json'},'wrong replay contract'
        assert type(r['schemaVersion']) is int
        assert s['schemaVersion']==1 and type(s['schemaVersion']) is int and s['units']=='mm' and set(s['assembly'])==set(fixtures['assembly'])
        assert len(s['settings'])==3
        for n,point in s['assembly'].items():assert len(point)==3 and all(number(v) and abs(v)<=1000 for v in point)
        for i,c in enumerate(s['settings']):
            assert c['id']=='abc'[i] and c['sample']==['sample_a.png','sample_b.png','sample_a.png'][i]
            assert all(number(c[k]) and abs(c[k])<=limit for k,limit in [('stageOffset',10),('objectiveOffset',2),('eyepieceOffset',5)])
            assert all(close(c[k],fixtures['settings'][i][k],0,1e-6) for k in ['stageOffset','objectiveOffset','eyepieceOffset']),'three prescribed settings required'
        assert (ROOT/'report.md').stat().st_size>=100
        check('R01','must',True)
    except (OSError,ValueError,AssertionError,KeyError,TypeError) as e:check('R01','must',False,str(e));finish();return
    required={'microscope/assets/sample_a.png','microscope/assets/sample_b.png','microscope/vendor/three.module.js','microscope/vendor/OrbitControls.js','references/front.png','references/side.png','references/three_quarter.png','optics.pdf'}
    covered={a.get('path') for a in manifest.get('assets',[]) if a.get('source') and a.get('license') in ['CC0-1.0','MIT','self-authored']}
    required|={p.relative_to(ROOT).as_posix() for p in files if p.suffix.lower() in ['.png','.jpg','.jpeg','.webp','.ttf','.woff','.woff2']}
    check('R15','must',manifest.get('schemaVersion')==1 and required<=covered,'reference/sample/vendor provenance required; system fonts only')
    jobs=[{'name':'case_'+str(i),'index':i,'persistence':i==0} for i in range(3)]
    jobs += [{'name':'repeat','index':0},{'name':'objective_1mm','index':0,'patch':{'objectiveOffset':1}},{'name':'heldout','index':1,'patch':{'objectiveOffset':-.37,'stageOffset':.12,'eyepieceOffset':-1.75}},{'name':'near','index':0,'patch':{'stageOffset':.12}},{'name':'near_plus','index':0,'patch':{'stageOffset':.120001}},{'name':'eye_infinity','index':0,'patch':{'stageOffset':4.12-540/131}},{'name':'zero','index':0,'patch':{'stageOffset':4.12}},{'name':'checker','index':0,'sample':'http://127.0.0.1:8090/__probe/checker.png'}]
    request={'url':'http://127.0.0.1:8090/'+r['entry'],'state':s,'jobs':jobs}
    pathlib.Path('/tmp/request.json').write_text(json.dumps(request))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',8090),Server);threading.Thread(target=server.serve_forever,daemon=True).start()
    # Trusted child driver and sandboxed browser; candidate modules never execute in Node.
    proc=subprocess.run(['node','/tests/browser.mjs','/tmp/request.json','/tmp/observations.json'],capture_output=True,text=True,timeout=240)
    (LOG/'browser.stdout.txt').write_text(proc.stdout);(LOG/'browser.stderr.txt').write_text(proc.stderr)
    if proc.returncode:raise RuntimeError('trusted browser driver failed: '+proc.stderr[-2000:])
    qs=load(pathlib.Path('/tmp/observations.json'));assert len(qs)==len(jobs),'malformed trusted extraction'
    check('R02','critical',all(not q['external'] for q in qs),'attempted external requests: '+str([q['external'] for q in qs if q['external']]))
    if any('error' in q or q['errors'] for q in qs):check('R01_runtime','must',False,str([{k:v for k,v in q.items() if k in ['job','error','errors']} for q in qs]));finish();return
    try:
        for q in qs:
            assert set(q['parts'])==set(fixtures['assembly'])
            for part in q['parts'].values():assert part and len(part['position'])==3 and all(number(v) for v in part['position'])
            assert isinstance(q['rays'],list) and isinstance(q['optics'],dict)
            for k in ['objective','eyepiece']:
                assert all(key in q['optics'][k] for key in ['s','v','m','kind'])
            assert all(k in q['optics'] for k in ['height','total','orientation'])
            assert decode(q['image']).shape==(720,1280,3)
    except (AssertionError,TypeError,ValueError,KeyError) as exc:
        check('R01_runtime','must',False,'invalid runtime observables: '+str(exc));finish();return
    expected=[]
    for j in jobs:
        c={**s['settings'][j['index']],**j.get('patch',{})};p={n:list(v) for n,v in fixtures['assembly'].items()}
        for n,k in [('stage','stageOffset'),('objective','objectiveOffset'),('eyepiece','eyepieceOffset')]:p[n][1]+=c[k]
        expected.append((p,optical(p['stage'][1],p['objective'][1],p['eyepiece'][1])))
    check('R03','must',all(geometry(q,expected[i][0]) for i,q in enumerate(qs[:3])),'five nonempty visible meshes, hierarchy, bounds, landmark position/angle')
    check('R04','must',all(math.dist(qs[i]['parts'][n]['position'],expected[i][0][n])<=.1 for i in [0,1,2,4,5] for n in ['stage','objective','eyepiece']),'actual focus coordinates ±0.1 mm')
    check('R05','must',all(optics_match(qs[i]['optics'],expected[i][1]) and close(qs[i]['optics']['eyepiece']['s'],expected[i][1]['eyepiece']['s'],0,.5) for i in range(3)),'independent two-stage lens calculation, all settings; eyepiece object distance ±0.5 mm')
    check('R06','must',all(close(qs[i]['optics'].get('total'),expected[i][1]['total'],.02) and qs[i]['optics'].get('orientation')==expected[i][1]['orientation'] for i in range(3)))
    check('R07','must',all(ray_check(q) for q in qs[:3]),'ray vertices, lens aperture and real/virtual image intersection')
    scores=[similarity(decode(qs[i]['image']),expected_image(TEST/'fixtures'/s['settings'][i]['sample'],expected[i][1]['total'])) for i in range(3)]
    maps=[mapping_ok(decode(qs[i]['image']),expected_image(TEST/'fixtures'/s['settings'][i]['sample'],expected[i][1]['total']),1024*abs(expected[i][1]['total'])*.006) for i in range(3)]
    check('R08','normal',min(scores)>=.90 and all(maps),'independent image mapping SSIM: '+str(scores)+'; foreground geometry/colour: '+str(maps))
    check('R09','must',all(optics_match(qs[i]['optics'],expected[i][1]) for i in [6,7,8,9]),'objective/eyepiece infinity, near-focus and zero-distance degeneracy')
    score_b=similarity(decode(qs[1]['image']),expected_image(TEST/'fixtures'/'sample_b.png',expected[1][1]['total']))
    check('R10','must',score_b>=.90 and maps[1] and optics_match(qs[5]['optics'],expected[5][1]),'second sample and held-out legal controls')
    def same(a,b):return a['parts']==b['parts'] and a['optics']==b['optics'] and a['image']==b['image']
    check('R11','must',same(qs[0],qs[0]['restored']) and geometry(qs[0]['reset'],fixtures['assembly'],1e-4) and optics_match(qs[0]['reset']['optics'],expected[0][1],1e-6))
    check('R12','critical',same(qs[0],qs[3]),'two fresh browser contexts from state only')
    check('R13','critical',optics_match(qs[4]['optics'],expected[4][1],.005) and optics_match(qs[5]['optics'],expected[5][1],.005) and not close(qs[4]['optics']['objective']['v'],qs[0]['optics']['objective']['v'],.005),'1 mm objective shift plus held-out compound perturbation')
    checker=similarity(decode(qs[10]['image']),expected_image(TEST/'fixtures'/'checker.png',expected[10][1]['total']))
    check('R14','critical',checker>=.90 and similarity(decode(qs[10]['image']),decode(qs[0]['image']))<.98,'unseen sample through same mapping: '+str(checker))
    finish()
if __name__=='__main__':
    LOG.mkdir(parents=True,exist_ok=True)
    try:main()
    except Exception:
        (LOG/'infrastructure-error.txt').write_text(traceback.format_exc());raise
