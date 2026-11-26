"""Grader for toy-car. Usage: python3 grade.py /app/out"""
import json
import tempfile
import traceback
import os
import shutil
import subprocess
import sys
import hashlib

import numpy as np
from PIL import Image

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


def gray(p, size=None):
    im = Image.open(p).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, np.float32).mean(-1)


def mask(p):
    """Silhouette = everything not reachable from the border through white."""
    im = Image.open(p).convert("L").resize((240, 240), Image.LANCZOS)
    a = np.asarray(im)
    h, w = a.shape
    white = a > 230
    seen = np.zeros_like(white, dtype=bool)
    stack = [(y, x) for y in (0, h - 1) for x in range(w)] +             [(y, x) for x in (0, w - 1) for y in range(h)]
    while stack:
        y, x = stack.pop()
        if 0 <= y < h and 0 <= x < w and white[y, x] and not seen[y, x]:
            seen[y, x] = True
            stack.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    return ~seen


def mask_file(p):
    a = np.asarray(Image.open(p).convert("L").resize((240, 240), Image.LANCZOS))
    return a > 128


def iou(a, b):
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    return float(inter / union) if union else 0.0


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "toy_car.blend")
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
    add("R02_parts", "must", bool(req) and all(req.values()),
        {k: v for k, v in req.items() if not v} or "all present")

    wb = rep.get("wheelbase")
    add("R03_wheelbase", "must", wb is not None and abs(wb - 0.240) <= 0.003,
        f"{wb:.4f} m" if wb else "n/a")

    wheels = rep.get("wheels") or {}
    diam = [w["diameter_z"] for w in wheels.values() if w]
    add("R04_wheel_diameter", "must",
        len(diam) == 4 and all(abs(d - 0.060) <= 0.002 for d in diam),
        [round(d, 4) for d in diam])

    dz, par = rep.get("axle_level_dz"), rep.get("axle_parallel")
    add("R05_axle_pose", "must",
        dz is not None and dz <= 0.002 and par <= 0.002,
        f"level_dz={dz} parallel_dx={par}")

    b0, b1 = rep.get("body_before_spin"), rep.get("body_after_spin")
    moved = 0.0
    if b0 and b1:
        moved = max(abs(b0[0][i] - b1[0][i]) + abs(b0[1][i] - b1[1][i]) for i in range(3))
    add("R06_wheel_spin", "must", bool(b0 and b1) and moved < 1e-6,
        f"body moved {moved:.2e}")

    steer = rep.get("steer_parents") or {}
    add("R07_steering", "must", steer == {"wheel_fl": "steer_fl", "wheel_fr": "steer_fr"}, steer)

    doors = rep.get("doors") or {}
    d_ok, dd = set(doors) == {"door_l", "door_r"}, {}
    for name, info in doors.items():
        if not info:
            d_ok = False
            continue
        hp, front = info["hinge"], info["front_edge"]
        if front is None or abs(hp[0] - front) > 0.02:
            d_ok = False
        if any(info["overlap"].values()):
            d_ok = False
        dd[name] = {"hinge_x": round(hp[0], 3), "overlap": info["overlap"]}
    add("R08_doors", "must", d_ok, dd)

    views = ["front", "side", "back", "top"]
    r_ok, detail, hashes = True, [], []
    for v in views:
        p = os.path.join(out, f"render_{v}.png")
        if not os.path.exists(p):
            r_ok = False
            detail.append(f"{v}:missing")
            continue
        hashes.append(sha(p))
        detail.append(f"{v}:{Image.open(p).size}")
        if Image.open(p).size != (1200, 1200):
            r_ok = False
    add("R09_views", "must", r_ok and len(set(hashes)) == 4, " ".join(detail))

    ious, s_ok = {}, True
    for v in views:
        ref = f"/tests/reference/silhouettes/{v}.png"
        got = os.path.join(out, f"render_{v}.png")
        if not os.path.exists(ref) or not os.path.exists(got):
            s_ok = False
            continue
        val = iou(mask_file(ref), mask(got))
        ious[v] = round(val, 3)
        if val < 0.75:
            s_ok = False
    add("R10_silhouette", "must", s_ok, ious)

    imgs = rep.get("images", [])
    unpacked = [i["name"] for i in imgs if i.get("filepath") and not i.get("packed")]
    add("R11_packed", "must", not unpacked, unpacked)

    polys = rep.get("polys_total", 10 ** 9)
    add("R12_polys", "normal", polys <= 150000, f"{polys} triangles")

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
    add("R13_manifest", "must", man_ok, md)

    ac_ok, acd = False, "skipped: prerequisite checks failed"
    if ok and all(c["pass"] for c in CHECKS) and os.path.exists(blend) and os.path.exists(os.path.join(out, "render_side.png")):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp, "--python", "/tests/rerender.py",
                 "--", os.path.join(WORK, "ac_base.png"), os.path.join(WORK, "ac_spun.png")], timeout=900)
            if os.path.exists(os.path.join(WORK, "ac_base.png")) and os.path.exists(os.path.join(WORK, "ac_spun.png")):
                base = gray(os.path.join(WORK, "ac_base.png"))
                spun = gray(os.path.join(WORK, "ac_spun.png"))
                delivered = gray(os.path.join(out, "render_side.png"), size=(960, 960))
                s_match = ss(base, delivered)
                s_chg = ss(base, spun)
                ac_ok = s_match >= 0.90 and s_chg <= 0.995
                acd = f"delivered_vs_scene={s_match:.3f} wheel90={s_chg:.3f}"
        except Exception as exc:
            acd = f"rerender failed: {exc}"
    add("R14_anti_cheat", "critical", ac_ok, acd)

    view_scores = {}
    try:
        for view in ['front', 'side', 'back', 'top']:
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
    result = {"reward": reward, "must_pass": must_pass, "critical_pass": crit_pass,
              "normal_rate": round(rate, 3), "checks": CHECKS}
    json.dump(result, open(os.path.join(WORK, "metrics.json"), "w"), indent=1)
    print(json.dumps(result, indent=1))
    return 0 if reward else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        CHECKS.append({"id": "R_verifier_error", "level": "must", "pass": False, "detail": str(exc)})
        print(json.dumps({"reward": 0, "must_pass": False, "critical_pass": False, "normal_rate": 0, "checks": CHECKS}, indent=1))
        sys.exit(1)
