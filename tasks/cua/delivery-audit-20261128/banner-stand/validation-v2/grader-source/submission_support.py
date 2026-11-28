"""Validate manifest coverage against image datablocks used by the scene."""
from pathlib import PurePosixPath


def manifest_error(man, scene, renders, cameras):
    if man.get('schemaVersion') != 1 or man.get('units') != 'meters':
        return 'schemaVersion must be 1 and units meters'
    assets = man.get('assets', [])
    if not assets or any(not a.get('source') or not a.get('license') for a in assets):
        return 'every asset needs source and license'
    paths = [str(a.get('path', '')).replace('\\', '/') for a in assets]
    if len(set(paths)) != len(paths) or any(not p or PurePosixPath(p).is_absolute()
                                          or '..' in PurePosixPath(p).parts for p in paths):
        return 'asset paths must be unique relative paths without traversal'
    textures = {PurePosixPath(p).name for a, p in zip(assets, paths) if a.get('role') == 'texture'}
    images = {PurePosixPath(i['filepath'].replace('\\', '/')).name
              for i in scene.get('images', []) if i.get('filepath')}
    if not images or not images <= textures:
        return f'unlicensed/unlisted scene images: {sorted(images - textures)}'
    rows = man.get('renders', [])
    if len(rows) != len(renders) or {r.get('file') for r in rows} != set(renders):
        return 'all three render entries required exactly once'
    for row in rows:
        name = row['file']
        if row.get('camera') != cameras[name] or row.get('resolution') != list(renders[name]) or row.get('samples') != 64:
            return f'incorrect render metadata: {name}'
    return None
