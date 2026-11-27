import bpy
bpy.data.objects["hinge_right"].location.x += 0.050

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/drawer_cabinet.blend', compress=True)
