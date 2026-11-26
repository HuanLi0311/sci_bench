"""Independently check a completed raw Codex trial and extract original images."""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path

from record_baselines import ROOT, inventory


def images(value, pointer=""):
    if isinstance(value, dict):
        if value.get("type") == "input_image" and isinstance(value.get("image_url"), str) and value["image_url"].startswith("data:image/"):
            yield pointer, value["image_url"]
        for key, child in value.items():
            yield from images(child, pointer + "/" + key)
    elif isinstance(value, list):
        for number, child in enumerate(value):
            yield from images(child, pointer + "/" + str(number))


def audit(run):
    state = json.loads((run / "trial.json").read_text())
    if not state.get("finished_at"):
        raise ValueError("Trial is still running")
    calls, messages, ids, models = [], [], [], set()
    observations = []
    raw_hashes = {}
    for path in sorted((run / "raw-rollout").rglob("*.jsonl")):
        raw_hashes[str(path.relative_to(run))] = hashlib.sha256(path.read_bytes()).hexdigest()
        for line_number, line in enumerate(path.read_text().splitlines(), 1):
            event = json.loads(line)
            payload = event.get("payload", {})
            if event.get("type") == "turn_context" and payload.get("model"):
                models.add(payload["model"])
            if event.get("type") == "response_item":
                if payload.get("type") in {"function_call", "custom_tool_call"}:
                    calls.append(payload.get("name", "unknown"))
                    if payload.get("call_id"):
                        ids.append(payload["call_id"])
                elif payload.get("type") == "message" and payload.get("role") == "assistant":
                    messages.append((str(path), line_number))
            for pointer, uri in images(event):
                header, encoded = uri.split(",", 1)
                content = base64.b64decode(encoded, validate=True)
                mime = header.split(";", 1)[0][5:]
                extension = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "image")
                filename = f"observation_{len(observations)+1:03}.{extension}"
                folder = run / "observations"
                folder.mkdir(exist_ok=True)
                (folder / filename).write_bytes(content)
                observations.append({"file": filename, "source_session": str(path.relative_to(run)), "line": line_number, "json_pointer": pointer, "mime": mime, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    actual = {"agent_steps": len(messages) + len(calls), "tool_calls": len(calls), "assistant_messages": len(messages), "tool_names": dict(Counter(calls)), "reported_models": sorted(models), "duplicate_call_ids": [key for key, count in Counter(ids).items() if count > 1], "raw_session_hashes": raw_hashes}
    recorded = json.loads((run / "step-counts.json").read_text())
    actual["counts_match_recorded"] = all(actual[key] == recorded[key] for key in ("agent_steps", "tool_calls"))
    actual["definition"] = recorded["step_definition"]
    if not actual["counts_match_recorded"] or actual["duplicate_call_ids"] or not raw_hashes:
        raise ValueError("Independent raw step check failed")
    (run / "independent-step-check.json").write_text(json.dumps(actual, indent=2) + "\n")
    if observations:
        (run / "observations/index.json").write_text(json.dumps(observations, indent=2) + "\n")
        lines = ["# Original model image observations", "", "Decoded byte-for-byte from the unchanged raw session data URIs. Each event line and JSON pointer is recorded in index.json.", "", "| Image | Source session line | SHA-256 |", "|---|---|---|"]
        for item in observations:
            lines.append(f"| [{item['file']}]({item['file']}) | {item['source_session']}:{item['line']} | {item['sha256']} |")
        (run / "observations/README.md").write_text("\n".join(lines) + "\n")
    config = json.loads((run / "config.json").read_text())
    copied_materials = inventory(run / "input-materials")
    material_ok = copied_materials == config["materials"]
    submission_ok = inventory(run / "submission") == state.get("submission")
    isolation = json.loads((run / "container-isolation.json").read_text())
    initial = json.loads((run / "input-isolation.stdout.txt").read_text())
    inputs = {"materials_match_config": material_ok, "instruction_sha256": hashlib.sha256((run / "instruction.md").read_bytes()).hexdigest(), "material_files": [{"agent_path": "/app/materials/" + name, "stored_path": "input-materials/" + name, **value} for name, value in copied_materials.items()], "no_mounts": isolation["mounts"] == [], "forbidden_paths_absent": not any(initial["forbidden_paths"].values()), "initial_output_empty": initial["output_files"] == [], "submission_unchanged": submission_ok}
    if not all(inputs[key] for key in ("materials_match_config", "no_mounts", "forbidden_paths_absent", "initial_output_empty", "submission_unchanged")) or inputs["instruction_sha256"] != config["instruction_sha256"]:
        raise ValueError("Input/isolation/submission audit failed")
    (run / "input-reconstruction.json").write_text(json.dumps(inputs, indent=2) + "\n")
    cli = [json.loads(line) for line in (run / "agent-events.stdout.txt").read_text().splitlines() if line.startswith("{")]
    executions = [event["item"] for event in cli if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "command_execution"]
    review = {"classification": state["outcome"], "cli_exit_code": state.get("agent_exit_code"), "terminal_error": state.get("terminal_error"), "artifact_reward": state.get("reward"), "grading_run": state.get("grading_run"), "gui_compliant": False, "agent_steps": actual["agent_steps"], "tool_requests": actual["tool_calls"], "cli_completed_commands": len(executions), "cli_commands_exit_zero": sum(item.get("exit_code") == 0 for item in executions), "cli_commands_exit_nonzero": sum(item.get("exit_code") not in (None, 0) for item in executions), "image_observations": len(observations), "note": "Execution outcome, artifact score and GUI compliance are separate. API/setup failures are not model capability failures; tool requests are not successful commands or GUI clicks."}
    (run / "outcome-review.json").write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps({"run": str(run), **review}))
    return review


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    audit(args.run.resolve())
