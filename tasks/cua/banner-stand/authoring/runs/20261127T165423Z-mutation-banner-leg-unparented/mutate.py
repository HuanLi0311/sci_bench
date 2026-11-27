import bpy
leg = bpy.data.objects["leg_rear"]
m = leg.matrix_world.copy()
leg.parent = None
leg.matrix_world = m

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/banner_stand.blend', compress=True)
