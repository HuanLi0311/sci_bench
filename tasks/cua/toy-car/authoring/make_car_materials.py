"""Authoring tool: toy-car tables, joint spec and licence text."""
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Font

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import mm


def make_sizes(path):
    wb = Workbook()
    ws = wb.active
    ws.append(["item", "value_mm"])
    for k, v in (("length", 380), ("width", 160), ("wheelbase", 240),
                 ("wheel diameter", 60), ("ride height", 32),
                 ("front steer", 30), ("door opening", 75)):
        ws.append([k, v])
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 12
    wb.save(path)


def make_spec(path):
    doc = SimpleDocTemplate(path, pagesize=A4)
    st = getSampleStyleSheet()
    body = st["BodyText"]
    story = [
        Paragraph("Toy car — joint and material specification", st["Heading1"]),
        Paragraph("Length 380, width 160, wheelbase 240, wheel diameter 60 mm. "
                  "Four wheels spin freely about their own axle; the front pair "
                  "steers ±30°; both doors open 0–75° about a vertical hinge at "
                  "the door's front edge.", body),
        Spacer(1, 4 * mm),
        Paragraph("Materials", st["Heading2"]),
        Paragraph("Body: matte plastic, deep red. Chassis and bumpers: dark "
                  "plastic. Windows: semi-transparent glass. Tyres: rubber, "
                  "roughness above 0.7.", body),
        Spacer(1, 4 * mm),
        Paragraph("Rig rules", st["Heading2"]),
        Paragraph("Wheels are parented to their hubs, hubs to the body (front "
                  "hubs through a steering pivot). Spinning or steering a wheel "
                  "must not move the body. Doors are parented to hinge empties "
                  "and may not pass through the body at 0°, 25°, 50° or 75°.",
                  body),
    ]
    doc.build(story)


def make_licence(path):
    with open(path, "w") as fh:
        fh.write("Toy car pack — CC0-1.0, authored for this benchmark task. "
                 "Videos and silhouettes are rendered from the reference model.\n")


def main():
    materials = sys.argv[1]
    os.makedirs(os.path.join(materials, "tables"), exist_ok=True)
    make_sizes(os.path.join(materials, "tables", "car_sizes.xlsx"))
    make_spec(os.path.join(materials, "drawings", "joint_spec.pdf"))
    make_licence(os.path.join(materials, "LICENSE.txt"))
    print("car materials written")


if __name__ == "__main__":
    main()
