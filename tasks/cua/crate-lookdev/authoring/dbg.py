import bpy
s = bpy.context.scene
s.camera = bpy.data.objects["cam_front"]
s.render.resolution_x = 480
s.render.resolution_y = 360
s.cycles.samples = 16
s.render.engine = 'BLENDER_WORKBENCH'
s.render.filepath = "/tmp/test_wb.png"
bpy.ops.render.render(write_still=True)
s.render.engine = 'CYCLES'
s.render.filepath = "/tmp/test_cy.png"
bpy.ops.render.render(write_still=True)
print("lens", s.camera.data.lens, s.camera.data.clip_start, s.camera.data.clip_end)
print("loc", tuple(s.camera.location), "rot", tuple(s.camera.rotation_euler))
print("world strength", s.world.node_tree.nodes["Background"].inputs["Strength"].default_value)
