"""Extract a scene report from a submitted folding banner stand.

    blender -b <file>.blend --python check_scene.py -- <out.json>
"""
import json
import math
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PARTS = ["base", "mast_left", "mast_right", "top_bar", "canvas", "leg_rear"]
HINGE = "hinge_rear"
FRAME = ["base", "mast_left", "mast_right", "top_bar"]


def world_aabb(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    if not me.vertices:
        ev.to_mesh_clear()
        return None
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    ev.to_mesh_clear()
    return [mn, mx]


def world_verts(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return pts


def bvh_of(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    if not verts or not faces:
        return None
    return BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0)


def polys(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def objs(names):
    return [bpy.data.objects[n] for n in names if n in bpy.data.objects]


def hits(a_objs, b_objs):
    total = 0
    for a in a_objs:
        ta = bvh_of(a)
        if ta is None:
            continue
        for b in b_objs:
            tb = bvh_of(b)
            if tb is not None:
                total += len(ta.overlap(tb))
    return total


def set_hinge(deg):
    hinge = bpy.data.objects.get(HINGE)
    if hinge is not None:
        hinge.rotation_mode = 'XYZ'
        hinge.rotation_euler = (math.radians(-deg), 0.0, 0.0)
    bpy.context.view_layer.update()


def canvas_uv(ob):
    me = ob.data
    uv = me.uv_layers.active
    if uv is None:
        return {"area": 0.0, "bbox": None}
    area = 0.0
    lo = [9.0, 9.0]
    hi = [-9.0, -9.0]
    for poly in me.polygons:
        pts = [uv.data[li].uv for li in poly.loop_indices]
        s = 0.0
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            s += a[0] * b[1] - b[0] * a[1]
        area += abs(s) / 2
        for u, v in pts:
            lo = [min(lo[0], u), min(lo[1], v)]
            hi = [max(hi[0], u), max(hi[1], v)]
    return {"area": area, "bbox": [lo, hi]}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_path = argv[0]
    sc = bpy.context.scene
    report = {"ok": True, "blender": bpy.app.version_string,
              "unit_scale": float(sc.unit_settings.scale_length),
              "objects": {}, "meshes": [], "cameras": {}, "materials": {},
              "images": [], "libraries": [l.filepath for l in bpy.data.libraries],
              "polys_total": 0}

    for ob in bpy.data.objects:
        entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
                 "location": list(ob.matrix_world.translation)}
        if ob.type == 'MESH':
            entry["aabb"] = world_aabb(ob)
            entry["polys"] = polys(ob)
            entry["materials"] = [m.name if m else None for m in ob.data.materials]
            report["polys_total"] += entry["polys"]
            report["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            entry.update({"lens": float(ob.data.lens), "type": ob.data.type,
                          "ortho_scale": float(ob.data.ortho_scale)})
            report["cameras"][ob.name] = entry
        report["objects"][ob.name] = entry

    for mat in bpy.data.materials:
        info = {"name": mat.name, "metallic": None, "roughness": None, "images": []}
        if mat.use_nodes:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is not None:
                info["metallic"] = float(bsdf.inputs["Metallic"].default_value)
                info["roughness"] = float(bsdf.inputs["Roughness"].default_value)
                for link in bsdf.inputs["Base Color"].links:
                    node = link.from_node
                    guard = 0
                    while node.type != 'TEX_IMAGE' and guard < 6:
                        guard += 1
                        nxt = [l.from_node for s in node.inputs for l in s.links]
                        if not nxt:
                            break
                        node = nxt[0]
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        info["images"].append({"name": node.image.name,
                                               "size": list(node.image.size),
                                               "packed": bool(node.image.packed_file is not None)})
        report["materials"][mat.name] = info

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        report["images"].append({"name": img.name, "size": list(img.size),
                                 "packed": bool(img.packed_file is not None),
                                 "filepath": img.filepath})
    report["unpacked_images"] = [i["name"] for i in report["images"]
                                 if i["filepath"] and not i["packed"]]

    report["parts_present"] = {n: (n in bpy.data.objects) for n in PARTS + [HINGE]}
    frame = objs(FRAME)
    boxes = [report["objects"][o.name]["aabb"] for o in frame
             if report["objects"][o.name]["aabb"]]
    if boxes:
        mn = [min(b[0][i] for b in boxes) for i in range(3)]
        mx = [max(b[1][i] for b in boxes) for i in range(3)]
        report["frame_mm"] = {"width": round((mx[0] - mn[0]) * 1000, 2),
                              "height": round(mx[2] * 1000, 2),
                              "depth": round((mx[1] - mn[1]) * 1000, 2),
                              "min_z": round(mn[2] * 1000, 2)}

    canvas = bpy.data.objects.get("canvas")
    if canvas is not None and canvas.type == 'MESH':
        a = report["objects"]["canvas"]["aabb"]
        verts = world_verts(canvas)
        ys = [v.y for v in verts]
        report["canvas"] = {
            "width_mm": round((a[1][0] - a[0][0]) * 1000, 2),
            "height_mm": round((a[1][2] - a[0][2]) * 1000, 2),
            "z_top_mm": round(a[1][2] * 1000, 2),
            "y": round(sum(ys) / len(ys), 5),
            "planarity_mm": round((max(ys) - min(ys)) * 1000, 3),
            "uv": canvas_uv(canvas),
        }

    hinge = bpy.data.objects.get(HINGE)
    leg = bpy.data.objects.get("leg_rear")
    fold = {"hinge": hinge.name if hinge else None,
            "parent": leg.parent.name if leg else None,
            "hinge_location": [round(c, 4) for c in hinge.matrix_world.translation] if hinge else None,
            "states": {}}
    if hinge is not None and leg is not None:
        for deg in (0, 7, 14):
            set_hinge(deg)
            verts = world_verts(leg)
            state = {
                "z_min_mm": round(min(v.z for v in verts) * 1000, 2),
                "z_max_mm": round(max(v.z for v in verts) * 1000, 2),
                "y_max_mm": round(max(abs(v.y) for v in verts) * 1000, 1),
                "overlap": hits([leg], objs([n for n in FRAME + ["canvas"] if n != "canvas"]
                                            + ["canvas"])),
            }
            fold["states"][str(deg)] = state
        set_hinge(0)
        allv = []
        for ob in bpy.data.objects:
            if ob.type == 'MESH' and ob.name != "ground":
                allv.extend(world_verts(ob))
        fold["folded_depth_mm"] = round((max(v.y for v in allv) - min(v.y for v in allv)) * 1000, 1)
        set_hinge(14)
        allv = [v for ob in bpy.data.objects
                if ob.type == 'MESH' and ob.name.startswith("leg_rear")
                for v in world_verts(ob)]
        fold["open_depth_mm"] = round(max(abs(v.y) for v in allv) * 1000, 1) if allv else 0.0
    set_hinge(14)
    report["fold"] = fold

    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/scene.json"
        with open(out, "w") as fh:
            json.dump({"ok": False, "error": "see stderr"}, fh)
        sys.exit(2)
