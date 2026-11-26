import bpy
camera = bpy.data.objects["cam_entrance"]
for constraint in list(camera.constraints):
    camera.constraints.remove(constraint)
camera.rotation_mode = "XYZ"
camera.rotation_euler = (0, 0, 0)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
