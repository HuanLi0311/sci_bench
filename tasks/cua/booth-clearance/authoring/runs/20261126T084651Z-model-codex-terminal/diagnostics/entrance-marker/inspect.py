import bpy
import json
import sys


def describe(ob):
    result = {"name": ob.name, "type": ob.type, "location": list(ob.location),
              "world_location": list(ob.matrix_world.translation),
              "rotation_euler": list(ob.rotation_euler), "scale": list(ob.scale),
              "dimensions": list(ob.dimensions), "parent": ob.parent.name if ob.parent else None,
              "children": [child.name for child in ob.children],
              "empty_display_type": ob.empty_display_type, "empty_display_size": ob.empty_display_size,
              "hide_render": ob.hide_render, "hide_viewport": ob.hide_viewport,
              "scenes": [s.name for s in bpy.data.scenes if ob.name in s.objects]}
    if ob.type == "MESH":
        evaluated = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        points = [list(evaluated.matrix_world @ v.co) for v in mesh.vertices]
        result["world_vertices"] = points
        result["polygons"] = [{"vertices": list(p.vertices), "material_index": p.material_index} for p in mesh.polygons]
        result["aabb"] = [[min(p[i] for p in points) for i in range(3)], [max(p[i] for p in points) for i in range(3)]] if points else None
        evaluated.to_mesh_clear()
    return result


marker = bpy.data.objects.get("entrance_zone")
shell = bpy.data.objects.get("booth_shell")
data = {"blender_version": bpy.app.version_string, "active_scene": bpy.context.scene.name,
        "scene_names": [s.name for s in bpy.data.scenes],
        "entrance_zone": describe(marker) if marker else None,
        "related_objects": [describe(o) for o in bpy.data.objects if o is not marker and
                            ("entrance" in o.name.lower() or (marker is not None and marker in o.parent_recursive))],
        "booth_shell": describe(shell) if shell else None}
with open(sys.argv[sys.argv.index("--") + 1], "w") as f:
    json.dump(data, f, indent=2)
