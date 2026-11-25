"""Authoring tool: builds the reference crate scene and its four renders.

Run with Blender 4.2.3:  blender -b -P build_crate.py -- <out_dir> <materials_dir>

This is authoring/reference tooling, not shipped to the agent and not used by
the verifier. The .blend it produces is the reference solution; every rubric
threshold in tests/grade.py was calibrated against this file.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector


# --------------------------------------------------------------------------
# numbers from the drawing pack (metres)
# --------------------------------------------------------------------------
W, D, H = 0.800, 0.600, 0.600     # outer envelope
T = 0.020                          # panel thickness
BODY_H = H - T                     # body top at 0.58, lid adds 0.02
BAND = 0.060                       # corner bracket leg length
BAND_T = 0.002                     # bracket plate thickness


def log(*a):
    print("[crate]", *a, flush=True)


# --------------------------------------------------------------------------
# helpers
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


def box(name, center, dims, bevel=0.003, segments=3):
    """Axis-aligned box; dimensions baked into the mesh (scale = 1)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * dims[0], v.co.y * dims[1], v.co.z * dims[2]))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = center
    bpy.context.collection.objects.link(ob)
    if bevel > 0:
        m = ob.modifiers.new("bevel", 'BEVEL')
        m.width = bevel
        m.segments = segments
        m.limit_method = 'ANGLE'
    return ob


def uv_cube(ob, scale=1.0):
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=scale, correct_aspect=True)
    bpy.ops.object.mode_set(mode='OBJECT')


# --------------------------------------------------------------------------
# procedural texture maps (numpy -> packed Blender images)
# --------------------------------------------------------------------------
def _smooth_noise(n, cells, rng):
    """Value noise on an n x n grid from a coarse random lattice."""
    g = rng.random((cells, cells))
    # bilinear upsample to n x n
    y = np.linspace(0, cells - 1, n)
    x = np.linspace(0, cells - 1, n)
    xi, yi = x.astype(int), y.astype(int)
    xi2, yi2 = np.minimum(xi + 1, cells - 1), np.minimum(yi + 1, cells - 1)
    fx, fy = (x - xi)[None, :], (y - yi)[:, None]
    a = g[yi][:, xi]
    b = g[yi][:, xi2]
    c = g[yi2][:, xi]
    d = g[yi2][:, xi2]
    top = a * (1 - fx) + b * fx
    bot = c * (1 - fx) + d * fx
    return top * (1 - fy) + bot * fy


def fbm(n, rng, octaves=5, base=8):
    out = np.zeros((n, n))
    amp, cells = 1.0, base
    for _ in range(octaves):
        out += amp * _smooth_noise(n, cells, rng)
        amp *= 0.5
        cells *= 2
    out /= out.max()
    return out


def save_image(name, rgb, path, colorspace='sRGB'):
    """rgb: (n, n, 3) float 0..1, origin bottom-left (Blender pixel order)."""
    n = rgb.shape[0]
    img = bpy.data.images.new(name, width=n, height=n, alpha=False)
    rgba = np.ones((n, n, 4), dtype=np.float32)
    rgba[..., :3] = rgb
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.colorspace_settings.name = colorspace
    img.save()
    img.pack()
    return img


def save_alpha_image(name, alpha, rgb, path):
    h, w = alpha.shape
    img = bpy.data.images.new(name, width=w, height=h, alpha=True)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = rgb
    rgba[..., 3] = alpha
    img.pixels.foreach_set(rgba.ravel())
    img.update()
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.colorspace_settings.name = 'sRGB'
    img.alpha_mode = 'STRAIGHT'
    img.save()
    img.pack()
    return img


def make_wood(n=2048):
    rng = np.random.default_rng(7)
    v = np.linspace(0, 1, n)
    uu, vv = np.meshgrid(v, v)
    warp = fbm(n, rng, octaves=4, base=6)
    # vertical grain running along the panel's U axis
    grain = np.sin((uu * 34.0 + 4.0 * warp) * 2 * math.pi)
    fine = fbm(n, rng, octaves=6, base=48)
    height = 0.55 * (grain * 0.5 + 0.5) + 0.45 * fine
    weather = fbm(n, rng, octaves=3, base=4)
    # weathered oak: grey-brown, desaturated where weather is high
    base = np.array([0.34, 0.24, 0.15])
    grey = np.array([0.43, 0.41, 0.37])
    w = np.clip((weather - 0.45) * 2.2, 0, 1)[..., None]
    albedo = base * (0.72 + 0.55 * height[..., None])
    albedo = albedo * (1 - w) + grey * (0.65 + 0.5 * height[..., None]) * w
    albedo = np.clip(albedo, 0, 1)
    rough = np.clip(0.58 + 0.22 * (height - 0.5) + 0.10 * (weather - 0.5), 0.35, 0.92)

    # normal from height gradient
    dy, dx = np.gradient(height)
    strength = 3.0
    nx, ny = -dx * strength, -dy * strength
    nz = np.ones_like(nx)
    ln = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    normal = np.stack([nx / ln, ny / ln, nz / ln], -1) * 0.5 + 0.5
    return albedo, rough, normal


def make_rust(n=2048):
    rng = np.random.default_rng(11)
    patch = fbm(n, rng, octaves=5, base=10)
    speck = fbm(n, rng, octaves=6, base=64)
    iron = np.array([0.16, 0.16, 0.17])
    rust = np.array([0.42, 0.20, 0.09])
    m = np.clip((patch * 0.75 + speck * 0.25 - 0.42) * 2.6, 0, 1)[..., None]
    albedo = np.clip(iron * (1 - m) + rust * (0.85 + 0.3 * speck[..., None]) * m, 0, 1)
    rough = np.clip(0.66 + 0.18 * speck + 0.08 * (patch - 0.5), 0.60, 0.90)
    return albedo, rough


# --------------------------------------------------------------------------
# stencil: render white text, erode it with noise
# --------------------------------------------------------------------------
def make_stencil_mask(materials_dir, n_w=2048, n_h=1024):
    tmp = os.path.join(materials_dir, "_tmp_stencil.png")
    scene = bpy.data.scenes.new("stencil_tmp")
    sc = bpy.context.window.scene
    bpy.context.window.scene = scene

    cam_data = bpy.data.cameras.new("sc")
    cam_data.type = 'ORTHO'
    cam_data.ortho_scale = 1.0
    cam = bpy.data.objects.new("sc", cam_data)
    cam.location = (0, 0, 3)
    scene.collection.objects.link(cam)
    scene.camera = cam

    cu = bpy.data.curves.new("txt", 'FONT')
    cu.body = "HANDLE\nWITH CARE"
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.size = 0.16
    cu.extrude = 0.0
    ob = bpy.data.objects.new("txt", cu)
    ob.location = (0, 0, 0)
    scene.collection.objects.link(ob)

    mat = bpy.data.materials.new("em")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    ob.data.materials.append(mat)

    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.film_transparent = True
    scene.render.resolution_x = n_w
    scene.render.resolution_y = n_h
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = tmp
    bpy.ops.render.render(write_still=True, scene=scene.name)

    img = bpy.data.images.load(tmp)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    alpha = px[..., 3].copy()
    bpy.data.images.remove(img)

    # wear: subtract a high-frequency noise field and hard-threshold, so the
    # letters lose their clean vector edge and pick up pinholes
    rng = np.random.default_rng(23)
    noise = fbm(max(w, h), rng, octaves=5, base=32)[:h, :w]
    worn = np.clip(alpha - (noise - 0.30) * 1.4, 0, 1)
    worn = (worn > 0.45).astype(np.float32) * 0.92
    # keep the interior of thick strokes intact, erode only near edges
    inner = (worn > 0) & (noise > 0.18)
    worn = np.where(inner, worn, 0.0)

    bpy.context.window.scene = sc
    bpy.data.scenes.remove(scene)
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    if os.path.exists(tmp):
        os.remove(tmp)
    return worn


# --------------------------------------------------------------------------
# scene construction
# --------------------------------------------------------------------------
def build_panels():
    objs = {}
    objs['crate_front'] = box("crate_front", (0, -D / 2 + T / 2, BODY_H / 2),
                              (W, T, BODY_H))
    objs['crate_back'] = box("crate_back", (0, D / 2 - T / 2, BODY_H / 2),
                             (W, T, BODY_H))
    objs['crate_left'] = box("crate_left", (-W / 2 + T / 2, 0, BODY_H / 2),
                             (T, D - 2 * T, BODY_H))
    objs['crate_right'] = box("crate_right", (W / 2 - T / 2, 0, BODY_H / 2),
                              (T, D - 2 * T, BODY_H))
    objs['crate_bottom'] = box("crate_bottom", (0, 0, T / 2), (W, D, T))
    return objs


def build_lid():
    """Lid pivots on an empty at the rear top edge."""
    hinge = bpy.data.objects.new("lid_hinge", None)
    hinge.empty_display_type = 'ARROWS'
    hinge.empty_display_size = 0.08
    hinge.location = (0, D / 2, BODY_H)
    bpy.context.collection.objects.link(hinge)

    # mesh is modelled in hinge-local space: extends -0.6 in y, 0..0.02 in z
    me = bpy.data.meshes.new("crate_lid")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * W, (v.co.y - 0.5) * D,
                       0.0005 + (v.co.z + 0.5) * T))
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("crate_lid", me)
    ob.parent = hinge
    ob.location = (0, 0, 0)
    bpy.context.collection.objects.link(ob)
    m = ob.modifiers.new("bevel", 'BEVEL')
    m.width = 0.003
    m.segments = 3
    m.limit_method = 'ANGLE'
    return hinge, ob


def build_brackets():
    """Eight 60x60x2 mm iron corner brackets, flush with the outer faces."""
    brackets = []
    idx = 0
    for sx in (-1, 1):
        for sy in (-1, 1):
            for z0, z1 in ((0.0, BAND), (BODY_H - BAND, BODY_H)):
                idx += 1
                name = f"bracket_{idx:02d}"
                # plate on the x face
                px = sx * (W / 2 - BAND_T / 2)
                plate_x = box(name + "_x", (px, sy * (D / 2 - BAND / 2), (z0 + z1) / 2),
                              (BAND_T, BAND, BAND), bevel=0.0015, segments=2)
                # plate on the y face, inset in x so the two plates do not z-fight
                py = sy * (D / 2 - BAND_T / 2)
                plate_y = box(name + "_y", (sx * (W / 2 - BAND / 2 - BAND_T), py, (z0 + z1) / 2),
                              (BAND - BAND_T, BAND_T, BAND), bevel=0.0015, segments=2)
                # join the two plates into one object
                bpy.ops.object.select_all(action='DESELECT')
                plate_x.select_set(True)
                plate_y.select_set(True)
                bpy.context.view_layer.objects.active = plate_x
                bpy.ops.object.join()
                plate_x.name = name
                plate_x.data.name = name
                brackets.append(plate_x)
    return brackets


def build_stencil(mask):
    """A 1 mm-thick painted plate on the front face carrying the worn mask."""
    n_h, n_w = mask.shape
    rgb = np.ones((n_h, n_w, 3), dtype=np.float32) * np.array([0.86, 0.85, 0.82])
    img = save_alpha_image("stencil_mask", mask, rgb, "/tmp/stencil_mask.png")

    ob = box("stencil_text", (0, -D / 2 - 0.0005, 0.42),
             (0.62, 0.001, 0.31), bevel=0.0)
    # direct UVs: x -> u, z -> v
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode='OBJECT')

    mat = bpy.data.materials.new("mat_stencil_paint")
    mat.use_nodes = True
    mat.blend_method = 'CLIP'
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.75
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    ob.data.materials.append(mat)
    return ob


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------
def add_uv(obj_names, scale=0.45):
    for name in obj_names:
        ob = bpy.data.objects.get(name)
        if ob:
            uv_cube(ob, scale)


def make_wood_material(wood, paths):
    albedo, rough, normal = wood
    name = "mat_weathered_oak"
    img_a = save_image("oak_basecolor", albedo, paths["oak_albedo"])
    img_r = save_image("oak_roughness", np.repeat(rough[..., None], 3, -1),
                       paths["oak_rough"], colorspace='Non-Color')
    img_n = save_image("oak_normal", normal, paths["oak_normal"], colorspace='Non-Color')

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    def tex(img, cs='sRGB'):
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = img
        t.interpolation = 'Linear'
        return t

    ta, tr, tn = tex(img_a), tex(img_r), tex(img_n)
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.inputs["Strength"].default_value = 1.0
    nt.links.new(ta.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    nt.links.new(tn.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Metallic"].default_value = 0.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_iron_material(rust, paths):
    albedo, rough = rust
    img_a = save_image("iron_basecolor", albedo, paths["iron_albedo"])
    img_r = save_image("iron_roughness", np.repeat(rough[..., None], 3, -1),
                       paths["iron_rough"], colorspace='Non-Color')
    mat = bpy.data.materials.new("mat_rusted_iron")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    ta = nt.nodes.new("ShaderNodeTexImage")
    ta.image = img_a
    tr = nt.nodes.new("ShaderNodeTexImage")
    tr.image = img_r
    nt.links.new(ta.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bsdf.inputs["Roughness"])
    bsdf.inputs["Metallic"].default_value = 1.0
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


# --------------------------------------------------------------------------
# world + lights + cameras
# --------------------------------------------------------------------------
def build_world(hdri_path):
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    img = bpy.data.images.load(hdri_path)
    img.pack()
    env.image = img
    bg.inputs["Strength"].default_value = 0.55
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def add_area(name, loc, rot, size, power, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.size = size
    ld.energy = power
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    ob.location = loc
    ob.rotation_euler = rot
    bpy.context.collection.objects.link(ob)
    return ob


def add_lights():
    add_area("light_key", (1.1, -1.2, 1.4), (math.radians(55), 0, math.radians(42)),
             1.5, 300, (1.0, 0.96, 0.90))
    add_area("light_fill", (-1.3, -0.6, 0.9), (math.radians(75), 0, math.radians(-60)),
             2.0, 90, (0.92, 0.95, 1.0))
    add_area("light_rim", (0.2, 1.4, 1.2), (math.radians(-50), 0, math.radians(170)),
             1.2, 140, (1.0, 0.98, 0.95))


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def add_cameras():
    cams = {}
    # front 3/4: 35 mm, 1.6 m from the crate, lens height 0.9 m
    cd = bpy.data.cameras.new("cam_front")
    cd.lens = 35
    cam = bpy.data.objects.new("cam_front", cd)
    cam.location = (1.13, -1.13, 0.90)
    bpy.context.collection.objects.link(cam)
    look_at(cam, (0, 0, 0.32))
    cams['front'] = cam

    cd = bpy.data.cameras.new("cam_back")
    cd.lens = 35
    cam = bpy.data.objects.new("cam_back", cd)
    cam.location = (-1.13, 1.13, 0.90)
    bpy.context.collection.objects.link(cam)
    look_at(cam, (0, 0, 0.32))
    cams['back'] = cam

    cd = bpy.data.cameras.new("cam_top")
    cd.type = 'ORTHO'
    cd.ortho_scale = 1.0
    cam = bpy.data.objects.new("cam_top", cd)
    cam.location = (0, 0, 3.0)
    look_at(cam, (0, 0, 0))
    bpy.context.collection.objects.link(cam)
    cams['top'] = cam

    cd = bpy.data.cameras.new("cam_macro")
    cd.lens = 100
    cam = bpy.data.objects.new("cam_macro", cd)
    corner = Vector((W / 2, -D / 2, 0.55))
    d = Vector((1.0, -1.0, 0.35)).normalized()
    cam.location = corner + d * 0.25
    bpy.context.collection.objects.link(cam)
    look_at(cam, corner)
    cams['macro'] = cam
    return cams


# --------------------------------------------------------------------------
# render + manifest
# --------------------------------------------------------------------------
RENDERS = [
    ("render_front", "front", (1600, 1200)),
    ("render_back", "back", (1600, 1200)),
    ("render_top", "top", (1600, 1280)),
    ("render_macro", "macro", (1600, 1200)),
]


def render_all(cams, out_dir):
    sc = bpy.context.scene
    for fname, cam_key, res in RENDERS:
        sc.camera = cams[cam_key]
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.resolution_percentage = 100
        sc.render.filepath = os.path.join(out_dir, fname + ".png")
        bpy.ops.render.render(write_still=True)
        log("rendered", fname)


def write_manifest(out_dir, assets):
    import json
    man = {
        "schemaVersion": 1,
        "units": "meters",
        "blenderVersion": bpy.app.version_string,
        "assets": assets,
        "renders": [
            {"file": f + ".png", "camera": "cam_" + c, "resolution": list(r), "samples": 64}
            for f, c, r in RENDERS
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(man, fh, indent=2)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    out_dir, materials_dir = argv[0], argv[1]
    tex_dir = os.path.join(out_dir, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    os.makedirs(materials_dir, exist_ok=True)

    reset_scene()
    paths = {
        "oak_albedo": os.path.join(tex_dir, "oak_basecolor.png"),
        "oak_rough": os.path.join(tex_dir, "oak_roughness.png"),
        "oak_normal": os.path.join(tex_dir, "oak_normal.png"),
        "iron_albedo": os.path.join(tex_dir, "iron_basecolor.png"),
        "iron_rough": os.path.join(tex_dir, "iron_roughness.png"),
    }

    panels = build_panels()
    add_uv(list(panels.keys()), scale=0.45)
    hinge, lid = build_lid()
    uv_cube(lid, scale=0.45)
    brackets = build_brackets()

    wood = make_wood()
    rust = make_rust()
    wood_mat = make_wood_material(wood, paths)
    iron_mat = make_iron_material(rust, paths)

    for ob in panels.values():
        ob.data.materials.append(wood_mat)
    lid.data.materials.append(wood_mat)
    for b in brackets:
        b.data.materials.append(iron_mat)

    mask = make_stencil_mask(materials_dir)
    build_stencil(mask)

    hdri = os.path.join(materials_dir, "hdri", "studio_soft.hdr")
    build_world(hdri)
    add_lights()

    # pack every image so the file survives without the materials directory
    for img in bpy.data.images:
        if img.source == 'FILE' and not img.packed_file:
            img.pack()

    cams = add_cameras()
    render_all(cams, out_dir)

    assets = [
        {"path": "textures/oak_basecolor.png", "role": "texture", "source": "self-authored", "license": "CC0-1.0", "url": ""},
        {"path": "textures/oak_roughness.png", "role": "texture", "source": "self-authored", "license": "CC0-1.0", "url": ""},
        {"path": "textures/oak_normal.png", "role": "texture", "source": "self-authored", "license": "CC0-1.0", "url": ""},
        {"path": "textures/iron_basecolor.png", "role": "texture", "source": "self-authored", "license": "CC0-1.0", "url": ""},
        {"path": "textures/iron_roughness.png", "role": "texture", "source": "self-authored", "license": "CC0-1.0", "url": ""},
        {"path": "textures/stencil_mask.png", "role": "texture", "source": "self-authored", "license": "CC0-1.0", "url": ""},
        {"path": "hdri/studio_soft.hdr", "role": "hdri", "source": "self-authored", "license": "CC0-1.0", "url": ""},
    ]
    write_manifest(out_dir, assets)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "crate.blend"), compress=True)
    log("saved", os.path.join(out_dir, "crate.blend"))


if __name__ == "__main__":
    main()
