# CUA verification evidence

This pack contains five tasks. Each task keeps its instruction in `instruction.md`, agent-visible assets in `environment/materials/`, the reference deliverables in `solution/`, and the independently executed verifier in `tests/`.

The captured execution index is [RUNS.md](RUNS.md), with machine-readable records in [run-index.json](run-index.json). `tools/summarize_runs.py` regenerates both from actual `run.json` files. The final batch and the exact verifier snapshots are under `evaluation/`. Scores in old calibration notes are historical authoring claims; the newly captured records do not reconstruct missing historical logs or prove that an old unrecorded execution occurred.

## Oracle and NOP protocol

Each Oracle starts a fresh task environment, mounts the reference solution read-only, executes its real `solve.sh`, exports `/app/out`, and grades that exported submission in a separate container. Each NOP starts the same fresh task image, executes only `/bin/true`, and exports the untouched `/app/out`. It performs zero model calls and zero solving steps. A deleted marker, broken hinge, modified texture, or substituted image is a negative test, never a NOP.

Every captured run contains:

- `run.json`: exact commands, UTC times, exit codes, image metadata, instruction/source/submission SHA-256 hashes and outcome.
- `agent.stdout.txt` / `agent.stderr.txt`: raw reference-publisher or NOP execution output.
- `verifier.stdout.txt` / `verifier.stderr.txt` and `verifier/stderr.log`: raw verifier output and errors.
- `verifier/metrics.json` and `verifier/reward.txt`: per-check results and binary reward. A crash can leave invalid/missing metrics; such a record is retained as an execution failure and cannot validate an Oracle or NOP.
- `grader-source/`: the exact verifier source used. Final runs use a single frozen batch snapshot; development runs may use different source versions.
- `submission/`: the actual graded files. A genuine NOP submission is empty. Blender subprocess logs and independently rendered images are retained for the final verifier.

Docker containers use `--network none`. This is a direct Docker validation of the task's verifier, not a successful Harbor `no-network` run. The historical Harbor error is preserved instead of being silently rewritten. Cached local Blender images and their image IDs are recorded in each run; their rebuild recipe is [crate-lookdev/authoring/base-image.md](crate-lookdev/authoring/base-image.md).

## Model attempts and step counts

Every task has `authoring/model-attempts.json`. The recoverable historical archive contains 14 `crate-lookdev` trial directories from WSL `/tmp/harbor-jobs`, including their configuration, trial/job logs, result or exception records, and submitted artifacts where available. [The historical inventory](crate-lookdev/authoring/runs/historical/inventory.json) records original file sizes and SHA-256 hashes. The other four tasks have no historical model attempt in the searched local archives; they are explicitly marked unmeasured.

Thirteen attempts have no recovered model inference trajectory: setup timeout, installation error, cancellation, missing model configuration, or incomplete execution. Their full available execution records are retained. No synthetic model messages, model versions, rewards, or zero-step "successful trajectories" have been created to fill those gaps.

One attempt, `crate-lookdev__dMX45qL`, includes the complete original Codex JSONL rollout, `codex.txt`, and ATIF trajectory. It records `gpt-6.1-sol`, `codex-cli 0.172.0`, reasoning effort `high`, approval policy `never`, sandbox `danger-full-access`, and working directory `/app`. The provider did not record an immutable model snapshot identifier. This is a Codex terminal agent using `exec`; it is not a `computer-1` GUI-only trial and cannot establish a CUA model pass rate. Its original verifier failed because the local Harbor backend rejected `network_mode='no-network'`; the preserved submission is graded separately with the final verifier, without modifying the historical result.

The step accounting is reproducible from the raw ATIF file:

| Metric | Count | Definition |
|---|---:|---|
| All ATIF steps | 73 | Length of `steps`, including system and user messages |
| Agent steps | 67 | Steps whose `source` equals `agent`, including messages and tool requests |
| Tool calls | 66 | Sum of `len(step.tool_calls)` over agent steps |
| System / user steps | 4 / 2 | Counted separately; excluded from agent-step count |

These are transcript statistics for a completed agent execution, not evidence that it solved the task. The separate final regrade determines success or failure. No GUI click count is inferred from shell commands, and no successful model trajectory is claimed without a passing result.

## Verifier changes and tested boundaries

The verifier now checks every delivered view/state against an independent RGB re-render from the submitted scene. It disables the compositor and sequencer for this check, requires the specified cameras, and retains each view's minimum per-channel SSIM (threshold 0.90). A real constant-colour top-view substitution still scored 1 under that check (SSIM 0.918), so the verifier also requires relative RGB gradient error <= 0.60 after a 2-pixel Gaussian blur. A constant image has gradient error 1 regardless of uniform-background area. Captured valid render pairs measured 0.093?0.459; the replay test and input hashes are in `evaluation/gradient-regression.json`. Full final Docker reruns validate the combined checks. Existing physical/light perturbation checks remain in place.

Each grading invocation uses an isolated work directory and checks Blender's exit status with automatic embedded Python execution disabled. Unreadable scenes, malformed images and unexpected exceptions fail closed with a structured failure record. Source and subprocess logs make failed extraction distinguishable from a solved task.

Additional checks reject empty/hidden name placeholders for physical geometry (auxiliary Empty entrance markers are supported), count evaluated geometry for modifier-dependent polygon budgets, validate rainroom object positions, constrain the booth entrance marker and include the shell/other products in visibility rays. Chair collision sampling always covers frames 0–60 in steps of two, and an arbitrary shared root no longer exempts mesh pairs from collision checks. Car spin uses a nontrivial 90-degree rotation and validates the front steering hierarchy. Crate PBR checks require connected, packed 2K maps reaching the active material output; image counts and image brightness no longer substitute for roughness/base-color wiring or metallic values.

Negative tests include a substituted view for each task, disconnected crate PBR maps, intersecting chair meshes under an ordinary common root, a moved booth marker, and an invalid car steering parent. Their actual outcomes and raw evidence belong in the final batch index. These finite checks do not certify subjective artistic quality or establish a measured frontier-model pass rate.

## Reproduction

Run from WSL, with the existing Docker images available:

```bash
python3 tasks/cua/tools/record_final.py --jobs 3
python3 tasks/cua/tools/summarize_runs.py
python3 tasks/cua/tools/sanity_check.py
```

The sanity check requires actual final Oracle and NOP records whose source hashes match the current verifier. It also checks rewards, per-check results, reference input hashes, untouched NOP output, original no-op command, and model inventory; prose containing "reward 1" cannot satisfy these gates.

New isolated terminal-model trials for booth-clearance are recorded in its model-attempts index, separately from the historical crate archive. Runtime smoke calls are diagnostic checks, not task successes. A terminal trial whose tools cannot launch is an infrastructure failure even when its empty output receives reward 0.

Booth brand-colour grading uses sRGB values converted from Blender linear shader inputs. The original reference used the wrong transfer convention; its scene/renders/input photos are corrected with unchanged geometry and a preserved backup. See [the colour-space audit](booth-clearance/authoring/calibration/COLOR_SPACE.md). Auxiliary Empty markers are supported; entrance geometry and camera-frame visibility are checked independently.
