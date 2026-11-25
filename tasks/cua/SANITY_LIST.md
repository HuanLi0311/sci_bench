# SANITY_LIST — CUA task pack QC

Every task under `ic-bench/tasks/cua/` must pass all of the checks below before
it is considered done. `tools/sanity_check.py` runs them and prints a table;
this file says what each check means and what a pass looks like.

Run it with:

```
python3 ic-bench/tasks/cua/tools/sanity_check.py        # on the host, docker available
```

| # | Check | Pass means |
|---|---|---|
| 1 | **Pack layout** | `task.toml`, `instruction.md`, `README.md`, `environment/Dockerfile`, `tests/{Dockerfile,test.sh,grade.py,check_scene.py,rerender.py}`, `solution/solve.sh`, `authoring/provenance/SOURCES.md`, `authoring/calibration/results.md` all exist |
| 2 | **task.toml** | `schema_version = "1.4"`, `[task].name = "terminal-bench-science/<folder>"`, non-empty description, authors, keywords, `[verifier] environment_mode = "separate"`, both timeouts set |
| 3 | **Instruction suffix** | `instruction.md` ends with `You have <N> seconds to complete this task.` and N equals `[agent].timeout_sec` |
| 4 | **Materials** | `environment/materials/` is non-empty and has a `LICENSE.txt` |
| 5 | **Environment image** | Dockerfile builds; `/app/materials` present, `/app/out` empty, no `solution/` or answer file inside the image |
| 6 | **Verifier image** | `tests/Dockerfile` builds and `test.sh` is executable |
| 7 | **Oracle** | running the verifier against `solution/` returns `reward.txt` = 1 and every check passes |
| 8 | **Deliverables** | the reference output contains every file the instruction names, at the stated resolution |
| 9 | **Anti-cheat present** | `grade.py` has at least one `critical` check and `rerender.py` re-renders from the delivered scene |
| 10 | **Negative test** | the tolerance table in `authoring/calibration/results.md` records at least one mutation that scores 0 |
| 11 | **Licences** | every asset in the solution `manifest.json` has `source` and `license` |

## Known local deviations (not failures)

- `[verifier.environment] network_mode = "no-network"` is rejected by the local
  Docker backend (WSL2 lacks `nftables fib inet`); for the oracle run the QC
  script runs the verifier image directly instead of through `harbor run`.
- Base image `blender-bench:gui` is local; see
  `crate-lookdev/authoring/base-image.md`.
- Videos in `toy-car` are 3 s at 640×360 rather than 6 s at 1280×720.
- `rainroom` ships three photographs rather than four.
