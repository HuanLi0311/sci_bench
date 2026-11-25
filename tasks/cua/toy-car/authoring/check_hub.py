import bpy, math
w = bpy.data.objects["wheel_fl"]
h = w.parent

def c(o):
    d = bpy.context.evaluated_depsgraph_get()
    e = o.evaluated_get(d); m = e.to_mesh(); mw = e.matrix_world
    p = [mw @ v.co for v in m.vertices]
    e.to_mesh_clear()
    return [round(sum(q[i] for q in p) / len(p), 4) for i in range(3)]

print("PARENT", h.name, "BEFORE", c(w))
h.rotation_mode = "XYZ"
h.rotation_euler = (0, math.radians(90), 0)
bpy.context.view_layer.update()
print("AFTER", c(w), "CAP", c(bpy.data.objects["wheel_fl_cap"]))
