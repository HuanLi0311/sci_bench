import bpy
bpy.data.objects["hinge_rear"].location.y -= 0.060

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/banner_stand.blend', compress=True)
