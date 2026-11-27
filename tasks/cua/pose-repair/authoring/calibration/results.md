# Final sanity record

Date: 2026-11-27 (Asia/Shanghai). Task: `pose-repair`. Operational source SHA-256:
`0c521e24006a04cefdbd672bf6a3a74b3d824629c4a972b99f393a1433c909b4`. Per-file source hashes are in `source-digest.json`;
all final grader snapshots and commands are retained under the indexed runs.

Sanity functional matrix: PASS. Scope: direct Docker, not a Harbor scheduler
trial; no model inference, GUI-model success claim or difficulty calibration.
Every candidate trial ran with 4 CPUs, 8 GiB container memory, 256 PID limit,
and a no-network verifier. Only declared output plus trusted sidecar evidence
(pose task) were passed. No actor source checkout was mounted in the verifier.
The actor/solution mount used for the artifact oracle is explicit in `run.json`.

The oracle actually executes the numerical fitter using the public service. All three cases used 105 queries each; maximum positional error was 1.182e-5 m, maximum orientation error 0.001350 degrees. Independent unprivileged reproduction under Node 22.20.0 passed. The public interface and three target images were exercised in Chromium 141.0.7390.37 with WebGL2.

| Probe | Reward | Verifier exit | Evidence |
|---|---|---|---|
| oracle | 1 | 0 | `authoring/runs/20261127T123213Z-final-oracle` |
| nop | 0 | 0 | `authoring/runs/20261127T123213Z-final-nop` |
| zero-controls | 0 | 0 | `authoring/runs/20261127T123213Z-final-zero-controls` |
| nan-controls | 0 | 0 | `authoring/runs/20261127T123213Z-final-nan-controls` |
| boolean-controls | 0 | 0 | `authoring/runs/20261127T123213Z-final-boolean-controls` |
| duplicate-json | 0 | 0 | `authoring/runs/20261127T123213Z-final-duplicate-json` |
| wrong-case | 0 | 0 | `authoring/runs/20261127T123213Z-final-wrong-case` |
| over-budget | 0 | 0 | `authoring/runs/20261127T123213Z-final-over-budget` |
| private-route | 0 | 0 | `authoring/runs/20261127T123213Z-final-private-route` |
| fixture-corrupt | absent (expected infrastructure fault) | 1 | `authoring/runs/20261127T123213Z-final-fixture-corrupt` |

## Environment

- `sci-pose-env:dev`: `sha256:9b31924d7e1f7e66ac2e34558319a5591f78b4ea46e3e5aa1d08298f29032abf`, 3800817241 bytes.
- `sci-pose-tests:dev`: `sha256:fbc8e8fe451d909f27ac7a6044ab8b25d2b7934663dad76eb3d86ef17aefc499`, 3736083046 bytes.

Image metadata and installed package versions are in `images.json` and
`packages-*.txt`. Bases are pinned by OCI digest; Blender 4.2.3 archive is
verified by SHA-256. Builds used the declared contexts, network only during
build, the Tsinghua Ubuntu mirror, and BuildKit caches. Cached dependencies
were reused after source-only changes. The package repositories are live,
not an immutable OS snapshot; a cache-purge rebuild on a second machine has
not been verified. This is excluded from the reproducibility claim.

`desktop.png` records the 1920x1080 GUI. The Blender first-run dialog is
disabled; the pose inspector opens locally and its query button increments
the trusted service count. External network failure and absence of private
actor files were checked in `desktop-smoke.txt` (pose network probe) and the
startup smoke. Verifier Docker runs use `--network none` in every run command.

## Reproduction

Build the environment and tests contexts with the image tags used by
`tasks/cua/tools/sanity_animation_web3d.py`; build the pose sidecar separately.
From WSL run:

```sh
python3 tasks/cua/tools/sanity_animation_web3d.py pose-repair
```

Static validation uses `static_animation_web3d.py` in an environment with
Python 3.12, Bash and Node 22. The older batch sanity script has a hard-coded
list of Blender-only files and model-calibration gates; it is not used as a
Web3D task validator. Runtime semantic checks use the formal `tests/test.sh`,
not an alternate permissive grader. `reward.txt` is the sole binary reward;
injected trusted fixture/metrics failures have nonzero exit and no reward.

## Explicit limits

- Full Harbor scheduling and sidecar handoff through the installed Harbor
  application were not executed. Compose merge and the documented service
  artifact contract were inspected; direct Docker handoff was executed.
- No five-model pass-rate calibration, independent acceptance agent, cold GUI
  model trace, cache-purge/second-machine test or cross-platform study ran.
- Fight collisions are evaluated at the 300 frame samples, on convex authored
  segment geometry, with ancestor/descendant joint exclusions; penetration
  depth uses vertex containment. This is not continuous collision detection.
- Pose privacy uses separate containers and root-only verifier fixtures plus
  an unprivileged candidate process. The audit records service route access;
  it is not a full operating-system syscall audit.
- Sanity demonstrates the stated functional contract; target model difficulty
  and the README proposal's 30-50% pass-rate goal remain unmeasured.
