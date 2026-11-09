"""Shared, hash-sealed export of a complete typed cinematic component."""
import hashlib
import json
from pathlib import Path
import re

from fighter_animation import AnimationEnvelope, require
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_behavior_files import unique_object
from fighter_cinematic_graphs import CinematicGraphs
from fighter_elf import Model
from fighter_face import FacePalettes
from fighter_rig import Skeleton
from fighter_timelines import TagTimelines,tag_rows
from mods import ordinary_path


def export_film(game,request_path,pins):
    request_path=ordinary_path(Path(request_path));raw=request_path.read_bytes()
    require(0<len(raw)<=65536,'Cinematic export request exceeds budget')
    request=json.loads(raw.decode('utf-8'),object_pairs_hook=unique_object)
    require(type(request) is dict and set(request)=={'format','template','model','bundle','tags','absent_tags'}
            and request['format']=='fighter-cinematic-export-request-1' and type(request['absent_tags']) is bool,
            'Unsupported cinematic export request')
    template=request['template'];require(type(template) is str and re.fullmatch(r'C[IE]_[A-Za-z0-9]{4}|BT[123]_[0-9]{2}|BT4C[0-9]{2}',template),
                                        'Cinematic export requires a verified role template')
    inputs={}
    def asset(spec):
        require(type(spec) is dict and set(spec)=={'path','sha256'},'Cinematic input needs path and SHA-256')
        path=ordinary_path(Path(spec['path']))
        with path.open('rb') as stream:data=stream.read(64*1024**2+1)
        require(0<len(data)<=64*1024**2 and hashlib.sha256(data).hexdigest()==spec['sha256'],'Cinematic source changed or exceeds budget')
        inputs[path]=spec['sha256'];return unpack(data)
    def original(relative,pin):
        data=(Path(game)/relative).read_bytes()
        require(len(data)<=512*1024**2 and hashlib.sha256(data).hexdigest()==pins[pin],'Cinematic export original differs from baseline')
        return data
    rig=Skeleton(Model(asset(request['model'])))
    data=asset(request['bundle']);bundle=Archive(data)
    bodies=[entry.name[:-2] for entry in bundle.entries if entry.name.endswith('.o') and not entry.name.endswith(('_f.o','_h.o','_EYE.o','_TARGET.o'))]
    require(len(bodies)==1 and re.fullmatch('[A-Za-z0-9_]{1,15}',bodies[0]),'Cinematic source needs one body member')
    token=bodies[0];require(token.startswith('CI_')==template.startswith('CI_'),'Cinematic layout differs from template category')
    compiler=CinematicGraphs(original('assets/v2ta.viv','v2ta_sha256'),pins['v2ta_sha256'])
    require((template+'.viv').lower() in compiler.archive.by_name,'Unknown verified cinematic template')
    misc=Archive(original('assets/misc.viv','misc_sha256'))
    hands=FacePalettes(Model(unpack(misc.read('share_hp.o'))),57,(32,32))
    value=compiler.convert(data,token,rig.pose_sha256,len(rig.rows))
    assigned='FI00000' if template.startswith('CI_') else 'FV00000' if template.startswith('CE_') else 'B00000'
    _compiled,receipt=compiler.compose(value,assigned,rig.pose_sha256,len(rig.rows),hands)
    tags=TagTimelines(original('audio/animtags.dat','tags_sha256'),pins['tags_sha256'])
    rows={row['name']:row for row in tag_rows(asset(request['tags']))}
    if request['absent_tags']:
        require(token not in rows,'Explicit absent timeline conflicts with a source tag row');timeline=None
    else:
        require(token in rows,'Source cinematic has no declared tag row')
        timeline=tags.library.export(rows[token]['events'])
        profile='cinematic-intro-1' if template.startswith('CI_') else 'cinematic-victory-1' if template.startswith('CE_') else 'cinematic-activation-1'
        tags.compose({assigned:{'profile':profile,'timeline':timeline}})
    require(request_path.read_bytes()==raw,'Cinematic request changed during export')
    for path,digest in inputs.items():require(hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Cinematic input changed during export')
    return {'component_compilation':True,'native_playtest':False,'graph':value,'tags':timeline,
            'source_token':token,'template':template,'receipt':receipt,
            'inputs':{str(path):digest for path,digest in inputs.items()},
            'source_format':'fighter-cinematic-2' if template.startswith(('CI_','CE_')) else 'fighter-blazin-5',
            'camera_policy':'native-venue' if template.startswith('BT4') else 'owned-relative'}
