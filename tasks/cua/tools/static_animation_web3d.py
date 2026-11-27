"""Static acceptance checks for the two newly authored task packages."""
from pathlib import Path
import ast,json,re,subprocess,tomllib,zipfile,struct
import xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
results=[]
for name in ['fight-retarget','pose-repair']:
    t=root/name;c=tomllib.loads((t/'task.toml').read_text())
    assert c['schema_version']=='1.4' and c['verifier']['environment_mode']=='separate'
    assert c['verifier']['environment']['network_mode']=='no-network'
    assert c['environment']['cpus']==4 and c['environment']['memory_mb']==8192
    instruction=(t/'instruction.md').read_text();assert instruction.endswith('You have 7200 seconds to complete this task.\n')
    required=['task.toml','instruction.md','README.md','environment/Dockerfile','environment/materials/LICENSE.txt','tests/Dockerfile','tests/grade.py','tests/test.sh','solution/solve.sh','authoring/provenance/SOURCES.md']
    assert all((t/f).is_file() for f in required)
    for f in list((t/'environment').rglob('Dockerfile'))+[t/'tests/Dockerfile']:
        assert re.search(r'^FROM .+@sha256:[0-9a-f]{64}$',f.read_text(),re.M),f
    for f in t.rglob('*.py'):
        if 'runs' not in f.parts:ast.parse(f.read_text(),filename=str(f))
    for f in t.rglob('*.sh'):
        if 'runs' not in f.parts:
            assert b'\r\n' not in f.read_bytes(),f
            subprocess.run(['bash','-n',str(f)],check=True)
    for f in t.rglob('*.cjs'):
        if 'runs' not in f.parts:subprocess.run(['node','--check',str(f)],check=True)
    if name=='fight-retarget':
        m=t/'environment/materials'
        assert (m/'stage.pdf').read_bytes().startswith(b'%PDF-')
        with zipfile.ZipFile(m/'bone_mapping.xlsx') as z:
            assert z.testzip() is None
            xml=ET.fromstring(z.read('xl/worksheets/sheet1.xml'));ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            cells={c.attrib['r']:c for c in xml.findall('.//s:c',ns)};rows=json.loads((m/'bone_mapping.json').read_text())
            assert len(rows)==44
            for i,r in enumerate(rows,2):
                assert cells[f'D{i}'].attrib.get('t','n')=='n'
                assert abs(float(cells[f'D{i}'].find('s:v',ns).text)-r['length'])<1e-12
        assert (m/'fighters.blend').read_bytes()[:7]==b'BLENDER'
        assert (t/'solution/fight.blend').read_bytes()[:7]==b'BLENDER'
        assert all((t/'solution'/f'render_key_{i:02d}.png').read_bytes().startswith(b'\x89PNG') for i in range(1,5))
    else:
        assert c['environment']['network_mode']=='allowlist' and c['environment']['allowed_hosts']==['pose-service']
        assert c['artifacts'][1]['service']=='pose-service'
        assert 'COPY . ' not in (t/'environment/Dockerfile').read_text()
        assert (t/'environment/service/fixture.json').read_bytes()==(t/'tests/fixture.json').read_bytes()
        glb=(t/'environment/materials/avatar.glb').read_bytes();assert struct.unpack_from('<III',glb)==(0x46546c67,2,len(glb))
    results.append(dict(task=name,static='pass'))
print(json.dumps(results,indent=2))
