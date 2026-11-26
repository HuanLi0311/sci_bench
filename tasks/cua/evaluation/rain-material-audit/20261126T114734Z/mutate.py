import bpy, json
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
slot = len(shell.data.materials) - 1
assert not any(p.material_index == slot for p in shell.data.polygons)
proof = {'unused_material': fake.name, 'slot': slot, 'assigned_faces': 0,
         'all_other_principled_metallic': 0.0}
with open('/audit/material-proof.json', 'w') as f: json.dump(proof, f, indent=2)
bpy.ops.wm.save_as_mainfile(filepath='/audit/submission/rainroom.blend', compress=True)
