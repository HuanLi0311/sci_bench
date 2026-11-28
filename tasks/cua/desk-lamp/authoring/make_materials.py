"""Authoring tool: writes the desk-lamp design pack.

    blender -b -P make_materials.py -- <materials_dir> [<solution_dir>]
"""
import csv
import math
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packgen

INK = (26, 28, 34)
DIM = (170, 60, 40)
GREY = (150, 150, 155)
PAPER = (250, 249, 245)
METAL = (196, 199, 205)

TARGETS = [(0.300, 0.350, 0.350), (-0.280, 0.320, 0.340), (0.050, 0.470, 0.360)]
L1, L2 = 0.320, 0.300


def plan(c, ox, oy, s):
    """Desk plan view: x to the right, y upwards on the drawing."""
    def p(x, y):
        return ox + x * s, oy - y * s

    c.rect(*p(-0.50, 0.65), *p(0.70, -0.05), INK, width=1.2)
    c.circle(*p(0, 0), 0.060 * s, INK, fill=METAL)
    c.circle(*p(0, 0), 0.014 * s, INK)
    for i, (tx, ty, tz) in enumerate(TARGETS, start=1):
        px, py = p(tx, ty)
        c.circle(px, py, 0.030 * s, DIM, width=1.4)
        c.circle(px, py, 3, DIM, fill=DIM)
        c.text(px + 10, py - 22, f"T{i}", 2, DIM)
    # reach circles for the two arm links
    c.dashed(*p(-0.62, 0), *p(0.62, 0), GREY)
    c.circle(*p(0, 0), (L1 + L2) * s, GREY, width=0.8)
    c.text(p(-0.52, -0.02)[0], p(-0.52, -0.02)[1] + 10, "R 620 MAX REACH", 1, GREY)

    yd = p(0, -0.05)[1] + 48
    c.line(p(-0.50, 0)[0], yd, p(0.70, 0)[0], yd, DIM, 1.0)
    c.text_center((p(-0.50, 0)[0] + p(0.70, 0)[0]) / 2, yd + 12, "DESK 1200", 2, DIM)


def elevation(c, ox, oy, s):
    def p(r, z):
        return ox + r * s, oy - z * s

    c.line(*p(-0.34, 0), *p(0.70, 0), INK, 1.6)
    c.rect(*p(-0.060, 0.022), *p(0.060, 0), INK, fill=METAL, width=1.1)
    c.rect(*p(-0.015, 0.342), *p(0.015, 0.022), INK, fill=METAL, width=1.0)
    c.rect(*p(-0.012, 0.642), *p(0.012, 0.342), INK, fill=METAL, width=1.0)
    c.text(p(0.05, 0.20)[0], p(0.05, 0.20)[1], "LOWER 320", 1, GREY)
    c.text(p(0.05, 0.46)[0], p(0.05, 0.46)[1], "UPPER 300", 1, GREY)
    for r, z in ((0.030, 0.022), (0.030, 0.342), (0.030, 0.642), (0.030, 0.732)):
        c.circle(*p(0, z), 4, DIM, fill=DIM)
    c.text(p(0.05, 0.70)[0], p(0.05, 0.70)[1], "SHADE 90", 1, GREY)
    hx = p(-0.10, 0)[0]
    c.line(hx, p(0, 0)[1], hx, p(0, 0.732)[1], DIM, 0.9)
    c.text(hx - 66, p(0, 0.36)[1], "732", 2, DIM)
    c.text(ox - 60, oy + 40, "REST POSE: ALL JOINTS AT ZERO, ARM VERTICAL", 1, INK)


def target_table(c, ox, oy):
    c.text(ox, oy, "REACH TARGETS (HEAD PIVOT, METRES)", 2, INK)
    c.text(ox, oy + 30, "FRAME 1  ->  T1", 1, DIM)
    c.text(ox, oy + 50, "FRAME 2  ->  T2", 1, DIM)
    c.text(ox, oy + 70, "FRAME 3  ->  T3", 1, DIM)
    c.text(ox, oy + 100, "T1  ( 0.300,  0.350,  0.120)", 1, INK)
    c.text(ox, oy + 118, "T2  (-0.280,  0.320,  0.120)", 1, INK)
    c.text(ox, oy + 136, "T3  ( 0.050,  0.550,  0.140)", 1, INK)
    c.text(ox, oy + 166, "TOLERANCE 8 MM PER AXIS AT EVERY FRAME", 1, GREY)


def draw_views(path):
    W, H = 1800, 1250
    c = packgen.Canvas(W, H, PAPER)
    c.text(40, 26, "ARTICULATED DESK LAMP - PLAN AND ELEVATION", 3, INK)
    c.text(40, 60, "FOUR JOINTS: YAW, SHOULDER, ELBOW, HEAD. LOWER 320, UPPER 300, SHADE 90.", 1, INK)
    plan(c, 480, 780, 700)
    elevation(c, 1420, 780, 560)
    target_table(c, 60, 1000)
    c.text(40, 1200, "ORIGIN AT THE BASE PIVOT ON THE DESK, +Z UP, +Y AWAY FROM THE SITTER. JOINTS ARE EMPTIES.", 1, INK)
    with open(path, "wb") as fh:
        fh.write(c.png())


def spec_pdf(path):
    pdf = packgen.PDF(595, 842)

    def heading(y, text):
        pdf.text(56, y, text, 13, bold=True)
        pdf.line(56, y + 6, 539, y + 6, width=0.8)

    pdf.text(56, 56, "ARTICULATED DESK LAMP - DESIGN PACK", 16, bold=True)
    pdf.text(56, 76, "Product visualisation. Units: millimetres unless stated.", 10)
    heading(108, "1. Geometry")
    for i, line in enumerate([
        "Base disc 120 diameter, 22 high, on the desk plane z = 0.",
        "Lower arm 320 x 30 x 30, upper arm 300 x 24 x 24, shade 90 long,",
        "   104 at the mouth tapering to 60. Rest pose: every joint at zero, arm vertical,",
        "   top of the shade at 732.",
        "Meshes: base, column, lower_arm, upper_arm, shade, bulb, desk, target_01..03.",
    ]):
        pdf.text(64, 130 + 14 * i, line, 9)
    heading(220, "2. Joints")
    for i, line in enumerate([
        "Four empties, named joint_yaw, joint_shoulder, joint_elbow, joint_head.",
        "joint_yaw at (0, 0, 22) rotates about Z; joint_shoulder sits at the same",
        "   point as its child and rotates about X; joint_elbow at (0, 0, 342);",
        "   joint_head at (0, 0, 642). lower_arm hangs off joint_shoulder,",
        "   upper_arm off joint_elbow, shade and bulb off joint_head.",
        "Do not bake the poses into the mesh: the empties must carry the chain.",
    ]):
        pdf.text(64, 242 + 14 * i, line, 9)
    heading(340, "3. Reach")
    for i, line in enumerate([
        "Action Pose_Reach, keyframes at 1, 2 and 3 on all four joints. At frame 1 the",
        "   head pivot must sit on T1 = (0.300, 0.350, 0.120), frame 2 on",
        "   T2 = (-0.280, 0.320, 0.120), frame 3 on T3 = (0.050, 0.550, 0.140),",
        "   each within 8 mm of the target position. Scene range 1-3.",
        "The arms and shade must stay above the desk (z >= 0) at all three poses and",
        "   must not pass through each other.",
    ]):
        pdf.text(64, 362 + 14 * i, line, 9)
    heading(452, "4. Light")
    for i, line in enumerate([
        "One spot lamp, named lamp_spot, parented to joint_head, 42 degree cone,",
        "   energy 40-60 W at 2700-3200 K, aimed at the frame's target.",
        "With the lamp on, the desk under the target must be clearly brighter than",
        "   with it off: the mean image luminance has to rise by at least 30 percent.",
    ]):
        pdf.text(64, 474 + 14 * i, line, 9)
    heading(548, "5. Deliverables and render brief")
    for i, line in enumerate([
        "desk_lamp.blend, manifest.json.",
        "render_pose_01..03.png: cam_pose, 35 mm, 1.6 m from the lamp base, 0.85 m high,",
        "   1600 x 1200, frames 1, 2 and 3.",
        "render_hero.png: cam_hero, 50 mm, 1600 x 1200, frame 1.",
        "Cycles CPU, 64 samples, denoising, fixed seed. Textures packed.",
    ]):
        pdf.text(64, 570 + 14 * i, line, 9)
    heading(680, "6. Licence")
    pdf.text(64, 702, "Everything in this pack was authored for this task; CC0-1.0.", 9)
    pdf.save(path)


def paint_texture(path, size=1024, seed=17):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    grain = (np.sin(x / size * 60 * np.pi) * 0.5 + 0.5) * 0.35
    speck = rng.random((size, size)).astype(np.float32) * 0.12
    base = np.zeros((size, size, 3), np.float32)
    field = 0.55 + grain * 0.5 + speck
    base[..., 0] = 0.16 + 0.14 * field
    base[..., 1] = 0.34 + 0.22 * field
    base[..., 2] = 0.33 + 0.20 * field
    rgb = (np.clip(base, 0, 1) * 255).astype(np.uint8)
    with open(path, "wb") as fh:
        fh.write(packgen.encode_png(rgb))


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    materials = argv[0]
    solution = argv[1] if len(argv) > 1 else None
    for sub in ("drawings", "spec", "photos", "textures"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    draw_views(os.path.join(materials, "drawings", "lamp_views.png"))
    spec_pdf(os.path.join(materials, "spec", "lamp_spec.pdf"))
    paint_texture(os.path.join(materials, "textures", "lamp_paint.png"))
    rows = [
        ["part", "size_mm", "material"],
        ["base", "dia 120 x 22", "powder-coat paint"],
        ["lower_arm", "320 x 30 x 30", "powder-coat paint"],
        ["upper_arm", "300 x 24 x 24", "powder-coat paint"],
        ["shade", "90 long, 104 to 60", "brushed steel, metallic 1.0"],
        ["bulb", "dia 40", "warm emitter, 2700-3200 K"],
        ["lamp_spot", "spot, 42 deg cone", "40-60 W"],
        ["joint_yaw/shoulder/elbow/head", "empties", "yaw Z, others X"],
    ]
    with open(os.path.join(materials, "spec", "parts.csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    packgen.write_xlsx(os.path.join(materials, "spec", "parts.xlsx"), "parts", rows,
                       col_widths=[30, 24, 30])
    if solution:
        for name, dst in (("render_pose_01.png", "ref_pose_01.png"),
                          ("render_pose_02.png", "ref_pose_02.png"),
                          ("render_pose_03.png", "ref_pose_03.png"),
                          ("render_hero.png", "ref_hero.png")):
            src = os.path.join(solution, name)
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(materials, "photos", dst))
    with open(os.path.join(materials, "LICENSE.txt"), "w") as fh:
        fh.write(
            "ARTICULATED DESK LAMP DESIGN PACK - CC0-1.0\n\n"
            "Drawings, tables, the paint texture and the reference renders were\n"
            "authored for this task and are released under CC0-1.0.\n")
    print("materials written to", materials)


if __name__ == "__main__":
    main()
