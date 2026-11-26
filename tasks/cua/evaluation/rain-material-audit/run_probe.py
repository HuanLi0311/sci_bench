"""Probe whether an unused material slot satisfies rainroom's metal check."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from record_baselines import record

run = Path(__file__).parent / dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
run.mkdir()
submission = run / "submission"
shutil.copytree(ROOT / "rainroom/solution", submission,
                ignore=shutil.ignore_patterns("*.blend1", "solve.sh"))
script = run / "mutate.py"
script.write_text('''import bpy, json
for material in bpy.data.materials:
    if material.use_nodes:
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Metallic'].default_value = 0.0
fake = bpy.data.materials.new('adversarial_unused_metal')
fake.use_nodes = True
fake.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value = 1.0
shell = bpy.data.objects['room_shell']
shell.data.materials.append(fake)
slot = len(shell.data.materials) - 1
assert not any(p.material_index == slot for p in shell.data.polygons)
proof = {'unused_material': fake.name, 'slot': slot, 'assigned_faces': 0,
         'all_other_principled_metallic': 0.0}
with open('/audit/material-proof.json', 'w') as f: json.dump(proof, f, indent=2)
bpy.ops.wm.save_as_mainfile(filepath='/audit/submission/rainroom.blend', compress=True)
''', encoding="utf-8")
command = ["docker", "run", "--rm", "--network", "none", "--cpus", "4", "--memory", "8g",
           "-v", f"{run}:/audit", "cua-qc-rainroom-tests", "blender", "--disable-autoexec",
           "--python-exit-code", "2", "-b", "/audit/submission/rainroom.blend", "-t", "4",
           "--python", "/audit/mutate.py"]
with (run / "mutate.stdout.txt").open("wb") as stdout, (run / "mutate.stderr.txt").open("wb") as stderr:
    result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=300)
meta = {"purpose": "Independent material negative, never NOP or model inference", "argv": command,
        "exit_code": result.returncode, "mutation_sha256": hashlib.sha256(script.read_bytes()).hexdigest()}
(run / "probe.json").write_text(json.dumps(meta, indent=2) + "\n")
if result.returncode:
    raise SystemExit(result.returncode)
grading = record("rainroom", "negative-unused-metal-probe", "audit", submission)
meta["grading_run"] = str(grading.relative_to(ROOT))
meta["result"] = json.loads((grading / "run.json").read_text())
(run / "probe.json").write_text(json.dumps(meta, indent=2) + "\n")
print(json.dumps({"probe": str(run), "grading_run": str(grading), "reward": meta["result"].get("reward"),
                  "failed_checks": meta["result"].get("failed_checks")}), flush=True)
