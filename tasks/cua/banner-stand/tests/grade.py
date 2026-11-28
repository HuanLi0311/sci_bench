"""Grader for banner-stand.

Usage: python3 grade.py /app/out
Exit 0 -> reward 1. Every `must` and `critical` check must pass and at least
80% of the `normal` checks.
"""
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import traceback

import numpy as np
from PIL import Image
from render_compare import gradient_error
from submission_support import manifest_error

BLENDER = shutil.which("blender") or "/usr/local/bin/blender"
CHECKS = []
INFRA_ERRORS = []
os.makedirs("/logs/verifier", exist_ok=True)
WORK = tempfile.mkdtemp(prefix="work-", dir="/logs/verifier")

PARTS = ["base", "mast_left", "mast_right", "top_bar", "canvas", "leg_rear"]
RENDERS = {"render_front.png": (1200, 1600),
           "render_three_quarter.png": (1600, 1200),
           "render_folded.png": (1200, 1600)}


def add(cid, level, ok, detail=""):
    CHECKS.append({"id": cid, "level": level, "pass": bool(ok), "detail": str(detail)})
    return ok


def record(cmd, result):
    with open("/logs/verifier/blender-processes.jsonl", "a") as fh:
        fh.write(json.dumps({"command": cmd, "returncode": result.returncode,
                             "stdout": result.stdout[-4000:],
                             "stderr": result.stderr[-4000:]}) + "\n")


def run(cmd, timeout):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        INFRA_ERRORS.append(str(exc))
        raise
    if r.returncode in (-9, 137):
        INFRA_ERRORS.append(f'Blender killed: {r.returncode}')
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


def load_gray(path, size=None):
    im = Image.open(path).convert("RGB")
    if size is not None:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32).mean(-1)


def file_sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "banner_stand.blend")
    scene, scene_ok = {}, False
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

    frame = scene.get("frame_mm") or {}
    size_ok = (abs(frame.get("width", 0) - 800) <= 3
               and abs(frame.get("height", 0) - 2000) <= 3
               and abs(frame.get("min_z", 9) - 0) <= 2
               and abs(float(scene.get("unit_scale", 0)) - 1.0) <= 1e-6)
    add("R02_dimensions", "must", size_ok,
        f"frame={frame} unit_scale={scene.get('unit_scale')}")

    present = scene.get("parts_present") or {}
    objs = scene.get("objects") or {}
    missing = [k for k in PARTS + ["hinge_rear"] if not present.get(k)]
    mesh_ok = all(objs.get(n, {}).get("visible_mesh") for n in PARTS)
    parent_ok = objs.get("leg_rear", {}).get("parent") == "hinge_rear" \
        and objs.get("hinge_rear", {}).get("type") == "EMPTY"
    add("R03_parts", "must", not missing and parent_ok and mesh_ok,
        f"missing={missing} leg_parent={objs.get('leg_rear', {}).get('parent')}")

    canvas = scene.get("canvas") or {}
    uv = canvas.get("uv") or {}
    bbox = uv.get("bbox") or [[0, 0], [0, 0]]
    canvas_ok = (abs(canvas.get("width_mm", 0) - 800) <= 3
                 and abs(canvas.get("height_mm", 0) - 1900) <= 3
                 and canvas.get("planarity_mm", 9) <= 2.0
                 and abs(canvas.get("z_top_mm", 0) - 1960) <= 3)
    add("R04_canvas", "must", canvas_ok,
        f"w={canvas.get('width_mm')} h={canvas.get('height_mm')} "
        f"top={canvas.get('z_top_mm')} planarity={canvas.get('planarity_mm')}mm")

    imgs = []
    for name in objs.get('canvas', {}).get('materials', []):
        imgs.extend((scene.get('materials') or {}).get(name, {}).get('images') or [])
    graphic = imgs[0] if imgs else None
    aspect_ok = False
    if graphic:
        w, h = graphic["size"]
        aspect_ok = abs((w / h) - (800 / 1900)) <= 0.02 * (800 / 1900)
    uv_ok = (graphic is not None and 0.95 <= uv.get("area", 0) <= 1.02
             and bbox[0][0] <= 0.05 and bbox[0][1] <= 0.05
             and bbox[1][0] >= 0.95 and bbox[1][1] >= 0.95
             and aspect_ok and max(graphic["size"]) <= 2048
             and uv.get("mapping_error", 1) <= 0.005)
    add("R05_uv", "must", uv_ok,
        f"image={graphic} area={uv.get('area')} bbox={bbox} aspect_ok={aspect_ok}")

    fold = scene.get("fold") or {}
    states = fold.get("states") or {}
    hinge_loc = fold.get("hinge_location") or [9, 9, 9]
    hinge_ok = (fold.get("parent") == "hinge_rear"
                and abs(hinge_loc[0]) <= 0.01 and abs(hinge_loc[1] + 0.045) <= 0.01
                and abs(hinge_loc[2] - 0.075) <= 0.01)
    state14 = states.get("14") or {}
    state0 = states.get("0") or {}
    fold_ok = (hinge_ok
               and 1860 <= state14.get("z_max_mm", 0) <= 1960
               and 460 <= state14.get("y_max_mm", 0) <= 560
               and abs(state0.get("z_min_mm", 0) - 75) <= 10
               and fold.get("folded_depth_mm", 999) <= 130)
    add("R06_fold_geometry", "must", fold_ok,
        f"hinge={hinge_loc} state0={state0} state14={state14} "
        f"folded={fold.get('folded_depth_mm')}mm")

    collision = {k: v.get("overlap") for k, v in states.items()}
    add("R07_no_contact", "must", set(states) == {"0", "7", "14"} and all(v == 0 for v in collision.values())
        and all(v.get("motion_error_mm", 999) <= 2 for v in states.values()),
        collision)

    mats = scene.get('materials') or {}
    metal_ok = all(any((mats.get(m, {}).get('metallic') or 0) >= 0.8
                       for m in objs.get(n, {}).get('materials', []))
                   for n in ('base', 'mast_left', 'mast_right', 'top_bar', 'leg_rear'))
    canvas_ok = all(mats.get(m, {}).get('images') and
                    0.55 <= (mats.get(m, {}).get('roughness') or 0) <= 0.85
                    for m in objs.get('canvas', {}).get('materials', []))
    add('R08_materials', 'must', metal_ok and canvas_ok, f'frame={metal_ok} canvas={canvas_ok}')
    expected = {'base': [800, 120, 50], 'mast_left': [40, 40, 1910],
                'mast_right': [40, 40, 1910], 'top_bar': [800, 40, 40]}
    dimensions = {}
    for n, target in expected.items():
        box = objs.get(n, {}).get('aabb')
        dimensions[n] = bool(box) and all(abs((box[1][i]-box[0][i])*1000-target[i]) <= 3 for i in range(3))
    add('R_frame_parts', 'must', all(dimensions.values()), dimensions)

    path_imgs = [i for i in (scene.get("images") or []) if i.get("filepath")]
    packed_ok = (bool(path_imgs) and all(i["packed"] for i in path_imgs)
                 and not (scene.get("unpacked_images") or [])
                 and not (scene.get("libraries") or []))
    add("R09_self_contained", "must", packed_ok,
        f"images={len(path_imgs)} unpacked={scene.get('unpacked_images')}")

    add("R10_polys", "normal", (scene.get("polys_total") or 10 ** 9) <= 40000,
        f"{scene.get('polys_total')} triangles")

    renders_ok, detail, hashes = True, [], []
    for name, (w, h) in RENDERS.items():
        p = os.path.join(out, name)
        if not os.path.exists(p):
            renders_ok = False
            detail.append(f"{name}:missing")
            continue
        try:
            iw, ih = Image.open(p).size
        except Exception:
            renders_ok = False
            detail.append(f"{name}:unreadable")
            continue
        hashes.append(file_sha(p))
        detail.append(f"{name}:{iw}x{ih}")
        if (iw, ih) != (w, h):
            renders_ok = False
    distinct = len(set(hashes)) == len(hashes) == len(RENDERS)
    cams = scene.get("cameras") or {}
    cf = cams.get("cam_front")
    f_ok = bool(cf) and cf.get("type") == "ORTHO" and abs(cf.get("ortho_scale", 0) - 2.15) <= 0.02
    cq = cams.get("cam_three_quarter")
    q_ok = bool(cq) and abs(cq.get("lens", 0) - 35) <= 1
    ck = cams.get("cam_folded")
    k_ok = bool(ck) and ck.get("type") == "ORTHO" and abs(ck.get("ortho_scale", 0) - 2.15) <= 0.02
    add("R11_renders", "must", renders_ok and distinct and f_ok and q_ok and k_ok,
        " ".join(detail) + f" distinct={distinct} cams={f_ok}/{q_ok}/{k_ok}")

    man_ok, m_detail = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp) as fh:
                man = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            error = manifest_error(man, scene, RENDERS, {'render_front.png': 'cam_front', 'render_folded.png': 'cam_folded', 'render_three_quarter.png': 'cam_three_quarter'})
            man_ok = error is None
            m_detail = error or 'all scene images licensed; render metadata matches'
        except Exception as exc:
            m_detail = f"unreadable: {exc}"
    add("R12_manifest", "must", man_ok, m_detail)

    ac_ok = False
    ac_detail = "skipped: prerequisite checks failed"
    if scene_ok and os.path.exists(blend) and all(c["pass"] for c in CHECKS if c["level"] == "must"):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp,
                 "--python", "/tests/rerender.py", "--", WORK], timeout=1800)
            base_front = load_gray(os.path.join(WORK, "render_front.png"))
            base_q = load_gray(os.path.join(WORK, "render_three_quarter.png"))
            delivered_front = load_gray(os.path.join(out, "render_front.png"), size=(600, 800))
            delivered_q = load_gray(os.path.join(out, "render_three_quarter.png"), size=(800, 600))
            checker = load_gray(os.path.join(WORK, "ac_graphic.png"))
            folded25 = load_gray(os.path.join(WORK, "ac_hinge.png"))
            s_match = min(ss_img(base_front, delivered_front), ss_img(base_q, delivered_q))
            s_graphic = ss_img(base_front, checker)
            s_hinge = ss_img(base_q, folded25)
            ac_ok = s_match >= 0.90 and s_graphic <= 0.98 and s_hinge <= 0.98
            ac_detail = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                         f"checker_vs_base={s_graphic:.3f} (<=0.98) "
                         f"hinge25_vs_14={s_hinge:.3f} (<=0.98)")
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R13_anticheat", "critical", ac_ok, ac_detail)

    view_scores, view_gradients = {}, {}
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
    add("R14_render_authenticity", "critical", views_ok, view_scores)
    structure_ok = views_ok and all(np.isfinite(v) and v <= 0.60 for v in view_gradients.values())
    add("R_render_structure", "critical", structure_ok, view_gradients)

    if INFRA_ERRORS:
        raise RuntimeError('; '.join(INFRA_ERRORS))
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
        print(json.dumps({"status": "infrastructure_error", "reward": None, "must_pass": False, "critical_pass": False,
                          "normal_rate": 0, "checks": CHECKS}, indent=1))
        sys.exit(2)
