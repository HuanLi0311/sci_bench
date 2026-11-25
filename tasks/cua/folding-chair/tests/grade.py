"""Grader for folding-chair.

Usage: python3 grade.py /app/out
"""
import json
import os
import shutil
import subprocess
import sys
import hashlib

import numpy as np
from PIL import Image

BLENDER = shutil.which("blender") or "/usr/local/bin/blender"
TOL = {"size": 0.005, "hinge": 0.002, "thickness": 0.095, "coincide": 0.005}
HINGES = {
    "hinge_01": (-0.28, 0.00, 0.225),
    "hinge_02": (0.28, 0.00, 0.225),
    "hinge_03": (-0.28, 0.27, 0.430),
    "hinge_04": (0.00, 0.27, 0.475),
}
LIMBS = ["seat", "back", "front_leg_l", "front_leg_r", "rear_leg_l", "rear_leg_r"]
CHECKS = []


def add(cid, level, ok, detail=""):
    CHECKS.append({"id": cid, "level": level, "pass": bool(ok), "detail": str(detail)})
    return ok


def run(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def ss_img(a, b):
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


def gray(path, size=None):
    im = Image.open(path).convert("RGB")
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32).mean(-1)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "folding_chair.blend")
    rep, ok = {}, False
    if os.path.exists(blend):
        try:
            r = run([BLENDER, "-b", blend, "--python", "/tests/check_scene.py",
                     "--", "/tmp/scene.json"], timeout=900)
            if os.path.exists("/tmp/scene.json"):
                with open("/tmp/scene.json") as fh:
                    rep = json.load(fh)
                ok = bool(rep.get("ok"))
            if not ok:
                print((r.stderr or "")[-2000:], file=sys.stderr)
        except Exception as exc:
            print("check_scene failed:", exc, file=sys.stderr)

    add("R01_open", "must", ok and rep.get("blender", "").startswith("4."),
        rep.get("blender", "unreadable"))

    objs = rep.get("objects", {})
    missing = [n for n in LIMBS + list(HINGES) if n not in objs]
    add("R02_parts", "must", not missing, f"missing={missing}")

    hp_ok, hp_detail = True, {}
    for name, want in HINGES.items():
        got = rep.get("hinges", {}).get(name)
        if got is None:
            hp_ok = False
            continue
        d = max(abs(got[i] - want[i]) for i in range(3))
        hp_detail[name] = round(d, 4)
        if d > TOL["hinge"]:
            hp_ok = False
    add("R03_hinges", "must", hp_ok, hp_detail)

    st0 = rep.get("states", {}).get("0", {})
    if st0:
        mn = [min(st0[k][0][i] for k in st0 if not k.startswith("stage")) for i in range(3)]
        mx = [max(st0[k][1][i] for k in st0 if not k.startswith("stage")) for i in range(3)]
        size = [mx[i] - mn[i] for i in range(3)]
    else:
        size = [0, 0, 0]
    want = [0.620, 0.580, 0.820]
    add("R04_unfolded", "must",
        all(abs(size[i] - want[i]) <= TOL["size"] for i in range(3)),
        f"{[round(s, 3) for s in size]} m")

    thick = rep.get("folded_thickness", 9.9)
    add("R05_folded_thickness", "must", thick <= TOL["thickness"],
        f"{thick:.3f} m (<= 0.095)")

    fps = rep.get("fps")
    f0, f1 = rep.get("frame_start"), rep.get("frame_end")
    add("R06_animation", "must", fps == 24 and f0 == 0 and f1 == 60,
        f"{f0}-{f1} @ {fps} fps")

    overlaps = rep.get("overlaps") or {}
    add("R07_no_interpenetration", "must", not overlaps, overlaps)

    ends = rep.get("hinge_end_distance") or {}
    ends_ok = len(ends) == 4 and all(v is not None and v <= TOL["coincide"]
                                     for v in ends.values())
    add("R08_hinge_coincidence", "must", ends_ok,
        {k: (round(v, 4) if v is not None else None) for k, v in ends.items()})

    renders = ["render_unfolded.png", "render_half.png",
               "render_folded.png", "render_locked.png"]
    r_ok, detail, hashes = True, [], []
    for f in renders:
        p = os.path.join(out, f)
        if not os.path.exists(p):
            r_ok = False
            detail.append(f"{f}:missing")
            continue
        iw, ih = Image.open(p).size
        hashes.append(sha(p))
        detail.append(f"{f}:{iw}x{ih}")
        if (iw, ih) != (1200, 1200):
            r_ok = False
    add("R09_states", "must", r_ok and len(set(hashes)) == 4,
        " ".join(detail))

    imgs = rep.get("images", [])
    unpacked = [i["name"] for i in imgs if i.get("filepath") and not i.get("packed")]
    add("R10_packed", "must", not unpacked, unpacked)

    polys = rep.get("polys_total", 10 ** 9)
    add("R11_polys", "normal", polys <= 120000, f"{polys} triangles")

    man_ok, mdetail = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp) as fh:
                man = json.load(fh)
            assets = man.get("assets", [])
            man_ok = len(assets) >= 1 and all(a.get("source") and a.get("license")
                                              for a in assets)
            mdetail = f"assets={len(assets)}"
        except Exception as exc:
            mdetail = f"unreadable: {exc}"
    add("R12_manifest", "must", man_ok, mdetail)

    ac_ok, ac_detail = False, "not run"
    if ok and os.path.exists(blend) and os.path.exists(os.path.join(out, "render_unfolded.png")):
        try:
            cp = "/tmp/anticheat.blend"
            shutil.copy(blend, cp)
            run([BLENDER, "-b", cp, "--python", "/tests/rerender.py",
                 "--", "/tmp/ac_f0.png", "/tmp/ac_f30.png"], timeout=900)
            if os.path.exists("/tmp/ac_f0.png") and os.path.exists("/tmp/ac_f30.png"):
                f0img = gray("/tmp/ac_f0.png")
                f30 = gray("/tmp/ac_f30.png")
                delivered = gray(os.path.join(out, "render_unfolded.png"), size=(960, 960))
                s_match = ss_img(f0img, delivered)
                s_change = ss_img(f0img, f30)
                ac_ok = s_match >= 0.90 and s_change <= 0.98
                ac_detail = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                             f"frame30_vs_frame0={s_change:.3f} (<=0.98)")
            else:
                ac_detail = "rerender produced no images"
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R13_anti_cheat", "critical", ac_ok, ac_detail)

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
    with open("/tmp/metrics.json", "w") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps(result, indent=1))
    return 0 if reward == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
