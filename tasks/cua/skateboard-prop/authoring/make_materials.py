"""Authoring tool: writes the skateboard design pack.

    blender -b -P make_materials.py -- <materials_dir> [<solution_dir>]

Pure standard library; see packgen.py.
"""
import csv
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packgen

INK = (26, 30, 42)
DIM = (170, 60, 40)
GREY = (150, 150, 155)
PAPER = (250, 249, 245)
NAVY = (24, 38, 64)
CREAM = (238, 228, 205)
ORANGE = (216, 96, 44)

MM = 1.0 / 1000.0


# --------------------------------------------------------------------------
def deck_graphic(path, w=2048, h=512):
    """1:1 artwork for the 800 x 200 mm underside. Asymmetric nose mark."""
    c = packgen.Canvas(w, h, CREAM, scale=1)
    c.rect(0, 0, w, h, NAVY, fill=NAVY, width=0)
    c.rect(28, 28, w - 28, h - 28, CREAM, width=0)
    # chevrons
    for k in range(-4, 14):
        x = k * 180
        c.line(x, h - 40, x + 150, 40, ORANGE, 10)
        c.line(x + 60, h - 40, x + 210, 40, (200, 170, 120), 4)
    # wordmark
    c.rect(560, 150, 1480, 360, NAVY, fill=NAVY, width=0)
    c.text_center(1020, 190, "ATLAS", 12, CREAM)
    c.text_center(1020, 320, "SKATE MFG - 78A", 4, (240, 200, 120))
    # nose marker (right end = +X, i.e. the nose)
    c.rect(1900, 60, 1980, 452, ORANGE, fill=ORANGE, width=0)
    c.text_center(1940, 230, "N", 4, NAVY)
    with open(path, "wb") as fh:
        fh.write(c.png())


# --------------------------------------------------------------------------
def three_views(path):
    W, H = 1800, 1250
    c = packgen.Canvas(W, H, PAPER)
    c.text(40, 26, "SKATEBOARD DECK - THREE VIEWS (MM)", 3, INK)
    c.text(40, 60, "DECK 800 x 200 x 12. KICK 20 DEG OVER THE LAST 130 AT EACH END. CONCAVE 8. WHEELBASE 440.", 1, INK)

    s = 1.55  # px per mm

    def plan(x_mm, y_mm):
        return 480 + x_mm * s, 420 - y_mm * s

    def side(x_mm, z_mm):
        return 480 + x_mm * s, 900 - z_mm * s

    def end(y_mm, z_mm):
        return 1420 + y_mm * s * 1.2, 900 - z_mm * s

    # plan view
    x0, y0 = plan(-400, 100)
    x1, y1 = plan(400, -100)
    c.rect(x0, y0, x1, y1, INK, width=1.4)
    for kick_x in (-270, 270):
        c.dashed(*plan(kick_x, 100), *plan(kick_x, -100), GREY)
        c.text(plan(kick_x, 0)[0] - 22, plan(kick_x, 0)[1] - 26, "KICK", 1, GREY)
    for axle in (-220, 220):
        c.dashed(*plan(axle, 100), *plan(axle, -100), DIM)
        cx, cy = plan(axle, 0)
        c.circle(cx, cy, 5, DIM, width=1.2)
    # wheelbase dim
    ax0 = plan(-220, -100)[0]
    ax1 = plan(220, -100)[0]
    yd = plan(0, -100)[1] + 52
    c.line(ax0, yd, ax1, yd, DIM, 1.0)
    for x in (ax0, ax1):
        c.line(x, yd - 8, x, yd + 8, DIM, 1.0)
    c.text_center((ax0 + ax1) / 2, yd + 14, "WHEELBASE 440", 2, DIM)
    # deck length
    lx = plan(-400, 0)[0] - 55
    c.line(lx, plan(0, 100)[1], lx, plan(0, -100)[1], DIM, 1.0)
    c.text(lx - 74, (plan(0, 100)[1] + plan(0, -100)[1]) / 2 - 6, "800", 2, DIM)
    c.text_center((x0 + x1) / 2, y1 + 40, "UNDERSIDE PATTERN 1:1 ON THIS FACE", 2, INK)

    # side view
    def deck_profile(xm):
        d = max(0.0, -50 - xm, xm - 490)
        return 0.0 if d <= 0 else 20.0 * 0.364 * d  # tan(20) in mm/mm

    pts_top = [(x, deck_profile(x) + 12) for x in range(-400, 401, 10)]
    pts_bot = [(x, deck_profile(x)) for x in reversed(range(-400, 401, 10))]
    poly = [side(x, z) for x, z in pts_top] + [side(x, z) for x, z in pts_bot]
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1]):
        c.line(ax, ay, bx, by, INK, 1.4)
    for axle in (-220, 220):
        cx, cy = side(axle, 30)
        c.line(cx, cy, cx, side(axle, 6)[1], INK, 1.0)
        c.circle(side(axle, 27)[0], side(axle, 27)[1], 27 * s, INK, width=1.0)
        c.circle(side(axle, 27)[0], side(axle, 27)[1], 4, GREY, fill=GREY)
    c.text(side(-160, 118)[0], side(-160, 118)[1], "KICK 20 DEG", 2, DIM)
    c.text(side(120, 90)[0], side(120, 90)[1], "TRUCK + 54 WHEEL", 1, GREY)

    # end view: concave and plies
    cx, cy = end(0, 0)
    width = 100 * s * 1.2
    pts = []
    for ym in range(-100, 101, 4):
        z = 8.0 * (ym / 100.0) ** 2
        pts.append((ym, z))
    top = [(ym, z + 12) for ym, z in pts]
    for (a, b), (d, e) in zip(pts, pts[1:]):
        c.line(*end(a, b), *end(d, e), INK, 1.4)
    for (a, b), (d, e) in zip(top, top[1:]):
        c.line(*end(a, b), *end(d, e), INK, 1.4)
    c.line(*end(-100, 8), *end(-100, 20), INK, 1.4)
    c.line(*end(100, 8), *end(100, 20), INK, 1.4)
    # seven plies
    for k in range(1, 7):
        z = 8 + 12 * k / 7
        c.line(*end(-100, z), *end(100, z), GREY, 0.8)
    c.text(end(0, 30)[0] - 70, end(0, 30)[1], "7 PLY / 12", 2, DIM)
    c.text(end(-100, 46)[0], end(-100, 46)[1], "CONCAVE 8", 2, DIM)

    c.text(40, 1180, "REAR AXLE CENTRE IS THE MODEL ORIGIN. +X POINTS TO THE NOSE. WHEEL DIA 54, TRUCK WIDTH 180.", 1, INK)
    with open(path, "wb") as fh:
        fh.write(c.png())


# --------------------------------------------------------------------------
def spec_pdf(path):
    pdf = packgen.PDF(595, 842)

    def heading(y, text):
        pdf.text(56, y, text, 13, bold=True)
        pdf.line(56, y + 6, 539, y + 6, width=0.8)

    pdf.text(56, 56, "SKATEBOARD DECK - DESIGN AND MATERIAL PACK", 16, bold=True)
    pdf.text(56, 76, "Game prop, real-world dimensions in millimetres. Units in the scene: metres.", 10)
    heading(108, "1. Deck")
    for i, line in enumerate([
        "Plan 800 x 200, slab 12 thick, 7-ply maple, each ply about 1.7.",
        "Kicktails: 20 degrees, starting 130 from each end; noses and tails are symmetric.",
        "Concave: 8 at the rails, 0 at the centreline.",
        "Wheelbase 440, measured axle to axle. Rear axle centre is the model origin,",
        "   +X towards the nose, +Y to the rider's left, +Z up.",
        "Underside artwork deck_graphic.png (2048 x 512) is mapped 1:1, no crop,",
        "   nose marker at the +X end, UVs not overlapping.",
    ]):
        pdf.text(64, 130 + 14 * i, line, 9)
    heading(240, "2. Hardware")
    for i, line in enumerate([
        "Trucks: 6061 aluminium, 180 wide, 30 from axle centre to deck underside;",
        "   metallic >= 0.8, roughness 0.30-0.40.",
        "Wheels: polyurethane 78A, 54 diameter, 32 wide, roughness 0.50-0.80.",
        "Bearings: steel, metallic 1.0, inside each wheel.",
        "Grip tape on top: dark, roughness >= 0.9, fine noise bump.",
    ]):
        pdf.text(64, 262 + 14 * i, line, 9)
    heading(366, "3. Game specification")
    for i, line in enumerate([
        "Triangles <= 40 000 for the whole board.",
        "Textures <= 2048 in either dimension, PBR metallic-roughness, packed.",
        "GLB <= 15 MB, textures embedded, metres.",
        "Scene origin at the rear axle centre, within 5 mm.",
        "Keep the hierarchy: deck, truck_front, truck_rear, wheel_01..04, bearings.",
    ]):
        pdf.text(64, 388 + 14 * i, line, 9)
    heading(486, "4. Deliverables and render brief")
    for i, line in enumerate([
        "skateboard.blend, skateboard.glb, manifest.json.",
        "render_three_quarter.png: cam_three_quarter, 35 mm, 1.2 m from the deck centre,",
        "   0.80 m above the deck plane, 1600 x 1200.",
        "render_bottom.png: cam_bottom, orthographic, 900 x 506 coverage, 1600 x 900,",
        "   looking at the underside.",
        "render_edge.png: cam_edge, 100 mm macro, 0.25 m from the side rail, 1600 x 1200;",
        "   the seven plies must be readable.",
        "Cycles CPU, 64 samples, denoising, fixed seed.",
    ]):
        pdf.text(64, 508 + 14 * i, line, 9)
    heading(646, "5. Licence")
    pdf.text(64, 668, "Artwork and specification authored for this task; CC0-1.0. See LICENSE.txt.", 9)
    pdf.save(path)


# --------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    materials = argv[0]
    solution = argv[1] if len(argv) > 1 else None
    for sub in ("drawings", "spec", "photos"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    deck_graphic(os.path.join(materials, "spec", "deck_graphic.png"))
    three_views(os.path.join(materials, "drawings", "skateboard_three_views.png"))
    spec_pdf(os.path.join(materials, "spec", "material_spec.pdf"))
    rows = [
        ["part", "material", "parameters"],
        ["deck", "7-ply maple", "12 total, ply ~1.7, 7 visible edge bands"],
        ["deck underside", "printed graphic", "2048x512, 1:1, UV not overlapping"],
        ["deck top", "grip tape", "roughness >=0.9, noise bump"],
        ["truck_front/rear", "6061 aluminium", "metallic >=0.8, roughness 0.30-0.40"],
        ["wheel_01..04", "polyurethane 78A", "dia 54, width 32, roughness 0.50-0.80"],
        ["bearings", "steel", "metallic 1.0, roughness 0.20-0.30"],
    ]
    with open(os.path.join(materials, "spec", "material_spec.csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    packgen.write_xlsx(os.path.join(materials, "spec", "material_spec.xlsx"), "materials", rows,
                       col_widths=[20, 22, 44])
    if solution:
        for src_name, dst_name in (("render_three_quarter.png", "ref_three_quarter.png"),
                                   ("render_bottom.png", "ref_bottom.png"),
                                   ("render_edge.png", "ref_edge.png")):
            src = os.path.join(solution, src_name)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(materials, "photos", dst_name))
    with open(os.path.join(materials, "LICENSE.txt"), "w") as fh:
        fh.write(
            "SKATEBOARD DECK DESIGN PACK - CC0-1.0\n\n"
            "Every drawing, texture and table in this pack was authored for this\n"
            "task and is released under CC0-1.0. You may copy, modify and\n"
            "redistribute it, including commercially, without attribution.\n\n"
            "Files: drawings/*, spec/*, photos/*\n")
    print("materials written to", materials)


if __name__ == "__main__":
    main()
