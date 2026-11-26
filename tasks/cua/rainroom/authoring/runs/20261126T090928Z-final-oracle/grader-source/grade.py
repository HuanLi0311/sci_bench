"""Grader for rainroom. Usage: python3 grade.py /app/out"""
import json
import tempfile
import traceback
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
from render_compare import gradient_error

BLENDER = shutil.which("blender") or "/usr/local/bin/blender"
CHECKS = []
os.makedirs("/logs/verifier", exist_ok=True)
WORK = tempfile.mkdtemp(prefix="work-", dir="/logs/verifier")


def add(cid, level, ok, detail=""):
    CHECKS.append({"id": cid, "level": level, "pass": bool(ok), "detail": str(detail)})


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


def ss(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    if a.shape != b.shape:
        return 0.0
    win = 8
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2

    def box(x):
        h, w = x.shape
        h2, w2 = h - h % win, w - w % win
        return x[:h2, :w2].reshape(h2 // win, win, w2 // win, win).mean(axis=(1, 3))

    ma, mb = box(a), box(b)
    va, vb = box(a * a) - ma ** 2, box(b * b) - mb ** 2
    cov = box(a * b) - ma * mb
    return float((((2 * ma * mb + c1) * (2 * cov + c2)) /
                  ((ma ** 2 + mb ** 2 + c1) * (va + vb + c2))).mean())


def stats(p, size=None):
    im = Image.open(p).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    return float(a.mean()), float((a[..., 0] - a[..., 2]).mean())


def gray(p, size=None):
    return stats(p, size)[0]


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "rainroom.blend")
    rep, ok = {}, False
    if os.path.exists(blend):
        try:
            r = run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", blend, "--python", "/tests/check_scene.py",
                     "--", os.path.join(WORK, "scene.json")], timeout=600)
            if r.returncode == 0 and os.path.exists(os.path.join(WORK, "scene.json")):
                rep = json.load(open(os.path.join(WORK, "scene.json")), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
                ok = bool(rep.get("ok"))
            if not ok:
                print((r.stderr or "")[-1500:], file=sys.stderr)
        except Exception as exc:
            print("check_scene failed:", exc, file=sys.stderr)

    add("R01_open", "must", ok and rep.get("blender", "").startswith("4."),
        rep.get("blender", "unreadable"))

    req = rep.get("required", {})
    missing = [k for k, v in req.items() if not v]
    add("R02_objects", "must", len(req) == 26 and not missing,
        f"missing={missing}")

    size = rep.get("room_size") or [0, 0, 0]
    add("R03_room_size", "must",
        all(abs(size[i] - w) <= 0.02 for i, w in enumerate((4.2, 3.6, 2.8))),
        [round(s, 3) for s in size])

    colls = rep.get("collections", {})
    n = colls.get("light_night", {})
    m = colls.get("light_morning", {})
    add("R04_light_sets", "must",
        len(n.get("lights", [])) >= 1 and len(m.get("lights", [])) >= 1,
        f"night={len(n.get('lights', []))} morning={len(m.get('lights', []))}")

    cams = rep.get("cameras", {})
    add("R05_camera", "must", "cam_room" in cams,
        cams.get("cam_room", {}).get("lens"))

    renders = {"render_night.png": (1600, 900), "render_morning.png": (1600, 900)}
    r_ok, detail = True, []
    for f, want in renders.items():
        p = os.path.join(out, f)
        if not os.path.exists(p):
            r_ok = False
            detail.append(f"{f}:missing")
            continue
        got = Image.open(p).size
        detail.append(f"{f}:{got[0]}x{got[1]}")
        if got != want:
            r_ok = False
    add("R06_renders", "must", r_ok, " ".join(detail))

    night, nl = 0.0, 0.0
    morning, ml = 0.0, 0.0
    if os.path.exists(os.path.join(out, "render_night.png")):
        night, nl = stats(os.path.join(out, "render_night.png"))
    if os.path.exists(os.path.join(out, "render_morning.png")):
        morning, ml = stats(os.path.join(out, "render_morning.png"))
    lum_ok = 0.10 <= night <= 0.32 and 0.55 <= morning <= 0.80
    add("R07_brightness", "must", lum_ok,
        f"night={night:.3f} morning={morning:.3f}")

    hue_ok = (ml - nl) >= 0.02 and (morning - night) >= 0.25
    add("R08_time_of_day", "must", hue_ok,
        f"night R-B={nl:.3f} morning R-B={ml:.3f} dLum={morning-night:.3f}")

    mats = rep.get("materials", {})
    glass = [n for n, m in mats.items() if (m.get("transmission") or 0) > 0.5
             or (m.get("alpha") is not None and m["alpha"] < 0.5)]
    metal = [n for n, m in mats.items() if (m.get("metallic") or 0) >= 0.9]
    add("R09_materials", "must", bool(glass) and bool(metal),
        f"glass={glass} metal={metal}")

    imgs = rep.get("images", [])
    unpacked = [i["name"] for i in imgs if i.get("filepath") and not i.get("packed")]
    add("R10_packed", "must", not unpacked, unpacked)

    polys = rep.get("polys_total", 10 ** 9)
    add("R11_polys", "normal", polys <= 400000, f"{polys} triangles")

    man_ok, md = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            man = json.load(open(mp))
            assets = man.get("assets", [])
            man_ok = len(assets) >= 1 and all(a.get("source") and a.get("license")
                                              for a in assets)
            md = f"assets={len(assets)}"
        except Exception as exc:
            md = f"unreadable: {exc}"
    add("R12_manifest", "must", man_ok, md)

    errors = rep.get("position_errors", {})
    add("R_object_positions", "must", len(errors) == 26 and all(v <= 0.15 for v in errors.values()), errors)

    ac_ok, acd = False, "skipped: prerequisite checks failed"
    if ok and all(c["pass"] for c in CHECKS) and os.path.exists(blend) and os.path.exists(os.path.join(out, "render_night.png")):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp, "--python", "/tests/rerender.py",
                 "--", os.path.join(WORK, "ac_on.png"), os.path.join(WORK, "ac_off.png")], timeout=900)
            if os.path.exists(os.path.join(WORK, "ac_on.png")) and os.path.exists(os.path.join(WORK, "ac_off.png")):
                on = gray(os.path.join(WORK, "ac_on.png"))
                off = gray(os.path.join(WORK, "ac_off.png"))
                delivered = gray(os.path.join(out, "render_night.png"), size=(800, 450))
                s_match = 1.0 - abs(on - delivered) / max(on, 1e-6)
                s_chg = ss(_img(os.path.join(WORK, "ac_on.png")), _img(os.path.join(WORK, "ac_off.png")))
                ac_ok = s_match >= 0.85 and s_chg <= 0.98
                acd = f"delivered_vs_scene~{s_match:.3f} night_off={s_chg:.3f}"
        except Exception as exc:
            acd = f"rerender failed: {exc}"
    add("R13_anti_cheat", "critical", ac_ok, acd)

    view_scores = {}
    view_gradients = {}
    try:
        for view in ['night', 'morning']:
            filename = "render_" + view + ".png"
            trusted = Image.open(os.path.join(WORK, filename)).convert("RGB")
            delivered = Image.open(os.path.join(out, filename)).convert("RGB").resize(trusted.size, Image.Resampling.LANCZOS)
            a, b = np.asarray(trusted, np.float32), np.asarray(delivered, np.float32)
            compare = globals().get("ss_img") or globals().get("ss")
            view_scores[view] = min(compare(a[..., c], b[..., c]) for c in range(3))
            view_gradients[view] = gradient_error(a, b)
        views_ok = all(np.isfinite(v) and v >= 0.90 for v in view_scores.values())
    except Exception as exc:
        views_ok = False
        view_scores["error"] = str(exc)
    add("R_all_render_authenticity", "critical", views_ok, view_scores)
    structure_ok = views_ok and all(np.isfinite(v) and v <= 0.60 for v in view_gradients.values())
    add("R_render_structure", "critical", structure_ok, view_gradients)

    must = [c for c in CHECKS if c["level"] == "must"]
    crit = [c for c in CHECKS if c["level"] == "critical"]
    norm = [c for c in CHECKS if c["level"] == "normal"]
    must_pass = all(c["pass"] for c in must)
    crit_pass = all(c["pass"] for c in crit)
    rate = sum(c["pass"] for c in norm) / max(len(norm), 1)
    reward = 1 if (must_pass and crit_pass and rate >= 0.8) else 0
    result = {"reward": reward, "must_pass": must_pass, "critical_pass": crit_pass,
              "normal_rate": round(rate, 3), "checks": CHECKS}
    json.dump(result, open(os.path.join(WORK, "metrics.json"), "w"), indent=1)
    print(json.dumps(result, indent=1))
    return 0 if reward else 1


def _img(p):
    return np.asarray(Image.open(p).convert("RGB"), np.float32).mean(-1)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        CHECKS.append({"id": "R_verifier_error", "level": "must", "pass": False, "detail": str(exc)})
        print(json.dumps({"reward": 0, "must_pass": False, "critical_pass": False, "normal_rate": 0, "checks": CHECKS}, indent=1))
        sys.exit(1)
