"""Run with Python's standard library; no Blender or Docker needed."""
import copy
import json
from pathlib import Path
import unittest

from rubric import check_sizes, check_support, linear_rgb_to_srgb


class GeometryRegression(unittest.TestCase):
    def test_blender_linear_brand_colour(self):
        # Actual values extracted from the model's correctly entered #1F6F5C.
        linear = (0.013702083379030228, 0.15896083414554596, 0.10702310502529144)
        self.assertEqual(tuple(round(c * 255) for c in linear_rgb_to_srgb(linear)), (31, 111, 92))
        self.assertEqual(linear_rgb_to_srgb((0, 0, 0)), [0, 0, 0])
        for channel in linear_rgb_to_srgb((1, 1, 1)):
            self.assertAlmostEqual(channel, 1)

    def test_reference_and_invalid_deliveries(self):
        objects = json.loads((Path(__file__).parent / "reference/geometry.json").read_text())["objects"]
        self.assertTrue(check_sizes(objects)[0])
        self.assertTrue(check_support(objects)[0])
        scaled = copy.deepcopy(objects)
        scaled["product_01"]["aabb"][1][2] += 0.15
        self.assertFalse(check_sizes(scaled)[0])
        floating = copy.deepcopy(objects)
        for corner in floating["product_02"]["aabb"]:
            corner[2] += 0.25
        self.assertTrue(check_sizes(floating)[0])
        self.assertFalse(check_support(floating)[0])
        del floating["plinth_03"]
        self.assertFalse(check_sizes(floating)[0])
        self.assertFalse(check_support(floating)[0])


if __name__ == "__main__":
    unittest.main()
