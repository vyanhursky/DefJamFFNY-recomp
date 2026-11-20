"""Invented left-finger authoring inputs; no game data or destination input."""
import copy
import math
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf_hand import FORMAT,DESTINATIONS,validate_hand,apply_graphs,weight_at
from fighter_caf_mouth import neutral_mouth,FORMAT as PERFORMANCE_FORMAT,decoded_jaw
from fighter_caf_cinematic import validate
from fighter_behavior_files import validate_source


def value():
    q=[math.sin(.2),0.,0.,math.cos(.2)]
    return dict(format=FORMAT,pose=[q[:] for _ in range(15)],envelope=[[0,0],[19,0],[24,1],[39,1],[44,0],[106,0]])


def test_closed_caf_victory_source_admits_hand_and_refuses_other_donors():
    source=dict(format=PERFORMANCE_FORMAT,template='CE_113A',edits=[],mouth=neutral_mouth(106),speech_tick=0,left_hand=value())
    validate(source);validate_source('cinematic',dict(source,format='fighter-cinematic-caf-performance-2'))
    with pytest.raises(ValueError):validate(dict(source,template='CI_113A'))
    with pytest.raises(ValueError):validate_hand(value(),'CE_113B')


@pytest.mark.parametrize('change',[
 lambda x:x.update(pointer=1),lambda x:x.update(destinations=[4]),lambda x:x['pose'].pop(),
 lambda x:x['pose'][0].__setitem__(0,float('nan')),lambda x:x['pose'][0].__setitem__(0,True),
 lambda x:x['pose'].__setitem__(0,[0.,0.,0.,0.]),lambda x:x['envelope'].__setitem__(0,[0,1]),
 lambda x:x['envelope'].__setitem__(-1,[106,.1]),lambda x:x['envelope'].__setitem__(1,[0,0]),
 lambda x:x['envelope'].__setitem__(1,[19,1.01]),lambda x:x['envelope'].__setitem__(1,[19.5,0]),
 lambda x:x['envelope'].__setitem__(1,[19,True]),
])
def test_refuses_unsafe_or_ambiguous_hand_data(change):
    x=value();change(x)
    with pytest.raises(ValueError):validate_hand(x,'CE_113A')


def test_generated_left_writer_cannot_overwrite_right_or_body_and_returns_to_donor():
    left=dict(kind=25,selector=0,times=[0,44,52,105],samples=[21,21,9,9])
    right=dict(kind=25,selector=1,times=[0,46,53,105],samples=[21,21,20,20])
    graph={'CE_113A_p':dict(duration_ticks=106,time_scale=29,children=[left,right])};saved=copy.deepcopy(graph)
    frame=tuple((0.,0.,0.,1.) for _ in range(15));palette=SimpleNamespace(quaternion_destinations=DESTINATIONS,vector_destinations=(),frames=[frame]*32)
    out=apply_graphs(graph,value(),'CE_113A',SimpleNamespace(palettes=[palette]))
    assert graph==saved and out['CE_113A_p']['children']==[right]
    leaf=out['CE_113A_s']['children'][0];assert leaf['destinations']==list(DESTINATIONS)
    assert set(d//12 for d in leaf['destinations'])==set(range(21,36))
    assert leaf['bits']==16 and leaf['times']==list(range(1,107))
    poses=decoded_jaw(leaf)
    for tick in [0,19,44,80,106]:assert poses[tick]==pytest.approx([v for q in frame for v in q],abs=.0002)
    assert poses[30]==pytest.approx([v for q in value()['pose'] for v in q],abs=.0002)
    assert 0<weight_at(value()['envelope'],21.5)<1
    bad=SimpleNamespace(quaternion_destinations=tuple(reversed(DESTINATIONS)),vector_destinations=(),frames=[frame]*32)
    with pytest.raises(ValueError):apply_graphs(graph,value(),'CE_113A',SimpleNamespace(palettes=[bad]))
