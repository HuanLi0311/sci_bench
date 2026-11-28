from pathlib import Path
import importlib.util, sys
from PIL import Image
from reportlab.pdfgen import canvas
import fitz

ROOT=Path(__file__).resolve().parent

def edit(path, old, new):
    s=path.read_text(encoding='utf-8'); assert old in s,(path,old)
    path.write_text(s.replace(old,new),encoding='utf-8',newline='\n')

p=ROOT/'banner-stand/instruction.md'
edit(p, 'the\nhinge at (0, 0, 1.96) ± 10 mm; at 14° the leg tip on the floor and 450–540 mm\nbehind the stand;', 'the\nhinge at (0, −0.045, 0.075) ± 10 mm; at 14° the brace top 460–560 mm\nbehind the stand and 1860–1960 mm above the floor;')
edit(p,'on the base\'s rear edge', 'near the base\'s rear edge')
p=ROOT/'banner-stand/task.toml'
edit(p,'a 2020 mm rear leg on a 0-14 degree hinge that folds the stand to 120 mm and opens its foot to the floor', 'a 1900 mm rear brace on a base-mounted 0-14 degree hinge that folds within 130 mm and opens its top 460-560 mm behind the stand')
p=ROOT/'banner-stand/authoring/make_materials.py'
edit(p,'p(-400, 1955)', 'p(-400, 1960)')
edit(p,'    c.rect(*p(-400, 1955), *p(-370, 60), GREY, width=0.8)\n', '') if False else None
# Replace the obsolete top-hinged leg in both side views.
s=p.read_text();start=s.index('    c.rect(*p(-400, 1955)') if '    c.rect(*p(-400, 1955)' in s else s.index('    c.rect(*p(-400, 1960)', s.index('def side_open'))
end=s.index('\n\n\ndef side_folded',start)
s=s[:start]+'''    c.line(*p(30, 60), *p(30, 1960), GREY, 1.0)
    r = math.radians(14)
    tipy, tipz = -45 - 1900 * math.sin(r), 75 + 1900 * math.cos(r)
    c.line(*p(-45, 75), *p(tipy, tipz), INK, 1.2)
    c.circle(*p(-45, 75), 4, INK, fill=INK)
    c.dashed(*p(0, 0), *p(tipy, 0), DIM)
    c.text(p(tipy, 0)[0] - 10, p(0, 0)[1] + 16, "TOP OFFSET 505", 1, DIM)
    c.text(ox - 150, oy - 2100 * s - 10, "BRACE 1900. HINGE Y=-45 Z=75. OPEN 14 DEG.", 1, INK)
'''+s[end:];p.write_text(s,encoding='utf-8',newline='\n')
edit(p, 'c.line(*p(0, 50), *p(0, 1960), INK, 1.2)', 'c.line(*p(-45, 75), *p(-45, 1975), INK, 1.2)\n    c.circle(*p(-45, 75), 4, INK, fill=INK)')
edit(p,'"FOLDED: 120 DEEP"','"FOLDED: 123 DEEP"')
edit(p,'REAR LEG 2020, OPENS 0-14 DEG. FOLDED DEPTH 120.', 'REAR BRACE 1900, OPENS 0-14 DEG. FOLDED DEPTH <=130.')
edit(p,"on the\"", "near the\"")
edit(p,'base rear edge.', 'base rear edge.')
p=ROOT/'drawer-cabinet/instruction.md'
edit(p,'fronts 440 × 150 mm\n   and 18 mm thick', 'fronts 440 × 140 mm\n   and 18 mm thick on a 150 mm vertical pitch (10 mm gaps)')
edit(p,'460 × 750 × 18 mm', '450 × 746 × 18 mm')
p=ROOT/'drawer-cabinet/authoring/make_materials.py'
edit(p,'z0 + 4', 'z0 + 5'); edit(p,'z1 - 4', 'z1 - 5')
edit(p,'p(22, 130), *p(478, 880)', 'p(31, 132), *p(481, 878)')
edit(p,'p(22, 130), *p(478, 880)', 'p(31, 132), *p(481, 878)') if False else None
edit(p,'p(22, 880), *p(478, 130)', 'p(31, 878), *p(481, 132)')
edit(p,'440 x 150', '440 x 140')
edit(p,'460 x 750', '450 x 746')
edit(p,'0.70 m above', '1.15 m above')
edit(p,'fronts 440 x 140 x 18,', 'fronts 440 x 140 x 18, pitch 150,')
# Show full travel in the side view, rather than labelling a 300 mm pose 420.
edit(p,'p(525, 430)', 'p(645, 430)'); edit(p,'p(525 - 18, 280)', 'p(645 - 18, 280)'); edit(p,'p(525, 355)', 'p(645, 355)')

for task,prefix in [('banner-stand','banner'),('drawer-cabinet','cabinet')]:
    directory=ROOT/task
    # Distinct module name to avoid sharing task-specific packgen state.
    sys.path.insert(0,str(directory/'authoring'))
    spec=importlib.util.spec_from_file_location(task, directory/'authoring/make_materials.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sys.argv=['make_materials.py',str(directory/'environment/materials'),str(directory/'solution')]
    module.main()
    drawing=directory/f'environment/materials/drawings/{prefix}_three_views.png'
    im=Image.open(drawing)
    pdf=canvas.Canvas(str(drawing.with_suffix('.pdf')),pagesize=(im.width/2,im.height/2))
    pdf.drawImage(str(drawing),0,0,width=im.width/2,height=im.height/2);pdf.save()
    qa=ROOT/'delivery-audit-20261128'/task/'pdf-qa';qa.mkdir(parents=True,exist_ok=True)
    for path in [drawing.with_suffix('.pdf'),directory/f'environment/materials/spec/{prefix}_spec.pdf']:
        doc=fitz.open(path)
        for i,page in enumerate(doc):
            page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(qa/f'{path.stem}-{i+1}.png')
    sys.path.pop(0)
