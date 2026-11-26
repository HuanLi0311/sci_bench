"""Refresh current validation reports and core-file inventory from real evidence."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

from record_baselines import ROOT, TASKS
from sanity_check import check_model_records, check_negative, check_recorded_run


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qc", type=Path, help="Completed whole-package QC metadata to link")
    options = parser.parse_args()
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    current_rows, summary = [], []
    package = {"checked_utc": stamp, "scope": "instruction, metadata, environment recipe/materials, reference deliverables and complete verifier source/fixtures; excludes caches and blend1 backups", "tasks": {}}
    tracked_result = subprocess.run(["git", "-c", "safe.directory=" + str(ROOT.parents[1]), "-C", str(ROOT.parents[1]), "ls-files", "-z", "tasks/cua"], capture_output=True, check=True)
    tracked = set(tracked_result.stdout.decode().split("\0"))
    for name in TASKS:
        task = ROOT / name
        source = {p.relative_to(task / "tests").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (task / "tests").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        gates = {"oracle": check_recorded_run(str(task), "oracle"), "nop": check_recorded_run(str(task), "nop"), "negatives": check_negative(str(task)), "models": check_model_records(str(task))}
        current_rows.append({"task": name, **{("model_records" if key == "models" else key): value for key, value in gates.items()}})
        latest = {}
        for path in sorted((task / "authoring/runs").glob("*-final-*/run.json")):
            meta = json.loads(path.read_text())
            recorded = {key: value["sha256"] for key, value in meta["grader_source"].items()}
            if recorded == source and meta.get("finished_at") and (meta["kind"] in ("oracle", "nop") or meta["kind"].startswith("negative-")):
                latest[meta["kind"]] = path
        for kind in ("oracle", "nop"):
            if gates[kind][0]:
                latest[kind] = task / "authoring/runs" / gates[kind][1] / "run.json"
        records = []
        for kind, path in sorted(latest.items(), key=lambda item: (0 if item[0] == "oracle" else 1 if item[0] == "nop" else 2, item[0])):
            meta = json.loads(path.read_text())
            metrics = json.loads((path.parent / "verifier/metrics.json").read_text())
            records.append({"kind": kind, "run": path.parent.name, "reward": meta.get("reward"), "passed_checks": sum(bool(c["pass"]) for c in metrics["checks"]), "check_count": len(metrics["checks"])})
        status = {"checked_utc": stamp, "gates": gates, "grader_source": source, "records": records}
        if options.qc:
            status["whole_package_qc"] = str(options.qc.resolve().relative_to(ROOT))
        folder = task / "authoring/calibration"
        (folder / "validation.json").write_text(json.dumps(status, indent=2) + "\n")
        lines = [f"# Current validation: {name}", "", f"Evidence checked {stamp}. These records match the current verifier source. Model provenance/completeness is separate from model-solving success.", "", "| Gate | Status | Evidence |", "|---|---|---|"]
        lines += [f"| {key} | {'PASS' if value[0] else 'PENDING / FAIL'} | {value[1]} |" for key, value in gates.items()]
        lines += ["", "| Case | Reward | Checks passed | Raw evidence |", "|---|---:|---:|---|"]
        for row in records:
            path = "../runs/" + row["run"]
            lines.append(f"| {row['kind']} | {row['reward']} | {row['passed_checks']}/{row['check_count']} | [metadata]({path}/run.json), [metrics]({path}/verifier/metrics.json), [reward]({path}/verifier/reward.txt) |")
        lines += ["", "NOP executes only /bin/true in a fresh environment and exports the untouched output. Mutations are separate actual grading runs. Model requests, artifact grades and GUI compliance are recorded in the [model inventory](../model-attempts.json)."]
        if options.qc:
            lines += ["", f"The completed [whole-package QC](../../../{options.qc.resolve().relative_to(ROOT).as_posix()}) retains its raw output and exit code."]
        (folder / "VALIDATION.md").write_text("\n".join(lines) + "\n")
        attempts = json.loads((task / "authoring/model-attempts.json").read_text())["attempts"]
        model_lines = [f"# Recorded model baselines: {name}", "", "Terminal baselines are explicitly gui_compliant=false. Execution status and artifact score are separate; API/setup failures are not model capability failures. No unrun result is invented.", "", "| Attempt | Execution | Artifact reward | Agent items / requests | Raw evidence |", "|---|---|---:|---|---|"]
        for attempt in attempts:
            path = Path(attempt["path"])
            if not path.is_absolute():
                path = ROOT.parents[1] / path
            relative = "../runs/" + path.relative_to(task / "authoring/runs").as_posix()
            model_lines.append(f"| {attempt['id']} | {attempt.get('outcome', attempt.get('status'))} | {attempt.get('reward', 'see inventory')} | {attempt.get('agent_steps')} / {attempt.get('tool_calls')} | [config]({relative}/config.json), [log]({relative}/trial.log), [inventory](../model-attempts.json) |")
        if not attempts:
            model_lines.append("| — | No actual task attempt recorded | — | — | [inventory](../model-attempts.json) |")
        model_lines += ["", "Raw Codex counts use assistant-message or function_call/custom_tool_call response items; tool requests count call items only. User/system messages, reasoning-only items, results and duplicated CLI representations are excluded. See each attempt's step_definition and independent-step-check.json. Historical ATIF uses its separate stated definition."]
        (folder / "MODEL_BASELINES.md").write_text("\n".join(model_lines) + "\n")
        core = [task / "instruction.md", task / "task.toml", task / "environment/Dockerfile"]
        for directory in (task / "environment/materials", task / "solution", task / "tests"):
            core += [p for p in directory.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix not in (".blend1", ".pyc")]
        package["tasks"][name] = [{"path": p.relative_to(task).as_posix(), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "tracked": p.relative_to(ROOT.parents[1]).as_posix() in tracked} for p in sorted(set(core))]
        oracle = next((r for r in records if r["kind"] == "oracle"), {})
        summary.append({"task": name, "oracle": oracle.get("reward"), "nop": next((r["reward"] for r in records if r["kind"] == "nop"), None), "checks": oracle.get("check_count"), "negative_cases": sum(r["kind"].startswith("negative-") for r in records), "model_attempts": len(attempts), "model_records_valid": gates["models"][0]})
    (ROOT / "current-validation.json").write_text(json.dumps(current_rows, indent=2) + "\n")
    (ROOT / "evaluation/final-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (ROOT / "evaluation/package-inventory.json").write_text(json.dumps(package, indent=2) + "\n")
    print(json.dumps(summary))
