import base64
import hashlib
import io
from pathlib import Path
import struct
import sys
import wave

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
from fighter_behavior_identity import caf_key, valid
from fighter_workshop import decode_audio, check
from fighter_voice import encode_stream
from fighter_voice_compile import encode_voice_bindings
from fighter_ai import encode_ai_bindings
from test_fighter_voice_compile import source, voice
from test_fighter_ai import source as ai_source, profile
from test_fighter_voice_r2 import source as r2_source


def test_caf_bindings_keep_shared_motion_core_out_of_identity():
    _,compiler=source();data,receipt=compiler.compose({'test/a':voice(1),'test/b':voice(2)})
    keys={caf_key(1001):'test/a',caf_key(1002):'test/b',256:'test/a'}
    table=encode_voice_bindings(data,receipt,keys)
    assert table[:8]==b'FVA3\x03\0\0\0'
    assert [struct.unpack_from('<I',table,48+i*12)[0] for i in range(3)]==sorted(keys)
    assert struct.unpack_from('<I',table,64)[0]!=struct.unpack_from('<I',table,76)[0]
    _,compiler=ai_source();data,receipt=compiler.compose({'test/a':profile(),'test/b':profile()})
    table=encode_ai_bindings(data,receipt,keys)
    assert table[:8]==b'FIA2\x02\0\0\0'
    assert [struct.unpack_from('<I',table,48+i*36)[0] for i in range(3)]==sorted(keys)


@pytest.mark.parametrize('selection',[True,99,-1,0x7fffffff])
def test_refuses_non_roster_caf_identity(selection):
    with pytest.raises(ValueError):caf_key(selection)
    assert not valid(selection)


def test_pcm_audition_preserves_samples():
    pcm=struct.pack('<5h',-32768,-1,0,1,32767)
    with wave.open(io.BytesIO(decode_audio(encode_stream(pcm,24000,2))),'rb') as audio:
        assert audio.getframerate()==24000 and audio.readframes(5)==pcm


def test_check_requires_original_clip_bounds_and_role():
    catalog=dict(fighters=[dict(key='retail/pockets',voice=510)],banks=[dict(category='Character',voice=510,count=2)],
                 cinematics=[dict(key='CI_0001',role='intro')],ai=[])
    value=dict(voice=dict(preset='retail/pockets',banks={},clips={'Character:1':'opaque'}))
    assert check(value,catalog)['valid']
    value['voice']['clips']={'Character:2':'opaque'}
    with pytest.raises(ValueError):check(value,catalog)


def test_r2_literal_histories_feed_predictive_block_across_packets():
    # R2 literal headers contain the next predictor histories, independently
    # of the 28 literal output samples (including a partial final packet).
    literal=b'\xee'+struct.pack('>30h',1600,-100,*range(28))
    raw=r2_source((28,3),[literal,b'\x1c'+bytes(14)])
    with wave.open(io.BytesIO(decode_audio(raw)),'rb') as stream:
        samples=struct.unpack('<31h',stream.readframes(31))
    assert samples[:28]==tuple(range(28))
    assert samples[28:]==(1500,1406,1318)


def test_invented_body_and_root_tracks_keep_literal_bone_destinations():
    from test_fighter_animation_graphs import graph_template,motion
    from fighter_animation import AnimationIndex
    from fighter_workshop_animation import tracks
    envelope,_=graph_template().compose('A',motion())
    rows=tracks(AnimationIndex(envelope),'A')
    assert {r[0] for r in rows}=={'body','root'}
    assert all(0<=n<2 for row in rows for n in row[3])
    assert all(len(row[2].sample(0))==len(row[3]) for row in rows if row[1]!=13)


def test_new_typed_presets_do_not_need_fabricated_asset_files(tmp_path):
    from fighter_behavior_files import Reader,validate_source
    reader=Reader()
    assert reader.resource(tmp_path,'voice',dict(format='fighter-voice-retail-1',donor='retail/pockets'))==dict(retail_donor='retail/pockets')
    assert reader.resource(tmp_path,'cinematic',dict(format='fighter-cinematic-retail-1',template='CI_0001'))==dict(template='CI_0001',tracks=None)
    ai=dict(format='fighter-ai-2',template_profile='char0005',tendencies={l:{str(i):{} for i in range(4)} for l in ['easy','normal','hard']})
    assert reader.resource(tmp_path,'ai',ai)['tendencies']==dict(easy={},normal={},hard={})
    ai['format']='fighter-ai-1'
    with pytest.raises(ValueError):validate_source('ai',ai)
