"""Creator files remain bounded data before native behavior composition."""
import hashlib
import io
import json
import struct
import wave
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))

from fighter_assets import AssetError
from fighter_behavior_files import Reader, quaternion_file, wav_file, validate_source
from fighter_voice import parse_stream


def pose():
    return {'schema': 'fighter-quaternions-1', 'rig_sha256': 'a' * 64,
            'bone_count': 1, 'poses': [[[0, 0, 0, 1]], [[0, 0, 0, 1]]]}


def descriptor(root, name, data):
    (root / name).write_bytes(data)
    return {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}


def wav(channels=1):
    output = io.BytesIO()
    with wave.open(output, 'wb') as audio:
        audio.setparams((channels, 2, 24000, 0, 'NONE', 'not compressed'))
        audio.writeframes(struct.pack('<8h', 0, 1, -2, 100, -100, 1, -1, 0))
    return output.getvalue()


def test_voice3_reads_explicit_category_templates_and_typed_files(tmp_path):
    audio = {**descriptor(tmp_path, 'voice.wav', wav()), 'format': 'wav-pcm16'}
    source = {'format': 'fighter-voice-3', 'banks': {
        category: {'template_voice': template, 'family': family, 'samples': {'0': audio}}
        for category, template, family in [('Character', 0, 1), ('Taunts', 22, 16626), ('Enviro', 12, 40963)]},
        'intro': audio, 'extro': audio}
    result = Reader().resource(tmp_path, 'voice', source)
    assert result['banks']['Taunts']['template_voice'] == 22
    assert result['banks']['Character']['family'] == 1
    assert parse_stream(result['banks']['Enviro']['samples'][0]).sample_count == 8
    source['banks']['Taunts']['family'] = 1
    with pytest.raises(AssetError, match='family'):
        validate_source('voice', source)


def test_moveset_reader_produces_typed_complete_rig_tracks(tmp_path):
    spec = descriptor(tmp_path, 'pose.json', json.dumps(pose()).encode())
    source = {'format': 'fighter-moveset-1', 'donor': 'retail/example',
              'selections': {'54': 55}, 'tracks': {'N0001_A': spec}}
    result = Reader().resource(tmp_path, 'moveset', source)
    assert result['selections'] == {54: 55}
    track = result['tracks']['N0001_A']
    assert track.bones == (0,) and len(track.poses) == 2
    track.encode()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), 10**400, True])
def test_invalid_quaternion_numbers_are_rejected(value):
    doc = pose()
    doc['poses'][0][0][0] = value
    with pytest.raises(AssetError):
        quaternion_file(json.dumps(doc).encode())


def test_duplicate_json_members_and_incomplete_rigs_are_rejected():
    data = json.dumps(pose()).encode()
    with pytest.raises(AssetError):
        quaternion_file(data[:-1] + b',"bone_count":1}')
    doc = pose()
    doc['bone_count'] = 2
    with pytest.raises(AssetError, match='complete rig'):
        quaternion_file(json.dumps(doc).encode())


def test_voice_reader_converts_pcm_without_accepting_native_banks(tmp_path):
    spec = descriptor(tmp_path, 'voice.wav', wav())
    source = {'format': 'fighter-voice-1', 'template_voice': 22,
              'samples': {'Character': {'0': spec}}, 'intro': spec, 'extro': spec}
    result = Reader().resource(tmp_path, 'voice', source)
    assert result['intro'] == result['extro'] == result['samples']['Character'][0]
    parse_stream(result['intro'])
    with pytest.raises(AssetError):
        wav_file(wav(channels=2))
    with pytest.raises(AssetError):
        wav_file(wav()[:-2])


def test_reader_checks_hash_path_and_aggregate_budget(tmp_path):
    spec = descriptor(tmp_path, 'data', b'12345678')
    reader = Reader(10)
    assert reader.file(tmp_path, spec) == b'12345678'
    with pytest.raises(AssetError, match='budget'):
        reader.file(tmp_path, spec)
    with pytest.raises(AssetError, match='hash'):
        Reader().file(tmp_path, {**spec, 'sha256': '0' * 64})
    with pytest.raises(ValueError):
        Reader().file(tmp_path, {**spec, 'path': '../data'})


def test_typed_voice_reader_mixes_pcm_and_validated_r2_without_codec_guessing(tmp_path):
    from test_fighter_voice_r2 import source as r2_source
    from fighter_voice import parse_owned_stream
    from fighter_voice_r2 import inspect_source
    pcm = {**descriptor(tmp_path, 'spoken.wav', wav()), 'format': 'wav-pcm16'}
    coded = {**descriptor(tmp_path, 'reaction.bin', r2_source()), 'format': 'ea-adpcm-r2'}
    source = {'format': 'fighter-voice-2', 'template_voice': 22,
              'samples': {'Character': {'0': coded}}, 'intro': pcm, 'extro': coded}
    result = Reader().resource(tmp_path, 'voice', source)
    assert parse_owned_stream(result['intro']).metadata()['native_codec'] == 8
    assert parse_owned_stream(result['extro']).metadata()['native_codec'] == 10
    assert inspect_source(result['extro']).packets == inspect_source(r2_source()).packets
    with pytest.raises(AssetError, match='Unsupported typed voice'):
        Reader().resource(tmp_path, 'voice', {**source, 'intro': {**pcm, 'format': 'guess'}})
    with pytest.raises(AssetError):
        Reader().resource(tmp_path, 'voice', {**source, 'format': 'fighter-voice-1'})


def test_ai_has_closed_named_tendencies():
    source = {'format': 'fighter-ai-1', 'template_profile': 'char0005',
              'tendencies': {d: {str(i): {'Blazin_Frequency': 5} for i in range(4)}
                             for d in ('easy', 'normal', 'hard')}}
    result = Reader().resource(None, 'ai', source)
    assert result['tendencies']['normal'][3] == {'Blazin_Frequency': 5}
    source['tendencies']['hard']['0']['Specification_environment'] = 1
    with pytest.raises(AssetError, match='named tendency'):
        validate_source('ai', source)


def test_cinematic_reader_rejects_code_and_wrong_sequence_template(tmp_path):
    spec = descriptor(tmp_path, 'pose.json', json.dumps(pose()).encode())
    source = {'format': 'fighter-cinematic-1', 'template': 'CI_113A', 'track': spec}
    assert Reader().resource(tmp_path, 'cinematic', source)['tracks'].bone_count == 1
    for bad in ({**source, 'hook': 0x1234}, {**source, 'template': 'BT4V_any'}):
        with pytest.raises(AssetError):
            validate_source('cinematic', bad)


def test_blazin_reader_preserves_roles_and_allows_partial_body_authoring(tmp_path):
    from copy import deepcopy
    spec = descriptor(tmp_path, 'pose.json', json.dumps(pose()).encode())
    source = {'format': 'fighter-blazin-1', 'shots': [
        {'template': token} for token in ('BT1_01', 'BT2_01', 'BT3_01', 'BT4C01')]}
    source['shots'][0]['track'] = spec
    result = Reader().resource(tmp_path, 'blazin', source)
    assert result['shots'][0]['tracks'].bone_count == 1
    assert result['shots'][3] == {'template': 'BT4C01', 'tracks': None}
    assert result['pairs'] == {}
    paired = deepcopy(source); paired['pairs'] = {'2': {'subject': spec, 'counterpart': spec}}
    result = Reader().resource(tmp_path, 'blazin', paired)
    assert result['pairs'][2]['subject'].bone_count == result['pairs'][2]['counterpart'].bone_count == 1
    for bad in ({'82': paired['pairs']['2']}, {'2': {'subject': spec}}, {'02': paired['pairs']['2']}):
        with pytest.raises(AssetError):
            validate_source('blazin', {**source, 'pairs': bad})
    for field, value in [('template', 'BT4V01A'), ('address', 123), ('track', None)]:
        invalid = deepcopy(source)
        invalid['shots'][3][field] = value
        with pytest.raises(AssetError):
            validate_source('blazin', invalid)
    source['shots'].pop()
    with pytest.raises(AssetError):
        validate_source('blazin', source)


def test_blazin_slots_are_explicit_bounded_and_cannot_mix_with_choice_pairs(tmp_path):
    from copy import deepcopy
    spec = descriptor(tmp_path, 'pose.json', json.dumps(pose()).encode())
    pair = {'template_choice': 2, 'subject': spec, 'counterpart': spec}
    source = {'format': 'fighter-blazin-2', 'shots': [{'template': token}
        for token in ('BT1_01', 'BT2_01', 'BT3_01', 'BT4C01')], 'slots': {'0': pair, '3': pair}}
    parsed = Reader().resource(tmp_path, 'blazin', source)
    assert parsed['pairs'] == {} and set(parsed['slots']) == {0, 3}
    assert parsed['slots'][3]['template_choice'] == 2
    assert parsed['slots'][0]['counterpart'].bone_count == 1
    for slots in ({}, {'00': pair}, {'4': pair}, {'0': {**pair, 'template_choice': True}},
                  {'0': {**pair, 'template_choice': 82}}, {'0': {'template_choice': 2, 'subject': spec}}):
        with pytest.raises(AssetError):
            validate_source('blazin', {**source, 'slots': slots})
    for edit in ({'pairs': {'2': {'subject': spec, 'counterpart': spec}}}, {'format': 'fighter-blazin-1'}):
        bad = deepcopy(source); bad.update(edit)
        with pytest.raises(AssetError):
            validate_source('blazin', bad)
