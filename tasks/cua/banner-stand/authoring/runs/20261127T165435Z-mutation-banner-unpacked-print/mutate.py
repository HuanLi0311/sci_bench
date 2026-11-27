import bpy
img = bpy.data.images.new("adversarial_unpacked", 8, 8)
img.filepath = "/app/materials/textures/banner_graphic.png"

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/banner_stand.blend', compress=True)
