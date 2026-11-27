"""Blender 4.2.3 authoring entry point. Generates starter + reference solution."""
import bpy
from mathutils import Matrix, Vector
import sys,json,math,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from choreography import PARENTS,EVENTS,KEYS,pose,stance,radius
from prepare_desktop import prepare

ROOT=Path(sys.argv[sys.argv.index('--')+1]);MAT=ROOT/'environment/materials';OUT=ROOT/'solution'
bpy.context.preferences.filepaths.save_version=0
MAT.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
    m.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.62
    return m
def matrix(a,b):
    return Matrix.Translation(a) @ (b-a).to_track_quat('Y','Z').to_matrix().to_4x4()
def segment(name,a,b,r,mat,rig,bone):
    # Convex octagonal segments with a clearance gap at joints.
    mid=(a+b)/2;length=(b-a).length
    bpy.ops.mesh.primitive_cube_add(size=1,location=mid);o=bpy.context.object;o.name=name
    o.rotation_mode='QUATERNION';o.rotation_quaternion=(b-a).to_track_quat('Z','Y')
    o.scale=(2*r,2*r,max(.016,length+(.1*(1 if rig.name=='rig_left' else 1.9/1.7) if bone=='head' else -.025)));bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bevel=o.modifiers.new('rounded_edges','BEVEL');bevel.width=.015;bevel.segments=2
    bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=bevel.name)
    # Store mesh coordinates in armature space, preserving exact rest positions.
    mw=o.matrix_world.copy();o.data.transform(mw);o.matrix_world=Matrix.Identity(4)
    vg=o.vertex_groups.new(name=bone);vg.add(list(range(len(o.data.vertices))),1,'REPLACE')
    arm=o.modifiers.new('skin','ARMATURE');arm.object=rig;o.parent=rig;o.matrix_parent_inverse=Matrix.Identity(4)
    o.data.materials.append(mat);o['bone']=bone;o['character']=rig.name
    return o
def make_rig(which):
    rest=pose(which,1);data=bpy.data.armatures.new('skeleton_'+which);rig=bpy.data.objects.new('rig_'+which,data);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for n in PARENTS:
        eb=data.edit_bones.new(n);eb.head,eb.tail=rest[n]
        if PARENTS[n]:eb.parent=data.edit_bones[PARENTS[n]]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    mat=material('fighter_'+which,(.045,.33,.68) if which=='left' else (.82,.15,.06))
    for n,(a,b) in rest.items():
        if n not in ['root','pelvis','clavicle.L','clavicle.R']:segment(which+'_'+n,a,b,radius(n)*(1 if which=='left' else 1.9/1.7),mat,rig,n)
    for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
    return rig
def camera():
    bpy.ops.object.camera_add(location=(0,-5.8,2.25));c=bpy.context.object;c.name='cam_fixed';c.data.type='ORTHO';c.data.ortho_scale=3.8
    c.rotation_euler=(Vector((0,0,.9))-c.location).to_track_quat('-Z','Y').to_euler();bpy.context.scene.camera=c
def stage():
    bpy.ops.mesh.primitive_plane_add(size=6);floor=bpy.context.object;floor.name='stage';floor.data.materials.append(material('mat_stage',(.055,.065,.09)))
    m=floor.data.materials[0];nt=m.node_tree;n=nt.nodes.new('ShaderNodeTexChecker');n.inputs['Color1'].default_value=(.09,.11,.15,1);n.inputs['Color2'].default_value=(.16,.19,.23,1);n.inputs['Scale'].default_value=12;nt.links.new(n.outputs['Color'],nt.nodes.get('Principled BSDF').inputs['Base Color'])
    for loc,power,size in [((1,-3,4),950,5),((-2,1,3),700,4)]:
        bpy.ops.object.light_add(type='AREA',location=loc);bpy.context.object.data.energy=power;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=size
        bpy.context.object.rotation_euler=(Vector((0,0,1))-bpy.context.object.location).to_track_quat('-Z','Y').to_euler()
    camera()
def configure():
    s=bpy.context.scene;s.frame_start=1;s.frame_end=300;s.render.fps=30;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1
    s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=64;s.cycles.seed=19;s.cycles.use_denoising=True
    s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100
    s.view_settings.view_transform='Standard';s.world.color=(.12,.12,.12)
def fbx(rig,path):
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for c in rig.children:c.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=rig.animation_data is not None,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
def save_tables(rigs):
    rows=[]
    for rig in rigs:
        for b in rig.data.bones:rows.append(dict(character=rig.name,bone=b.name,parent=b.parent.name if b.parent else '',length=b.length,head=list(b.head_local),tail=list(b.tail_local)))
    (MAT/'bone_mapping.json').write_text(json.dumps(rows,indent=2))
    with open(MAT/'bone_mapping.csv','w',newline='') as f:
        w=csv.writer(f);w.writerow(['character','bone','parent','length_m','head_x','head_y','head_z','tail_x','tail_y','tail_z'])
        for r in rows:w.writerow([r['character'],r['bone'],r['parent'],r['length'],*r['head'],*r['tail']])
    with open(MAT/'action_segments.csv','w',newline='') as f:
        w=csv.writer(f);w.writerow(['start','contact','end','attacker','target','tolerance_frames'])
        for c,s,target in EVENTS:w.writerow([c-12,c,c+12,'left_hand.'+s,'right_'+target,2])
        w.writerow([215,235,253,'left_foot.L','duck_no_contact',2])
    supports={}
    for s in ['L','R']:
        ranges=[];start=None
        for f in range(1,302):
            yes=f<=300 and stance(s,f)
            if yes and start is None:start=f
            if not yes and start is not None:ranges.append([start,f-1]);start=None
        supports[s]=ranges
    (MAT/'support_phases.json').write_text(json.dumps(supports,indent=2))
    (MAT/'stage.json').write_text(json.dumps(dict(size=[6,6],initial_distance=2.4,camera=dict(name='cam_fixed',location=[0,-5.8,2.25],target=[0,0,.9],ortho_scale=3.8),key_frames=list(KEYS))))

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
rigs=[make_rig(w) for w in ['left','right']];stage();configure();save_tables(rigs)
prepare()
bpy.ops.wm.save_as_mainfile(filepath=str(MAT/'fighters.blend'))
for rig in rigs:fbx(rig,MAT/(rig.name+'.fbx'))
for rig in rigs:
    which=rig.name[4:];rig.animation_data_create();act=bpy.data.actions.new('Fight_'+which.title());rig.animation_data.action=act
    for f in range(1,301):
        targets=pose(which,f)
        for n in PARENTS:
            pb=rig.pose.bones[n];pb.matrix=matrix(*targets[n]);bpy.context.view_layer.update()
            for prop in ['location','rotation_quaternion','scale']:pb.keyframe_insert(prop,frame=f,group=n)
    for fc in act.fcurves:
        for key in fc.keyframe_points:key.interpolation='LINEAR'
bpy.context.scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'fight.blend'))
for rig in rigs:fbx(rig,OUT/('fight_'+rig.name[4:]+'.fbx'))
if '--geometry-only' in sys.argv:sys.exit(0)
manifest=dict(schemaVersion=1,units='meters',blenderVersion='4.2.3',assets=[dict(path='fighters',role='geometry-and-animation',source='self-authored',license='CC0-1.0',url='')],renders=[])
for i,f in enumerate(KEYS,1):
    s=bpy.context.scene;s.frame_set(f);s.render.filepath=str(OUT/f'render_key_{i:02d}.png');bpy.ops.render.render(write_still=True)
    manifest['renders'].append(dict(file=f'render_key_{i:02d}.png',camera='cam_fixed',frame=f,resolution=[1280,720],samples=64))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
# Playblast uses Workbench; evidence renders above remain Cycles CPU.
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.render.image_settings.file_format='FFMPEG';s.render.ffmpeg.format='MPEG4';s.render.ffmpeg.codec='H264';s.render.ffmpeg.constant_rate_factor='MEDIUM';s.render.filepath=str(OUT/'playblast.mp4')
bpy.ops.render.render(animation=True)
import shutil
shutil.copyfile(OUT/'playblast.mp4',MAT/'reference.mp4')
