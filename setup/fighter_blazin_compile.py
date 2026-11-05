"""Typed four-phase Blazin activation clips, separate from combat move pairs.

Preserve the native shot roles: phases 1..3 carry body and camera helpers;
phase 4 carries body helpers and retains the game's venue-specific camera.
The runtime selects by full core and native shot ordinal, never a pack pointer.
"""
import hashlib
import re
import struct

from fighter_assets import AssetError, unpack
from fighter_archive import Archive, MAX_ARCHIVE
from fighter_animation import AnimationIndex
from fighter_animation_compile import AnimationTemplate
from fighter_cinematic_compile import envelope, rename_bank, MAX_BYTES
from fighter_registry import key


def require(condition, message):
    if not condition:
        raise AssetError(message)


def phase_template(token, phase):
    require(type(phase) is int and 0 <= phase < 4 and isinstance(token, str)
            and re.fullmatch((f'BT{phase + 1}_' if phase < 3 else 'BT4C') + r'[0-9]{2}', token),
            'Blazin template differs from its native shot role')


class BlazinTemplate:
    def __init__(self, data, expected_sha256, token, phase, rig_sha256, bone_count):
        phase_template(token, phase)
        require(isinstance(data, bytes) and 0 < len(data) <= MAX_BYTES
                and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Blazin bundle differs from its verified template')
        archive = Archive(data)
        suffixes = ('.o', '_f.o', '_h.o') + (('_EYE.o', '_TARGET.o') if phase < 3 else ())
        require({e.name for e in archive.entries} == {token + s for s in suffixes},
                'Blazin template has missing or unsupported helpers')
        self.members, used = {}, 0
        for entry in archive.entries:
            payload = unpack(archive.read(entry.name))
            used += len(payload)
            require(used <= MAX_BYTES, 'Decoded Blazin bundle exceeds budget')
            bank = AnimationIndex(envelope(payload))
            expected = token if entry.name in (token + '.o', token + '_f.o', token + '_h.o') else entry.name[:-2]
            require(bank.envelope.bank == '__AnimationBank:::' + expected, 'Unexpected Blazin helper export')
            self.members[entry.name] = payload
        body = envelope(self.members[token + '.o'], token)
        require(AnimationIndex(body).names == [token + '_s', token + '_t'], 'Blazin body needs paired skeletal/root tracks')
        self.body = AnimationTemplate(body, hashlib.sha256(body.model.data).hexdigest(), rig_sha256, bone_count)
        self.archive, self.token, self.phase, self.source_sha256 = archive, token, phase, expected_sha256

    def compose(self, assigned, tracks):
        require(isinstance(assigned, str) and re.fullmatch(r'B[0-9]{5}', assigned), 'Invalid allocated Blazin name')
        authored = None
        if tracks is not None:
            authored, animation = self.body.compose({self.token: tracks})
        else:
            animation = {'schema': 'fighter-blazin-inherited-body-1',
                         'sha256': hashlib.sha256(self.members[self.token + '.o']).hexdigest(), 'runtime_ready': False}
        replacements, renames = {}, {}
        for name, original in self.members.items():
            payload = authored.model.data if authored is not None and name == self.token + '.o' else original
            replacements[name] = rename_bank(payload, self.token, assigned)
            renames[name] = assigned + name[6:]
        result = self.archive.compose(renames=renames, replacements=replacements)
        require(len(result) <= MAX_BYTES, 'Compiled Blazin bundle exceeds budget')
        return result, {'schema': 'fighter-blazin-template-1', 'template': self.token,
                        'phase': self.phase, 'native_name': assigned,
                        'source_sha256': self.source_sha256, 'sha256': hashlib.sha256(result).hexdigest(),
                        'animation': animation, 'camera_policy': 'owned-helpers' if self.phase < 3 else 'native-venue',
                        'runtime_ready': False}


class BlazinArchive:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and len(data) <= MAX_ARCHIVE
                and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Blazin archive requires a verified resource generation')
        self.archive, self.source_sha256 = Archive(data), expected_sha256

    def compose(self, resources):
        require(type(resources) is dict and 0 < len(resources) <= 4096, 'Blazin resource population exceeds budget')
        for identifier in resources:
            key(identifier)
        additions, bindings = {}, {}
        occupied = set(self.archive.by_name)
        used, next_id = len(self.archive.data), 0
        for identifier, resource in sorted(resources.items()):
            require(type(resource) is dict and set(resource) == {'rig_sha256', 'bone_count', 'shots'}
                    and type(resource['shots']) is list and len(resource['shots']) == 4,
                    'Blazin activation requires exactly four typed native shot roles')
            shots = []
            for phase, shot in enumerate(resource['shots']):
                require(type(shot) is dict and set(shot) == {'template', 'tracks'}, 'Invalid Blazin shot definition')
                token = shot['template']; phase_template(token, phase)
                source = unpack(self.archive.read(token + '.viv'))
                compiler = BlazinTemplate(source, hashlib.sha256(source).hexdigest(), token, phase,
                                          resource['rig_sha256'], resource['bone_count'])
                while next_id <= 99999 and f'b{next_id:05d}.viv' in occupied:
                    next_id += 1
                require(next_id <= 99999, 'Blazin resource filename namespace exhausted')
                assigned = f'B{next_id:05d}'; next_id += 1
                data, receipt = compiler.compose(assigned, shot['tracks'])
                used += len(data) + len(assigned) + 13
                require(used <= MAX_ARCHIVE, 'Blazin resource generation exceeds budget')
                additions[assigned + '.viv'] = data
                occupied.add((assigned + '.viv').lower())
                shots.append(receipt)
            bindings[identifier] = shots
        result = self.archive.compose(additions=additions)
        return result, {'schema': 'fighter-blazin-archive-1', 'source_sha256': self.source_sha256,
                        'sha256': hashlib.sha256(result).hexdigest(), 'bytes': len(result),
                        'bindings': bindings, 'runtime_ready': False}


def encode_blazin_bindings(data, report, cores, *, extension=None):
    require(type(report) is dict and isinstance(data, bytes), 'Invalid Blazin artifact receipt')
    # The coordinator may append intro/victory bundles after these shots.
    # Keep both receipts intact and verify the explicit composition chain.
    final_hash = hashlib.sha256(data).hexdigest()
    direct = extension is None and report.get('bytes') == len(data) and report.get('sha256') == final_hash
    extended = (type(extension) is dict and extension.get('schema') == 'fighter-cinematic-archive-1'
                and extension.get('source_sha256') == report.get('sha256')
                and extension.get('sha256') == final_hash)
    require(type(report) is dict and report.get('schema') == 'fighter-blazin-archive-1'
            and isinstance(data, bytes) and (direct or extended), 'Blazin archive differs from its receipt chain')
    require(type(cores) is dict and 0 < len(cores) <= 16384 - 141
            and all(type(core) is int and 141 <= core < 16384 for core in cores), 'Invalid core-to-Blazin population')
    archive, rows = Archive(data), []
    for core, identifier in sorted(cores.items()):
        require(identifier in report['bindings'] and type(report['bindings'][identifier]) is list
                and len(report['bindings'][identifier]) == 4, 'Unknown or incomplete Blazin resource')
        names = []
        for phase, shot in enumerate(report['bindings'][identifier]):
            require(type(shot) is dict and shot.get('phase') == phase
                    and isinstance(shot.get('native_name'), str)
                    and re.fullmatch(r'B[0-9]{5}', shot['native_name']), 'Invalid Blazin phase receipt')
            name = shot['native_name']
            require(hashlib.sha256(archive.read(name + '.viv')).hexdigest() == shot.get('sha256'),
                    'Blazin shot differs from its receipt')
            names.append(name.encode('ascii'))
        rows.append(struct.pack('<I8s8s8s8s', core, *names))
    return b'FBZ1' + struct.pack('<3I', 1, len(rows), len(data)) + bytes.fromhex(final_hash) + b''.join(rows)
