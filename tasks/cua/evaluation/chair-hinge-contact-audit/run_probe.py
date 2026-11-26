"""Reproduce collision exemption away from a hinge, without changing the task."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from record_baselines import record, inventory

run = Path(__file__).parent / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
run.mkdir()
submission = run / "submission"
shutil.copytree(ROOT / "folding-chair/solution", submission,
                ignore=shutil.ignore_patterns("*.blend1", "solve.sh"))
script = run / "mutate.py"
script.write_text('''import bpy, json, sys
from mathutils.bvhtree import BVHTree
bpy.context.scene.frame_set(0)
hinge = bpy.data.objects["hinge_01"]
added = []
for name, point in (("collision_a", (-.28, 0, .100)), ("collision_b", (-.277, .003, .102))):
    bpy.ops.mesh.primitive_cube_add(size=.014, location=point)
    ob = bpy.context.object
    ob.name = name
    bpy.context.view_layer.update()
    matrix = ob.matrix_world.copy()
    ob.parent = hinge
    ob.matrix_world = matrix
    added.append(ob)
bpy.context.view_layer.update()
def tree(ob):
    return BVHTree.FromPolygons([ob.matrix_world @ v.co for v in ob.data.vertices],
                               [tuple(p.vertices) for p in ob.data.polygons])
pairs = tree(added[0]).overlap(tree(added[1]))
assert pairs
proof = {"surface_intersections": len(pairs), "cube_centres": [list(o.matrix_world.translation) for o in added],
         "hinge": list(hinge.matrix_world.translation), "cube_size_m": .014,
         "parents": [o.parent.name for o in added]}
print("COLLISION_PROOF", json.dumps(proof))
with open('/audit/collision-proof.json', 'w') as f: json.dump(proof, f, indent=2)
bpy.ops.wm.save_as_mainfile(filepath="/audit/submission/folding_chair.blend", compress=True)
''', encoding="utf-8")
command = ["docker", "run", "--rm", "--network", "none", "--cpus", "4", "--memory", "8g",
           "-v", f"{run}:/audit", "cua-qc-folding-chair-tests", "blender", "--disable-autoexec",
           "--python-exit-code", "2", "-b", "/audit/submission/folding_chair.blend", "-t", "4",
           "--python", "/audit/mutate.py"]
with (run / "mutate.stdout.txt").open("wb") as stdout, (run / "mutate.stderr.txt").open("wb") as stderr:
    result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=300)
meta = {"purpose": "Independent negative collision probe, never NOP or model inference",
        "argv": command, "exit_code": result.returncode, "source": inventory(ROOT / "folding-chair/tests"),
        "mutation_sha256": hashlib.sha256(script.read_bytes()).hexdigest()}
(run / "probe.json").write_text(json.dumps(meta, indent=2) + "\n")
if result.returncode:
    raise SystemExit(result.returncode)
grading = record("folding-chair", "negative-hinge-contact-probe", "audit", submission)
meta["grading_run"] = str(grading.relative_to(ROOT))
meta["result"] = json.loads((grading / "run.json").read_text())
(run / "probe.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps({"probe": str(run), "grading_run": str(grading), "reward": meta["result"].get("reward"),
                  "failed_checks": meta["result"].get("failed_checks")}), flush=True)
