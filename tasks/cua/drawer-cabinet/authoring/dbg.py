import bpy
d = bpy.data.objects["door_right"]
bpy.context.view_layer.update()
pts = [d.matrix_world @ v.co for v in d.data.vertices]
print("DBG door z", round(min(p.z for p in pts),3), round(max(p.z for p in pts),3),
      "x", round(min(p.x for p in pts),3), round(max(p.x for p in pts),3))
print("DBG door parent_inverse", [round(c,3) for c in d.matrix_parent_inverse.translation])
for i in (1,3):
    dr = bpy.data.objects[f"drawer_{i:02d}"]
    pts = [dr.matrix_world @ v.co for v in dr.data.vertices]
    print("DBG drawer", i, "z", round(min(p.z for p in pts),3), round(max(p.z for p in pts),3))
