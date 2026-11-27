"""Create public target images and the immutable GLB from the server fixture."""
import json,math,struct,sys,hashlib,shutil
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
from kinematics import replay
p=json.loads((ROOT/'environment/service/fixture.json').read_text());out=ROOT/'environment/materials'
font=ImageFont.truetype('DejaVuSans.ttf',19) if Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').exists() else ImageFont.load_default()
def project(pt,v):
    return (640+240*(pt[0] if v==0 else pt[1] if v==1 else (pt[0]-pt[1])/math.sqrt(2)),650-300*pt[2])
names=['hips','spine','chest','neck','upper_arm.L','forearm.L','upper_arm.R','forearm.R']
colors=['#f26739','#82c994','#6f9ce5']
for k in 'abc':
    positions,rotations=replay(p,p['targets'][k])
    for v,view in enumerate(['front','side','oblique']):
        im=Image.new('RGB',(1280,720),'#111e30');d=ImageDraw.Draw(im)
        d.text((42,28),f'CASE {k.upper()} / {view.upper()} - joint centres and local axes',fill='white',font=font)
        for i,parent in enumerate(p['parents']):
            x,y=project(positions[i],v)
            if parent>=0:d.line([project(positions[parent],v),(x,y)],fill='#e9a756',width=10)
            for a in range(3):d.line([(x,y),project(positions[i]+rotations[i][:,a]*.16,v)],fill=colors[a],width=3)
            d.ellipse((x-6,y-6,x+6,y+6),fill='#f2b969',outline='white',width=1)
            d.text((x+9,y+7),str(i),fill='white',font=font)
        d.text((42,680),'0 hips  1 spine  2 chest  3 neck  4/5 left arm  6/7 right arm | red X, green Y, blue Z',fill='#adc0d7',font=font)
        im.save(out/f'target_case_{k}_{view}.png')
# glTF nodes preserve the same fixed hierarchy and rest offsets. Each segment is
# a genuine line primitive in the GLB, not a screenshot billboard.
positions=[]
for i,parent in enumerate(p['parents']):positions.append(np.array([0,0,.9]) if parent<0 else positions[parent]+np.array(p['offsets'][i]))
verts=[];joints=[]
for i,parent in enumerate(p['parents']):
    if parent>=0:verts.extend([positions[parent].tolist(),positions[i].tolist()]);joints.extend([parent,i])
chunks=[b''.join(struct.pack('<fff',*v) for v in verts),b''.join(struct.pack('<HHHH',j,0,0,0) for j in joints),b''.join(struct.pack('<ffff',1,0,0,0) for j in joints)]
bind=[]
for v in positions:
    m=np.eye(4);m[:3,3]=-v;bind.extend(m.T.flatten().tolist())
chunks.append(struct.pack('<'+'f'*len(bind),*bind))
binary=b''.join(chunks)
nodes=[dict(name=names[i],translation=p['offsets'][i] if i else [0,0,.9],children=[j for j,x in enumerate(p['parents']) if x==i]) for i in range(8)]
nodes.append(dict(name='avatar_geometry',mesh=0,skin=0))
offset=0;views=[]
for chunk in chunks:views.append(dict(buffer=0,byteOffset=offset,byteLength=len(chunk)));offset+=len(chunk)
doc=dict(asset=dict(version='2.0',generator='sci_bench CC0 pose avatar'),scene=0,scenes=[dict(nodes=[0,8])],nodes=nodes,skins=[dict(joints=list(range(8)),inverseBindMatrices=3,skeleton=0)],meshes=[dict(primitives=[dict(attributes=dict(POSITION=0,JOINTS_0=1,WEIGHTS_0=2),mode=1)])],buffers=[dict(byteLength=len(binary))],bufferViews=views,accessors=[dict(bufferView=0,componentType=5126,count=len(verts),type='VEC3',min=np.min(verts,axis=0).tolist(),max=np.max(verts,axis=0).tolist()),dict(bufferView=1,componentType=5123,count=len(verts),type='VEC4'),dict(bufferView=2,componentType=5126,count=len(verts),type='VEC4'),dict(bufferView=3,componentType=5126,count=8,type='MAT4')])
raw=json.dumps(doc,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);binary+=b'\0'*((-len(binary))%4)
glb=struct.pack('<III',0x46546c67,2,12+8+len(raw)+8+len(binary))+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary
(out/'avatar.glb').write_bytes(glb)
(out/'scene.json').write_text(json.dumps(dict(schemaVersion=1,parents=p['parents'],offsets=p['offsets'],joint_names=names,observations='3 views, 8 joints, centre and XYZ-axis endpoints; 192 scalar pixel coordinates',projection=dict(views=['front','side','oblique'],width=1280,height=720,scale_xy=240,scale_z=300,origin=[640,650])),indent=2))
hashes={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ['avatar.glb','scene.json','bounds.json']}
(ROOT/'tests/public-hashes.json').write_text(json.dumps(hashes,indent=2))
(ROOT/'tests/original').mkdir(exist_ok=True)
for name in hashes:shutil.copyfile(out/name,ROOT/'tests/original'/name)
(ROOT/'tests/service').mkdir(exist_ok=True)
for name in ['server.cjs','model.cjs','fixture.json']:shutil.copyfile(ROOT/'environment/service'/name,ROOT/'tests/service'/name)
