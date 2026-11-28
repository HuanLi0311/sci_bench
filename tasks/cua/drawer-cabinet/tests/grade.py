"""Grader for drawer-cabinet.

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

CARCASS = ["carcass_left", "carcass_right", "carcass_top", "carcass_bottom",
           "carcass_back", "carcass_divider"]
DRAWERS = [f"drawer_{i:02d}" for i in range(1, 6)]
SLIDES = [f"slide_{i:02d}" for i in range(1, 6)]
RENDERS = {"render_day.png": (1600, 1200), "render_night.png": (1600, 1200),
           "render_detail.png": (1600, 1200)}


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
    blend = os.path.join(out, "drawer_cabinet.blend")
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

    size = scene.get("outer_size_mm") or [0, 0, 0]
    size_ok = (abs(size[0] - 1000) <= 3 and abs(size[1] - 450) <= 3
               and abs(size[2] - 900) <= 3
               and abs(float(scene.get("unit_scale", 0)) - 1.0) <= 1e-6)
    add("R02_dimensions", "must", size_ok,
        f"outer={size} mm unit_scale={scene.get('unit_scale')}")

    present = scene.get("parts_present") or {}
    missing = [k for k in CARCASS + DRAWERS + SLIDES + ["door_right", "hinge_right"] if not present.get(k)]
    objs = scene.get("objects") or {}
    meshes_ok = all(objs.get(n, {}).get("visible_mesh") for n in CARCASS + DRAWERS + ["door_right"])
    empties_ok = all(objs.get(n, {}).get("type") == "EMPTY" for n in SLIDES)
    slides_ok = all(objs.get(d, {}).get("parent") == s for d, s in zip(DRAWERS, SLIDES))
    door_ok = (objs.get("door_right", {}).get("parent") == "hinge_right"
               and objs.get("hinge_right", {}).get("type") == "EMPTY")
    add("R03_parts", "must", not missing and slides_ok and door_ok and meshes_ok and empties_ok,
        f"missing={missing} slide_parents={slides_ok} door={door_ok}")

    panels = scene.get("panels") or {}
    thin = [f"{k}:{v['thickness_mm']}" for k, v in panels.items()
            if not (17.0 <= v["thickness_mm"] <= 19.0)]
    add("R04_panels", "must", len(panels) == len(CARCASS) and not thin,
        f"panels={len(panels)} out_of_range={thin[:4]}")

    travel = scene.get("drawer_travel_mm") or {}
    travel_ok = all(v is not None and abs(v - 420) <= 2 for v in travel.values()) and len(travel) == 5
    add("R05_travel", "must", travel_ok, travel)

    clearance = scene.get("drawer_clearance") or {}
    hits = {k: v for k, v in clearance.items()
            if v.get("carcass_hits", 1) != 0 or v.get("neighbour_hits", 1) != 0}
    add("R06_drawer_clearance", "must", len(clearance) == 5 and not hits,
        hits or "no overlap at 420 mm")

    door = scene.get("door") or {}
    door_ov = door.get("overlap") or {}
    door_clean = set(door_ov) == {"0", "55", "110"} and all(v == 0 for v in door_ov.values())
    motion = door.get("motion_error_mm") or {}
    door_clean &= set(motion) == {"0", "55", "110"} and all(v <= 2 for v in motion.values())
    hinge_loc = door.get("hinge_location") or [9, 9, 9]
    hinge_ok = (door.get("parent") == "hinge_right"
                and abs(hinge_loc[0] - 0.481) <= 0.01 and abs(hinge_loc[1] - 0.2265) <= 0.01
                and abs(hinge_loc[2] - 0.505) <= 0.01)
    add("R07_door_hinge", "must", hinge_ok and door_clean,
        f"hinge={hinge_loc} overlap={door_ov} motion_error_mm={motion}")

    add("R08_combined", "normal", door.get("combined_overlap") == 0,
        f"drawer_05 out 420 + door 110 overlaps={door.get('combined_overlap')}")

    mats = scene.get("materials") or {}
    wood_ok, metal_ok = {}, {}
    for n in CARCASS + DRAWERS + ['door_right']:
        assigned = [mats[m] for m in objs.get(n, {}).get('materials', []) if m in mats]
        wood_ok[n] = any({'Base Color', 'Roughness', 'Normal'} <=
                         {i['feeds'] for i in m.get('images', []) if i['size'] == [2048, 2048] and i['packed']}
                         and len({i['name'] for i in m.get('images', [])}) >= 3 for m in assigned)
    for n in DRAWERS + ['door_right'] + [f'foot_{i}' for i in range(1, 5)]:
        metal_ok[n] = any((mats.get(m, {}).get('metallic') or 0) >= 0.9
                          for m in objs.get(n, {}).get('materials', []))
    add('R09_materials', 'must', all(wood_ok.values()) and all(metal_ok.values()),
        f'wood={wood_ok} steel={metal_ok}')
    geometry = {}
    for n in DRAWERS + ['door_right']:
        target = [440, 18, 140] if n in DRAWERS else [450, 18, 746]
        geometry[n] = any(all(abs(d[i]-target[i]) <= 2 for i in range(3))
                          for d in objs.get(n, {}).get('components_mm', []))
        if n in DRAWERS:
            geometry[n] &= any(abs(d[1]-400) <= 2 for d in objs.get(n, {}).get('components_mm', []))
    add('R_panel_fronts', 'must', all(geometry.values()), geometry)

    imgs = [i for i in (scene.get("images") or []) if i.get("filepath")]
    packed_ok = (bool(imgs) and all(i["packed"] for i in imgs)
                 and not (scene.get("unpacked_images") or [])
                 and not (scene.get("libraries") or []))
    add("R10_self_contained", "must", packed_ok,
        f"images={len(imgs)} unpacked={scene.get('unpacked_images')} libs={scene.get('libraries')}")

    add("R11_polys", "normal", (scene.get("polys_total") or 10 ** 9) <= 60000,
        f"{scene.get('polys_total')} triangles")

    lights = scene.get("light_collections") or {}
    lights_ok = len(lights.get("light_day") or []) == 3 and len(lights.get("light_night") or []) == 2
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
    cf = cams.get("cam_front34")
    cam_ok = False
    if cf:
        dist = math.hypot(cf["location"][0], cf["location"][1])
        cam_ok = abs(cf.get("lens", 0) - 35) <= 1 and abs(dist - 1.6) <= 0.06 \
            and abs(cf["location"][2] - 1.15) <= 0.05
        detail.append(f"front34 lens={cf.get('lens')} d={dist:.3f} z={cf['location'][2]:.3f}")
    cd = cams.get("cam_detail")
    if cd and cf:
        target = (-0.242, 0.207 + 0.300, 0.355)
        dist = math.dist(cd["location"], target)
        cam_ok &= abs(cd.get("lens", 0) - 50) <= 1 and abs(dist - 0.60) <= 0.06
        detail.append(f"detail lens={cd.get('lens')} d={dist:.3f}")
    else:
        cam_ok = False
    add("R12_renders", "must", renders_ok and distinct and cam_ok and lights_ok,
        " ".join(detail) + f" distinct={distinct} lights={sorted(lights)}")

    man_ok, m_detail = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp) as fh:
                man = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            error = manifest_error(man, scene, RENDERS, {'render_day.png': 'cam_front34', 'render_night.png': 'cam_front34', 'render_detail.png': 'cam_detail'})
            man_ok = error is None
            m_detail = error or 'all scene images licensed; render metadata matches'
        except Exception as exc:
            m_detail = f"unreadable: {exc}"
    add("R13_manifest", "must", man_ok, m_detail)

    # ---- anti-cheat ----------------------------------------------------
    ac_ok = False
    ac_detail = "skipped: prerequisite checks failed"
    if scene_ok and os.path.exists(blend) and all(c["pass"] for c in CHECKS if c["level"] == "must"):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp,
                 "--python", "/tests/rerender.py", "--", WORK], timeout=1800)
            base_day = load_gray(os.path.join(WORK, "render_day.png"))
            base_night = load_gray(os.path.join(WORK, "render_night.png"))
            base_detail = load_gray(os.path.join(WORK, "render_detail.png"))
            delivered_day = load_gray(os.path.join(out, "render_day.png"), size=(800, 600))
            delivered_detail = load_gray(os.path.join(out, "render_detail.png"), size=(800, 600))
            day_off = load_gray(os.path.join(WORK, "ac_lights.png"))
            drawer_shift = load_gray(os.path.join(WORK, "ac_drawer.png"))
            s_match = min(ss_img(base_day, delivered_day), ss_img(base_detail, delivered_detail))
            s_lights = ss_img(base_night, day_off)
            s_drawer = ss_img(base_detail, drawer_shift)
            ac_ok = s_match >= 0.90 and s_lights <= 0.98 and s_drawer <= 0.98
            ac_detail = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                         f"night_vs_daylit={s_lights:.3f} (<=0.98) "
                         f"drawer300_vs_150={s_drawer:.3f} (<=0.98)")
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R14_anticheat", "critical", ac_ok, ac_detail)

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
    add("R15_render_authenticity", "critical", views_ok, view_scores)
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
