"""Blender-side checks of the geometry and materials actually used in the scene."""
import bpy
from mathutils import Vector


def used_materials(ob):
    return sorted({ob.data.materials[p.material_index].name
                   for p in ob.data.polygons
                   if p.material_index < len(ob.data.materials)
                   and ob.data.materials[p.material_index]})


def upstream(node, seen=None):
    seen = set() if seen is None else seen
    if node in seen:
        return []
    seen.add(node)
    return [node] + [n for socket in node.inputs for link in socket.links
                     for n in upstream(link.from_node, seen)]


def material_report(mat):
    info = {'name': mat.name, 'metallic': None, 'roughness': None, 'images': []}
    if not mat.use_nodes:
        return info
    output = next((n for n in mat.node_tree.nodes
                   if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
    nodes = upstream(output) if output else []
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        return info
    for key in ('Metallic', 'Roughness'):
        socket = bsdf.inputs[key]
        info[key.lower()] = float(socket.default_value) if not socket.is_linked else None
    for key in ('Base Color', 'Roughness', 'Normal'):
        for link in bsdf.inputs[key].links:
            for node in upstream(link.from_node):
                if node.type == 'TEX_IMAGE' and node.image:
                    img = node.image
                    info['images'].append({'name': img.name, 'size': list(img.size),
                                           'packed': bool(img.packed_file), 'feeds': key,
                                           'filepath': img.filepath})
    return info


def visible_mesh(ob):
    # Named parts must be evaluated meshes linked to the rendered scene.
    return (ob.type == 'MESH' and ob.name in bpy.context.scene.objects
            and not ob.hide_render and ob.visible_camera
            and any(not c.hide_render for c in ob.users_collection)
            and bool(ob.data.polygons))


def component_dimensions(ob):
    """Bounds of connected mesh components (front, tray panels, handle)."""
    me = ob.data
    neighbours = [set() for _ in me.vertices]
    for edge in me.edges:
        a, b = edge.vertices
        neighbours[a].add(b); neighbours[b].add(a)
    remaining = set(range(len(me.vertices)))
    result = []
    while remaining:
        todo = [remaining.pop()]; indices = []
        while todo:
            i = todo.pop(); indices.append(i)
            new = neighbours[i] & remaining
            remaining.difference_update(new); todo.extend(new)
        pts = [ob.matrix_world @ me.vertices[i].co for i in indices]
        result.append([round((max(p[k] for p in pts) - min(p[k] for p in pts))*1000, 3)
                       for k in range(3)])
    return result


def motion_error(ob, initial, expected):
    actual = ob.matrix_world
    return max((actual @ Vector(corner) - expected @ initial @ Vector(corner)).length
               for corner in ob.bound_box) * 1000
