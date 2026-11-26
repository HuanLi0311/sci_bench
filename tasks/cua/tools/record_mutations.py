"""Grade the latest prepared adversarial inputs, retaining full run evidence."""
import argparse
from concurrent.futures import ThreadPoolExecutor

from record_baselines import ROOT, record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--jobs", type=int, default=3, choices=range(1, 4))
    options = parser.parse_args()
    jobs = []
    for task in ("crate-lookdev", "booth-clearance", "folding-chair", "rainroom", "toy-car"):
        mutations = {}
        for path in sorted((ROOT / task / "authoring" / "runs").glob("*-mutation-*/submission")):
            name = path.parent.name.split("-mutation-", 1)[1]
            mutations[name] = path
        for name, path in mutations.items():
            jobs.append((task, "negative-" + name, options.label, path))
    if len(jobs) != 9:
        raise SystemExit(f"Expected 9 prepared mutation inputs, found {len(jobs)}; run prepare_mutations.py first")
    with ThreadPoolExecutor(max_workers=options.jobs) as pool:
        list(pool.map(lambda args: record(*args), jobs))
