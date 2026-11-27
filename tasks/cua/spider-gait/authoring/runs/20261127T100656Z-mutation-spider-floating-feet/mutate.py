import bpy
bpy.data.objects["rig_spider"].location.z += 0.020

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/spider.blend', compress=True)
