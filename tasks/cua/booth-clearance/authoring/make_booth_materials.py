"""Authoring tool: generates the booth material pack.

    python3 make_booth_materials.py <materials_dir>

Drawings in millimetres, 3D scene in metres. Self-authored, CC0.
"""
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon, FancyArrowPatch

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

W, D, H = 6000, 4000, 4000          # booth footprint and height limit, mm
ENTRANCE = 2400
COLUMN = 400
HYD_X = -1200                        # hydrant centre, 1.2 m outside the entrance
BRAND = {"primary": "#1F6F5C", "secondary": "#F2C14E"}

PRODUCTS = [
    ("P1000", 300, 200, 250, 12, "front"),
    ("P2000", 380, 260, 320, 21, "front"),
    ("P3000", 460, 300, 380, 32, "front"),
]
FURNITURE = [
    ("cabinet_01", 1200, 500, 2000),
    ("cabinet_02", 1200, 500, 2000),
    ("counter", 1800, 600, 1000),
    ("plinth_01", 800, 800, 400),
    ("plinth_02", 800, 800, 400),
    ("plinth_03", 800, 800, 400),
]


def dim(ax, p0, p1, text, off=0.0, vertical=False):
    ax.annotate("", xy=p1, xytext=p0,
                arrowprops=dict(arrowstyle="<->", color="#222", lw=1.2,
                                shrinkA=0, shrinkB=0))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    if vertical:
        ax.text(mx + off, my, text, rotation=90, ha="center", va="center",
                fontsize=10, backgroundcolor="white")
    else:
        ax.text(mx, my + off, text, ha="center", va="center",
                fontsize=10, backgroundcolor="white")


def make_plan(out_dir):
    fig, ax = plt.subplots(figsize=(13, 9), dpi=200)
    ax.set_title("EXHIBITION BOOTH — FLOOR PLAN (all dimensions mm, 1:50)",
                 fontsize=14, fontweight="bold")
    # shell
    ax.add_patch(Rectangle((0, 0), W, D, fill=False, lw=3, ec="#111"))
    # entrance on the left 4 m side, centred
    ax.plot([0, 0], [0, (D - ENTRANCE) / 2], lw=0, color="white")
    ax.add_patch(Rectangle((0, (D - ENTRANCE) / 2), 0, ENTRANCE,
                           fill=True, fc="white", ec="white"))
    ax.plot([0, 0], [(D - ENTRANCE) / 2, (D + ENTRANCE) / 2], color="white", lw=5)
    ax.annotate("", xy=(0, (D - ENTRANCE) / 2), xytext=(0, (D + ENTRANCE) / 2),
                arrowprops=dict(arrowstyle="<->", color="#2c7", lw=2))
    ax.text(-350, D / 2, "ENTRANCE\n2400", color="#2c7", ha="center",
            va="center", fontsize=11, fontweight="bold")
    # column at the back-right corner
    ax.add_patch(Rectangle((W - COLUMN - 20, 20), COLUMN, COLUMN,
                           fc="#999", ec="#333", lw=1.5))
    ax.text(W - COLUMN / 2 - 20, -180, "column 400 x 400", ha="center", fontsize=9)
    # hydrant outside the entrance, 1.2 m clear
    ax.add_patch(Circle((HYD_X, D / 2), 60, fc="#c0392b", ec="#7b241c"))
    ax.add_patch(Circle((HYD_X, D / 2), 1200, fill=False, ls="--", ec="#c0392b", lw=1.6))
    ax.text(HYD_X - 80, D / 2 + 1350, "fire hydrant\nØ1200 clear", color="#c0392b",
            fontsize=9, ha="center")
    # furniture footprints, placed as the reference does
    layout = {
        "cabinet_01": (1800, -1750, 1200, 500),
        "cabinet_02": (-500, 1750, 1200, 500),
        "counter": (-2200, -1500, 1800, 600),
        "plinth_01": (2200, -1200, 800, 800),
        "plinth_02": (2200, 0, 800, 800),
        "plinth_03": (2200, 1200, 800, 800),
    }
    for name, (cx, cy, w, d) in layout.items():
        x0, y0 = cx + W / 2 - w / 2, cy + D / 2 - d / 2
        fc = "#d9e8e3" if name.startswith("cabinet") else ("#f6e7b8" if name.startswith("counter") else "#e8e8e8")
        ax.add_patch(Rectangle((x0, y0), w, d, fc=fc, ec="#333", lw=1.2))
        ax.text(x0 + w / 2, y0 + d / 2, name.replace("_", " "), ha="center",
                va="center", fontsize=8)
    # products on the plinths
    for i, (nm, pw, pd, ph, kg, _) in enumerate(PRODUCTS):
        cx = 2200
        cy = [-1200, 0, 1200][i]
        ax.add_patch(Rectangle((cx + W / 2 - pw / 2, cy + D / 2 - pd / 2),
                               pw, pd, fc="#1F6F5C", ec="#123", lw=1))
        ax.text(cx + W / 2, cy + D / 2 + 260, nm, ha="center", fontsize=8,
                color="#1F6F5C", fontweight="bold")
    # aisle width callouts
    dim(ax, (0, -500), (W, -500), "6000", off=-180)
    dim(ax, (W + 450, 0), (W + 450, D), "4000", off=170, vertical=True)
    ax.annotate("main aisle >= 900", xy=(400, 900), xytext=(1200, 3300),
                fontsize=9, arrowprops=dict(arrowstyle="->", lw=1))
    ax.annotate("exit wall: entrance side", xy=(0, 3400), xytext=(500, 3800),
                fontsize=9, arrowprops=dict(arrowstyle="->", lw=1))
    ax.set_xlim(-2000, W + 900)
    ax.set_ylim(-900, D + 700)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(os.path.join(out_dir, "booth_floor_plan.png"), facecolor="white")
    fig.savefig(os.path.join(out_dir, "booth_floor_plan.pdf"), facecolor="white")
    plt.close(fig)


def make_xlsx(path, headers, rows, widths):
    wb = Workbook()
    ws = wb.active
    ws.title = "data"
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    wb.save(path)


def make_tables(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    make_xlsx(os.path.join(out_dir, "product_sizes.xlsx"),
              ["model", "width_mm", "depth_mm", "height_mm", "weight_kg", "face_to"],
              [list(p) for p in PRODUCTS],
              [12, 12, 12, 12, 12, 12])
    make_xlsx(os.path.join(out_dir, "furniture_list.xlsx"),
              ["name", "width_mm", "depth_mm", "height_mm"],
              [list(f) for f in FURNITURE],
              [16, 12, 12, 12])


def make_brand(path):
    doc = SimpleDocTemplate(path, pagesize=A4)
    st = getSampleStyleSheet()
    story = [Paragraph("Booth brand sheet", st["Heading1"]),
             Paragraph("Primary colour is used for the back wall and the product "
                       "plinths' accent band; secondary colour for the counter "
                       "front and wayfinding.", st["BodyText"]),
             Spacer(1, 8 * mm)]
    t = Table([["role", "hex", "swatch"],
               ["primary", BRAND["primary"], ""],
               ["secondary", BRAND["secondary"], ""]],
              colWidths=[40 * mm, 40 * mm, 40 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (2, 1), (2, 1), colors.HexColor(BRAND["primary"])),
        ("BACKGROUND", (2, 2), (2, 2), colors.HexColor(BRAND["secondary"])),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
    ]))
    story += [t, Spacer(1, 6 * mm),
              Paragraph("Logo: use logo.svg on the back wall, 900 mm wide, centred "
                        "at 2600 mm above the floor.", st["BodyText"])]
    doc.build(story)


def make_logo(path):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="300" viewBox="0 0 900 300">
  <rect width="900" height="300" fill="none"/>
  <polygon points="40,150 160,40 280,150 160,260" fill="{BRAND['primary']}"/>
  <polygon points="160,90 220,150 160,210 100,150" fill="{BRAND['secondary']}"/>
  <text x="320" y="185" font-family="Helvetica" font-size="96" font-weight="bold"
        fill="{BRAND['primary']}">VOLTA</text>
</svg>
'''
    with open(path, "w") as fh:
        fh.write(svg)


def make_logo_png(path):
    """Raster version of the logo, for use as a decal texture."""
    fig, ax = plt.subplots(figsize=(9, 3), dpi=200)
    ax.add_patch(Polygon([[0.4, 1.5], [1.6, 0.4], [2.8, 1.5], [1.6, 2.6]],
                         closed=True, fc=BRAND["primary"]))
    ax.add_patch(Polygon([[1.6, 0.9], [2.2, 1.5], [1.6, 2.1], [1.0, 1.5]],
                         closed=True, fc=BRAND["secondary"]))
    ax.text(3.2, 1.5, "VOLTA", fontsize=64, fontweight="bold",
            color=BRAND["primary"], va="center")
    ax.set_xlim(0, 9)
    ax.set_ylim(0, 3)
    ax.axis("off")
    fig.subplots_adjust(0, 0, 1, 1)
    fig.savefig(path, transparent=True)
    plt.close(fig)


def make_constraints(path):
    doc = SimpleDocTemplate(path, pagesize=A4)
    st = getSampleStyleSheet()
    body = st["BodyText"]
    story = [Paragraph("Booth constraints", st["Heading1"]),
             Paragraph("All distances are clear distances between solid geometry, "
                       "measured in the horizontal plane unless stated.", body),
             Spacer(1, 4 * mm)]
    rows = [
        ["item", "requirement"],
        ["Envelope", "6.0 x 4.0 m footprint, 4.0 m height limit"],
        ["Entrance", "2.4 m wide, centred on the 4 m short side"],
        ["Main aisle", "clear width >= 0.9 m between furniture and walls"],
        ["Fire hydrant", "nothing within a 1.2 m radius of the hydrant centre, "
                         "which sits 1.2 m outside the entrance"],
        ["Sight lines", "all three products visible from the entrance camera "
                        "without occlusion by cabinets or the column"],
        ["Floor load", "500 kg/m2"],
        ["Triangle budget", "<= 300k triangles for the whole file"],
        ["Deliverables", "booth.blend, render_entrance.png 1920x1080, "
                         "render_top.png 2048x1536 orthographic over 6 x 4 m, "
                         "manifest.json with every asset licensed"],
    ]
    t = Table(rows, colWidths=[32 * mm, 130 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story += [t]
    doc.build(story)


def write_licence(path):
    with open(path, "w") as fh:
        fh.write("""Booth material pack — CC0-1.0
============================

Floor plan, product and furniture tables, brand sheet, logo, constraints and
reference photographs were all produced for this benchmark task and are
released under CC0-1.0. Photographs are renders of the reference booth model.
""")


def main():
    materials = sys.argv[1]
    for sub in ("drawings", "tables", "brand", "photos"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    make_plan(os.path.join(materials, "drawings"))
    make_tables(os.path.join(materials, "tables"))
    make_brand(os.path.join(materials, "brand", "brand_sheet.pdf"))
    make_logo(os.path.join(materials, "brand", "logo.svg"))
    make_logo_png(os.path.join(materials, "brand", "logo.png"))
    make_constraints(os.path.join(materials, "drawings", "constraints.pdf"))
    write_licence(os.path.join(materials, "LICENSE.txt"))
    print("booth materials written to", materials)


if __name__ == "__main__":
    main()
