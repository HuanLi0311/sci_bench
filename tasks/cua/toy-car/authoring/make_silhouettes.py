"""Build white-on-black silhouette plates from the four opaque renders."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
dst.mkdir(parents=True, exist_ok=True)
for v in ("front", "side", "back", "top"):
    a = np.asarray(Image.open(src / f"render_{v}.png").convert("L"))
    m = ((a >= 245).astype(np.uint8) * 255)  # car black on white
    Image.fromarray(m).save(dst / f"{v}.png")
    print(v, float((m > 0).mean()))
