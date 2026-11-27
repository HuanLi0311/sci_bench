import bpy
for i in range(1, 6):
    d = bpy.data.objects[f"drawer_{i:02d}"]
    m = d.matrix_world.copy()
    d.parent = None
    d.matrix_world = m

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/drawer_cabinet.blend', compress=True)
