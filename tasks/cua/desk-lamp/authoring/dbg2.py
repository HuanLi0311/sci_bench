import bpy, os, numpy as np
from mathutils import Vector
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 16; sc.cycles.use_denoising = False
sc.render.resolution_x = 320; sc.render.resolution_y = 240
sc.render.image_settings.file_format = 'PNG'
sc.camera = bpy.data.objects["cam_pose"]
sc.frame_set(2); bpy.context.view_layer.update()
L = bpy.data.objects["lamp_spot"]
mw = L.matrix_world
fwd = (mw.to_quaternion() @ Vector((0, 0, -1)))
print("DBG face", [round(c,3) for c in mw.translation], "dir", [round(c,3) for c in fwd])
print("DBG to target", [round(c,3) for c in (Vector((-0.28,0.32,0.12)) - mw.translation).normalized()])
print("DBG energy", L.data.energy, "spot_size", round(L.data.spot_size,3),
      "use_nodes", L.data.use_nodes, "cycles_visibility", getattr(L, "visible_camera", None))
print("DBG hide_get", L.hide_get(), "hide_viewport", L.hide_viewport,
      "hide_render", L.hide_render, "visible", L.visible_get())
def mean(path):
    img = bpy.data.images.load(path, check_existing=False)
    a = np.asarray(img.pixels[:], dtype=np.float32)
    return round(float(a.mean()), 5)
for label, energy, hide in (("off", 0.0, False), ("on70", 70.0, False),
                            ("on4000", 4000.0, False), ("hidden4000", 4000.0, True)):
    L.data.energy = energy
    L.hide_render = hide
    p = f"/tmp/dl_{label}.png"
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    print("DBG", label, mean(p))
