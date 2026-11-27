import bpy,sys,json
from pathlib import Path
args=sys.argv[sys.argv.index('--')+1:]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.fbx(filepath=args[0],use_anim=True,anim_offset=0.0)
rigs=[o for o in bpy.data.objects if o.type=='ARMATURE']
Path(args[1]).write_text(json.dumps([dict(bones=len(r.data.bones),ranges=[list(a.frame_range) for a in bpy.data.actions],has_animation=bool(r.animation_data and r.animation_data.action)) for r in rigs]))
