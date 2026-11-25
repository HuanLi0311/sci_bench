"""Authoring tool: generates the input material pack (drawings, spec, HDRI).

Run on the host with matplotlib + reportlab:
    python3 make_materials.py <materials_dir>

Everything written here is self-authored and released CC0; the pack is copied
into the agent image at /app/materials.
"""
import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Circle

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors

W, D, H = 800.0, 600.0, 600.0      # mm, outer envelope
T = 20.0                            # panel thickness
BAND = 60.0                         # corner bracket leg
BAND_T = 2.0                        # bracket plate thickness
LID_OPEN = 95.0                     # degrees


def dim(ax, p0, p1, text, off=0.0, vertical=False, color="#222"):
    """Dimension line with arrows and a centred label."""
    x0, y0 = p0
    x1, y1 = p1
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.2, shrinkA=0, shrinkB=0))
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    if vertical:
        ax.text(mx + off, my, text, rotation=90, ha="center", va="center",
                fontsize=11, color=color, backgroundcolor="white")
    else:
        ax.text(mx, my + off, text, ha="center", va="center",
                fontsize=11, color=color, backgroundcolor="white")


def draw_front(ax):
    ax.set_title("FRONT (800 x 600)", fontsize=13, fontweight="bold")
    ax.add_patch(Rectangle((0, 0), W, H - T + T, fill=False, lw=2.2, ec="#111"))
    # lid seam
    ax.plot([0, W], [H - T, H - T], lw=1.0, ls="--", color="#888")
    # wall thickness (left)
    ax.plot([T, T], [T, H - T], lw=0.8, color="#999")
    ax.plot([0, T], [T, T], lw=0.8, color="#999")
    # corner brackets (8): 4 bottom, 4 top
    for x0 in (0, W - BAND):
        for y0 in (0, H - T - BAND):
            ax.add_patch(Rectangle((x0, y0), BAND, BAND, fill=False, lw=1.4,
                                   ec="#c0392b", hatch="////"))
    ax.text(W / 2, H / 2 + 30, "STENCIL: HANDLE / WITH CARE", ha="center",
            fontsize=10, color="#555")
    ax.text(W / 2, H / 2 - 20, "white worn paint", ha="center", fontsize=9, color="#777")
    dim(ax, (0, -70), (W, -70), "800", off=-18)
    dim(ax, (-70, 0), (-70, H), "600", off=-20, vertical=True)
    dim(ax, (W + 45, 0), (W + 45, T), "20", off=10, vertical=True)
    ax.annotate("lid seam", xy=(W * 0.72, H - T), xytext=(W * 0.78, H + 55),
                fontsize=9, arrowprops=dict(arrowstyle="->", lw=1))
    ax.set_xlim(-130, W + 130)
    ax.set_ylim(-130, H + 110)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_side(ax):
    ax.set_title("SIDE (600 x 600)", fontsize=13, fontweight="bold")
    ax.add_patch(Rectangle((0, 0), D, H, fill=False, lw=2.2, ec="#111"))
    ax.plot([0, D], [H - T, H - T], lw=1.0, ls="--", color="#888")
    for x0 in (0, D - BAND):
        for y0 in (0, H - T - BAND):
            ax.add_patch(Rectangle((x0, y0), BAND, BAND, fill=False, lw=1.4,
                                   ec="#c0392b", hatch="////"))
    # hinge at rear top edge
    ax.add_patch(Circle((D, H - T), 12, fill=True, color="#2c3e50"))
    ax.annotate("rear hinge, lid 0-95 deg", xy=(D, H - T), xytext=(D - 40, H + 60),
                fontsize=9, ha="right",
                arrowprops=dict(arrowstyle="->", lw=1))
    dim(ax, (0, -70), (D, -70), "600", off=-18)
    dim(ax, (-70, 0), (-70, H), "600", off=-20, vertical=True)
    ax.set_xlim(-130, D + 160)
    ax.set_ylim(-130, H + 110)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_top(ax):
    ax.set_title("TOP (800 x 600)", fontsize=13, fontweight="bold")
    ax.add_patch(Rectangle((0, 0), W, D, fill=False, lw=2.2, ec="#111"))
    ax.plot([0, W], [0, 0], lw=3.0, color="#2c3e50")  # hinge edge
    for x0 in (0, W - BAND):
        for y0 in (0, D - BAND):
            ax.add_patch(Rectangle((x0, y0), BAND, BAND, fill=False, lw=1.4,
                                   ec="#c0392b", hatch="////"))
    dim(ax, (0, -70), (W, -70), "800", off=-18)
    dim(ax, (W + 45, 0), (W + 45, D), "600", off=15, vertical=True)
    ax.text(W / 2, D / 2, "lid panel 20 thick", ha="center", fontsize=10, color="#555")
    ax.set_xlim(-130, W + 150)
    ax.set_ylim(-130, D + 100)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_bracket(ax):
    ax.set_title("CORNER BRACKET  60 x 60 x 2 (8x)", fontsize=13, fontweight="bold")
    # unfolded L: 60 + 60 legs, 2 thick
    ax.add_patch(Rectangle((0, 0), BAND, BAND, fill=False, lw=2.0, ec="#c0392b"))
    ax.add_patch(Rectangle((0, 0), BAND_T, BAND, fill=True, fc="#c0392b", alpha=0.35))
    ax.add_patch(Rectangle((0, 0), BAND, BAND_T, fill=True, fc="#c0392b", alpha=0.35))
    dim(ax, (0, -45), (BAND, -45), "60", off=-16)
    dim(ax, (BAND + 30, 0), (BAND + 30, BAND), "60", off=12, vertical=True)
    dim(ax, (0, BAND + 30), (BAND_T, BAND + 30), "2", off=14)
    ax.text(BAND / 2, BAND / 2 - 30, "rusted iron, 2 mm plate,\nflush with the crate face",
            ha="center", fontsize=9, color="#444")
    ax.set_xlim(-90, BAND + 110)
    ax.set_ylim(-110, BAND + 80)
    ax.set_aspect("equal")
    ax.axis("off")


def make_drawing(out_dir):
    fig, axes = plt.subplots(2, 2, figsize=(17, 11), dpi=220)
    fig.suptitle("WEATHERED WOODEN CRATE — DESIGN VIEWS (all dimensions mm, 1:10)",
                 fontsize=15, fontweight="bold")
    draw_front(axes[0][0])
    draw_side(axes[0][1])
    draw_top(axes[1][0])
    draw_bracket(axes[1][1])
    fig.text(0.5, 0.015,
             "Outer 800 x 600 x 600 · panel thickness 20 · lid hinged at rear edge, opens 0-95 deg · "
             "8 corner brackets 60 x 60 x 2 · stencil on front face",
             ha="center", fontsize=10, color="#333")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    os.makedirs(out_dir, exist_ok=True)
    png = os.path.join(out_dir, "crate_three_views.png")
    fig.savefig(png, facecolor="white")
    fig.savefig(os.path.join(out_dir, "crate_three_views.pdf"), facecolor="white")
    plt.close(fig)
    return png


def make_spec(path):
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()
    h = styles["Heading1"]
    body = styles["BodyText"]
    small = ParagraphStyle("small", parent=body, fontSize=9, leading=12)

    story = [Paragraph("Crate LookDev — material and delivery specification", h),
             Paragraph("Units are millimetres unless stated otherwise. "
                       "Nominal outer size 800 x 600 x 600; panel thickness 20; "
                       "lid hinged at the rear top edge and opening 0–95°; "
                       "eight iron corner brackets 60 x 60 x 2, flush with the outer faces.",
                       body),
             Spacer(1, 6 * mm)]

    rows = [
        ["Surface", "Look", "Measured requirement"],
        ["Weathered oak (panels, lid)",
         "Grey-brown oak, visible grain, fine checks and raised grain. "
         "Weathering must come from roughness and normal detail, not from colour alone.",
         "Roughness varies across the surface (std >= 0.05). "
         "basecolor / roughness / normal maps, each >= 2048 px."],
        ["Rusted iron (8 corner brackets)",
         "Dark iron with orange-brown rust blooms. Real metal, not painted wood.",
         "Metallic input = 1.0; roughness in the 0.65–0.85 band."],
        ["Stencil paint (front face)",
         "White stencilled lettering, edges broken up by wear and pinholes. "
         "It is a painted layer, not a clean vector label.",
         "Edges must be irregular; a crisp new font is a fail."],
        ["Lid hinge",
         "Rear top edge; the lid rotates about that edge.",
         "0–95°, no interpenetration at 0/45/95°."],
    ]
    t = Table(rows, colWidths=[38 * mm, 72 * mm, 58 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.4),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [t, Spacer(1, 6 * mm)]

    story += [Paragraph("Render brief", styles["Heading2"]),
              Paragraph("- front 3/4: 35 mm, 1.6 m from the crate, lens 0.9 m above the floor, 1600 x 1200.<br/>"
                        "- back 3/4: same parameters, mirrored to the opposite rear corner.<br/>"
                        "- top: orthographic, covering 1.0 x 0.8 m, 1600 x 1280.<br/>"
                        "- macro: 100 mm, 0.25 m from a top corner bracket, 1600 x 1200.<br/>"
                        "- Cycles, CPU, 64 samples, fixed seed, denoise on. Deliver the four PNGs.",
                        body),
              Spacer(1, 4 * mm),
              Paragraph("Self-contained file", styles["Heading2"]),
              Paragraph("The .blend must open and render on a machine with no access to the "
                        "material folder: every image and the HDRI are packed into the file. "
                        "Objects keep semantic names; the lid stays a hinge-driven object.",
                        body),
              Spacer(1, 4 * mm),
              Paragraph("Licences", styles["Heading2"]),
              Paragraph("The supplied HDRI and drawings are CC0-1.0, self-authored. "
                        "Any asset you bring in must be recorded in manifest.json with its "
                        "source and licence.", small)]
    doc.build(story)
    return path


# --------------------------------------------------------------------------
# procedural studio HDRI (Radiance RGBE, equirectangular)
# --------------------------------------------------------------------------
def _smooth_noise2(h, w, cells, rng):
    g = rng.random((cells, cells))
    y = np.linspace(0, cells - 1, h)
    x = np.linspace(0, cells - 1, w)
    xi, yi = x.astype(int), y.astype(int)
    xi2, yi2 = np.minimum(xi + 1, cells - 1), np.minimum(yi + 1, cells - 1)
    fx, fy = (x - xi)[None, :], (y - yi)[:, None]
    a, b, c, d = g[yi][:, xi], g[yi][:, xi2], g[yi2][:, xi], g[yi2][:, xi2]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def make_hdri(path, w=1024, h=512):
    rng = np.random.default_rng(3)
    theta = np.linspace(0, 2 * np.pi, w, endpoint=False)
    phi = np.linspace(np.pi, 0, h)            # top row = zenith
    th, ph = np.meshgrid(theta, phi)

    # soft studio gradient: dim floor, brighter ceiling
    base = 0.05 + 0.22 * (ph / np.pi) ** 1.4
    img = np.stack([base * 0.98, base, base * 1.02], -1)

    # three softboxes
    def softbox(az, el, width, height, power, tint):
        d = np.arccos(np.clip(np.sin(ph) * np.sin(el) + np.cos(ph) * np.cos(el) *
                              np.cos(th - az), -1, 1))
        # elliptical-ish falloff
        da = np.abs(((th - az + np.pi) % (2 * np.pi)) - np.pi)
        de = np.abs(ph - el)
        m = np.exp(-(da ** 2) / (2 * width ** 2) - (de ** 2) / (2 * height ** 2))
        return np.stack([m * power * tint[0], m * power * tint[1], m * power * tint[2]], -1)

    img += softbox(np.radians(40), np.radians(55), 0.35, 0.30, 3.0, (1.0, 0.97, 0.92))
    img += softbox(np.radians(-130), np.radians(40), 0.45, 0.40, 1.2, (0.9, 0.95, 1.0))
    img += softbox(np.radians(170), np.radians(25), 0.25, 0.20, 0.8, (1.0, 1.0, 1.0))
    img += 0.02 * _smooth_noise2(h, w, 16, rng)[..., None]

    img = np.clip(img, 0, None)

    # write Radiance .hdr (flat RGBE)
    def rgbe(x):
        v = np.maximum(x[..., 0], np.maximum(x[..., 1], x[..., 2]))
        e = np.zeros_like(v)
        nz = v > 1e-8
        mant, exp = np.frexp(v)
        e[nz] = exp[nz]
        scale = np.where(nz, mant * 256.0 / np.where(v > 1e-8, v, 1.0), 0.0)
        r = np.clip(x[..., 0] * scale, 0, 255).astype(np.uint8)
        g = np.clip(x[..., 1] * scale, 0, 255).astype(np.uint8)
        b = np.clip(x[..., 2] * scale, 0, 255).astype(np.uint8)
        return np.stack([r, g, b, e.astype(np.uint8)], -1)

    rgbe = rgbe(img)
    header = (b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n"
              + f"-Y {h} +X {w}\n".encode())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(rgbe.astype(np.uint8).tobytes())
    return path


def write_licence(path):
    with open(path, "w") as fh:
        fh.write("""Crate LookDev — material pack licence
=====================================

Everything under materials/ is self-authored for this benchmark task and
released under CC0-1.0 (public-domain dedication):

  drawings/crate_three_views.png, .pdf   drawn for this task
  spec/material_spec.pdf                 written for this task
  hdri/studio_soft.hdr                   procedurally generated, 1024x512 equirect
  photos/*.jpg                           rendered from the reference crate model

You may use these files freely inside the task. If you ship an asset that did
not come from this folder, record its source and licence in manifest.json.
""")


def main():
    materials = sys.argv[1]
    os.makedirs(os.path.join(materials, "drawings"), exist_ok=True)
    os.makedirs(os.path.join(materials, "spec"), exist_ok=True)
    os.makedirs(os.path.join(materials, "photos"), exist_ok=True)
    os.makedirs(os.path.join(materials, "hdri"), exist_ok=True)

    make_drawing(os.path.join(materials, "drawings"))
    make_spec(os.path.join(materials, "spec", "material_spec.pdf"))
    make_hdri(os.path.join(materials, "hdri", "studio_soft.hdr"))
    write_licence(os.path.join(materials, "LICENSE.txt"))
    print("materials written to", materials)


if __name__ == "__main__":
    main()
