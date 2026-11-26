"""Extract real Oracle/model/representation scenes without rendering or modifying them."""
import datetime as dt
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from record_baselines import ROOT, inventory


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", nargs="+", choices=["booth-clearance", "crate-lookdev"], default=["booth-clearance", "crate-lookdev"])
    options = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch = ROOT / "evaluation" / (stamp + "-scene-probes")
    batch.mkdir(parents=True)
    tasks = {t: ROOT / t for t in ("booth-clearance", "crate-lookdev")}
    for task, directory in tasks.items():
        if task in options.tasks:
            shutil.copytree(directory / "tests", batch / "source" / task, ignore=shutil.ignore_patterns("__pycache__"))
    booth = tasks["booth-clearance"]
    crate = tasks["crate-lookdev"]
    cases = [
        ("booth-oracle", "booth-clearance", booth / "solution" / "booth.blend"),
        ("booth-model", "booth-clearance", booth / "authoring/runs/20261126T084651Z-model-codex-terminal/submission/booth.blend"),
        ("booth-empty-positive", "booth-clearance", sorted(booth.glob("authoring/runs/*-representation-booth-empty-marker-positive/submission/booth.blend"))[-1]),
        ("crate-oracle", "crate-lookdev", crate / "solution" / "crate.blend"),
        ("crate-model-font", "crate-lookdev", crate / "authoring/runs/historical/2026-11-25__22-10-48/crate-lookdev__dMX45qL/artifacts/app/out/crate.blend"),
    ]
    for name in ("booth-closed-opening", "booth-camera-away", "booth-missing-secondary-color"):
        cases.append((name, "booth-clearance", sorted(booth.glob(f"authoring/runs/*-mutation-{name}/submission/booth.blend"))[-1]))
    rows = []
    for label, task, blend in cases:
        if task not in options.tasks:
            continue
        run = batch / label
        run.mkdir()
        command = ["docker", "run", "--rm", "--network", "none", "--cpus", "4", "--memory", "8g", "-v", f"{batch / 'source' / task}:/tests:ro", "-v", f"{blend.parent}:/submission:ro", "-v", f"{run}:/diagnostic", f"cua-qc-{task}-tests", "blender", "--disable-autoexec", "--python-exit-code", "2", "-b", "/submission/" + blend.name, "--python", "/tests/check_scene.py", "--", "/diagnostic/scene.json"]
        meta = {"label": label, "source_blend": str(blend), "argv": command, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(), "grader_source": inventory(batch / "source" / task), "submission_access": "read-only"}
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        (run / "stdout.txt").write_text(result.stdout)
        (run / "stderr.txt").write_text(result.stderr)
        meta.update({"exit_code": result.returncode, "finished_at": dt.datetime.now(dt.timezone.utc).isoformat()})
        if (run / "scene.json").exists():
            scene = json.loads((run / "scene.json").read_text())
            meta["scene_ok"] = scene.get("ok")
            meta["scene_error"] = scene.get("error")
        (run / "probe.json").write_text(json.dumps(meta, indent=2) + "\n")
        rows.append({"label": label, "exit_code": result.returncode, "scene_ok": meta.get("scene_ok"), "scene_error": meta.get("scene_error")})
        print(json.dumps(rows[-1]), flush=True)
    (batch / "probes.json").write_text(json.dumps(rows, indent=2) + "\n")
    print("PROBES", batch, flush=True)
