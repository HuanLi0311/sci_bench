import bpy, json, sys
from mathutils.bvhtree import BVHTree
bpy.context.scene.frame_set(0)
hinge = bpy.data.objects["hinge_01"]
added = []
for name, point in (("collision_a", (-.28, 0, .100)), ("collision_b", (-.277, .003, .102))):
    bpy.ops.mesh.primitive_cube_add(size=.014, location=point)
    ob = bpy.context.object
    ob.name = name
    bpy.context.view_layer.update()
    matrix = ob.matrix_world.copy()
    ob.parent = hinge
    ob.matrix_world = matrix
    added.append(ob)
bpy.context.view_layer.update()
def tree(ob):
    return BVHTree.FromPolygons([ob.matrix_world @ v.co for v in ob.data.vertices],
                               [tuple(p.vertices) for p in ob.data.polygons])
pairs = tree(added[0]).overlap(tree(added[1]))
assert pairs
proof = {"surface_intersections": len(pairs), "cube_centres": [list(o.matrix_world.translation) for o in added],
         "hinge": list(hinge.matrix_world.translation), "cube_size_m": .014,
         "parents": [o.parent.name for o in added]}
print("COLLISION_PROOF", json.dumps(proof))
with open('/audit/collision-proof.json', 'w') as f: json.dump(proof, f, indent=2)
bpy.ops.wm.save_as_mainfile(filepath="/audit/submission/folding_chair.blend", compress=True)
