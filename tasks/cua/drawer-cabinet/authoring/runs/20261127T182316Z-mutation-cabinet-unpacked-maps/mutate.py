import bpy
img = bpy.data.images.load("/mutation/submission/textures/wood_basecolor.png")
img.name = "adversarial_unpacked"
img.use_fake_user = True
assert img.packed_file is None

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/drawer_cabinet.blend', compress=True)
