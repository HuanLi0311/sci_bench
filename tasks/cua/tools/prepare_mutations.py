"""Prepare reproducible adversarial submissions from references (WSL Python).

Only prepares inputs; record_baselines.py --regrade runs the actual verifier.
"""
import datetime as dt
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RENDERS = {"crate-lookdev": "render_back.png", "booth-clearance": "render_top.png", "folding-chair": "render_locked.png", "rainroom": "render_night.png", "toy-car": "render_back.png"}
BLENDS = {"crate-lookdev": "crate.blend", "booth-clearance": "booth.blend", "folding-chair": "folding_chair.blend", "rainroom": "rainroom.blend", "toy-car": "toy_car.blend"}
SCRIPTS = {
    "crate-disconnected-maps": '''import bpy
mat = bpy.data.objects["crate_front"].data.materials[0]
bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
for name in ("Base Color", "Roughness"):
    for link in list(bsdf.inputs[name].links):
        mat.node_tree.links.remove(link)
''',
    "chair-common-root-collision": '''import bpy
root = bpy.data.objects.new("shared_non_hinge_root", None)
bpy.context.scene.collection.objects.link(root)
for name, x in (("collision_a", 0.0), ("collision_b", 0.01)):
    bpy.ops.mesh.primitive_cube_add(size=0.02, location=(x, 0, 0.5))
    ob = bpy.context.object
    ob.name = name
    ob.parent = root
''',
    "booth-moved-entrance-marker": '''import bpy
bpy.data.objects["entrance_zone"].location.x += 10.0
''',
    "toy-wrong-wheel-parent": '''import bpy
wheel = bpy.data.objects["wheel_fl"]
matrix = wheel.matrix_world.copy()
wheel.parent = bpy.data.objects["chassis"]
wheel.matrix_world = matrix
''',
}


def prepare(task, name, source):
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ROOT / task / "authoring" / "runs" / (stamp + "-mutation-" + name)
    run.mkdir(parents=True)
    submission = run / "submission"
    shutil.copytree(ROOT / task / "solution", submission, ignore=shutil.ignore_patterns("*.blend1", "solve.sh"))
    script = run / "mutate.py"
    if name == "secondary-render-substitution":
        script.write_text('''from PIL import Image, ImageStat
from pathlib import Path
import json
p = Path("/mutation/submission") / ''' + repr(RENDERS[task]) + '''
original = Image.open(p).convert("RGB")
mean = tuple(round(v) for v in ImageStat.Stat(original).mean)
Image.new("RGB", original.size, mean).save(p)
print(json.dumps({"file": p.name, "size": original.size, "original_rgb_mean": ImageStat.Stat(original).mean, "replacement_rgb": mean}))
''')
        command = ["docker", "run", "--rm", "--network", "none", "-v", f"{run}:/mutation", f"cua-qc-{task}-tests", "python3", "/mutation/mutate.py"]
    else:
        script.write_text(source + '\nbpy.ops.wm.save_as_mainfile(filepath=' + repr("/mutation/submission/" + BLENDS[task]) + ', compress=True)\n')
        command = ["docker", "run", "--rm", "--network", "none", "--cpus", "4", "--memory", "8g", "-v", f"{run}:/mutation", f"cua-qc-{task}-tests", "blender", "-b", "/mutation/submission/" + BLENDS[task], "--python", "/mutation/mutate.py"]
    meta = {"kind": "mutation-preparation", "name": name, "task": task, "started_at": stamp, "argv": command, "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(), "meaning": "Preserved reference copy mutated; this is a negative input, never NOP or model attempt."}
    with (run / "mutation.stdout.txt").open("wb") as stdout, (run / "mutation.stderr.txt").open("wb") as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=600)
    meta["exit_code"] = result.returncode
    meta["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (run / "mutation.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"task": task, "name": name, "submission": str(submission), "exit_code": result.returncode}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["secondary-render-substitution", *SCRIPTS])
    options = parser.parse_args()
    if not options.only or options.only == "secondary-render-substitution":
        for task_name in RENDERS:
            prepare(task_name, "secondary-render-substitution", None)
    for task_name, mutation in (("crate-lookdev", "crate-disconnected-maps"), ("folding-chair", "chair-common-root-collision"), ("booth-clearance", "booth-moved-entrance-marker"), ("toy-car", "toy-wrong-wheel-parent")):
        if not options.only or options.only == mutation:
            prepare(task_name, mutation, SCRIPTS[mutation])
