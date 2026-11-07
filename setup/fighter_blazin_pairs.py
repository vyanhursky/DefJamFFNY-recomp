"""Append independently owned paired combat animation resources.

Preserve the donor choice's WAZA/event behavior and both participants' timing.
The emitted ordinals belong to the external motion provider, never the packed
WPAR choice byte. Native registration/selection is a separate acceptance gate.
"""
import hashlib
import re
import struct

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_compile import AnimationTemplate
from fighter_archive import Archive, MAX_ARCHIVE
from fighter_assets import unpack
from fighter_registry import key

MAX_PAIRS = 4096
RETAIL_PAIRS = 82
EXTERNAL_BASE = 709


def rename_records(envelope, original, assigned):
    """Rename indexed names only; each native motion retains its bank export."""
    require(re.fullmatch(r'N[A-Za-z0-9]{4}_[AB]', original)
            and re.fullmatch(r'P[0-9]{4}_[AB]', assigned), 'Invalid paired motion token')
    index, model = AnimationIndex(envelope), envelope.model
    require(index.names and all(name.startswith(original + '_') for name in index.names),
            'Paired motion has unrelated named records')
    output = bytearray(model.data)
    root = model.export_offset(envelope.bank)
    table = model.local_pointer(root + 20, len(index.names) * 4)
    for i, name in enumerate(index.names):
        at = model.data_range(model.local_pointer(table + i * 4, len(name) + 1), len(name) + 1)
        output[at:at + 7] = assigned.encode('ascii')
    split = model.sections[2][4]
    result = AnimationEnvelope(bytes(output[:split]), bytes(output[split:]),
                               struct.pack('<II', 1, 0) + assigned.encode('ascii') + b'.')
    checked = AnimationIndex(result)
    require(checked.records == index.records and checked.model.pointers == model.pointers
            and checked.names == [assigned + name[7:] for name in index.names],
            'Paired motion rename changed record ownership')
    return result


class BlazinPairs:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and len(data) <= MAX_ARCHIVE
                and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Paired Blazin compiler requires a verified original archive')
        self.archive, self.source_sha256 = Archive(data), expected_sha256
        names = unpack(self.archive.read('blazin.mnl'))
        require(len(names) >= 8 and struct.unpack_from('<II', names) == (164, 0)
                and names.endswith(b'.'), 'Unsupported original paired Blazin population')
        self.tokens = names[8:-1].decode('ascii').split('.')
        require(len(self.tokens) == 164 and len(set(self.tokens)) == 164
                and all(re.fullmatch(r'N[A-Za-z0-9]{4}_[AB]', token) for token in self.tokens)
                and all(a.endswith('_A') and b == a[:-1] + 'B'
                        for a, b in zip(self.tokens[::2], self.tokens[1::2])),
                'Blazin motion names do not form ordered subject/counterpart pairs')

    def compose(self, resources):
        require(type(resources) is dict and 0 < len(resources) <= MAX_PAIRS,
                'Paired Blazin resource population exceeds budget')
        for identifier in resources:
            key(identifier)
        additions, bindings = {}, {}
        tokens = list(self.tokens)
        used, number = len(self.archive.data), 0
        for identifier, resource in sorted(resources.items()):
            require(type(resource) is dict and set(resource) == {
                'template_choice', 'rig_sha256', 'bone_count', 'subject', 'counterpart'},
                'Paired Blazin needs a template choice, verified rig and two typed tracks')
            choice = resource['template_choice']
            require(type(choice) is int and 0 <= choice < RETAIL_PAIRS, 'Invalid inherited Blazin choice')
            while any(f'p{number:04d}_{role}.{suffix}' in self.archive.by_name
                      for role in ('a', 'b') for suffix in ('ord', 'orl')):
                number += 1
            require(number <= 9999, 'Paired Blazin name namespace exhausted')
            pair = {'template_choice': choice, 'external_ordinal': EXTERNAL_BASE + len(tokens), 'roles': {}}
            for role, letter, ordinal in (('subject', 'A', 2*choice), ('counterpart', 'B', 2*choice+1)):
                original, assigned = self.tokens[ordinal], f'P{number:04d}_{letter}'
                envelope = AnimationEnvelope(*(unpack(self.archive.read(original + '.' + suffix))
                                               for suffix in ('ord', 'orl')),
                                             struct.pack('<II', 1, 0) + original.encode('ascii') + b'.')
                compiler = AnimationTemplate(envelope, hashlib.sha256(envelope.model.data).hexdigest(),
                                             resource['rig_sha256'], resource['bone_count'])
                compiled, receipt = compiler.compose({original: resource[role]})
                compiled = rename_records(compiled, original, assigned)
                split = compiled.model.sections[2][4]
                parts = {'ord': compiled.model.data[:split], 'orl': compiled.model.data[split:]}
                used += sum(len(part) + len(assigned) + 16 for part in parts.values())
                require(used <= MAX_ARCHIVE, 'Paired Blazin generation exceeds byte budget')
                for suffix, part in parts.items():
                    additions[assigned + '.' + suffix] = part
                pair['roles'][role] = {'template': original, 'native_name': assigned,
                    'parts_sha256': {suffix: hashlib.sha256(part).hexdigest() for suffix, part in parts.items()},
                    'animation': receipt, 'sha256': hashlib.sha256(compiled.model.data).hexdigest()}
                tokens.append(assigned)
            bindings[identifier] = pair
            number += 1
        names = struct.pack('<II', len(tokens), 0) + '.'.join(tokens).encode('ascii') + b'.'
        result = self.archive.compose(additions=additions, replacements={'blazin.mnl': names})
        return result, {'schema': 'fighter-blazin-pairs-1', 'source_sha256': self.source_sha256,
                        'sha256': hashlib.sha256(result).hexdigest(), 'bytes': len(result),
                        'external_base': EXTERNAL_BASE, 'motion_count': len(tokens),
                        'bindings': bindings, 'runtime_ready': False}


def encode_pair_bindings(data, report, cores, *, slots=False):
    require(isinstance(data, bytes) and type(report) is dict
            and report.get('schema') == 'fighter-blazin-pairs-1'
            and report.get('bytes') == len(data)
            and report.get('sha256') == hashlib.sha256(data).hexdigest()
            and report.get('external_base') == EXTERNAL_BASE,
            'Paired Blazin archive differs from its receipt')
    require(type(cores) is dict and 0 < len(cores) <= 16384 - 141
            and all(type(core) is int and 141 <= core < 16384 for core in cores),
            'Invalid core-to-finisher population')
    archive = Archive(data)
    names = archive.read('blazin.mnl')
    count = report.get('motion_count')
    require(type(count) is int and 164 < count <= 164 + 2*MAX_PAIRS
            and len(names) >= 8 and struct.unpack_from('<II', names) == (count, 0)
            and names.endswith(b'.'), 'Paired Blazin name count differs')
    tokens = names[8:-1].decode('ascii').split('.')
    require(len(tokens) == count, 'Paired Blazin name population differs')
    bindings = report.get('bindings')
    require(type(bindings) is dict, 'Missing paired Blazin bindings')
    rows = []
    for core, choices in sorted(cores.items()):
        require(type(choices) is dict and 0 < len(choices) <= 4
                and all(type(choice) is int and 0 <= choice < (4 if slots else RETAIL_PAIRS) for choice in choices),
                'A fighter has at most four inherited finisher choices')
        for selection, identifier in sorted(choices.items()):
            require(type(identifier) is str and identifier in bindings, 'Unknown paired Blazin resource')
            pair = bindings[identifier]
            choice = pair.get('template_choice') if type(pair) is dict and slots else selection
            require(type(pair) is dict and type(choice) is int and 0 <= choice < RETAIL_PAIRS
                    and pair.get('template_choice') == choice
                    and type(pair.get('external_ordinal')) is int and type(pair.get('roles')) is dict
                    and set(pair['roles']) == {'subject', 'counterpart'},
                    'Paired Blazin binding differs from its inherited behavior')
            ordinal = pair['external_ordinal']
            require(873 <= ordinal < EXTERNAL_BASE + count - 1 and (ordinal - 873) % 2 == 0,
                    'Paired Blazin ordinal is outside appended pairs')
            native_names = []
            for role, letter, offset in (('subject', 'A', 0), ('counterpart', 'B', 1)):
                item = pair['roles'][role]
                require(type(item) is dict and type(item.get('native_name')) is str
                        and re.fullmatch(r'P[0-9]{4}_' + letter, item['native_name'])
                        and type(item.get('parts_sha256')) is dict, 'Invalid paired motion receipt')
                name = item['native_name']
                require(tokens[ordinal - EXTERNAL_BASE + offset] == name, 'Paired motion ordinal differs from its name')
                parts = [archive.read(name + '.' + suffix) for suffix in ('ord', 'orl')]
                require([hashlib.sha256(part).hexdigest() for part in parts]
                        == [item['parts_sha256'].get(suffix) for suffix in ('ord', 'orl')]
                        and hashlib.sha256(b''.join(parts)).hexdigest() == item.get('sha256'),
                        'Paired motion differs from its receipt')
                native_names.append(name.encode('ascii'))
            require(native_names[0][:-1] == native_names[1][:-1], 'Paired roles belong to different resources')
            rows.append(struct.pack('<IIII8s8s', core, selection, choice, ordinal, *native_names) if slots
                        else struct.pack('<III8s8s', core, choice, ordinal, *native_names))
    return ((b'FBP2' if slots else b'FBP1') + struct.pack('<4I', 2 if slots else 1, len(rows), count, len(data))
            + hashlib.sha256(data).digest() + b''.join(rows))
