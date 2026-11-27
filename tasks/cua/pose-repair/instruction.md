# Multiview pose fitter repair

Repair `/app/materials/fitter.cjs`. It runs but returns an incorrect neutral
pose because it ignores a fixed, globally coupled control mapping. Three
independent target cases have front, side and oblique PNGs with joint centres
and local orientation axes. There are 24 bounded controls, three angular
degrees of freedom per joint, on an immutable eight-joint upper-body avatar.

Use only the public client `/app/materials/client.cjs` to query the local
`http://pose-service:8090` API. `targets()` gives all three target observations;
`query(case, controls)` gives current observations and the server query count.
The 192 scalar observations are three views, each with eight joints, each with
four 2D points: centre, local +X, +Y, +Z endpoints at 0.16 m. See `scene.json`
for projection constants and fixed bone hierarchy. Bounds are in `bounds.json`.
The GLB, bone lengths, global mapping and hidden target controls are immutable.
The local WebGL2 inspector is at `http://localhost:8080`; drag to orbit.

Each case has a lifetime budget of 1200 queries, including rejected controls
and calls beyond the limit. There is no reset endpoint; restarting your client
does not reset server state. `targets()` and health checks do not count.
Controls must be a JSON array of exactly 24 finite real numbers in [-1, 1].
Booleans, NaN, Infinity, wrong shapes, duplicate object keys and symlinks are
not accepted. Dependencies must be local and run under the supplied Node.
Only the internal pose service is reachable; the task has no external network.

Deliver to `/app/out`:

- `solution/fitter.cjs` and any local dependencies. Run interface:
  `node /app/out/solution/fitter.cjs /app/out`. It must solve all three cases,
  write the files below, and work from an empty output directory with a fresh
  public service. At most 64 solution files, each <=2 MB; no symlinks.
- `controls_case_a.json`, `controls_case_b.json`, `controls_case_c.json`.
- `replay.json`, exactly
  `{"schemaVersion":1,"scene":"avatar.glb","cases":["controls_case_a.json","controls_case_b.json","controls_case_c.json"]}`.
- `query_counts.json`, object with integer fields `a`, `b`, `c`, recording the
  actual server query counts. This machine-readable companion is mandatory.
- `report.md`: method, reproduction command above and query counts, including
  a JSON count object. No self-reported positional errors are used for grading.

Every specified joint in every case must be within 0.02 m of its target in
world space, with local world orientation error <=5 degrees. The verifier
replays controls in the original scene with the private coupling: changing
your copy of the avatar cannot affect grading. Bone lengths may not change
by more than 1e-6 m. Repeated replay must agree to 1e-4. All three cases must
pass individually. It also runs your submitted code from a clean directory
against a new service. That subprocess has a 120 s wall limit, 90 s CPU,
4 GiB address space, 64 file descriptors, 64 processes and no access to the
trusted fixture; it may only use the public API. It must reproduce passing
controls within 1200 queries per case without external network or downloads.

Reward is binary: all must and critical requirements, plus >=80% of normal
checks. Normal checks are exact report/count agreement, average <=800 queries,
and successful clean-directory reproduction. Attempting a non-public service
endpoint is recorded and fails the private-access audit. The trusted ledger
is collected directly from the isolated service, never from your report.
Do not read private files, change the scene/service, reset counters, alter the
benchmark or verifier, or fabricate logs and reward files. Shell and JS coding
are allowed because this task is a program repair task.

You have 7200 seconds to complete this task.
