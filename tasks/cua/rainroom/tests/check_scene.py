"""Extract a scene report from a submitted rainroom."""
import json
import sys

import bpy
from mathutils import Vector

REQUIRED = [
    "rug", "sofa", "sofa_back", "coffee_table", "side_table", "side_table_leg",
    "floor_lamp", "floor_lamp_shade", "table_lamp", "bookshelf",
    "books_1", "books_2", "books_3", "books_4", "vase_01", "vase_02",
    "mug_01", "mug_02", "tray", "candle_01", "candle_02", "bottle",
    "plant_pot", "plant_leaves", "cushion_01", "cushion_02",
]


def world_aabb(ob):
    deps = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(deps)
    me = ev.to_mesh()
    mw = ev.matrix_world
    pts = [mw @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    if not pts:
        return None
    return [[min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)]]


def main():
    out_path = sys.argv[sys.argv.index("--") + 1]
    sc = bpy.context.scene
    rep = {"ok": True, "blender": bpy.app.version_string, "objects": {},
           "meshes": [], "polys_total": 0, "images": [], "cameras": {},
           "collections": {}, "materials": {}}

    for ob in bpy.data.objects:
        e = {"type": ob.type}
        if ob.type == 'MESH':
            a = world_aabb(ob)
            e["aabb"] = a
            e["polys"] = sum(len(p.vertices) - 2 for p in ob.data.polygons)
            e["materials"] = [m.name if m else None for m in ob.data.materials]
            rep["polys_total"] += e["polys"]
            rep["meshes"].append(ob.name)
        elif ob.type == 'CAMERA':
            e["lens"] = float(ob.data.lens)
            e["location"] = list(ob.matrix_world.translation)
            rep["cameras"][ob.name] = e
        elif ob.type == 'LIGHT':
            e["energy"] = float(ob.data.energy)
            e["collections"] = [c.name for c in ob.users_collection]
        rep["objects"][ob.name] = e

    for c in bpy.data.collections:
        rep["collections"][c.name] = {
            "objects": [o.name for o in c.objects],
            "lights": [o.name for o in c.objects if o.type == 'LIGHT'],
        }

    for mat in bpy.data.materials:
        info = {"transmission": None, "metallic": None, "roughness": None,
                "images": []}
        if mat.use_nodes:
            b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            em = next((n for n in mat.node_tree.nodes if n.type == 'EMISSION'), None)
            if b is not None:
                t = b.inputs.get("Transmission Weight")
                info["transmission"] = float(t.default_value) if t else 0.0
                info["metallic"] = float(b.inputs["Metallic"].default_value)
                info["roughness"] = float(b.inputs["Roughness"].default_value)
                info["alpha"] = float(b.inputs["Alpha"].default_value)
            info["emissive"] = em is not None
        rep["materials"][mat.name] = info

    for img in bpy.data.images:
        if img.name in ("Render Result", "Viewer Node"):
            continue
        rep["images"].append({"name": img.name, "packed": bool(img.packed_file),
                              "filepath": img.filepath, "size": list(img.size)})

    shell = rep["objects"].get("room_shell", {}).get("aabb")
    if shell:
        rep["room_size"] = [shell[1][i] - shell[0][i] for i in range(3)]

    rep["required"] = {n: (n in bpy.data.objects) for n in REQUIRED}

    with open(out_path, "w") as fh:
        json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import traceback
        traceback.print_exc()
        p = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp/scene.json"
        with open(p, "w") as fh:
            json.dump({"ok": False, "error": str(exc)}, fh)
        sys.exit(2)
