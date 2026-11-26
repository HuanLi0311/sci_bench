import bpy
for material in bpy.data.materials:
    if material.use_nodes:
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Metallic'].default_value = 0.0
fake = bpy.data.materials.new('adversarial_unused_metal')
fake.use_nodes = True
fake.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value = 1.0
shell = bpy.data.objects['room_shell']
shell.data.materials.append(fake)
assert not any(p.material_index == len(shell.data.materials) - 1 for p in shell.data.polygons)

bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/rainroom.blend', compress=True)
