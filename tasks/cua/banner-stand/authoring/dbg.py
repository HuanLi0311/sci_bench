import bpy, math, sys
sys.path.insert(0, "/task/authoring")
leg = bpy.data.objects["leg_rear"]
hinge = bpy.data.objects["hinge_rear"]
print("DBG leg mesh z-range", min(v.co.z for v in leg.data.vertices), max(v.co.z for v in leg.data.vertices))
print("DBG leg matrix_world", [round(c,3) for c in leg.matrix_world.translation])
for deg in (0, 14, -14):
    hinge.rotation_mode = 'XYZ'
    hinge.rotation_euler = (math.radians(deg), 0, 0)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ev = leg.evaluated_get(deps); me = ev.to_mesh(); mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    print("DBG", deg, "z", round(min(p.z for p in pts),3), round(max(p.z for p in pts),3),
          "y", round(min(p.y for p in pts),3), round(max(p.y for p in pts),3))
    ev.to_mesh_clear()
