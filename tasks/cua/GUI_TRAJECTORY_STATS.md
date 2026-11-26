# GUI trajectory statistics ? four CUA tasks

Generated from the recovered task indexes and raw trajectories. A GUI operation requires an actual computer/CUA input event or screenshot-control call. Terminal `exec` and `wait` calls do not count as GUI operations.

| Task | Attempts | Trajectories | GUI trajectories | Terminal trajectories | Agent steps | Tool calls |
|---|---:|---:|---:|---:|---:|---:|
| crate-lookdev | 14 | 1 | 0 | 1 | 67 | 66 |
| folding-chair | 0 | 0 | 0 | 0 | 0 | 0 |
| rainroom | 1 | 1 | 0 | 1 | 68 | 64 |
| toy-car | 0 | 0 | 0 | 0 | 0 | 0 |
| **Total** | **15** | **2** | **0** | **2** | **135** | **130** |

The crate trajectory is an ATIF terminal run. The rainroom trajectory is a Codex raw JSONL terminal run with 56 `exec` calls and 8 `wait` calls. No recovered model attempt contains GUI click, drag, key, screenshot-control, or computer-1 input events. Oracle/NOP/negative verifier runs are excluded from model trajectory counts.
