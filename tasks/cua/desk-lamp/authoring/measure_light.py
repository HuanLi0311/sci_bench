import bpy, os, sys, numpy as np
work = "/task/work"
os.makedirs(work, exist_ok=True)
sc = bpy.context.scene
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=32
sc.cycles.use_denoising=True; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='PNG'
sc.camera = bpy.data.objects["cam_pose"]
sc.render.resolution_x=800; sc.render.resolution_y=600
sc.frame_set(2)
bpy.context.view_layer.update()
sc.render.filepath = os.path.join(work,"on.png"); bpy.ops.render.render(write_still=True)
light = bpy.data.objects["lamp_spot"]
light.hide_render = True
sc.render.filepath = os.path.join(work,"off.png"); bpy.ops.render.render(write_still=True)
a = np.asarray(bpy.data.images.load(os.path.join(work,"on.png")).pixels[:], dtype=np.float32)
b = np.asarray(bpy.data.images.load(os.path.join(work,"off.png")).pixels[:], dtype=np.float32)
print("MEASURE on", round(float(a.mean()),4), "off", round(float(b.mean()),4),
      "ratio", round(float(a.mean()/max(b.mean(),1e-6)),3))
