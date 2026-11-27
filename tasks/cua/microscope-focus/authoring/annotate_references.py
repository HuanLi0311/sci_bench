from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1]/'environment/materials/references'
coords=json.loads((root/'landmarks.json').read_text())
font=ImageFont.truetype('DejaVuSans.ttf',20) if Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf').exists() else ImageFont.load_default(size=20)
for name,parts in coords.items():
 im=Image.open(root/(name+'.png')).convert('RGB');d=ImageDraw.Draw(im)
 d.rectangle((0,0,1280,65),fill='#123349');d.text((28,20),'MICROSCOPE / '+name.upper()+' / landmark centres in mm',fill='white',font=font)
 labels={'eyepiece':(45,120),'tube':(45,350),'body':(960,450),'objective':(45,690),'stage':(960,790)}
 for n,(x,y) in parts.items():
  lx,ly=labels[n];d.line((x-7,y,x+7,y),fill='#bd3e44',width=2);d.line((x,y-7,x,y+7),fill='#bd3e44',width=2);d.line((x,y,lx,ly+12),fill='#46657a',width=2)
  d.rectangle((lx-5,ly-5,lx+275,ly+53),fill='#f5f8fa');d.text((lx,ly),n,fill='#123349',font=font)
  text={'body':'(55,60,0)','tube':'(0,80,0)','objective':'(0,0,0)','eyepiece':'(0,160,0)','stage':'(0,-4.12,0)'}[n];d.text((lx,ly+25),text,fill='#31516c',font=font)
 im.save(root/(name+'.png'))
print('annotated 3 reference views')
