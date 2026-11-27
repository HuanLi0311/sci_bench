"""Extract a scene report from a submitted skateboard .blend.

    blender -b <file>.blend --python check_scene.py -- <out.json>

Measurements only; grade.py applies the rubric.
"""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector

PARTS = ["deck", "truck_front", "truck_rear", "wheel_01", "wheel_02",
         "wheel_03", "wheel_04", "bearings"]


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


def evaluated_polys(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def material_report(mat):
    rep = {"name": mat.name, "base_color": None, "metallic": 0.0, "roughness": None,
           "images": []}
    if not mat.use_nodes:
        return rep
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        c = bsdf.inputs["Base Color"].default_value
        rep["base_color"] = [float(c[0]), float(c[1]), float(c[2])]
        rep["metallic"] = float(bsdf.inputs["Metallic"].default_value)
        rep["roughness"] = float(bsdf.inputs["Roughness"].default_value)
        if bsdf.inputs["Base Color"].is_linked:
            node = bsdf.inputs["Base Color"].links[0].from_node
            if node.type == 'TEX_IMAGE' and node.image is not None:
                rep["images"].append({"name": node.image.name,
                                      "size": list(node.image.size),
                                      "packed": bool(node.image.packed_file is not None)})
    return rep


def deck_report(ob):
    me = ob.data
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = []
    uv_layer = me.uv_layers.active
    uv_area = 0.0
    uv_min = [1e9, 1e9]
    uv_max = [-1e9, -1e9]
    bottom_faces = 0
    bands = {"left": {}, "right": {}}
    thickness_samples = []
    for poly in me.polygons:
        n = poly.normal.copy()
        n.rotate(ob.matrix_world.to_quaternion())
        idx = poly.material_index
        if abs(n.y) > 0.9 and abs(n.z) < 0.5:
            zs = [verts[v].z for v in poly.vertices]
            side = "right" if n.y > 0 else "left"
            centre = poly.center
            entry = bands[side].setdefault(idx, {"faces": 0, "zmin": 1e9, "zmax": -1e9,
                                                 "mid_spans": []})
            entry["faces"] += 1
            entry["zmin"] = min(entry["zmin"], min(zs))
            entry["zmax"] = max(entry["zmax"], max(zs))
            if abs(centre.x - 0.22) < 0.10:
                # vertical extent of this band along the straight mid-section
                entry["mid_spans"].append(max(zs) - min(zs))
        if n.z < -0.5:
            bottom_faces += 1
            if uv_layer is not None:
                us = [uv_layer.data[li].uv for li in poly.loop_indices]
                area = 0.0
                for i in range(len(us)):
                    a, b = us[i], us[(i + 1) % len(us)]
                    area += a[0] * b[1] - b[0] * a[1]
                uv_area += abs(area) / 2.0
                for u, v in us:
                    uv_min = [min(uv_min[0], u), min(uv_min[1], v)]
                    uv_max = [max(uv_max[0], u), max(uv_max[1], v)]
    for v in verts:
        if abs(v.x) < 0.05 and abs(v.y) < 0.01:
            thickness_samples.append(v.z)
    thickness = (max(thickness_samples) - min(thickness_samples)) if thickness_samples else 0.0
    return {
        "aabb": world_aabb(ob),
        "polys": evaluated_polys(ob),
        "material_slots": [m.name if m else None for m in me.materials],
        "thickness_mm": thickness * 1000.0,
        "bottom_faces": bottom_faces,
        "uv_area": uv_area,
        "uv_bbox": [uv_min, uv_max] if bottom_faces else None,
        "bands": {side: {str(k): {
            "faces": v["faces"],
            "thickness_mm": (sum(v["mid_spans"]) / len(v["mid_spans"]) * 1000.0
                             if v["mid_spans"] else 0.0),
        } for k, v in bands[side].items()} for side in bands},
        "origin": list(ob.matrix_world.translation),
        "rotation": list(ob.matrix_world.to_euler()),
        "scale": list(ob.matrix_world.to_scale()),
    }


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
            entry["polys"] = evaluated_polys(ob)
            entry["materials"] = [m.name if m else None for m in ob.data.materials]
            report["polys_total"] += entry["polys"]
            report["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            cam = ob.data
            entry.update({"lens": float(cam.lens), "type": cam.type,
                          "ortho_scale": float(cam.ortho_scale)})
            report["cameras"][ob.name] = entry
        report["objects"][ob.name] = entry

    for mat in bpy.data.materials:
        report["materials"][mat.name] = material_report(mat)

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        report["images"].append({"name": img.name, "size": list(img.size),
                                 "packed": bool(img.packed_file is not None),
                                 "filepath": img.filepath})
    report["unpacked_images"] = [i["name"] for i in report["images"]
                                 if i["filepath"] and not i["packed"]]

    report["parts_present"] = {p: p in bpy.data.objects for p in PARTS}
    deck = bpy.data.objects.get("deck")
    report["deck"] = deck_report(deck) if deck is not None and deck.type == 'MESH' else None

    wheels = {}
    for name in ("wheel_01", "wheel_02", "wheel_03", "wheel_04"):
        ob = bpy.data.objects.get(name)
        if ob is not None and ob.type == 'MESH':
            aabb = world_aabb(ob)
            wheels[name] = {
                "aabb": aabb,
                "centre": [ (aabb[0][i] + aabb[1][i]) / 2 for i in range(3) ],
                "diameter_mm": (aabb[1][2] - aabb[0][2]) * 1000.0,
                "width_mm": (aabb[1][1] - aabb[0][1]) * 1000.0,
            }
    report["wheels"] = wheels
    trucks = {}
    for name in ("truck_front", "truck_rear"):
        ob = bpy.data.objects.get(name)
        if ob is not None and ob.type == 'MESH':
            aabb = world_aabb(ob)
            trucks[name] = {
                "aabb": aabb,
                "centre": [ (aabb[0][i] + aabb[1][i]) / 2 for i in range(3) ],
                "width_mm": (aabb[1][1] - aabb[0][1]) * 1000.0,
            }
    report["trucks"] = trucks

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
