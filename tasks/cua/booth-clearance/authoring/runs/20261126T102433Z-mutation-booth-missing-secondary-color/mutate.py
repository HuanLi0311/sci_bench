import bpy
material = bpy.data.materials["mat_brand_secondary"]
node = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
node.inputs["Base Color"].default_value = (0.25, 0.25, 0.25, 1)
material.diffuse_color = (0.25, 0.25, 0.25, 1)
unused = bpy.data.materials.new("adversarial_unused_secondary_yellow")
unused.use_nodes = True
unused.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.8879231178819663, 0.5332764040105052, 0.07618538148130785, 1)
bpy.data.objects["booth_shell"].data.materials.append(unused)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend', compress=True)
