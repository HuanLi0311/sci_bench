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
from bpy_extras.object_utils import world_to_camera_view

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


def world_bvh(ob, deps):
    """BVH built from world-space vertices.

    BVHTree.FromObject keeps the object's local space, so a ray cast in world
    coordinates silently tests the wrong volume for anything not at the origin.
    """
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0)


def poly_count(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def main():
    out_path = sys.argv[sys.argv.index("--") + 1]
    for name in ['booth_shell', 'counter', 'cabinet_01', 'cabinet_02', 'product_01', 'product_02', 'product_03', 'plinth_01', 'plinth_02', 'plinth_03']:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != 'MESH' or not ob.data.polygons:
            raise ValueError(f"{name}: required nonempty mesh missing")
        if (ob.hide_render and name != "lock_pin") or not any(ob.name in scn.objects for scn in bpy.data.scenes):
            raise ValueError(f"{name}: required mesh hidden or outside scenes")
        if any(not __import__('math').isfinite(c) for v in ob.data.vertices for c in v.co):
            raise ValueError(f"{name}: non-finite vertex")
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
            e["dimensions"] = list(ob.dimensions)
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
            nodes = mat.node_tree.nodes
            active, pending = set(), [n for n in nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output]
            while pending:
                node = pending.pop()
                if node in active:
                    continue
                active.add(node)
                pending.extend(link.from_node for link in mat.node_tree.links if link.to_node == node)
            b = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED' and n in active), None)
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

    # The entrance is fixed by the plan. A helper's scale cannot redefine it.
    marker = bpy.data.objects.get("entrance_zone")
    marker_point = marker.matrix_world.translation if marker is not None else None
    if marker is not None and marker.type == 'MESH':
        bounds = rep["objects"].get("entrance_zone", {}).get("aabb")
        if bounds:
            marker_point = Vector([(bounds[0][i] + bounds[1][i]) / 2 for i in range(3)])
    rep["entrance_marker_valid"] = (marker is not None and marker.type in ('MESH', 'EMPTY')
        and marker.name in sc.objects and abs(marker_point.x + 3.0) <= 0.15
        and abs(marker_point.y) <= 0.02 and -0.06 <= marker_point.z <= 4.02)
    rep["entrance_marker_type"] = marker.type if marker else None
    # A vertical opening plane gives horizontal clear distances at any cabinet height.
    entrance = [[-3.0, -1.2, -0.06], [-3.0, 1.2, 4.02]]
    rep["entrance_clearance"] = {
        name: aabb_distance(rep["objects"][name]["aabb"], entrance)
        for name in ("cabinet_01", "cabinet_02") if rep["objects"].get(name, {}).get("aabb")}
    # Check the actual shell cross-section, not just the presence of a marker.
    shell = bpy.data.objects.get("booth_shell")
    opening = {}
    if shell is not None:
        tree = world_bvh(shell, bpy.context.evaluated_depsgraph_get())
        for y in (-1.21, -1.19, 0.0, 1.19, 1.21):
            hit = tree.ray_cast(Vector((-3.05, y, 1.0)), Vector((1, 0, 0)), 0.30)[0]
            should_be_open = abs(y) < 1.2
            opening[str(y)] = (hit is None) == should_be_open
    rep["entrance_opening_samples"] = opening

    # hydrant clearance over everything but the shell (horizontal distance)
    def point_box_xy(p, a):
        dx = max(a[0][0] - p.x, 0.0, p.x - a[1][0])
        dy = max(a[0][1] - p.y, 0.0, p.y - a[1][1])
        return (dx * dx + dy * dy) ** 0.5

    hyd = {}
    for o in mesh_objs:
        if o.name in ("booth_shell", "entrance_zone"):
            continue
        a = rep["objects"][o.name]["aabb"]
        if a:
            hyd[o.name] = float(point_box_xy(HYDRANT, a))
    rep["hydrant_distance"] = hyd

    # sight lines: entrance camera to each product centre
    cam = bpy.data.objects.get("cam_entrance")
    vis = {}
    if cam is not None:
        deps = bpy.context.evaluated_depsgraph_get()
        occluders = [o for o in mesh_objs
                     if o.name != "entrance_zone"]
        trees = [world_bvh(o, deps) for o in occluders]
        origin = cam.matrix_world.translation.copy()
        saved_resolution = (sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage)
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1920, 1080, 100
        for pname in ("product_01", "product_02", "product_03"):
            a = rep["objects"].get(pname, {}).get("aabb")
            if not a:
                vis[pname] = None
                continue
            target = Vector(((a[0][0] + a[1][0]) / 2, (a[0][1] + a[1][1]) / 2,
                             (a[0][2] + a[1][2]) / 2))
            projected = world_to_camera_view(sc, cam, target)
            if projected.z <= 0 or not (0 <= projected.x <= 1 and 0 <= projected.y <= 1):
                vis[pname] = "outside camera frame"
                continue
            d = target - origin
            dist = d.length
            hit = None
            for ob, t in zip(occluders, trees):
                if ob.name == pname:
                    continue
                loc, _n, _i, _d = t.ray_cast(origin, d.normalized(), dist)
                if loc is not None and (loc - origin).length < dist - 0.05:
                    hit = ob.name
                    break
            vis[pname] = (hit is None) or hit
        sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = saved_resolution
    rep["visible_from_entrance"] = vis

    # Measure material actually assigned to the inward-facing back wall.
    # An unused green material slot must not authenticate a differently coloured wall.
    shell = bpy.data.objects.get("booth_shell")
    weighted_delta, area, used = 0.0, 0.0, set()
    if shell is not None:
        deps = bpy.context.evaluated_depsgraph_get()
        evaluated = shell.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        normal_matrix = evaluated.matrix_world.to_3x3().inverted().transposed()
        for polygon in mesh.polygons:
            center = evaluated.matrix_world @ polygon.center
            normal = (normal_matrix @ polygon.normal).normalized()
            if center.x < 2.95 or center.z < 0.05 or normal.x > -0.9:
                continue
            mat = mesh.materials[polygon.material_index] if polygon.material_index < len(mesh.materials) else None
            color = rep["materials"].get(mat.name, {}).get("basecolor") if mat else None
            delta = max(abs(color[i] - PRIMARY[i]) * 255 for i in range(3)) if color else 255.0
            weighted_delta += polygon.area * delta
            area += polygon.area
            if mat:
                used.add(mat.name)
        evaluated.to_mesh_clear()
    rep["brand_delta"] = weighted_delta / area if area > 0 else None
    rep["brand_material"] = sorted(used)
    rep["brand_back_wall_area"] = area

    rep["required_present"] = {n: (n in bpy.data.objects) for n in PANELS}
    rep["has_lighting"] = any(o.type == 'LIGHT' for o in bpy.data.objects) and         ("lighting" in bpy.data.objects)
    with open(out_path, "w") as fh:
        json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    main()
