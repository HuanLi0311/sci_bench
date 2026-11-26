"""Back up, correct reference color space, render, publish and regenerate cases.

Geometry stays unchanged. All old files, hashes, exact commands, raw output and
new source snapshots are retained under the authoring run before publishing.
"""
import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess

from record_baselines import ROOT, inventory, sha

TASK = ROOT / "booth-clearance"


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


if __name__ == "__main__":
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = TASK / "authoring" / "runs" / (stamp + "-reference-srgb-repair")
    run.mkdir(parents=True)
    backup = run / "backup"
    shutil.copytree(TASK / "solution", backup / "solution")
    shutil.copytree(TASK / "environment/materials/photos", backup / "photos")
    source = run / "source"
    source.mkdir()
    for name in ("build_booth.py", "render_photos.py"):
        shutil.copy2(TASK / "authoring" / name, source / name)
    shutil.copytree(TASK / "tests", source / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    meta = {"started_at": now(), "reason": "Correct shader linear RGB for supplied sRGB hex colors; preserve geometry and historical evidence", "backup": inventory(backup), "source": inventory(source), "commands": []}
    stage = run / "stage"
    (stage / "solution").mkdir(parents=True)
    (source / "update_colors.py").write_text('''import bpy, json, hashlib, sys
def signature():
    data = {o.name: {"matrix": [list(r) for r in o.matrix_world], "verts": [list(v.co) for v in o.data.vertices], "faces": [list(p.vertices) for p in o.data.polygons]} for o in bpy.data.objects if o.type == "MESH"}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
def linear(n):
    v=n/255.0
    return v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4
before = signature()
colors = {"mat_brand_primary": (31,111,92), "mat_brand_secondary": (242,193,78)}
changes = {}
for name, color in colors.items():
    mat=bpy.data.materials[name]
    node=next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    old=list(node.inputs["Base Color"].default_value)
    value=tuple(linear(v) for v in color)+(1,)
    node.inputs["Base Color"].default_value=value
    mat.diffuse_color=value
    changes[name]={"old_linear":old,"new_linear":value,"srgb_8bit":color}
after=signature()
assert before==after, "Geometry unexpectedly changed"
output=sys.argv[sys.argv.index("--")+1]
bpy.ops.wm.save_as_mainfile(filepath=output, compress=True)
with open("/stage/color-change.json","w") as f: json.dump({"geometry_sha256_before":before,"geometry_sha256_after":after,"materials":changes},f,indent=2)
print(json.dumps({"geometry_unchanged":before==after,"materials":changes}))
''')
    (source / "render_formal.py").write_text('''import bpy, os, sys
out=sys.argv[sys.argv.index("--")+1]
sc=bpy.context.scene
sc.render.engine="CYCLES"
sc.cycles.device="CPU"
sc.cycles.samples=64
sc.cycles.use_denoising=True
sc.cycles.seed=0
sc.render.resolution_percentage=100
sc.render.image_settings.file_format="PNG"
for name, camera, size in (("render_entrance","cam_entrance",(1920,1080)),("render_top","cam_top",(2048,1536))):
    sc.camera=bpy.data.objects[camera]
    sc.render.resolution_x,sc.render.resolution_y=size
    sc.render.filepath=os.path.join(out,name+".png")
    bpy.ops.render.render(write_still=True)
    print("[formal]",name,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,"booth.blend"),compress=True)
''')

    def command(args, name, timeout=7200):
        item = {"argv": [str(a) for a in args], "started_at": now()}
        meta["commands"].append(item)
        (run / "repair.json").write_text(json.dumps(meta, indent=2) + "\n")
        with (run / (name + ".stdout.txt")).open("wb") as stdout, (run / (name + ".stderr.txt")).open("wb") as stderr:
            result = subprocess.run(args, stdout=stdout, stderr=stderr, timeout=timeout)
        item.update({"exit_code": result.returncode, "finished_at": now()})
        (run / "repair.json").write_text(json.dumps(meta, indent=2) + "\n")
        if result.returncode:
            raise RuntimeError(name + " failed; original files remain backed up")
        print(name, "exit", result.returncode, flush=True)

    meta["source"] = inventory(source)
    common = ["docker", "run", "--rm", "--network", "none", "--cpus", "4", "--memory", "8g", "--env", "PYTHONPATH=/source/tests", "-v", f"{source}:/source:ro", "-v", f"{stage}:/stage"]
    command(common + ["-v", f"{backup / 'solution'}:/input:ro", "blender-bench:gui", "blender", "--disable-autoexec", "--python-exit-code", "2", "-b", "/input/booth.blend", "--python", "/source/update_colors.py", "--", "/stage/solution/booth.blend"], "update-colors")
    probes = [("old-reference", backup / "solution"), ("new-reference", stage / "solution"), ("blind-model", TASK / "authoring/runs/20261126T084651Z-model-codex-terminal/submission")]
    meta["color_probes"] = []
    for label, folder in probes:
        command(common + ["-v", f"{folder}:/input:ro", "cua-qc-booth-clearance-tests", "blender", "--disable-autoexec", "--python-exit-code", "2", "-b", "/input/booth.blend", "--python", "/source/tests/check_scene.py", "--", "/stage/" + label + ".json"], "probe-" + label, 600)
        scene = json.loads((stage / (label + ".json")).read_text())
        result = {"case": label, "ok": scene.get("ok"), "brand_delta": scene.get("brand_delta")}
        meta["color_probes"].append(result)
        print(json.dumps(result), flush=True)
    assert meta["color_probes"][0]["brand_delta"] > 2
    assert all(p["ok"] and p["brand_delta"] <= 2 for p in meta["color_probes"][1:])
    command(common + ["blender-bench:gui", "blender", "--disable-autoexec", "--python-exit-code", "2", "-b", "/stage/solution/booth.blend", "--python", "/source/render_formal.py", "--", "/stage/solution"], "render-formal")
    command(common + ["blender-bench:gui", "blender", "--disable-autoexec", "--python-exit-code", "2", "-b", "/stage/solution/booth.blend", "--python", "/source/render_photos.py", "--", "/stage/photos"], "render-photos")
    for filename in ("booth.blend", "render_entrance.png", "render_top.png"):
        shutil.copy2(stage / "solution" / filename, TASK / "solution" / filename)
    for photo in (stage / "photos").glob("*.jpg"):
        shutil.copy2(photo, TASK / "environment/materials/photos" / photo.name)
    meta["published_at"] = now()
    meta["published_solution"] = inventory(TASK / "solution")
    meta["published_photos"] = inventory(TASK / "environment/materials/photos")
    command(["docker", "build", "-t", "cua-qc-booth-clearance-env", str(TASK / "environment")], "rebuild-environment")
    import prepare_mutations
    prepare_mutations.prepare("booth-clearance", "secondary-render-substitution", None)
    latest = sorted(TASK.glob("authoring/runs/*-mutation-secondary-render-substitution"))[-1]
    original_counterexample = TASK / "authoring/runs/20261126T074326Z-mutation-secondary-render-substitution/submission/render_top.png"
    target = latest / "submission/render_top.png"
    shutil.copy2(original_counterexample, target)
    (latest / "reuse-original-secondary.json").write_text(json.dumps({"source": str(original_counterexample.relative_to(ROOT)), "source_sha256": sha(original_counterexample), "target_sha256": sha(target), "reason": "Keep exactly the same solid-color counterexample PNG while using the corrected reference scene/colors"}, indent=2) + "\n")
    for name in ("booth-moved-entrance-marker", "booth-product-scaled", "booth-product-floating", "booth-unused-brand-slot", "booth-closed-opening", "booth-camera-away", "booth-empty-marker-positive"):
        prepare_mutations.prepare("booth-clearance", name, prepare_mutations.SCRIPTS[name])
    meta["finished_at"] = now()
    (run / "repair.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("REPAIR", run, flush=True)
