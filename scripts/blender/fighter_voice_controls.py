"""Blender voice waveform and editable native mouth controls. Loaded by the bridge."""
import hashlib
import json
from pathlib import Path
import subprocess
import bpy

BRIDGE=None
VOICE_NAME='FFNY Imported Voice'
MOUTH_OBJECT='FFNY_Mouth'
PREVIEW=None


def strips():
    ed=bpy.context.scene.sequence_editor_create()
    return ed.strips if hasattr(ed,'strips') else ed.sequences


def voice_strip():
    return next((s for s in strips() if s.type=='SOUND' and s.name==VOICE_NAME),None)


def voice_bytes():
    s=voice_strip()
    if not s:raise ValueError('Import a voice track first')
    raw=bytes(s.sound.packed_file.data) if s.sound.packed_file else Path(bpy.path.abspath(s.sound.filepath)).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=bpy.context.scene.get('ffny_voice_sha256'):
        raise ValueError('Voice changed outside Import Voice Track; re-import it')
    return raw


def mouth_data():
    from fighter_caf_mouth import validate_mouth
    if not bpy.context.scene.get('ffny_mouth_enabled'):return None
    obj=bpy.data.objects.get(MOUTH_OBJECT)
    if not obj or not obj.animation_data or not obj.animation_data.action:raise ValueError('Mouth action missing')
    if obj.animation_data.drivers or obj.animation_data.nla_tracks:raise ValueError('Mouth drivers/NLA are unsupported')
    curves=obj.animation_data.action.fcurves
    if len(curves)!=2:raise ValueError('Keep the Jaw Open and Lip Shape mouth curves')
    result={}
    for name,path,interpolation in [('jaw','jaw_open','LINEAR'),('lips','lip_pose','CONSTANT')]:
        curve=curves.find('["'+path+'"]')
        if curve is None or curve.mute or curve.modifiers:raise ValueError('Unsupported mouth curve/muting/modifiers')
        rows=[]
        for k in curve.keyframe_points:
            if abs(k.co.x-round(k.co.x))>1e-5 or k.interpolation!=interpolation:
                raise ValueError('Mouth keys use whole frames; Jaw Linear and Lip Shape Constant')
            value=float(k.co.y)
            if name=='lips':
                if value!=round(value):raise ValueError('Lip Shape must be a whole pose number')
                value=int(value)
            rows.append([int(round(k.co.x))-1,value])
        result[name]=rows
    validate_mouth(result,int(BRIDGE.STATE['model'].duration));return result


def set_mouth(data):
    from fighter_caf_mouth import validate_mouth
    validate_mouth(data,int(BRIDGE.STATE['model'].duration))
    scene=bpy.context.scene
    obj=bpy.data.objects.get(MOUTH_OBJECT)
    if obj is None:
        obj=bpy.data.objects.new(MOUTH_OBJECT,None);scene.collection.objects.link(obj)
    obj['jaw_open']=0.0;obj['lip_pose']=0
    obj.id_properties_ui('jaw_open').update(min=0.,max=1.,description='Native jaw opening; capped at12degrees')
    obj.id_properties_ui('lip_pose').update(min=0,max=14,description='Existing native lip-expression sample')
    old=obj.animation_data.action if obj.animation_data else None
    obj.animation_data_create();obj.animation_data.action=bpy.data.actions.new('FFNY Mouth '+str(len(bpy.data.actions)))
    for name,path,interp in [('jaw','jaw_open','LINEAR'),('lips','lip_pose','CONSTANT')]:
        curve=obj.animation_data.action.fcurves.new('["'+path+'"]',action_group='Mouth / '+name)
        for tick,value in data[name]:curve.keyframe_points.insert(tick+1,value,options={'FAST'}).interpolation=interp
        curve.update()
    if old and old.users==0:bpy.data.actions.remove(old)
    scene['ffny_mouth_enabled']=True
    for o in bpy.context.selected_objects:o.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    BRIDGE.STATE.pop('error',None);BRIDGE.update_pose(scene)


def sync_controls(scene,tick,mouth):
    if mouth is None:return
    from bisect import bisect_right
    from fighter_caf_mouth import sample_jaw,MAX_JAW_DEGREES
    import math
    q=sample_jaw(mouth['jaw'],tick)
    scene.ffny_jaw_open=max(0.,min(1.,2*math.atan2(q[0],q[3])/math.radians(MAX_JAW_DEGREES)))
    at=max(0,bisect_right([r[0] for r in mouth['lips']],tick)-1)
    scene.ffny_lip_shape=str(mouth['lips'][at][1])


def import_voice(path):
    from fighter_caf_mouth import require_voice_fit,neutral_mouth,PREVIEW_AUDIO_DELAY
    stop_preview()
    scene=bpy.context.scene;source=Path(path).expanduser().resolve()
    previous=mouth_data() if scene.get('ffny_mouth_enabled') else None
    if not source.is_file():raise ValueError('Voice file missing')
    output=Path(BRIDGE.STATE['model'].document['output_dir']).parent/'audio';output.mkdir(parents=True,exist_ok=True)
    if source.suffix.lower()=='.wav':raw=source.read_bytes()
    else:
        converter=BRIDGE.STATE.get('audio_converter')
        if not converter or not Path(converter).is_file():raise ValueError('This launcher needs FFmpeg for MP3 import; mono PCM16 WAV also works')
        temporary=output/('convert-'+hashlib.sha256(source.read_bytes()).hexdigest()+'.wav')
        if not temporary.exists():
            r=subprocess.run([converter,'-hide_banner','-loglevel','error','-i',str(source),'-ac','1','-ar','24000','-c:a','pcm_s16le','-fs','8388609',str(temporary)],capture_output=True,text=True)
            if r.returncode:raise ValueError('Audio conversion failed: '+r.stderr[-1200:])
        raw=temporary.read_bytes()
    info=require_voice_fit(raw,0,int(BRIDGE.STATE['model'].duration));digest=hashlib.sha256(raw).hexdigest();canonical=output/(digest+'.wav')
    if canonical.exists():
        if canonical.read_bytes()!=raw:raise ValueError('Voice cache checksum changed')
    else:canonical.write_bytes(raw)
    old=voice_strip()
    if old:strips().remove(old)
    for s in strips():
        if s.type=='SOUND':s.mute=True
    s=strips().new_sound(VOICE_NAME,str(canonical),channel=2,frame_start=1+PREVIEW_AUDIO_DELAY)
    s.sound.pack();s.show_waveform=True;s.mute=False
    scene['ffny_voice_sha256']=digest;scene['ffny_voice_label']=source.name;scene['ffny_voice_seconds']=info['seconds']
    scene.frame_end=int(BRIDGE.STATE['model'].duration)+1;scene.render.fps=30;scene.render.fps_base=1.;scene.sync_mode='AUDIO_SYNC'
    set_mouth(previous if previous is not None else neutral_mouth(int(BRIDGE.STATE['model'].duration)))
    scene['ffny_status']='Imported %.3fs voice; existing mouth keys retained. Generate a guide or retime manually'%info['seconds']
    return info


def speech_tick():
    from fighter_caf_mouth import PREVIEW_AUDIO_DELAY
    scene=bpy.context.scene;s=voice_strip()
    if not s:raise ValueError('Import a voice track first')
    if scene.render.fps!=30 or scene.render.fps_base!=1.:raise ValueError('Keep the native preview at30frames per second')
    if s.frame_start!=round(s.frame_start):raise ValueError('Voice starts on a whole source frame')
    if any(x.type=='SOUND' and x!=s and not x.mute for x in strips()):raise ValueError('Mute other sound strips; export contains one voice')
    return int(s.frame_start)-1-PREVIEW_AUDIO_DELAY


def checked_voice():
    from fighter_caf_mouth import require_voice_fit,PREVIEW_AUDIO_DELAY
    raw=voice_bytes();s=voice_strip();tick=speech_tick()
    if s.mute or s.frame_offset_start or s.frame_offset_end or s.volume!=1 or getattr(s,'pitch',1)!=1 or getattr(s,'speed_factor',1)!=1 or bool(getattr(s,'modifiers',[])):
        raise ValueError('Keep voice untrimmed/unmuted at normal volume/pitch; edit a source copy then re-import')
    require_voice_fit(raw,tick,int(BRIDGE.STATE['model'].duration))
    return raw,tick


def export_voice(path):
    raw,tick=checked_voice()
    target=Path(path).with_suffix('.voice.wav')
    if target.exists():raise ValueError('Voice export already exists; choose a new export filename')
    return dict(path=str(target.resolve()),sha256=hashlib.sha256(raw).hexdigest(),start_tick=tick),raw


def stop_preview():
    """Release only this player's audio/timer; leave the editing cursor in place."""
    global PREVIEW
    player,PREVIEW=PREVIEW,None
    if player is None:return
    try:player['audio'].close()
    finally:
        try:player['wm'].event_timer_remove(player['timer'])
        except (ReferenceError,RuntimeError):pass
    try:
        for area in player['window'].screen.areas:area.tag_redraw()
    except ReferenceError:pass


def start_preview(context,speed):
    global PREVIEW
    from fighter_preview_playback import PreviewAudio
    stop_preview()
    if not context.window:raise ValueError('Use an interactive Blender window for preview')
    if context.screen.is_animation_playing:bpy.ops.screen.animation_cancel(restore_frame=False)
    BRIDGE.validate_scene();raw,_=checked_voice();scene=context.scene
    duration=float(BRIDGE.STATE['model'].duration)
    tick=max(0.,min(duration,scene.frame_current_final-1))
    if tick>=duration:
        tick=0.;scene.frame_set(1)
    audio=PreviewAudio(raw,int(voice_strip().frame_start)-1,duration,tick,speed)
    try:
        timer=context.window_manager.event_timer_add(1/30,window=context.window)
        PREVIEW=dict(audio=audio,scene=scene,window=context.window,wm=context.window_manager,timer=timer,
                     last_frame=scene.frame_current_final,speed=speed)
    except Exception:
        audio.close();raise
    return PREVIEW


def step_preview(context,player):
    """Advance from audio position, dropping preview frames rather than drifting."""
    if PREVIEW is not player:return False
    scene=player['scene']
    if (context.scene!=scene or context.screen.is_animation_playing
            or abs(scene.frame_current_final-player['last_frame'])>1e-4):
        stop_preview();return False  # User scrubbed or started ordinary playback.
    audio=player['audio'];tick=audio.tick
    if not audio.playing and tick<audio.duration-.01:
        stop_preview();return False
    frame=tick+1;scene.frame_set(int(frame),subframe=frame-int(frame))
    if BRIDGE.STATE.get('error'):raise ValueError(BRIDGE.STATE['error'])
    player['last_frame']=scene.frame_current_final
    if tick>=audio.duration-.0001:
        scene.frame_set(int(audio.duration)+1);stop_preview();return False
    for area in player['window'].screen.areas:area.tag_redraw()
    return True


class FFNY_OT_preview_play(bpy.types.Operator):
    bl_idname='ffny.preview_play';bl_label='Play Preview'
    bl_description='Play from the cursor at preview speed; exported timing stays unchanged'
    speed:bpy.props.FloatProperty(default=.5,options={'SKIP_SAVE'})
    def execute(self,context):
        try:
            self.player=start_preview(context,self.speed)
            context.window_manager.modal_handler_add(self);return {'RUNNING_MODAL'}
        except Exception as e:
            stop_preview();self.report({'ERROR'},str(e));return {'CANCELLED'}
    def modal(self,context,event):
        if PREVIEW is not self.player:return {'FINISHED'}
        if event.type in {'ESC','SPACE'} and event.value=='PRESS':
            stop_preview();return {'FINISHED'}
        if event.type=='TIMER':
            try:return {'PASS_THROUGH'} if step_preview(context,self.player) else {'FINISHED'}
            except Exception as e:
                stop_preview();self.report({'ERROR'},str(e));return {'CANCELLED'}
        return {'PASS_THROUGH'}
    def cancel(self,context):
        if PREVIEW is self.player:stop_preview()


class FFNY_OT_preview_stop(bpy.types.Operator):
    bl_idname='ffny.preview_stop';bl_label='Stop Preview'
    def execute(self,context):stop_preview();return {'FINISHED'}


@bpy.app.handlers.persistent
def preview_teardown(*_):stop_preview()


class FFNY_OT_voice_import(bpy.types.Operator):
    bl_idname='ffny.import_voice';bl_label='Import Voice Track'
    filepath:bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob:bpy.props.StringProperty(default='*.wav;*.mp3;*.flac;*.m4a;*.aiff;*.aif',options={'HIDDEN'})
    def invoke(self,context,event):context.window_manager.fileselect_add(self);return {'RUNNING_MODAL'}
    def execute(self,context):
        try:import_voice(self.filepath);return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}


class FFNY_OT_mouth_key(bpy.types.Operator):
    bl_idname='ffny.key_mouth';bl_label='Key Mouth Pose Here';bl_options={'UNDO'}
    def execute(self,context):
        try:
            stop_preview()
            scene=context.scene;data=mouth_data();tick=scene.frame_current-1
            if not 0<tick<BRIDGE.STATE['model'].duration:raise ValueError('First and last mouth keys stay closed; key inside the clip')
            for name,value in [('jaw',scene.ffny_jaw_open),('lips',int(scene.ffny_lip_shape))]:
                data[name]=sorted([r for r in data[name] if r[0]!=tick]+[[tick,value]])
            set_mouth(data);return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}


class FFNY_OT_jaw_guide(bpy.types.Operator):
    bl_idname='ffny.jaw_guide';bl_label='Generate Rough Jaw Guide';bl_options={'UNDO'}
    def execute(self,context):
        try:
            stop_preview()
            from fighter_caf_mouth import jaw_guide,PREVIEW_AUDIO_DELAY
            data=jaw_guide(voice_bytes(),speech_tick(),int(BRIDGE.STATE['model'].duration))
            data['lips']=mouth_data()['lips'];set_mouth(data)
            context.scene['ffny_status']='Amplitude guide only: refine closures and lip shapes manually';return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}



def generate_speech_guide():
    stop_preview()
    import datetime,uuid
    from fighter_caf_mouth import phoneme_guide,PREVIEW_AUDIO_DELAY
    scene=bpy.context.scene;raw=voice_bytes();helper=BRIDGE.STATE.get('helper_python')
    if not helper:raise ValueError('Open through the voice workbench launcher to enable the local aligner')
    transcript=scene.ffny_transcript.strip()
    if not transcript:raise ValueError('Enter the words spoken in the imported voice')
    folder=Path(BRIDGE.STATE['model'].document['output_dir']).parent/'alignment';folder.mkdir(exist_ok=True)
    wav=folder/(hashlib.sha256(raw).hexdigest()+'.wav')
    if wav.exists():
        if wav.read_bytes()!=raw:raise ValueError('Alignment audio checksum changed')
    else:wav.write_bytes(raw)
    target=folder/('phones-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]+'.json')
    script=Path(__file__).resolve().parents[1]/'fighter-speech-align.py'
    result=subprocess.run([helper,str(script),'--wav',str(wav),'--text',transcript,'--out',str(target)],capture_output=True,text=True,timeout=60)
    log=target.with_suffix('.log');log.write_text(result.stdout+result.stderr)
    if result.returncode:raise ValueError('Local alignment failed; see '+str(log))
    cues=json.loads(target.read_text());tick=speech_tick()
    mouth=phoneme_guide(cues,raw,tick,int(BRIDGE.STATE['model'].duration));set_mouth(mouth)
    scene['ffny_alignment']=str(target);scene['ffny_status']='Estimated phone guide loaded; refine closure timing and lip poses manually'
    return cues


class FFNY_OT_speech_guide(bpy.types.Operator):
    bl_idname='ffny.speech_guide';bl_label='Generate Lip Sync Guide';bl_options={'UNDO'}
    def execute(self,context):
        try:generate_speech_guide();return {'FINISHED'}
        except Exception as e:self.report({'ERROR'},str(e));return {'CANCELLED'}


class FFNY_OT_voice_timeline(bpy.types.Operator):
    bl_idname='ffny.voice_timeline';bl_label='Show Voice Waveform'
    def execute(self,context):
        areas=[a for a in context.screen.areas if a.type in ('DOPESHEET_EDITOR','TIMELINE','GRAPH_EDITOR','SEQUENCE_EDITOR')]
        if areas:
            area=min(areas,key=lambda a:a.height);area.type='SEQUENCE_EDITOR';area.spaces.active.view_type='SEQUENCER'
            s=voice_strip()
            if s:s.select=True
            region=next((r for r in area.regions if r.type=='WINDOW'),None)
            if region:
                with context.temp_override(area=area,region=region):bpy.ops.sequencer.view_all()
        return {'FINISHED'}


class FFNY_PT_voice(bpy.types.Panel):
    bl_label='Voice & Lip Sync';bl_idname='FFNY_PT_voice';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='FFNY'
    def draw(self,context):
        l=self.layout;s=context.scene;l.operator('ffny.import_voice')
        if not s.get('ffny_mouth_enabled'):l.label(text='Import audio to enable mouth controls');return
        l.label(text=s.get('ffny_voice_label','Imported voice'));l.label(text='%.3fs voice / %.3fs donor'%(s.get('ffny_voice_seconds',0),BRIDGE.STATE['model'].duration/30))
        l.operator('ffny.voice_timeline')
        row=l.row(align=True);row.operator('ffny.preview_play',text='Play 50%',icon='PLAY').speed=.5
        row.operator('ffny.preview_play',text='Play 100%',icon='PLAY').speed=1.
        if PREVIEW:
            l.operator('ffny.preview_stop',icon='PAUSE');l.label(text='Preview %d%% · Space/Esc stops'%(PREVIEW['speed']*100))
        l.label(text='Preview only · 50% lowers voice pitch')
        l.label(text='Set pose, then press Key Mouth Pose:')
        l.prop(s,'ffny_jaw_open',text='Jaw Open');l.prop(s,'ffny_lip_shape',text='Lip Shape')
        l.operator('ffny.key_mouth')
        l.separator();l.prop(s,'ffny_transcript',text='Spoken words');l.operator('ffny.speech_guide')
        l.label(text='Estimated timing; replaces mouth keys')
        l.operator('ffny.jaw_guide');l.label(text='Move mouth keys in the Graph Editor')
        l.label(text='Jaw keys: Linear · Lip IDs: Constant')
        l.label(text='Native lips blend between pose keys');l.label(text='First/last keys: closed / neutral')
        l.label(text='Lip poses are expressions, not named phonemes')


def register(bridge):
    global BRIDGE;BRIDGE=bridge
    for handlers in (bpy.app.handlers.load_pre,bpy.app.handlers.undo_pre,bpy.app.handlers.redo_pre):
        if preview_teardown not in handlers:handlers.append(preview_teardown)
    for c in (FFNY_OT_voice_import,FFNY_OT_mouth_key,FFNY_OT_jaw_guide,FFNY_OT_speech_guide,FFNY_OT_voice_timeline,FFNY_OT_preview_play,FFNY_OT_preview_stop,FFNY_PT_voice):bpy.utils.register_class(c)
    bpy.types.Scene.ffny_transcript=bpy.props.StringProperty(name='Spoken words',description='Exact English words in the imported recording',maxlen=500,options=set())
    bpy.types.Scene.ffny_jaw_open=bpy.props.FloatProperty(name='Jaw Open',min=0,max=1,default=0,options=set())
    bpy.types.Scene.ffny_lip_shape=bpy.props.EnumProperty(items=[(str(i),'Neutral' if i==0 else 'Native lip pose %02d'%i,'Native CAF lip-expression palette sample') for i in range(15)],options=set())
