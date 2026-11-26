import bpy
old = bpy.data.objects["entrance_zone"]
matrix = old.matrix_world.copy()
collections = list(old.users_collection)
new = bpy.data.objects.new("empty_marker_replacement", None)
for collection in collections:
    collection.objects.link(new)
new.matrix_world = matrix
new.empty_display_type = "CUBE"
new.empty_display_size = 1.0
bpy.data.objects.remove(old, do_unlink=True)
new.name = "entrance_zone"

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
