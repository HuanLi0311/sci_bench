"""Authoring tool: writes the drawer-cabinet design pack.

    blender -b -P make_materials.py -- <materials_dir> [<solution_dir>]
"""
import csv
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packgen

INK = (26, 28, 34)
DIM = (170, 60, 40)
GREY = (150, 150, 155)
PAPER = (250, 249, 245)
WOOD = (196, 162, 126)


def front_view(c, ox, oy, s):
    """Front elevation in millimetres; y grows downward on the canvas."""
    def p(x, z):
        return ox + x * s, oy - z * s

    c.rect(*p(-500, 900), *p(500, 0), INK, width=1.4)
    for i in range(5):
        z0 = 130 + i * 150
        z1 = z0 + 150
        c.rect(*p(-462, z0 + 4), *p(-22, z1 - 4), INK, width=1.1)
        cx, cy = p(-242, z0 + 75)
        c.circle(cx, cy, 5, GREY, fill=GREY, width=0)
        c.text(p(-462, z0 + 75)[0] - 46, p(-462, z0 + 75)[1] - 6, f"D{i + 1:02d}", 1, GREY)
    c.rect(*p(22, 130), *p(478, 880), INK, width=1.1)
    c.line(*p(22, 130), *p(478, 880), GREY, 0.6)
    c.line(*p(22, 880), *p(478, 130), GREY, 0.6)
    hx0, hy0 = p(58, 505)
    c.line(hx0, hy0 - 40, hx0, hy0 + 40, INK, 1.0)

    yd = oy + 60
    x0, y0 = p(-500, 0)
    x1, _ = p(500, 0)
    c.line(x0, yd, x1, yd, DIM, 1.0)
    c.line(x0, yd - 8, x0, yd + 8, DIM, 1.0)
    c.line(x1, yd - 8, x1, yd + 8, DIM, 1.0)
    c.text_center((x0 + x1) / 2, yd + 14, "1000", 2, DIM)

    dim_x = x0 - 60
    _, top_y = p(-500, 900)
    c.line(dim_x, top_y, dim_x, y0, DIM, 1.0)
    c.line(dim_x - 8, top_y, dim_x + 8, top_y, DIM, 1.0)
    c.line(dim_x - 8, y0, dim_x + 8, y0, DIM, 1.0)
    c.text(dim_x - 78, (top_y + y0) / 2 - 6, "900", 2, DIM)

    hdx = p(-462, 130)[0] - 34
    c.line(hdx, p(-462, 130)[1], hdx, p(-462, 280)[1], DIM, 0.8)
    c.text(hdx - 62, (p(-462, 130)[1] + p(-462, 280)[1]) / 2 - 6, "150", 1, DIM)


def side_view(c, ox, oy, s):
    def p(y, z):
        return ox + (y + 225) * s, oy - z * s

    c.rect(*p(-225, 900), *p(225, 60), INK, width=1.4)
    c.rect(*p(-225, 60), *p(225, 0), GREY, width=1.0)
    c.text(ox - 40, oy - 30 * s, "PLINTH 60", 1, GREY)
    c.rect(*p(225, 280), *p(525, 430), INK, fill=WOOD, width=1.2)
    c.rect(*p(525 - 18, 280), *p(525, 430), INK, fill=INK, width=1.0)
    c.dashed(*p(225, 355), *p(525, 355), DIM)
    c.text(p(300, 355)[0] + 10, p(300, 355)[1] - 26, "TRAVEL 420", 1, DIM)
    yb = oy + 40
    c.line(p(-225, 0)[0], yb, p(225, 0)[0], yb, DIM, 1.0)
    c.line(p(-225, 0)[0], yb - 8, p(-225, 0)[0], yb + 8, DIM, 1.0)
    c.line(p(225, 0)[0], yb - 8, p(225, 0)[0], yb + 8, DIM, 1.0)
    c.text_center(ox, yb + 14, "450", 2, DIM)


def door_detail(c, ox, oy, s):
    import math

    def p(x, y):
        return ox + x * s, oy - y * s

    c.rect(*p(-240, -100), *p(0, 100), INK, fill=WOOD, width=1.2)
    c.circle(*p(0, 0), 5, INK, fill=INK)
    c.text(ox + 12, oy - 96, "HINGE AXIS", 1, GREY)
    for deg in (0, 55, 110):
        r = math.radians(deg)
        ex, ey = -240 * math.cos(r), 240 * math.sin(r)
        c.line(*p(0, 0), *p(ex, ey), DIM if deg else INK, 1.0)
        px, py = p(ex, ey)
        c.text(px + 8, py - 14, f"{deg}", 1, DIM)
    c.text(ox - 230, oy + 130, "DOOR OPENS 0-110 DEG, NO CONTACT WITH THE CARCASS", 1, INK)


def draw_three_views(path):
    W, H = 1760, 1180
    c = packgen.Canvas(W, H, PAPER)
    c.text(40, 26, "DRAWER CABINET - THREE VIEWS (MM)", 3, INK)
    c.text(40, 60, "1000 x 450 x 900. PANELS 18. FIVE DRAWERS TRAVEL 420. ONE DOOR 0-110 DEG.", 1, INK)
    s = 1.05
    front_view(c, 520, 560, s)
    side_view(c, 1300, 560, s * 0.85)
    door_detail(c, 1300, 900, s * 0.55)
    c.text(40, 1050, "ORIGIN AT FLOOR CENTRE. +Y IS THE FRONT. DRAWERS SLIDE ALONG +Y, DOOR SWINGS ABOUT A VERTICAL AXIS.", 1, INK)
    c.text(40, 1074, "DRAWER FRONTS 440 x 150, TRAY DEPTH 400, TRAY PANELS 18. HANDLES: STEEL TUBES, 14 DIA.", 1, INK)
    with open(path, "wb") as fh:
        fh.write(c.png())


def spec_pdf(path):
    pdf = packgen.PDF(595, 842)

    def heading(y, text):
        pdf.text(56, y, text, 13, bold=True)
        pdf.line(56, y + 6, 539, y + 6, width=0.8)

    pdf.text(56, 56, "DRAWER CABINET - DESIGN PACK", 16, bold=True)
    pdf.text(56, 76, "Furniture prop for an interior scene. Units: millimetres.", 10)
    heading(108, "1. Carcass")
    for i, line in enumerate([
        "Outer 1000 wide x 450 deep x 900 high, panels 18 thick, 60 plinth with four feet.",
        "Parts: carcass_left, carcass_right, carcass_top, carcass_bottom, carcass_back,",
        "   carcass_divider at the centreline, all separate meshes.",
        "Origin at floor centre, +Y towards the front, +Z up.",
    ]):
        pdf.text(64, 130 + 14 * i, line, 9)
    heading(206, "2. Drawers")
    for i, line in enumerate([
        "Five drawers drawer_01..05 in the left bay (x -462..-22), fronts 440 x 150 x 18,",
        "   tray 400 deep with 18 panels, steel handle tubes 320 long, 14 diameter.",
        "Each drawer is a separate mesh parented to an empty slide_01..05.",
        "The slide empty translates along +Y from 0 to 420; nothing else moves.",
        "Fully open, the tray must clear the carcass and the neighbouring drawers.",
    ]):
        pdf.text(64, 228 + 14 * i, line, 9)
    heading(310, "3. Door")
    for i, line in enumerate([
        "One door_right 460 x 750 x 18 covering the right bay, hinged on its outer edge",
        "   by an empty hinge_right at (500, 216, 505).",
        "Rotation is about the vertical axis, 0 to 110 degrees, swinging outwards.",
        "The door must not touch the carcass or the drawer fronts at any angle.",
    ]):
        pdf.text(64, 332 + 14 * i, line, 9)
    heading(406, "4. Materials and lighting")
    for i, line in enumerate([
        "Oak with 2K basecolor, roughness and normal maps, all packed.",
        "Steel handles: metallic 1.0, roughness 0.25-0.35.",
        "Two light collections: light_day (three area lights) and light_night",
        "   (warm key plus cool fill). Both live in the file and can be switched.",
    ]):
        pdf.text(64, 428 + 14 * i, line, 9)
    heading(506, "5. Deliverables and render brief")
    for i, line in enumerate([
        "drawer_cabinet.blend, manifest.json.",
        "render_day.png: cam_front34, 35 mm, 1.6 m from the cabinet centre, 0.70 m above",
        "   the floor, 1600 x 1200, light_day only.",
        "render_night.png: same camera, light_night only, 1600 x 1200.",
        "render_detail.png: cam_detail, 50 mm, 0.60 m from the front, 0.66 m high, aimed at",
        "   drawer_02 pulled out 300 mm, 1600 x 1200, light_day only.",
        "Cycles CPU, 64 samples, denoising, fixed seed.",
    ]):
        pdf.text(64, 528 + 14 * i, line, 9)
    heading(668, "6. Licence")
    pdf.text(64, 690, "Everything in this pack was authored for this task; CC0-1.0.", 9)
    pdf.save(path)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    materials = argv[0]
    solution = argv[1] if len(argv) > 1 else None
    for sub in ("drawings", "spec", "photos", "textures"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    draw_three_views(os.path.join(materials, "drawings", "cabinet_three_views.png"))
    spec_pdf(os.path.join(materials, "spec", "cabinet_spec.pdf"))
    rows = [
        ["part", "size_mm", "material"],
        ["carcass panels", "18 thick, 1000x450x900 outer", "oak, 2K maps"],
        ["drawer front", "440 x 150 x 18", "oak"],
        ["drawer tray", "400 deep, panels 18", "oak"],
        ["drawer handle", "320 long, 14 dia", "steel, metallic 1.0"],
        ["door_right", "460 x 750 x 18", "oak, hinged outer edge"],
        ["plinth feet", "60 high, 44 dia", "steel"],
    ]
    with open(os.path.join(materials, "spec", "parts.csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    packgen.write_xlsx(os.path.join(materials, "spec", "parts.xlsx"), "parts", rows,
                       col_widths=[20, 32, 26])
    if solution:
        import numpy as np
        src = os.path.join(solution, "textures", "wood_basecolor.png")
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(materials, "textures", "wood_basecolor.png"))
        for name, dst in (("render_day.png", "ref_day.png"),
                          ("render_night.png", "ref_night.png"),
                          ("render_detail.png", "ref_detail.png")):
            path = os.path.join(solution, name)
            if os.path.exists(path):
                shutil.copyfile(path, os.path.join(materials, "photos", dst))
    with open(os.path.join(materials, "LICENSE.txt"), "w") as fh:
        fh.write(
            "DRAWER CABINET DESIGN PACK - CC0-1.0\n\n"
            "Drawings, tables and the sample wood texture were authored for this\n"
            "task and are released under CC0-1.0. The reference photographs under\n"
            "photos/ were rendered from the reference model and carry the same\n"
            "licence. Copy, modify and redistribute freely.\n")
    print("materials written to", materials)


if __name__ == "__main__":
    main()
