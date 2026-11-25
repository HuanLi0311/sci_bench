# ic-bench — verifiable-reward IC tasks

Three tasks, all Terminal-Bench-Science / Harbor format, all original work.

## Tasks

| Task | What the agent must do | Reference | Frontier model (codex, gpt-6.1-sol, high) |
|---|---|---|---|
| `opamp-triage` | Diagnose three drifted parameters of a CMOS op-amp macro-model from two noisy scope captures, then deliver a sizing that also holds at an amplitude and process corners that were never captured | reward 1.0 in container | **passes**, reward 1, all five tiers |
| `fsm-recode` | Re-implement a 20-state one-hot controller so it is cycle-accurately equivalent but synthesises to <=160 cells and <=42 levels | 140 cells / 34 levels | **fails**, 485,034/500,000 cycles mismatched |
| `datapath-debug` | Repair a four-stage streaming datapath whose modules were written against two revisions of one interface spec, so every unit test passes while the integrated system drops and rejects beats | `TOP_ERR=0`, 9000/9000 beats | pending |

```
tasks/engineering-sciences/electrical-engineering/
  opamp-triage/
  fsm-recode/
  datapath-debug/
tasks/cua/
  crate-lookdev/
```

## CUA batch

`tasks/cua/` holds computer-use tasks that run against the harbor `computer-1`
agent on a virtual 1920x1080 XFCE desktop. First one built:

| Task | What the agent must do | Reference | Oracle |
|---|---|---|---|
| `crate-lookdev` | Build a weathered 800x600x600 mm wooden crate in the Blender 4.2 GUI from a three-view drawing — 20 mm panels, rear-hinged lid 0-95°, eight rusted corner brackets, worn stencil — and deliver a packed `.blend` plus four camera renders | 13/13 checks, 2858 tris | **reward 1**; swapped render and unpacked textures both score 0 |

Its base image is the local Blender desktop image (`blender-bench:gui`), recipe
in `tasks/cua/crate-lookdev/authoring/base-image.md`.

Both are laid out per the TB-Science schema: `instruction.md`, `task.toml`,
`environment/Dockerfile`, `tests/Dockerfile` (separate verifier), `tests/test.sh`,
`solution/solve.sh`, `README.md` with the three required sections, and
`authoring/provenance/SOURCES.md`.

## Verified state

| Check | opamp-triage | fsm-recode | datapath-debug |
|---|---|---|---|
| all 24 static `ci_checks/` | pass | pass | same result as fsm-recode on every check |
| reference solution, host | reward 1 | reward 1 (140/34) | reward 1 (`TOP_ERR=0`, 9000/9000) |
| reference solution, container (oracle) | **reward 1.0** | **reward 1.0** (0 mismatch, 140/34) | **reward 1.0** (38 s) |
| agent image isolation | verified: only `sim/`, `fixtures/`, empty `out/`; no answer values | verified by construction: only `rtl/baseline.v` | verified: only `rtl/`, `tb/`, `SPEC.md`, `REPORT.md`, `sim.sh`; no answer values |
| blind frontier model (codex) | **passes** — needs hardening | **fails** — discriminating | pending |

## Blind-run findings

**`opamp-triage` is too easy.** codex passed all five tiers. The task hands
over the full specification (gain band, overshoot, settling, slew, all three
amplitudes, the corner model), the simulator costs 50 ms, and there are 14
parameters with a stated budget of 4 edits. That is a search problem, and the
model solved it by search. The `vsat` holdout — designed to punish an agent
that only fixes what it can see in the captures — did not bite, because the
datasheet states the 1.2 V amplitude and the +/-1.5 V input range explicitly.

**`fsm-recode` works, and for a reason worth recording.** codex produced a
39-cell / 27-level design, comfortably inside both QoR budgets, and it did
write its own equivalence testbench. It still failed on 485,034 of 500,000
cycles. Two distinct errors compounded:

1. It assumed the transition function was `state + in + 1` with three
   hand-patched exceptions. The real table has no such regularity.
2. Its testbench checked the design against *its own inferred state mapping*
   (`16 -> 3, 17 -> 7, 18 -> 11, 19 -> 14`) rather than against observable
   behaviour, so the implementation and the check shared one wrong premise.

The second is the interesting one. It is not a failure to verify; it is
verification that cannot fail. A task that only measured QoR would have
scored this a pass.

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
