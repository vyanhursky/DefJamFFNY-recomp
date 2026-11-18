"""Headless voice editing acceptance, supplied media stays private."""
import hashlib,json
import bpy
b=bridge;v=b.STATE['voice_module'];s=bpy.context.scene;model=b.STATE['model'];accepted=b.validate_scene();mouth=v.mouth_data()
assert accepted['mouth']==mouth and accepted['template']==model.token
assert v.voice_strip().show_waveform and v.voice_strip().sound.packed_file
from fighter_caf_mouth import sample_jaw,require_voice_fit,PREVIEW_AUDIO_DELAY
raw=v.voice_bytes();voice_info=require_voice_fit(raw,accepted['speech_tick'],int(model.duration))
checks=[];samples=[]
for tick in [0.,.5,5.,15.,30.,45.,60.,75.,90.,100.,float(model.duration)]:
 s.frame_set(int(tick)+1,subframe=tick-int(tick));assert b.validate_scene()==accepted
 q=model.pose(tick,b.read_cues(),mouth)[69,4:8]
 assert max(abs(a-c) for a,c in zip(q,sample_jaw(mouth['jaw'],tick)))<1e-7
 samples.append(dict(tick=tick,jaw=q.tolist()))
obj=bpy.data.objects['FFNY_Mouth'];curve=obj.animation_data.action.fcurves.find('["jaw_open"]');key=curve.keyframe_points[0];saved=key.co.y
key.co.y=.3
try:b.validate_scene()
except ValueError:checks.append('non-neutral-start-rejected')
else:raise AssertionError('Unsafe endpoint accepted')
key.co.y=saved
lip=obj.animation_data.action.fcurves.find('["lip_pose"]');saved=lip.keyframe_points[0].co.y;lip.keyframe_points[0].co.y=.5
try:v.mouth_data()
except ValueError:checks.append('fractional-lip-pose-rejected')
else:raise AssertionError('Fractional lip pose accepted')
lip.keyframe_points[0].co.y=saved
strip=v.voice_strip();strip.volume=.5
try:v.export_voice(output.with_suffix('.probe.json'))
except ValueError:checks.append('unsupported-audio-volume-rejected')
else:raise AssertionError('Audio edit silently dropped')
strip.volume=1
s.render.fps=24
try:v.export_voice(output.with_suffix('.probe.json'))
except ValueError:checks.append('different-preview-clock-rejected')
else:raise AssertionError('Preview clock changed silently')
s.render.fps=30
original=next(x for x in v.strips() if x.type=='SOUND' and x!=strip);original.mute=False
try:v.export_voice(output.with_suffix('.probe.json'))
except ValueError:checks.append('unexported-audio-layer-rejected')
else:raise AssertionError('Extra audio layer silently dropped')
original.mute=True
# Exercise user-facing manual insertion/retiming, then restore the exact guide.
s.frame_set(42);s.ffny_jaw_open=.5;s.ffny_lip_shape='4';assert bpy.ops.ffny.key_mouth()=={'FINISHED'}
assert [41,.5] in v.mouth_data()['jaw'] and [41,4] in v.mouth_data()['lips'];checks.append('manual-mouth-key-edit-preview-accepted')
v.set_mouth(mouth);assert b.validate_scene()==accepted
label=s.get('ffny_voice_label');source=bpy.path.abspath(v.voice_strip().sound.filepath)
v.import_voice(source);assert v.voice_bytes()==raw and v.mouth_data()==mouth;checks.append('voice-reimport-retains-mouth-and-packed-bytes')
assert bpy.ops.ffny.jaw_guide()=={'FINISHED'} and v.mouth_data()['lips']==mouth['lips'];checks.append('jaw-only-guide-preserves-edited-lips')
if s.ffny_transcript:
    cues=v.generate_speech_guide();assert len(cues['transcript'].split())>=1
    generated=v.mouth_data();assert len(generated['jaw'])>2 and any(r[1]==1 for r in generated['lips'])
    checks.append('complete-word-phone-guide-generated-and-previewed')
v.set_mouth(mouth);s['ffny_voice_label']=label;assert b.validate_scene()==accepted
report=dict(schema='fighter-voice-blender-audit-1',blender=bpy.app.version_string,voice=voice_info,
 voice_sha256=hashlib.sha256(raw).hexdigest(),packed_voice=True,waveform=True,token=model.token,
 jaw_keys=len(mouth['jaw']),lip_keys=len(mouth['lips']),native_jaw_degrees_cap=12,
 samples=samples,checks=checks,performance=accepted,
 qualification='Offline preview/export and manual keys; native acceptance is separate')
output.write_text(json.dumps(report,indent=2)+'\n');print('FFNY_VOICE_AUDIT_PASSED',len(checks))
