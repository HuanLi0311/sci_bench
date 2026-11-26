import bpy
bpy.data.objects["product_01"].scale *= 0.5

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
