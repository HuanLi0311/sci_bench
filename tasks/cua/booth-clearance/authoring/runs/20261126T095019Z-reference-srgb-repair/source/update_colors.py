import bpy, json, hashlib, sys
def signature():
    data = {o.name: {"matrix": [list(r) for r in o.matrix_world], "verts": [list(v.co) for v in o.data.vertices], "faces": [list(p.vertices) for p in o.data.polygons]} for o in bpy.data.objects if o.type == "MESH"}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
def linear(n):
    v=n/255.0
    return v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4
before = signature()
colors = {"mat_brand_primary": (31,111,92), "mat_brand_secondary": (242,193,78)}
changes = {}
for name, color in colors.items():
    mat=bpy.data.materials[name]
    node=next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    old=list(node.inputs["Base Color"].default_value)
    value=tuple(linear(v) for v in color)+(1,)
    node.inputs["Base Color"].default_value=value
    mat.diffuse_color=value
    changes[name]={"old_linear":old,"new_linear":value,"srgb_8bit":color}
after=signature()
assert before==after, "Geometry unexpectedly changed"
output=sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.save_as_mainfile(filepath=output, compress=True)
with open("/stage/color-change.json","w") as f: json.dump({"geometry_sha256_before":before,"geometry_sha256_after":after,"materials":changes},f,indent=2)
print(json.dumps({"geometry_unchanged":before==after,"materials":changes}))
