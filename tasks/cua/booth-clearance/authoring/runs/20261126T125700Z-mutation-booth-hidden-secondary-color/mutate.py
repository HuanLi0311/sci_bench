import bpy
from mathutils import Vector
counter = bpy.data.objects['counter']
material = bpy.data.materials['mat_brand_secondary']
material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.25, 0.25, 0.25, 1)
center = counter.matrix_world @ (sum((Vector(v) for v in counter.bound_box), Vector()) / 8)
bpy.ops.mesh.primitive_cube_add(size=0.2, location=center)
hidden = bpy.context.object
hidden.name = 'hidden_yellow_inside_counter'
yellow = bpy.data.materials.new('hidden_secondary_brand')
yellow.use_nodes = True
yellow.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0.8879231178819663, 0.5332764040105052, 0.07618538148130785, 1)
hidden.data.materials.append(yellow)
bpy.ops.object.select_all(action='DESELECT')
hidden.select_set(True)
counter.select_set(True)
bpy.context.view_layer.objects.active = counter
bpy.ops.object.join()
bpy.ops.wm.save_as_mainfile(filepath='/mutation/submission/booth.blend')
