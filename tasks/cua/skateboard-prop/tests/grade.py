"""Grader for skateboard-prop.

Usage: python3 grade.py /app/out
Exit 0 -> reward 1. Every `must` and `critical` check must pass and at least
80% of the `normal` checks.
"""
import hashlib
import json
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import traceback

import numpy as np
from PIL import Image
from render_compare import gradient_error

BLENDER = shutil.which("blender") or "/usr/local/bin/blender"
CHECKS = []
os.makedirs("/logs/verifier", exist_ok=True)
WORK = tempfile.mkdtemp(prefix="work-", dir="/logs/verifier")

PARTS = ["deck", "truck_front", "truck_rear", "wheel_01", "wheel_02",
         "wheel_03", "wheel_04", "bearings"]
RENDERS = {
    "render_three_quarter.png": "cam_three_quarter",
    "render_bottom.png": "cam_bottom",
    "render_edge.png": "cam_edge",
}
SIZES = {"render_three_quarter.png": (1600, 1200),
         "render_bottom.png": (1600, 900),
         "render_edge.png": (1600, 1200)}


def add(cid, level, ok, detail=""):
    CHECKS.append({"id": cid, "level": level, "pass": bool(ok), "detail": str(detail)})
    return ok


def record(cmd, result):
    with open("/logs/verifier/blender-processes.jsonl", "a") as fh:
        fh.write(json.dumps({"command": cmd, "returncode": result.returncode,
                             "stdout": result.stdout[-4000:],
                             "stderr": result.stderr[-4000:]}) + "\n")


def run(cmd, timeout):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    record(cmd, r)
    r.check_returncode()
    return r


def ss_img(a, b):
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    if a.shape != b.shape:
        return 0.0
    win = 8
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2

    def box(x):
        h, w = x.shape
        h2, w2 = h - h % win, w - w % win
        return x[:h2, :w2].reshape(h2 // win, win, w2 // win, win).mean(axis=(1, 3))

    ma, mb = box(a), box(b)
    va = box(a * a) - ma ** 2
    vb = box(b * b) - mb ** 2
    cov = box(a * b) - ma * mb
    num = (2 * ma * mb + c1) * (2 * cov + c2)
    den = (ma ** 2 + mb ** 2 + c1) * (va + vb + c2)
    return float((num / den).mean())


def load_gray(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float32).mean(-1)


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def glb_json(path):
    with open(path, "rb") as fh:
        header = fh.read(12)
        magic, version, length = struct.unpack("<4sII", header)
        if magic != b"glTF":
            raise ValueError("not a GLB")
        chunk_len, chunk_type = struct.unpack("<II", fh.read(8))
        if chunk_type != 0x4E4F534A:
            raise ValueError("first chunk is not JSON")
        return json.loads(fh.read(chunk_len).decode("utf-8"))


def col_distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# --------------------------------------------------------------------------
def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "skateboard.blend")
    scene = {}
    scene_ok = False
    if os.path.exists(blend):
        try:
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", blend,
                 "--python", "/tests/check_scene.py", "--", os.path.join(WORK, "scene.json")],
                timeout=900)
            with open(os.path.join(WORK, "scene.json")) as fh:
                scene = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            scene_ok = bool(scene.get("ok"))
        except Exception as exc:
            print("check_scene failed:", exc, file=sys.stderr)

    add("R01_open", "must", scene_ok and str(scene.get("blender", "")).startswith("4."),
        scene.get("blender", "unreadable"))

    deck = scene.get("deck") or {}
    wheels = scene.get("wheels") or {}
    trucks = scene.get("trucks") or {}
    aabb = deck.get("aabb") or [[0, 0, 0], [0, 0, 0]]
    length = (aabb[1][0] - aabb[0][0]) * 1000
    width = (aabb[1][1] - aabb[0][1]) * 1000
    thickness = deck.get("thickness_mm", 0)
    wheelbase = 0.0
    if "truck_front" in trucks and "truck_rear" in trucks:
        wheelbase = abs(trucks["truck_front"]["centre"][0] - trucks["truck_rear"]["centre"][0]) * 1000
    wheel_dia = np.mean([w["diameter_mm"] for w in wheels.values()]) if wheels else 0
    z_extent = deck.get("z_extent_mm", 0)
    concave = deck.get("concave_mm", 0)
    dims_ok = (abs(length - 800) <= 3 and abs(width - 200) <= 2
               and abs(thickness - 12) <= 1 and abs(wheelbase - 440) <= 3
               and abs(wheel_dia - 54) <= 1
               and 45 <= z_extent <= 90 and abs(concave - 8) <= 2)
    add("R02_dimensions", "must", dims_ok,
        f"deck={length:.1f}x{width:.1f}x{thickness:.2f}mm wheelbase={wheelbase:.1f} "
        f"wheel_dia={wheel_dia:.1f} kick_z={z_extent:.1f}mm concave={concave:.1f}mm")

    present = scene.get("parts_present") or {}
    objs = scene.get("objects") or {}
    parents_ok = (objs.get("truck_front", {}).get("parent") == "deck"
                  and objs.get("truck_rear", {}).get("parent") == "deck"
                  and objs.get("wheel_01", {}).get("parent") == "truck_front"
                  and objs.get("wheel_02", {}).get("parent") == "truck_front"
                  and objs.get("wheel_03", {}).get("parent") == "truck_rear"
                  and objs.get("wheel_04", {}).get("parent") == "truck_rear")
    add("R03_parts", "must", all(present.get(p) for p in PARTS) and parents_ok,
        f"missing={[p for p in PARTS if not present.get(p)]} parents="
        f"{ {k: objs.get(k, {}).get('parent') for k in ('truck_front', 'wheel_01', 'bearings')} }")

    mats = scene.get("materials") or {}
    bands = deck.get("bands") or {}
    ply_counts = {}
    band_thin = []
    ply_colours = []
    for side in ("left", "right"):
        entries = bands.get(side) or {}
        ply_counts[side] = len(entries)
        for k, v in entries.items():
            if not (1.0 <= v.get("thickness_mm", 0) <= 2.6):
                band_thin.append(f"{side}:{k}:{v.get('thickness_mm'):.2f}mm")
    slot_mats = [m for m in (deck.get("material_slots") or []) if m]
    for name in slot_mats:
        c = (mats.get(name) or {}).get("base_color")
        if c:
            ply_colours.append(c)
    distinct_colours = 0
    for i, a in enumerate(ply_colours):
        if all(col_distance(a, b) > 0.05 for j, b in enumerate(ply_colours) if i != j):
            distinct_colours += 1
    plies_ok = (min(ply_counts.values() or [0]) >= 7 and not band_thin
                and distinct_colours >= 7 and len(slot_mats) >= 7)
    add("R04_plies", "must", plies_ok,
        f"bands_per_side={ply_counts} thin={band_thin[:4]} distinct_colours={distinct_colours}")

    graphic_img = None
    for name in slot_mats:
        imgs = (mats.get(name) or {}).get("images") or []
        if imgs:
            graphic_img = imgs[0]
            break
    uv_area = deck.get("uv_area", 0)
    uv_bbox = deck.get("uv_bbox") or [[0, 0], [0, 0]]
    uv_ok = (graphic_img is not None and graphic_img.get("size") == [2048, 512]
             and 0.95 <= uv_area <= 1.02
             and uv_bbox[0][0] <= 0.05 and uv_bbox[0][1] <= 0.05
             and uv_bbox[1][0] >= 0.95 and uv_bbox[1][1] >= 0.95
             and deck.get("bottom_faces", 0) >= 1000)
    add("R05_graphic_uv", "must", uv_ok,
        f"image={graphic_img} uv_area={uv_area:.3f} bbox={uv_bbox} bottom_faces={deck.get('bottom_faces')}")

    imgs = scene.get("images") or []
    textured = [i for i in imgs if i.get("filepath")]
    tex_ok = (bool(textured)
              and all(max(i["size"]) <= 2048 for i in textured)
              and all(i.get("packed") for i in textured)
              and not (scene.get("unpacked_images") or [])
              and not (scene.get("libraries") or []))
    add("R06_textures", "must", tex_ok,
        f"images={[(i['name'], i['size'], i['packed']) for i in textured]}")

    truck_metallic = None
    wheel_rough = None
    grip_rough = None
    for ob_name in ("truck_front", "truck_rear"):
        mat_names = [m for m in (objs.get(ob_name, {}).get("materials") or []) if m]
        vals = [(mats.get(m) or {}).get("metallic") for m in mat_names]
        vals = [v for v in vals if v is not None]
        if vals:
            truck_metallic = max(truck_metallic or 0, max(vals))
    for ob_name in ("wheel_01", "wheel_02", "wheel_03", "wheel_04"):
        mat_names = [m for m in (objs.get(ob_name, {}).get("materials") or []) if m]
        vals = [(mats.get(m) or {}).get("roughness") for m in mat_names]
        vals = [v for v in vals if v is not None]
        if vals:
            wheel_rough = max(wheel_rough or 0, max(vals))
    deck_mats = [m for m in (deck.get("material_slots") or []) if m]
    grip_rough = max([(mats.get(m) or {}).get("roughness") or 0 for m in deck_mats] or [0])
    mat_ok = ((truck_metallic or 0) >= 0.8
              and wheel_rough is not None and 0.5 <= wheel_rough <= 0.8
              and grip_rough >= 0.85)
    add("R07_materials", "normal", mat_ok,
        f"truck_metallic={truck_metallic} wheel_roughness={wheel_rough} grip_roughness={grip_rough}")

    glb = os.path.join(out, "skateboard.glb")
    glb_size = os.path.getsize(glb) if os.path.exists(glb) else 0
    png_count = 0
    add("R08_glb", "must", 0 < glb_size <= 15 * 1024 * 1024,
        f"{glb_size/1e6:.1f} MB")

    glb_report = {}
    glb_meta = {}
    if glb_size:
        try:
            glb_meta = glb_json(glb)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b",
                 "--factory-startup", "--python", "/tests/check_glb.py", "--", glb,
                 os.path.join(WORK, "glb.json")], timeout=600)
            with open(os.path.join(WORK, "glb.json")) as fh:
                glb_report = json.load(fh)
        except Exception as exc:
            print("glb check failed:", exc, file=sys.stderr)

    imported = set(glb_report.get("meshes") or [])
    glb_mats = len(glb_report.get("materials") or [])
    embedded = all(("bufferView" in i and "uri" not in i) for i in glb_meta.get("images", []))
    tri_ratio = (abs((glb_report.get("polys_total") or 0) - (scene.get("polys_total") or 1))
                 / max(scene.get("polys_total") or 1, 1))
    # The task promises an engine-ready hierarchy.  Checking mesh names alone
    # accepts a flattened export, which loses the truck/wheel relationships.
    expected_glb_parents = {
        "deck": None,
        "truck_front": "deck", "truck_rear": "deck",
        "wheel_01": "truck_front", "wheel_02": "truck_front",
        "wheel_03": "truck_rear", "wheel_04": "truck_rear",
        "bearings": "deck",
    }
    glb_objects = glb_report.get("objects") or {}
    hierarchy_bad = [
        f"{name}->{(glb_objects.get(name) or {}).get('parent')}"
        for name, parent in expected_glb_parents.items()
        if name not in glb_objects or (glb_objects.get(name) or {}).get("parent") != parent
    ]
    hierarchy_ok = not hierarchy_bad
    rt_ok = (bool(glb_report.get("ok"))
             and set(PARTS) <= imported
             and hierarchy_ok
             and tri_ratio <= 0.01
             and glb_mats >= 7
             and bool(glb_meta.get("images"))
             and embedded
             and len(glb_meta.get("meshes", [])) >= 1)
    add("R09_glb_roundtrip", "must", rt_ok,
        f"imported={sorted(imported)[:9]} tri_diff={tri_ratio:.4f} glb_materials={glb_mats} "
        f"images={len(glb_meta.get('images', []))} embedded={embedded} "
        f"hierarchy={'ok' if hierarchy_ok else hierarchy_bad[:4]}")

    add("R10_polys", "normal", (scene.get("polys_total") or 10 ** 9) <= 40000,
        f"{scene.get('polys_total')} triangles")

    rear = None
    if "wheel_03" in wheels and "wheel_04" in wheels:
        c3, c4 = wheels["wheel_03"]["centre"], wheels["wheel_04"]["centre"]
        rear = [(c3[i] + c4[i]) / 2 for i in range(3)]
    origin_ok = (rear is not None and math.hypot(rear[0], rear[1]) <= 0.005
                 and abs(rear[2]) <= 0.005
                 and math.hypot(*deck.get("origin", [9, 9, 9])[:2]) <= 0.005)
    add("R11_origin", "must", origin_ok,
        f"rear_axle={[round(c, 4) for c in rear] if rear else None} "
        f"deck_origin={[round(c, 4) for c in deck.get('origin', [])]}")

    renders_ok = True
    detail = []
    hashes = []
    for name, (w, h) in SIZES.items():
        path = os.path.join(out, name)
        if not os.path.exists(path):
            renders_ok = False
            detail.append(f"{name}:missing")
            continue
        try:
            iw, ih = Image.open(path).size
        except Exception:
            renders_ok = False
            detail.append(f"{name}:unreadable")
            continue
        hashes.append(file_sha(path))
        detail.append(f"{name}:{iw}x{ih}")
        if (iw, ih) != (w, h):
            renders_ok = False
    distinct = len(set(hashes)) == len(hashes) == len(RENDERS)

    cams = scene.get("cameras") or {}
    cam_detail = []
    deck_centre = [(aabb[0][i] + aabb[1][i]) / 2 for i in range(3)]
    tq = cams.get("cam_three_quarter")
    tq_ok = False
    if tq:
        loc = tq["location"]
        horiz = math.hypot(loc[0] - deck_centre[0], loc[1] - deck_centre[1])
        tq_ok = abs(tq.get("lens", 0) - 35) <= 1 and abs(horiz - 1.2) <= 0.06 and abs(loc[2] - 0.8) <= 0.05
        cam_detail.append(f"3q lens={tq.get('lens')} horiz={horiz:.3f} z={loc[2]:.3f}")
    else:
        cam_detail.append("cam_three_quarter missing")
    cb = cams.get("cam_bottom")
    bottom_ok = bool(cb) and cb.get("type") == "ORTHO" and abs(cb.get("ortho_scale", 0) - 0.9) <= 0.01 \
        and cb["location"][2] < 0
    cam_detail.append(f"bottom={cb and (cb.get('type'), cb.get('ortho_scale'))}")
    ce = cams.get("cam_edge")
    edge_ok = False
    if ce:
        loc = ce["location"]
        dist = math.hypot(loc[0] - 0.22, loc[1] - 0.10, loc[2] - 0.036)
        edge_ok = abs(ce.get("lens", 0) - 100) <= 5 and abs(dist - 0.25) <= 0.06
        cam_detail.append(f"edge lens={ce.get('lens')} dist={dist:.3f}")
    else:
        cam_detail.append("cam_edge missing")
    add("R12_renders", "must", renders_ok and distinct and tq_ok and bottom_ok and edge_ok,
        " ".join(detail) + f" distinct={distinct} " + " ".join(cam_detail))

    man_ok, m_detail = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp) as fh:
                man = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            assets = man.get("assets", [])
            licensed = [a for a in assets if a.get("source") and a.get("license")]
            listed = {r.get("file") for r in man.get("renders", [])}
            man_ok = (len(assets) >= 1 and len(licensed) == len(assets)
                      and any(a.get("role") == "texture" for a in licensed)
                      and set(RENDERS) <= listed)
            m_detail = f"assets={len(assets)} licensed={len(licensed)} renders={len(listed)}"
        except Exception as exc:
            m_detail = f"unreadable: {exc}"
    add("R13_manifest", "must", man_ok, m_detail)

    # ---- anti-cheat ----------------------------------------------------
    ac_ok = False
    ac_detail = "skipped: prerequisite checks failed"
    if scene_ok and os.path.exists(blend):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp,
                 "--python", "/tests/rerender.py", "--", WORK], timeout=1800)
            base_bottom = load_gray(os.path.join(WORK, "render_bottom.png"))
            base_tq = load_gray(os.path.join(WORK, "render_three_quarter.png"))
            delivered_bottom = load_gray(os.path.join(out, "render_bottom.png"))
            checker_bottom = load_gray(os.path.join(WORK, "ac_graphic.png"))
            lifted_tq = load_gray(os.path.join(WORK, "ac_decklift.png"))
            s_match = ss_img(base_bottom, delivered_bottom)
            s_graphic = ss_img(base_bottom, checker_bottom)
            s_lift = ss_img(base_tq, lifted_tq)
            ac_ok = s_match >= 0.90 and s_graphic <= 0.98 and s_lift <= 0.98
            ac_detail = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                         f"checker_vs_base={s_graphic:.3f} (<=0.98) "
                         f"decklift_vs_base={s_lift:.3f} (<=0.98)")
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R14_anticheat", "critical", ac_ok, ac_detail)

    view_scores = {}
    view_gradients = {}
    try:
        for name in RENDERS:
            trusted = Image.open(os.path.join(WORK, name)).convert("RGB")
            delivered = Image.open(os.path.join(out, name)).convert("RGB")
            if delivered.size != trusted.size:
                delivered = delivered.resize(trusted.size, Image.Resampling.LANCZOS)
            a = np.asarray(trusted, np.float32)
            b = np.asarray(delivered, np.float32)
            view_scores[name] = min(ss_img(a[..., c], b[..., c]) for c in range(3))
            view_gradients[name] = gradient_error(a, b)
        views_ok = all(np.isfinite(v) and v >= 0.90 for v in view_scores.values())
    except Exception as exc:
        views_ok = False
        view_scores["error"] = str(exc)
    add("R15_render_authenticity", "critical", views_ok, view_scores)
    structure_ok = views_ok and all(np.isfinite(v) and v <= 0.60 for v in view_gradients.values())
    add("R_render_structure", "critical", structure_ok, view_gradients)

    must = [c for c in CHECKS if c["level"] == "must"]
    crit = [c for c in CHECKS if c["level"] == "critical"]
    norm = [c for c in CHECKS if c["level"] == "normal"]
    must_pass = all(c["pass"] for c in must)
    crit_pass = all(c["pass"] for c in crit)
    norm_rate = sum(c["pass"] for c in norm) / max(len(norm), 1)
    reward = 1 if (must_pass and crit_pass and norm_rate >= 0.8) else 0
    result = {"reward": reward, "must_pass": must_pass, "critical_pass": crit_pass,
              "normal_rate": round(norm_rate, 3), "checks": CHECKS}
    with open(os.path.join(WORK, "metrics.json"), "w") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps(result, indent=1))
    return 0 if reward == 1 else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        CHECKS.append({"id": "R_verifier_error", "level": "must", "pass": False, "detail": str(exc)})
        print(json.dumps({"reward": 0, "must_pass": False, "critical_pass": False,
                          "normal_rate": 0, "checks": CHECKS}, indent=1))
        sys.exit(1)
