"""Authoring tool: writes the banner-stand design pack.

    blender -b -P make_materials.py -- <materials_dir> [<solution_dir>]
"""
import csv
import math
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packgen

INK = (26, 28, 34)
DIM = (170, 60, 40)
GREY = (150, 150, 155)
PAPER = (250, 249, 245)
ALU = (196, 199, 205)


def front(c, ox, oy, s):
    def p(x, z):
        return ox + x * s, oy - z * s

    c.rect(*p(-400, 50), *p(400, 0), INK, fill=ALU, width=1.2)
    for x in (-380, 380):
        c.rect(*p(x - 20, 1960), *p(x + 20, 50), INK, fill=ALU, width=1.1)
    c.rect(*p(-400, 2000), *p(400, 1960), INK, fill=ALU, width=1.1)
    c.rect(*p(-400, 1960), *p(400, 60), INK, fill=(238, 232, 216), width=1.1)
    c.text_center(ox, p(0, 1700)[1], "BANNER 800 x 1900", 2, GREY)
    c.text_center(ox, p(0, 1500)[1], "PRINT 1:1", 2, GREY)
    yb = oy + 50
    c.line(p(-400, 0)[0], yb, p(400, 0)[0], yb, DIM, 1.0)
    c.line(p(-400, 0)[0], yb - 8, p(-400, 0)[0], yb + 8, DIM, 1.0)
    c.line(p(400, 0)[0], yb - 8, p(400, 0)[0], yb + 8, DIM, 1.0)
    c.text_center(ox, yb + 14, "800", 2, DIM)
    hx = p(-400, 0)[0] - 55
    c.line(hx, p(0, 0)[1], hx, p(0, 2000)[1], DIM, 1.0)
    c.text(hx - 76, p(0, 1000)[1], "2000", 2, DIM)


def side_open(c, ox, oy, s):
    def p(y, z):
        return ox + (y + 260) * s, oy - z * s

    c.rect(*p(-60, 50), *p(60, 0), INK, fill=ALU, width=1.1)
    c.rect(*p(-20, 2000), *p(20, 50), INK, fill=ALU, width=1.1)
    c.line(*p(30, 60), *p(30, 1960), GREY, 1.0)
    r = math.radians(14)
    tipy, tipz = -45 - 1900 * math.sin(r), 75 + 1900 * math.cos(r)
    c.line(*p(-45, 75), *p(tipy, tipz), INK, 1.2)
    c.circle(*p(-45, 75), 4, INK, fill=INK)
    c.dashed(*p(0, 0), *p(tipy, 0), DIM)
    c.text(p(tipy, 0)[0] - 10, p(0, 0)[1] + 16, "TOP OFFSET 505", 1, DIM)
    c.text(ox - 150, oy - 2100 * s - 10, "BRACE 1900. HINGE Y=-45 Z=75. OPEN 14 DEG.", 1, INK)



def side_folded(c, ox, oy, s):
    def p(y, z):
        return ox + (y + 120) * s, oy - z * s

    c.rect(*p(-60, 50), *p(60, 0), INK, fill=ALU, width=1.1)
    c.rect(*p(-20, 2000), *p(20, 50), INK, fill=ALU, width=1.1)
    c.line(*p(-45, 75), *p(-45, 1975), INK, 1.2)
    c.circle(*p(-45, 75), 4, INK, fill=INK)
    c.text(ox - 40, p(0, 2000)[1] - 30, "FOLDED: 123 DEEP", 2, INK)


def draw_views(path):
    W, H = 1800, 1300
    c = packgen.Canvas(W, H, PAPER)
    c.text(40, 26, "FOLDING BANNER STAND - FRONT, SIDE AND FOLDED (MM)", 3, INK)
    c.text(40, 60, "800 WIDE, 2000 HIGH. CANVAS 800 x 1900. REAR BRACE 1900, OPENS 0-14 DEG. FOLDED DEPTH <=130.", 1, INK)
    front(c, 430, 1150, 0.42)
    side_open(c, 1030, 1150, 0.36)
    side_folded(c, 1500, 1150, 0.36)
    c.text(40, 1240, "ORIGIN AT FLOOR CENTRE. +Y IS THE FRONT. MASTS 40 SQUARE, TOP BAR 800 x 40 x 40, BASE 800 x 120 x 50.", 1, INK)
    with open(path, "wb") as fh:
        fh.write(c.png())
    c.save_pdf(os.path.splitext(path)[0] + '.pdf')


def spec_pdf(path):
    pdf = packgen.PDF(595, 842)

    def heading(y, text):
        pdf.text(56, y, text, 13, bold=True)
        pdf.line(56, y + 6, 539, y + 6, width=0.8)

    pdf.text(56, 56, "FOLDING BANNER STAND - DESIGN PACK", 16, bold=True)
    pdf.text(56, 76, "Exhibition display. Units: millimetres.", 10)
    heading(108, "1. Frame")
    for i, line in enumerate([
        "Overall 800 wide, 2000 high, base 800 x 120 x 50 on the floor.",
        "Masts 40 x 40 from z = 50 to 1960 at x = +/-380; top bar 800 x 40 x 40 at 1960..2000.",
        "Parts: base, mast_left, mast_right, top_bar, canvas, leg_rear, hinge_rear.",
        "Origin at floor centre, +Y front, +Z up.",
    ]):
        pdf.text(64, 130 + 14 * i, line, 9)
    heading(206, "2. Canvas")
    for i, line in enumerate([
        "Canvas 800 x 1900, from z = 60 to 1960, facing +Y at y = 30.",
        "It hangs flat: every vertex within 2 mm of the plane and the top edge within",
        "   3 mm of the top bar underside.",
        "Print artwork 819 x 1945 (1.024 px/mm) mapped 1:1: UV area 1.0, no crop,",
        "   no overlap, image aspect within 2 percent of 800/1900.",
    ]):
        pdf.text(64, 228 + 14 * i, line, 9)
    heading(310, "3. Rear leg")
    for i, line in enumerate([
        "leg_rear is 1900 long, parented to an empty hinge_rear at (0, -45, 75) near the",
        "   base rear edge. The hinge rotates about X away from the print: 0 degrees is",
        "   folded against the masts, 14 degrees is open with the top 500 mm behind the",
        "   stand and 1920 high.",
        "At 0, 7 and 14 degrees the brace must not touch the masts, bar, base or canvas.",
        "Folded, the whole stand is at most 130 mm deep.",
    ]):
        pdf.text(64, 332 + 14 * i, line, 9)
    heading(410, "4. Materials")
    for i, line in enumerate([
        "Canvas: printed, roughness 0.55-0.85, artwork packed.",
        "Frame: aluminium, metallic >= 0.8, roughness 0.25-0.40.",
    ]):
        pdf.text(64, 432 + 14 * i, line, 9)
    heading(470, "5. Deliverables and render brief")
    for i, line in enumerate([
        "banner_stand.blend, manifest.json.",
        "render_front.png: cam_front, orthographic, 2.15 m coverage, 1200 x 1600,",
        "   rear brace open at 14 degrees.",
        "render_three_quarter.png: cam_three_quarter, 35 mm, 1600 x 1200, open.",
        "render_folded.png: cam_folded, orthographic, 1200 x 1600, brace folded to 0.",
        "Cycles CPU, 64 samples, denoising, fixed seed.",
    ]):
        pdf.text(64, 492 + 14 * i, line, 9)
    heading(612, "6. Licence")
    pdf.text(64, 634, "Authored for this task; CC0-1.0.", 9)
    pdf.save(path)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    materials = argv[0]
    solution = argv[1] if len(argv) > 1 else None
    for sub in ("drawings", "spec", "photos"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    draw_views(os.path.join(materials, "drawings", "banner_three_views.png"))
    spec_pdf(os.path.join(materials, "spec", "banner_spec.pdf"))
    rows = [
        ["part", "size_mm", "material"],
        ["base", "800 x 120 x 50", "aluminium, metallic 0.9"],
        ["mast_left/right", "40 x 40 x 1910", "aluminium"],
        ["top_bar", "800 x 40 x 40", "aluminium"],
        ["canvas", "800 x 1900, print 819 x 1945", "printed textile, roughness 0.72"],
        ["leg_rear", "1900 long, 36 square", "aluminium, hinged at 0-14 deg"],
    ]
    with open(os.path.join(materials, "spec", "parts.csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    packgen.write_xlsx(os.path.join(materials, "spec", "parts.xlsx"), "parts", rows,
                       col_widths=[18, 34, 32])
    if solution:
        for name, dst in (("render_front.png", "ref_front.png"),
                          ("render_three_quarter.png", "ref_three_quarter.png"),
                          ("render_folded.png", "ref_folded.png")):
            src = os.path.join(solution, name)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(materials, "photos", dst))
    with open(os.path.join(materials, "LICENSE.txt"), "w") as fh:
        fh.write(
            "FOLDING BANNER STAND DESIGN PACK - CC0-1.0\n\n"
            "Drawings, tables and the reference renders were authored for this\n"
            "task and are released under CC0-1.0. Copy, modify and redistribute\n"
            "freely.\n")
    print("materials written to", materials)


if __name__ == "__main__":
    main()
