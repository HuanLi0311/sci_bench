# Brand-colour correction

The task gives sRGB hexadecimal colours `#1F6F5C` and `#F2C14E`. Blender stores Principled shader base colours in linear RGB. Comparing that stored value directly with hexadecimal byte values is incorrect.

| Quantity | Primary RGB |
|---|---|
| Task target, sRGB bytes | (31, 111, 92) |
| Correct Blender linear value | approximately (0.01370208, 0.15896083, 0.10702310) |
| Old reference's mistaken linear input | (0.1216, 0.4353, 0.3608) |
| Old reference's actual sRGB bytes | approximately (98, 176, 162) |

The isolated model used the correct linear values. The earlier grader falsely measured a difference of 70.466/255 because it compared linear shader values with sRGB values. The current grader converts linear values to sRGB before applying the unchanged 2/255 tolerance. It records both `basecolor_linear` and the converted sRGB `basecolor`.

The reference builder now converts both hexadecimal colours to linear RGB when assigning Blender materials. The reference scene, its two deliverable renders, and four input photographs are regenerated consistently. This does not accept both the old and new interpretations: the old reference values are incorrect under the current rule.

The [reference repair record](../runs/20261126T095019Z-reference-srgb-repair/stage/color-change.json) records old/new material values and equal geometry SHA-256 hashes before and after the change. The old scene, images and photographs are backed up in that run. Existing historical scores remain tied to their old source and input hashes.

The secondary colour must be assigned to at least one real geometry surface. A correctly coloured but unused material or material slot does not satisfy the check.

The standard-library regression test uses the actual model's linear values and verifies that they decode to (31,111,92), together with black/white endpoints:

```bash
python3 tasks/cua/booth-clearance/tests/test_rubric.py
```

Raw image-comparison regression pairs use immutable recorded submissions, rather than mutable `solution/` files, so the earlier constant-image exploit remains reproducible after this correction.
