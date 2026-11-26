import bpy
bpy.data.objects["entrance_zone"].location.x += 10.0

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
