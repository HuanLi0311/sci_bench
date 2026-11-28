import bpy, os, numpy as np
sc = bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.samples=16; sc.cycles.use_denoising=False
sc.render.resolution_x=320; sc.render.resolution_y=240
sc.render.image_settings.file_format='PNG'
sc.camera = bpy.data.objects["cam_pose"]
sc.frame_set(2); bpy.context.view_layer.update()
L = bpy.data.objects["lamp_spot"]
print("DBG type", L.type, "energy", L.data.energy, "hide_render", L.hide_render,
      "loc", [round(c,3) for c in L.matrix_world.translation],
      "rot", [round(c,3) for c in L.matrix_world.to_euler()])
print("DBG collections", [c.name for c in L.users_collection],
      [c.hide_render for c in L.users_collection])
print("DBG parent", L.parent.name if L.parent else None)
def shot(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    a = np.asarray(img.pixels[:], dtype=np.float32)
    return round(float(a.mean()), 5)
p = "/tmp/dbg"
shot(p + "0.png")
L.data.energy = 0
print("DBG energy0", shot(p + "1.png"))
L.data.energy = 500
print("DBG energy500", shot(p + "2.png"))
