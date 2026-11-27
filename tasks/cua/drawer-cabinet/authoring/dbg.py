import sys
sys.path.insert(0, "/task/authoring")
import packgen, make_materials as mm

orig_line = packgen.Canvas.line
def traced(self, x0, y0, x1, y1, color=(0, 0, 0), width=1.0):
    if abs(y1 - y0) < 2 and abs(x1 - x0) > 400:
        print("WIDE-LINE", round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1), color, width)
    return orig_line(self, x0, y0, x1, y1, color, width)
packgen.Canvas.line = traced
c = packgen.Canvas(1760, 1180, mm.PAPER)
mm.front_view(c, 520, 1060, 0.85)
print("DONE")
