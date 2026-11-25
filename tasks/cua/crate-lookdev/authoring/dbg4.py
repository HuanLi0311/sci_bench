import bpy, numpy as np

def mk(name, path, set_cs=True, do_pack=True):
    img = bpy.data.images.new(name, width=64, height=64, alpha=False)
    rgba = np.ones((64,64,4), dtype=np.float32)
    rgba[...,0] = 0.8; rgba[...,1] = 0.2; rgba[...,2] = 0.1
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    if set_cs:
        img.colorspace_settings.name = 'sRGB'
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    if do_pack:
        img.pack()
    img2 = bpy.data.images.load(path)
    print(name, "reload mean", round(float(np.array(img2.pixels[:]).mean()),3))

mk("a", "/tmp/a.png", set_cs=False, do_pack=False)
mk("b", "/tmp/b.png", set_cs=True, do_pack=False)
mk("c", "/tmp/c.png", set_cs=True, do_pack=True)
