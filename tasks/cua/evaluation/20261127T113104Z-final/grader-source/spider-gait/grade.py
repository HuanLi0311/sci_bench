"""Grader for spider-gait.

Usage: python3 grade.py /app/out
Exit 0 -> reward 1. Every `must` and `critical` check must pass and at least
80% of the `normal` checks. Per-check detail is printed as JSON and written to
/logs/verifier/metrics.json.

Rubric IDs map 1:1 to the task README.
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

BLENDER = shutil.which("blender") or "/usr/local/bin/blender"
CHECKS = []
os.makedirs("/logs/verifier", exist_ok=True)
WORK = tempfile.mkdtemp(prefix="work-", dir="/logs/verifier")

LEGS = range(1, 9)
SEGMENTS = ("coxa", "femur", "tibia")
BODY_MESHES = ("body_head", "body_abdomen")
REQUIRED_MESHES = list(BODY_MESHES) + [
    f"leg_{leg:02d}_{seg}" for leg in LEGS for seg in SEGMENTS
]
PHASES = {1: 0, 2: 12, 3: 6, 4: 18, 5: 12, 6: 0, 7: 18, 8: 6}
CYCLE = 24
STANCE = 18
RENDERS = {
    "render_pose_01.png": (960, 540),
    "render_pose_02.png": (960, 540),
    "render_pose_03.png": (960, 540),
    "render_pose_04.png": (960, 540),
    "render_top.png": (960, 960),
}


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
    """SSIM on equal-shape grayscale arrays with an 8x8 mean window."""
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


def stance_frames(leg):
    p = PHASES[leg]
    return [f for f in range(1, 25) if ((f - 1) - p) % CYCLE < STANCE]


def swing_frames(leg):
    p = PHASES[leg]
    return [f for f in range(1, 25) if ((f - 1) - p) % CYCLE >= STANCE]


# --------------------------------------------------------------------------
def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "spider.blend")
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
    else:
        print("spider.blend missing", file=sys.stderr)

    add("R01_open", "must", scene_ok and str(scene.get("blender", "")).startswith("4."),
        scene.get("blender", "unreadable"))

    bones = scene.get("bones") or {}
    expected = {"body": None}
    for leg in range(1, 9):
        expected[f"leg_{leg:02d}_coxa"] = "body"
        expected[f"leg_{leg:02d}_femur"] = f"leg_{leg:02d}_coxa"
        expected[f"leg_{leg:02d}_tibia"] = f"leg_{leg:02d}_femur"
    bones_ok = set(bones) == set(expected) and all(
        bones[n].get("parent") == p and bones[n].get("deform", False)
        for n, p in expected.items())
    add("R02_bones", "must", bones_ok,
        f"count={len(bones)} missing={sorted(set(expected) - set(bones))[:4]} "
        f"extra={sorted(set(bones) - set(expected))[:4]}")

    skin = scene.get("skin") or {}
    skin_bad = []
    for name in REQUIRED_MESHES:
        e = skin.get(name) or {}
        if not e.get("present"):
            skin_bad.append(f"{name}:missing")
            continue
        if e.get("armature_modifiers") != [scene.get("rig")]:
            skin_bad.append(f"{name}:modifier={e.get('armature_modifiers')}")
        if e.get("unweighted", 1) != 0:
            skin_bad.append(f"{name}:unweighted={e.get('unweighted')}")
        if e.get("max_influences", 0) > 4:
            skin_bad.append(f"{name}:influences={e.get('max_influences')}")
        if not (0.99 <= e.get("min_weight_sum", 0) and e.get("max_weight_sum", 2) <= 1.01):
            skin_bad.append(f"{name}:weightsum={e.get('min_weight_sum')}..{e.get('max_weight_sum')}")
        expected_group = name if name.startswith("leg_") else "body"
        if e.get("dominant_group") != expected_group or e.get("dominant_frac", 0) < 0.9:
            skin_bad.append(f"{name}:bound_to={e.get('dominant_group')} "
                            f"({e.get('dominant_frac', 0):.2f})")
    add("R03_skinning", "must", not skin_bad, skin_bad[:6] or "26 meshes skinned")

    feet = scene.get("feet") or {}
    frame1 = {}
    for leg in range(1, 9):
        series = feet.get(f"leg_{leg:02d}")
        if series:
            frame1[leg] = series[0]
    span = (max(p[0] for p in frame1.values()) - min(p[0] for p in frame1.values())
            if len(frame1) == 8 else 0.0)
    body_aabb = scene.get("body_aabb_keyframes") or {}
    try:
        head = body_aabb["1:body_head"]
        abd = body_aabb["1:body_abdomen"]
        body_length = max(head[1][1], abd[1][1]) - min(head[0][1], abd[0][1])
    except Exception:
        body_length = 0.0
    body_head = scene.get("body_head") or []
    stance_height = body_head[0][2] if body_head else 0.0
    size_ok = (abs(body_length - 0.180) <= 0.005 and abs(span - 0.420) <= 0.010
               and abs(stance_height - 0.120) <= 0.005
               and abs(float(scene.get("unit_scale", 0)) - 1.0) <= 1e-6)
    add("R04_size", "must", size_ok,
        f"body={body_length*1000:.1f}mm span={span*1000:.1f}mm height={stance_height*1000:.1f}mm "
        f"unit_scale={scene.get('unit_scale')}")

    action = scene.get("action") or {}
    animated = set(action.get("animated_bones") or [])
    leg_bones = {f"leg_{leg:02d}_{seg}" for leg in LEGS for seg in SEGMENTS}
    action_ok = (action.get("name") == "Walk_Cycle"
                 and (action.get("frame_min") or 99) <= 1.0
                 and (action.get("frame_max") or 0) >= 25.0
                 and scene.get("frame_start") == 1 and scene.get("frame_end") == 24
                 and leg_bones <= animated)
    add("R05_action", "must", action_ok,
        f"name={action.get('name')} range={action.get('frame_min')}-{action.get('frame_max')} "
        f"scene={scene.get('frame_start')}-{scene.get('frame_end')} animated={len(animated)}")

    seam = scene.get("seam") or {}
    seam_ok = (seam.get("max_rotation_deg", 99) <= 0.5
               and seam.get("max_translation_mm", 99) <= 1.0)
    add("R06_loop", "must", seam_ok,
        f"rotation={seam.get('max_rotation_deg')}deg translation={seam.get('max_translation_mm')}mm")

    if len(frame1) == 8:
        support_bad = []
        ground_bad = []
        for leg in range(1, 9):
            series = feet[f"leg_{leg:02d}"]
            for f in stance_frames(leg):
                z = series[f - 1][2]
                if not (-0.001 <= z <= 0.002):
                    support_bad.append(f"leg_{leg:02d}@{f}:{z*1000:.1f}mm")
            low = min(p[2] for p in series[:24])
            if low < -0.001:
                ground_bad.append(f"leg_{leg:02d}:{low*1000:.1f}mm")
        add("R07_support", "must", not support_bad, support_bad[:6] or "all stance feet on the floor")
        add("R08_no_penetration", "must", not ground_bad, ground_bad[:6] or "min foot z >= -1mm")

        lift_bad = []
        for leg in range(1, 9):
            series = feet[f"leg_{leg:02d}"]
            peak = max(series[f - 1][2] for f in swing_frames(leg))
            if peak < 0.015:
                lift_bad.append(f"leg_{leg:02d}:{peak*1000:.1f}mm")
        add("R09_swing_lift", "must", not lift_bad, lift_bad[:6] or "all swing feet lift >= 15mm")

        drift_bad = []
        for leg in range(1, 9):
            series = feet[f"leg_{leg:02d}"]
            pts = [series[f - 1] for f in stance_frames(leg)]
            d = max(math.hypot(p[0] - pts[0][0], p[1] - pts[0][1]) for p in pts)
            if d > 0.005:
                drift_bad.append(f"leg_{leg:02d}:{d*1000:.1f}mm")
        add("R10_slide", "normal", not drift_bad, drift_bad[:6] or "stance drift <= 5mm")

        zs = [p[2] for p in body_head[:24]]
        bob = (max(zs) - min(zs)) if zs else 0.0
        add("R11_body_bob", "normal", bob <= 0.008, f"{bob*1000:.1f}mm")
    else:
        for cid in ("R07_support", "R08_no_penetration", "R09_swing_lift",
                    "R10_slide", "R11_body_bob"):
            add(cid, "must" if cid in ("R07_support", "R08_no_penetration", "R09_swing_lift") else "normal",
                False, "feet missing")

    collisions = scene.get("collisions") or {}
    total_overlaps = sum(v.get("overlaps", 0) for v in collisions.values()) if collisions else 0
    add("R12_no_intersection", "normal",
        len(collisions) == 24 and total_overlaps == 0,
        {k: v.get("overlaps") for k, v in collisions.items()} or "not measured")

    renders_ok = True
    detail = []
    hashes = []
    for name, (w, h) in RENDERS.items():
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
    side = cams.get("cam_side")
    if side:
        good = (abs(side.get("lens", 0) - 50) <= 1.0
                and abs(side["location"][0] - 0.75) <= 0.05
                and abs(side["location"][2] - 0.13) <= 0.03)
        cam_detail.append(f"side lens={side.get('lens')} loc={[round(c, 3) for c in side['location']]}")
    else:
        good = False
        cam_detail.append("cam_side missing")
    top = cams.get("cam_top")
    top_ok = bool(top) and top.get("type") == "ORTHO" and abs(top.get("ortho_scale", 0) - 0.5) <= 0.01
    if top:
        cam_detail.append(f"top ortho={top.get('ortho_scale')} type={top.get('type')}")
    else:
        cam_detail.append("cam_top missing")
    add("R13_renders", "must", renders_ok and distinct and good and top_ok,
        " ".join(detail) + f" distinct={distinct} " + " ".join(cam_detail))

    add("R14_polys", "normal", (scene.get("polys_total") or 10 ** 9) <= 80000,
        f"{scene.get('polys_total')} triangles")

    imgs = [i for i in (scene.get("images") or []) if i.get("filepath")]
    texture_ok = (bool(imgs) and all(i.get("packed") for i in imgs)
                  and not (scene.get("libraries") or [])
                  and not (scene.get("unpacked_images") or []))
    add("R15_self_contained", "must", texture_ok,
        f"images={len(imgs)} unpacked={scene.get('unpacked_images')} libraries={scene.get('libraries')}")

    man_ok, m_detail = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp) as fh:
                man = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            assets = man.get("assets", [])
            licensed = [a for a in assets if a.get("source") and a.get("license")]
            textures = [a for a in licensed if a.get("role") == "texture"]
            listed = {r.get("file") for r in man.get("renders", [])}
            man_ok = (len(assets) >= 1 and len(licensed) == len(assets)
                      and len(textures) >= 1 and set(RENDERS) <= listed)
            m_detail = f"assets={len(assets)} licensed={len(licensed)} textures={len(textures)} renders={len(listed)}"
        except Exception as exc:
            m_detail = f"unreadable: {exc}"
    add("R16_manifest", "must", man_ok, m_detail)

    # ---- anti-cheat ----------------------------------------------------
    ac_ok = False
    ac_detail = "skipped: prerequisite checks failed"
    if scene_ok and os.path.exists(blend) and os.path.exists(os.path.join(out, "render_pose_01.png")):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp,
                 "--python", "/tests/rerender.py", "--", WORK], timeout=1500)
            base = load_gray(os.path.join(WORK, "render_pose_01.png"))
            shifted = load_gray(os.path.join(WORK, "ac_shift.png"))
            delivered = load_gray(os.path.join(out, "render_pose_01.png"), size=(960, 540))
            s_match = ss_img(base, delivered)
            s_shift = ss_img(base, shifted)
            ac_ok = s_match >= 0.90 and s_shift <= 0.98
            ac_detail = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                         f"frame7_vs_frame1={s_shift:.3f} (<=0.98)")
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R17_phase_anticheat", "critical", ac_ok, ac_detail)

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
    add("R18_render_authenticity", "critical", views_ok, view_scores)
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
