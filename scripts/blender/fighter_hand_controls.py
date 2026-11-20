"""Native left-finger preset timing. Mesh/arm/wrist ownership remains locked."""
import copy
import json
import bpy
BRIDGE=None


def hand_data():
    scene=bpy.context.scene
    if not scene.get('ffny_left_hand_enabled'):return None
    value=json.loads(scene['ffny_left_hand_document'])
    value['envelope']=[[0,0],[scene.ffny_hand_begin,0],[scene.ffny_hand_full,1],
                       [scene.ffny_hand_hold,1],[scene.ffny_hand_end,0],[106,0]]
    from fighter_caf_hand import validate_hand
    return validate_hand(value,BRIDGE.STATE['model'].token)


class FFNY_PT_left_hand(bpy.types.Panel):
    bl_label='Left Hand Pose';bl_idname='FFNY_PT_left_hand';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='FFNY'
    @classmethod
    def poll(cls,context):return bool(context.scene.get('ffny_left_hand_enabled'))
    def draw(self,context):
        layout=self.layout;s=context.scene
        layout.label(text='West Side / native left fingers')
        for name,label in [('begin','Begin'),('full','Full pose'),('hold','Hold until'),('end','Return to donor')]:
            layout.prop(s,'ffny_hand_'+name,text=label+' (tick)')
        layout.label(text='Frame = source tick + 1; 30 ticks/sec')
        layout.label(text='Wrist, arm and right hand stay original')
        layout.label(text='Finger shape is the native pose preset')


def register(bridge):
    global BRIDGE
    BRIDGE=bridge
    def update(self,context):
        if BRIDGE.STATE:BRIDGE.update_pose(context.scene)
    for name,default in [('begin',19),('full',24),('hold',39),('end',44)]:
        setattr(bpy.types.Scene,'ffny_hand_'+name,bpy.props.IntProperty(default=default,min=1,max=105,update=update))
    bpy.utils.register_class(FFNY_PT_left_hand)


def initialize(document):
    scene=bpy.context.scene
    if 'left_hand' in document and not scene.get('ffny_left_hand_enabled'):
        value=copy.deepcopy(document['left_hand']);scene['ffny_left_hand_document']=json.dumps(value);scene['ffny_left_hand_enabled']=True
        for name,row in zip(['begin','full','hold','end'],value['envelope'][1:5]):setattr(scene,'ffny_hand_'+name,row[0])
