# Stream Interface Specification — revision history

This file is the normative reference for every module in `rtl/`. Each module
declares the revision it was written against in its file header. A module is
conformant if and only if its behaviour matches the revision it declares.

The current system revision is **1.1**. Modules on 1.0 are expected to be
migrated.

---

## §3 Handshake

### 1.0

A beat is consumed on any cycle where `valid` and `ready` are both high.
`data` must be stable while `valid` is high and `ready` is low.

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
notice. A write presented while `full` is high **is still accepted**, provided
the buffer is not yet at maximum occupancy. Only a write presented when the
buffer is already at maximum occupancy is discarded.

> Rationale: 1.0 forced the upstream to stop writing the moment `full`
> asserted, which cost a cycle of throughput on every boundary. 1.1 lets the
> upstream pipeline one beat deeper.

**4.2 `empty`** — unchanged from 1.0.

---

## §7 Conformance

A monitor or adapter that observes a buffer is not itself required to declare
a revision, but any module that reads `full` or `empty` must declare one, and
must behave as specified in that revision.

---

## Changelog

| rev | change |
|---|---|
| 1.0 | initial |
| 1.1 | §4.1 `full` changed from blocking to advisory |
