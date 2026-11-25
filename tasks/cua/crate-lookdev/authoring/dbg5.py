import bpy, math
from mathutils import Vector
lid = bpy.data.objects["crate_lid"]
hinge = lid.parent
print("mode", hinge.rotation_mode, "rot", tuple(hinge.rotation_euler))
def aabb(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ev.to_mesh_clear()
    return [round(c,4) for c in mn], [round(c,4) for c in mx]
print("closed", aabb(lid))
hinge.rotation_euler[0] = math.radians(60)
bpy.context.view_layer.update()
print("after60", aabb(lid), "hinge rot", tuple(hinge.rotation_euler))
bpy.context.scene.frame_set(1)
print("after_frame_set", aabb(lid))
