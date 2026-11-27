"""Structure comparison that cannot be diluted by a uniform image background."""
import numpy as np
from PIL import Image, ImageFilter


def gradient_error(trusted, delivered):
    """Relative RGB gradient L2 error after a 2px low-pass filter.

    A constant replacement has error 1 for every nonconstant trusted image,
    regardless of how much of the image is uniform background.
    """
    arrays = [np.asarray(Image.fromarray(np.asarray(x, dtype=np.uint8)).filter(
        ImageFilter.GaussianBlur(2)), dtype=np.float64) / 255 for x in (trusted, delivered)]
    if arrays[0].shape != arrays[1].shape:
        return float("inf")
    gradients = [[np.diff(x, axis=axis) for axis in (0, 1)] for x in arrays]
    energy = sum(float(np.square(g).sum()) for g in gradients[0])
    if energy <= 1e-12:
        return float("inf")
    difference = sum(float(np.square(a - b).sum()) for a, b in zip(*gradients))
    return (difference / energy) ** 0.5
