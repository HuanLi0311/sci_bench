import bpy, numpy as np
s = bpy.context.scene
for img in bpy.data.images:
    if img.size[0] == 0:
        continue
    a = np.array(img.pixels[:], dtype=np.float32)
    print("IMG", img.name, img.size[:], "mean", float(a.mean()), "max", float(a.max()), "cs", img.colorspace_settings.name, "packed", bool(img.packed_file))
print("engine", s.render.engine, "view", s.view_settings.view_transform, "look", s.view_settings.look, "exposure", s.view_settings.exposure)
for o in bpy.data.objects:
    if o.type == 'LIGHT':
        print("LIGHT", o.name, o.data.type, o.data.energy, "rot", tuple(round(x,3) for x in o.rotation_euler), "loc", tuple(round(x,3) for x in o.location))
S = bpy.data.materials.get("mat_weathered_oak")
if S:
    b = [n for n in S.node_tree.nodes if n.type=='BSDF_PRINCIPLED'][0]
    print("oak base linked", b.inputs['Base Color'].is_linked, "rough linked", b.inputs['Roughness'].is_linked, "alpha", b.inputs['Alpha'].default_value)
