"""Operational priority change: pause final scheduling, cancel duplicate old runs.

Run in the Ubuntu root namespace; keeps all already-running final verifiers
alive. SIGCONT recorded final PID to resume its unchanged scheduling later.
"""
import datetime as dt
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cancel-final", action="store_true", help="Actively cancel the old full batch and its non-booth running verifiers under the new priority")
    parser.add_argument("--cancel-booth-negatives", action="store_true", help="Also cancel obsolete booth negative runs, after preserving its completed Oracle")
    parser.add_argument("--preserve-structure-first", action="store_true", help="Keep the newer structure-first booth scheduler alive")
    parser.add_argument("--grader-sha256", help="Limit cancelled run containers to this snapshotted grade.py hash")
    options = parser.parse_args()
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
            if options.preserve_structure_first and "--structure-first" in args:
                continue
            try:
                os.kill(int(proc.name), signal.SIGTERM if options.cancel_final else signal.SIGSTOP)
                if options.cancel_final:
                    os.kill(int(proc.name), signal.SIGCONT)
            except ProcessLookupError:
                continue
            record["processes"].append({"pid": int(proc.name), "argv": args, "signal": "SIGTERM+SIGCONT" if options.cancel_final else "SIGSTOP", "meaning": "Cancel full batch scheduling under new explicit priority" if options.cancel_final else "Pause scheduling only; child verifiers keep running; resume with SIGCONT"})
        elif args[1].endswith("/record_baselines.py") and "--label" in args and args[args.index("--label") + 1] in ("pre-hardening", "hardened", "hardened-lf-fix"):
            try:
                os.kill(int(proc.name), signal.SIGTERM)
            except ProcessLookupError:
                continue
            record["processes"].append({"pid": int(proc.name), "argv": args, "signal": "SIGTERM", "meaning": "Cancel obsolete duplicate harness under new task priority"})
        (evidence / "priority-change.json").write_text(json.dumps(record, indent=2) + "\n")
    for run_json in ROOT.glob("*/authoring/runs/*/run.json"):
        meta = json.loads(run_json.read_text())
        allowed = ("pre-hardening", "hardened", "hardened-lf-fix", "final") if options.cancel_final else ("pre-hardening", "hardened", "hardened-lf-fix")
        preserve_booth = meta.get("label") == "final" and meta.get("task") == "booth-clearance" and not (options.cancel_booth_negatives and meta.get("kind", "").startswith("negative-"))
        if meta.get("finished_at") or meta.get("label") not in allowed or preserve_booth:
            continue
        if options.grader_sha256 and meta.get("grader_source", {}).get("grade.py", {}).get("sha256") != options.grader_sha256:
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
