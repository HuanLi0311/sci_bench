import bpy
from mathutils import Vector

def aabb(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]

from mathutils.bvhtree import BVHTree

def world_bvh(ob, deps):
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0)

parts = [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("stage") and o.name != "lock_pin"]
worst = {}
for f in range(0, 61, 2):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    trees = {o.name: world_bvh(o, deps) for o in parts}
    for i, a in enumerate(parts):
        for b in parts[i+1:]:
            n = len(trees[a.name].overlap(trees[b.name]))
            if n:
                worst[(a.name, b.name)] = worst.get((a.name, b.name), 0) + n
def shares_hinge(a, b):
    pa = bpy.data.objects[a]; pb = bpy.data.objects[b]
    chain = set()
    for o in (pa, pb):
        cur = o
        while cur is not None:
            chain.add((o.name, cur.name))
            cur = cur.parent
    # true if one is an ancestor of the other, or both share a hinge parent
    for (an, cn) in chain:
        if cn == b or cn == a or (pa.parent is not None and pa.parent == pb.parent):
            return True
    return False

strict = {k: v for k, v in worst.items() if not shares_hinge(*k)}
print("OVERLAPS_ALL", worst if worst else "none")
print("OVERLAPS_STRICT", strict if strict else "none")

for frame in (0, 30, 60):
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()
    print("== frame", frame)
    allmin = [1e9]*3; allmax = [-1e9]*3
    for ob in bpy.data.objects:
        if ob.type != 'MESH' or ob.name.startswith("stage"):
            continue
        mn, mx = aabb(ob)
        print(f"  {ob.name:22s} y[{mn[1]:+.3f},{mx[1]:+.3f}] z[{mn[2]:+.3f},{mx[2]:+.3f}]")
        for i in range(3):
            allmin[i] = min(allmin[i], mn[i]); allmax[i] = max(allmax[i], mx[i])
    print("  TOTAL size", [round(allmax[i]-allmin[i],3) for i in range(3)],
          "min", [round(v,3) for v in allmin])
