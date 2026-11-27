import bpy
mat = bpy.data.materials["mat_aluminium"]
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Metallic"].default_value = 0.0

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/skateboard.blend', compress=True)
