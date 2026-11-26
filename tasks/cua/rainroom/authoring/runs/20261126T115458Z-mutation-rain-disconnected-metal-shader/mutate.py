import bpy
for material in bpy.data.materials:
    if material.use_nodes:
        for node in list(material.node_tree.nodes):
            if node.type == 'BSDF_PRINCIPLED' and node.inputs['Metallic'].default_value >= .9:
                diffuse = material.node_tree.nodes.new('ShaderNodeBsdfDiffuse')
                diffuse.inputs['Color'].default_value = node.inputs['Base Color'].default_value
                for output in material.node_tree.nodes:
                    if output.type == 'OUTPUT_MATERIAL' and output.is_active_output:
                        material.node_tree.links.new(diffuse.outputs[0], output.inputs['Surface'])

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/rainroom.blend', compress=True)
