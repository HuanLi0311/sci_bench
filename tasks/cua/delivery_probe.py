from pathlib import Path
import json, subprocess, sys, shutil

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / 'delivery-audit-20261128'
AUDIT.mkdir(exist_ok=True)

def run(args, name, timeout=3600):
    with (AUDIT / (name + '.log')).open('w') as log:
        p = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    print(name, p.returncode, flush=True)
    if p.returncode:
        print((AUDIT / (name + '.log')).read_text()[-3000:], flush=True)
    return p.returncode

if sys.argv[1] == 'probe':
    task = ROOT / 'drawer-cabinet'
    out = AUDIT / 'static-door'
    shutil.copytree(task / 'solution', out, dirs_exist_ok=True)
    script = AUDIT / 'static-door.py'
    script.write_text('''import bpy,sys
door=bpy.data.objects['door_right']
target=bpy.data.objects.new('static_door_target',None)
bpy.context.scene.collection.objects.link(target)
target.matrix_world=door.matrix_world.copy()
c=door.constraints.new('COPY_TRANSFORMS')
c.target=target
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
''')
    run(['docker','run','--rm','--network','none','--entrypoint','blender','-v',f'{AUDIT}:/audit',
         'cua-qc-drawer-cabinet-tests','--disable-autoexec','-b','/audit/static-door/drawer_cabinet.blend',
         '-P','/audit/static-door.py','--','/audit/static-door/drawer_cabinet.blend'], 'prepare-static-door')
    logs = AUDIT / 'pre-static-door'; logs.mkdir(exist_ok=True)
    run(['docker','run','--rm','--network','none','--cpus','4','--memory','8g','--entrypoint','bash',
         '-v',f'{out}:/app/out:ro','-v',f'{logs}:/logs/verifier',
         'cua-qc-drawer-cabinet-tests','/tests/test.sh'], 'pre-static-door', 3600)
elif sys.argv[1] == 'inspect':
    run(['docker','run','--rm','--network','none','--entrypoint','bash',
         'blender-bench:gui','-lc',
         'cat /usr/local/bin/entrypoint /usr/local/bin/start-desktop; ls /opt/blender; du -sh /opt/blender; command -v Xvfb; cat /etc/os-release'], 'base-inspect')
