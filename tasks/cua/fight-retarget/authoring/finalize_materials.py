"""Convert authored tables to the verifier's immutable numerical contract."""
from pathlib import Path
import json,csv
root=Path(__file__).resolve().parents[1];mat=root/'environment/materials'
rows=json.loads((mat/'bone_mapping.json').read_text())
parents={r['bone']:r['parent'] or None for r in rows if r['character']=='rig_left'}
events=[]
for r in csv.DictReader((mat/'action_segments.csv').open()):
    if r['target']!='duck_no_contact':events.append(dict(frame=int(r['contact']),attacker=r['attacker'],target=r['target']))
spec=dict(schemaVersion=1,parents=parents,lengths={w:{r['bone']:r['length'] for r in rows if r['character']=='rig_'+w} for w in ['left','right']},events=events,supports=json.loads((mat/'support_phases.json').read_text()),keys=[48,65,235,300])
(root/'tests/spec.json').write_text(json.dumps(spec,indent=2))
