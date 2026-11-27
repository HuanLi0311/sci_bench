# Recorded model baselines: rainroom

Terminal baselines are explicitly gui_compliant=false. Execution status and artifact score are separate; API/setup failures are not model capability failures. No unrun result is invented.

| Attempt | Execution | Artifact reward | Agent items / requests | Raw evidence |
|---|---|---:|---|---|
| 20261126T111524Z-codex-terminal-gpt-6.1-sol-high | task-failure | 0 | 68 / 64 | [config](../runs/20261126T111524Z-model-codex-terminal/config.json), [log](../runs/20261126T111524Z-model-codex-terminal/trial.log), [inventory](../model-attempts.json) |
| 20261127T032512Z-model-computer-1-gui | interrupted-by-operator | 0 | 149 / 149 | [config](../runs/20261127T032512Z-model-computer-1-gui/config.json), [log](../runs/20261127T032512Z-model-computer-1-gui/trial.log), [inventory](../model-attempts.json) |

Raw Codex counts use assistant-message or function_call/custom_tool_call response items; tool requests count call items only. User/system messages, reasoning-only items, results and duplicated CLI representations are excluded. See each attempt's step_definition and independent-step-check.json. Historical ATIF uses its separate stated definition.
