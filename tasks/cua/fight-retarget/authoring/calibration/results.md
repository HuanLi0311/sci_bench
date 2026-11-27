# Final sanity record

Date: 2026-11-27 (Asia/Shanghai). Task: `fight-retarget`. Operational source SHA-256:
`84d9ba4a272709171713d82cb7771b949401fefc58b0afc1d0c551cf6845d985`. Per-file source hashes are in `source-digest.json`;
all final grader snapshots and commands are retained under the indexed runs.

Sanity functional matrix: PASS. Scope: direct Docker, not a Harbor scheduler
trial; no model inference, GUI-model success claim or difficulty calibration.
Every candidate trial ran with 4 CPUs, 8 GiB container memory, 256 PID limit,
and a no-network verifier. Only declared output plus trusted sidecar evidence
(pose task) were passed. No actor source checkout was mounted in the verifier.
The actor/solution mount used for the artifact oracle is explicit in `run.json`.

The oracle is replay of known authored artifacts, not a cold GUI solve. Two 22-bone rigs, 300 frames, all contacts, every-frame collision checks, foot locks, FBX imports, four Cycles PNGs and four decoded video frames passed. A six-frame action shift scored below 0.98; swapped actions failed reachability as intended.

| Probe | Reward | Verifier exit | Evidence |
|---|---|---|---|
| oracle | 1 | 0 | `authoring/runs/20261127T123141Z-final-oracle` |
| nop | 0 | 0 | `authoring/runs/20261127T123141Z-final-nop` |
| render-substitution | 0 | 0 | `authoring/runs/20261127T123141Z-final-render-substitution` |
| malformed-image | 0 | 0 | `authoring/runs/20261127T123141Z-final-malformed-image` |
| floating-feet | 0 | 0 | `authoring/runs/20261127T123141Z-final-floating-feet` |
| static-action | 0 | 0 | `authoring/runs/20261127T123141Z-final-static-action` |
| camera-away | 0 | 0 | `authoring/runs/20261127T123141Z-final-camera-away` |
| fixture-corrupt | absent (expected infrastructure fault) | 1 | `authoring/runs/20261127T123141Z-final-fixture-corrupt` |
| metrics-omitted | absent (expected infrastructure fault) | 1 | `authoring/runs/20261127T123141Z-final-metrics-omitted` |

## Environment

- `sci-fight-env:dev`: `sha256:8e2fae008f50190d89441e0ed831b2e04202c70dc78d705ca81a97736b1eb7c1`, 2880050965 bytes.
- `sci-fight-tests:dev`: `sha256:26de596efb9a98199961402e3a5669d65b21045c411f89bd0635dfb6fbe2d9d6`, 2678602306 bytes.

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
python3 tasks/cua/tools/sanity_animation_web3d.py fight-retarget
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
