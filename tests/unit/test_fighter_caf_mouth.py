"""Closed voice/mouth contract, quantization and clock tests; invented audio only."""
import copy,io,math,struct,wave
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_caf_mouth import (neutral_mouth,validate_mouth,jaw_leaf,decoded_jaw,sample_jaw,
                               quaternion,require_voice_fit,jaw_guide,apply_graphs,FORMAT)
from fighter_caf_cinematic import validate
from fighter_behavior_files import validate_source


def wav(seconds=1,rate=24000,channels=1):
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<h',int(10000*math.sin(i*.2))) for i in range(round(seconds*rate)*channels)))
    return out.getvalue()


def value():return dict(format=FORMAT,template='CI_113A',edits=[],mouth=neutral_mouth(106),speech_tick=0)


def test_explicit_profile_and_blaze_duration_are_admitted():
    v=value();validate(v);validate_source('cinematic',dict(v,format='fighter-cinematic-caf-performance-2'))
    with pytest.raises(ValueError):validate(dict(v,template='CI_113B'))
    with pytest.raises(ValueError):validate(dict(v,format='fighter-caf-cinematic-1'))
    with pytest.raises(ValueError):validate(dict(v,edits=[dict(selector=1,key=0,expected=0,sample=1)]))


@pytest.mark.parametrize('change',[
 lambda v:v['jaw'].append([100,0.]),lambda v:v['jaw'].__setitem__(0,[0,.1]),
 lambda v:v['jaw'].__setitem__(1,[65,float('nan')]),lambda v:v['jaw'].__setitem__(1,[65,True]),
 lambda v:v['jaw'].__setitem__(1,[65,1.01]),lambda v:v['jaw'].__setitem__(1,[64.5,0.]),
 lambda v:v['lips'].__setitem__(1,[65,15]),lambda v:v['lips'].__setitem__(1,[65,1.5]),
 lambda v:v.update(pointer=123),lambda v:v['jaw'].__setitem__(1,[66,0.]),
])
def test_rejects_unsafe_or_ambiguous_mouth_controls(change):
    v=neutral_mouth();change(v)
    with pytest.raises(ValueError):validate_mouth(v)


def test_quantized_jaw_keeps_native_destination_and_error_budget_at_keys_and_midpoints():
    rows=[[0,0.],[5,1.],[12,.25],[40,.8],[65,0.]];leaf=jaw_leaf(rows)
    assert leaf['destinations']==[832] and leaf['bits']==16 and leaf['times']==[5,12,40,65]
    for q,(_,v) in zip(decoded_jaw(leaf),rows):assert q==pytest.approx(quaternion(v),abs=.00005)
    q=sample_jaw(rows,2.5);assert sum(v*v for v in q)==pytest.approx(1.,abs=2e-6)
    assert math.degrees(2*math.acos(q[3]))==pytest.approx(6.,abs=.001)
    assert sample_jaw(rows,65)==pytest.approx((0,0,0,1),abs=.00005)


def test_long_voice_is_rejected_in_ice_t_and_fits_blaze_without_audio_trimming():
    raw=wav(3.135)
    with pytest.raises(ValueError,match='beyond'):require_voice_fit(raw,0,65)
    assert require_voice_fit(raw,0,106)['seconds']==pytest.approx(3.135)
    with pytest.raises(ValueError):require_voice_fit(raw,8,106)
    with pytest.raises(ValueError):require_voice_fit(wav(channels=2),0,106)
    with pytest.raises(ValueError):require_voice_fit(raw[:-2],0,106)


def test_rough_guide_is_bounded_neutral_at_edges_and_does_not_claim_phonemes():
    result=jaw_guide(wav(1),0,106);validate_mouth(result,106)
    assert result['jaw'][0]==[0,0.] and result['jaw'][-1]==[106,0.]
    assert result['lips']==[[0,0],[106,0]] and all(0<=r[1]<=.85 for r in result['jaw'])


def test_face_s_is_separate_from_palette_namespace_and_preserves_brows():
    source={'CI_113A_p':dict(duration_ticks=106,time_scale=29,children=[
        dict(kind=25,selector=0,times=[0,106],samples=[3,4]),dict(kind=25,selector=1,times=[0,106],samples=[1,2])])}
    saved=copy.deepcopy(source);mouth=neutral_mouth(106);mouth['lips']=[[0,0],[20,4],[106,0]]
    result=apply_graphs(source,mouth,'CI_113A')
    assert source==saved
    assert result['CI_113A_p']['children'][0]==source['CI_113A_p']['children'][0]
    assert len(result['CI_113A_p']['children'])==2
    assert result['CI_113A_s']['children'][0]['destinations']==[832]
    assert result['CI_113A_p']['children'][1]['times']==[0,20,106]


def test_phone_guide_preserves_bilabial_closure_and_rejects_wrong_audio_or_unmapped_data():
    import hashlib
    from fighter_caf_mouth import phoneme_guide
    raw=wav(1);cues=dict(schema='fighter-speech-cues-1',source_sha256=hashlib.sha256(raw).hexdigest(),words=[dict(phones=[
        dict(phone='AA',start=0.,end=.4),dict(phone='M',start=.4,end=.5),dict(phone='IY',start=.5,end=1.)])])
    result=phoneme_guide(cues,raw,0,106);validate_mouth(result,106)
    assert [17,0.] in result['jaw'] and [17,1] in result['lips']
    for change in [lambda c:c.update(source_sha256='00'*32),
                   lambda c:c['words'][0]['phones'][1].update(phone='POINTER'),
                   lambda c:c['words'][0]['phones'][1].update(start=.3),
                   lambda c:c['words'][0]['phones'][1].update(end=float('inf'))]:
        bad=copy.deepcopy(cues);change(bad)
        with pytest.raises(ValueError):phoneme_guide(bad,raw,0,106)


def test_native_preload_is_separate_from_timeline_and_general_bank_budgets():
    from fighter_voice import encode_stream,presentation_stream,parse_owned_stream
    # Same timing fits Blaze; high-rate PCM exceeds its fixed resident slot.
    with pytest.raises(ValueError,match='native preload'):require_voice_fit(wav(3.135,48000),0,106)
    assert require_voice_fit(wav(3.135,24000),0,106)['encoded_bytes']<153600
    large=encode_stream(bytes(100000*2),24000)
    assert parse_owned_stream(large).sample_count==100000
    with pytest.raises(ValueError,match='native preload'):presentation_stream(large,'intro')
    assert presentation_stream(large,'extro').sample_count==100000
    larger=encode_stream(bytes(260000*2),24000)
    with pytest.raises(ValueError,match='native preload'):presentation_stream(larger,'extro')


def test_workshop_authored_source_is_bound_to_its_voice_and_donor():
    import base64,hashlib
    from fighter_workshop import check
    raw=wav();source=dict(value(),format='fighter-cinematic-caf-performance-2')
    settings=dict(intro='CI_113A',voice=dict(preset='retail/blaze',banks={},clips={'intro':base64.b64encode(raw).decode()}),
                  cinematics={'intro':dict(source=source,voice_sha256=hashlib.sha256(raw).hexdigest())})
    choices=dict(cinematics=[dict(key='CI_113A',role='intro'),dict(key='CI_132A',role='intro')],fighters=[dict(key='retail/blaze',voice=1)],banks=[])
    assert check(settings,choices)['valid']
    bad=copy.deepcopy(settings);bad['intro']='CI_132A'
    with pytest.raises(ValueError):check(bad,choices)
    bad=copy.deepcopy(settings);bad['cinematics']['intro']['voice_sha256']='00'*32
    with pytest.raises(ValueError):check(bad,choices)


def test_blaze_victory_binds_extro_audio_and_keeps_intro_separate():
    import base64, hashlib
    from fighter_workshop import check
    raw=wav(3.135,48000)
    assert require_voice_fit(raw,0,106,purpose='extro')['encoded_bytes']>153600
    source=dict(value(),template='CE_113A',format='fighter-cinematic-caf-performance-2')
    settings=dict(victory='CE_113A',voice=dict(preset='retail/blaze',banks={},clips={'extro':base64.b64encode(raw).decode()}),
                  cinematics={'victory':dict(source=source,voice_sha256=hashlib.sha256(raw).hexdigest())})
    choices=dict(cinematics=[dict(key='CE_113A',role='victory'),dict(key='CI_113A',role='intro')],fighters=[dict(key='retail/blaze',voice=1)],banks=[])
    assert check(settings,choices)['valid']
    wrong=copy.deepcopy(settings);wrong['voice']['clips']={'intro':wrong['voice']['clips']['extro']}
    with pytest.raises(ValueError):check(wrong,choices)
    wrong=copy.deepcopy(settings);wrong['cinematics']['victory']['source']['template']='CI_113A'
    with pytest.raises(ValueError):check(wrong,choices)


def test_victory_speech_uses_only_verified_extro_start_and_preserves_other_events():
    from fighter_caf_mouth import speech_timeline
    from fighter_timelines import EventLibrary
    from types import SimpleNamespace
    events=[(0,[60,[0]]),(6,[68,[1]]),(72,[60,[1]]),(101,[60,[0]])]
    rows=[dict(name='CE_113A',events=events)]
    library=SimpleNamespace(by_name={'CE_113A':rows[0]},library=EventLibrary('tag',rows))
    result=library.library.compile(speech_timeline(library,'CE_113A',8))
    assert result==[(6,[68,[1]]),(8,[60,[0]]),(72,[60,[1]])]
    assert events==rows[0]['events']


def test_preview_calibration_moves_guide_only_and_keeps_native_fit_limits():
    raw=wav(1)
    late=jaw_guide(raw,0,106,preview_delay=5)
    early=jaw_guide(raw,0,106,preview_delay=3)
    assert early['jaw'][1][0]==late['jaw'][1][0]-2
    assert early['jaw'][0]==late['jaw'][0]==[0,0.]
    assert early['jaw'][-1]==late['jaw'][-1]==[106,0.]
    with pytest.raises(ValueError):jaw_guide(raw,0,106,preview_delay=True)
    with pytest.raises(ValueError):jaw_guide(raw,0,106,preview_delay=13)
    with pytest.raises(ValueError):jaw_guide(wav(3.3),0,106,preview_delay=12)
