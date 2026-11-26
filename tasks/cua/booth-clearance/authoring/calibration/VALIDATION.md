# Completed 20-check booth-clearance snapshot (superseded)

Checked at 2026-11-26T08:52:53.529466+00:00. These records use the then-current 20-check verifier. A subsequent real-model review found an Empty-helper false rejection; the current 21-check verifier is being revalidated.

| Case | Reward | Raw evidence |
|---|---:|---|
| oracle | 1 | [run](../runs/20261126T083757Z-final-oracle/run.json), [metrics](../runs/20261126T083757Z-final-oracle/verifier/metrics.json), [reward](../runs/20261126T083757Z-final-oracle/verifier/reward.txt) |
| nop | 0 | [run](../runs/20261126T084447Z-final-nop/run.json), [metrics](../runs/20261126T084447Z-final-nop/verifier/metrics.json), [reward](../runs/20261126T084447Z-final-nop/verifier/reward.txt) |
| negative-secondary-render-substitution | 0 | [run](../runs/20261126T084454Z-final-negative-secondary-render-substitution/run.json), [metrics](../runs/20261126T084454Z-final-negative-secondary-render-substitution/verifier/metrics.json), [reward](../runs/20261126T084454Z-final-negative-secondary-render-substitution/verifier/reward.txt) |
| negative-booth-moved-entrance-marker | 0 | [run](../runs/20261126T083730Z-final-negative-booth-moved-entrance-marker/run.json), [metrics](../runs/20261126T083730Z-final-negative-booth-moved-entrance-marker/verifier/metrics.json), [reward](../runs/20261126T083730Z-final-negative-booth-moved-entrance-marker/verifier/reward.txt) |
| negative-booth-product-scaled | 0 | [run](../runs/20261126T083737Z-final-negative-booth-product-scaled/run.json), [metrics](../runs/20261126T083737Z-final-negative-booth-product-scaled/verifier/metrics.json), [reward](../runs/20261126T083737Z-final-negative-booth-product-scaled/verifier/reward.txt) |
| negative-booth-product-floating | 0 | [run](../runs/20261126T083743Z-final-negative-booth-product-floating/run.json), [metrics](../runs/20261126T083743Z-final-negative-booth-product-floating/verifier/metrics.json), [reward](../runs/20261126T083743Z-final-negative-booth-product-floating/verifier/reward.txt) |
| negative-booth-unused-brand-slot | 0 | [run](../runs/20261126T083750Z-final-negative-booth-unused-brand-slot/run.json), [metrics](../runs/20261126T083750Z-final-negative-booth-unused-brand-slot/verifier/metrics.json), [reward](../runs/20261126T083750Z-final-negative-booth-unused-brand-slot/verifier/reward.txt) |

The discovered prior SSIM-only counterexample remains [reward 1](../runs/20261126T082402Z-final-negative-secondary-render-substitution/verifier/reward.txt). The same submitted image is rejected by the current structure check (error 1.000). Oracle structure errors: entrance 0.458844, top 0.265647.

Model evidence: the first new terminal attempt is an infrastructure failure (missing runtime companion, all tool executions failed); its full raw sessions are retained. The corrected runtime passed a real-command smoke check, and the second isolated terminal trial is still running. Final model outcome and step counts will be added after it terminates. This report does not claim GUI/CUA model success.
