#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json /logs/verifier/metrics.json
# Any Python/runtime failure is infrastructure failure: no reward is written.
python3 /tests/grade.py "${1:-/app/out}" > /logs/verifier/metrics.tmp.json 2>/logs/verifier/stderr.log
python3 - <<'PY'
import json,os
from pathlib import Path
p=Path('/logs/verifier');d=json.loads((p/'metrics.tmp.json').read_text())
assert type(d['reward']) is int and d['reward'] in (0,1)
assert d['checks'] and all(type(c['pass']) is bool for c in d['checks'])
assert d['reward']==int(all(c['pass'] for c in d['checks'] if c['level']!='normal') and (not [c for c in d['checks'] if c['level']=='normal'] or sum(c['pass'] for c in d['checks'] if c['level']=='normal')/len([c for c in d['checks'] if c['level']=='normal'])>=.8))
os.replace(p/'metrics.tmp.json',p/'metrics.json')
(p/'reward.txt').write_text(str(d['reward'])+'\n')
PY
cat /logs/verifier/metrics.json
