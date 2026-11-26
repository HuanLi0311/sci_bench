"""Run with Python's standard library; no Blender or Docker needed."""
import copy
import json
from pathlib import Path
import unittest

from rubric import check_sizes, check_support


class GeometryRegression(unittest.TestCase):
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
