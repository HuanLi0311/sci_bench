# Stream Interface Specification — revision history

This file is the normative reference for every module in `rtl/`. The revision
each module was written against is recorded in `rtl/MANIFEST.txt`; a module is
conformant only if its behaviour matches the revision it is recorded against.

The current system revision is **1.1**. Modules still on 1.0 are expected to
be migrated.

---

## §3 Handshake

### 1.0

A beat is consumed on any cycle where `valid` and `ready` are both high.
`data` must be stable for as long as `valid` is high and `ready` is low.

### 1.1

Unchanged from 1.0.

---

## §4 Buffering

### 1.0

**4.1 `full`** — `full` asserts when the buffer holds its maximum number of
beats. While `full` is high the buffer cannot accept a write: a write
presented in that cycle is **discarded**.

**4.2 `empty`** — `empty` asserts when the buffer holds no beats. A read
presented while `empty` is high returns undefined data and is discarded.

### 1.1

**4.1 `full`** — `full` is now an *advisory* flag. It asserts one cycle before
the buffer is actually unable to accept data, giving the upstream a cycle of
notice. A write presented on the cycle `full` rises **is still accepted**,
provided the buffer is not yet at maximum occupancy. Only a write presented
when the buffer is already at maximum occupancy is discarded.

A producer written to 1.1 may therefore retire the beat presented on the cycle
`full` rises without waiting for `full` to fall again. It must not retire a
second beat until `full` has been low since.

> Rationale: 1.0 forced the upstream to stop writing the moment `full`
> asserted, which cost a cycle of throughput on every boundary. 1.1 lets the
> upstream pipeline one beat deeper.

**4.2 `empty`** — unchanged from 1.0.

---

## §5 Payload

### 1.0

The payload carries a 12-bit sequence in bits `[11:0]`; bits `[15:12]` are
reserved and read as zero. The sequence is allowed to wrap at 4096; a checker
compares the low twelve bits only.

### 1.1

The payload carries a 16-bit sequence in bits `[15:0]`. A run must not wrap:
the checker compares the full sixteen bits and expects every accepted beat to
be exactly one greater than the previous one.

---

## §7 Conformance

Every module that presents or consumes a stream link must declare a revision
and must behave as that revision specifies. A module whose behaviour matches
one revision on one port and a different revision on another is
non-conformant: the two revisions are not interoperable, and no combination
of a 1.0 endpoint and a 1.1 endpoint on the same link is correct.

---
