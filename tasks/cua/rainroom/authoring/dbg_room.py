import bpy
sc = bpy.context.scene
print("LIGHTS", [(o.name, o.data.energy, o.users_collection[0].name if o.users_collection else None, o.hide_render) for o in bpy.data.objects if o.type == 'LIGHT'])
for c in bpy.data.collections:
    print("COLL", c.name, c.hide_render, len(c.objects))
print("CAM", sc.camera.name if sc.camera else None, tuple(round(v,2) for v in sc.camera.location))
print("WORLD", sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value if sc.world else None)
print("EXPOSURE", sc.view_settings.exposure, sc.view_settings.view_transform)
