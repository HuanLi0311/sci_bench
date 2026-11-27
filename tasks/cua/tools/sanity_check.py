"""QC runner for the CUA task pack.

    python3 tools/sanity_check.py [task ...]

Runs every check in SANITY_LIST.md against each task under tasks/cua/ and
prints a table. Exits non-zero if any check fails. Docker must be available;
runs inside WSL (`wsl.exe -e bash -lc 'python3 ...'`).
"""
import json
import hashlib
from pathlib import Path
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEGATIVE_CASES = {
    "booth-clearance": {"secondary-render-substitution", "booth-moved-entrance-marker", "booth-product-scaled",
                        "booth-product-floating", "booth-unused-brand-slot", "booth-closed-opening",
                        "booth-camera-away", "booth-missing-secondary-color", "booth-hidden-secondary-color"},
    "crate-lookdev": {"secondary-render-substitution", "crate-disconnected-maps"},
    "folding-chair": {"secondary-render-substitution", "chair-common-root-collision", "chair-shared-hinge-collision"},
    "rainroom": {"secondary-render-substitution", "rain-unused-metal-slot",
                 "rain-linked-metal-default", "rain-disconnected-metal-shader"},
    "toy-car": {"secondary-render-substitution", "toy-wrong-wheel-parent"},
    "spider-gait": {"secondary-render-substitution", "spider-broken-skin",
                    "spider-floating-feet", "spider-static-pose"},
    "skateboard-prop": {"secondary-render-substitution", "deck-single-ply",
                        "deck-graphic-unlinked", "truck-dielectric"},
}

REQUIRED = [
    "task.toml", "instruction.md", "README.md",
    "environment/Dockerfile", "tests/Dockerfile", "tests/test.sh",
    "tests/grade.py", "tests/check_scene.py", "tests/rerender.py",
    "solution/solve.sh",
    "authoring/provenance/SOURCES.md", "authoring/calibration/results.md",
]


def sh(cmd, timeout=1800, cwd=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                          timeout=timeout, cwd=cwd)


def check_layout(t):
    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(t, f))]
    return (not missing), f"missing={missing}" if missing else "ok"


def toml_get(text, section, key):
    m = re.search(rf"^\[{re.escape(section)}\]\s*$(.*?)(?=^\[|\Z)", text,
                  re.M | re.S)
    if not m:
        return None
    km = re.search(rf'^{re.escape(key)}\s*=\s*(.+)$', m.group(1), re.M)
    if not km:
        return None
    return km.group(1).strip().strip('"')


def check_toml(t, name):
    p = os.path.join(t, "task.toml")
    if not os.path.exists(p):
        return False, "no task.toml"
    text = open(p, encoding="utf-8").read()
    problems = []
    if 'schema_version = "1.4"' not in text:
        problems.append("schema")
    if f"terminal-bench-science/{name}" not in text:
        problems.append("name")
    for sec, key in (("verifier", "environment_mode"), ("agent", "timeout_sec"),
                     ("verifier", "timeout_sec"), ("task", "description"),
                     ("task", "authors"), ("task", "keywords")):
        if toml_get(text, sec, key) is None:
            problems.append(f"{sec}.{key}")
    if toml_get(text, "verifier", "environment_mode") != "separate":
        problems.append("mode!=separate")
    return (not problems), problems or "ok"


def check_suffix(t):
    p = os.path.join(t, "instruction.md")
    text = open(p, encoding="utf-8").read() if os.path.exists(p) else ""
    m = re.search(r"You have (\d+) seconds to complete this task\.\s*\Z", text)
    if not m:
        return False, "no suffix"
    n = int(m.group(1))
    agent = toml_get(open(os.path.join(t, "task.toml"), encoding="utf-8").read(), "agent", "timeout_sec")
    want = int(float(agent)) if agent else None
    return (n == want), f"{n} vs {want}"


def check_materials(t):
    mdir = os.path.join(t, "environment", "materials")
    if not os.path.isdir(mdir):
        return False, "no materials"
    files = [f for _, _, fs in os.walk(mdir) for f in fs]
    return (len(files) >= 2 and os.path.exists(os.path.join(mdir, "LICENSE.txt")),
            f"{len(files)} files")


def image_exists(tag):
    return sh(f"docker image inspect {tag} >/dev/null 2>&1").returncode == 0


def build(t, kind, tag):
    ctx = os.path.join(t, kind)
    r = sh(f"docker build -q -t {tag} {ctx}", timeout=3600)
    return r.returncode == 0, (r.stderr or "")[-300:]


def check_isolation(tag):
    r = sh(f"docker run --rm {tag} bash -lc "
           "'test -d /app/solution && echo LEAK; test -d /app/tests && echo LEAK; "
           "ls /app/out 2>/dev/null | wc -l'", timeout=300)
    out = (r.stdout or "").strip().splitlines()
    leak = any("LEAK" in line for line in out)
    empty = out and out[-1].strip() == "0"
    return (not leak and empty), f"leak={leak} out_files={out[-1] if out else '?'}"


def check_recorded_run(t, kind):
    """A prose claim or a negative mutation is never evidence of Oracle/NOP."""
    task = Path(t)
    current = {p.relative_to(task / "tests").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (task / "tests").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    candidates = sorted((task / "authoring/runs").glob("*-final-" + kind), reverse=True)
    problems = []
    for run in candidates:
        try:
            meta = json.loads((run / "run.json").read_text(encoding="utf-8"))
            metrics = json.loads((run / "verifier/metrics.json").read_text(encoding="utf-8"))
            reward = int((run / "verifier/reward.txt").read_text(encoding="utf-8").strip())
            recorded = {name: entry["sha256"] for name, entry in meta["grader_source"].items()}
            if current != recorded:
                raise ValueError("grader differs from current source")
            for name, entry in meta["grader_source"].items():
                if hashlib.sha256((run / "grader-source" / name).read_bytes()).hexdigest() != entry["sha256"]:
                    raise ValueError("snapshot hash mismatch")
            if reward != metrics["reward"] or reward != meta["reward"]:
                raise ValueError("reward disagreement")
            if any(c["id"] == "R_verifier_error" for c in metrics.get("checks", [])):
                raise ValueError("verifier exception is not a valid baseline score")
            if not meta.get("finished_at") or meta.get("error") or meta.get("agent_exit_code") != 0:
                raise ValueError("agent did not complete cleanly")
            if kind == "oracle":
                if reward != 1 or meta.get("verifier_exit_code") != 0 or not metrics["checks"] or not all(c["pass"] for c in metrics["checks"]):
                    raise ValueError("Oracle not all-pass")
                for name, entry in meta["solution_source"].items():
                    if hashlib.sha256((task / "solution" / name).read_bytes()).hexdigest() != entry["sha256"]:
                        raise ValueError("reference differs from measured input")
            else:
                if reward != 0 or meta.get("model_steps") != 0 or meta.get("submission") != {}:
                    raise ValueError("NOP must take zero solving steps and export original empty output")
                if not any(c["argv"][-1:] == ["/bin/true"] and c["exit_code"] == 0 for c in meta["commands"]):
                    raise ValueError("NOP no-op execution absent")
            if not (run / "verifier.stdout.txt").exists() or not (run / "agent.stdout.txt").exists():
                raise ValueError("raw logs missing")
            return True, str(run.name)
        except Exception as exc:
            problems.append(f"{run.name}: {exc}")
    return False, "; ".join(problems) or f"no final {kind} evidence"


def check_oracle(t, tests_tag):
    return check_recorded_run(t, "oracle")


def check_model_records(t):
    def repo_path(value):
        path = Path(value)
        return path if path.is_absolute() else Path(ROOT).parents[1] / path

    try:
        record = json.loads((Path(t) / "authoring/model-attempts.json").read_text(encoding="utf-8"))
        ids = [a["id"] for a in record["attempts"]]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate model attempt IDs")
        for attempt in record["attempts"]:
            path = repo_path(attempt["path"])
            if not (path / "config.json").exists() or not (path / "trial.log").exists():
                raise ValueError("attempt raw config/log missing")
            if attempt.get("outcome") == "running":
                raise ValueError(f"model attempt {attempt['id']} is still running")
            if attempt.get("trajectory_format", "").startswith("Codex raw JSONL"):
                raw = repo_path(attempt["raw_rollout_path"])
                files = sorted(raw.rglob("*.jsonl"))
                if not files or not (path / "agent-events.stdout.txt").exists():
                    raise ValueError("complete raw Codex sessions/CLI events missing")
                agent_steps = tool_calls = 0
                for file in files:
                    for line in file.read_text(encoding="utf-8").splitlines():
                        event = json.loads(line)
                        payload = event.get("payload", {})
                        if event.get("type") != "response_item":
                            continue
                        call = payload.get("type") in ("function_call", "custom_tool_call")
                        tool_calls += int(call)
                        agent_steps += int(call or (payload.get("type") == "message" and payload.get("role") == "assistant"))
                if agent_steps != attempt["agent_steps"] or tool_calls != attempt["tool_calls"]:
                    raise ValueError("Codex step count differs from all raw sessions")
                if attempt.get("reward") == 1 and not attempt.get("grading_run"):
                    raise ValueError("model success has no grading evidence")
            elif attempt.get("trajectory_present"):
                trajectory = json.loads((path / "agent/trajectory.json").read_text(encoding="utf-8"))
                agent = [step for step in trajectory["steps"] if step.get("source") == "agent"]
                if len(agent) != attempt["agent_steps"] or sum(len(step.get("tool_calls", [])) for step in agent) != attempt["tool_calls"]:
                    raise ValueError("ATIF step count differs from raw trajectory")
        return True, f"{len(record['attempts'])} recorded attempts; complete raw trajectories checked where inference occurred"
    except Exception as exc:
        return False, str(exc)


def check_deliverables(t):
    """Only files listed under 'What to deliver' count as deliverables."""
    sol = os.path.join(t, "solution")
    text = open(os.path.join(t, "instruction.md"), encoding="utf-8").read()
    part = text.split("What to deliver", 1)[-1].split("##", 1)[0]
    names = set(re.findall(r"`([a-z0-9_]+\.(?:png|blend|json))`", part))
    missing = [n for n in names if not os.path.exists(os.path.join(sol, n))]
    return (not missing), (f"missing={missing}" if missing else f"{len(names)} files")


def check_anticheat(t):
    g = open(os.path.join(t, "tests", "grade.py"), encoding="utf-8").read()
    return ('"critical"' in g, "critical check present" if '"critical"' in g
            else "no critical check")


def check_negative(t):
    task = Path(t)
    current = {p.relative_to(task / "tests").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (task / "tests").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    prepared = {p.name.split("-mutation-", 1)[1]
                for p in (task / "authoring/runs").glob("*-mutation-*") if (p / "submission").is_dir()}
    required = {"negative-" + name for name in NEGATIVE_CASES[task.name] | prepared}
    latest = {}
    for path in sorted((task / "authoring/runs").glob("*-final-negative-*/run.json")):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
            recorded = {name: item["sha256"] for name, item in meta["grader_source"].items()}
            if recorded == current:
                latest[meta["kind"]] = (path, meta)
        except (OSError, ValueError, KeyError):
            pass
    missing = required - latest.keys()
    if not required or missing:
        return False, f"missing current-source negative cases: {sorted(missing or ['all'])}"
    for kind, (path, meta) in latest.items():
        try:
            metrics = json.loads((path.parent / "verifier/metrics.json").read_text(encoding="utf-8"))
            reward = int((path.parent / "verifier/reward.txt").read_text(encoding="utf-8"))
            if not meta.get("finished_at") or meta.get("outcome") != "graded":
                raise ValueError("grading incomplete/errored")
            if reward != 0 or meta.get("reward") != 0 or metrics["reward"] != 0:
                raise ValueError("negative submission unexpectedly accepted")
            if any("timed out" in str(c.get("detail", "")) for c in metrics["checks"]):
                raise ValueError("timeout is not a rejected negative")
            decisive = {
                "negative-secondary-render-substitution": "R_render_structure",
                "negative-booth-moved-entrance-marker": "R05_entrance_clearance",
                "negative-booth-product-scaled": "R_furniture_product_sizes",
                "negative-booth-product-floating": "R_product_support",
                "negative-booth-unused-brand-slot": "R08_brand_colour",
                "negative-booth-closed-opening": "R_actual_entrance_opening",
                "negative-booth-camera-away": "R07_visibility",
                "negative-booth-missing-secondary-color": "R_secondary_brand_colour",
                "negative-booth-hidden-secondary-color": "R_secondary_brand_colour",
                "negative-crate-disconnected-maps": "R07_pbr_maps",
                "negative-chair-common-root-collision": "R07_no_interpenetration",
                "negative-chair-shared-hinge-collision": "R07_no_interpenetration",
                "negative-rain-unused-metal-slot": "R09_materials",
                "negative-rain-linked-metal-default": "R09_materials",
                "negative-rain-disconnected-metal-shader": "R09_materials",
                "negative-toy-wrong-wheel-parent": "R07_steering",
                "negative-spider-broken-skin": "R03_skinning",
                "negative-spider-floating-feet": "R07_support",
                "negative-spider-static-pose": "R17_phase_anticheat",
                "negative-deck-single-ply": "R04_plies",
                "negative-deck-graphic-unlinked": "R05_graphic_uv",
                "negative-truck-dielectric": "R07_materials",
            }
            failed = {c["id"] for c in metrics["checks"] if not c["pass"]}
            if not any(c["id"] == "R01_open" and c["pass"] for c in metrics["checks"]):
                raise ValueError("valid-scene mutation failed extraction; rejection is not attributable to the intended check")
            if "R_verifier_error" in failed or decisive.get(kind) not in failed:
                raise ValueError("the intended rubric check did not reject the mutation")
        except (OSError, ValueError, KeyError) as exc:
            return False, f"{kind}: {exc}"
    return True, f"all {len(required)} prepared negative cases rejected by the current verifier"


def check_manifest(t):
    p = os.path.join(t, "solution", "manifest.json")
    if not os.path.exists(p):
        return False, "no manifest"
    man = json.load(open(p, encoding="utf-8"))
    assets = man.get("assets", [])
    ok = bool(assets) and all(a.get("source") and a.get("license") for a in assets)
    return ok, f"{len(assets)} assets"


def main():
    tasks = sys.argv[1:]
    base = os.path.join(ROOT)
    if not tasks:
        tasks = sorted(d for d in os.listdir(base)
                       if os.path.isdir(os.path.join(base, d))
                       and os.path.exists(os.path.join(base, d, "task.toml")))
    rows = []
    for name in tasks:
        t = os.path.join(base, name)
        env_tag = f"cua-qc-{name}-env"
        tests_tag = f"cua-qc-{name}-tests"
        results = {}
        results["1 layout"] = check_layout(t)
        results["2 task.toml"] = check_toml(t, name)
        results["3 suffix"] = check_suffix(t)
        results["4 materials"] = check_materials(t)
        ok, msg = build(t, "environment", env_tag) if not image_exists(env_tag) else (True, "cached")
        results["5 env image"] = (ok, msg)
        results["5b isolation"] = check_isolation(env_tag) if ok else (False, "no image")
        ok_t, msg_t = build(t, "tests", tests_tag)
        results["6 tests image"] = (ok_t, msg_t)
        results["7 oracle"] = check_oracle(t, tests_tag) if ok_t else (False, "no image")
        results["7b true NOP"] = check_recorded_run(t, "nop")
        results["7c model records"] = check_model_records(t)
        results["8 deliverables"] = check_deliverables(t)
        results["9 anti-cheat"] = check_anticheat(t)
        results["10 negative"] = check_negative(t)
        results["11 licences"] = check_manifest(t)
        rows.append((name, results))

    width = max(len(k) for _, r in rows for k in r)
    names = [n for n, _ in rows]
    header = "check".ljust(width + 2) + "  ".join(n[:16].ljust(16) for n in names)
    print(header)
    print("-" * len(header))
    failures = 0
    for key in rows[0][1]:
        cells = []
        for _, r in rows:
            ok, msg = r[key]
            cells.append(("PASS " if ok else "FAIL ").ljust(16))
            if not ok:
                failures += 1
        print(key.ljust(width + 2) + "  ".join(cells))
    print()
    for name, r in rows:
        for key, (ok, msg) in r.items():
            if not ok:
                print(f"{name} / {key}: {msg}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
