import bpy
for material in bpy.data.materials:
    if material.use_nodes:
        for node in list(material.node_tree.nodes):
            if node.type == 'BSDF_PRINCIPLED' and node.inputs['Metallic'].default_value >= .9:
                zero = material.node_tree.nodes.new('ShaderNodeValue')
                zero.outputs[0].default_value = 0.0
                material.node_tree.links.new(zero.outputs[0], node.inputs['Metallic'])

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/rainroom.blend', compress=True)
