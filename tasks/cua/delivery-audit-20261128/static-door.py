import bpy,sys
door=bpy.data.objects['door_right']
target=bpy.data.objects.new('static_door_target',None)
bpy.context.scene.collection.objects.link(target)
target.matrix_world=door.matrix_world.copy()
c=door.constraints.new('COPY_TRANSFORMS')
c.target=target
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-1])
