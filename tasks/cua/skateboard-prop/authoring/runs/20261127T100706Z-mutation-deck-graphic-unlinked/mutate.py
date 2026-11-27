import bpy
mat = bpy.data.materials["mat_deck_graphic"]
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
for link in list(bsdf.inputs["Base Color"].links):
    mat.node_tree.links.remove(link)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/skateboard.blend', compress=True)
