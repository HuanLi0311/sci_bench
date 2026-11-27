"""Import a submitted .glb into an empty scene and report what came back.

    blender -b --python check_glb.py -- <file.glb> <out.json>
"""
import json
import sys

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    glb, out = argv[0], argv[1]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    report = {"ok": True, "objects": {}, "meshes": [], "materials": [],
              "images": [], "polys_total": 0}
    for ob in bpy.data.objects:
        entry = {"type": ob.type, "parent": ob.parent.name if ob.parent else None,
                 "location": list(ob.matrix_world.translation)}
        if ob.type == 'MESH':
            deps = bpy.context.evaluated_depsgraph_get()
            ev = ob.evaluated_get(deps)
            me = ev.to_mesh()
            tris = sum(len(p.vertices) - 2 for p in me.polygons)
            ev.to_mesh_clear()
            entry["polys"] = tris
            entry["materials"] = [m.name if m else None for m in ob.data.materials]
            report["polys_total"] += tris
            report["meshes"].append(ob.name)
        report["objects"][ob.name] = entry
    report["materials"] = sorted({m.name for m in bpy.data.materials})
    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        report["images"].append({"name": img.name, "size": list(img.size),
                                 "packed": bool(img.packed_file is not None),
                                 "filepath": img.filepath})
    with open(out, "w") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        out = sys.argv[sys.argv.index("--") + 2] if "--" in sys.argv else "/tmp/glb.json"
        with open(out, "w") as fh:
            json.dump({"ok": False, "error": "see stderr"}, fh)
        sys.exit(2)
