"""Run a blind Codex terminal baseline, preserving raw events and rollout.

This is explicitly NOT a GUI/CUA compliance run. Credentials stay in a private
temporary directory and inside the isolated container, never in recorded argv.
Run through the Ubuntu namespace with its existing private Codex provider.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import tomllib
import uuid

from record_baselines import ROOT, inventory, record

TASK = ROOT / "booth-clearance"
MODEL = "gpt-6.1-sol"
EFFORT = "high"
BINARY = Path("/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex")


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def count_steps(directory):
    tool_calls = assistant_items = 0
    models = set()
    for path in sorted(directory.rglob("*.jsonl")):
        for line in path.read_text().splitlines():
            event = json.loads(line)
            payload = event.get("payload", {})
            if event.get("type") == "turn_context" and payload.get("model"):
                models.add(payload["model"])
            if event.get("type") == "response_item":
                is_call = payload.get("type") in ("function_call", "custom_tool_call")
                tool_calls += is_call
                assistant_items += is_call or (payload.get("type") == "message" and payload.get("role") == "assistant")
    return {"agent_steps": assistant_items, "tool_calls": tool_calls, "reported_models": sorted(models), "step_definition": "agent_steps = raw rollout response_item events whose payload is an assistant message or function_call/custom_tool_call; tool_calls = function_call/custom_tool_call events only. Excludes user/system messages, reasoning-only items, tool results, initialization, Oracle/verifier actions and CLI duplicates."}


def main():
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = TASK / "authoring" / "runs" / (stamp + "-model-codex-terminal")
    run.mkdir(parents=True)
    attempt_id = stamp + "-codex-terminal-gpt-6.1-sol-high"
    source_config = tomllib.loads(Path("/root/.codex/config.toml").read_text())
    provider = source_config["model_provider"]
    provider_config = source_config["model_providers"][provider]
    secret = provider_config.get("experimental_bearer_token", "")
    if not secret:
        raise RuntimeError("Existing private provider has no inline bearer credential; no unapproved credential fallback")
    timeout = int(tomllib.loads((TASK / "task.toml").read_text())["agent"]["timeout_sec"])
    instructions = (TASK / "instruction.md").read_text()
    prompt = """This is an explicitly labeled terminal baseline for a blind benchmark task.
You may use Blender headless Python in this terminal baseline. This does not
count as complying with the original GUI-only interaction requirement.
You only have the supplied task materials and instruction. Do not seek any
reference solution, task repository, grading code, prior runs, or credentials.
Do not read or print authentication/configuration files. Deliver to /app/out.
Use one Blender process at a time, with -t 4; render views sequentially.
The original 7200-second task budget applies. Complete the task autonomously.

Original instruction follows verbatim:

""" + instructions
    (run / "prompt.txt").write_text(prompt)
    shutil.copy2(TASK / "instruction.md", run / "instruction.md")
    effective = {"model_identifier": MODEL, "provider_label": provider, "reasoning_effort": EFFORT, "agent": "Codex terminal baseline", "cli_version": "0.172.0", "timeout_seconds": timeout, "approval": "never (externally isolated Docker)", "sandbox": "danger-full-access inside container only", "gui_compliant": False, "network": "Docker bridge; no host repository, Docker socket, solution/tests/authoring mounts", "credentials": "private minimal provider config; values omitted; never archived", "materials": inventory(TASK / "environment" / "materials"), "instruction_sha256": hashlib.sha256(instructions.encode()).hexdigest()}
    (run / "config.json").write_text(json.dumps(effective, indent=2) + "\n")
    state = {"id": attempt_id, "started_at": now(), "effective_config": effective, "commands": [], "outcome": "running"}
    container = "cua-booth-model-" + uuid.uuid4().hex[:10]

    def scrub(text):
        return text.replace(secret, "[REDACTED_PRIVATE_CREDENTIAL]")

    def command(args, name, input_text=None, command_timeout=1800):
        entry = {"argv": [str(a) for a in args], "started_at": now()}
        state["commands"].append(entry)
        try:
            result = subprocess.run(args, input=input_text, capture_output=True, text=True, timeout=command_timeout)
            code, stdout, stderr = result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired as exc:
            code = 124
            stdout = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = (exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            entry["timeout_seconds"] = command_timeout
        (run / (name + ".stdout.txt")).write_text(scrub(stdout))
        (run / (name + ".stderr.txt")).write_text(scrub(stderr))
        entry.update({"exit_code": code, "finished_at": now()})
        (run / "trial.json").write_text(json.dumps(state, indent=2) + "\n")
        with (run / "trial.log").open("a") as log:
            log.write(json.dumps(entry) + "\n")
        return code

    try:
        with tempfile.TemporaryDirectory(prefix="cua-booth-private-") as private_dir:
            private_config = Path(private_dir) / "config.toml"
            private_config.write_text(f'model = {json.dumps(MODEL)}\nmodel_provider = {json.dumps(provider)}\nmodel_reasoning_effort = "high"\n[model_providers.{provider}]\n' + "\n".join(f'{key} = {json.dumps(value)}' for key, value in provider_config.items()) + "\n")
            private_config.chmod(0o600)
            command(["docker", "image", "inspect", "cua-qc-booth-clearance-env"], "environment-image")
            if command(["docker", "create", "--name", container, "--cpus", "4", "--memory", "8g", "--env", "CODEX_HOME=/run/codex-home", "cua-qc-booth-clearance-env", "sleep", "infinity"], "container-create"):
                raise RuntimeError("model container creation failed")
            command(["docker", "start", container], "container-start")
            command(["docker", "exec", container, "mkdir", "-p", "/run/codex-home", "/app/out"], "prepare-home")
            command(["docker", "cp", str(BINARY), container + ":/usr/local/bin/codex"], "install-codex-binary")
            command(["docker", "cp", str(private_config), container + ":/run/codex-home/config.toml"], "install-private-config")
            command(["docker", "cp", str(TASK / "instruction.md"), container + ":/app/instruction.md"], "supply-instruction")
            command(["docker", "exec", container, "ls", "-laR", "/app"], "initial-app")
            command(["docker", "exec", container, "codex", "--version"], "codex-version")
            state["agent_started_at"] = now()
            state["agent_exit_code"] = command(["docker", "exec", "-i", container, "codex", "exec", "--json", "--color", "never", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check", "-C", "/app", "-m", MODEL, "-c", 'model_reasoning_effort="high"', "-o", "/app/model-final.txt", "-"], "agent-events", prompt, timeout)
            state["agent_finished_at"] = now()
            if state["agent_exit_code"] == 124:
                command(["docker", "stop", "--time", "5", container], "stop-timed-out-agent")
            private_rollout = Path(private_dir) / "raw-rollout"
            command(["docker", "cp", container + ":/run/codex-home/sessions", str(private_rollout)], "collect-rollout")
            for path in private_rollout.rglob("*.jsonl"):
                target = run / "raw-rollout" / path.relative_to(private_rollout)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(scrub(path.read_text()))
            command(["docker", "cp", container + ":/app/out", str(run / "submission")], "collect-submission")
            private_message = Path(private_dir) / "model-final.txt"
            command(["docker", "cp", container + ":/app/model-final.txt", str(private_message)], "collect-model-final")
            if private_message.exists():
                (run / "model-final.txt").write_text(scrub(private_message.read_text()))
            state["steps"] = count_steps(run / "raw-rollout")
            (run / "step-counts.json").write_text(json.dumps(state["steps"], indent=2) + "\n")
            if (run / "submission").is_dir():
                grading = record("booth-clearance", "model-regrade", "final", run / "submission")
                grade = json.loads((grading / "run.json").read_text())
                state.update({"grading_run": str(grading.relative_to(ROOT)), "reward": grade.get("reward"), "grading_outcome": grade.get("outcome")})
            state["outcome"] = "agent-timeout" if state["agent_exit_code"] == 124 else ("agent-error" if state["agent_exit_code"] else ("terminal-artifact-pass-not-gui-compliant" if state.get("reward") == 1 else "task-failure"))
    except Exception as exc:
        state["outcome"] = "harness-error"
        state["error"] = scrub(repr(exc))
    finally:
        command(["docker", "rm", "-f", container], "container-cleanup")
        state["finished_at"] = now()
        (run / "trial.json").write_text(json.dumps(state, indent=2) + "\n")
        index_path = TASK / "authoring" / "model-attempts.json"
        index = json.loads(index_path.read_text())
        index["scope"] = "Recovered historical attempts plus newly recorded blind attempts; Oracle/NOP are excluded."
        index.pop("absence_note", None)
        steps = state.get("steps", {})
        index["attempts"] = [item for item in index.get("attempts", []) if item["id"] != attempt_id]
        index["attempts"].append({"id": attempt_id, "path": str(run.relative_to(ROOT.parents[1])), "model_identifier": MODEL, "agent": "codex-terminal", "gui_compliant": False, "effective_config": effective, "outcome": state["outcome"], "reward": state.get("reward"), "raw_rollout_path": str((run / "raw-rollout").relative_to(ROOT.parents[1])), "trajectory_format": "Codex raw JSONL plus CLI --json events", "step_definition": steps.get("step_definition"), "agent_steps": steps.get("agent_steps"), "tool_calls": steps.get("tool_calls"), "grading_run": state.get("grading_run"), "cli_exit_code": state.get("agent_exit_code")})
        index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(json.dumps({"run": str(run), "outcome": state["outcome"], "reward": state.get("reward"), "steps": state.get("steps")}), flush=True)


if __name__ == "__main__":
    main()
