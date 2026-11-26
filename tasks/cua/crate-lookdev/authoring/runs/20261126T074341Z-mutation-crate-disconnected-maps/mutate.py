import bpy
mat = bpy.data.objects["crate_front"].data.materials[0]
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
for name in ("Base Color", "Roughness"):
    for link in list(bsdf.inputs[name].links):
        mat.node_tree.links.remove(link)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/crate.blend', compress=True)
