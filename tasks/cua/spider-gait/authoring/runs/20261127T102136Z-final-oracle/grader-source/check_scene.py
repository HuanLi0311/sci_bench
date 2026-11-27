"""Extract a scene report from a submitted spider .blend.

Run inside the verifier image:
    blender -b <file>.blend --python check_scene.py -- <out.json>

The JSON is the contract grade.py reads. Nothing here decides pass/fail; it
measures, and grade.py applies the rubric.
"""
import json
import math
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

LEGS = range(1, 9)
SEGMENTS = ("coxa", "femur", "tibia")
BODY_MESHES = ("body_head", "body_abdomen")
REQUIRED_MESHES = list(BODY_MESHES) + [
    f"leg_{leg:02d}_{seg}" for leg in LEGS for seg in SEGMENTS
]
KEY_FRAMES = (1, 10, 18, 21)


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


def find_rig():
    rigs = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    named = next((o for o in rigs if o.name == "rig_spider"), None)
    return named or (rigs[0] if rigs else None)


def image_report(img):
    return {
        "name": img.name,
        "size": list(img.size),
        "packed": bool(img.packed_file is not None),
        "filepath": img.filepath,
        "source": img.source,
    }


def compose(bone, pose_bone, parents):
    """World (armature-space) matrix of a pose bone."""
    return pose_bone.matrix


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_path = argv[0]
    sc = bpy.context.scene

    report = {
        "ok": True,
        "blender": bpy.app.version_string,
        "unit_system": sc.unit_settings.system,
        "unit_scale": float(sc.unit_settings.scale_length),
        "frame_start": sc.frame_start,
        "frame_end": sc.frame_end,
        "fps": sc.render.fps,
        "objects": {},
        "meshes": [],
        "cameras": {},
        "materials": {},
        "images": [],
        "libraries": [lib.filepath for lib in bpy.data.libraries],
        "polys_total": 0,
    }

    for ob in bpy.data.objects:
        entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None}
        if ob.type == 'MESH':
            entry["aabb"] = world_aabb(ob)
            entry["polys"] = evaluated_polys(ob)
            entry["materials"] = [m.name if m else None for m in ob.data.materials]
            entry["modifiers"] = [{"type": m.type,
                                   "object": getattr(getattr(m, "object", None), "name", None)}
                                  for m in ob.modifiers]
            entry["shape_keys"] = bool(ob.data.shape_keys)
            entry["vertex_groups"] = [g.name for g in ob.vertex_groups]
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
        info = {"name": mat.name, "metallic": None, "roughness": None}
        if mat.use_nodes:
            bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bsdf is not None:
                info["metallic"] = float(bsdf.inputs["Metallic"].default_value)
                info["roughness"] = float(bsdf.inputs["Roughness"].default_value)
        report["materials"][mat.name] = info

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        report["images"].append(image_report(img))

    # ---- armature ------------------------------------------------------
    rig = find_rig()
    report["rig"] = rig.name if rig else None
    bones = {}
    if rig is not None:
        for b in rig.data.bones:
            bones[b.name] = {
                "parent": b.parent.name if b.parent else None,
                "head": list(b.head_local),
                "tail": list(b.tail_local),
                "deform": bool(b.use_deform),
                "connected": bool(b.use_connect),
            }
        report["bones"] = bones
        report["bone_count"] = len(bones)
        report["pose_bone_rotation_modes"] = {pb.name: pb.rotation_mode for pb in rig.pose.bones}

    # ---- skinning ------------------------------------------------------
    skin = {}
    for name in REQUIRED_MESHES:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != 'MESH':
            skin[name] = {"present": False}
            continue
        deform = {b for b in bones if bones[b]["deform"]}
        mods = [m.object.name for m in ob.modifiers if m.type == 'ARMATURE' and m.object]
        unweighted = 0
        max_infl = 0
        sums = []
        for v in ob.data.vertices:
            groups = [g for g in v.groups
                      if g.group < len(ob.vertex_groups)
                      and ob.vertex_groups[g.group].name in deform and g.weight > 0.0]
            if not groups:
                unweighted += 1
                continue
            max_infl = max(max_infl, len(groups))
            sums.append(sum(g.weight for g in groups))
        skin[name] = {
            "present": True,
            "armature_modifiers": mods,
            "unweighted": unweighted,
            "max_influences": max_infl,
            "min_weight_sum": min(sums) if sums else 0.0,
            "max_weight_sum": max(sums) if sums else 0.0,
            "vertices": len(ob.data.vertices),
            "shape_keys": bool(ob.data.shape_keys),
        }
    report["skin"] = skin

    # ---- action --------------------------------------------------------
    action = None
    if rig is not None and rig.animation_data and rig.animation_data.action:
        action = rig.animation_data.action
    act = {"name": None}
    if action is not None:
        animated = set()
        keys = {}
        for fc in action.fcurves:
            path = fc.data_path
            if path.startswith('pose.bones["'):
                bone = path.split('"')[1]
                animated.add(bone)
                keys[bone] = keys.get(bone, 0) + len(fc.keyframe_points)
        frames = [kp.co[0] for fc in action.fcurves for kp in fc.keyframe_points]
        act = {
            "name": action.name,
            "frame_min": min(frames) if frames else None,
            "frame_max": max(frames) if frames else None,
            "animated_bones": sorted(animated),
            "key_counts": keys,
            "fcurves": len(action.fcurves),
        }
    report["action"] = act

    # ---- per-frame foot and body tracking ------------------------------
    feet = {}
    body_pos = []
    bone_pos = {b: [] for b in bones}
    if rig is not None:
        for frame in range(1, 26):
            sc.frame_set(frame)
            bpy.context.view_layer.update()
            mw = rig.matrix_world
            for leg in LEGS:
                name = f"leg_{leg:02d}_tibia"
                pb = rig.pose.bones.get(name)
                if pb is not None:
                    feet.setdefault(f"leg_{leg:02d}", []).append(list(mw @ pb.tail))
            pb = rig.pose.bones.get("body")
            if pb is not None:
                body_pos.append(list(mw @ pb.head))
            for b in bones:
                pb = rig.pose.bones.get(b)
                if pb is not None:
                    bone_pos[b].append(list(pb.matrix.translation))
        # loop seam
        sc.frame_set(1)
        bpy.context.view_layer.update()
        m1 = {b: rig.pose.bones[b].matrix.copy() for b in bones if b in rig.pose.bones}
        sc.frame_set(25)
        bpy.context.view_layer.update()
        seam_rot = 0.0
        seam_pos = 0.0
        for b, mat in m1.items():
            m25 = rig.pose.bones[b].matrix
            q1, q25 = mat.to_quaternion(), m25.to_quaternion()
            ang = math.degrees(q1.rotation_difference(q25).angle)
            seam_rot = max(seam_rot, ang)
            d = (mat.translation - m25.translation).length
            seam_pos = max(seam_pos, d)
        report["seam"] = {"max_rotation_deg": seam_rot, "max_translation_mm": seam_pos * 1000.0}
        sc.frame_set(1)

    report["feet"] = feet
    report["body_head"] = body_pos

    # ---- body bounds ---------------------------------------------------
    at_frame = {}
    for frame in KEY_FRAMES:
        sc.frame_set(frame)
        bpy.context.view_layer.update()
        for name in BODY_MESHES:
            ob = bpy.data.objects.get(name)
            if ob is not None:
                at_frame[f"{frame}:{name}"] = world_aabb(ob)
    report["body_aabb_keyframes"] = at_frame
    sc.frame_set(1)
    bpy.context.view_layer.update()

    # ---- self-intersection (femur/tibia only; coxae sit in sockets) ----
    coll = {}
    for frame in range(1, 25):
        sc.frame_set(frame)
        bpy.context.view_layer.update()
        parts = {}
        for leg in LEGS:
            for seg in ("femur", "tibia"):
                ob = bpy.data.objects.get(f"leg_{leg:02d}_{seg}")
                if ob is not None:
                    parts[(leg, seg)] = bvh_of(ob)
        body = {}
        for name in BODY_MESHES:
            ob = bpy.data.objects.get(name)
            if ob is not None:
                body[name] = bvh_of(ob)
        overlaps = 0
        pairs = []
        keys = list(parts)
        for i, (leg_a, seg_a) in enumerate(keys):
            for leg_b, seg_b in keys[i + 1:]:
                if leg_a == leg_b:
                    continue
                a, b = parts[(leg_a, seg_a)], parts[(leg_b, seg_b)]
                if a is not None and b is not None:
                    n = len(a.overlap(b))
                    if n:
                        overlaps += n
                        pairs.append([f"leg_{leg_a:02d}_{seg_a}", f"leg_{leg_b:02d}_{seg_b}", n])
            for name, b in body.items():
                a = parts[(leg_a, seg_a)]
                if a is not None and b is not None:
                    n = len(a.overlap(b))
                    if n:
                        overlaps += n
                        pairs.append([f"leg_{leg_a:02d}_{seg_a}", name, n])
        coll[str(frame)] = {"overlaps": overlaps, "pairs": pairs[:20]}
    report["collisions"] = coll
    sc.frame_set(1)

    # ---- material wiring for the texture -------------------------------
    packed_with_path = [i for i in report["images"] if i["filepath"]]
    report["images_with_path"] = packed_with_path
    report["unpacked_images"] = [i["name"] for i in packed_with_path if not i["packed"]]

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
