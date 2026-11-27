"""Record real Docker Oracle/NOP runs. Run this with WSL Python, not Windows Python.

Examples: python3 record_baselines.py --label pre-hardening
          python3 record_baselines.py --label hardened --tasks toy-car
The grader source is snapshotted before each run; no historical runs are invented.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[1]
TASKS = ["crate-lookdev", "booth-clearance", "folding-chair", "rainroom", "toy-car",
         "spider-gait", "skateboard-prop",
         "drawer-cabinet", "banner-stand"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(path):
    return {str(p.relative_to(path)): {"sha256": sha(p), "bytes": p.stat().st_size}
            for p in sorted(path.rglob("*")) if p.is_file()}


def record(task, kind, label, source_submission=None, grader_source=None):
    task_dir = ROOT / task
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = task_dir / "authoring" / "runs" / (stamp + "-" + label + "-" + kind)
    run_dir.mkdir(parents=True)
    commands = []
    meta = {"task": task, "kind": kind, "label": label, "started_at": stamp,
            "agent": "reference-publisher" if kind == "oracle" else (("adversarial-input-regrade" if kind.startswith("negative-") else "historical-artifact-regrade") if source_submission else "NOP"),
            "model": None, "model_steps": 0, "commands": commands,
            "nop_definition": "fresh task environment; /bin/true only; no solving actions; export original /app/out" if kind == "nop" else None}

    def command(args, name, timeout=1800):
        item = {"argv": [str(a) for a in args], "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}
        commands.append(item)
        with (run_dir / (name + ".stdout.txt")).open("wb") as stdout, (run_dir / (name + ".stderr.txt")).open("wb") as stderr:
            try:
                result = subprocess.run(args, stdout=stdout, stderr=stderr, timeout=timeout)
                item["exit_code"] = result.returncode
            except subprocess.TimeoutExpired:
                item["exit_code"] = 124
                item["timeout_seconds"] = timeout
        item["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        (run_dir / "run.json").write_text(json.dumps(meta, indent=2) + "\n")
        return item["exit_code"]

    tests = run_dir / "grader-source"
    shutil.copytree(grader_source or task_dir / "tests", tests, ignore=shutil.ignore_patterns("__pycache__"))
    meta["grader_source"] = inventory(tests)
    meta["instruction_sha256"] = sha(task_dir / "instruction.md")
    meta["environment_source"] = inventory(task_dir / "environment")
    env_tag, tests_tag = f"cua-qc-{task}-env", f"cua-qc-{task}-tests"
    command(["docker", "version"], "docker-version")
    for tag, name in ((env_tag, "environment-image"), (tests_tag, "verifier-image")):
        command(["docker", "image", "inspect", tag], name)
    suffix = uuid.uuid4().hex[:10]
    agent = "cua-evidence-agent-" + suffix
    verifier = "cua-evidence-verifier-" + suffix
    submission = run_dir / "submission"
    submission.mkdir()
    try:
        if source_submission:
            meta["source_submission"] = str(source_submission)
            meta["model_steps"] = None
            meta["nop_definition"] = None
            shutil.copytree(source_submission, submission, dirs_exist_ok=True)
        else:
            mounts = ["-v", f"{task_dir / 'solution'}:/solution:ro"] if kind == "oracle" else []
            if command(["docker", "create", "--name", agent, "--network", "none", "--cpus", "4", "--memory", "8g", *mounts, env_tag, "sleep", "infinity"], "agent-create"):
                raise RuntimeError("agent container creation failed")
            command(["docker", "start", agent], "agent-start")
            command(["docker", "exec", agent, "blender", "--version"], "blender-version")
            command(["docker", "exec", agent, "ls", "-laR", "/app"], "initial-app")
            command(["docker", "exec", agent, "test", "!", "-e", "/tests"], "test-isolation")
            if kind == "oracle":
                meta["solution_source"] = inventory(task_dir / "solution")
                meta["agent_exit_code"] = command(["docker", "exec", agent, "bash", "/solution/solve.sh", "/app/out"], "agent")
            else:
                meta["agent_exit_code"] = command(["docker", "exec", agent, "/bin/true"], "agent")
            command(["docker", "exec", agent, "ls", "-laR", "/app/out"], "final-output")
            if command(["docker", "cp", agent + ":/app/out/.", str(submission)], "collect-submission"):
                raise RuntimeError("output collection failed")
        meta["submission"] = inventory(submission)
        (run_dir / "verifier").mkdir()
        command(["docker", "create", "--name", verifier, "--network", "none", "--cpus", "4", "--memory", "8g", "-v", f"{tests}:/tests:ro", "-v", f"{submission}:/app/out:ro", "-v", f"{run_dir / 'verifier'}:/logs/verifier", tests_tag, "bash", "/tests/test.sh", "/app/out"], "verifier-create")
        meta["verifier_exit_code"] = command(["docker", "start", "-a", verifier], "verifier", timeout=3600)
        command(["docker", "inspect", verifier], "verifier-state")
        command(["docker", "cp", verifier + ":/tmp/.", str(run_dir / "verifier-tmp")], "collect-verifier-tmp")
        reward = run_dir / "verifier" / "reward.txt"
        meta["reward"] = int(reward.read_text().strip()) if reward.exists() else None
        metrics = run_dir / "verifier" / "metrics.json"
        try:
            parsed_metrics = json.loads(metrics.read_text())
            meta["failed_checks"] = [c["id"] for c in parsed_metrics.get("checks", []) if not c["pass"]]
            meta["outcome"] = "graded" if "checks" in parsed_metrics else "verifier-error"
        except (OSError, ValueError):
            meta["outcome"] = "verifier-error"
        if meta.get("agent_exit_code", 0) != 0:
            meta["outcome"] = "agent-execution-error"
    except Exception as exc:
        meta["error"] = repr(exc)
        meta["outcome"] = "harness-error"
    finally:
        for container in (agent, verifier):
            command(["docker", "rm", "-f", container], "cleanup-" + container)
        meta["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
        (run_dir / "run.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"task": task, "kind": kind, "reward": meta.get("reward"), "run": str(run_dir), "error": meta.get("error")}), flush=True)
    return run_dir


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--tasks", nargs="+", choices=TASKS, default=TASKS)
    parser.add_argument("--kinds", nargs="+", choices=["oracle", "nop"], default=["oracle", "nop"])
    parser.add_argument("--regrade", type=Path, help="Regrade preserved submission; requires exactly one task and ignores --kinds")
    parser.add_argument("--regrade-kind", default="model-regrade", help="Evidence kind for --regrade, e.g. negative-secondary-render")
    parser.add_argument("--jobs", type=int, default=1, choices=range(1, 4), help="Independent tasks to run concurrently (maximum 3)")
    options = parser.parse_args()
    if options.regrade:
        if len(options.tasks) != 1:
            parser.error("--regrade requires exactly one --tasks value")
        record(options.tasks[0], options.regrade_kind, options.label, options.regrade.resolve())
        raise SystemExit(0)
    def run_task(selected_task):
        for selected_kind in options.kinds:
            record(selected_task, selected_kind, options.label)
    with ThreadPoolExecutor(max_workers=options.jobs) as pool:
        list(pool.map(run_task, options.tasks))
