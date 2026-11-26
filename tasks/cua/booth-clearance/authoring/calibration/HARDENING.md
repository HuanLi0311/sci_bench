# Booth-clearance hardening audit

This task is the current validation priority. The original reference `.blend`, renders and materials are retained. The Oracle publisher's Linux line endings were fixed and it now creates the output directory before copying files.

| Finding | Change | Evidence required |
|---|---|---|
| Only the entrance image was authenticated | Independently render entrance and top views; compare each RGB channel | Reference Oracle passes; substituted top view fails `R_all_render_authenticity` |
| Moving the entrance marker could redefine the clearance test | Validate its position at x=-3 m, width 2.4 m and centred y=0 before measuring both cabinets | Moved-marker submission fails `R05_entrance_clearance` |
| Shell and other products were omitted from visibility occluders | Build world-space BVHs for all meshes except the marker, skipping only the target product for each ray | Reference visibility passes; additional occluders can fail `R07_visibility` |
| Furniture/product dimensions were not checked | Check table dimensions and vertical height within 20 mm; allow floor-plan rotation | Reference passes; resized product fails `R_furniture_product_sizes` |
| Products could float above their plinths | Check each product's bottom against its plinth top and footprint | Floating product fails `R_product_support` |
| An unused green material slot could pass brand colour | Measure the material actually assigned to the inward-facing back-wall faces and connected to the active material output | White wall retaining unused green slot fails `R08_brand_colour` |
| Empty/name-only placeholders could count as required objects | Require actual nonempty meshes for the shell, furniture, products, marker and all three plinths | Missing/empty parts fail scene extraction |
| Failed Blender calls could leave stale files | Unique work directories, checked process exit codes, disabled embedded auto-execution, complete subprocess logs | Invalid scenes cannot reuse a prior report/render |

The standard-library regression check is:

```bash
python3 tasks/cua/booth-clearance/tests/test_rubric.py
```

It uses geometry extracted from the real reference Oracle scene. It checks the reference, a resized product, a floating product and a missing plinth. This is a geometry regression check; only an actual full verifier run proves an Oracle reward.

Final raw records and their exact source hashes are indexed in [RUNS.md](../../../RUNS.md). The recording protocol and definitions are in [EVIDENCE.md](../../../EVIDENCE.md). Development and interrupted runs remain visible, with their original logs and outcomes. A reward file after an execution error does not establish a solved/unsolved model trial. New model success is never inferred from the reference Oracle.

## Captured structural regressions

The frozen verifier used by these runs is recorded in `evaluation/20261126T081627Z-final-booth-clearance` (relative to `tasks/cua`). All four completed as normal grading, each with reward 0 and a decisive matching rubric failure:

| Mutation | Evidence | Decisive failure |
|---|---|---|
| Entrance marker moved | [run](../runs/20261126T081628Z-final-negative-booth-moved-entrance-marker/run.json) | `R05_entrance_clearance` |
| Product enlarged | [run](../runs/20261126T081635Z-final-negative-booth-product-scaled/run.json) | `R_furniture_product_sizes`, `R_product_support` |
| Product floating above plinth | [run](../runs/20261126T081642Z-final-negative-booth-product-floating/run.json) | `R_product_support` |
| White back wall with unused green slot retained | [run](../runs/20261126T081650Z-final-negative-booth-unused-brand-slot/run.json) | `R08_brand_colour`, measured delta 223.992/255 |

The grader skips expensive authenticity renders once a prerequisite already makes reward 1 impossible. This does not relax acceptance of any submission: this task has two normal checks and requires at least 80%, so both must pass. The log explicitly records the skip. Valid scenes and submitted-image substitutions still execute full independent rendering.

## Discovered counterexample and structure fix

The real [constant-top-view run](../runs/20261126T082402Z-final-negative-secondary-render-substitution/run.json) unexpectedly scored **1**, despite replacing the top image with constant RGB (209, 211, 210). Its RGB SSIM was 0.9176626638, above 0.90. This is a confirmed failure of the previous grader, retained without changing its original metrics or reward.

The current grader adds `R_render_structure`: after a 2-pixel Gaussian blur, it divides the L2 difference of RGB image gradients by the trusted render's gradient L2 norm. A constant replacement scores exactly 1; the allowed error is at most 0.60. It still also requires RGB SSIM >=0.90. Twenty captured valid render pairs score 0.093?0.459; the same discovered exploit scores 1.000. Reproduce the component regression with `python3 tasks/cua/tools/check_render_metric.py`; the report includes both image hashes in `evaluation/gradient-regression.json` relative to `tasks/cua`.

Earlier 19-check Oracle results remain valid for their snapshots, but do not prove the current 20-check verifier. The current verifier requires a fresh Oracle/NOP and the same five full negative cases, with matching hashes. The QC gate now requires every prepared negative case to be rejected; one unexpectedly accepted negative prevents a pass.
