"""Grader for crate-lookdev.

Usage: python3 grade.py /app/out
Exit 0 -> reward 1. Per-check detail is printed as JSON and also written to
/tmp/metrics.json; harbor only reads reward.txt.

Rubric levels follow the task README: every `must` and every `critical` check
has to pass, and at least 80% of `normal` checks.
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
from render_compare import gradient_error

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


def run(cmd, timeout, env=None):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    _log_process(cmd, r)
    r.check_returncode()
    return r


# --------------------------------------------------------------------------
# image helpers
# --------------------------------------------------------------------------
def ss_img(a, b):
    """SSIM on grayscale float arrays of equal shape, uniform 8x8 window."""
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    if a.shape != b.shape:
        return 0.0
    win = 8
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2

    def box(x):
        # mean over non-overlapping win x win blocks, then bilinear-free expand
        h, w = x.shape
        h2, w2 = h - h % win, w - w % win
        x = x[:h2, :w2].reshape(h2 // win, win, w2 // win, win).mean(axis=(1, 3))
        return x

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


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/app/out"
    blend = os.path.join(out, "crate.blend")
    scene = {}
    scene_ok = False

    if os.path.exists(blend):
        try:
            r = run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", blend, "--python", "/tests/check_scene.py",
                     "--", os.path.join(WORK, "scene.json")], timeout=600)
            if r.returncode == 0 and os.path.exists(os.path.join(WORK, "scene.json")):
                with open(os.path.join(WORK, "scene.json")) as fh:
                    scene = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
                scene_ok = bool(scene.get("ok"))
            if not scene_ok:
                print((r.stderr or "")[-2000:], file=sys.stderr)
        except Exception as exc:
            print("check_scene failed:", exc, file=sys.stderr)

    # ---- R01 the file opens and is a real scene -------------------------
    add("R01_open", "must", scene_ok and scene.get("blender", "").startswith("4."),
        scene.get("blender", "unreadable"))

    objs = scene.get("objects", {})
    meshes = set(scene.get("meshes", []))

    panels = ["crate_front", "crate_back", "crate_left", "crate_right", "crate_bottom"]
    brackets = scene.get("brackets", [])
    parts_ok = (all(p in meshes for p in panels) and "crate_lid" in meshes
                and scene.get("has_stencil", False) and len(brackets) == 8)
    add("R02_parts", "must", parts_ok,
        f"panels={scene.get('panels_present')} lid={'crate_lid' in meshes} "
        f"stencil={scene.get('has_stencil')} brackets={len(brackets)}")

    # ---- R03 outer size --------------------------------------------------
    size = scene.get("outer_size") or [0, 0, 0]
    want = [0.800, 0.600, 0.600]
    ok = all(abs(s - w) <= 0.005 for s, w in zip(size, want))
    add("R03_outer_size", "must", ok, f"{[round(s, 4) for s in size]} m")

    # ---- R04 panel thickness --------------------------------------------
    th_ok, th_detail = True, []
    for p in panels:
        aabb = objs.get(p, {}).get("aabb")
        if not aabb:
            th_ok = False
            th_detail.append(f"{p}:missing")
            continue
        dims = [aabb[1][i] - aabb[0][i] for i in range(3)]
        th = min(dims)
        th_detail.append(f"{p}:{th*1000:.1f}mm")
        if not (0.018 <= th <= 0.022):
            th_ok = False
    add("R04_thickness", "must", th_ok, " ".join(th_detail))

    # ---- R05 lid hinge ---------------------------------------------------
    lid = scene.get("lid") or {}
    pl = lid.get("parent_location") or [0, 0, 0]
    hinge_ok = (lid.get("parent") is not None
                and abs(pl[0]) < 0.01 and abs(pl[1] - 0.300) < 0.01
                and abs(pl[2] - 0.580) < 0.01)
    overlap = lid.get("overlap") or {}
    angles = {k: v for k, v in overlap.items() if k != "sign"}
    no_pen = bool(angles) and all(v == 0 for v in angles.values())
    add("R05_lid_hinge", "must", hinge_ok and no_pen,
        f"parent={lid.get('parent')} at {[round(c,3) for c in pl]} overlap={overlap}")

    # ---- R06 real geometry ----------------------------------------------
    bevel_ok = True
    bev_detail = []
    for name in panels + ["crate_lid"]:
        mods = objs.get(name, {}).get("modifiers") or []
        widths = [m.get("width") for m in mods if m.get("type") == "BEVEL" and m.get("width")]
        w = max(widths) if widths else 0.0
        bev_detail.append(f"{name}:{w*1000:.1f}mm")
        if w < 0.002:
            bevel_ok = False
    solid_brackets = all(
        objs.get(b, {}).get("polys", 0) >= 12 and objs.get(b, {}).get("aabb")
        for b in brackets
    )
    add("R06_real_geometry", "must", bevel_ok and solid_brackets,
        "bevel " + " ".join(bev_detail) + f" brackets_solid={solid_brackets}")

    # ---- R07 PBR map set -------------------------------------------------
    mats = scene.get("materials", {})
    front_mats = [m for m in (objs.get("crate_front", {}).get("materials") or []) if m]
    wood = mats.get(front_mats[0], {}) if front_mats else {}
    imgs = wood.get("images", [])
    big = [i for i in imgs if i.get("size", [0, 0])[0] >= 2048
           and i.get("size", [0, 0])[1] >= 2048 and i.get("packed")]
    feeds = [now for i in big for now in i.get("feeds", [])]
    # A map is "wired" if it reaches the shader directly or through any node;
    # what matters is that the material actually uses three 2K maps and one of
    # them drives a normal map node.
    has_base = any("Base Color" in f for f in feeds)
    has_rough = any("Roughness" in f for f in feeds)
    has_normal = any("BSDF_PRINCIPLED:Normal" in f for f in feeds) and any("NORMAL_MAP" in f for f in feeds)
    packed_all = all(i.get("packed") for i in scene.get("images", [])
                     if i.get("filepath"))
    add("R07_pbr_maps", "must",
        len({i["name"] for i in big if any(f in i.get("feeds", []) for f in ("BSDF_PRINCIPLED:Base Color", "BSDF_PRINCIPLED:Roughness", "BSDF_PRINCIPLED:Normal"))}) >= 3 and has_base and has_rough and has_normal and packed_all,
        f"big_maps={len(big)} base={has_base} rough={has_rough} normal={has_normal} "
        f"packed_all={packed_all}")

    # ---- R08 material distinction ---------------------------------------
    rough_std = wood.get("roughness_std")
    if rough_std is None:
        rough_std = max([i.get("grey_std", 0.0) for i in imgs if "BSDF_PRINCIPLED:Roughness" in i.get("feeds", [])] or [0.0])
    bracket_mats = [m for m in (objs.get(brackets[0], {}).get("materials") or []) if m] if brackets else []
    bmat = mats.get(bracket_mats[0], {}) if bracket_mats else {}
    metal = bmat.get("metallic")
    rough_ok = rough_std is not None and rough_std >= 0.05
    add("R08_materials", "must", rough_ok and (metal or 0) >= 0.9,
        f"wood_roughness_std={rough_std} bracket_metallic={metal}")

    # ---- R09 stencil wear ------------------------------------------------
    smats = [m for m in (objs.get("stencil_text", {}).get("materials") or []) if m]
    smat = mats.get(smats[0], {}) if smats else {}
    frac = smat.get("alpha_frac")
    cov = smat.get("alpha_coverage")
    if frac is None:
        cand = [i for i in smat.get("images", []) if i.get("alpha_frac") is not None]
        if cand:
            frac = cand[0]["alpha_frac"]
            cov = cand[0].get("alpha_coverage")
    add("R09_stencil_wear", "normal",
        frac is not None and frac >= 0.02 and cov is not None and 0.002 < cov < 0.7,
        f"edge_fraction={frac} coverage={cov}")

    # ---- R10 renders + cameras ------------------------------------------
    renders = {
        "render_front.png": (1600, 1200),
        "render_back.png": (1600, 1200),
        "render_top.png": (1600, 1280),
        "render_macro.png": (1600, 1200),
    }
    r_ok, r_detail = True, []
    hashes = []
    for f, (w, h) in renders.items():
        p = os.path.join(out, f)
        if not os.path.exists(p):
            r_ok = False
            r_detail.append(f"{f}:missing")
            continue
        iw, ih = Image.open(p).size
        hashes.append(file_sha(p))
        r_detail.append(f"{f}:{iw}x{ih}")
        if (iw, ih) != (w, h):
            r_ok = False
    distinct = len(set(hashes)) == len(hashes) == 4

    cams = scene.get("cameras", {})
    cam_ok, c_detail = True, []
    cf = cams.get("cam_front")
    if cf:
        dist = math.hypot(cf["location"][0], cf["location"][1])
        good = abs(cf.get("lens", 0) - 35) <= 1.0 and abs(dist - 1.6) <= 0.06 \
            and abs(cf["location"][2] - 0.9) <= 0.03
        cam_ok &= good
        c_detail.append(f"front lens={cf.get('lens')} d={dist:.3f} z={cf['location'][2]:.3f}")
    else:
        cam_ok = False
    cb = cams.get("cam_back")
    if cb:
        dist = math.hypot(cb["location"][0], cb["location"][1])
        cam_ok &= abs(cb.get("lens", 0) - 35) <= 1.0 and abs(dist - 1.6) <= 0.06
        c_detail.append(f"back d={dist:.3f}")
    else:
        cam_ok = False
    ct = cams.get("cam_top")
    if ct:
        cam_ok &= ct.get("type") == "ORTHO" and ct.get("ortho_scale", 0) >= 0.99
        c_detail.append(f"top ortho={ct.get('ortho_scale')}")
    else:
        cam_ok = False
    cm = cams.get("cam_macro")
    if cm:
        nearest = min((math.dist(cm["location"], objs[b]["location"])
                       for b in brackets if objs.get(b, {}).get("location")), default=99)
        cam_ok &= abs(cm.get("lens", 0) - 100) <= 5 and abs(nearest - 0.25) <= 0.06
        c_detail.append(f"macro lens={cm.get('lens')} d={nearest:.3f}")
    else:
        cam_ok = False
    add("R10_renders", "must", r_ok and distinct and cam_ok,
        " ".join(r_detail) + f" distinct={distinct} " + " ".join(c_detail))

    # ---- R11 poly budget -------------------------------------------------
    polys = scene.get("polys_total", 10 ** 9)
    add("R11_polys", "normal", polys <= 200000, f"{polys} triangles")

    # ---- R12 licence manifest -------------------------------------------
    man_ok, m_detail = False, "missing"
    mp = os.path.join(out, "manifest.json")
    if os.path.exists(mp):
        try:
            with open(mp) as fh:
                man = json.load(fh, parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
            assets = man.get("assets", [])
            have = [a for a in assets if a.get("source") and a.get("license")]
            hdri = [a for a in assets if a.get("role") == "hdri"
                    and a.get("source") and a.get("license")]
            man_ok = len(have) >= 1 and len(hdri) >= 1 and all(
                ("url" in a or a.get("role") == "texture") for a in assets)
            m_detail = f"assets={len(assets)} licensed={len(have)} hdri={len(hdri)}"
        except Exception as exc:
            m_detail = f"unreadable: {exc}"
    add("R12_manifest", "must", man_ok, m_detail)

    # ---- R13 anti-cheat --------------------------------------------------
    ac_ok, ac_detail = False, "skipped: prerequisite checks failed"
    if scene_ok and all(c["pass"] for c in CHECKS) and os.path.exists(blend) and os.path.exists(os.path.join(out, "render_front.png")):
        try:
            cp = os.path.join(WORK, "anticheat.blend")
            shutil.copy(blend, cp)
            r = run([BLENDER, "--disable-autoexec", "--python-exit-code", "2", "-b", cp, "--python", "/tests/rerender.py",
                     "--", os.path.join(WORK, "ac_base.png"), os.path.join(WORK, "ac_lid.png")], timeout=900)
            if os.path.exists(os.path.join(WORK, "ac_base.png")) and os.path.exists(os.path.join(WORK, "ac_lid.png")):
                base = load_gray(os.path.join(WORK, "ac_base.png"))
                lidimg = load_gray(os.path.join(WORK, "ac_lid.png"))
                delivered = load_gray(os.path.join(out, "render_front.png"),
                                      size=(960, 720))
                s_match = ss_img(base, delivered)
                s_change = ss_img(base, lidimg)
                ac_ok = s_match >= 0.90 and s_change <= 0.98
                ac_detail = f"delivered_vs_scene={s_match:.3f} (>=0.90) lid60_vs_closed={s_change:.3f} (<=0.98)"
            else:
                ac_detail = "rerender produced no images"
                print((r.stderr or "")[-1500:], file=sys.stderr)
        except Exception as exc:
            ac_detail = f"rerender failed: {exc}"
    add("R13_render_authenticity", "critical", ac_ok, ac_detail)

    # ---- verdict ---------------------------------------------------------
    view_scores = {}
    view_gradients = {}
    try:
        for view in ['front', 'back', 'top', 'macro']:
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
        print(json.dumps({"reward": 0, "must_pass": False, "critical_pass": False, "normal_rate": 0, "checks": CHECKS}, indent=1))
        sys.exit(1)
