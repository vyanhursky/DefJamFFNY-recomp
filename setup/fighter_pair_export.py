"""Verified-template component export shared with installed creator commands."""
import hashlib
import json
from pathlib import Path
import struct

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_compile import AnimationTemplate
from fighter_animation_graphs import FullMotionTemplate, ROLES, read_motion
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_behavior_files import unique_object
from fighter_elf import Model
from fighter_face import FacePalettes, declared_capacities
from fighter_rig import Skeleton
from mods import ordinary_path

MAX_FILE=64*1024**2
MAX_INPUT=256*1024**2


def export_pair(game,request_path,pins):
    request_path=ordinary_path(Path(request_path))
    with request_path.open('rb') as stream:
        request_bytes=stream.read(65537)
    require(len(request_bytes)<=65536,'Pair export request exceeds budget')
    request=json.loads(request_bytes.decode('utf-8'),object_pairs_hook=unique_object)
    timed=type(request) is dict and request.get('format')=='fighter-pair-export-request-2'
    require(type(request) is dict and set(request)=={'format','template_choice','model','face','subject','counterpart'}
            | ({'tags','cameras'} if timed else set())
            and request['format'] in ('fighter-pair-export-request-1','fighter-pair-export-request-2'),
            'Unsupported pair export request')
    choice=request['template_choice']
    require(type(choice) is int and 0<=choice<82,'Pair export requires an explicit retail behavior choice')
    inputs,used={},0

    def asset(spec):
        nonlocal used
        require(type(spec) is dict and set(spec)=={'path','sha256'},'Pair input requires path and hash')
        path=ordinary_path(Path(spec['path']))
        with path.open('rb') as stream:
            data=stream.read(MAX_FILE+1)
        used+=len(data)
        require(0<len(data)<=MAX_FILE and used<=MAX_INPUT and hashlib.sha256(data).hexdigest()==spec['sha256'],
                'Pair input changed or exceeds its byte budget')
        inputs[path]=spec['sha256']
        return unpack(data)

    rig=Skeleton(Model(asset(request['model'])))
    face_model=Model(asset(request['face']))
    face=FacePalettes(face_model,len(rig.rows),declared_capacities(face_model))

    def original(relative,pin):
        with (Path(game)/relative).open('rb') as stream:
            data=stream.read(512*1024**2+1)
        require(len(data)<=512*1024**2 and hashlib.sha256(data).hexdigest()==pins[pin],
                'Pair export original differs from its verified baseline')
        return data

    archive=Archive(original('motion/blazin.viv','blazin_sha256'))
    names=unpack(archive.read('blazin.mnl'))
    require(struct.unpack_from('<2I',names)==(164,0) and names.endswith(b'.'),'Unsupported original pair names')
    tokens=names[8:-1].decode('ascii').split('.')
    misc=Archive(original('assets/misc.viv','misc_sha256'))
    hand_data=unpack(misc.read('share_hp.o'))
    require(hashlib.sha256(hand_data).hexdigest()==pins['shared_hand_sha256'],'Shared hand identity differs')
    hands=FacePalettes(Model(hand_data),57,(32,32))
    graphs,receipts={},{}
    for role,offset in (('subject',0),('counterpart',1)):
        pair=request[role]
        require(type(pair) is dict and set(pair)=={'data','links'},'Pair role needs data and links')
        source=AnimationIndex(AnimationEnvelope(asset(pair['data']),asset(pair['links'])))
        candidates=[name[:-2] for name in source.names if name.endswith('_s')]
        require(len(candidates)==1 and set(source.names)=={candidates[0]+suffix for suffix in ROLES.values()},
                'Pair source must contain exactly five related motion graphs')
        source_token,template_token=candidates[0],tokens[2*choice+offset]
        trusted=AnimationEnvelope(*(unpack(archive.read(template_token+'.'+suffix)) for suffix in ('ord','orl')),
                                  struct.pack('<2I',1,0)+template_token.encode()+b'.')
        compiler=FullMotionTemplate(AnimationTemplate(trusted,hashlib.sha256(trusted.model.data).hexdigest(),
                                                     rig.pose_sha256,len(rig.rows)),face,hands)
        _compiled,receipt=compiler.convert(source,source_token,template_token)
        graphs[role]=read_motion(source,source_token,rig.pose_sha256,len(rig.rows))
        receipts[role]={'source_token':source_token,'template_token':template_token,
                        'compiled_sha256':receipt['sha256'],'source_controls_matched':True}
    timelines,validation=None,None
    if timed:
        from fighter_timelines import TagTimelines,CameraTimelines,tag_rows,camera_rows
        tag_base=TagTimelines(original('audio/animtags.dat','tags_sha256'),pins['tags_sha256'])
        camera_base=CameraTimelines(original('motion/camera.xml','camera_sha256'),pins['camera_sha256'])
        source_tags={row['name']:row for row in tag_rows(asset(request['tags']))}
        source_cameras=camera_rows(asset(request['cameras']))
        timelines={};tag_additions={}
        for role,letter in (('subject','A'),('counterpart','B')):
            name=receipts[role]['source_token']
            require(name in source_tags,'Source paired role has no tag timeline')
            timeline=tag_base.library.export(source_tags[name]['events'])
            timelines[role+'_tags']=timeline
            tag_additions['XPA0000'+letter]={'template':receipts[role]['template_token'],'timeline':timeline}
        tag_base.compose(tag_additions)
        name=receipts['subject']['source_token']
        candidates=[row for row in source_cameras if row['name']==name]
        require(candidates,'Source paired subject has no camera timetable')
        template=name if name in camera_base.by_name else receipts['subject']['template_token']
        timeline=camera_base.library.export(candidates[0]['events'])
        camera={'template':template,'timeline':timeline}
        camera_base.compose({'XPA0000A':camera});timelines['camera']=camera
        validation={'camera_selection':'first-native-match','shadowed_camera_schedules':len(candidates)-1,
                    'tag_payload_order_matched':True,'camera_nonshake_template_matched':True}
    require(request_path.read_bytes()==request_bytes,'Pair export request changed during compilation')
    for path,digest in inputs.items():
        with path.open('rb') as stream:
            data=stream.read(MAX_FILE+1)
        require(len(data)<=MAX_FILE and hashlib.sha256(data).hexdigest()==digest,'Pair source changed during compilation')
    return {'component_compilation':True,'native_playtest':False,'template_choice':choice,
            'rig_sha256':rig.pose_sha256,'bone_count':len(rig.rows),'graphs':graphs,
            'roles':receipts,'inputs':{str(path):digest for path,digest in inputs.items()},
            'required_source_format':'fighter-blazin-4' if timed else 'fighter-blazin-3',
            **({'timelines':timelines,'timeline_validation':validation} if timed else {})}
