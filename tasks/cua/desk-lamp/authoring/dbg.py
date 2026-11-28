import bpy
sc = bpy.context.scene
print("DBG range", sc.frame_start, sc.frame_end)
for ob in bpy.data.objects:
    if ob.animation_data and ob.animation_data.action:
        print("DBG action", ob.name, ob.animation_data.action.name,
              [fc.data_path for fc in ob.animation_data.action.fcurves])
for f in (1, 2, 3):
    sc.frame_set(f)
    bpy.context.view_layer.update()
    for name in ("joint_yaw", "joint_shoulder", "joint_elbow", "joint_head"):
        ob = bpy.data.objects[name]
        print("DBG", f, name, [round(c,4) for c in ob.rotation_euler],
              [round(c,4) for c in ob.matrix_world.translation])
