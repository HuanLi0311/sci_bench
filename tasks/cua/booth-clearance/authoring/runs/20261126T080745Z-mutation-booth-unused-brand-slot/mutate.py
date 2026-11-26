import bpy
shell = bpy.data.objects["booth_shell"]
white = bpy.data.materials.new("adversarial_white_back_wall")
white.use_nodes = True
white.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (1, 1, 1, 1)
shell.data.materials.append(white)
for face in shell.data.polygons:
    face.material_index = len(shell.data.materials) - 1

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
