# Incident: data beats arrive out of sequence under load

**Severity:** high
**Symptom:** the sink reports sequence errors, but only when the system is busy.

## What we see

`top` streams an incrementing 16-bit sequence from `axis_source` into
`axis_sink`. The sink checks that each accepted beat follows the previous one
and bumps `err_count` when it does not.

Under light load, `err_count` stays at zero and every beat is accepted.

Under heavy load, `err_count` climbs steadily. From a recent run:

```
TOP_OK=1248 TOP_ERR=250 TOP_BEATS=1498
```

Roughly one beat in six is rejected.

## What we have already ruled out

All three unit tests pass:

```
tb_source   SOURCE_CHECKED=200 SOURCE_MISMATCH=0
tb_sink     SINK_OK=299 SINK_ERR=0
tb_monitor  MON_BEATS=52 MON_STALL=14
```

Each module has been reviewed against its own header comment and looks
correct. The clock is clean, reset is synchronous, and the design is
single-clock.

## Where to look

The failure depends on the *load*, which suggests a flow-control or timing
interaction rather than a logic error inside any one module. Nothing in the
unit tests exercises a busy system.

## What we need

Find the root cause and fix it. The acceptance condition is simple:

- integration run with `tb_top` must report `TOP_ERR=0`

Keep the module interfaces as they are — the fix belongs inside a module, not
in a change to the port lists.
