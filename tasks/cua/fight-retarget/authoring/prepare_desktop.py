import bpy,sys
def prepare():
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.color_type='MATERIAL'
    bpy.ops.object.select_all(action='DESELECT')
    rig=bpy.data.objects.get('rig_left')
    if rig:rig.select_set(True);bpy.context.view_layer.objects.active=rig
if __name__=='__main__':
    bpy.context.preferences.filepaths.save_version=0
    prepare()
    bpy.ops.wm.save_as_mainfile(filepath=sys.argv[sys.argv.index('--')+1])
