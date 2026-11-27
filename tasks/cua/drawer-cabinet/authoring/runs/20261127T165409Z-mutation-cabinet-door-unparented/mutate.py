import bpy
d = bpy.data.objects["door_right"]
m = d.matrix_world.copy()
d.parent = None
d.matrix_world = m

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/drawer_cabinet.blend', compress=True)
