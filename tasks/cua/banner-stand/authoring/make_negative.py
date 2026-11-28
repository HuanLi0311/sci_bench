"""Create adversarial .blend variants for delivery regression tests.

Run inside Blender: blender -b scene.blend -P make_negative.py -- CASE OUTPUT
The parent test copies the reference submission first. These are deliberately
invalid submissions, never agent-visible starting scenes.
"""
import bpy
import sys

case, output = sys.argv[sys.argv.index('--') + 1:]
banner = 'canvas' in bpy.data.objects
if case == 'unused-materials':
    ob = bpy.data.objects['canvas' if banner else 'carcass_left']
    blank = bpy.data.materials.new('untextured')
    blank.use_nodes = True
    for i in range(len(ob.data.materials)):
        ob.data.materials[i] = blank
elif case == 'hidden-part':
    bpy.data.objects['mast_left' if banner else 'door_right'].hide_render = True
elif case == 'uv-tiling':
    me = bpy.data.objects['canvas'].data
    uv = me.uv_layers.active
    for polygon in list(me.polygons)[::2]:
        for li in polygon.loop_indices:
            uv.data[li].uv.x += 0.25
elif case == 'static-door':
    door = bpy.data.objects['door_right']
    target = bpy.data.objects.new('static_target', None)
    bpy.context.scene.collection.objects.link(target)
    target.matrix_world = door.matrix_world.copy()
    door.constraints.new('COPY_TRANSFORMS').target = target
elif case == 'coupled-slides':
    # Every drawer now follows every slide. Correct travel alone is insufficient.
    for i in range(1, 6):
        ob = bpy.data.objects[f'drawer_{i:02d}']
        driver = ob.driver_add('location', 1).driver
        terms = []
        for j in range(1, 6):
            if i == j:
                continue
            variable = driver.variables.new()
            variable.name = f's{j}'
            variable.type = 'SINGLE_PROP'
            variable.targets[0].id = bpy.data.objects[f'slide_{j:02d}']
            variable.targets[0].data_path = 'location[1]'
            terms.append(variable.name)
        driver.expression = '+'.join(terms)
else:
    raise ValueError(case)
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=output)
