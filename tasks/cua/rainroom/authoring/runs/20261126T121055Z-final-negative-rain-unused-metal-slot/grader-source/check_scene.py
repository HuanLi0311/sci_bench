"""Extract a scene report from a submitted rainroom."""
import json
import math
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


def evaluated_triangles(ob):
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ev.to_mesh()
    count = sum(len(p.vertices) - 2 for p in mesh.polygons)
    ev.to_mesh_clear()
    return count


def scalar_input(socket, visited=None):
    """Read constant values without substituting a linked socket's default."""
    if socket is None:
        return None
    if not socket.is_linked:
        value = float(socket.default_value)
        return value if math.isfinite(value) else None
    visited = set() if visited is None else visited
    node = socket.links[0].from_node
    if node in visited:
        return None
    visited.add(node)
    if node.type == 'VALUE':
        value = float(node.outputs[0].default_value)
        return value if math.isfinite(value) else None
    if node.type == 'REROUTE':
        return scalar_input(node.inputs[0], visited)
    return None


def main():
    out_path = sys.argv[sys.argv.index("--") + 1]
    for name in ['room_shell', 'rug', 'sofa', 'sofa_back', 'coffee_table', 'side_table', 'side_table_leg', 'floor_lamp', 'floor_lamp_shade', 'table_lamp', 'bookshelf', 'books_1', 'books_2', 'books_3', 'books_4', 'vase_01', 'vase_02', 'mug_01', 'mug_02', 'tray', 'candle_01', 'candle_02', 'bottle', 'plant_pot', 'plant_leaves', 'cushion_01', 'cushion_02']:
        ob = bpy.data.objects.get(name)
        if ob is None or ob.type != 'MESH' or not ob.data.polygons:
            raise ValueError(f"{name}: required nonempty mesh missing")
        if ob.hide_render or ob.name not in bpy.context.scene.objects:
            raise ValueError(f"{name}: hidden or outside current scene")
        if any(not __import__('math').isfinite(c) for v in ob.data.vertices for c in v.co):
            raise ValueError(f"{name}: non-finite vertex")
    sc = bpy.context.scene
    rep = {"ok": True, "blender": bpy.app.version_string, "objects": {},
           "meshes": [], "polys_total": 0, "images": [], "cameras": {},
           "collections": {}, "materials": {}}

    for ob in bpy.data.objects:
        e = {"type": ob.type}
        if ob.type == 'MESH':
            a = world_aabb(ob)
            e["aabb"] = a
            e["polys"] = evaluated_triangles(ob)
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

    assigned_faces = {}
    for ob in sc.objects:
        if ob.type != 'MESH' or ob.hide_render:
            continue
        ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = ev.to_mesh()
        try:
            for polygon in mesh.polygons:
                if polygon.area <= 1e-12 or polygon.material_index >= len(ev.material_slots):
                    continue
                material = ev.material_slots[polygon.material_index].material
                if material is not None:
                    assigned_faces[material.name] = assigned_faces.get(material.name, 0) + 1
        finally:
            ev.to_mesh_clear()

    for mat in bpy.data.materials:
        info = {"transmission": None, "metallic": None, "roughness": None,
                "images": [], "assigned_faces": assigned_faces.get(mat.name, 0)}
        if mat.use_nodes:
            active, todo = set(), []
            for output in mat.node_tree.nodes:
                if output.type == 'OUTPUT_MATERIAL' and output.is_active_output:
                    todo.extend(link.from_node for link in output.inputs['Surface'].links)
            while todo:
                node = todo.pop()
                if node in active:
                    continue
                active.add(node)
                todo.extend(link.from_node for socket in node.inputs for link in socket.links)
            b = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED' and n in active), None)
            em = next((n for n in mat.node_tree.nodes if n.type == 'EMISSION' and n in active), None)
            if b is not None:
                info["transmission"] = scalar_input(b.inputs.get("Transmission Weight"))
                info["metallic"] = scalar_input(b.inputs["Metallic"])
                info["roughness"] = scalar_input(b.inputs["Roughness"])
                info["alpha"] = scalar_input(b.inputs["Alpha"])
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

    positions = {'rug': [0.0, 0.2, 0.006], 'sofa': [-1.45, 0.55, 0.42], 'sofa_back': [-1.75, 0.55, 0.62], 'coffee_table': [0.1, 0.35, 0.36], 'side_table': [-1.35, -0.9, 0.28], 'side_table_leg': [-1.35, -0.9, 0.14], 'floor_lamp': [1.55, 1.3, 0.9], 'floor_lamp_shade': [1.55, 1.3, 1.72], 'table_lamp': [-1.35, -0.9, 0.42], 'bookshelf': [1.85, 0.1, 0.95], 'books_1': [1.83, -0.35, 0.35], 'books_2': [1.83, -0.15, 0.75], 'books_3': [1.83, 0.05, 1.15], 'books_4': [1.83, 0.25, 1.55], 'vase_01': [0.15, 0.35, 0.5], 'vase_02': [0.35, 0.3, 0.47], 'mug_01': [0.5, 0.45, 0.41], 'mug_02': [0.62, 0.4, 0.41], 'tray': [0.3, 0.55, 0.39], 'candle_01': [0.25, 0.55, 0.45], 'candle_02': [0.37, 0.55, 0.44], 'bottle': [0.05, 0.2, 0.47], 'plant_pot': [1.7, -1.1, 0.18], 'plant_leaves': [1.7, -1.1, 0.62], 'cushion_01': [-1.55, 0.1, 0.68], 'cushion_02': [-1.55, 0.85, 0.68]}
    rep["position_errors"] = {}
    for name, want in positions.items():
        a = rep["objects"][name]["aabb"]
        rep["position_errors"][name] = max(abs((a[0][i] + a[1][i]) / 2 - want[i]) for i in range(3))

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
