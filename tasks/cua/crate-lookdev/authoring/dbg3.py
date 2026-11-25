import bpy, numpy as np
img = bpy.data.images.new("t", width=4, height=4, alpha=False)
rgba = np.ones((4,4,4), dtype=np.float32)
rgba[...,0] = 0.8
rgba[...,1] = 0.2
rgba[...,2] = 0.1
img.pixels.foreach_set(rgba.ravel())
img.update()
print("buf mean after set", float(np.array(img.pixels[:]).mean()))
img.filepath_raw = "/tmp/t.png"
img.file_format = 'PNG'
img.save()
print("saved")
img2 = bpy.data.images.load("/tmp/t.png")
print("reloaded mean", float(np.array(img2.pixels[:]).mean()), "size", img2.size[:])
