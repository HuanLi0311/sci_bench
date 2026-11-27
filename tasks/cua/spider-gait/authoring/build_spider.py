"""Authoring tool: builds the reference spider scene, its renders and manifest.

Run with Blender 4.2.3:
    blender -b -P build_spider.py -- <solution_dir> <materials_dir>

Authoring only. Not shipped to the agent and never used by the verifier; the
.blend it writes is the reference solution and every threshold in
tests/grade.py was calibrated against this file.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spider_spec as S  # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1]
MATERIALS = sys.argv[sys.argv.index("--") + 2]
RENDER_DIR = OUT


def log(*a):
    print("[spider]", *a, flush=True)


# --------------------------------------------------------------------------
# scene scaffolding
# --------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = 'METERS'
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.cycles.seed = 0
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.fps = 24
    sc.frame_start = 1
    sc.frame_end = 24
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.05, 0.055, 0.06, 1.0)
    bg.inputs[1].default_value = 0.35
    sc.world = world


def link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def make_mesh(name):
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    return link(ob)


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def image_texture(path, name):
    img = bpy.data.images.load(path)
    img.name = name
    if img.colorspace_settings.name != 'sRGB':
        img.colorspace_settings.name = 'sRGB'
    return img


def chitin_material(name, image, tint):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.52
    bsdf.inputs["Base Color"].default_value = tint
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tex.location = (-420, 260)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 42.0
    noise.location = (-420, -40)
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.25
    bump.location = (-200, -40)
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def plain_material(name, colour, rough=0.6, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*colour, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------
def bevel_box(name, centre, dims, bevel=0.004, segments=2):
    ob = make_mesh(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segments,
                    affect='EDGES', clamp_overlap=True)
    bm.to_mesh(ob.data)
    bm.free()
    ob.location = centre
    return ob


def tube(name, p0, p1, r0, r1, sides=10):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    length = d.length
    ob = make_mesh(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=sides,
                          radius1=r0, radius2=r1, depth=length)
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized()).to_matrix().to_4x4()
    mat = Matrix.Translation((p0 + p1) * 0.5) @ rot
    bmesh.ops.transform(bm, matrix=mat, verts=bm.verts)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def joint(name, point, radius, sides=12):
    ob = make_mesh(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=sides, v_segments=max(6, sides // 2),
                              radius=radius)
    bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(point)), verts=bm.verts)
    bm.to_mesh(ob.data)
    bm.free()
    return ob


def assign(ob, material, bone):
    ob.data.materials.append(material)
    vg = ob.vertex_groups.new(name=bone)
    vg.add(list(range(len(ob.data.vertices))), 1.0, 'REPLACE')


# --------------------------------------------------------------------------
# rig
# --------------------------------------------------------------------------
def build_rig():
    arm = bpy.data.armatures.new("rig_spider")
    rig = bpy.data.objects.new("rig_spider", arm)
    link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm.edit_bones
    for name, parent, head, tail, _r, _deg in S.bone_table():
        bone = eb.new(name)
        bone.head = Vector(head)
        bone.tail = Vector(tail)
        if parent:
            bone.parent = eb[parent]
            bone.use_connect = name.endswith(("femur", "tibia"))
        if name != "body":
            bone.align_roll(Vector((0, 0, 1)))
        bone.use_deform = True
    bpy.ops.object.mode_set(mode='OBJECT')
    return rig


def build_pose():
    """Reference pose (frame 1..25) computed analytically from the gait table."""
    rig = bpy.data.objects["rig_spider"]
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    action = bpy.data.actions.new("Walk_Cycle")
    rig.animation_data_create()
    rig.animation_data.action = action

    rest_rot = {pb.name: pb.bone.matrix_local.to_quaternion() for pb in rig.pose.bones}

    def local_quat(name, world_axis, degrees):
        q = Quaternion(Vector(world_axis).normalized(), math.radians(degrees))
        rr = rest_rot[name]
        return rr.inverted() @ q @ rr

    for leg in range(1, 9):
        u, _deg = S.leg_direction(leg)
        lift_axis = Vector((u[1], -u[0], 0.0)).normalized()  # u x z
        p = S.PHASES[leg]
        names = [f"leg_{leg:02d}_coxa", f"leg_{leg:02d}_femur", f"leg_{leg:02d}_tibia"]
        for frame in range(1, 26):
            t = (frame - 1) % S.CYCLE
            s_in_swing = (t - (p + S.STANCE_FRAMES)) % S.CYCLE
            if s_in_swing < S.SWING_FRAMES:
                s = s_in_swing / S.SWING_FRAMES
                lift = math.sin(math.pi * s)
                qa = local_quat(names[0], lift_axis, S.SWING_LIFT_DEG * lift)
                qa = qa @ local_quat(names[0], (0, 0, 1), S.SWING_REACH_DEG * lift)
                qf = local_quat(names[1], lift_axis, S.SWING_KNEE_DEG * lift)
            else:
                qa = Quaternion((1, 0, 0, 0))
                qf = Quaternion((1, 0, 0, 0))
            rig.pose.bones[names[0]].rotation_quaternion = qa
            rig.pose.bones[names[1]].rotation_quaternion = qf
            rig.pose.bones[names[2]].rotation_quaternion = Quaternion((1, 0, 0, 0))
            for q, name in ((qa, names[0]), (qf, names[1]), (Quaternion((1, 0, 0, 0)), names[2])):
                rig.pose.bones[name].rotation_quaternion = q
                rig.pose.bones[name].keyframe_insert("rotation_quaternion", frame=frame)
    for fc in action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
    # Frame 1 and frame 25 must be identical by construction; assert it here so
    # a change to the phase table cannot silently break the loop.
    bpy.context.scene.frame_set(1)
    first = {pb.name: pb.matrix.copy() for pb in rig.pose.bones}
    bpy.context.scene.frame_set(25)
    worst = 0.0
    for pb in rig.pose.bones:
        m = pb.matrix
        worst = max(worst, max(abs(m[i][j] - first[pb.name][i][j]) for i in range(4) for j in range(4)))
    log("loop seam max matrix element delta", worst)
    bpy.context.scene.frame_set(1)
    return rig


# --------------------------------------------------------------------------
# world, lights, cameras
# --------------------------------------------------------------------------
def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def build_stage():
    ground_mat = plain_material("mat_ground", (0.22, 0.22, 0.235), 0.75)
    ob = make_mesh("ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.6)
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.materials.append(ground_mat)

    def area(name, loc, energy, size, colour=(1, 1, 1)):
        lamp = bpy.data.lights.new(name, 'AREA')
        lamp.energy = energy
        lamp.size = size
        lamp.color = colour
        o = bpy.data.objects.new(name, lamp)
        o.location = loc
        look_at(o, (0, 0.04, 0.08))
        return link(o)

    area("light_key", (0.55, 0.55, 0.62), 55.0, 0.9, (1.0, 0.96, 0.91))
    area("light_fill", (-0.65, 0.15, 0.42), 18.0, 1.2, (0.82, 0.88, 1.0))
    area("light_rim", (0.05, -0.75, 0.5), 26.0, 0.8, (1.0, 0.93, 0.85))

    cam_side = bpy.data.cameras.new("cam_side")
    cam_side.lens = 50.0
    cs = link(bpy.data.objects.new("cam_side", cam_side))
    cs.location = (0.75, 0.04, 0.13)
    look_at(cs, (0.0, 0.04, 0.070))

    cam_top = bpy.data.cameras.new("cam_top")
    cam_top.type = 'ORTHO'
    cam_top.ortho_scale = 0.5
    ct = link(bpy.data.objects.new("cam_top", cam_top))
    ct.location = (0.0, 0.04, 0.9)
    look_at(ct, (0.0, 0.04, 0.0))


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def render(cam, frame, path, width, height):
    sc = bpy.context.scene
    sc.camera = bpy.data.objects[cam]
    sc.render.resolution_x = width
    sc.render.resolution_y = height
    sc.render.resolution_percentage = 100
    sc.frame_set(frame)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    log("rendered", path)


def write_manifest():
    import json
    manifest = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": [
            {"path": "textures/chitin_basecolor.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": f"render_pose_{i:02d}.png", "camera": "cam_side",
             "resolution": [960, 540], "samples": 64} for i in range(1, 5)
        ] + [
            {"file": "render_top.png", "camera": "cam_top",
             "resolution": [960, 960], "samples": 64},
        ],
    }
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)


# --------------------------------------------------------------------------
def main():
    os.makedirs(OUT, exist_ok=True)
    reset_scene()

    tex_path = os.path.join(MATERIALS, "textures", "chitin_basecolor.png")
    image = image_texture(tex_path, "chitin_basecolor")
    image.pack()
    body_mat = chitin_material("mat_chitin", image, (0.42, 0.30, 0.22, 1.0))
    leg_mat = chitin_material("mat_leg_chitin", image, (0.30, 0.24, 0.19, 1.0))

    head = bevel_box("body_head", (0.0, 0.040, 0.121), (0.064, 0.100, 0.038))
    abdomen = bevel_box("body_abdomen", (0.0, -0.050, 0.120), (0.070, 0.080, 0.056))
    assign(head, body_mat, "body")
    assign(abdomen, body_mat, "body")

    for leg in range(1, 9):
        _deg, attach, ctail, ftail, foot = S.leg_points(leg)
        coxa = tube(f"leg_{leg:02d}_coxa", attach, ctail, 0.0065, 0.0055)
        femur = tube(f"leg_{leg:02d}_femur", ctail, ftail, 0.0055, 0.0042)
        tibia = tube(f"leg_{leg:02d}_tibia", ftail, foot, 0.0042, 0.0016)
        knee = joint(f"leg_{leg:02d}_knee", ftail, 0.0052)
        ankle = joint(f"leg_{leg:02d}_ankle", ctail, 0.0058)
        assign(coxa, leg_mat, f"leg_{leg:02d}_coxa")
        assign(femur, leg_mat, f"leg_{leg:02d}_femur")
        assign(tibia, leg_mat, f"leg_{leg:02d}_tibia")
        assign(knee, leg_mat, f"leg_{leg:02d}_femur")
        assign(ankle, leg_mat, f"leg_{leg:02d}_coxa")

    rig = build_rig()
    build_stage()
    build_pose()

    # Skinning: every mesh deforms with the armature; object origins stay at the
    # world origin so the rig owns the transform.
    for ob in list(bpy.data.objects):
        if ob.type == 'MESH' and ob.name != "ground":
            mod = ob.modifiers.new("Armature", 'ARMATURE')
            mod.object = rig
            mod.use_vertex_groups = True
            ob.parent = rig

    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "spider.blend"))
    log("saved blend")

    # Keep the packed texture next to the deliverable as well; the manifest
    # lists it and the .blend keeps its own copy.
    os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
    src = np.array(bpy.data.images["chitin_basecolor"].pixels[:], dtype=np.float32)
    w, h = bpy.data.images["chitin_basecolor"].size
    rgb = (np.clip(src.reshape(h, w, 4)[..., :3], 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)[::-1]
    import packgen
    with open(os.path.join(OUT, "textures", "chitin_basecolor.png"), "wb") as fh:
        fh.write(packgen.encode_png(rgb))

    poses = [(1, "01"), (10, "02"), (18, "03"), (21, "04")]
    for frame, tag in poses:
        render("cam_side", frame, os.path.join(RENDER_DIR, f"render_pose_{tag}.png"), 960, 540)
    render("cam_top", 1, os.path.join(RENDER_DIR, "render_top.png"), 960, 960)
    write_manifest()
    log("done")


if __name__ == "__main__":
    main()
