"""Extract a scene report from a submitted drawer-cabinet .blend.

    blender -b <file>.blend --python check_scene.py -- <out.json>
"""
import json
import math
import sys

import bpy
from mathutils.bvhtree import BVHTree

CARCASS = ["carcass_left", "carcass_right", "carcass_top", "carcass_bottom",
           "carcass_back", "carcass_divider"]
DRAWERS = [f"drawer_{i:02d}" for i in range(1, 6)]
SLIDES = [f"slide_{i:02d}" for i in range(1, 6)]
DOOR = "door_right"
HINGE = "hinge_right"
TRAVEL = 0.420


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


def overlaps(a_objs, b_objs):
    a = [bvh_of(o) for o in a_objs]
    b = [bvh_of(o) for o in b_objs]
    hits = 0
    for x in a:
        if x is None:
            continue
        for y in b:
            if y is None:
                continue
            hits += len(x.overlap(y))
    return hits


def reset_pose():
    for s in objs(SLIDES):
        s.location.y = 0.0
    hinge = bpy.data.objects.get(HINGE)
    if hinge is not None:
        hinge.rotation_mode = 'XYZ'
        hinge.rotation_euler = (0.0, 0.0, 0.0)
    bpy.context.view_layer.update()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_path = argv[0]
    sc = bpy.context.scene
    report = {"ok": True, "blender": bpy.app.version_string,
              "unit_scale": float(sc.unit_settings.scale_length),
              "objects": {}, "meshes": [], "cameras": {}, "materials": {},
              "images": [], "libraries": [l.filepath for l in bpy.data.libraries],
              "collections": {c.name: [o.name for o in c.objects] for c in bpy.data.collections},
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
        elif ob.type == 'LIGHT':
            entry["energy"] = float(ob.data.energy)
        report["objects"][ob.name] = entry

    for mat in bpy.data.materials:
        info = {"name": mat.name, "metallic": None, "roughness": None, "images": []}
        if mat.use_nodes:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is not None:
                info["metallic"] = float(bsdf.inputs["Metallic"].default_value)
                info["roughness"] = float(bsdf.inputs["Roughness"].default_value)
                for sock in ("Base Color", "Roughness", "Normal"):
                    for link in bsdf.inputs[sock].links:
                        node = link.from_node
                        while node.type != 'TEX_IMAGE' and node.inputs:
                            nxt = [l.from_node for l in node.inputs[0].links]
                            if not nxt:
                                break
                            node = nxt[0]
                        if node.type == 'TEX_IMAGE' and node.image is not None:
                            info["images"].append({"name": node.image.name,
                                                   "size": list(node.image.size),
                                                   "packed": bool(node.image.packed_file is not None),
                                                   "feeds": sock})
        report["materials"][mat.name] = info

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        report["images"].append({"name": img.name, "size": list(img.size),
                                 "packed": bool(img.packed_file is not None),
                                 "filepath": img.filepath})
    report["unpacked_images"] = [i["name"] for i in report["images"]
                                 if i["filepath"] and not i["packed"]]

    report["parts_present"] = {n: (n in bpy.data.objects) for n in
                               CARCASS + DRAWERS + SLIDES + [DOOR, HINGE]}

    # ---- carcass envelope and panel thickness --------------------------
    parts = objs(CARCASS)
    panels = {}
    for ob in parts:
        a = report["objects"][ob.name]["aabb"]
        if a:
            dims = [a[1][i] - a[0][i] for i in range(3)]
            panels[ob.name] = {"dims_mm": [round(d * 1000, 2) for d in dims],
                               "thickness_mm": round(min(dims) * 1000, 2)}
    report["panels"] = panels
    boxes = [report["objects"][o.name]["aabb"] for o in parts
             if report["objects"][o.name]["aabb"]]
    if boxes:
        mn = [min(b[0][i] for b in boxes) for i in range(3)]
        mx = [max(b[1][i] for b in boxes) for i in range(3)]
        report["outer_size_mm"] = [round((mx[i] - mn[i]) * 1000, 2) for i in range(3)]
        report["outer_min"] = mn

    # ---- drawers -------------------------------------------------------
    reset_pose()
    closed = {d: report["objects"][d]["aabb"] for d in DRAWERS
              if report["objects"].get(d, {}).get("aabb")}
    travel = {}
    clearance = {}
    for i, (drawer, slide) in enumerate(zip(DRAWERS, SLIDES), start=1):
        s_ob = bpy.data.objects.get(slide)
        d_ob = bpy.data.objects.get(drawer)
        if s_ob is None or d_ob is None:
            travel[drawer] = None
            continue
        reset_pose()
        before = world_aabb(d_ob)
        s_ob.location.y = TRAVEL
        bpy.context.view_layer.update()
        after = world_aabb(d_ob)
        travel[drawer] = round((after[1][1] - before[1][1]) * 1000, 2) if after and before else None
        others = [o for o in objs(CARCASS) if o.name != "carcass_back"]
        neighbours = [bpy.data.objects[d] for d in DRAWERS if d != drawer]
        clearance[drawer] = {"carcass_hits": overlaps([d_ob], others),
                             "neighbour_hits": overlaps([d_ob], neighbours)}
    reset_pose()
    report["drawer_travel_mm"] = travel
    report["drawer_clearance"] = clearance
    report["drawer_front_mm"] = {
        d: (lambda a: [round((a[1][0] - a[0][0]) * 1000, 1), round((a[1][2] - a[0][2]) * 1000, 1)])(closed[d])
        for d in closed
    }

    # ---- door ----------------------------------------------------------
    hinge = bpy.data.objects.get(HINGE)
    door = bpy.data.objects.get(DOOR)
    door_rep = {"parent": door.parent.name if door else None}
    if hinge is not None:
        door_rep["hinge_location"] = [round(c, 4) for c in hinge.matrix_world.translation]
        door_rep["rotation_mode"] = hinge.rotation_mode
        door_rep["overlap"] = {}
        for deg in (0, 55, 110):
            reset_pose()
            hinge.rotation_mode = 'XYZ'
            hinge.rotation_euler = (0.0, 0.0, -math.radians(deg))
            bpy.context.view_layer.update()
            door_rep["overlap"][str(deg)] = overlaps([door], objs(CARCASS) + objs(DRAWERS))
        # combined pose: top drawer out 420 and door 110
        reset_pose()
        if "slide_05" in bpy.data.objects:
            bpy.data.objects["slide_05"].location.y = TRAVEL
        hinge.rotation_euler = (0.0, 0.0, -math.radians(110))
        bpy.context.view_layer.update()
        door_rep["combined_overlap"] = overlaps(
            [door] + objs(["drawer_05"]), objs(CARCASS))
    reset_pose()
    report["door"] = door_rep

    # ---- lighting ------------------------------------------------------
    report["light_collections"] = {
        name: sorted(o.name for o in bpy.data.collections[name].objects
                     if o.type == 'LIGHT')
        for name in ("light_day", "light_night")
        if name in bpy.data.collections
    }

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
