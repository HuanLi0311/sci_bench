"""Extract evaluated world geometry from the untrusted .blend, autoexec disabled."""
import bpy,json,sys,math,itertools
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

dest=Path(sys.argv[sys.argv.index('--')+1]);dest.mkdir(parents=True,exist_ok=True)
spec=json.loads(Path('/tests/spec.json').read_text())
scene=bpy.context.scene
rigs={w:bpy.data.objects.get('rig_'+w) for w in ['left','right']}
report=dict(version=bpy.app.version_string,range=[scene.frame_start,scene.frame_end],fps=scene.render.fps,rigs={},frames=[],camera={},external=[])
for im in bpy.data.images:
    if im.source=='FILE' and not im.packed_file:report['external'].append(im.filepath)
def geometry(o):
    ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh();vs=[ev.matrix_world@v.co for v in m.vertices];fs=[tuple(p.vertices) for p in m.polygons];ev.to_mesh_clear()
    if not vs or not fs:return None
    lo=Vector(tuple(min(v[i] for v in vs) for i in range(3)));hi=Vector(tuple(max(v[i] for v in vs) for i in range(3)))
    return dict(bvh=BVHTree.FromPolygons(vs,fs,all_triangles=False),vertices=vs,lo=lo,hi=hi,center=(lo+hi)/2,triangles=sum(len(f)-2 for f in fs))
def close(a,b,margin=0):return all(a['hi'][i]+margin>=b['lo'][i] and b['hi'][i]+margin>=a['lo'][i] for i in range(3))
def distance(a,b):
    return min([a['bvh'].find_nearest(v)[3] for v in b['vertices']]+[b['bvh'].find_nearest(v)[3] for v in a['vertices']])
def penetration(a,b):
    depths=[]
    for aa,bb in [(a,b),(b,a)]:
        for v in aa['vertices']:
            p,n,_,d=bb['bvh'].find_nearest(v)
            if (v-p).dot(n)<-1e-6:depths.append(d)
    return max(depths,default=0.)
def related(a,b):
    p=spec['parents']
    def chain(n):
        out=[n]
        for _ in range(3):
            n=p.get(n)
            if n:out.append(n)
        return out
    return a in chain(b) or b in chain(a)
meshes={}
scene.frame_set(1)
for w,rig in rigs.items():
    if not rig or rig.type!='ARMATURE':continue
    action=rig.animation_data.action if rig.animation_data else None
    ms=[o for o in scene.objects if o.type=='MESH' and o.name.startswith(w+'_')]
    meshes[w]=ms
    geos=[geometry(o) for o in ms];geos=[g for g in geos if g]
    skin=[]
    for o in ms:
        skin.append(dict(name=o.name,armatures=[m.object.name if m.object else '' for m in o.modifiers if m.type=='ARMATURE' and m.show_render and m.show_viewport],unweighted=sum(not any(g.weight>0 and o.vertex_groups[g.group].name in rig.data.bones for g in v.groups) for v in o.data.vertices),max_weights=max((sum(g.weight>0 for g in v.groups) for v in o.data.vertices),default=0),shape_keys=bool(o.data.shape_keys),visible=not o.hide_render,vertices=len(o.data.vertices)))
    foot=rig.pose.bones['foot.L'];forward=rig.matrix_world.to_3x3()@(foot.tail-foot.head)
    report['rigs'][w]=dict(bones={b.name:dict(parent=b.parent.name if b.parent else None,length=b.length) for b in rig.data.bones},action=action.name if action else None,action_range=list(action.frame_range) if action else [],curves=len(action.fcurves) if action else 0,skin=skin,height=max(g['hi'].z for g in geos)-min(g['lo'].z for g in geos) if geos else 0,triangles=sum(g['triangles'] for g in geos),root=list(rig.matrix_world@rig.pose.bones['root'].head),forward=list(forward.normalized()),drivers=len(rig.animation_data.drivers) if rig.animation_data else 0)
report['armature_count']=sum(o.type=='ARMATURE' for o in scene.objects)
cam=bpy.data.objects.get('cam_fixed')
if cam and cam.type=='CAMERA':report['camera']=dict(location=list(cam.matrix_world.translation),type=cam.data.type,scale=cam.data.ortho_scale,direction=list(cam.matrix_world.to_quaternion()@Vector((0,0,-1))))
events=spec['events']
for f in range(1,301):
    scene.frame_set(f);gs={o.name:geometry(o) for w in meshes for o in meshes[w]};gs={n:g for n,g in gs.items() if g}
    collisions=[];maxdepth=0
    for (na,a),(nb,b) in itertools.combinations(gs.items(),2):
        wa,ba=na.split('_',1);wb,bb=nb.split('_',1)
        if wa==wb and related(ba,bb):continue
        if not close(a,b):continue
        overlap=a['bvh'].overlap(b['bvh']);depth=penetration(a,b)
        if not overlap and depth<=1e-6:continue
        allowed=any(abs(f-e['frame'])<=2 and {na,nb}=={e['attacker'],e['target']} for e in events)
        if allowed:maxdepth=max(maxdepth,depth)
        elif depth>1e-5 or overlap:collisions.append([na,nb,depth])
    roots={w:list(r.matrix_world@r.pose.bones['root'].head) for w,r in rigs.items() if r and r.type=='ARMATURE'}
    feet={w+'_'+s:dict(center=list(gs[w+'_foot.'+s]['center']),bottom=gs[w+'_foot.'+s]['lo'].z) for w in meshes for s in ['L','R'] if w+'_foot.'+s in gs}
    distances={str(e['frame']):distance(gs[e['attacker']],gs[e['target']]) for e in events if e['attacker'] in gs and e['target'] in gs}
    report['frames'].append(dict(frame=f,roots=roots,feet=feet,collisions=collisions,penetration=maxdepth,contacts=distances,bounds_ok=all(g['lo'].x>=-3 and g['hi'].x<=3 and g['lo'].y>=-3 and g['hi'].y<=3 for g in gs.values())))
(dest/'scene.json').write_text(json.dumps(report))
if '--no-render' not in sys.argv:
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=64;scene.cycles.seed=19;scene.cycles.use_denoising=True
    scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.camera=cam
    for i,f in enumerate(spec['keys'],1):
        scene.frame_set(f);scene.render.filepath=str(dest/f'render_key_{i:02d}.png');bpy.ops.render.render(write_still=True)
    # Shift every right-side skeletal curve six frames, leaving everything else fixed.
    act=rigs['right'].animation_data.action
    original=[[(k.co.x,k.handle_left.x,k.handle_right.x) for k in fc.keyframe_points] for fc in act.fcurves]
    for fc in act.fcurves:
        for k in fc.keyframe_points:k.co.x+=6;k.handle_left.x+=6;k.handle_right.x+=6
    scene.frame_set(spec['events'][0]['frame']);scene.render.filepath=str(dest/'shifted.png');bpy.ops.render.render(write_still=True)
    for fc,old in zip(act.fcurves,original):
        for k,v in zip(fc.keyframe_points,old):k.co.x,k.handle_left.x,k.handle_right.x=v
    left,right=rigs['left'],rigs['right'];la,ra=left.animation_data.action,right.animation_data.action
    left.animation_data.action=ra;right.animation_data.action=la
    swapped=[]
    for e in events:
        scene.frame_set(e['frame']);a=geometry(bpy.data.objects[e['attacker']]);b=geometry(bpy.data.objects[e['target']]);swapped.append(distance(a,b))
    (dest/'swapped.json').write_text(json.dumps(swapped))
    left.animation_data.action=la;right.animation_data.action=ra
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
    for i,f in enumerate(spec['keys'],1):
        scene.frame_set(f);scene.render.filepath=str(dest/f'video_key_{i:02d}.png');bpy.ops.render.render(write_still=True)
