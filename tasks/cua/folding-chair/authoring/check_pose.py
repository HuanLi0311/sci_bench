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
