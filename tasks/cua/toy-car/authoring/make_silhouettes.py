"""Silhouette plates: car white on black, taken from the four renders."""
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def car_mask(a):
    h, w = a.shape
    white = a > 230
    seen = np.zeros_like(white, dtype=bool)
    stack = [(y, x) for y in (0, h - 1) for x in range(w)] + \
            [(y, x) for x in (0, w - 1) for y in range(h)]
    while stack:
        y, x = stack.pop()
        if 0 <= y < h and 0 <= x < w and white[y, x] and not seen[y, x]:
            seen[y, x] = True
            stack.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    return ~seen


def main():
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for v in ("front", "side", "back", "top"):
        a = np.asarray(Image.open(src / f"render_{v}.png").convert("L")
                       .resize((240, 240), Image.LANCZOS))
        m = car_mask(a).astype(np.uint8) * 255
        Image.fromarray(m).save(dst / f"{v}.png")
        print(v, float((m > 0).mean()))


if __name__ == "__main__":
    main()
