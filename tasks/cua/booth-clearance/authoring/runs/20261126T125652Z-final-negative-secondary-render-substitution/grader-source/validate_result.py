"""Reject incomplete/error verifier output before publishing a candidate reward."""
import json
import sys


def validate(metrics, status):
    checks = metrics.get("checks", [])
    if status not in (0, 1) or metrics.get("reward") != (1 if status == 0 else 0):
        raise ValueError("exit/reward disagreement")
    if len(checks) != 22 or len({c["id"] for c in checks}) != 22:
        raise ValueError("incomplete check set")
    if any(type(c.get("pass")) is not bool for c in checks):
        raise ValueError("invalid verdict")
    if any(c["id"] == "R_verifier_error" or "timed out" in c.get("detail", "").lower() for c in checks):
        raise ValueError("verifier exception/timeout")
    must = all(c["pass"] for c in checks if c["level"] == "must")
    critical = all(c["pass"] for c in checks if c["level"] == "critical")
    normal = [c["pass"] for c in checks if c["level"] == "normal"]
    expected = int(must and critical and sum(normal) / max(1, len(normal)) >= 0.8)
    if expected != metrics["reward"]:
        raise ValueError("check/reward disagreement")


if __name__ == "__main__":
    try:
        with open(sys.argv[1], encoding="utf-8") as stream:
            metrics = json.load(stream)
        validate(metrics, int(sys.argv[2]))
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Invalid verifier result: {error}", file=sys.stderr)
        sys.exit(2)
