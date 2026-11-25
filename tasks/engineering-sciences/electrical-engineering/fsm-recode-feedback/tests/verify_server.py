"""Verifier side of the feedback loop. Runs on the host, never inside the
agent container: the stimulus, the golden model and the thresholds all live
here, so the agent can query the verdict but cannot read how it is reached.

POST /verify  {"trial": "<id>", "source": "<verilog text>"}
  -> {"equiv": bool, "mismatches": int, "cells": int, "levels": int,
      "calls_used": int, "calls_left": int}

Budget is per trial id and persisted to disk.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(HERE, "reference", "golden.v")
TB = os.path.join(HERE, "tb.v")
BUDGET_FILE = os.environ.get("AMP_BUDGET_FILE", os.path.join(HERE, "budget.json"))
CALL_BUDGET = int(os.environ.get("VERIFY_BUDGET", "12"))

CELL_MAX = 420
LEVEL_MAX = 57

_lock = threading.Lock()


def _budget():
    if os.path.exists(BUDGET_FILE):
        try:
            with open(BUDGET_FILE, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass
    return {}


def _save(d):
    tmp = BUDGET_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
    os.replace(tmp, BUDGET_FILE)


def _run(cmd, timeout=600):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def verify(source):
    with tempfile.TemporaryDirectory() as td:
        dut = os.path.join(td, "dut.v")
        with open(dut, "w", encoding="utf-8") as fh:
            fh.write(source)
        exe = os.path.join(td, "sim")

        cc = _run(["iverilog", "-o", exe, TB, GOLD, dut])
        if cc.returncode != 0:
            return {"equiv": False, "mismatches": -1, "cells": -1, "levels": -1,
                    "error": "compile failed", "log": (cc.stderr or cc.stdout)[-600:]}

        try:
            sim = _run([exe], timeout=180)
        except subprocess.TimeoutExpired:
            return {"equiv": False, "mismatches": -1, "cells": -1, "levels": -1,
                    "error": "simulation timed out"}

        m = re.search(r"MISMATCHES=(\d+)", sim.stdout)
        mismatches = int(m.group(1)) if m else -1

        syn = _run(["yosys", "-p",
                    "read_verilog %s; synth -top fsm; stat; ltp" % dut])
        cm = re.search(r"Number of cells:\s+(\d+)", syn.stdout)
        lm = re.search(r"length=(\d+)", syn.stdout)
        cells = int(cm.group(1)) if cm else -1
        levels = int(lm.group(1)) if lm else -1

        ok = (mismatches == 0 and 0 < cells <= CELL_MAX and 0 < levels <= LEVEL_MAX)
        out = {"equiv": mismatches == 0, "mismatches": mismatches,
               "cells": cells, "levels": levels, "pass": ok}
        if mismatches != 0 and mismatches > 0:
            out["note"] = "output differs from the reference machine"
        return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.path != "/verify":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", "0"))
        try:
            req = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            self.send_error(400)
            return

        trial = str(req.get("trial", "anonymous"))
        source = req.get("source", "")

        with _lock:
            b = _budget()
            used = int(b.get(trial, 0))
            if used >= CALL_BUDGET:
                body = json.dumps({"error": "verify budget exhausted",
                                   "calls_used": used, "calls_left": 0}).encode()
                self.send_response(429)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

        result = verify(source)

        with _lock:
            b = _budget()
            used = int(b.get(trial, 0)) + 1
            b[trial] = used
            _save(b)

        result["calls_used"] = used
        result["calls_left"] = CALL_BUDGET - used
        body = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8899
    srv = HTTPServer(("0.0.0.0", port), Handler)
    print("verify server on :%d, budget %d calls per trial" % (port, CALL_BUDGET))
    srv.serve_forever()


if __name__ == "__main__":
    main()
