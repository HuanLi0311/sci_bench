import bpy, os, sys
out=sys.argv[sys.argv.index("--")+1]
sc=bpy.context.scene
sc.render.engine="CYCLES"
sc.cycles.device="CPU"
sc.cycles.samples=64
sc.cycles.use_denoising=True
sc.cycles.seed=0
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
for name, camera, size in (("render_entrance","cam_entrance",(1920,1080)),("render_top","cam_top",(2048,1536))):
    sc.camera=bpy.data.objects[camera]
    sc.render.resolution_x,sc.render.resolution_y=size
    sc.render.filepath=os.path.join(out,name+".png")
    bpy.ops.render.render(write_still=True)
    print("[formal]",name,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,"booth.blend"),compress=True)
