import bpy
img = bpy.data.images.new("adversarial_unpacked", 8, 8)
img.filepath = "/app/materials/textures/wood_basecolor.png"

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/drawer_cabinet.blend', compress=True)
