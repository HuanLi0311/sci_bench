"""One-time, reviewable patch of the two purchased environments."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def edit(path, old, new):
    s = path.read_text(encoding='utf-8')
    assert old in s, (path, old[:100])
    path.write_text(s.replace(old, new), encoding='utf-8', newline='\n')

for task in ('banner-stand', 'drawer-cabinet'):
    tests = ROOT / task / 'tests'
    p = tests / 'check_scene.py'
    edit(p, 'import bpy\n', "import bpy\nimport os\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\nfrom scene_support import used_materials, material_report, visible_mesh, component_dimensions, motion_error\nfrom mathutils import Matrix, Vector\n")
    edit(p, '"materials": [m.name if m else None for m in ob.data.materials]', '"materials": [m.name if m else None for m in ob.data.materials]') if False else None
    edit(p, 'entry["materials"] = [m.name if m else None for m in ob.data.materials]', 'entry["materials"] = used_materials(ob)\n            entry["visible_mesh"] = visible_mesh(ob)\n            entry["components_mm"] = component_dimensions(ob)')
    s = p.read_text()
    start = s.index('    for mat in bpy.data.materials:')
    end = s.index('    for img in bpy.data.images:', start)
    s = s[:start] + '''    used = {m for ob in report['objects'].values() for m in ob.get('materials', [])}
    for mat in bpy.data.materials:
        if mat.name in used:
            report['materials'][mat.name] = material_report(mat)

''' + s[end:]
    p.write_text(s, encoding='utf-8', newline='\n')
    p = tests / 'grade.py'
    edit(p, 'from render_compare import gradient_error', 'from render_compare import gradient_error\nfrom submission_support import manifest_error')
    s = p.read_text(); start = s.index('            assets = man.get("assets", [])'); end = s.index('        except Exception as exc:', start)
    cameras = ({'render_front.png':'cam_front', 'render_folded.png':'cam_folded', 'render_three_quarter.png':'cam_three_quarter'} if task == 'banner-stand' else {'render_day.png':'cam_front34', 'render_night.png':'cam_front34', 'render_detail.png':'cam_detail'})
    s = s[:start] + f'''            error = manifest_error(man, scene, RENDERS, {cameras!r})
            man_ok = error is None
            m_detail = error or 'all scene images licensed; render metadata matches'
''' + s[end:]
    # Do not spend 5 renders on a structurally invalid submission.
    s = s.replace('if scene_ok and os.path.exists(blend):', 'if scene_ok and os.path.exists(blend) and all(c["pass"] for c in CHECKS if c["level"] == "must"):')
    p.write_text(s, encoding='utf-8', newline='\n')

p = ROOT/'banner-stand/tests/check_scene.py'
edit(p, 'return {"area": area, "bbox": [lo, hi]}', '''# A full-sheet map has a single spatial correspondence, so overlapping,
    # shuffled or tiled islands cannot pass using total area and bounds alone.
    pts = [ob.matrix_world @ v.co for v in me.vertices]
    xmin, xmax = min(p.x for p in pts), max(p.x for p in pts)
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    error = 1.0
    if xmax > xmin and zmax > zmin:
        error = max(max(abs(uv.data[li].uv.x - (xmax - pts[me.loops[li].vertex_index].x)/(xmax-xmin)),
                        abs(uv.data[li].uv.y - (pts[me.loops[li].vertex_index].z-zmin)/(zmax-zmin)))
                    for poly in me.polygons for li in poly.loop_indices)
    return {"area": area, "bbox": [lo, hi], "mapping_error": error}''')
edit(p, '"parent": leg.parent.name if leg else None,', '"parent": leg.parent.name if leg and leg.parent else None,')
edit(p, '        for deg in (0, 7, 14):', '''        set_hinge(0)
        initial = leg.matrix_world.copy()
        pivot = hinge.matrix_world.translation.copy()
        for deg in (0, 7, 14):''')
edit(p, '                "overlap": hits(', '''                "motion_error_mm": motion_error(leg, initial, Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(deg), 4, 'X') @ Matrix.Translation(-pivot)),
                "overlap": hits(''')
p = ROOT/'banner-stand/tests/grade.py'
edit(p, 'missing = [k for k, v in present.items() if not v]', 'missing = [k for k in PARTS + ["hinge_rear"] if not present.get(k)]\n    mesh_ok = all(objs.get(n, {}).get("visible_mesh") for n in PARTS)' )
edit(p, 'not missing and parent_ok,', 'not missing and parent_ok and mesh_ok,')
edit(p, 'and aspect_ok and max(graphic["size"]) <= 2048)', 'and aspect_ok and max(graphic["size"]) <= 2048\n             and uv.get("mapping_error", 1) <= 0.005)')
edit(p, '    imgs = []\n    for m in (scene.get("materials") or {}).values():\n        imgs.extend(m.get("images") or [])', '''    imgs = []
    for name in objs.get('canvas', {}).get('materials', []):
        imgs.extend((scene.get('materials') or {}).get(name, {}).get('images') or [])''')
edit(p, 'states and all(v == 0 for v in collision.values()),', 'set(states) == {"0", "7", "14"} and all(v == 0 for v in collision.values())\n        and all(v.get("motion_error_mm", 999) <= 2 for v in states.values()),')
start = p.read_text().index('    metal = max('); end=p.read_text().index('    path_imgs = ', start)
s=p.read_text(); s=s[:start]+'''    mats = scene.get('materials') or {}
    metal_ok = all(any((mats.get(m, {}).get('metallic') or 0) >= 0.8
                       for m in objs.get(n, {}).get('materials', []))
                   for n in ('base', 'mast_left', 'mast_right', 'top_bar', 'leg_rear'))
    canvas_ok = all(mats.get(m, {}).get('images') and
                    0.55 <= (mats.get(m, {}).get('roughness') or 0) <= 0.85
                    for m in objs.get('canvas', {}).get('materials', []))
    add('R08_materials', 'must', metal_ok and canvas_ok, f'frame={metal_ok} canvas={canvas_ok}')
    expected = {'base': [800, 120, 50], 'mast_left': [40, 40, 1910],
                'mast_right': [40, 40, 1910], 'top_bar': [800, 40, 40]}
    dimensions = {}
    for n, target in expected.items():
        box = objs.get(n, {}).get('aabb')
        dimensions[n] = bool(box) and all(abs((box[1][i]-box[0][i])*1000-target[i]) <= 3 for i in range(3))
    add('R_frame_parts', 'must', all(dimensions.values()), dimensions)

'''+s[end:];p.write_text(s,encoding='utf-8',newline='\n')
p=ROOT/'banner-stand/tests/rerender.py'
edit(p, '    if img is not None:\n        checker(img)', '    if img is not None:\n        original = np.array(img.pixels[:], dtype=np.float32)\n        checker(img)\n        img.update()')
edit(p, '    set_hinge(25)', '    if img is not None:\n        img.pixels.foreach_set(original)\n        img.update()\n    set_hinge(25)')

p=ROOT/'drawer-cabinet/tests/check_scene.py'
edit(p, '    sc = bpy.context.scene\n', '    sc = bpy.context.scene\n    reset_pose()\n')
edit(p, '        others = [o for o in objs(CARCASS) if o.name != "carcass_back"]', '        others = objs(CARCASS)')
edit(p, '    door_rep = {"parent": door.parent.name if door else None}', '    door_rep = {"parent": door.parent.name if door and door.parent else None}')
edit(p, '        for deg in (0, 55, 110):', '''        door_rep['motion_error_mm'] = {}
        reset_pose()
        initial = door.matrix_world.copy()
        pivot = hinge.matrix_world.translation.copy()
        for deg in (0, 55, 110):''')
edit(p, '            door_rep["overlap"][str(deg)] = ', '''            expected = Matrix.Translation(pivot) @ Matrix.Rotation(-math.radians(deg), 4, 'Z') @ Matrix.Translation(-pivot)
            door_rep['motion_error_mm'][str(deg)] = motion_error(door, initial, expected)
            door_rep["overlap"][str(deg)] = ''')
edit(p, '            [door] + objs(["drawer_05"]), objs(CARCASS))', '            [door] + objs(["drawer_05"]), objs(CARCASS)) + overlaps([door], objs(["drawer_05"]))')
p=ROOT/'drawer-cabinet/tests/grade.py'
edit(p, 'missing = [k for k, v in present.items() if not v]', 'missing = [k for k in CARCASS + DRAWERS + SLIDES + ["door_right", "hinge_right"] if not present.get(k)]')
edit(p, '    parents_ok = all(objs.get(s, {}).get("parent") == d\n                     for s, d in ())', '    meshes_ok = all(objs.get(n, {}).get("visible_mesh") for n in CARCASS + DRAWERS + ["door_right"])\n    empties_ok = all(objs.get(n, {}).get("type") == "EMPTY" for n in SLIDES)')
edit(p, 'not missing and slides_ok and door_ok,', 'not missing and slides_ok and door_ok and meshes_ok and empties_ok,')
edit(p, 'door_clean = bool(door_ov) and all(v == 0 for v in door_ov.values())', 'door_clean = set(door_ov) == {"0", "55", "110"} and all(v == 0 for v in door_ov.values())\n    motion = door.get("motion_error_mm") or {}\n    door_clean &= set(motion) == {"0", "55", "110"} and all(v <= 2 for v in motion.values())')
edit(p, 'f"hinge={hinge_loc} overlap={door_ov}"', 'f"hinge={hinge_loc} overlap={door_ov} motion_error_mm={motion}"')
start=p.read_text().index('    wood_imgs = []');end=p.read_text().index('    imgs = ', start)
s=p.read_text();s=s[:start]+'''    wood_ok, metal_ok = {}, {}
    for n in CARCASS + DRAWERS + ['door_right']:
        assigned = [mats[m] for m in objs.get(n, {}).get('materials', []) if m in mats]
        wood_ok[n] = any({'Base Color', 'Roughness', 'Normal'} <=
                         {i['feeds'] for i in m.get('images', []) if i['size'] == [2048, 2048] and i['packed']}
                         and len({i['name'] for i in m.get('images', [])}) >= 3 for m in assigned)
    for n in DRAWERS + ['door_right'] + [f'foot_{i}' for i in range(1, 5)]:
        metal_ok[n] = any((mats.get(m, {}).get('metallic') or 0) >= 0.9
                          for m in objs.get(n, {}).get('materials', []))
    add('R09_materials', 'must', all(wood_ok.values()) and all(metal_ok.values()),
        f'wood={wood_ok} steel={metal_ok}')
    geometry = {}
    for n in DRAWERS + ['door_right']:
        target = [440, 18, 140] if n in DRAWERS else [450, 18, 746]
        geometry[n] = any(all(abs(d[i]-target[i]) <= 2 for i in range(3))
                          for d in objs.get(n, {}).get('components_mm', []))
        if n in DRAWERS:
            geometry[n] &= any(abs(d[1]-400) <= 2 for d in objs.get(n, {}).get('components_mm', []))
    add('R_panel_fronts', 'must', all(geometry.values()), geometry)

'''+s[end:];p.write_text(s,encoding='utf-8',newline='\n')
edit(p, 'lights_ok = all(len(lights.get(k) or []) >= 1 for k in ("light_day", "light_night"))', 'lights_ok = len(lights.get("light_day") or []) == 3 and len(lights.get("light_night") or []) == 2')
