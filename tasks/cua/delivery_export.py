"""Export all Docker layers and source/provenance needed by each independent ZIP."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess, json, tarfile

ROOT=Path(__file__).resolve().parent
AUDIT=ROOT/'delivery-audit-20261128'

def export(task):
    directory=ROOT/task
    runtime=directory/'runtime';runtime.mkdir(exist_ok=True)
    tags=['blender-bench:gui',f'delivery-{task}-env:20261128',f'delivery-{task}-tests:20261128']
    info={}
    for tag in tags:
        data=json.loads(subprocess.check_output(['docker','image','inspect',tag]))[0]
        info[tag]={k:data[k] for k in ['Id','Architecture','Os','RootFS','Created']}
    (runtime/'images.json').write_text(json.dumps(info,indent=2))
    with (runtime/'export.log').open('w') as log:
        subprocess.run(['docker','save','-o',str(runtime/'images.tar'),*tags],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
    print(task,'images exported', (runtime/'images.tar').stat().st_size,flush=True)
    # Verify that the saved archive carries the complete layers for all tags.
    with tarfile.open(runtime/'images.tar') as archive:
        manifest=json.load(archive.extractfile('manifest.json'))
        names=set(archive.getnames())
        assert set(tags)=={tag for item in manifest for tag in item['RepoTags']}
        for item in manifest:
            assert item['Config'] in names
            assert all(layer in names for layer in item['Layers'])
        (runtime/'archive-images.json').write_text(json.dumps(manifest,indent=2))
    # Include the original license notices from the actual shipped image.
    container='delivery-license-'+task
    subprocess.run(['docker','create','--name',container,'--entrypoint','true',tags[1]],check=True,stdout=subprocess.DEVNULL)
    try:
        notices=runtime/'licenses';notices.mkdir(exist_ok=True)
        for source,dest in [('/opt/blender/copyright.txt','blender-copyright.txt'),('/opt/blender/license','blender'),('/usr/share/doc','system-doc')]:
            subprocess.run(['docker','cp',container+':'+source,str(notices/dest)],check=True,stdout=subprocess.DEVNULL,timeout=180)
    finally:
        subprocess.run(['docker','rm',container],check=True,stdout=subprocess.DEVNULL)
    # Original exploit evidence uses the unchanged supplier verifier image.
    if task=='drawer-cabinet':
        container='delivery-original-verifier'
        subprocess.run(['docker','create','--name',container,'--entrypoint','true','cua-qc-drawer-cabinet-tests'],check=True,stdout=subprocess.DEVNULL)
        try:
            destination=AUDIT/'pre-static-door'/'grader-source';destination.mkdir(exist_ok=True)
            subprocess.run(['docker','cp',container+':/tests/.',str(destination)],check=True,stdout=subprocess.DEVNULL)
        finally:
            subprocess.run(['docker','rm',container],check=True,stdout=subprocess.DEVNULL)

if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(export,['banner-stand','drawer-cabinet']))
