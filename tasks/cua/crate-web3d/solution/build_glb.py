"""Build the reference crate as a .glb, plus its four camera renders.

    python3 build_glb.py <out_dir> [--no-render]

The scene mirrors crate-lookdev exactly (800 x 600 x 600 mm, 20 mm panels,
rear-hinged lid, eight 60 x 60 x 2 mm brackets, worn stencil), but is written
as glTF 2.0 instead of a .blend.
"""
import json
import math
import os
import struct
import subprocess
import sys

W, D, H = 0.800, 0.600, 0.600
T = 0.020
BODY_H = H - T
BAND, BAND_T = 0.060, 0.002
HINGE = (0.0, D / 2, BODY_H)
LENS = 35.0
SENSOR_H = 13.5           # 36 mm sensor, 4:3 frame
RENDER_W, RENDER_H = 1200, 900


# ----------------------------------------------------------------- geometry
def box_mesh(lo, hi):
    """Axis-aligned box: positions, normals, indices (36 indices)."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    pos = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    idx = []
    for a, b, c, d in faces:
        idx += [a, b, c, a, c, d]
    return pos, idx


def box(lo, hi):
    """Box as (positions, indices) with flat normals."""
    pos, idx = box_mesh(lo, hi)
    normals = []
    for i in range(0, len(idx), 3):
        p0 = pos[idx[i]]
        p1 = pos[idx[i + 1]]
        p2 = pos[idx[i + 2]]
        u = [p1[k] - p0[k] for k in range(3)]
        v = [p2[k] - p0[k] for k in range(3)]
        n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
        ln = math.sqrt(sum(c * c for c in n)) or 1.0
        normals.append([c / ln for c in n])
    return pos, normals, idx


def merge(parts):
    """Concatenate several boxes into one mesh with per-face normals."""
    positions, normals, indices = [], [], []
    for pos, nrm, idx in parts:
        off = len(positions)
        positions += [list(p) for p in pos]
        for i in range(len(idx)):
            normals.append(nrm[i // 3])
        indices += [i + off for i in idx]
    return positions, normals, indices


# ------------------------------------------------------------------ look-at
def quat_from_matrix(m):
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (m[2][1] - m[1][2]) / s
        y = (m[0][2] - m[2][0]) / s
        z = (m[1][0] - m[0][1]) / s
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2
        w = (m[2][1] - m[1][2]) / s
        x = 0.25 * s
        y = (m[0][1] + m[1][0]) / s
        z = (m[0][2] + m[2][0]) / s
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2
        w = (m[0][2] - m[2][0]) / s
        x = (m[0][1] + m[1][0]) / s
        y = 0.25 * s
        z = (m[1][2] + m[2][1]) / s
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2
        w = (m[1][0] - m[0][1]) / s
        x = (m[0][2] + m[2][0]) / s
        y = (m[1][2] + m[2][1]) / s
        z = 0.25 * s
    return [x, y, z, w]


def look_at(eye, target, up=(0, 0, 1)):
    f = [target[i] - eye[i] for i in range(3)]
    ln = math.sqrt(sum(c * c for c in f)) or 1.0
    f = [c / ln for c in f]
    z = [-f[0], -f[1], -f[2]]                       # camera +Z points back
    x = [up[1] * z[2] - up[2] * z[1], up[2] * z[0] - up[0] * z[2], up[0] * z[1] - up[1] * z[0]]
    ln = math.sqrt(sum(c * c for c in x)) or 1.0
    x = [c / ln for c in x]
    y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]]
    m = [[x[0], y[0], z[0]], [x[1], y[1], z[1]], [x[2], y[2], z[2]]]
    return quat_from_matrix(m)


# ------------------------------------------------------------------ glb write
class Glb:
    def __init__(self):
        self.bin = bytearray()
        self.buffer_views = []
        self.accessors = []
        self.meshes = []
        self.nodes = []
        self.materials = []
        self.images = []
        self.textures = []
        self.cameras = []
        self.samplers = []

    def _pad(self):
        while len(self.bin) % 4:
            self.bin.append(0)

    def add_view(self, data, target=None):
        self._pad()
        off = len(self.bin)
        self.bin += data
        view = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target:
            view["target"] = target
        self.buffer_views.append(view)
        return len(self.buffer_views) - 1

    def add_mesh(self, positions, normals, indices, material):
        pos = b"".join(struct.pack("<3f", *p) for p in positions)
        nrm = b"".join(struct.pack("<3f", *n) for n in normals)
        idx = b"".join(struct.pack("<I", i) for i in indices)
        vp = self.add_view(pos, 34962)
        vn = self.add_view(nrm, 34962)
        vi = self.add_view(idx, 34963)
        lo = [min(p[k] for p in positions) for k in range(3)]
        hi = [max(p[k] for p in positions) for k in range(3)]
        ap = len(self.accessors)
        self.accessors.append({"bufferView": vp, "componentType": 5126, "count": len(positions),
                               "type": "VEC3", "min": lo, "max": hi})
        an = len(self.accessors)
        self.accessors.append({"bufferView": vn, "componentType": 5126, "count": len(normals),
                               "type": "VEC3"})
        ai = len(self.accessors)
        self.accessors.append({"bufferView": vi, "componentType": 5125, "count": len(indices),
                               "type": "SCALAR"})
        self.meshes.append({"name": "mesh_" + str(len(self.meshes)),
                            "primitives": [{"attributes": {"POSITION": ap, "NORMAL": an},
                                            "indices": ai, "material": material}]})
        return len(self.meshes) - 1

    def add_node(self, name, mesh=None, translation=None, rotation=None,
                 children=None, camera=None):
        node = {"name": name}
        if mesh is not None:
            node["mesh"] = mesh
        if translation:
            node["translation"] = list(translation)
        if rotation:
            node["rotation"] = list(rotation)
        if children:
            node["children"] = children
        if camera is not None:
            node["camera"] = camera
        self.nodes.append(node)
        return len(self.nodes) - 1

    def add_image_png(self, png_bytes, name):
        view = self.add_view(png_bytes)
        self.images.append({"name": name, "bufferView": view, "mimeType": "image/png"})
        self.textures.append({"source": len(self.images) - 1, "sampler": 0})
        return len(self.textures) - 1

    def write(self, path):
        self._pad()
        doc = {
            "asset": {"version": "2.0", "generator": "crate-web3d reference builder"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "accessors": self.accessors,
            "bufferViews": self.buffer_views,
            "buffers": [{"byteLength": len(self.bin)}],
            "materials": self.materials,
            "cameras": self.cameras,
        }
        if self.samplers:
            doc["samplers"] = self.samplers
        else:
            doc["samplers"] = [{"magFilter": 9729, "minFilter": 9987,
                                "wrapS": 10497, "wrapT": 10497}]
        if self.images:
            doc["images"] = self.images
            doc["textures"] = self.textures
        js = json.dumps(doc, separators=(",", ":")).encode("utf-8")
        while len(js) % 4:
            js += b" "
        total = 12 + 8 + len(js) + 8 + len(self.bin)
        with open(path, "wb") as fh:
            fh.write(struct.pack("<4sII", b"glTF", 2, total))
            fh.write(struct.pack("<II", len(js), 0x4E4F534A))
            fh.write(js)
            fh.write(struct.pack("<II", len(self.bin), 0x004E4942))
            fh.write(bytes(self.bin))
        return doc


def stencil_png(path, w=1024, h=512):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
    d.multiline_text((w // 2, h // 2), "HANDLE\nWITH CARE", font=font,
                     fill=(255, 255, 255, 235), anchor="mm", align="center", spacing=24)
    img.save(path)
    return path


def main():
    out_dir = sys.argv[1]
    no_render = "--no-render" in sys.argv
    os.makedirs(out_dir, exist_ok=True)
    tex_dir = os.path.join(out_dir, "textures")
    os.makedirs(tex_dir, exist_ok=True)

    g = Glb()
    oak = {"name": "mat_weathered_oak", "pbrMetallicRoughness": {
        "baseColorFactor": [0.30, 0.22, 0.14, 1.0], "metallicFactor": 0.0,
        "roughnessFactor": 0.72}}
    iron = {"name": "mat_rusted_iron", "pbrMetallicRoughness": {
        "baseColorFactor": [0.35, 0.25, 0.20, 1.0], "metallicFactor": 1.0,
        "roughnessFactor": 0.80}}
    png_path = stencil_png(os.path.join(tex_dir, "stencil_mask.png"))
    tex = g.add_image_png(open(png_path, "rb").read(), "stencil_mask")
    paint = {"name": "mat_stencil_paint", "alphaMode": "MASK", "alphaCutoff": 0.4,
             "pbrMetallicRoughness": {"baseColorTexture": {"index": tex},
                                      "metallicFactor": 0.0, "roughnessFactor": 0.9}}
    g.materials += [oak, iron, paint]

    # panels, absolute coordinates
    panels = {
        "crate_bottom": ((-W / 2, -D / 2, 0.0), (W / 2, D / 2, T)),
        "crate_front": ((-W / 2, -D / 2, T), (W / 2, -D / 2 + T, BODY_H)),
        "crate_back": ((-W / 2, D / 2 - T, T), (W / 2, D / 2, BODY_H)),
        "crate_left": ((-W / 2, -D / 2 + T, T), (-W / 2 + T, D / 2 - T, BODY_H)),
        "crate_right": ((W / 2 - T, -D / 2 + T, T), (W / 2, D / 2 - T, BODY_H)),
    }
    mesh_ids = {}
    for name, (lo, hi) in panels.items():
        mesh_ids[name] = g.add_mesh(*box(lo, hi), material=0)

    # lid, local to its hinge
    lid_lo = (-W / 2, -D, 0.0005)
    lid_hi = (W / 2, 0.0, 0.0005 + T)
    lid_mesh = g.add_mesh(*box(lid_lo, lid_hi), material=0)

    # brackets: L of two 60 x 60 x 2 plates, 1 mm proud
    bracket_meshes = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for z0, z1 in ((0.0, BAND), (BODY_H - BAND, BODY_H)):
                x_face = sx * (W / 2 + 0.001)
                y_face = sy * (D / 2 + 0.001)
                plate_x = box(
                    (min(x_face, x_face - sx * BAND_T), sy * (D / 2 - BAND), z0),
                    (max(x_face, x_face - sx * BAND_T), sy * (D / 2), z1))
                y_in = sx * (W / 2 - BAND + 0.001)
                plate_y = box(
                    (min(y_face, y_face - sy * BAND_T), min(y_in, y_in + sx * 0.002), z0),
                    (max(y_face, y_face - sy * BAND_T), max(y_in, y_in + sx * 0.002), z1))
                bracket_meshes.append(g.add_mesh(*merge([plate_x, plate_y]), material=1))

    # stencil: thin plate 1 mm off the front face
    st_lo = (-0.31, -D / 2 - 0.0016, 0.265)
    st_hi = (0.31, -D / 2 - 0.0006, 0.575)
    stencil_mesh = g.add_mesh(*box(st_lo, st_hi), material=2)

    # node tree
    hinge_idx = g.add_node("lid_hinge", translation=HINGE)
    lid_idx = g.add_node("crate_lid", mesh=lid_mesh, translation=(0, 0, 0))
    g.nodes[hinge_idx]["children"] = [lid_idx]

    root_children = []
    for name in panels:
        root_children.append(g.add_node(name, mesh=mesh_ids[name]))
    root_children.append(hinge_idx)
    for i, m in enumerate(bracket_meshes, 1):
        root_children.append(g.add_node(f"bracket_{i:02d}", mesh=m))
    root_children.append(g.add_node("stencil_text", mesh=stencil_mesh))

    # cameras
    yfov = 2 * math.atan(SENSOR_H / LENS)
    cams = {
        "cam_front": dict(eye=(1.13, -1.13, 0.90), target=(0, 0, 0.32),
                          cam={"type": "perspective", "perspective": {"yfov": yfov, "znear": 0.01, "zfar": 100}}),
        "cam_back": dict(eye=(-1.13, 1.13, 0.90), target=(0, 0, 0.32),
                         cam={"type": "perspective", "perspective": {"yfov": yfov, "znear": 0.01, "zfar": 100}}),
        "cam_top": dict(eye=(0, 0, 3.0), target=(0, 0, 0),
                        cam={"type": "orthographic", "orthographic": {
                            "xmag": 0.5, "ymag": 0.375, "znear": 0.01, "zfar": 100}}),
        "cam_macro": dict(eye=(0.58, -0.48, 0.62), target=(0.40, -0.30, 0.55),
                          cam={"type": "perspective", "perspective": {"yfov": 2 * math.atan(6.0 / 100), "znear": 0.01, "zfar": 100}}),
    }
    for name, spec in cams.items():
        g.cameras.append(spec["cam"])
        idx = g.add_node(name, translation=spec["eye"], camera=len(g.cameras) - 1,
                         rotation=look_at(spec["eye"], spec["target"]))
        root_children.append(idx)

    g.nodes.insert(0, {"name": "crate_root", "children": root_children})
    # every later node index shifts by one
    for n in g.nodes[1:]:
        if "children" in n:
            n["children"] = [c + 1 for c in n["children"]]
    g.scenes = [{"nodes": [0]}]

    glb_path = os.path.join(out_dir, "crate.glb")
    g.write(glb_path)
    print("[glb] wrote", glb_path, os.path.getsize(glb_path), "bytes")

    if no_render:
        return

    for cam in ("front", "back", "top", "macro"):
        out = os.path.join(out_dir, f"render_{cam}.png")
        subprocess.run(["node", os.path.join(os.path.dirname(__file__), "render_views.js"),
                        glb_path, f"cam_{cam}", out, str(RENDER_W), str(RENDER_H)],
                       check=True)
        print("[glb] rendered", cam)

    manifest = {
        "schemaVersion": 1,
        "units": "meters",
        "generator": "glTF 2.0 binary",
        "assets": [
            {"path": "textures/stencil_mask.png", "role": "texture",
             "source": "self-authored", "license": "CC0-1.0", "url": ""},
        ],
        "renders": [
            {"file": f"render_{c}.png", "camera": f"cam_{c}",
             "resolution": [RENDER_W, RENDER_H]} for c in ("front", "back", "top", "macro")
        ],
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)


if __name__ == "__main__":
    main()
