from pathlib import Path
import hashlib,json,sys
root=Path(__file__).resolve().parent
manifest=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
errors=[]
for item in manifest['files']:
 p=root/item['path']
 if not p.is_file() or p.stat().st_size!=item['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
  errors.append(item['path'])
print('PASS' if not errors else 'FAIL',len(manifest['files']),'files')
for p in errors:print(p)
sys.exit(bool(errors))
