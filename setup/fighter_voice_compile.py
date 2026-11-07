"""Compose independent authored voice resources into a verified local archive.

Package-facing event names and runtime admission remain separate work. Inputs
here are already-resolved logical voice keys, template entry ordinals, and
validated owned PCM or R2 streams. Original archive members remain unchanged.
"""
import hashlib
import re
import struct

from fighter_archive import Archive
from fighter_registry import key
from fighter_voice import parse_owned_stream, require
from fighter_voice_bank import VoiceBankTemplate, FAMILIES

CATEGORIES = ('Character', 'Taunts', 'Enviro')
MAX_VOICES = 4096


def bank_spec(category, value):
    require(category in FAMILIES and type(value) is dict
            and set(value) == {'template_voice', 'family', 'samples'},
            'Voice bank needs a template, explicit family and sample overrides')
    require(type(value['template_voice']) is int and 0 <= value['template_voice'] < 65535,
            'Invalid per-category voice template')
    require(type(value['family']) is int and value['family'] in FAMILIES[category],
            'Voice family differs from its category')
    require(type(value['samples']) is dict and len(value['samples']) <= 255,
            'Voice sample population exceeds budget')
    return value


class VoiceCompiler:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Voice archive differs from verified local source')
        self.archive = Archive(data, native_separators=True)
        self.source_hash = expected_sha256
        self.occupied = set()
        for entry in self.archive.entries:
            name = self.archive.name_key(entry.name)
            match = re.fullmatch(r'speech/(?:character|taunts|enviro)/def_jam_(?:ip_)?characters/(\d+)\.(?:hdr|dat)', name)
            if match:
                self.occupied.add(int(match[1]))
            match = re.fullmatch(r'speech/streams/(?:intro|extro)/(\d+)(?:[ie]\d+)?\.asf', name)
            if match:
                self.occupied.add(int(match[1]))

    def compose(self, voices):
        require(type(voices) is dict and 0 < len(voices) <= MAX_VOICES,
                'Invalid voice resource population')
        additions, bindings, next_id = {}, {}, 600
        for identifier, voice in sorted(voices.items()):
            key(identifier)
            require(type(voice) is dict and set(voice) in (
                {'template_voice', 'samples', 'intro', 'extro'}, {'banks', 'intro', 'extro'}),
                    'Voice resource needs explicit template, samples, intro and extro')
            explicit = 'banks' in voice
            if explicit:
                require(type(voice['banks']) is dict and set(voice['banks']) == set(CATEGORIES),
                        'Explicit voice needs all three category banks')
                banks = {category: bank_spec(category, value) for category, value in voice['banks'].items()}
            else:
                donor = voice['template_voice']
                require(type(donor) is int and 0 <= donor < 65535, 'Invalid template voice ID')
                require(type(voice['samples']) is dict and set(voice['samples']) <= set(CATEGORIES),
                        'Unknown voice sample category')
                banks = {category: {'template_voice': donor, 'family': None,
                                   'samples': voice['samples'].get(category, {})} for category in CATEGORIES}
            parse_owned_stream(voice['intro'])
            parse_owned_stream(voice['extro'])
            while next_id in self.occupied:
                next_id += 1
            require(next_id < 65535, 'Voice WORD namespace is exhausted')
            native_id = next_id
            next_id += 1
            category_reports = {}
            for category in CATEGORIES:
                bank = banks[category]
                donor = bank['template_voice']
                source_family = 'Def_Jam_IP_Characters' if donor >= 500 else 'Def_Jam_Characters'
                stem = f'speech/{category}/{source_family}/{donor:03d}'
                header, samples = self.archive.read(stem + '.hdr'), self.archive.read(stem + '.dat')
                template = VoiceBankTemplate(header, samples, hashlib.sha256(header).hexdigest(),
                                             hashlib.sha256(samples).hexdigest())
                require(template.voice_key == donor, 'Template bank key differs from requested voice')
                if explicit:
                    require(template.first_key in FAMILIES[category], 'Template voice family differs from its category')
                header, samples, report = template.compose(native_id, bank['samples'], family=bank['family'])
                report['template_voice'] = donor
                target = f'speech/{category}/Def_Jam_IP_Characters/{native_id:03d}'
                # Keep the original archive's native separator spelling for new
                # speech members as well. Alias collisions are checked by Archive.
                additions[(target + '.hdr').replace('/', '\\')] = header
                additions[(target + '.dat').replace('/', '\\')] = samples
                category_reports[category] = report
            for purpose in ('intro', 'extro'):
                additions[f'speech/streams/{purpose}/{native_id:03d}.asf'.replace('/', '\\')] = voice[purpose]
            bindings[identifier] = {'voice_id': native_id, 'template_voice': None if explicit else voice['template_voice'],
                                    'categories': category_reports,
                                    'cinematic_policy': 'explicit-owned-streams'}
        output = self.archive.compose(additions=additions)
        return output, {'schema': 'fighter-voice-archive-1', 'source_sha256': self.source_hash,
                        'sha256': hashlib.sha256(output).hexdigest(), 'bytes': len(output),
                        'bindings': bindings, 'runtime_ready': False}


def encode_voice_bindings(data, report, cores):
    """FVA1 binds zero-based owned cores to separate native WORD voice IDs."""
    require(type(report) is dict and report.get('schema') == 'fighter-voice-archive-1'
            and isinstance(data, bytes) and report.get('bytes') == len(data)
            and report.get('sha256') == hashlib.sha256(data).hexdigest(),
            'Voice archive differs from composition receipt')
    require(type(cores) is dict and 0 < len(cores) <= 16384 - 141,
            'Invalid core-to-voice binding population')
    archive = Archive(data, native_separators=True)
    bindings = report.get('bindings')
    require(type(bindings) is dict, 'Missing voice resource bindings')
    rows = []
    for core, identifier in sorted(cores.items()):
        require(type(core) is int and 141 <= core < 16384 and identifier in bindings,
                'Voice binding needs an owned core and known resource')
        native_id = bindings[identifier]['voice_id']
        require(type(native_id) is int and 600 <= native_id < 65535, 'Invalid allocated voice ID')
        for category in CATEGORIES:
            stem = f'speech/{category}/Def_Jam_IP_Characters/{native_id:03d}'
            h, d = archive.read(stem + '.hdr'), archive.read(stem + '.dat')
            expected = bindings[identifier]['categories'][category]['sha256']
            require([hashlib.sha256(v).hexdigest() for v in (h, d)] == expected,
                    'Voice bank differs from composition receipt')
            require(struct.unpack_from('<H', h, 2)[0] == native_id, 'Voice bank key differs')
        for purpose in ('intro', 'extro'):
            parse_owned_stream(archive.read(f'speech/streams/{purpose}/{native_id:03d}.asf'))
        rows.append(struct.pack('<2I', core, native_id))
    return b'FVA1' + struct.pack('<3I', 1, len(rows), len(data)) + bytes.fromhex(report['sha256']) + b''.join(rows)
