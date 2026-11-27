import bpy, collections
ob = bpy.data.objects["deck"]
me = ob.data
c = collections.Counter()
for p in me.polygons:
    n = p.normal
    if n.z > 0.5: c["up"] += 1
    elif n.z < -0.5: c["down"] += 1
    elif abs(n.y) > 0.9: c["sideY"] += 1
    else: c["other"] += 1
print("NORMALS", c)
areas = collections.defaultdict(float)
for p in me.polygons:
    areas[p.material_index] += p.area
print("AREAS", {k: round(v, 5) for k, v in sorted(areas.items())})
uv = me.uv_layers.active
down_area = 0.0
for p in me.polygons:
    if p.normal.z < -0.5:
        us = [uv.data[li].uv for li in p.loop_indices]
        s = 0.0
        for i in range(len(us)):
            a, b = us[i], us[(i+1) % len(us)]
            s += a[0]*b[1] - b[0]*a[1]
        down_area += abs(s)/2
print("DOWN_UV_AREA", round(down_area, 5), "DOWN_FACES", sum(1 for p in me.polygons if p.normal.z < -0.5))
