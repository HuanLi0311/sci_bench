# Microscope assembly and focus (README task 5)

Harbor 1.4 Web3D environment under tasks/cua. Agent may use browser, terminal and scripts. It receives original reference drawings, optical PDF, two authored samples, three model-derived target views, JSON Schema and a blank Three.js starter. No reference application or verifier code is copied into the agent image. Both containers use the same pinned Chromium/SwiftShader runtime; all dependencies install at build time.

Build from the two independent allowlisted contexts:
```sh
docker build -t cua-qc-microscope-focus-env environment
docker build -t cua-qc-microscope-focus-tests tests
```
Agent desktop: `docker run --rm --network none -p 6080:6080 -p 8080:8080 cua-qc-microscope-focus-env`. noVNC is at http://localhost:6080/vnc.html (1920×1080), starter at http://localhost:8080/starter/. Only publish localhost ports on shared hosts. The image also includes terminal/code tools. Resource allocation: 4 CPU, 8192 MiB, no GPU. Offline runtime is intentional and follows this Web3D task's supplied contract, despite older unrelated tasks using public agent networking.

Run `python3 authoring/run_sanity.py` on a Docker host from this directory for cold-start oracle, repeated oracle, true NOP, scientific and contract negatives, boundary checks, infrastructure fault injection and isolation evidence. The reference solve.sh copies an authored application into a clean agent container at execution time, never image build time. Only the `/app/out` directory is exported to the separate verifier at `/app/out`, read-only. Verification runs `/tests/test.sh` with `--network none`, 4 CPU, 8 GiB and 512 PIDs. Reward is exactly one binary `/logs/verifier/reward.txt`; rich metrics and CTRF are separate. A damaged trusted fixture or driver causes nonzero infrastructure exit and no reward. Submission errors produce reward 0 with an attributable check.

The rubric matches proposal R01-R15. Numerical truth is recomputed from actual world coordinates using an independent reciprocal lens formula. Actual ray vertices and image canvas are inspected in clean browser contexts. Unknown-sample substitution and compound held-out focus changes detect static outputs. JSON duplicate keys/nonfinite values/types, missing files, symlinks and output budgets are checked before loading browser code. The normal item is R08 image SSIM; it must pass to meet the 80% rule. See materials/SPEC.md for the exact callable interface and calibrated image-plane mapping. No screenshot-only submission is accepted.

Evidence and limits are in SANITY_REPORT.md. These are direct Docker tests, not official Harbor scheduling or a GUI model trajectory. No model success rate or five-run difficulty calibration is claimed. The repository's Blender-centric checker is extended only where necessary for this Web3D task. Browser rendering is inspected as runtime evidence, but this is not a proof against arbitrary adversarial JavaScript that falsifies every observable browser API. Physical modelling covers ideal paraxial thin lenses only.
