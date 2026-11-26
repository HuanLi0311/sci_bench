"""Replay real captured Oracle images and the discovered constant-image exploit."""
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "booth-clearance/tests/render_compare.py"
spec = importlib.util.spec_from_file_location("render_compare", HELPER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    path = ROOT / "evaluation/gradient-calibration.json"
    calibration = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for case in calibration["measurements"]:
        trusted_path = ROOT / case["run"]
        run = next(p for p in trusted_path.parents if (p / "run.json").exists())
        delivered_path = run / "submission" / trusted_path.name
        forged = case["view"] == "forged top"
        if forged:
            delivered_path = run / "submission/render_top.png"
        trusted = Image.open(trusted_path).convert("RGB")
        delivered = Image.open(delivered_path).convert("RGB").resize(trusted.size, Image.Resampling.LANCZOS)
        score = module.gradient_error(np.asarray(trusted), np.asarray(delivered))
        assert (score > 0.60) if forged else (score <= 0.60), (case["run"], score)
        records.append({
            "trusted": trusted_path.relative_to(ROOT).as_posix(),
            "trusted_sha256": hashlib.sha256(trusted_path.read_bytes()).hexdigest(),
            "delivered": delivered_path.relative_to(ROOT).as_posix(),
            "delivered_sha256": hashlib.sha256(delivered_path.read_bytes()).hexdigest(),
            "gradient_error": score, "expected": "reject" if forged else "accept",
        })
    report = {"helper_sha256": hashlib.sha256(HELPER.read_bytes()).hexdigest(),
              "threshold": 0.60, "blur_radius": 2, "checks": records}
    (ROOT / "evaluation/gradient-regression.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"PASS: {len(records) - 1} captured valid render pairs and the real constant-image exploit")


if __name__ == "__main__":
    main()
