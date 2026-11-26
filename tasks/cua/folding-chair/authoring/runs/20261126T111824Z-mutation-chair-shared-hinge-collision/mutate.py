import bpy
bpy.context.scene.frame_set(0)
hinge = bpy.data.objects["hinge_01"]
for name, point in (("collision_a", (-.28, 0, .100)), ("collision_b", (-.277, .003, .102))):
    bpy.ops.mesh.primitive_cube_add(size=.014, location=point)
    ob = bpy.context.object
    ob.name = name
    bpy.context.view_layer.update()
    matrix = ob.matrix_world.copy()
    ob.parent = hinge
    ob.matrix_world = matrix

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/folding_chair.blend', compress=True)
