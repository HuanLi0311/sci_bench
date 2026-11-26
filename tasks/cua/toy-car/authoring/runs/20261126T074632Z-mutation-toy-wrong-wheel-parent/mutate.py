import bpy
wheel = bpy.data.objects["wheel_fl"]
matrix = wheel.matrix_world.copy()
wheel.parent = bpy.data.objects["chassis"]
wheel.matrix_world = matrix

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/toy_car.blend', compress=True)
