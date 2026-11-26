import bpy
shell = bpy.data.objects["booth_shell"]
bpy.ops.mesh.primitive_cube_add(size=1, location=(-2.99, 0, 1.2))
closure = bpy.context.object
closure.name = "adversarial_entrance_closure"
closure.dimensions = (0.02, 2.4, 2.4)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.select_all(action="DESELECT")
closure.select_set(True)
shell.select_set(True)
bpy.context.view_layer.objects.active = shell
bpy.ops.object.join()

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
