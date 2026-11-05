"""Allocate independent participant animation banks in a verified archive.

Bank numbers and core identities are separate namespaces. A compiled bank keeps
its donor's motion-name ordinals so inherited action/event timing remains valid.
The typed quaternion compiler is the only authored payload path in this profile.
"""
import hashlib
import re
import struct

from fighter_archive import Archive, MAX_ARCHIVE
from fighter_assets import unpack
from fighter_animation import AnimationEnvelope, require
from fighter_animation_compile import AnimationTemplate
from fighter_registry import key


class AnimationArchive:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Animation archive must match its verified local source')
        self.archive = Archive(data)
        self.source_sha256 = expected_sha256
        self.occupied = set()
        for entry in self.archive.entries:
            match = re.fullmatch(r'wres(\d+)\.(?:mnl|ord|orl)', entry.name.lower())
            if match:
                self.occupied.add(int(match[1]))

    def compose(self, resources):
        require(type(resources) is dict and 0 < len(resources) <= 4096,
                'Animation library exceeds its resource budget')
        for identifier in resources:
            key(identifier)
        additions, bindings, next_id = {}, {}, 1000
        used = len(self.archive.data)
        for identifier, resource in sorted(resources.items()):
            require(type(resource) is dict and set(resource) in (
                {'template_bank', 'rig_sha256', 'bone_count', 'replacements'},
                {'template_bank', 'rig_sha256', 'bone_count', 'replacements', 'moveset'}),
                'Animation resource requires a template, verified rig and typed tracks')
            donor = resource['template_bank']
            require(type(donor) is int and 0 < donor < 1000, 'Invalid inherited participant bank')
            envelope = AnimationEnvelope(*(unpack(self.archive.read(f'wres{donor:03d}.' + suffix))
                                           for suffix in ('ord', 'orl', 'mnl')))
            compiler = AnimationTemplate(envelope, hashlib.sha256(envelope.model.data).hexdigest(),
                                         resource['rig_sha256'], resource['bone_count'])
            names = unpack(self.archive.read(f'wres{donor:03d}.mnl'))
            selection = None
            if 'moveset' in resource:
                from fighter_moveset import MovesetPlan
                request = resource['moveset']
                require(type(request) is dict and set(request) == {'plan', 'selections'}
                        and type(request['plan']) is MovesetPlan, 'Animation needs a typed moveset plan')
                plan = request['plan']
                require(plan.core + 1 == donor and plan.bank.envelope.model.data == envelope.model.data
                        and plan.bank.envelope.tokens == envelope.tokens,
                        'Moveset and animation resource templates differ')
                _, names, selection = plan.compose(request['selections'])
            if resource['replacements']:
                compiled, receipt = compiler.compose(resource['replacements'])
            else:
                require(type(resource['replacements']) is dict and selection is not None,
                        'Animation requires authored tracks or a typed moveset selection')
                compiled = envelope
                receipt = {'schema': 'fighter-animation-template-1',
                           'source_sha256': hashlib.sha256(envelope.model.data).hexdigest(),
                           'sha256': hashlib.sha256(envelope.model.data).hexdigest(),
                           'bindings': {}, 'motion_names_preserved': False,
                           'inherited_timing_preserved': True, 'runtime_ready': False}
            while next_id in self.occupied:
                next_id += 1
            require(next_id <= 99999, 'Animation bank filename namespace is exhausted')
            native = next_id; next_id += 1
            split = compiled.model.sections[2][4]
            parts = {'ord': compiled.model.data[:split], 'orl': compiled.model.data[split:],
                     'mnl': names}
            used += sum(len(value) + len(f'wres{native:03d}.{suffix}') + 9
                        for suffix, value in parts.items())
            require(used <= MAX_ARCHIVE, 'Composed animation archive exceeds budget')
            for suffix, value in parts.items():
                additions[f'wres{native:03d}.{suffix}'] = value
            bindings[identifier] = {'bank_number': native, 'template_bank': donor,
                                   'parts_sha256': {s: hashlib.sha256(v).hexdigest() for s, v in parts.items()},
                                   'animation': receipt}
            if selection is not None:
                bindings[identifier]['moveset'] = selection
        output = self.archive.compose(additions=additions)
        return output, {'schema': 'fighter-animation-archive-1', 'source_sha256': self.source_sha256,
                        'sha256': hashlib.sha256(output).hexdigest(), 'bytes': len(output),
                        'bindings': bindings, 'runtime_ready': False}


def encode_animation_bindings(data, report, cores):
    require(type(report) is dict and report.get('schema') == 'fighter-animation-archive-1'
            and isinstance(data, bytes) and report.get('bytes') == len(data)
            and report.get('sha256') == hashlib.sha256(data).hexdigest(),
            'Animation archive differs from its composition receipt')
    require(type(cores) is dict and 0 < len(cores) <= 16384 - 141,
            'Invalid core-to-animation binding population')
    archive = Archive(data)
    bindings = report.get('bindings')
    require(type(bindings) is dict, 'Missing animation resource bindings')
    rows = []
    require(all(type(core) is int and 141 <= core < 16384
                and type(identifier) is str and identifier in bindings
                for core, identifier in cores.items()),
                'Animation binding requires an owned core and known resource')
    for core, identifier in sorted(cores.items()):
        row = bindings[identifier]
        require(type(row) is dict and type(row.get('parts_sha256')) is dict
                and all(type(row['parts_sha256'].get(s)) is str for s in ('ord', 'orl', 'mnl'))
                and type(row.get('animation')) is dict
                and type(row['animation'].get('sha256')) is str,
                'Malformed animation resource receipt')
        native = row.get('bank_number')
        require(type(native) is int and 1000 <= native <= 99999, 'Invalid allocated animation bank')
        parts = [archive.read(f'wres{native:03d}.' + suffix) for suffix in ('ord', 'orl', 'mnl')]
        require([hashlib.sha256(p).hexdigest() for p in parts]
                == [row['parts_sha256'][s] for s in ('ord', 'orl', 'mnl')],
                'Animation bank differs from its composition receipt')
        envelope = AnimationEnvelope(*parts)
        require(envelope.metadata()['combined_sha256'] == row['animation']['sha256'],
                'Animation record receipt differs')
        rows.append(struct.pack('<2I', core, native))
    return b'FBA1' + struct.pack('<3I', 1, len(rows), len(data)) + bytes.fromhex(report['sha256']) + b''.join(rows)
