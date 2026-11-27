import bpy
ob = bpy.data.objects["leg_01_femur"]
for group in list(ob.vertex_groups):
    ob.vertex_groups.remove(group)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/spider.blend', compress=True)
