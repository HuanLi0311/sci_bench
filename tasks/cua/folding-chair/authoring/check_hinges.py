import bpy
for f in (0, 60):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    for n in ("hinge_01", "hinge_03", "hinge_04"):
        ob = bpy.data.objects[n]
        print(f, n, [round(v, 3) for v in ob.matrix_world.translation])
    a = bpy.data.objects["lower_leg_l_a"]
    print(f, "barA rot", [round(v, 3) for v in a.rotation_euler], "loc", [round(v,3) for v in a.location])
