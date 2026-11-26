"""Freeze all five graders, then record Oracle, NOP, 9 negatives and model regrade.

WSL: python3 tasks/cua/tools/record_final.py
All records remain in each task's authoring/runs; batch.json links them and
records the common frozen source hashes used by every run for that task.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import shutil

from record_baselines import ROOT, TASKS, inventory, record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=3, choices=range(1, 4))
    options = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch = ROOT / "evaluation" / (stamp + "-final")
    batch.mkdir(parents=True)
    meta = {"started_at": stamp, "label": "final", "grader_sources": {}, "runs": []}
    jobs = []
    for task in TASKS:
        source = batch / "grader-source" / task
        shutil.copytree(ROOT / task / "tests", source, ignore=shutil.ignore_patterns("__pycache__"))
        meta["grader_sources"][task] = inventory(source)
        jobs.append((task, [("oracle", None), ("nop", None)]))
    mutation_jobs = []
    for task in TASKS:
        mutations = {}
        for path in sorted((ROOT / task / "authoring" / "runs").glob("*-mutation-*/submission")):
            name = path.parent.name.split("-mutation-", 1)[1]
            mutations[name] = path
        for name, path in mutations.items():
            mutation_jobs.append((task, [("negative-" + name, path)]))
    if len(mutation_jobs) != 9:
        raise SystemExit(f"Expected 9 prepared mutations, found {len(mutation_jobs)}")
    jobs.extend(mutation_jobs)
    model = ROOT / "crate-lookdev" / "authoring" / "runs" / "historical" / "2026-11-25__22-10-48" / "crate-lookdev__dMX45qL" / "artifacts" / "app" / "out"
    if not model.is_dir():
        raise SystemExit(f"Historical model output missing: {model}")
    jobs.append(("crate-lookdev", [("model-regrade", model)]))
    (batch / "batch.json").write_text(json.dumps(meta, indent=2) + "\n")

    def run_job(job):
        task, cases = job
        rows = []
        for kind, submission in cases:
            path = record(task, kind, "final", submission, batch / "grader-source" / task)
            run_meta = json.loads((path / "run.json").read_text())
            rows.append({"task": task, "kind": kind, "run": str(path.relative_to(ROOT)), "reward": run_meta.get("reward"), "outcome": run_meta.get("outcome"), "failed_checks": run_meta.get("failed_checks")})
        return rows

    with ThreadPoolExecutor(max_workers=options.jobs) as pool:
        for rows in pool.map(run_job, jobs):
            meta["runs"].extend(rows)
            (batch / "batch.json").write_text(json.dumps(meta, indent=2) + "\n")
    meta["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (batch / "batch.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("BATCH", batch, flush=True)
