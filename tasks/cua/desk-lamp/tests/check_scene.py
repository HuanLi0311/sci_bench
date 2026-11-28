"""Extract a scene report from a submitted desk lamp.

    blender -b <file>.blend --python check_scene.py -- <out.json>

Measurements only; grade.py applies the rubric.
"""
import json
import math
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

JOINTS = ["joint_yaw", "joint_shoulder", "joint_elbow", "joint_head"]
ARMS = ["lower_arm", "upper_arm", "shade", "bulb"]
TARGETS = [(0.300, 0.350, 0.350), (-0.280, 0.320, 0.340), (0.050, 0.470, 0.360)]
REST = {"joint_yaw": (0, 0, 0.022), "joint_shoulder": (0, 0, 0.022),
        "joint_elbow": (0, 0, 0.342), "joint_head": (0, 0, 0.642)}


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


def local_dims(ob):
    """Mesh bounding box in its own space: unaffected by the pose."""
    if not ob.data.vertices:
        return None
    xs = [v.co for v in ob.data.vertices]
    return [max(v[i] for v in xs) - min(v[i] for v in xs) for i in range(3)]


def polys(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    n = sum(len(p.vertices) - 2 for p in me.polygons)
    ev.to_mesh_clear()
    return n


def min_z(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    z = min((mw @ v.co).z for v in me.vertices) if me.vertices else 0.0
    ev.to_mesh_clear()
    return z


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_path = argv[0]
    sc = bpy.context.scene
    report = {"ok": True, "blender": bpy.app.version_string,
              "unit_scale": float(sc.unit_settings.scale_length),
              "frame_start": sc.frame_start, "frame_end": sc.frame_end,
              "objects": {}, "meshes": [], "cameras": {}, "materials": {},
              "images": [], "libraries": [l.filepath for l in bpy.data.libraries],
              "polys_total": 0}

    for ob in bpy.data.objects:
        entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
                 "location": list(ob.location),
                 "world": list(ob.matrix_world.translation)}
        if ob.type == 'MESH':
            entry["aabb"] = world_aabb(ob)
            entry["local_dims"] = local_dims(ob)
            entry["polys"] = polys(ob)
            entry["materials"] = [m.name if m else None for m in ob.data.materials]
            report["polys_total"] += entry["polys"]
            report["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            entry.update({"lens": float(ob.data.lens), "type": ob.data.type})
            report["cameras"][ob.name] = entry
        elif ob.type == 'LIGHT':
            entry.update({"light_type": ob.data.type,
                          "energy": float(ob.data.energy),
                          "spot_size": float(getattr(ob.data, "spot_size", 0.0)),
                          "colour": list(ob.data.color)})
        report["objects"][ob.name] = entry

    for mat in bpy.data.materials:
        info = {"name": mat.name, "metallic": None, "roughness": None, "images": []}
        if mat.use_nodes:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is not None:
                info["metallic"] = float(bsdf.inputs["Metallic"].default_value)
                info["roughness"] = float(bsdf.inputs["Roughness"].default_value)
                stack = [bsdf]
                seen = set()
                while stack:
                    node = stack.pop()
                    if node in seen:
                        continue
                    seen.add(node)
                    if node.type == 'TEX_IMAGE' and node.image is not None:
                        info["images"].append({"name": node.image.name,
                                               "size": list(node.image.size),
                                               "packed": bool(node.image.packed_file is not None)})
                    for sock in node.inputs:
                        for link in sock.links:
                            stack.append(link.from_node)
        report["materials"][mat.name] = info

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        report["images"].append({"name": img.name, "size": list(img.size),
                                 "packed": bool(img.packed_file is not None),
                                 "filepath": img.filepath})
    report["unpacked_images"] = [i["name"] for i in report["images"]
                                 if i["filepath"] and not i["packed"]]

    # ---- joints --------------------------------------------------------
    joints = {}
    for name in JOINTS:
        ob = bpy.data.objects.get(name)
        if ob is None:
            joints[name] = {"present": False}
            continue
        rest = REST[name]
        joints[name] = {
            "present": True,
            "empty": ob.type == 'EMPTY',
            "parent": ob.parent.name if ob.parent else None,
            "local": [round(c, 4) for c in ob.location],
            "rest_error_mm": round(math.dist(list(ob.location), list(rest)) * 1000, 2),
        }
    report["joints"] = joints
    report["mesh_parents"] = {n: (bpy.data.objects[n].parent.name
                                  if n in bpy.data.objects and bpy.data.objects[n].parent
                                  else None) for n in ARMS}

    # ---- action --------------------------------------------------------
    action = {}
    for name in JOINTS:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.animation_data is None or ob.animation_data.action is None:
            action[name] = None
            continue
        act = ob.animation_data.action
        paths = sorted({fc.data_path for fc in act.fcurves})
        frames = sorted({round(kp.co[0], 3) for fc in act.fcurves
                         for kp in fc.keyframe_points})
        action[name] = {"action": act.name, "paths": paths, "frames": frames}
    report["action"] = action
    report["action_names"] = sorted({v["action"] for v in action.values() if v})

    # ---- poses ---------------------------------------------------------
    poses = {}
    for frame in (1, 2, 3):
        sc.frame_set(frame)
        bpy.context.view_layer.update()
        head = bpy.data.objects.get("joint_head")
        entry = {"frame": frame}
        if head is not None:
            pos = head.matrix_world.translation
            entry["head"] = [round(c, 4) for c in pos]
            entry["head_error_mm"] = round((pos - Vector(TARGETS[frame - 1])).length * 1000, 2)
            axis = (head.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
            entry["axis"] = [round(c, 4) for c in axis]
            if axis.z < -1e-6:
                t = -pos.z / axis.z
                hit = pos + axis * t
                d = math.hypot(hit.x - TARGETS[frame - 1][0], hit.y - TARGETS[frame - 1][1])
                entry["desk_hit"] = [round(hit.x, 4), round(hit.y, 4)]
                entry["desk_miss_mm"] = round(d * 1000, 2)
            else:
                entry["desk_hit"] = None
                entry["desk_miss_mm"] = None
        entry["min_z_mm"] = {n: round(min_z(bpy.data.objects[n]) * 1000, 2)
                             for n in ARMS if n in bpy.data.objects}
        a = bpy.data.objects.get("lower_arm")
        b = bpy.data.objects.get("upper_arm")
        if a is not None and b is not None:
            ta, tb = bvh_of(a), bvh_of(b)
            entry["arm_overlap"] = len(ta.overlap(tb)) if ta and tb else 0
        poses[str(frame)] = entry
    report["poses"] = poses
    sc.frame_set(1)
    bpy.context.view_layer.update()

    # ---- light ---------------------------------------------------------
    lamps = {n: report["objects"][n] for n in report["objects"]
             if report["objects"][n].get("type") == 'LIGHT'}
    report["lamps"] = lamps
    spot = bpy.data.objects.get("lamp_spot")
    if spot is not None:
        sc.frame_set(2)
        bpy.context.view_layer.update()
        axis = (spot.matrix_world.to_quaternion() @ Vector((0, 0, -1))).normalized()
        report["lamp"] = {"parent": spot.parent.name if spot.parent else None,
                          "direction": [round(c, 4) for c in axis],
                          "world": [round(c, 4) for c in spot.matrix_world.translation]}
        sc.frame_set(1)
        bpy.context.view_layer.update()

        # Optical alignment: the spot and the bulb must sit on the shade axis,
        # otherwise the lamp is not rigged inside the shade it appears to be in.
        head = bpy.data.objects.get("joint_head")
        bulb = bpy.data.objects.get("bulb")
        if head is not None:
            origin = head.matrix_world.translation.copy()
            axis = (head.matrix_world.to_quaternion() @ Vector((0, 0, 1))).normalized()
            spot_pos = spot.matrix_world.translation.copy()

            def off_axis(p):
                d = p - origin
                return (d - axis * d.dot(axis)).length

            optics = {"lamp_off_axis_mm": round(off_axis(spot_pos) * 1000, 2),
                      "lamp_along_axis_mm": round((spot_pos - origin).dot(axis) * 1000, 2)}
            if bulb is not None:
                deps = bpy.context.evaluated_depsgraph_get()
                ev = bulb.evaluated_get(deps)
                me = ev.to_mesh()
                mw = ev.matrix_world
                pts = [mw @ v.co for v in me.vertices]
                ev.to_mesh_clear()
                if pts:
                    centre = sum(pts, Vector()) / len(pts)
                    optics["bulb_off_axis_mm"] = round(off_axis(centre) * 1000, 2)
            report["optics"] = optics

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
