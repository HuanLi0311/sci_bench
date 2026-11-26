"""Grader for booth-clearance.

Usage: python3 grade.py /app/out
Exit 0 -> reward 1. Detail goes to stdout and /logs/verifier/metrics.json.
"""
import json
import tempfile
import traceback
import math
import os
import shutil
import subprocess
import sys
import hashlib

import numpy as np
from PIL import Image
from rubric import check_sizes, check_support

BLENDER = shutil.which("blender") or "/usr/local/bin/blender"
CHECKS = []
os.makedirs("/logs/verifier", exist_ok=True)
WORK = tempfile.mkdtemp(prefix="work-", dir="/logs/verifier")


def add(cid, level, ok, detail=""):
    CHECKS.append({"id": cid, "level": level, "pass": bool(ok), "detail": str(detail)})
    return ok


def _log_process(cmd, result):
    os.makedirs("/logs/verifier", exist_ok=True)
    with open("/logs/verifier/blender-processes.jsonl", "a") as f:
        f.write(json.dumps({"command": cmd, "returncode": result.returncode,
                            "stdout": result.stdout, "stderr": result.stderr}) + "\n")


def run(cmd, timeout):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    _log_process(cmd, r)
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
    return float((((2 * ma * mb + c1) * (2 * cov + c2)) /
                  ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2))).mean())


def load_gray(path, size=None):
    im = Image.open(path).convert("RGB")
    if size is not None:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32).mean(-1)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "booth.blend")
    scene = {}
    ok = False
    if os.path.exists(blend):
        try:
            r = run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", blend, "--python", "/tests/check_scene.py",
                     "--", os.path.join(WORK, "scene.json")], timeout=600)
            if r.returncode == 0 and os.path.exists(os.path.join(WORK, "scene.json")):
                with open(os.path.join(WORK, "scene.json")) as fh:
                    scene = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
                ok = bool(scene.get("ok"))
            if not ok:
                print((r.stderr or "")[-2000:], file=sys.stderr)
        except Exception as exc:
            print("check_scene failed:", exc, file=sys.stderr)

    add("R01_open", "must", ok and scene.get("blender", "").startswith("4."),
        scene.get("blender", "unreadable"))

    present = scene.get("required_present", {})
    missing = [k for k, v in present.items() if not v]
    add("R02_objects", "must",
        bool(present) and not missing and scene.get("has_lighting"),
        f"missing={missing} lighting={scene.get('has_lighting')}")

    size = scene.get("size") or [0, 0, 0]
    add("R03_size", "must",
        abs(size[0] - 6.0) <= 0.02 and abs(size[1] - 4.0) <= 0.02
        and size[2] <= 4.02,
        f"{[round(x, 3) for x in size]} m")

    b = scene.get("bounds") or [[0, 0, 0], [0, 0, 0]]
    inside = (b[0][0] >= -3.02 and b[0][1] >= -2.02 and b[0][2] >= -0.06
              and b[1][0] <= 3.02 and b[1][1] <= 2.02 and b[1][2] <= 4.02)
    add("R04_envelope", "must", inside, f"bounds={b}")

    clear = scene.get("entrance_clearance") or {}
    clear_ok = set(clear) == {"cabinet_01", "cabinet_02"} and all(v >= 0.9 for v in clear.values()) and scene.get("entrance_marker_valid", False)
    add("R05_entrance_clearance", "must", clear_ok,
        {k: round(v, 3) for k, v in clear.items()})

    hyd = scene.get("hydrant_distance") or {}
    bad = {k: round(v, 3) for k, v in hyd.items() if v < 1.2}
    add("R06_hydrant_clearance", "must", not bad, f"violations={bad}")

    vis = scene.get("visible_from_entrance") or {}
    vis_ok = len(vis) == 3 and all(v is True for v in vis.values())
    add("R07_visibility", "must", vis_ok, vis)

    delta = scene.get("brand_delta")
    add("R08_brand_colour", "normal", delta is not None and delta <= 2.0,
        f"delta={delta} material={scene.get('brand_material')}")

    mats = scene.get("materials", {})
    no_mat = [n for n in scene.get("meshes", [])
              if not (scene.get("objects", {}).get(n, {}).get("materials") or [None])[0]]
    add("R09_materials", "must", not no_mat, f"meshes without material={no_mat}")

    imgs = scene.get("images", [])
    unpacked = [i["name"] for i in imgs if i.get("filepath") and not i.get("packed")]
    add("R10_packed", "must", not unpacked, f"unpacked={unpacked}")

    ext = [i.get("filepath") for i in imgs
           if not i.get("packed") and i.get("filepath")
           and (i["filepath"].startswith("/") or "materials" in i["filepath"])]
    add("R11_no_external", "must", not ext, ext)

    polys = scene.get("polys_total", 10 ** 9)
    add("R12_polys", "normal", polys <= 300000, f"{polys} triangles")

    renders = {"render_entrance.png": (1920, 1080), "render_top.png": (2048, 1536)}
    r_ok, detail, hashes = True, [], []
    for f, size_px in renders.items():
        p = os.path.join(out, f)
        if not os.path.exists(p):
            r_ok = False
            detail.append(f"{f}:missing")
            continue
        got = Image.open(p).size
        hashes.append(sha(p))
        detail.append(f"{f}:{got[0]}x{got[1]}")
        if got != size_px:
            r_ok = False
    distinct = len(set(hashes)) == 2
    cams = scene.get("cameras", {})
    ce = cams.get("cam_entrance")
    cam_ok = bool(ce) and abs(ce.get("lens", 0) - 35) <= 1 \
        and abs(ce["location"][0] - (-1.5)) <= 0.05 \
        and abs(ce["location"][2] - 1.6) <= 0.05
    ct = cams.get("cam_top")
    top_ok = bool(ct) and ct.get("type") == "ORTHO" and ct.get("ortho_scale", 0) >= 5.95
    add("R13_entrance_render", "must", r_ok and distinct and cam_ok and top_ok,
        " ".join(detail) + f" cam={cam_ok} top={top_ok}")

    man_ok, mdetail = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp) as fh:
                man = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            assets = man.get("assets", [])
            man_ok = len(assets) >= 1 and all(a.get("source") and a.get("license")
                                              for a in assets)
            mdetail = f"assets={len(assets)}"
        except Exception as exc:
            mdetail = f"unreadable: {exc}"
    add("R14_manifest", "must", man_ok, mdetail)

    dimensions_ok, dimensions_detail = check_sizes(scene.get("objects", {}))
    add("R_furniture_product_sizes", "must", dimensions_ok, dimensions_detail)
    support_ok, support_detail = check_support(scene.get("objects", {}))
    add("R_product_support", "must", support_ok, support_detail)

    # anti-cheat: move cabinet_01 by 0.5 m and re-render
    ac_ok, ac_detail = False, "skipped: prerequisite checks failed"
    if ok and all(c["pass"] for c in CHECKS) and os.path.exists(blend) and os.path.exists(os.path.join(out, "render_entrance.png")):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp, "--python", "/tests/rerender.py",
                 "--", os.path.join(WORK, "ac_base.png"), os.path.join(WORK, "ac_moved.png")], timeout=900)
            if os.path.exists(os.path.join(WORK, "ac_base.png")) and os.path.exists(os.path.join(WORK, "ac_moved.png")):
                base = load_gray(os.path.join(WORK, "ac_base.png"))
                moved = load_gray(os.path.join(WORK, "ac_moved.png"))
                delivered = load_gray(os.path.join(out, "render_entrance.png"),
                                      size=(960, 540))
                s_match = ss_img(base, delivered)
                s_change = ss_img(base, moved)
                ac_ok = s_match >= 0.90 and s_change <= 0.98
                ac_detail = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                             f"cabinet_moved={s_change:.3f} (<=0.98)")
            else:
                ac_detail = "rerender produced no images"
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R15_anti_cheat", "critical", ac_ok, ac_detail)

    add("R16_deliverables", "must",
        os.path.exists(os.path.join(out, "booth.blend"))
        and os.path.exists(os.path.join(out, "manifest.json")),
        "blend+manifest")

    view_scores = {}
    try:
        for view in ['entrance', 'top']:
            filename = "render_" + view + ".png"
            trusted = Image.open(os.path.join(WORK, filename)).convert("RGB")
            delivered = Image.open(os.path.join(out, filename)).convert("RGB").resize(trusted.size, Image.Resampling.LANCZOS)
            a, b = np.asarray(trusted, np.float32), np.asarray(delivered, np.float32)
            compare = globals().get("ss_img") or globals().get("ss")
            view_scores[view] = min(compare(a[..., c], b[..., c]) for c in range(3))
        views_ok = all(np.isfinite(v) and v >= 0.90 for v in view_scores.values())
    except Exception as exc:
        views_ok = False
        view_scores["error"] = str(exc)
    add("R_all_render_authenticity", "critical", views_ok, view_scores)

    must = [c for c in CHECKS if c["level"] == "must"]
    crit = [c for c in CHECKS if c["level"] == "critical"]
    norm = [c for c in CHECKS if c["level"] == "normal"]
    must_pass = all(c["pass"] for c in must)
    crit_pass = all(c["pass"] for c in crit)
    rate = sum(c["pass"] for c in norm) / max(len(norm), 1)
    reward = 1 if (must_pass and crit_pass and rate >= 0.8) else 0

    result = {"reward": reward, "must_pass": must_pass,
              "critical_pass": crit_pass, "normal_rate": round(rate, 3),
              "checks": CHECKS}
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
        print(json.dumps({"reward": 0, "must_pass": False, "critical_pass": False, "normal_rate": 0, "checks": CHECKS}, indent=1))
        sys.exit(1)
