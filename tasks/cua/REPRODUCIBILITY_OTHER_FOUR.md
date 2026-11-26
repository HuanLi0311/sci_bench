# Four-task CUA delivery

Tasks: `crate-lookdev`, `folding-chair`, `rainroom`, `toy-car`.

The authoritative verification commands are:

```sh
cd /mnt/d/????/ic-bench/tasks/cua
python3 tools/sanity_check.py crate-lookdev folding-chair rainroom toy-car
```

The final run set has Oracle reward 1, true NOP reward 0, and all prepared negative cases reward 0 for each task. The current run and source hashes are in `run-index.json`, `current-validation.json`, and each task's `authoring/runs/`.

Docker image IDs and digests used by the final runs are in `RUNTIME_IMAGE_IDS.json`. The images are expected to be available in the WSL Docker daemon; this source package does not silently rebuild a different base image.

`rainroom/tests/rerender.py` uses 16 samples for the verifier's anti-cheat rerender and `rainroom/tests/grade.py` allows 1200 seconds for that verifier subprocess. The authenticity and structure thresholds are unchanged; this fixes a false infrastructure rejection caused by the former 64-sample/900-second combination.

GUI status is explicit in `GUI_TRAJECTORY_STATS.md`: no recovered model trajectory contains verified GUI input events. Terminal traces and verifier/oracle runs are not counted as GUI trajectories.
