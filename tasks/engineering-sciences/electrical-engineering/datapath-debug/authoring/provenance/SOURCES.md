# Provenance

The task is original work. No external task text, answer key or dataset is
included.

## What is authored here

- The RTL in `environment/rtl/` — a four-stage stream: generator, 16-deep
  FIFO, rate limiter, contiguity checker, plus three passive observers.
- `environment/SPEC.md` — the two-revision interface document.
- `environment/REPORT.md` — the incident report.
- The unit testbenches and the integration testbench.

## What it is modelled on

The failure mode is a real one: a producer and a receiver that were written
against different revisions of the same handshake contract, where each module
is conformant to the revision it declares and the *system* is what breaks.
Two properties are borrowed from practice rather than invented:

1. **Advisory flow control.** Moving a `full`/`ready` flag one cycle ahead of
   true capacity, so the upstream can pipeline a beat deeper, is a common
   latency optimisation and a common source of dropped beats when only one
   side of a link is migrated.
2. **Payload width drift.** A sequence counter widened from 12 to 16 bits in
   the specification while the generator keeps the old width. It is invisible
   for the first 4096 beats, which is the property that makes it worth
   including: a short test cannot see it.

No vendor document, datasheet or course material was copied. The 1.0/1.1
split, the wording of both revisions and the incident report are written for
this task.

## Numbers quoted in the repository

| Run | Result |
|---|---|
| shipped build | `TOP_OK=3054 TOP_ERR=4783 TOP_BEATS=7837 TOP_CYCLES=10601` |
| reference solution | `TOP_OK=9000 TOP_ERR=0 TOP_BEATS=9000` |
| iverilog 12.0, Ubuntu 24.04, `iverilog -g2012` | both reproduce |

## Tooling

`iverilog` 12.0 from the Ubuntu 24.04 archive, installed in both the agent
image and the verifier image from the same base so that the simulation is
bit-identical on both sides.
