import bpy
root = bpy.data.objects.new("shared_non_hinge_root", None)
bpy.context.scene.collection.objects.link(root)
for name, x in (("collision_a", 0.0), ("collision_b", 0.01)):
    bpy.ops.mesh.primitive_cube_add(size=0.02, location=(x, 0, 0.5))
    ob = bpy.context.object
    ob.name = name
    ob.parent = root

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/folding_chair.blend', compress=True)
