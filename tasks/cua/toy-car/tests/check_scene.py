"""Extract a scene report from a submitted toy car."""
import json
import math
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

WHEELS = ["wheel_fl", "wheel_fr", "wheel_rl", "wheel_rr"]
DOORS = ["door_l", "door_r"]


def world_aabb(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    if not pts:
        return None
    return [[min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)]]


def world_bvh(ob, deps):
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0)


def centre(a):
    return [(a[0][i] + a[1][i]) / 2 for i in range(3)]


def main():
    out_path = sys.argv[sys.argv.index("--") + 1]
    for name in ['body', 'chassis', 'wheel_fl', 'wheel_fr', 'wheel_rl', 'wheel_rr', 'door_l', 'door_r']:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != 'MESH' or not ob.data.polygons:
            raise ValueError(f"{name}: required nonempty mesh missing")
        if ob.hide_render or ob.name not in bpy.context.scene.objects:
            raise ValueError(f"{name}: hidden or outside current scene")
        if any(not __import__('math').isfinite(c) for v in ob.data.vertices for c in v.co):
            raise ValueError(f"{name}: non-finite vertex")
    rep = {"ok": True, "blender": bpy.app.version_string, "objects": {},
           "meshes": [], "polys_total": 0, "images": [], "cameras": {}}

    for ob in bpy.data.objects:
        e = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
        if ob.type == 'MESH':
            a = world_aabb(ob)
            e["aabb"] = a
            e["centre"] = centre(a) if a else None
            e["polys"] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            e["materials"] = [m.name if m else None for m in ob.data.materials]
            rep["polys_total"] += e["polys"]
            rep["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            e["type_cam"] = ob.data.type
            e["ortho_scale"] = float(ob.data.ortho_scale)
            rep["cameras"][ob.name] = e
        rep["objects"][ob.name] = e

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        rep["images"].append({"name": img.name, "packed": bool(img.packed_file),
                              "filepath": img.filepath, "size": list(img.size)})

    # wheel geometry
    wheels = {}
    for w in WHEELS:
        ob = bpy.data.objects.get(w)
        if ob is None or not rep["objects"][w]["aabb"]:
            wheels[w] = None
            continue
        a = rep["objects"][w]["aabb"]
        wheels[w] = {
            "centre": centre(a),
            "diameter_z": a[1][2] - a[0][2],
            "diameter_y": a[1][1] - a[0][1],
            "diameter_x": a[1][0] - a[0][0],
        }
    rep["wheels"] = wheels
    if all(wheels.values()):
        front = 0.5 * (wheels["wheel_fl"]["centre"][0] + wheels["wheel_fr"]["centre"][0])
        rear = 0.5 * (wheels["wheel_rl"]["centre"][0] + wheels["wheel_rr"]["centre"][0])
        rep["wheelbase"] = abs(front - rear)
        rep["axle_level_dz"] = max(abs(wheels["wheel_fl"]["centre"][2] - wheels["wheel_fr"]["centre"][2]),
                                   abs(wheels["wheel_rl"]["centre"][2] - wheels["wheel_rr"]["centre"][2]))
        rep["axle_parallel"] = max(abs(wheels["wheel_fl"]["centre"][0] - wheels["wheel_fr"]["centre"][0]),
                                   abs(wheels["wheel_rl"]["centre"][0] - wheels["wheel_rr"]["centre"][0]))

    # spinning a wheel must not move the body
    body = bpy.data.objects.get("body")
    if body is not None:
        before = world_aabb(body)
        hub = None
        w = bpy.data.objects.get("wheel_fl")
        if w is not None and w.parent is not None:
            hub = w.parent
        if hub is not None:
            hub.rotation_mode = 'XYZ'
            hub.rotation_euler = (0, math.radians(360), 0)
            bpy.context.view_layer.update()
            after = world_aabb(body)
            rep["body_after_spin"] = after
            rep["body_before_spin"] = before
            hub.rotation_euler = (0, 0, 0)
            bpy.context.view_layer.update()

    # steering pivots
    steer = {}
    for w in ("wheel_fl", "wheel_fr"):
        ob = bpy.data.objects.get(w)
        steer[w] = ob.parent.name if ob is not None and ob.parent is not None else None
    rep["steer_parents"] = steer

    # door hinges and clearance
    doors = {}
    for d in DOORS:
        ob = bpy.data.objects.get(d)
        if ob is None or ob.parent is None:
            doors[d] = None
            continue
        hinge = ob.parent
        hp = hinge.matrix_world.translation
        a = rep["objects"][d]["aabb"]
        occ = {}
        body_bvh = world_bvh(body, bpy.context.evaluated_depsgraph_get())
        hinge.rotation_mode = 'XYZ'
        sign = -1 if d.endswith("_l") else 1
        for deg in (0, 25, 50, 75):
            hinge.rotation_euler = (0, 0, sign * math.radians(deg))
            bpy.context.view_layer.update()
            deps = bpy.context.evaluated_depsgraph_get()
            db = world_bvh(ob, deps)
            occ[str(deg)] = len(db.overlap(body_bvh))
        hinge.rotation_euler = (0, 0, 0)
        bpy.context.view_layer.update()
        doors[d] = {"hinge": list(hp), "overlap": occ,
                    "front_edge": a[1][0] if a else None}
    rep["doors"] = doors

    rep["required"] = {n: (n in bpy.data.objects)
                       for n in ["body", "chassis"] + WHEELS + DOORS}

    with open(out_path, "w") as fh:
        json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        p = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/scene.json"
        with open(p, "w") as fh:
            json.dump({"ok": False, "error": str(exc)}, fh)
        sys.exit(2)
