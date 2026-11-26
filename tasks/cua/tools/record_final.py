"""Freeze selected graders, then record Oracle, NOP and prepared negatives.

WSL: python3 tasks/cua/tools/record_final.py
All records remain in each task's authoring/runs; batch.json links them and
records the common frozen source hashes used by every run for that task.
The full set includes a historical model regrade for crate-lookdev; the booth
subset contains Oracle, NOP and all prepared adversarial submissions.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import shutil

from record_baselines import ROOT, TASKS, inventory, record
from sanity_check import NEGATIVE_CASES


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=3, choices=range(1, 4))
    parser.add_argument("--tasks", nargs="+", choices=TASKS, default=TASKS)
    parser.add_argument("--structure-first", action="store_true", help="Record structural negatives before Oracle/NOP, then secondary-render substitution")
    parser.add_argument("--booth-model-artifact", type=Path, help="Regrade a preserved blind booth submission with the same frozen grader")
    options = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch = ROOT / "evaluation" / (stamp + "-final" + ("-" + options.tasks[0] if len(options.tasks) == 1 else ""))
    batch.mkdir(parents=True)
    meta = {"started_at": stamp, "label": "final", "grader_sources": {}, "runs": []}
    jobs = []
    for task in options.tasks:
        source = batch / "grader-source" / task
        shutil.copytree(ROOT / task / "tests", source, ignore=shutil.ignore_patterns("__pycache__"))
        meta["grader_sources"][task] = inventory(source)
        jobs.append((task, [("oracle", None), ("nop", None)]))
    mutation_jobs = []
    for task in options.tasks:
        mutations = {}
        for path in sorted((ROOT / task / "authoring" / "runs").glob("*-mutation-*/submission")):
            name = path.parent.name.split("-mutation-", 1)[1]
            mutations[name] = path
        if set(mutations) != NEGATIVE_CASES[task]:
            raise SystemExit(f"Mutation cases differ for {task}: expected={sorted(NEGATIVE_CASES[task])}, actual={sorted(mutations)}")
        for name, path in mutations.items():
            mutation_jobs.append((task, [("negative-" + name, path)]))
    expected_count = sum(len(NEGATIVE_CASES[task]) for task in options.tasks)
    if len(mutation_jobs) != expected_count:
        raise SystemExit(f"Expected {expected_count} prepared mutations, found {len(mutation_jobs)}")
    jobs.extend(mutation_jobs)
    model = ROOT / "crate-lookdev" / "authoring" / "runs" / "historical" / "2026-11-25__22-10-48" / "crate-lookdev__dMX45qL" / "artifacts" / "app" / "out"
    if "crate-lookdev" in options.tasks and not model.is_dir():
        raise SystemExit(f"Historical model output missing: {model}")
    if "crate-lookdev" in options.tasks:
        jobs.append(("crate-lookdev", [("model-regrade", model)]))
    if options.booth_model_artifact:
        if "booth-clearance" not in options.tasks or not options.booth_model_artifact.is_dir():
            parser.error("--booth-model-artifact requires booth-clearance and an existing submission directory")
        jobs.append(("booth-clearance", [("model-regrade", options.booth_model_artifact.resolve())]))
    if options.structure_first:
        jobs.sort(key=lambda job: (0 if job[1][0][0].startswith("negative-") and "secondary-render" not in job[1][0][0] else (2 if "secondary-render" in job[1][0][0] else 1)))
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
