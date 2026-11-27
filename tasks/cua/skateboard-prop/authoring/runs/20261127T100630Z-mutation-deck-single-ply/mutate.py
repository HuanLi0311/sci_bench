import bpy
deck = bpy.data.objects["deck"]
for poly in deck.data.polygons:
    if poly.material_index >= 2:
        poly.material_index = 2

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/skateboard.blend', compress=True)
