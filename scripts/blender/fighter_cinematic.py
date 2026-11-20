"""Private-source Blender workbench for bounded FFNY cinematic cue authoring.

Run Blender with --python this_file -- --source source.json --create scene.blend.
No scripts are embedded for automatic execution. Reopen via the same launcher.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import bpy
from bpy.app.handlers import persistent
from mathutils import Matrix, Vector
import numpy as np

STATE = {}
LABELS = ('brow_squint', 'lips_sneer')


def action_curves():
    obj = bpy.data.objects['FFNY_Cues']
    if not obj.animation_data or not obj.animation_data.action:
        raise ValueError('Original cue action is missing')
    return obj.animation_data.action.fcurves


def read_cues():
    model = STATE['model']; curves = action_curves(); result = []
    if len(curves) != 2: raise ValueError('Keep the two original cue curves')
    obj=bpy.data.objects['FFNY_Cues']
    if obj.animation_data.drivers or obj.animation_data.nla_tracks: raise ValueError('Cue drivers/NLA layers are not supported')
    for i, label in enumerate(LABELS):
        curve = curves.find('["' + label + '"]')
        times = model.face_leaves[i]['times']
        if curve is None or len(curve.keyframe_points) != len(times):
            raise ValueError('Adding/removing cue keys is not supported yet')
        if curve.modifiers or curve.mute: raise ValueError('Cue modifiers/muting are not supported')
        values = []
        for time, key in zip(times, curve.keyframe_points):
            if abs(key.co.x - (time + 1)) > 1e-6 or key.interpolation != 'CONSTANT':
                raise ValueError('Keep original cue timing and Constant key interpolation')
            value = float(key.co.y)
            if not np.isfinite(value) or value != round(value):
                raise ValueError('Cue poses must use whole sample numbers')
            values.append(int(value))
        result.append(values)
    model.source(result)  # Full selector/sample/change-budget validation.
    return result


@persistent
def update_pose(scene, *_):
    if (not STATE or STATE.get('updating') or
            scene.get('ffny_workbench_source')!=STATE['source_sha256']): return
    STATE['updating'] = True
    try:
        model = STATE['model']; cues = read_cues()
        tick = max(0., min(model.duration, scene.frame_current_final - 1.))
        mouth=STATE['voice_module'].mouth_data() if STATE.get('voice_module') else None
        if STATE.get('voice_module'):STATE['voice_module'].sync_controls(scene,tick,mouth)
        worlds, matrices = model.matrices(tick,cues,mouth)
        from fighter_blender_preview import C, deform
        for part in model.document['meshes']:
            obj = bpy.data.objects['FFNY_Mesh_' + str(part['slot']) + '_' + str(part['rm'])]
            points, normals = deform(part['positions'], part['normals'], part['skin_indices'], part['skin_weights'], matrices)
            obj.data.vertices.foreach_set('co', points.astype(np.float32).ravel())
            obj.data.update()
            obj.data.normals_split_custom_set_from_vertices(normals.tolist())
        rig = bpy.data.objects['FFNY_NativeRig']
        for i, bone in enumerate(rig.pose.bones):
            bone.matrix = Matrix((C @ worlds[i] @ C.T).tolist())
        scene['ffny_native_tick'] = tick
        scene['ffny_status'] = 'Native source tick %.2f / %.2fs' % (tick, tick / 30)
        STATE['last_tick'] = tick;STATE.pop('error',None)
    except Exception as error:
        scene['ffny_status'] = str(error)
        STATE['error'] = str(error)
    finally:
        STATE['updating'] = False


def validate_scene():
    """Geometry/rig edits cannot silently enter the native performance export."""
    if STATE.get('error'): raise ValueError(STATE['error'])
    model = STATE['model']; cues = read_cues(); scene = bpy.context.scene
    tick = max(0., min(model.duration, scene.frame_current_final - 1.))
    from fighter_blender_preview import C, deform
    mouth=STATE['voice_module'].mouth_data() if STATE.get('voice_module') else None
    worlds, matrices = model.matrices(tick,cues,mouth)
    for part in model.document['meshes']:
        obj = bpy.data.objects['FFNY_Mesh_' + str(part['slot']) + '_' + str(part['rm'])]
        if (obj.modifiers or obj.data.shape_keys or obj.parent or
                not np.allclose(np.array(obj.matrix_world), np.eye(4), atol=1e-7) or
                not np.allclose(obj.location,(0,0,0),atol=1e-7) or
                not np.allclose(obj.rotation_euler,(0,0,0),atol=1e-7) or
                not np.allclose(obj.scale,(1,1,1),atol=1e-7)):
            raise ValueError('Restore original mesh transforms/modifiers; this bridge exports facial cues only')
        if len(obj.data.vertices) != len(part['positions']): raise ValueError('Mesh vertex population changed')
        indices = [int(v) for p in obj.data.polygons for v in p.vertices]
        if indices != part['indices']: raise ValueError('Mesh topology/index ordering changed')
        points, _ = deform(part['positions'], part['normals'], part['skin_indices'], part['skin_weights'], matrices)
        actual = np.array([v.co[:] for v in obj.data.vertices])
        if np.max(np.abs(points - actual)) > 5e-5: raise ValueError('Mesh geometry was edited outside the native preview')
        for loop in obj.data.loops:
            u, v = part['uv'][loop.vertex_index]; actual_uv = obj.data.uv_layers['NativeUV'].data[loop.index].uv
            if abs(actual_uv.x-u) > 1e-6 or abs(actual_uv.y-(1-v)) > 1e-6: raise ValueError('Original UVs changed')
        for vertex, (indices, weights) in enumerate(zip(part['skin_indices'], part['skin_weights'])):
            expected = {}
            for bone, weight in zip(indices, weights):
                if weight: expected[STATE['bone_names'][bone]] = expected.get(STATE['bone_names'][bone], 0) + weight
            actual = {obj.vertex_groups[g.group].name:g.weight for g in obj.data.vertices[vertex].groups}
            if set(actual) != set(expected) or any(abs(actual[n]-w)>1e-6 for n,w in expected.items()):
                raise ValueError('Original skin weights changed')
    rig = bpy.data.objects['FFNY_NativeRig']
    if rig.animation_data and rig.animation_data.action: raise ValueError('Direct bone animation export is not supported yet; use the facial cue controls')
    if len(rig.data.bones) != 94 or [b.name for b in rig.data.bones] != STATE['bone_names']:
        raise ValueError('Native rig bone names/indexing changed')
    for bone in rig.data.bones:
        reference = STATE['bone_rest'][bone.name]
        if not np.allclose(np.array(bone.matrix_local), reference, atol=1e-6): raise ValueError('Native rig rest display changed')
        index=STATE['bone_names'].index(bone.name);parent=model.skeleton.parents[index]
        if (bone.parent.name if bone.parent else None)!=(STATE['bone_names'][parent] if parent>=0 else None):
            raise ValueError('Native rig parent relationships changed')
    speech_tick=0
    if mouth is not None:
        from fighter_caf_mouth import require_voice_fit,PREVIEW_AUDIO_DELAY
        voice=STATE['voice_module'];speech_tick=voice.speech_tick()
        require_voice_fit(voice.voice_bytes(),speech_tick,int(model.duration),purpose=voice.voice_purpose())
    return model.source(cues,mouth,speech_tick)


def export(path):
    if STATE.get('voice_module'):STATE['voice_module'].stop_preview()
    source = validate_scene(); doc = STATE['model'].document
    result = dict(schema='fighter-blender-cinematic-export-1',project_sha256=doc['project_sha256'],
                  preview_source_sha256=STATE['source_sha256'],performance=source,
                  locked_layers=['body','root','hands','cameras','events','speech','geometry','rig','weights','uv','normal_contract'],
                  scene_validation='preserved native source; existing face sample references only',mesh_export=False)
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): raise ValueError('Choose a new export filename; existing evidence is preserved')
    if bpy.context.scene.get('ffny_mouth_enabled'):
        spec,raw=STATE['voice_module'].export_voice(path)
        result.update(schema='fighter-blender-cinematic-export-2',voice=spec)
        result['locked_layers']=['body','root','hands','cameras','non_speech_events','geometry','rig','weights','uv','normal_contract']
        with Path(spec['path']).open('xb') as stream:stream.write(raw)
    path.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    bpy.context.scene['ffny_status'] = 'Exported ' + path.name
    return result


class FFNY_OT_apply_pose(bpy.types.Operator):
    bl_idname = 'ffny.apply_pose'; bl_label = 'Apply Pose to This Key'; bl_options = {'UNDO'}
    def execute(self, context):
        try:
            selector = int(context.scene.ffny_selector); key = context.scene.ffny_key
            if context.scene.get('ffny_mouth_enabled') and selector==1:raise ValueError('Use the Lip Shape mouth track while voice authoring is enabled')
            leaf = STATE['model'].face_leaves[selector]
            if not 0 <= key < len(leaf['samples']): raise ValueError('Select an existing key index')
            curve = action_curves().find('["'+LABELS[selector]+'"]')
            curve.keyframe_points[key].co.y = context.scene.ffny_sample; curve.update()
            STATE.pop('error', None); read_cues(); context.scene.frame_set(leaf['times'][key]+1); update_pose(context.scene)
            return {'FINISHED'}
        except Exception as error:
            self.report({'ERROR'}, str(error)); return {'CANCELLED'}


class FFNY_OT_export(bpy.types.Operator):
    bl_idname = 'ffny.export_cinematic'; bl_label = 'Export Native Performance'
    def execute(self, context):
        try:
            export(context.scene.ffny_export_path); self.report({'INFO'}, 'Validated performance exported'); return {'FINISHED'}
        except Exception as error:
            self.report({'ERROR'}, str(error)); return {'CANCELLED'}


class FFNY_OT_reset(bpy.types.Operator):
    bl_idname = 'ffny.reset_cues'; bl_label = 'Restore Donor Facial Cues'; bl_options = {'UNDO'}
    def execute(self, context):
        for i, values in enumerate(STATE['model'].cues):
            curve = action_curves().find('["'+LABELS[i]+'"]')
            for key,value in zip(curve.keyframe_points,values): key.co.y=value
            curve.update()
        STATE.pop('error',None); update_pose(context.scene); return {'FINISHED'}


class FFNY_OT_native(bpy.types.Operator):
    bl_idname='ffny.test_native';bl_label='Export and Test in Game'
    def execute(self,context):
        try:
            if not STATE.get('native_helper'):raise ValueError('Open through the workbench launcher for native testing')
            path=Path(STATE['model'].document['output_dir'])/('performance-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.json')
            export(path);context.scene.ffny_export_path=str(path)
            log=path.with_suffix('.native.log');stream=log.open('w')
            process=subprocess.Popen([STATE['helper_python'],STATE['native_helper'],str(path)],stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            STATE['native_process']=process
            stream.close();context.scene['ffny_status']='Native preview is preparing; see '+log.name
            scene=context.scene
            def poll():
                result=process.poll()
                if result is None:return 1.0
                try:
                    scene['ffny_status']=('Native preview complete; receipt saved' if result==0 else 'Native preview failed; see '+log.name)
                    for area in bpy.context.screen.areas:
                        if area.type=='VIEW_3D':area.tag_redraw()
                except (ReferenceError,AttributeError):pass
                return None
            bpy.app.timers.register(poll,first_interval=1.0)
            self.report({'INFO'},'Native preview is preparing in a separate test workspace');return {'FINISHED'}
        except Exception as error:self.report({'ERROR'},str(error));return {'CANCELLED'}


class FFNY_PT_cinematic(bpy.types.Panel):
    bl_label = 'FFNY Performance'; bl_idname = 'FFNY_PT_cinematic'; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'FFNY'
    def draw(self, context):
        layout=self.layout;scene=context.scene
        if not STATE: layout.label(text='Open using the FFNY workbench launcher'); return
        model=STATE['model']; layout.label(text='Tupac / '+model.document.get('donor_label','Ice-T')+' entrance '+model.token); layout.label(text=scene.get('ffny_status',''))
        layout.prop(scene,'ffny_selector',text='Facial layer');layout.prop(scene,'ffny_key_choice',text='Key time')
        i=int(scene.ffny_selector); k=scene.ffny_key
        if 0<=k<len(model.cues[i]):
            tick=model.face_leaves[i]['times'][k];layout.label(text='Tick %s / %.3fs / Blender frame %s'%(tick,tick/30,tick+1))
            try: layout.label(text='Current pose: %d / allowed 0–%d'%(read_cues()[i][k],(12,14)[i]))
            except Exception as error: layout.label(text=str(error),icon='ERROR')
        layout.prop(scene,'ffny_sample_choice',text='Expression pose');layout.operator('ffny.apply_pose')
        layout.operator('ffny.reset_cues');layout.separator();layout.prop(scene,'ffny_export_path',text='Export file');layout.operator('ffny.export_cinematic')
        if STATE.get('native_helper'):
            row=layout.row();process=STATE.get('native_process');row.enabled=not process or process.poll() is not None;row.operator('ffny.test_native')
        layout.separator();layout.label(text='Body / root / hands / camera locked')
        layout.label(text='Voice & Lip Sync panel edits imported audio' if scene.get('ffny_mouth_enabled') else 'Original dialogue is a timing reference')
        layout.label(text='Direct bone edits are not exported yet')


def register():
    for cls in (FFNY_OT_apply_pose,FFNY_OT_export,FFNY_OT_reset,FFNY_OT_native,FFNY_PT_cinematic):
        bpy.utils.register_class(cls)
    def choose_selector(self,context):
        self.ffny_key_choice='0';self.ffny_sample_choice=str(STATE['model'].cues[int(self.ffny_selector)][0])
    bpy.types.Scene.ffny_selector=bpy.props.EnumProperty(items=[('0','Brows / squint','Native selector0'),('1','Lips / sneer','Native selector1')],update=choose_selector)
    bpy.types.Scene.ffny_key=bpy.props.IntProperty(default=3,min=0,max=4095)
    bpy.types.Scene.ffny_sample=bpy.props.IntProperty(default=7,min=0,max=14)
    def key_items(self,context):
        selector=int(self.ffny_selector);cache=STATE.setdefault('key_enum_items',{})
        if selector not in cache:cache[selector]=[(str(i),'%.3fs (frame%d)'%(t/30,t+1),'Original source tick '+str(t)) for i,t in enumerate(STATE['model'].face_leaves[selector]['times'])]
        return cache[selector]
    def choose_key(self,context):
        if self.ffny_key_choice:
            self.ffny_key=int(self.ffny_key_choice)
            tick=STATE['model'].face_leaves[int(self.ffny_selector)]['times'][self.ffny_key]
            self.frame_set(tick+1)
    def sample_items(self,context):
        selector=int(self.ffny_selector);cache=STATE.setdefault('sample_enum_items',{})
        if selector not in cache:cache[selector]=[(str(i),'Pose %02d'%i,'Existing native expression sample') for i in range((13,15)[selector])]
        return cache[selector]
    def choose_sample(self,context):
        if self.ffny_sample_choice:self.ffny_sample=int(self.ffny_sample_choice)
    bpy.types.Scene.ffny_key_choice=bpy.props.EnumProperty(items=key_items,update=choose_key)
    bpy.types.Scene.ffny_sample_choice=bpy.props.EnumProperty(items=sample_items,update=choose_sample)
    bpy.types.Scene.ffny_export_path=bpy.props.StringProperty(subtype='FILE_PATH')
    bpy.app.handlers.frame_change_post.append(update_pose)


def reference_rig():
    from fighter_blender_preview import C,global_matrices
    model=STATE['model'];names=[None]*94;worlds=global_matrices(model.defaults,model.skeleton.parents)
    for name,index in model.skeleton.bones.items():names[index]=name.removeprefix('__Bone:::')
    STATE['bone_names']=names;STATE['bone_rest']={}
    bpy.data.objects['FFNY_NativeRig'].hide_set(True)
    for i,name in enumerate(names):
        matrix=np.eye(4);matrix[:3,3]=(C@worlds[i])[:3,3];STATE['bone_rest'][name]=matrix


def configure_audio(document):
    scene=bpy.context.scene;editor=scene.sequence_editor_create()
    strips=editor.strips if hasattr(editor,'strips') else editor.sequences
    if not any(s.type=='SOUND' for s in strips):
        strip=strips.new_sound('Original dialogue reference / approx +0.17s native onset',document['audio_path'],channel=1,frame_start=6)
        strip.sound.pack()
    # Preserve the donor's native end, but allow hearing the whole reference.
    scene.frame_end=max(document['duration_ticks']+1,max(s.frame_final_end+1 for s in strips if s.type=='SOUND'))
    if 'Native sequence end' not in scene.timeline_markers:
        scene.timeline_markers.new('Native sequence end',frame=document['duration_ticks']+1)
    scene.sync_mode='AUDIO_SYNC'


def create(document):
    from fighter_blender_preview import C,global_matrices
    scene=bpy.context.scene;bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene.render.fps=30;scene.frame_start=1;scene.frame_end=document['duration_ticks']+1
    scene['ffny_workbench_source']=STATE['source_sha256']
    rig=bpy.data.objects.new('FFNY_NativeRig',bpy.data.armatures.new('Native94BoneIndexMap'));scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    model=STATE['model'];worlds=global_matrices(model.defaults,model.skeleton.parents)
    names=[None]*94
    for name,index in model.skeleton.bones.items(): names[index]=name.removeprefix('__Bone:::')
    for i,name in enumerate(names):
        bone=rig.data.edit_bones.new(name);bone.head=(C@worlds[i])[:3,3];bone.tail=Vector(bone.head)+(Vector((0,.12,0)))
        if model.skeleton.parents[i]>=0:bone.parent=rig.data.edit_bones[names[model.skeleton.parents[i]]]
    bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True;rig.hide_render=True;rig.display_type='WIRE'
    rig.hide_set(True)
    rig['deformation']='Native CPU skinning with original affine inverse binds; armature displays physical channel hierarchy'
    for i,bone in enumerate(rig.data.bones):
        bone['native_index']=i;bone['stored_inverse_bind']=list(model.skeleton.rows[i][12:]);bone['native_permutation']=model.skeleton.rows[i][11]
        pb=rig.pose.bones[bone.name];pb.lock_location=(True,)*3;pb.lock_rotation=(True,)*3;pb.lock_scale=(True,)*3
    materials={}
    for slot,row in document['textures'].items():
        image=bpy.data.images.load(row['path'],check_existing=True);image.alpha_mode='CHANNEL_PACKED';image.pack()
        for transparent in (False,True):
            material=bpy.data.materials.new('NativeAtlas_'+slot+('_cutout' if transparent else ''));material.use_nodes=True
            nodes=material.node_tree.nodes;bs=nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.85
            tex=nodes.new('ShaderNodeTexImage');tex.image=image;material.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
            if transparent:material.node_tree.links.new(tex.outputs['Alpha'],bs.inputs['Alpha']);material.surface_render_method='DITHERED'
            materials[(slot,transparent)]=material
    for part in document['meshes']:
        name='FFNY_Mesh_'+str(part['slot'])+'_'+str(part['rm']);mesh=bpy.data.meshes.new(name)
        points=np.asarray(part['positions'])@C[:3,:3].T;indices=part['indices']
        mesh.from_pydata(points.tolist(),[],[indices[i:i+3] for i in range(0,len(indices),3)]);mesh.update()
        native_ids=mesh.attributes.new('native_vertex_index','INT','POINT');native_ids.data.foreach_set('value',range(len(points)))
        uv=mesh.uv_layers.new(name='NativeUV')
        for polygon in mesh.polygons:
            polygon.use_smooth=True
            for li in polygon.loop_indices:
                u,v=part['uv'][mesh.loops[li].vertex_index];uv.data[li].uv=(u,1-v)
        obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj);obj.data.materials.append(materials[(part['atlas'],bool(part['transparent']))]);obj.hide_select=True
        obj['native_part']=part['source_model'];obj['native_slot']=str(part['slot']);obj['native_rm']=part['rm']
        for i,name in enumerate(names):obj.vertex_groups.new(name=name)
        for i,(ids,weights) in enumerate(zip(part['skin_indices'],part['skin_weights'])):
            totals={}
            for bone,weight in zip(ids,weights):
                if weight:totals[bone]=totals.get(bone,0)+weight
            for bone,weight in totals.items():obj.vertex_groups[bone].add([i],weight,'REPLACE')
    cues=bpy.data.objects.new('FFNY_Cues',None);scene.collection.objects.link(cues);cues.animation_data_create();cues.animation_data.action=bpy.data.actions.new('NativeFacePaletteCues')
    for i,label in enumerate(LABELS):
        cues[label]=model.cues[i][0];curve=cues.animation_data.action.fcurves.new('["'+label+'"]')
        for time,value in zip(model.face_leaves[i]['times'],model.cues[i]):
            key=curve.keyframe_points.insert(time+1,value);key.interpolation='CONSTANT'
    bpy.ops.object.select_all(action='DESELECT');cues.select_set(True);bpy.context.view_layer.objects.active=cues
    for i in range(2):
        for tick in model.face_leaves[i]['times']:scene.timeline_markers.new(('Brow' if i==0 else 'Lips')+' tick'+str(tick),frame=tick+1)
    scene['ffny_notice']=document['source_notice']
    text=bpy.data.texts.new('FFNY_README');text.write('Use the FFNY sidebar. Frame1=source tick0. Edit existing face pose samples, then export. Body/root/hands/geometry remain preserved. Native CPU skinning retains original inverse binds; the armature is the actual94-channel hierarchy, not a free bone-animation exporter. Reopen through the workbench launcher to enable playback.\n')
    camera=bpy.data.objects.new('PerformanceCamera',bpy.data.cameras.new('PerformanceCamera'));scene.collection.objects.link(camera);scene.camera=camera
    target=Vector((0,0,18.5));camera.location=(4,-18,20.5);camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=8
    for name,loc,power,size in [('Key',(-7,-12,26),1800,8),('Fill',(8,-8,21),1200,8)]:
        light=bpy.data.objects.new(name,bpy.data.lights.new(name,'AREA'));scene.collection.objects.link(light);light.location=loc;light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler();light.data.energy=power;light.data.size=size
    scene.world.color=(.18,.18,.18);scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.view_settings.view_transform='Standard';scene.render.image_settings.file_format='PNG'
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.show_region_ui=True;area.spaces.active.shading.type='MATERIAL'
    reference_rig()
    configure_audio(document);scene.frame_set(35);update_pose(scene)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--create');parser.add_argument('--save');parser.add_argument('--export');parser.add_argument('--cue',nargs=3,type=int);parser.add_argument('--render');parser.add_argument('--audit');parser.add_argument('--native-helper');parser.add_argument('--helper-python');parser.add_argument('--audio-converter');parser.add_argument('--voice');parser.add_argument('--jaw-guide',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    for destination in (args.create,args.save):
        if destination and Path(destination).exists():raise ValueError('Choose a new Blender filename; prior scenes are retained')
    path=Path(args.source);document=json.loads(path.read_text());sys.path.insert(0,document['runtime_setup'])
    from fighter_blender_preview import Preview,fingerprint
    checksum=document['immutable_sha256'];copy=dict(document);copy.pop('immutable_sha256');assert fingerprint(copy)==checksum,'Preview source fingerprint differs'
    STATE.update(model=Preview(document),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    if args.helper_python:STATE['helper_python']=str(Path(args.helper_python).absolute())
    if args.native_helper and args.helper_python:STATE['native_helper']=str(Path(args.native_helper).resolve())
    register()
    if document['schema']=='fighter-blender-preview-2':
        sys.path.insert(0,str(Path(__file__).parent))
        import fighter_voice_controls
        fighter_voice_controls.register(sys.modules[__name__]);STATE['voice_module']=fighter_voice_controls
        if args.audio_converter:STATE['audio_converter']=str(Path(args.audio_converter).resolve())
    if args.create:create(document)
    else:
        if 'FFNY_Cues' not in bpy.context.scene.objects or 'FFNY_NativeRig' not in bpy.context.scene.objects:
            raise ValueError('Open a prepared FFNY workbench scene')
        bpy.context.scene['ffny_workbench_source']=STATE['source_sha256']
        reference_rig();configure_audio(document);update_pose(bpy.context.scene)
    if args.voice:
        STATE['voice_module'].import_voice(args.voice)
    if args.jaw_guide:assert bpy.ops.ffny.jaw_guide()=={'FINISHED'}
    scene=bpy.context.scene;scene.ffny_export_path=str(Path(document['output_dir'])/(STATE['model'].token+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json'))
    scene.ffny_key_choice=str(scene.ffny_key);scene.ffny_sample_choice=str(scene.ffny_sample)
    if args.cue:
        scene.ffny_selector=str(args.cue[0]);scene.ffny_key=args.cue[1];scene.ffny_sample=args.cue[2]
        scene.ffny_key_choice=str(args.cue[1]);scene.ffny_sample_choice=str(args.cue[2])
        assert bpy.ops.ffny.apply_pose()=={'FINISHED'}
    if args.export:export(args.export)
    if args.render:scene.render.filepath=args.render;bpy.ops.render.render(write_still=True)
    if args.audit:
        audit=Path(__file__).with_name('fighter_voice_audit.py' if bpy.context.scene.get('ffny_mouth_enabled') else 'fighter_cinematic_audit.py');namespace={'bridge':sys.modules[__name__],'output':Path(args.audit)};exec(compile(audit.read_text(),str(audit),'exec'),namespace)
    if args.create or args.save:bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.create or args.save).resolve()))
    print('FFNY_BLENDER_READY',scene.get('ffny_status'))


if __name__=='__main__':main()
