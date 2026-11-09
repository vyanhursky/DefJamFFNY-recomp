"""Invented full cinematic graphs: fresh storage and bounded role semantics."""
from copy import deepcopy
import hashlib
import pytest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"setup"))
from fighter_cinematic_graphs import CinematicGraphs,FORMAT,member_roles,read_cinematic
from fighter_animation_numeric import FORMAT as NUMERIC
from fighter_assets import AssetError
from fighter_face import FacePalettes
from test_fighter_animation_graphs import graph_template,motion,RIG


def fixture():
    template=graph_template().template.index.model
    compiler=object.__new__(CinematicGraphs)
    compiler.attributes={0x3030301D,0x3030301E};compiler.controls={};compiler.headers={};compiler.envelopes={}
    for suffix,roles in member_roles('CE_0000').items():
        compiler.envelopes[suffix]=template
        for role in roles:
            kind=25 if suffix in ('_f.o','_h.o') else 18 if role=='rotation' else 20
            compiler.controls[suffix,role]={'parent':{0x3F23},'leaf':{kind:{0x3F23}},'padding':{0xEA}}
            if kind==20:compiler.headers[suffix,role,kind]={(0,0)}
    source=motion();members={}
    for suffix,roles in member_roles('CE_0000').items():
        members[suffix]={}
        for role in roles:
            if role=='pose':children=[]
            else:
                leaf=deepcopy(source['graphs']['body' if role=='rotation' else 'root']['children'][0])
                children=[{'format':NUMERIC,'kind':leaf['kind'],'keys':2,'block_shift':0,
                    'destinations':leaf['destinations'],'constant_destinations':[],
                    'coefficients':leaf['coefficients'],'blocks':[{'seeds':row,'deltas':[]} for row in leaf['samples']],
                    'static':[],'times':leaf['times'],'unused_header':[] if role=='rotation' else [0,0]}]
                if suffix not in ('.o','_f.o','_h.o') and role=='rotation':
                    children[0]['destinations']=[0];children[0]['coefficients']=children[0]['coefficients'][:1]
                    for block in children[0]['blocks']:block['seeds']=block['seeds'][:1]
            members[suffix][role]={'duration_ticks':91,'time_scale':29,'children':children}
    value={'format':FORMAT,'rig_sha256':RIG,'bone_count':2,'layout':'single-camera','members':members}
    hands=object.__new__(FacePalettes);hands.frame_counts=(32,32)
    return compiler,value,hands


def test_fresh_cinematic_rebuild_preserves_all_roles_and_explicit_empty_parents():
    compiler,value,hands=fixture()
    data,report=compiler.compose(value,'FV00000',RIG,2,hands)
    assert read_cinematic(data,'FV00000',RIG,2)==value
    assert report['members']==5 and report['hand_frames']==[0,0] and report['decoded_key_checks']>0
    assert data==compiler.compose(value,'FV00000',RIG,2,hands)[0]


@pytest.mark.parametrize('change',[
    lambda v:v.update(bone_count=True),
    lambda v:v.update(layout='arbitrary'),
    lambda v:v['members']['.o']['rotation']['children'][0]['destinations'].__setitem__(1,2),
    lambda v:v['members']['_EYE.o']['position']['children'][0]['destinations'].__setitem__(0,63),
    lambda v:v['members']['_TARGET.o']['position']['children'][0].update(unused_header=[255,255]),
    lambda v:v['members']['.o']['position'].update(time_scale=60),
    lambda v:v['members']['.o']['rotation']['children'][0]['blocks'][0]['seeds'][0].__setitem__(3,8192),
    lambda v:v['members']['_EYE.o']['position']['children'].append(deepcopy(v['members']['_EYE.o']['position']['children'][0])),
])
def test_full_cinematic_rejects_unproved_controls_and_output_escapes(change):
    compiler,value,hands=fixture();change(value)
    with pytest.raises(AssetError):compiler.compose(value,'FV00000',RIG,2,hands)
