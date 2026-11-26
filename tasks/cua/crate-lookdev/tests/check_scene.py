"""Extract a scene report from a submitted .blend.

Run inside the verifier image:
    blender -b <file>.blend --python check_scene.py -- <out.json>

Prints nothing useful to stdout; the JSON is the contract grade.py reads.
"""
import json
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

PANELS = ["crate_front", "crate_back", "crate_left", "crate_right", "crate_bottom"]
STENCIL = "stencil_text"
LID = "crate_lid"


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


def poly_count(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def image_report(img):
    px = None
    try:
        arr = np.array(img.pixels[:], dtype=np.float32)
        px = arr
    except Exception:
        pass
    rep = {
        "name": img.name,
        "size": list(img.size),
        "packed": bool(img.packed_file is not None),
        "filepath": img.filepath,
        "colorspace": img.colorspace_settings.name,
    }
    if px is not None and px.size:
        rep["mean"] = float(px.mean())
    return rep


def material_report(mat):
    rep = {"name": mat.name, "nodes": {}, "images": [], "metallic": None,
           "roughness": None, "roughness_std": None, "alpha_frac": None}
    if not mat.use_nodes:
        return rep
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is not None:
        rep["metallic"] = float(bsdf.inputs["Metallic"].default_value)
        rep["roughness"] = float(bsdf.inputs["Roughness"].default_value)
        # base color linked to an image?
        rep["basecolor_linked"] = bool(bsdf.inputs["Base Color"].is_linked)
    for n in nt.nodes:
        if n.type == 'TEX_IMAGE' and n.image is not None:
            img = n.image
            info = image_report(img)
            info["node"] = n.name
            # which socket does it feed?
            sinks, todo, visited = [], [n], set()
            while todo:
                source = todo.pop()
                if source in visited:
                    continue
                visited.add(source)
                for link in nt.links:
                    if link.from_node == source:
                        sinks.append(f"{link.to_node.type}:{link.to_socket.name}")
                        if link.to_node.type != 'BSDF_PRINCIPLED':
                            todo.append(link.to_node)
            info["feeds"] = sinks
            rep["images"].append(info)
            if "Roughness" in sinks or any("Roughness" in x for x in sinks):
                rep["roughness_std"] = info.get("grey_std")
                rep["roughness_mean"] = info.get("grey_mean")
            if any("Alpha" in x for x in sinks):
                rep["alpha_frac"] = info.get("alpha_frac")
                rep["alpha_coverage"] = info.get("alpha_coverage")
            try:
                w, h = img.size
                arr = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, -1)
                grey = arr[..., :3].mean(-1)
                # stats are kept on the image itself: a map routed through a
                # Mix or ColorRamp node is still the same map.
                info["grey_std"] = float(grey.std())
                info["grey_mean"] = float(grey.mean())
                if arr.shape[-1] == 4:
                    a = arr[..., 3]
                    info["alpha_frac"] = float(((a > 0.05) & (a < 0.95)).mean())
                    info["alpha_coverage"] = float((a > 0.5).mean())
            except Exception:
                pass
    return rep


def overlap_test(lid, others, angles):
    """Rotate the lid about its hinge in world space and count BVH overlaps.

    The evaluated copy is rebuilt per angle by transforming vertices directly:
    dependency-graph updates for an empty parent are not reliable in
    background mode, and a stale pose is exactly the bug this check exists to
    catch.
    """
    from mathutils import Matrix
    hinge = lid.parent
    pivot = hinge.matrix_world.translation.copy()

    deps = bpy.context.evaluated_depsgraph_get()
    others_bvh = []
    for ob in others:
        if ob.name == lid.name:
            continue
        ev = ob.evaluated_get(deps)
        me_other = ev.to_mesh()
        mw = ev.matrix_world
        verts_other = [mw @ v.co for v in me_other.vertices]
        faces_other = [tuple(p.vertices) for p in me_other.polygons]
        ev.to_mesh_clear()
        others_bvh.append(BVHTree.FromPolygons(verts_other, faces_other,
                                               all_triangles=False, epsilon=0.0))

    ev = lid.evaluated_get(deps)
    me = ev.to_mesh()
    base = [ev.matrix_world @ v.co for v in me.vertices]
    faces = [tuple(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()

    def pose(deg):
        M = (Matrix.Translation(pivot)
             @ Matrix.Rotation(np.deg2rad(deg), 4, 'X')
             @ Matrix.Translation(-pivot))
        return [M @ v for v in base]

    def mean_z(vs):
        return sum(v.z for v in vs) / len(vs)

    # Which sign of the hinge rotation lifts the lid? Agents are free to build
    # the hinge facing either way; the check is that the *opening* direction is
    # clean, not that a particular sign was chosen.
    up = 1 if mean_z(pose(45)) > mean_z(base) else -1

    out = {"sign": up}
    for deg in angles:
        verts = pose(up * deg)
        lb = BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0)
        out[str(deg)] = sum(len(lb.overlap(b)) for b in others_bvh)
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_path = argv[0]

    for name in ['crate_front', 'crate_back', 'crate_left', 'crate_right', 'crate_bottom', 'crate_lid', 'stencil_text']:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != 'MESH' or not ob.data.polygons:
            raise ValueError(f"{name}: required nonempty mesh missing")
        if (ob.hide_render and name != "lock_pin") or not any(ob.name in scn.objects for scn in bpy.data.scenes):
            raise ValueError(f"{name}: required mesh hidden or outside scenes")
        if any(not __import__('math').isfinite(c) for v in ob.data.vertices for c in v.co):
            raise ValueError(f"{name}: non-finite vertex")
    sc = bpy.context.scene
    report = {
        "ok": True,
        "blender": bpy.app.version_string,
        "unit_system": sc.unit_settings.system,
        "unit_scale": float(sc.unit_settings.scale_length),
        "objects": {},
        "meshes": [],
        "cameras": {},
        "materials": {},
        "images": [],
        "polys_total": 0,
    }

    for ob in bpy.data.objects:
        entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
        if ob.type == 'MESH':
            entry["aabb"] = world_aabb(ob)
            entry["polys"] = poly_count(ob)
            entry["materials"] = [m.name if m else None for m in ob.data.materials]
            entry["modifiers"] = [{"type": m.type,
                                   "width": getattr(m, "width", None)}
                                  for m in ob.modifiers]
            entry["location"] = list(ob.matrix_world.translation)
            report["polys_total"] += entry["polys"]
            report["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            cam = ob.data
            entry.update({
                "lens": float(cam.lens),
                "type": cam.type,
                "ortho_scale": float(cam.ortho_scale),
                "location": list(ob.matrix_world.translation),
                "rotation": list(ob.rotation_euler),
            })
            report["cameras"][ob.name] = entry
        report["objects"][ob.name] = entry

    for mat in bpy.data.materials:
        report["materials"][mat.name] = material_report(mat)

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        report["images"].append(image_report(img))

    # derived checks the grader needs
    mesh_objs = [bpy.data.objects[n] for n in report["meshes"]]
    # Bounds are measured over the crate itself: five panels, the lid and the
    # eight brackets. Anything else in the file (a floor, a backdrop, a stray
    # helper) must not change whether the crate is the right size.
    crate_names = [n for n in PANELS + [LID] if n in bpy.data.objects]
    crate_names += [n for n in report["meshes"] if n.startswith("bracket")]
    body = [bpy.data.objects[n] for n in crate_names]
    mins = [o for o in body if report["objects"][o.name]["aabb"]]
    if mins:
        mn = Vector((min(report["objects"][o.name]["aabb"][0][0] for o in mins),
                     min(report["objects"][o.name]["aabb"][0][1] for o in mins),
                     min(report["objects"][o.name]["aabb"][0][2] for o in mins)))
        mx = Vector((max(report["objects"][o.name]["aabb"][1][0] for o in mins),
                     max(report["objects"][o.name]["aabb"][1][1] for o in mins),
                     max(report["objects"][o.name]["aabb"][1][2] for o in mins)))
        report["bounds"] = [list(mn), list(mx)]
        report["outer_size"] = [mx.x - mn.x, mx.y - mn.y, mx.z - mn.z]

    # lid hinge
    lid = bpy.data.objects.get(LID)
    if lid is not None:
        hinge = lid.parent
        report["lid"] = {
            "parent": hinge.name if hinge else None,
            "parent_location": list(hinge.matrix_world.translation) if hinge else None,
            "parent_type": hinge.type if hinge else None,
            "rotation_mode": hinge.rotation_mode if hinge else None,
            "aabb": report["objects"][LID]["aabb"],
        }
        if hinge is not None:
            others = [o for o in mesh_objs if o.name not in (LID,)]
            report["lid"]["overlap"] = overlap_test(lid, others, [0, 45, 95])

    # panels list actually present
    report["panels_present"] = [p for p in PANELS if p in bpy.data.objects]
    report["brackets"] = sorted(n for n in report["meshes"] if n.startswith("bracket"))
    report["has_stencil"] = STENCIL in bpy.data.objects

    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/scene.json"
        with open(out, "w") as fh:
            json.dump({"ok": False, "error": str(exc)}, fh)
        sys.exit(2)
