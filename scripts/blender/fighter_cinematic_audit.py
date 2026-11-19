"""Headless bridge acceptance; executed by fighter_cinematic.py --audit PATH."""
import json,time
import bpy
import numpy as np

b=bridge;s=bpy.context.scene;model=b.STATE['model'];original=b.read_cues();accepted=b.validate_scene()
ticks=[0,.5,5,10,20,34,40,55,64,65];times=[];snapshots=[]
for tick in ticks:
    before=time.perf_counter();s.frame_set(int(tick)+1,subframe=tick-int(tick));b.validate_scene();times.append(time.perf_counter()-before)
    pose=model.pose(tick,b.read_cues());snapshots.append(dict(tick=tick,facial_quaternions=pose[[68,69,70,71,72,74,76,77,78,79,80],4:8].tolist()))
s.frame_set(35);curve=b.action_curves().find('["brow_squint"]');key=curve.keyframe_points[3];saved=tuple(key.co);rejected=[]

def reject(label,change,restore):
    change()
    try:
        b.validate_scene()
    except (ValueError,AssertionError):rejected.append(label)
    else:raise AssertionError('Unsafe scene change accepted: '+label)
    finally:restore();b.STATE.pop('error',None)

reject('retimed-existing-cue',lambda:setattr(key.co,'x',saved[0]+1),lambda:setattr(key.co,'x',saved[0]))
reject('fractional-pose-index',lambda:setattr(key.co,'y',saved[1]+.25),lambda:setattr(key.co,'y',saved[1]))
reject('palette-index-overflow',lambda:setattr(key.co,'y',13),lambda:setattr(key.co,'y',saved[1]))
old_interpolation=key.interpolation
reject('unsupported-key-interpolation',lambda:setattr(key,'interpolation','BEZIER'),lambda:setattr(key,'interpolation',old_interpolation))
reject('muted-cue-layer',lambda:setattr(curve,'mute',True),lambda:setattr(curve,'mute',False))
obj=bpy.data.objects['FFNY_Mesh_2_0'];co=obj.data.vertices[0].co.copy()
reject('edited-head-geometry',lambda:setattr(obj.data.vertices[0].co,'x',co.x+.01),lambda:setattr(obj.data.vertices[0],'co',co))
uv=obj.data.uv_layers['NativeUV'].data[0].uv.copy()
reject('edited-head-uv',lambda:setattr(obj.data.uv_layers['NativeUV'].data[0].uv,'x',uv.x+.01),lambda:setattr(obj.data.uv_layers['NativeUV'].data[0],'uv',uv))
reject('object-transform',lambda:setattr(obj.location,'x',1),lambda:setattr(obj.location,'x',0))
rig=bpy.data.objects['FFNY_NativeRig'];rig.animation_data_create()
reject('unsupported-direct-bone-action',lambda:setattr(rig.animation_data,'action',bpy.data.actions.new('RejectedBoneEdit')),lambda:setattr(rig.animation_data,'action',None))
b.update_pose(s);assert b.read_cues()==original and b.validate_scene()==accepted
report=dict(blender=bpy.app.version_string,scene=bpy.data.filepath,native_bones=len(rig.data.bones),
            meshes=len(model.document['meshes']),vertices=sum(len(p['positions']) for p in model.document['meshes']),
            performance=accepted,validated_ticks=ticks,negative_checks_rejected=rejected,
            preview_plus_validation_median_seconds=float(np.median(times)),snapshot_phase='Offline exact source curves and palette evaluation; native affine CPU skinning',
            snapshots=snapshots,packed_audio=[sound.name for sound in bpy.data.sounds if sound.packed_file],
            packed_images={im.name:list(im.size) for im in bpy.data.images if im.packed_file},
            scope='Default shirtless outfit; existing sample cue editing; no new body curves/palettes or replacement speech')
output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print('FFNY_AUDIT_PASSED',len(rejected),len(ticks))
