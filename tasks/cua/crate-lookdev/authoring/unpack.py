import bpy
for img in bpy.data.images:
    if img.packed_file:
        img.unpack(method='WRITE_LOCAL')
bpy.ops.wm.save_as_mainfile(filepath="/tmp/mut/crate.blend", compress=True)
print("unpacked copies written")
