"""Authoring tool: rainroom object list, plan, material/lighting brief, photos."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm

W, D, H = 4200, 3600, 2800

OBJECTS = [
    ("rug", 2600, 2000, 12, 0, 200, 6),
    ("sofa", 850, 1900, 750, -1450, 550, 420),
    ("sofa_back", 220, 1900, 500, -1750, 550, 620),
    ("coffee_table", 1200, 700, 50, 100, 350, 360),
    ("side_table", 450, 450, 40, -1350, -900, 280),
    ("side_table_leg", 60, 60, 280, -1350, -900, 140),
    ("floor_lamp", 40, 40, 1800, 1550, 1300, 900),
    ("floor_lamp_shade", 360, 360, 280, 1550, 1300, 1720),
    ("table_lamp", 100, 100, 220, -1350, -900, 420),
    ("bookshelf", 350, 1500, 1900, 1850, 100, 950),
    ("books_1", 120, 160, 300, 1830, -350, 350),
    ("books_2", 120, 160, 280, 1830, -150, 750),
    ("books_3", 120, 160, 260, 1830, 50, 1150),
    ("books_4", 120, 160, 240, 1830, 250, 1550),
    ("vase_01", 140, 140, 220, 150, 350, 500),
    ("vase_02", 100, 100, 160, 350, 300, 470),
    ("mug_01", 80, 80, 90, 500, 450, 410),
    ("mug_02", 80, 80, 90, 620, 400, 410),
    ("tray", 320, 320, 20, 300, 550, 390),
    ("candle_01", 60, 60, 100, 250, 550, 450),
    ("candle_02", 56, 56, 80, 370, 550, 440),
    ("bottle", 90, 90, 180, 50, 200, 470),
    ("plant_pot", 320, 320, 320, 1700, -1100, 180),
    ("plant_leaves", 420, 420, 550, 1700, -1100, 620),
    ("cushion_01", 160, 400, 400, -1550, 100, 680),
    ("cushion_02", 160, 400, 400, -1550, 850, 680),
]


def make_objects(path):
    wb = Workbook()
    ws = wb.active
    ws.append(["name", "width_mm", "depth_mm", "height_mm", "x_mm", "y_mm", "z_mm"])
    for row in OBJECTS:
        ws.append(list(row))
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 20
    wb.save(path)


def make_plan(path):
    fig, ax = plt.subplots(figsize=(11, 9), dpi=200)
    ax.set_title("RAINROOM — PLAN 4200 x 3600, height 2800 (mm)", fontsize=13,
                 fontweight="bold")
    ax.add_patch(Rectangle((0, 0), W, D, fill=False, lw=3))
    ax.add_patch(Rectangle((W - 120, D / 2 - 600), 40, 1200, fc="#9cc", ec="#367"))
    ax.text(W - 260, D / 2 + 700, "window 1200x1400", ha="center", fontsize=9)
    ax.add_patch(Rectangle((W / 2 - 450, 0), 900, 40, fc="#ccc", ec="#333"))
    ax.text(W / 2, -220, "door 900", ha="center", fontsize=9)
    for name, w, d, h, x, y, z in OBJECTS:
        if name in ("table_leg_1",):
            continue
        ax.add_patch(Rectangle((x + W / 2 - w / 2, y + D / 2 - d / 2), w, d,
                               fc="#eee", ec="#666", alpha=0.9))
        ax.text(x + W / 2, y + D / 2, name.replace("_", "\n"), ha="center",
                va="center", fontsize=6)
    ax.set_xlim(-400, W + 400)
    ax.set_ylim(-500, D + 500)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def make_spec(path):
    doc = SimpleDocTemplate(path, pagesize=A4)
    st = getSampleStyleSheet()
    body = st["BodyText"]
    rows = [["surface", "requirement"],
            ["glass", "window pane and bottle: real transmission or alpha < 0.5, "
                      "not a grey solid"],
            ["ceramic", "vases, mugs, candles: roughness 0.15-0.3, no metal"],
            ["linen", "sofa, cushions, curtains, shade: roughness >= 0.8"],
            ["walnut", "table and shelf: brown albedo, roughness 0.35-0.5"],
            ["copper", "tray, wall art: metallic 1.0"],
            ["rain", "night glass carries droplets or streaks; morning has none"]]
    t = Table(rows, colWidths=[26 * mm, 130 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story = [Paragraph("Rainroom — material and lighting brief", st["Heading1"]),
             t, Spacer(1, 5 * mm),
             Paragraph("Lighting", st["Heading2"]),
             Paragraph("Two collections, one scene: <b>light_night</b> (cool window "
                       "glow, warm practicals, rain on the glass) and "
                       "<b>light_morning</b> (warm low sun, dry glass, brighter). "
                       "Both are switched by hiding one collection at render time; "
                       "the same camera renders both images.", body),
             Spacer(1, 3 * mm),
             Paragraph("Night render: mean luminance 0.10-0.32. Morning render: "
                       "0.55-0.80 and at least 0.02 warmer in R-B, and at least "
                       "0.25 brighter than the night render.", body)]
    doc.build(story)


def main():
    materials = sys.argv[1]
    for sub in ("tables", "drawings", "spec"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    make_objects(os.path.join(materials, "tables", "objects.xlsx"))
    make_plan(os.path.join(materials, "drawings", "room_plan.png"))
    make_spec(os.path.join(materials, "spec", "material_spec.pdf"))
    with open(os.path.join(materials, "LICENSE.txt"), "w") as fh:
        fh.write("Rainroom pack — CC0-1.0, authored for this benchmark task.\n")
    print("rainroom materials written")


if __name__ == "__main__":
    main()
