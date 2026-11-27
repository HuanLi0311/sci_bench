import bpy
me = bpy.data.objects["canvas"].data
uv = me.uv_layers.active
for i in range(len(uv.data)):
    uv.data[i].uv = (uv.data[i].uv[0] * 0.8, uv.data[i].uv[1] * 0.8)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/banner_stand.blend', compress=True)
