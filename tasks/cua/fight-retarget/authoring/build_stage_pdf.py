from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import subprocess
from pypdf import PdfReader
root=Path(__file__).resolve().parents[1]
p=root/'environment/materials/stage.pdf'
c=canvas.Canvas(str(p),pagesize=(595,842));c.setTitle('Fight stage and delivery specification')
c.setFillColor(HexColor('#183451'));c.rect(0,760,595,82,fill=1,stroke=0);c.setFillColorRGB(1,1,1);c.setFont('Helvetica-Bold',22);c.drawString(42,795,'Fight stage')
c.setFillColor(HexColor('#23364d'));c.setFont('Helvetica',12)
lines=['Units: metres. Stage: 6 x 6, centred at world origin. Z up.', 'Initial root X: left -1.20, right +1.20. Root distance 2.40.', 'Initial facing: blue +X, orange -X. Heights: 1.70 / 1.90.', 'Camera: cam_fixed. Orthographic scale 3.80.', 'Camera location: (0, -5.80, 2.25). Target: (0, 0, 0.90).', 'Frame rate: 30 fps. Animation: frames 1-300 (10 seconds).']
for i,line in enumerate(lines):c.drawString(42,725-i*25,line)
left,base,size=117,225,360
c.setStrokeColor(HexColor('#93a9c3'));c.setLineWidth(.5)
for i in range(13):
    v=i*size/12;c.line(left+v,base,left+v,base+size);c.line(left,base+v,left+size,base+v)
c.setStrokeColor(HexColor('#284764'));c.setLineWidth(1.5);c.rect(left,base,size,size)
c.setFillColor(HexColor('#287fd1'));c.circle(left+size*.3,base+size*.5,10,fill=1,stroke=0)
c.setFillColor(HexColor('#e26539'));c.circle(left+size*.7,base+size*.5,10,fill=1,stroke=0)
c.setFillColor(HexColor('#23364d'));c.setFont('Helvetica',10)
c.drawString(left+size*.3-15,base+size*.5+20,'LEFT');c.drawString(left+size*.7-18,base+size*.5+20,'RIGHT')
c.drawString(117,202,'Top view. Grid interval 0.5 m. Camera on negative Y side.')
c.setFont('Helvetica-Bold',13);c.drawString(42,158,'Required key frames')
c.setFont('Helvetica',11);c.drawString(42,136,'48 attack / 65 contact / 235 kick and duck / 300 finish')
c.drawString(42,102,'Contact and support intervals: action_segments.csv, support_phases.json.')
c.setFillColor(HexColor('#65778c'));c.setFont('Helvetica',9);c.drawString(42,50,'CC0-1.0 | Synthetic reference choreography | Source: authoring/choreography.py')
c.save()
doc=PdfReader(p)
assert '2.40' in doc.pages[0].extract_text() and len(doc.pages)==1
