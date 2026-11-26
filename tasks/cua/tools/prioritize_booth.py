"""Operational priority change: pause final scheduling, cancel duplicate old runs.

Run in the Ubuntu root namespace; keeps all already-running final verifiers
alive. SIGCONT recorded final PID to resume its unchanged scheduling later.
"""
import datetime as dt
import json
import os
from pathlib import Path
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


if __name__ == "__main__":
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "evaluation" / (stamp + "-booth-priority")
    evidence.mkdir(parents=True)
    record = {"time_utc": now(), "reason": "User requested booth-clearance first; no WSL restart; final verifier containers preserved", "processes": [], "cancelled_runs": []}
    (evidence / "priority-change.json").write_text(json.dumps(record, indent=2) + "\n")
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            argv = (proc / "cmdline").read_bytes().split(b"\0")
            args = [a.decode(errors="replace") for a in argv if a]
        except OSError:
            continue
        if len(args) < 2 or not args[0].endswith("python3"):
            continue
        if args[1].endswith("/record_final.py"):
            try:
                os.kill(int(proc.name), signal.SIGSTOP)
            except ProcessLookupError:
                continue
            record["processes"].append({"pid": int(proc.name), "argv": args, "signal": "SIGSTOP", "meaning": "Pause scheduling only; child verifiers keep running; resume with SIGCONT"})
        elif args[1].endswith("/record_baselines.py") and "--label" in args and args[args.index("--label") + 1] in ("pre-hardening", "hardened", "hardened-lf-fix"):
            try:
                os.kill(int(proc.name), signal.SIGTERM)
            except ProcessLookupError:
                continue
            record["processes"].append({"pid": int(proc.name), "argv": args, "signal": "SIGTERM", "meaning": "Cancel obsolete duplicate harness under new task priority"})
        (evidence / "priority-change.json").write_text(json.dumps(record, indent=2) + "\n")
    for run_json in ROOT.glob("*/authoring/runs/*/run.json"):
        meta = json.loads(run_json.read_text())
        if meta.get("finished_at") or meta.get("label") not in ("pre-hardening", "hardened", "hardened-lf-fix"):
            continue
        run = run_json.parent
        containers = []
        for item in meta["commands"]:
            args = item["argv"]
            if args[:2] == ["docker", "create"] and "--name" in args:
                containers.append(args[args.index("--name") + 1])
        cancellation = {"time_utc": now(), "reason": record["reason"], "containers": []}
        for name in containers:
            inspect = subprocess.run(["docker", "inspect", name], capture_output=True, text=True)
            (run / (name + ".before-cancel.json")).write_text(inspect.stdout)
            if inspect.returncode:
                continue
            status = subprocess.run(["docker", "stop", "--time", "5", name], capture_output=True, text=True)
            cancellation["containers"].append({"name": name, "stop_exit_code": status.returncode, "stdout": status.stdout, "stderr": status.stderr})
            if "verifier" in name:
                result = subprocess.run(["docker", "cp", name + ":/tmp/.", str(run / "verifier-tmp")], capture_output=True, text=True)
                cancellation["containers"][-1]["collect_tmp_exit_code"] = result.returncode
            after = subprocess.run(["docker", "inspect", name], capture_output=True, text=True)
            (run / (name + ".after-cancel.json")).write_text(after.stdout)
            subprocess.run(["docker", "rm", name], capture_output=True)
        (run / "cancellation.json").write_text(json.dumps(cancellation, indent=2) + "\n")
        meta["outcome"] = "cancelled-by-priority-change"
        meta["finished_at"] = now()
        meta["cancellation"] = "cancellation.json"
        run_json.write_text(json.dumps(meta, indent=2) + "\n")
        record["cancelled_runs"].append(str(run.relative_to(ROOT)))
    (evidence / "priority-change.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2), flush=True)
