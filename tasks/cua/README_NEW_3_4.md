# README questions 3 and 4

This delivery implements the two proposals in root README sections 4.3 and 4.4:

| Proposal | Task | Contents |
|---|---|---|
| 3: two-character fight retargeting | `fight-retarget/` | Two CC0 22-bone block-style humanoids, synthetic 10-second reference, mapping XLSX/CSV/JSON, segment/support tables, stage PDF, editable reference .blend and FBXs, video/PNGs, separate verifier |
| 4: multiview pose fitter repair | `pose-repair/` | Eight-joint upper-body avatar with 24 angular controls, nine target PNGs, broken JS fitter, public client, immutable skinned GLB, private budget service, numerical reference fitter, independent separate verifier |

The root README is the original proposal; its section 4.6 "not yet made" table
predates these two task packages. The executable per-task instructions and
`authoring/calibration/results.md` describe the delivered interfaces and evidence.
This document does not change the state of questions 1, 2 or 5.

The tasks include the input packs, reference solutions, authoring sources,
licensing, Docker contexts, binary-reward verifier and raw sanity evidence.
Neither task copies tests, authoring or solutions into its actor image. The
pose sidecar owns the private mapping and append-only service ledger. Only
declared output and directly collected service evidence reach the verifier.

Use `tools/static_animation_web3d.py` for scoped static checks and
`tools/sanity_animation_web3d.py <task>` for the direct Docker sanity matrix.
Image tags used by the runner are `sci-fight-env:dev`, `sci-fight-tests:dev`,
`sci-pose-env:dev`, `sci-pose-tests:dev`, `sci-pose-service:dev`. Build each from
its corresponding environment, tests, or environment/service context.

Blender is 4.2.3 with a verified archive hash. The Web3D runtime uses the pinned
Playwright 1.56.1 image, Node 22.20.0 and Chromium 141.0.7390.37, replacing the
proposal's unavailable local `web3d-bench:dev` image. Agent and verifier execute
submitted JS with the same Node build. The pose task needs a Compose-capable
Harbor backend with schema 1.4 service artifact collection. Direct Docker
collection and replay were tested; a complete Harbor scheduler job was not.

Sanity is intentionally separate from difficulty calibration: no model inference,
five-model pass-rate study or independent acceptance agent ran. The Blender
oracle is authored-artifact replay and is not a GUI model success. The pose
oracle actually solves each case via the public API. See each task's final
records for all candidate negatives, expected infrastructure failures, image
IDs, dependency versions, source hashes and explicit reproducibility limits.

The pinned base images and Blender binary fix the principal runtime. Ubuntu
package sources are live, and a cache-purge rebuild on a second host remains
unverified. Collision checking samples the 300 frames and uses the documented
anatomical joint exclusions; it does not claim continuous-time collision safety.
