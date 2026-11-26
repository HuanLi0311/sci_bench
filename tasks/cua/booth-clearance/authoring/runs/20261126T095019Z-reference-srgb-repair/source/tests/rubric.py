"""Geometric requirements taken from the supplied furniture/product tables."""
SIZES = {
    "counter": (1.8, 0.6, 1.0),
    "cabinet_01": (1.2, 0.5, 2.0), "cabinet_02": (1.2, 0.5, 2.0),
    "plinth_01": (0.8, 0.8, 0.4), "plinth_02": (0.8, 0.8, 0.4),
    "plinth_03": (0.8, 0.8, 0.4),
    "product_01": (0.3, 0.2, 0.25), "product_02": (0.38, 0.26, 0.32),
    "product_03": (0.46, 0.3, 0.38),
}


def linear_rgb_to_srgb(values):
    return [12.92 * value if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055
            for value in values]


def check_sizes(objects):
    errors = {}
    for name, expected in SIZES.items():
        obj = objects.get(name, {})
        box = obj.get("aabb")
        if not box:
            errors[name] = "missing geometry"
            continue
        # Local dimensions permit furniture to be rotated in the floor plan.
        size = obj.get("dimensions") or [box[1][i] - box[0][i] for i in range(3)]
        if max(abs(a - b) for a, b in zip(sorted(size), sorted(expected))) > 0.02:
            errors[name] = {"actual": size, "expected": expected}
        if abs(box[1][2] - box[0][2] - expected[2]) > 0.02:
            errors[name] = "wrong vertical height"
    return not errors, errors


def check_support(objects):
    errors = {}
    for i in range(1, 4):
        name = f"product_{i:02}"
        product = objects.get(name, {}).get("aabb")
        plinth = objects.get(f"plinth_{i:02}", {}).get("aabb")
        if not product or not plinth:
            errors[name] = "missing product/plinth"
        elif abs(product[0][2] - plinth[1][2]) > 0.02 or any(
            product[0][axis] < plinth[0][axis] - 0.02
            or product[1][axis] > plinth[1][axis] + 0.02 for axis in (0, 1)
        ):
            errors[name] = "not standing on its plinth"
    return not errors, errors
