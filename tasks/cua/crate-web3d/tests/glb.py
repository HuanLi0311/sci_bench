"""Read a .glb and report the geometry facts the rubric needs.

Pure standard library: glTF 2.0 JSON chunk + binary chunk, node hierarchy,
accessor POSITION min/max, materials, embedded images, cameras.
"""
import json
import struct


def load_glb(path):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError("not a glTF 2.0 binary")
    off, doc, bin_chunk = 12, None, b""
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            doc = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            bin_chunk = chunk
        off += 8 + clen
    if doc is None:
        raise ValueError("no JSON chunk")
    return doc, bin_chunk


def quat_matrix(q):
    x, y, z, w = q
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def node_local(node):
    if "matrix" in node:
        m = node["matrix"]
        return [[m[c * 4 + r] for c in range(4)] for r in range(4)]
    t = node.get("translation", [0, 0, 0])
    r = node.get("rotation", [0, 0, 0, 1])
    s = node.get("scale", [1, 1, 1])
    T = [[1, 0, 0, t[0]], [0, 1, 0, t[1]], [0, 0, 1, t[2]], [0, 0, 0, 1]]
    S = [[s[0], 0, 0, 0], [0, s[1], 0, 0], [0, 0, s[2], 0], [0, 0, 0, 1]]
    return mat_mul(mat_mul(T, quat_matrix(r)), S)


def apply(m, p):
    return [sum(m[i][k] * (p[k] if k < 3 else 1.0) for k in range(4)) for i in range(3)]


def world_matrices(doc):
    nodes = doc.get("nodes", [])
    parents = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parents[c] = i
    cache = {}

    def world(i):
        if i in cache:
            return cache[i]
        local = node_local(nodes[i])
        m = mat_mul(world(parents[i]), local) if i in parents else local
        cache[i] = m
        return m

    return {i: world(i) for i in range(len(nodes))}


def mesh_aabb(doc, mesh_index, matrix):
    mesh = doc["meshes"][mesh_index]
    lo = [1e9, 1e9, 1e9]
    hi = [-1e9, -1e9, -1e9]
    tris = 0
    for prim in mesh["primitives"]:
        acc = doc["accessors"][prim["attributes"]["POSITION"]]
        amin, amax = acc["min"], acc["max"]
        if "indices" in prim:
            tris += doc["accessors"][prim["indices"]]["count"] // 3
        else:
            tris += acc["count"] // 3
        corners = [[amin[0] if b & 1 else amax[0],
                    amin[1] if b & 2 else amax[1],
                    amin[2] if b & 4 else amax[2]] for b in range(8)]
        for c in corners:
            w = apply(matrix, c)
            for k in range(3):
                lo[k] = min(lo[k], w[k])
                hi[k] = max(hi[k], w[k])
    return lo, hi, tris


def report(path):
    doc, bin_chunk = load_glb(path)
    world = world_matrices(doc)
    nodes = doc.get("nodes", [])
    rep = {
        "asset_version": doc.get("asset", {}).get("version"),
        "generator": doc.get("asset", {}).get("generator"),
        "node_count": len(nodes),
        "nodes": {},
        "cameras": {},
        "materials": {},
        "images": [],
        "polys_total": 0,
        "bounds": None,
    }
    for i, n in enumerate(nodes):
        entry = {
            "name": n.get("name", ""),
            "parent": None,
            "translation": n.get("translation", [0, 0, 0])[:],
            "children": [nodes[c].get("name", "") for c in n.get("children", [])],
        }
        m = world[i]
        entry["world_translation"] = [m[0][3], m[1][3], m[2][3]]
        if "mesh" in n:
            lo, hi, tris = mesh_aabb(doc, n["mesh"], m)
            entry["aabb"] = [lo, hi]
            entry["dims"] = [hi[k] - lo[k] for k in range(3)]
            entry["tris"] = tris
            rep["polys_total"] += tris
        if "camera" in n:
            cam = doc["cameras"][n["camera"]]
            entry["camera"] = cam
            rep["cameras"][entry["name"]] = cam
        rep["nodes"][entry["name"]] = entry

    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            name = nodes[c].get("name", "")
            if name in rep["nodes"]:
                rep["nodes"][name]["parent"] = n.get("name", "")

    for mat in doc.get("materials", []):
        pbr = mat.get("pbrMetallicRoughness", {})
        rep["materials"][mat.get("name", "")] = {
            "metallic": pbr.get("metallicFactor", 1.0),
            "roughness": pbr.get("roughnessFactor", 1.0),
            "base_color": pbr.get("baseColorFactor", [1, 1, 1, 1]),
            "has_base_texture": "baseColorTexture" in pbr,
            "has_mr_texture": "metallicRoughnessTexture" in pbr,
            "has_normal_texture": "normalTexture" in mat,
            "alpha_mode": mat.get("alphaMode", "OPAQUE"),
            "alpha_cutoff": mat.get("alphaCutoff", 0.5),
        }

    for img in doc.get("images", []):
        rep["images"].append({
            "name": img.get("name", ""),
            "embedded": "bufferView" in img,
            "uri": img.get("uri", ""),
            "mime": img.get("mimeType", ""),
        })

    meshes = [k for k, v in rep["nodes"].items() if "aabb" in v]
    if meshes:
        lo = [min(rep["nodes"][k]["aabb"][0][i] for k in meshes) for i in range(3)]
        hi = [max(rep["nodes"][k]["aabb"][1][i] for k in meshes) for i in range(3)]
        rep["bounds"] = [lo, hi]
        rep["size"] = [hi[i] - lo[i] for i in range(3)]
    return rep
