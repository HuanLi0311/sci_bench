import bpy
rig = bpy.data.objects["rig_spider"]
if rig.animation_data:
    rig.animation_data.action = None
for action in list(bpy.data.actions):
    bpy.data.actions.remove(action)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/spider.blend', compress=True)
