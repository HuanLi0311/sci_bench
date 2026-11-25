# Incident: beat stream fails the contiguity check under load

**Severity:** high
**Symptom:** the sink reports sequence errors. They are intermittent early in a
run and then permanent once the run is long enough.

## What we see

`top` streams an incrementing 16-bit sequence from `axis_source` through
`fifo16` and `throttle` into `seq_check`. The sink checks that each accepted
beat follows the previous one and bumps `err_count` when it does not.

A recent integration run:

```
TOP_OK=3054 TOP_ERR=4783 TOP_BEATS=7837 TOP_CYCLES=10601
```

Of the 9000 beats the generator emits, only 7837 reach the sink at all, and
4783 of those are rejected.

## What we have already ruled out

All four unit tests pass:

```
tb_source    SOURCE_CHECKED=200 SOURCE_MISMATCH=0
tb_fifo16    FIFO_BAD=0
tb_throttle  THR_SENT=300 THR_GOT=300 THR_BAD=0
tb_seq       SEQ_OK=512 SEQ_ERR=0
```

Each module has been reviewed against its own header comment and looks
correct. The clock is clean, reset is synchronous, and the design is
single-clock.

## Where to look

Both symptoms depend on the *load* and on how *long* the run has been going,
which suggests the stages disagree about something that only shows up when
they run against each other. Nothing in the unit tests exercises a busy
system, and none of them runs long enough to see the second half of a run.

`SPEC.md` is the normative reference.

## What we need

Find the root cause and fix it. The acceptance condition is simple:

- integration run with `tb_top` must report `TOP_ERR=0`
- all 9000 beats must reach the sink

Keep the module interfaces as they are — the fix belongs inside a module, not
in a change to the port lists. `top`, `seq_check`, `monitor`, `checksum8` and
`reset_sync` are not part of the submission and will be replaced with pristine
copies when this is checked.
