"""Grader for crate-web3d. Usage: python3 grade.py /app/out"""
import json
import math
import os
import shutil
import subprocess
import sys
import hashlib

import numpy as np
from PIL import Image

sys.path.insert(0, "/tests")
import glb  # noqa: E402

CHECKS = []
NODE = shutil.which("node") or "/usr/bin/node"
PANELS = ["crate_front", "crate_back", "crate_left", "crate_right", "crate_bottom"]
VIEWS = {"front": (1200, 900), "back": (1200, 900),
         "top": (1200, 900), "macro": (1200, 900)}


def add(cid, level, ok, detail=""):
    CHECKS.append({"id": cid, "level": level, "pass": bool(ok), "detail": str(detail)})


def run(cmd, timeout):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


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


def render(glb_path, camera, out, w, h, rotate=""):
    cmd = [NODE, "/tests/render.js", "--glb", glb_path, "--camera", camera,
           "--out", out, "--w", str(w), "--h", str(h)]
    if rotate:
        cmd += ["--rotate", rotate]
    return run(cmd, timeout=600)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    path = os.path.join(out, "crate.glb")
    rep, ok = {}, False
    if os.path.exists(path):
        try:
            rep = glb.report(path)
            ok = True
        except Exception as exc:
            rep = {"error": str(exc)}
    add("R01_glb", "must", ok, rep.get("generator", rep.get("error", "unreadable")))

    nodes = rep.get("nodes", {})
    missing = [n for n in PANELS + ["crate_lid", "stencil_text"] if n not in nodes]
    brackets = [n for n in nodes if n.startswith("bracket_")]
    add("R02_parts", "must", not missing and len(brackets) == 8,
        f"missing={missing} brackets={len(brackets)}")

    def dims(name):
        n = nodes.get(name)
        return n["dims"] if n and "dims" in n else None

    crate = PANELS + ["crate_lid"] + brackets
    if all(dims(n) for n in crate):
        lo = [min(nodes[n]["aabb"][0][i] for n in crate) for i in range(3)]
        hi = [max(nodes[n]["aabb"][1][i] for n in crate) for i in range(3)]
        size = [hi[i] - lo[i] for i in range(3)]
    else:
        size = [0, 0, 0]
    add("R03_outer_size", "must",
        all(abs(size[i] - w) <= 0.005 for i, w in enumerate((0.800, 0.600, 0.600))),
        [round(s, 4) for s in size])

    thick, tdetail = True, {}
    for p in PANELS:
        d = dims(p)
        if not d:
            thick = False
            continue
        t = min(d)
        tdetail[p] = round(t * 1000, 1)
        if not (0.018 <= t <= 0.022):
            thick = False
    add("R04_thickness", "must", thick, tdetail)

    lid = nodes.get("crate_lid", {})
    hinge = nodes.get("lid_hinge", {})
    hp = hinge.get("world_translation") or [9, 9, 9]
    hinge_ok = (lid.get("parent") == "lid_hinge"
                and abs(hp[0]) < 0.01 and abs(hp[1] - 0.300) < 0.01
                and abs(hp[2] - 0.580) < 0.01)
    add("R05_lid_hinge", "must", hinge_ok,
        f"parent={lid.get('parent')} hinge={[round(c, 3) for c in hp]}")

    mats = rep.get("materials", {})
    iron = [m for m in mats.values() if m.get("metallic", 0) >= 0.9]
    paint = [m for m in mats.values() if m.get("alpha_mode") == "MASK"
             or m.get("has_base_texture")]
    add("R06_materials", "must", bool(iron) and bool(paint),
        f"metal={len(iron)} paint={len(paint)}")

    imgs = rep.get("images", [])
    add("R07_embedded_textures", "must",
        len(imgs) >= 1 and all(i.get("embedded") for i in imgs),
        [{"name": i["name"], "embedded": i["embedded"]} for i in imgs])

    polys = rep.get("polys_total", 10 ** 9)
    add("R08_polys", "normal", polys <= 200000, f"{polys} triangles")

    cams = rep.get("cameras", {})
    cam_ok = all(f"cam_{v}" in cams for v in VIEWS)
    add("R09_cameras", "must", cam_ok, sorted(cams))

    r_ok, detail, hashes = True, [], []
    for v, (w, h) in VIEWS.items():
        p = os.path.join(out, f"render_{v}.png")
        if not os.path.exists(p):
            r_ok = False
            detail.append(f"{v}:missing")
            continue
        iw, ih = Image.open(p).size
        hashes.append(sha(p))
        detail.append(f"{v}:{iw}x{ih}")
        if (iw, ih) != (w, h):
            r_ok = False
    add("R10_renders", "must", r_ok and len(set(hashes)) == 4, " ".join(detail))

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
    add("R11_manifest", "must", man_ok, md)

    # anti-cheat: the delivered front render must be reproducible from the glb,
    # and rotating the lid must change the picture
    ac_ok, acd = False, "not run"
    if ok and os.path.exists(os.path.join(out, "render_front.png")):
        try:
            r1 = render(path, "cam_front", "/tmp/ac_base.png", 800, 600)
            r2 = render(path, "cam_front", "/tmp/ac_lid.png", 800, 600, "lid_hinge:60")
            if os.path.exists("/tmp/ac_base.png") and os.path.exists("/tmp/ac_lid.png"):
                base = gray("/tmp/ac_base.png")
                lidimg = gray("/tmp/ac_lid.png")
                delivered = gray(os.path.join(out, "render_front.png"), size=(800, 600))
                s_match = ss(base, delivered)
                s_change = ss(base, lidimg)
                rotated = '"rotated":true' in (r2.stdout or "").replace(" ", "") or True
                ac_ok = s_match >= 0.90 and s_change <= 0.98
                acd = (f"delivered_vs_scene={s_match:.3f} (>=0.90) "
                       f"lid60={s_change:.3f} (<=0.98)")
            else:
                acd = f"render failed: {(r1.stderr or '')[-200:]}"
        except Exception as exc:
            acd = f"render failed: {exc}"
    add("R12_anti_cheat", "critical", ac_ok, acd)

    must = [c for c in CHECKS if c["level"] == "must"]
    crit = [c for c in CHECKS if c["level"] == "critical"]
    norm = [c for c in CHECKS if c["level"] == "normal"]
    must_pass = all(c["pass"] for c in must)
    crit_pass = all(c["pass"] for c in crit)
    rate = sum(c["pass"] for c in norm) / max(len(norm), 1)
    reward = 1 if (must_pass and crit_pass and rate >= 0.8) else 0
    result = {"reward": reward, "must_pass": must_pass, "critical_pass": crit_pass,
              "normal_rate": round(rate, 3), "checks": CHECKS}
    with open("/tmp/metrics.json", "w") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps(result, indent=1))
    return 0 if reward else 1


if __name__ == "__main__":
    sys.exit(main())
