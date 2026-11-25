# ic-bench — verifiable-reward IC tasks

Two tasks, both Terminal-Bench-Science / Harbor format, both original work.

## Tasks

| Task | What the agent must do | Reference | Frontier model |
|---|---|---|---|
| `opamp-triage` | Diagnose three drifted parameters of a CMOS op-amp macro-model from two noisy scope captures, then deliver a sizing that also holds at an amplitude and process corners that were never captured | reward 1.0 in container | not yet run |
| `fsm-recode` | Re-implement a 20-state one-hot controller so it is cycle-accurately equivalent but synthesises to <=160 cells and <=42 levels | 140 cells / 34 levels | **failed**: 434,397/500,000 cycles mismatched |

```
tasks/engineering-sciences/electrical-engineering/
  opamp-triage/
  fsm-recode/
```

Both are laid out per the TB-Science schema: `instruction.md`, `task.toml`,
`environment/Dockerfile`, `tests/Dockerfile` (separate verifier), `tests/test.sh`,
`solution/solve.sh`, `README.md` with the three required sections, and
`authoring/provenance/SOURCES.md`.

## Verified state

| Check | opamp-triage | fsm-recode |
|---|---|---|
| all 24 static `ci_checks/` | pass | pass |
| reference solution, host | reward 1 | reward 1 (140/34) |
| reference solution, container (oracle) | **reward 1.0** | not completed (memory reclaim killed the run mid-verifier) |
| agent image isolation | verified: only `sim/`, `fixtures/`, empty `out/`; no answer values | verified by construction: only `rtl/baseline.v` |
| blind frontier model | not yet run | failed equivalence |

## Why these two

They test different things. `opamp-triage` is inference from partial evidence —
two of the three drifts are visible in the captures, the third only appears at an
amplitude that is declared but never measured. `fsm-recode` is structural
optimisation under an equivalence constraint — and the obvious move (re-encode
the state register) is measurably insufficient, because four states are
behavioural duplicates that must be merged first.

## Negative results worth keeping

Three plausible designs were measured and rejected. They are recorded because
each one looked good on paper:

- **Constant multipliers (CSD)**: 2592 -> 1965 cells, but CSD is textbook, so a
  threshold there tests recall rather than optimisation.
- **Post-CSD headroom**: none. A hand-built balanced adder tree came out at 1972
  cells vs 1965 — `yosys`/`abc` had already found the better structure.
- **Karatsuba 16x16**: 1647 cells / 47 levels vs 1579 / 34 for plain `a*b`. The
  hand-written algorithm loses to the synthesiser.

Conclusion: on flat combinational datapaths, `abc` is a strong enough optimiser
that RTL-level rewrites get erased. What is left is structural decisions it does
not make — state encoding, resource sharing, retiming.

A fourth negative result, on the first attempt at `fsm-recode`: a 12-state
machine reduced to 10 gives no separation between "re-encode" and "minimise",
because both fit in a 4-bit register (68 vs 63 cells). Moving to 20 states with
4 dead duplicates crosses the 5-bit/4-bit boundary and separates the two steps
(192 vs 140).

## Tooling notes

- Local docker is a WSL2 Ubuntu 24.04 with `harbor==0.23.0` installed via uv.
- `network_mode = "no-network"` for the verifier is rejected by the docker
  backend here: harbor probes the kernel for `nftables fib inet` support and
  WSL2 fails it. Local runs flip the verifier to `public`; the committed files
  stay at `no-network`.
- `codex` cannot be installed inside the task container here (81 minutes, then
  `curl: not found`). `aider` also fails (uv download from GitHub breaks). Model
  tests were therefore run from the host against a sanitised directory.
- apt from within containers is flaky; both Dockerfiles retry the install.

## Open items

- `fsm-recode` oracle needs a rerun to completion.
- `opamp-triage` blind model test not yet run.
- Both thresholds are calibrated against one reference solution and one model
  run each; more data would sharpen them.
