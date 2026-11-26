# Shared-hinge collision audit

The complete pre-fix verifier accepted an intersecting scene with reward 1
(15/15 checks). Two 14 mm cubes, `collision_a` and `collision_b`, shared
`hinge_01` as their parent. Their centres were approximately
`(-0.280, 0.000, 0.100)` and `(-0.277, 0.003, 0.102)` metres. The hinge
centre was `(-0.280, 0.000, 0.225)` metres: this was penetration away from
the pin, not contact at the joint.

The old `related()` predicate exempted an entire mesh pair whenever the
objects shared a named hinge, or one mesh parented the other. This made
parenting a collision exemption at every sampled frame. Re-rendering could
not compensate for the missing physical check: all view checks also passed.

Evidence is preserved without rewriting the old result:

- [Independent construction, six intersecting face pairs and exact positions](../../../evaluation/chair-hinge-contact-audit/20261126T111258Z/collision-proof.json)
- [Probe command, mutation SHA and original grading metadata](../../../evaluation/chair-hinge-contact-audit/20261126T111258Z/probe.json)
- [Original complete reward-1 run](../runs/20261126T111304Z-audit-negative-hinge-contact-probe/run.json)
- [Original 15-check metrics](../runs/20261126T111304Z-audit-negative-hinge-contact-probe/verifier/metrics.json)

The fix removes parent-based exemptions. At each of the original 31 sampled
poses, all included mesh pairs are checked. A pair whose world AABBs have
no positive overlap along at least one axis is surface contact rather than
volumetric overlap; a one-micrometre numerical tolerance handles the
reference bars' coplanar touching faces. Every remaining pair is checked by
the existing evaluated-mesh BVH overlap test. The reference geometry,
animation, images, dimensions and scoring thresholds are unchanged.

Independent scene-level checks before publication found no collisions in
the reference and detected the constructed collision. Full current-source
Oracle/NOP and negative runs are linked from [current validation](VALIDATION.md).
The new permanent case is `chair-shared-hinge-collision`; preparation lives
in `tools/prepare_mutations.py`, and it is required by the shared
`NEGATIVE_CASES` registry in `tools/sanity_check.py`.

The old checker SHA256 was
`3f211e77a364e619d57c43a0041965efaa7641c591114a4985be6c7b0ed5ec47`.
The repaired checker SHA256 is
`93626c3f9eaa7ce463a5f05ca6e53f76211787d1fddd282fd33d7575442da27c`.
This audit is a geometric negative test, never a NOP or a model attempt.
