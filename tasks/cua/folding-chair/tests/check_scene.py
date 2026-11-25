"""Extract a scene report from a submitted folding chair.

    blender -b <file>.blend --python check_scene.py -- <out.json>

Measures three states, the hinge pivots, the fold thickness, per-frame BVH
overlaps (hinge-adjacent pairs excluded) and whether each leg's end still sits
on its hinge.
"""
import json
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

LIMBS = ["seat", "back", "front_leg_l", "front_leg_r", "rear_leg_l", "rear_leg_r"]
HINGES = ["hinge_01", "hinge_02", "hinge_03", "hinge_04"]


def world_bvh(ob, deps):
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0), verts


def aabb_of(verts):
    return ([min(v[i] for v in verts) for i in range(3)],
            [max(v[i] for v in verts) for i in range(3)])


def related(a, b):
    """True when two objects sit on a shared hinge (contact is expected)."""
    if a.parent is not None and a.parent is b.parent:
        return True
    return a.parent is b or b.parent is a or a.parent is b.parent or b.parent is a.parent


def main():
    out_path = sys.argv[sys.argv.index("--") + 1]
    sc = bpy.context.scene
    rep = {
        "ok": True,
        "blender": bpy.app.version_string,
        "unit_system": sc.unit_settings.system,
        "fps": sc.render.fps,
        "frame_start": sc.frame_start,
        "frame_end": sc.frame_end,
        "objects": {},
        "hinges": {},
        "states": {},
        "images": [],
        "polys_total": 0,
    }

    meshes = [o for o in bpy.data.objects if o.type == 'MESH']
    for ob in bpy.data.objects:
        e = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
        if ob.type == 'MESH':
            e["polys"] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            e["materials"] = [m.name if m else None for m in ob.data.materials]
            rep["polys_total"] += e["polys"]
        rep["objects"][ob.name] = e

    for h in HINGES:
        ob = bpy.data.objects.get(h)
        rep["hinges"][h] = list(ob.matrix_world.translation) if ob else None

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        rep["images"].append({"name": img.name, "size": list(img.size),
                              "packed": bool(img.packed_file is not None),
                              "filepath": img.filepath})

    # states
    for frame in (0, 30, 60):
        sc.frame_set(frame)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        state = {}
        for ob in meshes:
            if ob.name.startswith("stage"):
                continue
            _bvh, verts = world_bvh(ob, deps)
            state[ob.name] = aabb_of(verts)
        rep["states"][str(frame)] = state

    # folded thickness, ignoring the state prop
    st60 = rep["states"]["60"]
    lim = [k for k in st60 if k != "lock_pin"]
    ymin = min(st60[k][0][1] for k in lim)
    ymax = max(st60[k][1][1] for k in lim)
    rep["folded_thickness"] = ymax - ymin

    # overlaps across the whole animation
    overlaps = {}
    for frame in range(sc.frame_start, sc.frame_end + 1, 2):
        sc.frame_set(frame)
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        parts = [o for o in meshes if not o.name.startswith("stage") and o.name != "lock_pin"]
        trees = {o.name: world_bvh(o, deps)[0] for o in parts}
        for i, a in enumerate(parts):
            for b in parts[i + 1:]:
                if related(a, b):
                    continue
                n = len(trees[a.name].overlap(trees[b.name]))
                if n:
                    key = "|".join(sorted((a.name, b.name)))
                    overlaps[key] = overlaps.get(key, 0) + n
    rep["overlaps"] = overlaps

    # leg ends still on their hinge
    sc.frame_set(0)
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    ends = {}
    for side, hname in (("l", "hinge_01"), ("r", "hinge_02")):
        hp = bpy.data.objects[hname].matrix_world.translation
        for limb in (f"front_leg_{side}", f"rear_leg_{side}"):
            ob = bpy.data.objects.get(limb)
            if ob is None:
                ends[limb] = None
                continue
            _b, verts = world_bvh(ob, deps)
            ends[limb] = min((v - hp).length for v in verts)
    rep["hinge_end_distance"] = ends

    with open(out_path, "w") as fh:
        json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        path = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/scene.json"
        with open(path, "w") as fh:
            json.dump({"ok": False, "error": str(exc)}, fh)
        sys.exit(2)
