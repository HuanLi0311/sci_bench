"""Authoring tool: chair material pack (hinge layout, size table, states, spec)."""
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
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

HINGES = [("hinge_01", -280, 0, 225), ("hinge_02", 280, 0, 225),
          ("hinge_03", -280, 270, 430), ("hinge_04", 0, 270, 475)]
W, D, H = 620, 580, 820


def make_layout(path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), dpi=200)
    ax = axes[0]
    ax.set_title("SIDE — hinge layout (mm, 1:5)", fontsize=13, fontweight="bold")
    # side silhouette
    ax.add_patch(Rectangle((0, 0), D, 450, fill=False, lw=1.2, ls="--", ec="#888"))
    # scissor bars: (y0,z0) -> (y1,z1) with y measured from the front edge
    for s in (+1, -1):
        ax.plot([0, D], [0, 450], lw=3, color="#4a6fa5" if s < 0 else "#b5651d")
    ax.plot([0, D], [0, 450], lw=1, color="black")
    ax.plot([0, D], [450, 0], lw=3, color="#b5651d", alpha=0.0)
    for name, x, y, z in HINGES:
        yy = y + D / 2
        ax.plot([yy], [z], "o", ms=9, mfc="#e74c3c", mec="#7b241c")
        ax.annotate(name, (yy, z), textcoords="offset points", xytext=(8, 8), fontsize=9)
    ax.text(D / 2, -70, "590", ha="center", fontsize=9)
    ax.set_xlim(-120, D + 120)
    ax.set_ylim(-150, 560)
    ax.set_aspect("equal")
    ax.axis("off")

    ax = axes[1]
    ax.set_title("FOLDED — 90 mm pack", fontsize=13, fontweight="bold")
    ax.add_patch(Rectangle((0, 0), 90, 900, fc="#eee", ec="#333"))
    ax.text(45, 950, "thickness 90", ha="center", fontsize=10)
    ax.annotate("", xy=(0, 900), xytext=(90, 900),
                arrowprops=dict(arrowstyle="<->", lw=1.2))
    ax.set_xlim(-100, 200)
    ax.set_ylim(-80, 1050)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    plt.close(fig)


def make_tables(out_dir):
    wb = Workbook()
    ws = wb.active
    ws.title = "sizes"
    ws.append(["item", "value_mm"])
    for k, v in (("seat height", 450), ("width", W), ("depth", D),
                 ("height", H), ("folded thickness", 90),
                 ("seat width", 500), ("seat depth", 560)):
        ws.append([k, v])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 12
    wb.save(os.path.join(out_dir, "chair_sizes.xlsx"))

    wb = Workbook()
    ws = wb.active
    ws.title = "hinges"
    ws.append(["name", "x_mm", "y_mm", "z_mm", "range_deg"])
    for name, x, y, z in HINGES:
        ws.append([name, x, y, z, "0-180"])
    for c in ws[1]:
        c.font = Font(bold=True)
    wb.save(os.path.join(out_dir, "hinge_layout.xlsx"))


def make_states(path):
    doc = SimpleDocTemplate(path, pagesize=A4)
    st = getSampleStyleSheet()
    body = st["BodyText"]
    story = [Paragraph("Folding states", st["Heading1"]),
             Paragraph("Frame 0 is the unfolded state, frame 60 the folded state, "
                       "24 fps, 60 frames.", body), Spacer(1, 4 * mm)]
    rows = [["state", "observable criterion"],
            ["unfolded", "four legs on the floor, seat horizontal, back upright"],
            ["half", "legs part-folded, seat lifted, back tipped"],
            ["folded", "everything in one plane, pack thickness 90 mm"],
            ["locked", "unfolded, lock pin engaged between seat and frame"]]
    t = Table(rows, colWidths=[30 * mm, 120 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [t, Spacer(1, 4 * mm),
              Paragraph("The fold must be driven by the four hinges. Legs stay "
                        "connected through hinge_01 and hinge_02; the seat pivots "
                        "on hinge_03 and the back on hinge_04. No part may pass "
                        "through another at any frame.", body)]
    doc.build(story)


def write_licence(path):
    with open(path, "w") as fh:
        fh.write("Folding chair pack — CC0-1.0, authored for this benchmark task.\n")


def main():
    materials = sys.argv[1]
    for sub in ("drawings", "tables", "photos"):
        os.makedirs(os.path.join(materials, sub), exist_ok=True)
    make_layout(os.path.join(materials, "drawings", "hinge_layout.png"))
    make_layout(os.path.join(materials, "drawings", "hinge_layout.pdf"))
    make_tables(os.path.join(materials, "tables"))
    make_states(os.path.join(materials, "drawings", "states.pdf"))
    write_licence(os.path.join(materials, "LICENSE.txt"))
    print("chair materials written")


if __name__ == "__main__":
    main()
