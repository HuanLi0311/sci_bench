"""Deterministic, self-authored fixtures. Run on authoring host, never in verifier."""
from pathlib import Path
import json,sys,shutil
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
ROOT=Path(__file__).resolve().parents[1]; MAT=ROOT/'environment/materials';FIX=ROOT/'tests/fixtures'
for p in [MAT/'samples',MAT/'references',MAT/'targets',FIX]:p.mkdir(parents=True,exist_ok=True)
state={'schemaVersion':1,'units':'mm','assembly':{'body':[55,60,0],'tube':[0,80,0],'objective':[0,0,0],'eyepiece':[0,160,0],'stage':[0,-4.12,0]},'settings':[{'id':'a','stageOffset':0,'objectiveOffset':0,'eyepieceOffset':0,'sample':'sample_a.png'},{'id':'b','stageOffset':-.04,'objectiveOffset':0,'eyepieceOffset':1,'sample':'sample_b.png'},{'id':'c','stageOffset':-.08,'objectiveOffset':0,'eyepieceOffset':-2,'sample':'sample_a.png'}]}
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
dump(ROOT/'solution/state.json',state);dump(ROOT/'solution/replay.json',{'schemaVersion':1,'entry':'microscope/index.html','state':'state.json'})
dump(FIX/'truth.json',{'version':1,**{k:state[k] for k in ['assembly','settings']}})
for i,n in enumerate(['sample_a.png','sample_b.png','checker.png']):
 im=Image.new('RGB',(1024,1024),(237,232,215));d=ImageDraw.Draw(im)
 if i==2:
  for y in range(0,1024,64):
   for x in range(0,1024,64):d.rectangle((x,y,x+63,y+63),fill=(25,65,95) if (x//64+y//64)%2 else (245,195,50))
 else:
  d.rectangle((70,70,954,954),outline=(20,55,75),width=12)
  d.polygon([(160,700),(160,180),(440,180),(440,260),(250,260),(250,440),(400,440),(400,520),(250,520),(250,700)],fill=(195,65,55) if i==0 else (40,110,170))
  for j in range(5):d.ellipse((540+j*20,220+j*125,680+j*20,330+j*125),fill=(35,120,100) if i==0 else (175,70,140))
  d.rectangle((100,800,800,850),fill=(25,55,80));d.polygon([(800,760),(930,825),(800,890)],fill=(25,55,80))
  d.rectangle((80,80,145,145),fill=(255,180,0));d.ellipse((800,80,940,220),fill=(10,120,180))
  if i==1:d.polygon([(400,800),(700,500),(800,800)],fill=(235,145,35))
 im.save(FIX/n)
 if i<2:im.save(MAT/'samples'/n)
sys.path.insert(0,str(ROOT/'tests'));from check_scene import optical;from rerender import expected_image
for c in state['settings']:
 r=optical(-4.12+c['stageOffset'],c['objectiveOffset'],160+c['eyepieceOffset'])
 Image.fromarray(expected_image(FIX/c['sample'],r['total']).astype('uint8')).save(MAT/'targets'/('case_'+c['id']+'.png'))
license='All original drawings, geometry, samples and targets: self-authored for this task, CC0-1.0.\nThree.js and OrbitControls 0.169.0: MIT; see starter/vendor/THREE-LICENSE.txt at runtime.\nNo external fonts, models, textures or photographs.\n'
(MAT/'LICENSE.txt').write_text(license)
assets=[{'path':p,'role':role,'source':source,'license':lic} for p,role,source,lic in [(f'microscope/assets/sample_{s}.png','sample','self-authored','CC0-1.0') for s in 'ab']+[(f'references/{v}.png','reference','self-authored','CC0-1.0') for v in ['front','side','three_quarter']]+[('optics.pdf','spec','self-authored','CC0-1.0'),('microscope/vendor/three.module.js','library','https://github.com/mrdoob/three.js/tree/r169','MIT'),('microscope/vendor/OrbitControls.js','library','https://github.com/mrdoob/three.js/tree/r169','MIT')]]
dump(ROOT/'solution/manifest.json',{'schemaVersion':1,'units':'mm','assets':assets});dump(MAT/'manifest.json',{'schemaVersion':1,'units':'mm','assets':assets})
schema={'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'urn:microscope:state:1','type':'object','required':['schemaVersion','units','assembly','settings'],'properties':{'schemaVersion':{'const':1},'units':{'const':'mm'},'assembly':{'type':'object','required':list(state['assembly']),'additionalProperties':False,'properties':{n:{'type':'array','minItems':3,'maxItems':3,'items':{'type':'number','minimum':-1000,'maximum':1000}} for n in state['assembly']}},'settings':{'type':'array','minItems':3,'maxItems':3,'items':{'type':'object','required':['id','sample','stageOffset','objectiveOffset','eyepieceOffset'],'properties':{'id':{'enum':['a','b','c']},'sample':{'enum':['sample_a.png','sample_b.png']},**{k:{'type':'number','minimum':-v,'maximum':v} for k,v in [('stageOffset',10),('objectiveOffset',2),('eyepieceOffset',5)]}}}}}}
dump(MAT/'starter/state.schema.json',schema)
# Typeset the optical drawing as a single readable technical sheet.
c=canvas.Canvas(str(MAT/'optics.pdf'),pagesize=(842,595),invariant=1);c.setTitle('Microscope / Cartesian optical model')
c.setFillColor(HexColor('#123349'));c.rect(0,515,842,80,fill=1,stroke=0);c.setFillColorRGB(1,1,1);c.setFont('Helvetica-Bold',23);c.drawString(38,555,'MICROSCOPE / OPTICAL ASSEMBLY');c.setFont('Helvetica',12);c.drawString(38,531,'Ideal air model | finite conjugates | dimensions in millimetres | CC0-1.0')
c.setStrokeColor(HexColor('#6d8595'));c.line(60,350,780,350)
for x,label in [(100,'Object plane'),(215,'Objective f=4'),(640,'Eyepiece f=25')]:
 c.line(x,300,x,400);c.setFillColor(HexColor('#123349'));c.setFont('Helvetica-Bold',12);c.drawCentredString(x,420,label)
c.setFont('Helvetica',11);c.drawString(685,358,'+Y / light');c.drawString(280,375,'Nominal lens separation L=160 mm')
c.setStrokeColor(HexColor('#db9a27'));c.line(100,375,215,375);c.line(215,375,590,340);c.line(100,375,215,350);c.line(215,350,590,340)
lines=['Signed distances: s = objectY - lensY; v = imageY - lensY.', 'Cartesian equation: 1/v - 1/s = 1/f. Transverse magnification m = v/s.', 'Intermediate imageY = objectiveY + v_o; s_e = intermediateImageY - eyepieceY.', 'Total transverse m = m_o * m_e; signed final image height = 0.05 mm * m.', 'v>0: real image, forward intersection. v<0: virtual image, backward extensions.', 'Stage travel +/-10 mm; eyepiece +/-5 mm; objective perturbations +/-2 mm.', '|s+f|<1e-9: infinity. |s|<1e-10: no finite image. Use tagged nulls, never NaN/Inf.', 'Neutral stageY=-4.12, objectiveY=0, eyepieceY=160. Settings and landmarks: SPEC.md.', 'Observer view: 1280x720, centred, square width=1024*abs(m)*0.006 px; invert both axes if m<0.']
c.setFillColor(HexColor('#17354b'));c.setFont('Helvetica',12)
for i,line in enumerate(lines):c.drawString(38,265-i*24,line)
c.setFont('Helvetica',9);c.drawString(38,25,'Schematic is not to scale. Reference geometry and target images share the same neutral assembly.');c.save()
print('generated state, schema, fixtures, samples, targets, optical PDF and licences')
