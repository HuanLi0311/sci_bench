"""Extract a scene report from a submitted booth .blend.

    blender -b <file>.blend --python check_scene.py -- <out.json>
"""
import json
import sys
from itertools import product

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PANELS = ["booth_shell", "counter", "cabinet_01", "cabinet_02",
          "product_01", "product_02", "product_03", "entrance_zone"]
HYDRANT = Vector((-4.2, 0.0, 0.0))
PRIMARY = (0.1216, 0.4353, 0.3608)


def world_aabb(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    if not me.vertices:
        ev.to_mesh_clear()
        return None
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ev.to_mesh_clear()
    return [list(mn), list(mx)]


def aabb_distance(a, b):
    """Shortest distance between two axis-aligned boxes (0 if overlapping)."""
    d = 0.0
    for i in range(3):
        gap = max(a[0][i] - b[1][i], b[0][i] - a[1][i], 0.0)
        d += gap * gap
    return d ** 0.5


def poly_count(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def main():
    out_path = sys.argv[sys.argv.index("--") + 1]
    sc = bpy.context.scene
    rep = {
        "ok": True,
        "blender": bpy.app.version_string,
        "unit_system": sc.unit_settings.system,
        "objects": {},
        "meshes": [],
        "cameras": {},
        "materials": {},
        "images": [],
        "polys_total": 0,
    }

    for ob in bpy.data.objects:
        e = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
        if ob.type == 'MESH':
            e["aabb"] = world_aabb(ob)
            e["polys"] = poly_count(ob)
            e["materials"] = [m.name if m else None for m in ob.data.materials]
            rep["polys_total"] += e["polys"]
            rep["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            e.update({"lens": float(ob.data.lens), "type": ob.data.type,
                      "ortho_scale": float(ob.data.ortho_scale),
                      "location": list(ob.matrix_world.translation)})
            rep["cameras"][ob.name] = e
        rep["objects"][ob.name] = e

    for mat in bpy.data.materials:
        info = {"name": mat.name, "basecolor": None, "images": []}
        if mat.use_nodes:
            b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b is not None:
                info["basecolor"] = list(b.inputs["Base Color"].default_value)[:3]
                info["metallic"] = float(b.inputs["Metallic"].default_value)
            for n in mat.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image is not None:
                    img = n.image
                    entry = {"name": img.name, "size": list(img.size),
                             "packed": bool(img.packed_file is not None),
                             "filepath": img.filepath}
                    try:
                        w, h = img.size
                        arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, -1)
                        entry["alpha_frac"] = float(
                            ((arr[..., 3] > 0.05) & (arr[..., 3] < 0.95)).mean()
                        ) if arr.shape[-1] == 4 else None
                    except Exception:
                        entry["alpha_frac"] = None
                    info["images"].append(entry)
        rep["materials"][mat.name] = info

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        rep["images"].append({"name": img.name, "size": list(img.size),
                              "packed": bool(img.packed_file is not None),
                              "filepath": img.filepath})

    mesh_objs = [bpy.data.objects[n] for n in rep["meshes"]]

    # envelope over every mesh except the entrance marker (it is a mat on the floor)
    body = [o for o in mesh_objs if o.name != "entrance_zone" and rep["objects"][o.name]["aabb"]]
    if body:
        mn = Vector((min(rep["objects"][o.name]["aabb"][0][i] for o in body) for i in range(3)))
        mx = Vector((max(rep["objects"][o.name]["aabb"][1][i] for o in body) for i in range(3)))
        rep["bounds"] = [list(mn), list(mx)]
        rep["size"] = [mx[i] - mn[i] for i in range(3)]

    # entrance clearance: cabinets vs the entrance marker
    ez = rep["objects"].get("entrance_zone", {}).get("aabb")
    clear = {}
    if ez:
        for cab in ("cabinet_01", "cabinet_02"):
            a = rep["objects"].get(cab, {}).get("aabb")
            if a:
                clear[cab] = aabb_distance(a, ez)
    rep["entrance_clearance"] = clear

    # hydrant clearance over everything but the shell
    hyd = {}
    for o in mesh_objs:
        if o.name == "booth_shell":
            continue
        a = rep["objects"][o.name]["aabb"]
        if not a:
            continue
        c = Vector(((a[0][0] + a[1][0]) / 2, (a[0][1] + a[1][1]) / 2, (a[0][2] + a[1][2]) / 2))
        d = min(Vector((max(a[0][0], min(HYDRANT.x, a[1][0])),
                        max(a[0][1], min(HYDRANT.y, a[1][1])),
                        max(a[0][2], min(HYDRANT.z, a[1][2])))) - Vector((HYDRANT.x, HYDRANT.y, 0)))
        hyd[o.name] = float((c - Vector((HYDRANT.x, HYDRANT.y, c.z))).length) if False else float(
            Vector((max(a[0][0], min(HYDRANT.x, a[1][0])),
                    max(a[0][1], min(HYDRANT.y, a[1][1])),
                    HYDRANT.z)) - HYDRAUNT_PLACEHOLDER)
    rep["hydrant_distance"] = hyd

    with open(out_path, "w") as fh:
        json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    main()
