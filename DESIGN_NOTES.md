# Designing for difficulty

What makes a task hard for a frontier model, written from measurements made
while building the two tasks in this repository rather than from intuition.
The intuition was wrong twice, so the ordering below follows the evidence.

Everything here is backed by a run recorded in `README.md` or by a number in
the notes below. Where a claim is inference rather than measurement, it says
so.

## The evidence

| id | experiment | result |
|---|---|---|
| P1 | `opamp-triage`, codex / gpt-6.1-sol / high, sandbox containing only `sim/` and `fixtures/` | **pass**, reward 1, all five tiers |
| P2 | same task, second independent run | **pass**, reward 1 |
| F1 | `fsm-recode`, same model and scaffolding | **fail**: 485,034 / 500,000 cycles mismatched |
| F0 | `fsm-recode`, aider single-shot | fail, **not usable as evidence** — aider executes no commands, so the model could not simulate or synthesise at all |
| N1 | constant multipliers, plain vs CSD | 2592 -> 1965 cells; real headroom, but CSD is textbook |
| N2 | CSD plus a hand-built balanced adder tree | 1965 -> 1972 cells; no headroom left |
| N3 | 16x16 multiplier, `a*b` vs hand-written Karatsuba | 1579/34 vs 1647/47; the algorithm loses to the synthesiser |
| N4 | 12-state FSM: re-encode only vs minimise-then-encode | 68 vs 63 cells; the threshold cannot separate the two |

The headline result: the task that *looked* harder (analog, multi-objective,
process corners) was solved, and the task that looked like a textbook exercise
(state recoding) was not. Perceived domain complexity is not the variable.

## Criterion 1 — the correctness criterion must not be enumerable

`opamp-triage` states its acceptance as five numbers: gain 10.5-11.5, overshoot
<= 20 %, settling <= 4.0 us, slew >= 5.0 V/us, over three named amplitudes.
Once written down, "succeed" is a checklist, and closing a checklist over 14
parameters with a 50 ms simulator is search. The model searched and found it.

`fsm-recode` states its acceptance as one sentence: identical `out` on every
rising edge. That cannot be decomposed into partial credit — there is no "you
got state 3 right, +1". To move toward it at all you must first reconstruct
what the baseline machine *is*.

> Enumerable acceptance criterion -> an optimisation problem.
> Non-enumerable acceptance criterion -> a comprehension problem.

Practical rule: if you can write the grader's checks as a bulleted list in the
instruction, expect the task to be solved by search. Either keep the bullets
out (see Criterion 4 for how to stay gradable) or accept that you have built an
optimisation benchmark.

## Criterion 2 — the feedback must be built by the solver, and building it wrong must go undetected

This is the most valuable finding, and it came from watching *how* F1 failed.

codex did not skip verification. It wrote `tb_equivalence.v` and a `verify.sh`,
and ran them. The testbench checked the DUT against a state mapping it had
inferred itself:

```verilog
case (s) 16: mapped=3; 17: mapped=7; 18: mapped=11; 19: mapped=14; endcase
if (dut.state !== mapped[3:0]) $fatal(1, ...);
```

The mapping came from its (wrong) assumption that the transition function was
`state + in + 1`. Implementation and check shared one false premise, so the
check could not fail. This is not absent verification; it is verification that
is structurally incapable of reporting an error.

Contrast `opamp-triage`: the oracle is shipped by the task, external to the
agent, and objective. Every candidate can be checked against it. No
self-reference, so no self-confirmation, so search converges.

> An oracle the task supplies -> search works.
> An oracle the solver must construct -> the self-confirmation trap opens.

This is also why adding a simulation budget to `opamp-triage` is the wrong
hardening: it makes search expensive but leaves both the enumerable criterion
and the external oracle intact. A budgeted search is still a search.

Design consequence: tasks in this family should require the solver to produce
evidence, and the grader should be able to tell whether that evidence was
capable of failing. One way is to demand a discriminating stimulus: a test
input under which the faulty and corrected versions differ maximally, scored by
running both. A testbench that cannot distinguish the two scores zero.

## Criterion 3 — the search space must lie outside the tool's competence

Three designs died the same way:

- **CSD constants (N1).** 2592 -> 1965 cells, a 24 % win, and worthless as a
  task: CSD is in every textbook, so the threshold tests recall.
- **Post-CSD rewrites (N2).** A hand-balanced adder tree came out *worse*
  (1972 vs 1965). `abc` had already found the better structure.
- **Karatsuba (N3).** 1647 cells / 47 levels against 1579 / 34 for plain
  `a * b`. The hand-written algorithm loses.

The common cause is that all three live where the synthesiser is strongest:
gate-level rewriting, constant propagation, adder-tree restructuring. On flat
combinational datapaths, `yosys`/`abc` is a good enough reference optimiser that
RTL-level rewrites get erased.

What survives is the decisions the tool does not make: state encoding
(`fsm-recode`, 307 -> 140 cells), resource sharing, retiming. These are
cross-cycle or cross-module structural choices, and they are the designer's job
by construction.

> Do not put the task where the tool is strong. The tool will flatten the space.

Corollary: check the headroom *after* the obvious transformation. If the
textbook move leaves nothing, the task is unsolvable; if it leaves nothing
measurement-visible, it is not a task.

## Criterion 4 — difficulty needs a discrete step

The first `fsm-recode` draft had 12 states, minimisable to 10. Both fit in a
4-bit register, so "re-encode" and "minimise then re-encode" measured 68 and 63
cells — a 7 % gap that no threshold can split. The task was either trivially
solvable or impossible, with no middle.

Rebuilding it as 20 states with 4 reachable behavioural duplicates crosses the
5-bit/4-bit boundary, and the two steps separate cleanly: 192 vs 140. A
threshold at 160 turns "did half the job" into a graded failure.

> Put the step on a discrete boundary — bit width, register count, state count,
> pipeline depth. A continuous percentage gives you no threshold to stand on.

## Criterion 5 — the failure mode must exist in real work

`fsm-recode` is not a puzzle. "I changed the RTL and I need to know I did not
break it" is daily work, and writing the testbench from your own reading of the
spec is exactly where real engineers fall in. The model fell in the same place.

`opamp-triage` also models real work (parameter drift, partial observability),
but it fails Criterion 1, so the realism does not convert into difficulty.

> Practical difficulty is a failure mode that occurs in practice, not a long
> tool chain or a dense vocabulary.

A negative example on the other side: AlphaEvolve's "optimise an already
refined RTL block" is unquestionably real, and we cannot reproduce it — it
depends on commercial synthesis against a real cell library. Real is not the
same as reproducible. Both conditions have to hold.

## Checklist

A candidate task must pass all five:

1. **Is the acceptance criterion enumerable?** If yes, expect search to solve
   it. Rewrite it as observable equivalence, or accept it as an optimisation
   benchmark.
2. **Does the task supply the oracle?** If yes, expect convergence by
   trial and error. If the solver must build it, check that a wrong build can
   be detected from outside.
3. **Is the search space inside the tool's competence?** Measure the headroom
   after the obvious transformation. If it is zero, discard.
4. **Is there a discrete step to threshold on?** Find the bit width, state
   count, or depth that crosses a boundary. If none exists, the task has no
   middle.
5. **Does the failure mode occur in real work?** If not, it is a puzzle, and
   the difficulty will not transfer.

## What this predicts for the next task

The family that survives all five criteria is **behaviour preservation over
time**: a module with latency, handshaking, or a retiming requirement, where
the deliverable must produce the same observable sequence within a given cycle
budget.

- the criterion is per-cycle equality — not enumerable into partial credit
- the testbench must be built by the solver, and a weak one is detectable by
  scoring it against known-buggy variants
- `yosys` does not make retiming decisions, so the space is outside it
- pipeline depth and register count give discrete steps
- "I restructured it and it still behaves" is ordinary work

Not yet measured. Criterion 3 in particular has to be checked by building a
reference and seeing what headroom is actually left, exactly as N1-N3 were.
