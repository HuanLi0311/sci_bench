"""Recover missing .blend references without replacing any existing reference.

Run with WSL Python. Crate is rebuilt with the checked-in authoring program;
four other references are recovered from preserved Blender backups/local copy.
Every source hash, command, exit code and raw output is retained.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FILENAMES = {"booth-clearance": "booth.blend", "folding-chair": "folding_chair.blend", "rainroom": "rainroom.blend", "toy-car": "toy_car.blend"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for task, filename in FILENAMES.items():
        target = ROOT / task / "solution" / filename
        if target.exists():
            continue
        source = target.with_suffix(".blend1")
        if task == "folding-chair" and Path("/tmp/verify/repo/folding-chair/solution/folding_chair.blend").exists():
            source = Path("/tmp/verify/repo/folding-chair/solution/folding_chair.blend")
        run = ROOT / task / "authoring" / "runs" / (stamp + "-reference-recovery")
        run.mkdir(parents=True)
        shutil.copy2(source, target)
        record = {"kind": "reference-recovery", "time_utc": stamp, "source": str(source), "target": str(target), "source_sha256": sha(source), "target_sha256": sha(target), "operation": "shutil.copy2; original source preserved", "note": "Recovery provenance, not a historical Oracle log; actual verification recorded separately."}
        (run / "recovery.json").write_text(json.dumps(record, indent=2) + "\n")
        print(task, "restored", sha(target), flush=True)
    task = ROOT / "crate-lookdev"
    if (task / "solution" / "crate.blend").exists():
        return
    run = task / "authoring" / "runs" / (stamp + "-reference-rebuild")
    run.mkdir(parents=True)
    shutil.copytree(task / "environment" / "materials", run / "materials")
    command = ["docker", "run", "--rm", "--network", "none", "--cpus", "4", "--memory", "8g", "-v", f"{task / 'authoring'}:/authoring:ro", "-v", f"{run}:/build", "blender-bench:gui", "blender", "-b", "--python", "/authoring/build_crate.py", "--", "/build/solution", "/build/materials"]
    meta = {"kind": "reference-rebuild", "started_at": stamp, "argv": command, "builder_sha256": sha(task / "authoring" / "build_crate.py")}
    (run / "rebuild.json").write_text(json.dumps(meta, indent=2) + "\n")
    with (run / "build.stdout.txt").open("wb") as stdout, (run / "build.stderr.txt").open("wb") as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=7200)
    meta["exit_code"] = result.returncode
    meta["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    if result.returncode == 0:
        for path in (run / "solution").rglob("*"):
            if path.is_file():
                target = task / "solution" / path.relative_to(run / "solution")
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
        meta["reference_sha256"] = sha(task / "solution" / "crate.blend")
    (run / "rebuild.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("crate rebuilt", result.returncode, flush=True)


if __name__ == "__main__":
    main()
