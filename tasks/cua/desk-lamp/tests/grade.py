"""Grader for desk-lamp.

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

BLENDER = shutil.which("blender") or "/usr/local/bin/blender"
CHECKS = []
os.makedirs("/logs/verifier", exist_ok=True)
WORK = tempfile.mkdtemp(prefix="work-", dir="/logs/verifier")

JOINTS = ["joint_yaw", "joint_shoulder", "joint_elbow", "joint_head"]
ARMS = ["lower_arm", "upper_arm", "shade", "bulb"]
TARGETS = [(0.300, 0.350, 0.350), (-0.280, 0.320, 0.340), (0.050, 0.470, 0.360)]
RENDERS = {"render_pose_01.png": (1600, 1200), "render_pose_02.png": (1600, 1200),
           "render_pose_03.png": (1600, 1200), "render_hero.png": (1600, 1200)}


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
    blend = os.path.join(out, "desk_lamp.blend")
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

    objs = scene.get("objects") or {}

    def extent(name):
        a = (objs.get(name) or {}).get("aabb")
        if not a:
            return None
        return [a[1][i] - a[0][i] for i in range(3)]

    base = extent("base")
    lower = extent("lower_arm")
    upper = extent("upper_arm")
    shade = extent("shade")
    dims_ok = (
        base is not None and abs(max(base[0], base[1]) * 1000 - 120) <= 2
        and abs(base[2] * 1000 - 22) <= 1
        and lower is not None and abs(max(lower) * 1000 - 320) <= 3
        and upper is not None and abs(max(upper) * 1000 - 300) <= 3
        and shade is not None and abs(max(shade) * 1000 - 90) <= 4
        and abs(float(scene.get("unit_scale", 0)) - 1.0) <= 1e-6)
    add("R02_geometry", "must", dims_ok,
        f"base={[round(v * 1000, 1) for v in base] if base else None} "
        f"lower={max(lower) * 1000:.1f} upper={max(upper) * 1000:.1f} "
        f"shade={max(shade) * 1000:.1f}")

    joints = scene.get("joints") or {}
    chain_bad = []
    for name in JOINTS:
        e = joints.get(name) or {}
        if not e.get("present") or not e.get("empty"):
            chain_bad.append(f"{name}:{'missing' if not e.get('present') else 'not_empty'}")
            continue
        if e.get("rest_error_mm", 99) > 5:
            chain_bad.append(f"{name}:rest={e.get('rest_error_mm')}mm")
    expected_parents = {"joint_yaw": None, "joint_shoulder": "joint_yaw",
                        "joint_elbow": "joint_shoulder", "joint_head": "joint_elbow"}
    for name, parent in expected_parents.items():
        if (joints.get(name) or {}).get("parent") != parent:
            chain_bad.append(f"{name}:parent={(joints.get(name) or {}).get('parent')}")
    parents = scene.get("mesh_parents") or {}
    mesh_parents = {"lower_arm": "joint_shoulder", "upper_arm": "joint_elbow",
                    "shade": "joint_head", "bulb": "joint_head"}
    for name, parent in mesh_parents.items():
        if parents.get(name) != parent:
            chain_bad.append(f"{name}:parent={parents.get(name)}")
    add("R03_joint_chain", "must", not chain_bad, chain_bad[:6] or "four empties, meshes bound")

    action = scene.get("action") or {}
    act_bad = []
    for name in JOINTS:
        entry = action.get(name)
        if not entry:
            act_bad.append(f"{name}:no_action")
            continue
        if entry["paths"] != ["rotation_euler"]:
            act_bad.append(f"{name}:paths={entry['paths']}")
        need = {1.0, 2.0, 3.0}
        if not need <= set(entry["frames"]):
            act_bad.append(f"{name}:frames={entry['frames']}")
    range_ok = scene.get("frame_start") == 1 and scene.get("frame_end") == 3
    add("R04_action", "must", not act_bad and range_ok,
        (act_bad[:5] or "rotation keys on 1/2/3") + f" range={scene.get('frame_start')}-{scene.get('frame_end')}")

    poses = scene.get("poses") or {}
    reach = {k: (v.get("head_error_mm")) for k, v in poses.items()}
    reach_ok = len(poses) == 3 and all(v is not None and v <= 8.0 for v in reach.values())
    add("R05_reach", "must", reach_ok, reach)

    miss = {k: v.get("desk_miss_mm") for k, v in poses.items()}
    axis_ok = len(poses) == 3 and all(v is not None and v <= 25.0 for v in miss.values())
    add("R06_aim", "must", axis_ok, miss)

    lows = {k: v.get("min_z_mm") for k, v in poses.items()}
    above = all(all(z >= -1.0 for z in (d or {}).values()) for d in lows.values())
    add("R07_above_desk", "must", len(lows) == 3 and above, lows)

    overlaps = {k: v.get("arm_overlap") for k, v in poses.items()}
    add("R08_no_intersection", "normal",
        len(overlaps) == 3 and all(v == 0 for v in overlaps.values()), overlaps)

    lamp = scene.get("lamp") or {}
    spot = objs.get("lamp_spot") or {}
    lamp_ok = (spot.get("light_type") == "SPOT"
               and lamp.get("parent") == "joint_head"
               and 30.0 <= (spot.get("energy") or 0) <= 120.0
               and (lamp.get("direction") or [0, 0, 1])[2] < -0.3)
    add("R09_lamp_rig", "must", lamp_ok,
        f"type={spot.get('light_type')} parent={lamp.get('parent')} "
        f"energy={spot.get('energy')} dir={lamp.get('direction')}")

    probe = {}
    probe_ok = False
    if scene_ok and os.path.exists(blend):
        try:
            cp = os.path.join(WORK, "probe.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp,
                 "--python", "/tests/light_probe.py", "--", os.path.join(WORK, "probe.json")],
                timeout=1200)
            with open(os.path.join(WORK, "probe.json")) as fh:
                probe = json.load(fh)
            ratio = probe.get("ratio")
            probe_ok = bool(probe.get("ok") and probe.get("target_in_frame")
                            and ratio is not None and ratio >= 1.5)
        except Exception as exc:
            probe = {"error": str(exc)}
    add("R10_illumination", "must", probe_ok,
        f"ratio={probe.get('ratio')} on={probe.get('on_patch')} off={probe.get('off_patch')} "
        f"px={probe.get('target_px')}")

    mats = scene.get("materials") or {}
    paint_imgs = [i for m in mats.values() for i in (m.get("images") or [])]
    big = [i for i in paint_imgs if min(i["size"]) >= 1024]
    metal = max([m.get("metallic") or 0 for m in mats.values()] or [0])
    mats_ok = bool(big) and all(i["packed"] for i in big) and metal >= 0.9
    add("R11_materials", "normal", mats_ok,
        f"textured={[(i['name'], i['size'], i['packed']) for i in big]} metal={metal:.2f}")

    imgs = [i for i in (scene.get("images") or []) if i.get("filepath")]
    packed_ok = (bool(imgs) and all(i["packed"] for i in imgs)
                 and not (scene.get("unpacked_images") or [])
                 and not (scene.get("libraries") or []))
    add("R12_self_contained", "must", packed_ok,
        f"images={len(imgs)} unpacked={scene.get('unpacked_images')}")

    add("R13_polys", "normal", (scene.get("polys_total") or 10 ** 9) <= 40000,
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
    cp_ = cams.get("cam_pose") or {}
    cpe = cams.get("cam_hero") or {}
    cam_ok = (abs(cp_.get("lens", 0) - 40) <= 1.0 and abs(cpe.get("lens", 0) - 50) <= 1.0)
    add("R14_renders", "must", renders_ok and distinct and cam_ok,
        " ".join(detail) + f" distinct={distinct} lens={cp_.get('lens')}/{cpe.get('lens')}")

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
    add("R15_manifest", "must", man_ok, m_detail)

    ac_ok = False
    ac_detail = "skipped: prerequisite checks failed"
    if scene_ok and os.path.exists(blend):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp,
                 "--python", "/tests/rerender.py", "--", WORK], timeout=1800)
            base1 = load_gray(os.path.join(WORK, "render_pose_01.png"))
            yawed = load_gray(os.path.join(WORK, "ac_yaw.png"))
            delivered = load_gray(os.path.join(out, "render_pose_01.png"), size=(800, 600))
            s_match = ss_img(base1, delivered)
            s_yaw = ss_img(base1, yawed)
            ac_ok = s_match >= 0.90 and s_yaw <= 0.98
            ac_detail = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                         f"yaw25_vs_pose1={s_yaw:.3f} (<=0.98)")
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R16_anticheat", "critical", ac_ok, ac_detail)

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
    add("R17_render_authenticity", "critical", views_ok, view_scores)
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
