"""Extract a scene report from a submitted drawer-cabinet .blend.

    blender -b <file>.blend --python check_scene.py -- <out.json>
"""
import json
import math
import sys

import bpy
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene_support import used_materials, material_report, visible_mesh, component_dimensions, motion_error
from mathutils import Matrix, Vector
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
    reset_pose()
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
            entry["materials"] = used_materials(ob)
            entry["visible_mesh"] = visible_mesh(ob)
            entry["components_mm"] = component_dimensions(ob)
            report["polys_total"] += entry["polys"]
            report["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            entry.update({"lens": float(ob.data.lens), "type": ob.data.type,
                          "ortho_scale": float(ob.data.ortho_scale)})
            report["cameras"][ob.name] = entry
        elif ob.type == 'LIGHT':
            entry["energy"] = float(ob.data.energy)
        report["objects"][ob.name] = entry

    used = {m for ob in report['objects'].values() for m in ob.get('materials', [])}
    for mat in bpy.data.materials:
        if mat.name in used:
            report['materials'][mat.name] = material_report(mat)

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
    # Measure the front slab by its position, independent of whether the
    # author joined, welded or boolean-unioned the front and tray meshes.
    report['front_slabs'] = {}
    for ob in objs(DRAWERS + [DOOR]):
        ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        me = ev.to_mesh()
        pts = [ev.matrix_world @ v.co for v in me.vertices]
        slab = [p for p in pts if 0.205 <= p.y <= 0.228]
        dims = [round((max(p[i] for p in slab)-min(p[i] for p in slab))*1000, 3) for i in range(3)] if slab else []
        tray = [p for p in pts if p.y < 0.208]
        report['front_slabs'][ob.name] = {
            'dims_mm': dims,
            'tray_depth_mm': round((max(p.y for p in tray)-min(p.y for p in tray))*1000, 3) if tray else 0,
        }
        ev.to_mesh_clear()
    envelope = parts + [o for o in bpy.data.objects
                        if o.type == 'MESH' and o.name.startswith("foot")]
    boxes = [report["objects"][o.name]["aabb"] for o in envelope
             if report["objects"].get(o.name, {}).get("aabb")]
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
    slide_motion = {}
    for i, (drawer, slide) in enumerate(zip(DRAWERS, SLIDES), start=1):
        s_ob = bpy.data.objects.get(slide)
        d_ob = bpy.data.objects.get(drawer)
        if s_ob is None or d_ob is None:
            travel[drawer] = None
            continue
        reset_pose()
        before = world_aabb(d_ob)
        initial = d_ob.matrix_world.copy()
        other_objects = objs(CARCASS + [n for n in DRAWERS if n != drawer] + [DOOR])
        other_initial = {o.name: o.matrix_world.copy() for o in other_objects}
        s_ob.location.y = TRAVEL
        bpy.context.view_layer.update()
        after = world_aabb(d_ob)
        travel[drawer] = round((after[1][1] - before[1][1]) * 1000, 2) if after and before else None
        slide_motion[drawer] = {
            'target_error_mm': motion_error(d_ob, initial, Matrix.Translation((0, TRAVEL, 0))),
            'collateral_error_mm': max(motion_error(o, other_initial[o.name], Matrix.Identity(4)) for o in other_objects),
        }
        others = objs(CARCASS)
        neighbours = [bpy.data.objects[d] for d in DRAWERS if d != drawer]
        clearance[drawer] = {"carcass_hits": overlaps([d_ob], others),
                             "neighbour_hits": overlaps([d_ob], neighbours)}
    reset_pose()
    report["drawer_travel_mm"] = travel
    report['slide_motion'] = slide_motion
    report["drawer_clearance"] = clearance
    report["drawer_front_mm"] = {
        d: (lambda a: [round((a[1][0] - a[0][0]) * 1000, 1), round((a[1][2] - a[0][2]) * 1000, 1)])(closed[d])
        for d in closed
    }

    # ---- door ----------------------------------------------------------
    hinge = bpy.data.objects.get(HINGE)
    door = bpy.data.objects.get(DOOR)
    door_rep = {"parent": door.parent.name if door and door.parent else None}
    if hinge is not None:
        door_rep["hinge_location"] = [round(c, 4) for c in hinge.matrix_world.translation]
        door_rep["rotation_mode"] = hinge.rotation_mode
        door_rep["overlap"] = {}
        door_rep['motion_error_mm'] = {}
        reset_pose()
        initial = door.matrix_world.copy()
        pivot = hinge.matrix_world.translation.copy()
        for deg in (0, 55, 110):
            reset_pose()
            hinge.rotation_mode = 'XYZ'
            hinge.rotation_euler = (0.0, 0.0, -math.radians(deg))
            bpy.context.view_layer.update()
            expected = Matrix.Translation(pivot) @ Matrix.Rotation(-math.radians(deg), 4, 'Z') @ Matrix.Translation(-pivot)
            door_rep['motion_error_mm'][str(deg)] = motion_error(door, initial, expected)
            door_rep["overlap"][str(deg)] = overlaps([door], objs(CARCASS) + objs(DRAWERS))
        # combined pose: top drawer out 420 and door 110
        reset_pose()
        if "slide_05" in bpy.data.objects:
            bpy.data.objects["slide_05"].location.y = TRAVEL
        hinge.rotation_euler = (0.0, 0.0, -math.radians(110))
        bpy.context.view_layer.update()
        door_rep["combined_overlap"] = overlaps(
            [door] + objs(["drawer_05"]), objs(CARCASS)) + overlaps([door], objs(["drawer_05"]))
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
