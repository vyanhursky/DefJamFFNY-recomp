"""Bounded creator data for the experimental fighter behavior adapters.

Sources contain quaternion samples, action choices, PCM WAV audio and named
AI tendencies. Native archives, pointers, dispatch words and scripts are never
accepted here. Template ownership and cross-resource rig/event joins belong
to the composition coordinator, after the whole pack set has been resolved.
"""
import hashlib
import io
import json
import re
import wave

from fighter_assets import AssetError
from fighter_animation_tracks import QuaternionTracks
from fighter_ai import DIFFICULTIES, EDITABLE, basename
from fighter_voice_compile import CATEGORIES
from fighter_voice import encode_stream
from mods import ordinary_path, safe_relative

MAX_FILE = 64 * 1024**2
MAX_INPUT = 256 * 1024**2
KINDS = frozenset(('moveset', 'voice', 'ai', 'cinematic', 'blazin'))


def require(condition, message):
    if not condition:
        raise AssetError(message)


def file_spec(value):
    require(type(value) is dict and set(value) == {'path', 'sha256'},
            'Behavior file needs a relative path and SHA-256')
    safe_relative(value['path'])
    require(type(value['sha256']) is str and re.fullmatch('[0-9a-f]{64}', value['sha256']),
            'Behavior file requires a SHA-256 digest')


def ordinal(value, maximum):
    require(type(value) is str and re.fullmatch('0|[1-9][0-9]{0,4}', value)
            and int(value) <= maximum, 'Behavior entry needs a canonical bounded ordinal')
    return int(value)


def validate_source(kind, source):
    expected = {
        'moveset': {'format', 'donor', 'selections', 'tracks'},
        'voice': {'format', 'template_voice', 'samples', 'intro', 'extro'},
        'ai': {'format', 'template_profile', 'tendencies'},
        'cinematic': {'format', 'template', 'track'},
        'blazin': {'format', 'shots'},
    }
    require(kind in KINDS and type(source) is dict
            and (set(source) == expected[kind] or kind == 'blazin' and set(source) == expected[kind] | {'pairs'})
            and source['format'] == 'fighter-' + kind + '-1', 'Unsupported behavior source fields or format')
    if kind == 'moveset':
        require(type(source['donor']) is str and re.fullmatch(r'retail/[a-z0-9]+(?:-[a-z0-9]+)*', source['donor']),
                'Moveset requires an explicit retail behavior template')
        require(type(source['selections']) is dict and len(source['selections']) <= 124,
                'Moveset selections exceed budget')
        for target, chosen in source['selections'].items():
            ordinal(target, 124)
            require(type(chosen) is int and 1 <= chosen <= 124, 'Invalid selected action')
        require(type(source['tracks']) is dict and len(source['tracks']) <= 999,
                'Moveset track population exceeds budget')
        for token, spec in source['tracks'].items():
            require(type(token) is str and re.fullmatch(r'[A-Za-z0-9_]{1,64}', token),
                    'Invalid motion token')
            file_spec(spec)
        require(source['tracks'] or source['selections'], 'Moveset needs authored tracks or selections')
    elif kind == 'voice':
        require(type(source['template_voice']) is int and 0 <= source['template_voice'] < 65535,
                'Invalid voice template')
        require(type(source['samples']) is dict and set(source['samples']) <= set(CATEGORIES),
                'Invalid voice sample categories')
        for entries in source['samples'].values():
            require(type(entries) is dict and len(entries) <= 255, 'Voice sample population exceeds budget')
            for index, spec in entries.items():
                ordinal(index, 254)
                file_spec(spec)
        file_spec(source['intro'])
        file_spec(source['extro'])
    elif kind == 'ai':
        basename(source['template_profile'])
        tendencies = source['tendencies']
        require(type(tendencies) is dict and set(tendencies) == set(DIFFICULTIES),
                'AI needs all three difficulty profiles')
        for rows in tendencies.values():
            require(type(rows) is dict and set(rows) == {'0', '1', '2', '3'},
                    'AI needs all four native tendency slots')
            for edits in rows.values():
                require(type(edits) is dict and edits and set(edits) <= EDITABLE
                        and all(type(v) is int and 1 <= v <= 5 for v in edits.values()),
                        'AI supports only named tendency values from 1 to 5')
    elif kind == 'blazin':
        from fighter_blazin_compile import phase_template
        require(type(source['shots']) is list and len(source['shots']) == 4,
                'Blazin activation needs four native shot roles')
        for phase, shot in enumerate(source['shots']):
            require(type(shot) is dict and set(shot) in ({'template'}, {'template', 'track'}),
                    'Unsupported Blazin shot fields')
            phase_template(shot['template'], phase)
            if 'track' in shot:
                file_spec(shot['track'])
        if 'pairs' in source:
            require(type(source['pairs']) is dict and 0 < len(source['pairs']) <= 4,
                    'Blazin supports at most four inherited finisher choices')
            for choice, pair in source['pairs'].items():
                ordinal(choice, 81)
                require(type(pair) is dict and set(pair) == {'subject', 'counterpart'},
                        'Blazin finishing move needs both participant tracks')
                for spec in pair.values():
                    file_spec(spec)
    else:
        require(type(source['template']) is str and re.fullmatch(r'C[IE]_[A-Za-z0-9]{4}', source['template']),
                'Cinematic requires a supported simple intro/victory template')
        file_spec(source['track'])
    return source


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate behavior JSON member')
        result[key] = value
    return result


def quaternion_file(data):
    require(isinstance(data, bytes) and 0 < len(data) <= MAX_FILE, 'Quaternion file exceeds budget')
    try:
        doc = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object,
                         parse_constant=lambda _: (_ for _ in ()).throw(AssetError('Nonfinite behavior JSON')))
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        raise AssetError('Invalid quaternion JSON') from error
    require(type(doc) is dict and set(doc) == {'schema', 'rig_sha256', 'bone_count', 'poses'}
            and doc['schema'] == 'fighter-quaternions-1', 'Unsupported quaternion document')
    count, poses = doc['bone_count'], doc['poses']
    require(type(count) is int and 0 < count <= 4096 and type(poses) is list
            and 0 < len(poses) <= 65535 and len(poses) * count * 4 <= 4 * 1024**2,
            'Quaternion sample population exceeds budget')
    require(all(type(pose) is list and len(pose) == count
                and all(type(q) is list and len(q) == 4
                        and all(type(v) in (int, float) and -1.001 <= v <= 1.001 for v in q)
                        for q in pose) for pose in poses),
            'Quaternion poses need complete rig coverage')
    result = QuaternionTracks(doc['rig_sha256'], count, tuple(range(count)),
                              tuple(tuple(tuple(q) for q in pose) for pose in poses))
    result.validate()
    return result


def wav_file(data):
    require(isinstance(data, bytes) and 0 < len(data) <= MAX_FILE, 'Voice WAV exceeds budget')
    try:
        with wave.open(io.BytesIO(data), 'rb') as audio:
            require(audio.getnchannels() == 1 and audio.getsampwidth() == 2
                    and audio.getcomptype() == 'NONE', 'Voice WAV must be mono PCM16')
            count, rate = audio.getnframes(), audio.getframerate()
            require(0 < count <= MAX_FILE // 2, 'Voice WAV sample population exceeds budget')
            pcm = audio.readframes(count)
            require(len(pcm) == count * 2, 'Voice WAV has truncated samples')
    except (wave.Error, EOFError) as error:
        raise AssetError('Invalid voice WAV') from error
    return encode_stream(pcm, rate)


class Reader:
    """One aggregate input budget shared across the resolved pack set."""
    def __init__(self, budget=MAX_INPUT):
        require(type(budget) is int and 0 < budget <= MAX_INPUT, 'Invalid behavior input budget')
        self.remaining = budget

    def file(self, root, spec):
        file_spec(spec)
        root = ordinary_path(root)
        require(root.is_dir(), 'Behavior package directory is missing')
        path = ordinary_path(root.joinpath(*safe_relative(spec['path'])))
        require(path.is_relative_to(root), 'Behavior file escapes its package')
        maximum = min(MAX_FILE, self.remaining)
        with path.open('rb') as stream:
            data = stream.read(maximum + 1)
        require(0 < len(data) <= maximum, 'Behavior file exceeds the remaining input budget')
        require(hashlib.sha256(data).hexdigest() == spec['sha256'], 'Behavior file hash mismatch')
        self.remaining -= len(data)
        return data

    def resource(self, root, kind, source):
        validate_source(kind, source)
        if kind == 'moveset':
            return {'donor': source['donor'], 'selections': {int(a): b for a, b in source['selections'].items()},
                    'tracks': {token: quaternion_file(self.file(root, spec)) for token, spec in source['tracks'].items()}}
        if kind == 'voice':
            return {'template_voice': source['template_voice'],
                    'samples': {category: {int(i): wav_file(self.file(root, spec)) for i, spec in entries.items()}
                                for category, entries in source['samples'].items()},
                    'intro': wav_file(self.file(root, source['intro'])),
                    'extro': wav_file(self.file(root, source['extro']))}
        if kind == 'ai':
            return {'template_profile': source['template_profile'],
                    'tendencies': {difficulty: {int(i): dict(edits) for i, edits in rows.items()}
                                   for difficulty, rows in source['tendencies'].items()}}
        if kind == 'blazin':
            return {'shots': [{'template': shot['template'],
                              'tracks': quaternion_file(self.file(root, shot['track'])) if 'track' in shot else None}
                             for shot in source['shots']],
                    'pairs': {int(choice): {role: quaternion_file(self.file(root, spec)) for role, spec in pair.items()}
                              for choice, pair in source.get('pairs', {}).items()}}
        return {'template': source['template'], 'tracks': quaternion_file(self.file(root, source['track']))}
