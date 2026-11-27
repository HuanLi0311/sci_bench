import sys
sys.path.insert(0, "/task/authoring")
import packgen, make_materials as mm
c = packgen.Canvas(1760, 1180, mm.PAPER)
mm.front_view(c, 520, 1060, 0.85)
open("/task/dbg1.png","wb").write(c.png())
c2 = packgen.Canvas(1760, 1180, mm.PAPER)
mm.side_view(c2, 1300, 1060, 0.68)
open("/task/dbg2.png","wb").write(c2.png())
print("DBG OK")
