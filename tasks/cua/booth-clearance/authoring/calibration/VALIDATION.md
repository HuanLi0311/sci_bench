# Current validation: booth-clearance

Only matching-source records below validate this revision. Historical failures remain separately indexed.

| Case | Reward | Checks | Evidence |
|---|---:|---:|---|
| model-regrade | 1 | 22/22 | [run](../runs/20261126T125640Z-final-model-regrade/run.json), [metrics](../runs/20261126T125640Z-final-model-regrade/verifier/metrics.json) |
| negative-booth-camera-away | 0 | 17/22 | [run](../runs/20261126T125630Z-final-negative-booth-camera-away/run.json), [metrics](../runs/20261126T125630Z-final-negative-booth-camera-away/verifier/metrics.json) |
| negative-booth-closed-opening | 0 | 18/22 | [run](../runs/20261126T125630Z-final-negative-booth-closed-opening/run.json), [metrics](../runs/20261126T125630Z-final-negative-booth-closed-opening/verifier/metrics.json) |
| negative-booth-hidden-secondary-color | 0 | 18/22 | [run](../runs/20261126T125858Z-final-negative-booth-hidden-secondary-color/run.json), [metrics](../runs/20261126T125858Z-final-negative-booth-hidden-secondary-color/verifier/metrics.json) |
| negative-booth-missing-secondary-color | 0 | 18/22 | [run](../runs/20261126T125639Z-final-negative-booth-missing-secondary-color/run.json), [metrics](../runs/20261126T125639Z-final-negative-booth-missing-secondary-color/verifier/metrics.json) |
| negative-booth-moved-entrance-marker | 0 | 18/22 | [run](../runs/20261126T125621Z-final-negative-booth-moved-entrance-marker/run.json), [metrics](../runs/20261126T125621Z-final-negative-booth-moved-entrance-marker/verifier/metrics.json) |
| negative-booth-product-floating | 0 | 18/22 | [run](../runs/20261126T125621Z-final-negative-booth-product-floating/run.json), [metrics](../runs/20261126T125621Z-final-negative-booth-product-floating/verifier/metrics.json) |
| negative-booth-product-scaled | 0 | 17/22 | [run](../runs/20261126T125621Z-final-negative-booth-product-scaled/run.json), [metrics](../runs/20261126T125621Z-final-negative-booth-product-scaled/verifier/metrics.json) |
| negative-booth-unused-brand-slot | 0 | 18/22 | [run](../runs/20261126T125629Z-final-negative-booth-unused-brand-slot/run.json), [metrics](../runs/20261126T125629Z-final-negative-booth-unused-brand-slot/verifier/metrics.json) |
| negative-secondary-render-substitution | 0 | 21/22 | [run](../runs/20261126T125652Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T125652Z-final-negative-secondary-render-substitution/verifier/metrics.json) |
| nop | 0 | 5/22 | [run](../runs/20261126T130004Z-final-nop/run.json), [metrics](../runs/20261126T130004Z-final-nop/verifier/metrics.json) |
| oracle | 1 | 22/22 | [run](../runs/20261126T125639Z-final-oracle/run.json), [metrics](../runs/20261126T125639Z-final-oracle/verifier/metrics.json) |

The model row regrades a preserved terminal-baseline artifact; it is not a new GUI-compliant model run.
Independent verification renders use 16 samples; delivered renders retain their original contract. RGB SSIM/structure thresholds are unchanged.
The companion runtime archive includes exact prebuilt base, environment and verifier images.
