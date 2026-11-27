import bpy, os, sys
work = "/hosttmp/ac_test"
os.makedirs(work, exist_ok=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=64
sc.cycles.use_denoising=True; sc.cycles.seed=0
sc.render.resolution_percentage=100; sc.render.image_settings.file_format='PNG'
cam = bpy.data.objects["cam_three_quarter"]
sc.camera = cam; sc.render.resolution_x=1600; sc.render.resolution_y=1200
sc.render.filepath=os.path.join(work,"base_tq.png"); bpy.ops.render.render(write_still=True)
deck = bpy.data.objects["deck"]
import numpy as np
me = deck.data
co = np.empty(len(me.vertices)*3, dtype=np.float32); me.vertices.foreach_get("co", co)
co = co.reshape(-1,3); co[:,2] += 0.06
me.vertices.foreach_set("co", co.ravel()); me.update()
sc.render.filepath=os.path.join(work,"lift_tq.png"); bpy.ops.render.render(write_still=True)
print("DIAG RENDERS DONE")
