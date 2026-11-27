# Actual GUI trajectories

Four Harbor computer-1 screenshot/input trials. All were interrupted by the operator before the full budget. No successful GUI solution is claimed.

| Task | GUI inputs executed | Action requests | Screenshots | Artifact reward |
|---|---:|---:|---:|---:|
| crate-lookdev | 134 | 147 | 148 | 0 |
| folding-chair | 149 | 157 | 158 | 0 |
| rainroom | 142 | 149 | 150 | 0 |
| toy-car | 131 | 138 | 139 | 0 |

GUI input counts exclude wait/zoom/done/answer and failed requests. ATIF agent steps include all 591 requests. Each screenshot reference resolves and every screenshot decodes. Submission hashes agree with the separate current-source grading records.

The files opened in Blender but required objects and output files were missing. R01_open in the existing verifier also reflects extraction prerequisites, so its unreadable detail does not mean the .blend bytes were corrupt. See Blender subprocess logs for the exact missing parts.

GUI/terminal compliance and artifact success are separate. This package includes partial, failed GUI trajectories. It does not meet a requirement for successful, full-budget GUI demonstrations.
