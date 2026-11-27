"""Authoring tool: writes the spider design pack into environment/materials.

    python3 make_materials.py <materials_dir> [<solution_dir>]

Pure standard library (see packgen.py). The geometry comes from spider_spec.py,
so the drawing, the bone table and the reference .blend cannot disagree.
"""
import csv
import math
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import packgen
import spider_spec as S

INK = (24, 24, 26)
DIM = (170, 60, 40)
GREY = (150, 150, 155)
PAPER = (250, 249, 245)


def mm(v):
    return v * 1000.0


# --------------------------------------------------------------------------
# texture
# --------------------------------------------------------------------------
def chitin_texture(size=1024, seed=4207):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    base = np.zeros((size, size, 3), np.float32)
    # warped cellular mottling
    warp = []
    for octave, amp in ((3.0, 1.0), (7.0, 0.55), (17.0, 0.28), (41.0, 0.12)):
        phase = rng.uniform(0, 2 * np.pi, 5)
        v = (np.sin(x / size * octave * 2 * np.pi + phase[0]) *
             np.cos(y / size * octave * 2 * np.pi + phase[1]) +
             np.sin((x + y) / size * octave * 1.7 * np.pi + phase[2]))
        warp.append(amp * v)
    field = np.sum(warp, axis=0)
    field = (field - field.min()) / (field.max() - field.min())
    highlight = np.clip(field ** 2.2, 0, 1)
    base[..., 0] = 0.30 + 0.34 * field + 0.10 * highlight
    base[..., 1] = 0.22 + 0.26 * field + 0.07 * highlight
    base[..., 2] = 0.15 + 0.18 * field + 0.05 * highlight
    # sparse darker spots
    spots = rng.random((28, 2)) * size
    for sx, sy in spots:
        r = rng.uniform(8, 26)
        d2 = (x - sx) ** 2 + (y - sy) ** 2
        mask = np.exp(-d2 / (2 * r * r))
        base *= (1 - 0.28 * mask)[..., None]
    rgb = np.clip(base, 0, 1) * 255
    return rgb.astype(np.uint8)


def write_texture(materials):
    path = os.path.join(materials, "textures")
    os.makedirs(path, exist_ok=True)
    rgb = chitin_texture()
    with open(os.path.join(path, "chitin_basecolor.png"), "wb") as fh:
        fh.write(packgen.encode_png(rgb))


# --------------------------------------------------------------------------
# three-view drawing
# --------------------------------------------------------------------------
def dim_line(c, x0, y0, x1, y1, label, offset=16, vertical=False, colour=DIM):
    c.line(x0, y0, x1, y1, colour, 1.0)
    tick = 7
    if not vertical:
        c.line(x0, y0 - tick, x0, y0 + tick, colour, 1.0)
        c.line(x1, y1 - tick, x1, y1 + tick, colour, 1.0)
        c.text_center((x0 + x1) / 2, y0 + offset, label, 2, colour)
    else:
        c.line(x0 - tick, y0, x0 + tick, y0, colour, 1.0)
        c.line(x1 - tick, y1, x1 + tick, y1, colour, 1.0)
        c.text(x0 + offset, (y0 + y1) / 2 - 7, label, 2, colour)


def draw_three_views(path):
    W, H = 1760, 1440
    c = packgen.Canvas(W, H, PAPER)
    c.text(40, 26, "CARTOON SPIDER - THREE VIEWS  (MM)", 3, INK)
    c.text(40, 60, "ORTHOGRAPHIC. JOINT CENTRES MARKED. BODY LENGTH 180, LEG SPAN 420, STANCE HEIGHT 120.", 1, INK)

    scale = 1.35  # px per mm

    def make_projector(ox, oy, a_index, b_index, a_sign=1.0, b_sign=1.0):
        def project(p):
            return ox + mm(p[a_index]) * a_sign * scale, oy - mm(p[b_index]) * b_sign * scale
        return project

    top = make_projector(430, 430, 0, 1)
    front = make_projector(430, 1150, 0, 2)
    side = make_projector(1290, 1150, 1, 2)

    for title, (tx, ty) in (("TOP (XY)  X RIGHT, Y FORWARD", (300, 96)),
                            ("FRONT (XZ)  VIEW ALONG -Y", (300, 880)),
                            ("SIDE (YZ)  VIEW ALONG +X", (1150, 880))):
        c.text(tx, ty, title, 2, INK)
        c.line(tx, ty + 22, tx + 330, ty + 22, GREY, 1.0)

    def body_boxes(project):
        head = [(-0.032, -0.010), (0.032, -0.010), (0.032, 0.090), (-0.032, 0.090)]
        abd = [(-0.035, -0.090), (0.035, -0.090), (0.035, -0.010), (-0.035, -0.010)]
        z_head = (0.102, 0.140)
        z_abd = (0.092, 0.148)
        for pts, (z0, z1) in ((head, z_head), (abd, z_abd)):
            low = [(x, y, z0) for x, y in pts]
            high = [(x, y, z1) for x, y in pts]
            for a, b in zip(low, low[1:] + low[:1]):
                c.line(*project(a), *project(b), INK, 1.2)
            for a, b in zip(high, high[1:] + high[:1]):
                c.line(*project(a), *project(b), INK, 1.2)
            for a, b in zip(low, high):
                c.line(*project(a), *project(b), GREY, 0.8)

    body_boxes(top)
    body_boxes(front)
    body_boxes(side)

    for leg in range(1, 9):
        _deg, attach, ctail, ftail, foot = S.leg_points(leg)
        for project in (top, front, side):
            chain = [attach, ctail, ftail, foot]
            for a, b in zip(chain, chain[1:]):
                c.line(*project(a), *project(b), INK, 1.1)
            for joint in chain:
                px, py = project(joint)
                c.circle(px, py, 3.4, INK, fill=(255, 255, 255), width=1.0)
        px, py = top(attach)
        c.text(px + 10, py - 26, f"{leg:02d}", 1, GREY)
        px, py = top(foot)
        c.circle(px, py, 5.0, DIM, fill=(255, 255, 255), width=1.2)

    # --- dimensions ----------------------------------------------------
    def hdim(x0, x1, y, label, colour=DIM):
        c.line(x0, y, x1, y, colour, 1.0)
        for x in (x0, x1):
            c.line(x, y - 8, x, y + 8, colour, 1.0)
        c.text_center((x0 + x1) / 2, y + 14, label, 2, colour)

    def vdim(x, y0, y1, label, colour=DIM):
        c.line(x, y0, x, y1, colour, 1.0)
        for y in (y0, y1):
            c.line(x - 8, y, x + 8, y, colour, 1.0)
        c.text(x - 82, (y0 + y1) / 2 - 6, label, 2, colour)

    left = top((-0.210, 0.04, 0.002))
    right = top((0.210, 0.04, 0.002))
    y_dim = 790
    hdim(left[0], right[0], y_dim, "LEG SPAN 420")
    for x in (left[0], right[0]):
        c.dashed(x, top((0, 0.04, 0))[1] + 30, x, y_dim - 10, GREY)

    back = top((0, -0.090, 0))
    fronty = top((0, 0.090, 0))
    vdim(back[0] - 95, back[1], fronty[1], "BODY 180")

    hx = 300
    y0 = front((0, 0, 0.0))[1]
    y1 = front((0, 0, 0.120))[1]
    vdim(hx, y0, y1, "120")
    c.dashed(front((-0.04, 0, 0.120))[0], y1, hx, y1, GREY)
    c.dashed(front((-0.04, 0, 0))[0], y0, hx, y0, GREY)

    wx0 = front((-0.032, 0, 0.140))[0]
    wx1 = front((0.032, 0, 0.140))[0]
    hdim(wx0, wx1, front((0, 0, 0.140))[1] - 40, "64")

    # leg segment lengths called out on the side view
    sx = 1150
    c.text(sx, 918, "SEGMENTS 30 / 74 / 74 (HORIZONTAL PROJECTION)", 1, INK)
    c.text(sx, 942, "FOOT TIP Z = 1.5. ATTACH Z = 115.", 1, INK)

    c.text(40, 1360, "JOINT CENTRES: ATTACH, COXA TAIL, FEMUR TAIL, FOOT TIP (RED). SEGMENTS ARE RIGID TUBES.", 1, INK)
    c.text(40, 1384, "LEFT LEGS MIRROR RIGHT LEGS ABOUT X=0. DRIVING DIRECTIONS: +45, +20, 0, -35 DEG (RIGHT SIDE).", 1, INK)
    with open(path, "wb") as fh:
        fh.write(c.png())
    return c


def draw_phase(path):
    cols, rows = 24, 8
    cell_w, cell_h = 42, 40
    left, top = 190, 130
    W, H = left + cols * cell_w + 60, top + rows * cell_h + 170
    c = packgen.Canvas(W, H, PAPER)
    c.text(30, 26, "STEP TIMING - 24 FRAME CYCLE", 3, INK)
    c.text(30, 62, "DARK = STANCE 18 FRAMES (75%). LIGHT = SWING 6 FRAMES. GROUP B = GROUP A + 12 FRAMES.", 1, INK)
    for t in range(cols):
        if t % 6 == 0:
            c.text(left + t * cell_w + 4, top - 24, str(t), 1, GREY)
    c.text(left + cols * cell_w + 10, top - 24, "CYCLE", 1, GREY)
    for leg in range(1, 9):
        y = top + (leg - 1) * cell_h
        c.text(30, y + 12, f"LEG_{leg:02d}  P{S.PHASES[leg]:02d}", 1, INK)
        for t in range(cols):
            x = left + t * cell_w
            stance = S.is_stance(leg, t)
            fill = (92, 96, 104) if stance else (222, 214, 190)
            c.rect(x, y, x + cell_w, y + cell_h, (40, 40, 44), fill, 1.0)
            if not stance:
                c.text(x + 14, y + 15, "S", 1, (90, 80, 50))
    c.text(30, top + rows * cell_h + 24,
           "TOUCHDOWN = FIRST STANCE FRAME. SWING RUNS THE 6 FRAMES BEFORE THE NEXT TOUCHDOWN.", 1, INK)
    c.text(30, top + rows * cell_h + 48,
           "AT ANY FRAME EXACTLY TWO FEET SWING; THE OTHER SIX ARE PLANTED.", 1, INK)
    with open(path, "wb") as fh:
        fh.write(c.png())


# --------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------
def write_tables(materials):
    spec_dir = os.path.join(materials, "spec")
    os.makedirs(spec_dir, exist_ok=True)
    rows = [["bone", "parent", "head_x_mm", "head_y_mm", "head_z_mm",
             "tail_x_mm", "tail_y_mm", "tail_z_mm", "length_mm", "roll"]]
    for name, parent, head, tail, _r, deg in S.bone_table():
        length = math.dist(head, tail) * 1000.0
        roll = "align_roll +Z" if name != "body" else "-"
        rows.append([name, parent] + [round(mm(v), 2) for v in head]
                    + [round(mm(v), 2) for v in tail] + [round(length, 2), roll])
    with open(os.path.join(spec_dir, "bone_spec.csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(rows)
    packgen.write_xlsx(os.path.join(spec_dir, "bone_spec.xlsx"), "bones", rows,
                       col_widths=[18, 18, 10, 10, 10, 10, 10, 10, 10, 14])

    gait = [["leg", "group", "phase_offset", "touchdown_frame", "stance_frames",
             "swing_frames", "swing_start_frame", "swing_end_frame"]]
    for leg in range(1, 9):
        p = S.PHASES[leg]
        group = "A" if leg % 2 == 1 else "B"
        gait.append([f"leg_{leg:02d}", group, p, p + 1, 18, 6, p + 19, p + 24])
    with open(os.path.join(spec_dir, "gait_timing.csv"), "w", newline="") as fh:
        csv.writer(fh).writerows(gait)


def write_spec_pdf(materials):
    spec_dir = os.path.join(materials, "spec")
    os.makedirs(spec_dir, exist_ok=True)
    pdf = packgen.PDF(595, 842)

    def heading(y, text):
        pdf.text(56, y, text, 13, bold=True)
        pdf.line(56, y + 6, 539, y + 6, width=0.8)

    pdf.text(56, 56, "CARTOON SPIDER - DESIGN PACK", 17, bold=True)
    pdf.text(56, 76, "Game character, 25-bone rig, 24-frame closed-loop gait. Units: millimetres.", 10)
    heading(108, "1. Body")
    for i, line in enumerate([
        "Head-thorax: 64 wide x 100 long x 38 high, centred on y = +40, z = 102..140.",
        "Abdomen: 70 wide x 80 long x 56 high, centred on y = -50, z = 92..148.",
        "Overall body length 180 (y = -90..+90). Stance height 120 (body bone head z).",
        "Eight legs attach on the thorax at radius 32 from (0, 40), z = 115.",
    ]):
        pdf.text(64, 130 + 14 * i, line, 9)
    heading(206, "2. Legs")
    for i, line in enumerate([
        "Each leg: coxa 30, femur 74, tibia 74 (horizontal projection), three rigid segments.",
        "Right legs point at +45, +20, 0, -35 degrees from +X; left legs mirror about x = 0.",
        "Foot tip radius is 210 from (0, 40), so legs 05 and 06 give the 420 span.",
        "Joint heights: attach 115, coxa tail 112, femur tail 66, foot tip 1.5.",
        "Exact head/tail coordinates per bone are in bone_spec.csv / bone_spec.xlsx.",
    ]):
        pdf.text(64, 228 + 14 * i, line, 9)
    heading(310, "3. Rig")
    for i, line in enumerate([
        "Armature object rig_spider, 25 deform bones, body is the root.",
        "body -> leg_NN_coxa -> leg_NN_femur -> leg_NN_tibia, names exactly as in bone_spec.",
        "Leg bones roll so local +Z points to world +Z. Rotation quaternions, not Euler.",
        "Meshes: body_head, body_abdomen, and one mesh per segment leg_NN_coxa/femur/tibia.",
    ]):
        pdf.text(64, 332 + 14 * i, line, 9)
    heading(392, "4. Gait")
    for i, line in enumerate([
        "24-frame cycle, alternating tetrapod. Stance is 75 percent (18 frames), swing 6 frames.",
        "Phases: legs 01/03/05/07 at 0/6/12/18; legs 02/04/06/08 at 12/18/0/6.",
        "Touchdown is the first stance frame; swing is the six frames before the next touchdown.",
        "Stance feet stay planted (<= 5 mm drift). Swing feet lift at least 15 mm.",
        "Frame 1 and frame 25 must be identical; scene playback 1-24.",
    ]):
        pdf.text(64, 414 + 14 * i, line, 9)
    heading(474, "5. Deliverables and render brief")
    for i, line in enumerate([
        "spider.blend (packed), spider.blend unit scale 1.0, scene fps 24.",
        "render_pose_01..04.png: cam_side, 50 mm, 0.75 m from the body centre, height 0.13 m,",
        "  960 x 540, frames 1 / 10 / 18 / 21.",
        "render_top.png: cam_top, orthographic, 0.50 x 0.50 m coverage, 960 x 960, frame 1.",
        "Cycles CPU, 64 samples, denoising, fixed seed. Cameras named cam_side and cam_top.",
        "manifest.json lists every asset with source and licence.",
    ]):
        pdf.text(64, 496 + 14 * i, line, 9)
    heading(586, "6. Licence")
    for i, line in enumerate([
        "All drawings, tables and textures in this pack were authored for this task.",
        "Release: CC0-1.0. See LICENSE.txt.",
    ]):
        pdf.text(64, 608 + 14 * i, line, 9)
    pdf.save(os.path.join(spec_dir, "spider_spec.pdf"))


# --------------------------------------------------------------------------
def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    materials = argv[0]
    solution = argv[1] if len(argv) > 1 else None
    for sub in ("drawings", "spec", "poses", "textures"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    write_texture(materials)
    draw_three_views(os.path.join(materials, "drawings", "spider_three_views.png"))
    draw_phase(os.path.join(materials, "spec", "gait_phase.png"))
    write_tables(materials)
    write_spec_pdf(materials)
    if solution:
        for i in range(1, 5):
            src = os.path.join(solution, f"render_pose_{i:02d}.png")
            if os.path.exists(src):
                shutil.copyfile(src, os.path.join(materials, "poses", f"key_pose_{i:02d}.png"))
    with open(os.path.join(materials, "LICENSE.txt"), "w") as fh:
        fh.write(
            "CARTOON SPIDER DESIGN PACK - CC0-1.0\n\n"
            "Every file in this pack was authored for this task and is released\n"
            "under CC0-1.0. You may copy, modify and redistribute it, including\n"
            "commercially, without attribution.\n\n"
            "Files: drawings/spider_three_views.png, spec/*, poses/*, textures/*\n")
    print("materials written to", materials)


if __name__ == "__main__":
    main()
