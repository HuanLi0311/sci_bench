import bpy
bpy.data.objects["product_01"].location.z += 0.25

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
