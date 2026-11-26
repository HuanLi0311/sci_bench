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
