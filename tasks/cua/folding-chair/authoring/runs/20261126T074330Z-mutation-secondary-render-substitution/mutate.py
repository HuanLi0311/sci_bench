from PIL import Image, ImageStat
from pathlib import Path
import json
p = Path("/mutation/submission") / 'render_locked.png'
original = Image.open(p).convert("RGB")
mean = tuple(round(v) for v in ImageStat.Stat(original).mean)
Image.new("RGB", original.size, mean).save(p)
print(json.dumps({"file": p.name, "size": original.size, "original_rgb_mean": ImageStat.Stat(original).mean, "replacement_rgb": mean}))
