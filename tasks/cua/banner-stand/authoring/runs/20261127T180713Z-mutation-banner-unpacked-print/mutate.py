import bpy
img = bpy.data.images.load("/app/materials/textures/banner_graphic.png")
img.name = "adversarial_unpacked"
img.use_fake_user = True
assert img.packed_file is None

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/banner_stand.blend', compress=True)
