"""Compile typed intro/victory poses into independently named native bundles.

Only a verified local template supplies camera, facial, hair, root-motion and
timing data. Creator input is a complete typed quaternion track for that rig.
Names are changed through parsed string fields, never a binary search/replace.
This compiler does not admit team sequences or Blazin choreography.
"""
import hashlib
import re
import struct

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_compile import AnimationTemplate
from fighter_archive import Archive, MAX_ARCHIVE
from fighter_assets import unpack
from fighter_elf import Model, MAX_BYTES
from fighter_cinematics import Cinematic, Cinematics


def envelope(data, token=None):
    model = Model(data)
    split = model.sections[2][4]
    names = None if token is None else struct.pack('<2I', 1, 0) + token.encode('ascii') + b'.'
    return AnimationEnvelope(data[:split], data[split:], names)


def rename_bank(data, original, assigned):
    """Rename only parsed bank symbols and indexed record-name strings."""
    ordinary = re.fullmatch(r'C[IE]_[A-Za-z0-9]{4}', original) and re.fullmatch(r'F[IV][0-9]{5}', assigned)
    blazin = re.fullmatch(r'BT(?:[123]_[0-9]{2}|4C[0-9]{2})', original) and re.fullmatch(r'B[0-9]{5}', assigned)
    require((ordinary or blazin) and len(original) == len(assigned), 'Unsupported cinematic native identifier')
    width = len(original)
    parsed = AnimationIndex(envelope(data))
    model, output = parsed.model, bytearray(data)
    require(parsed.envelope.bank.startswith('__AnimationBank:::' + original),
            'Cinematic helper bank does not match its template')
    for i, (name, *_rest) in enumerate(model.symbols):
        prefix = '__AnimationBank:::' + original
        if name.startswith(prefix):
            string_offset, = model.unpack('<I', model.sections[4][4] + i * 16)
            at = model.sections[3][4] + string_offset + len('__AnimationBank:::')
            output[at:at + width] = assigned.encode('ascii')
    root = model.export_offset(parsed.envelope.bank)
    names = model.local_pointer(root + 20, 4 * len(parsed.names))
    for i, name in enumerate(parsed.names):
        if name.startswith(original + '_'):
            at = model.data_range(model.local_pointer(names + 4 * i, len(name) + 1), len(name) + 1)
            output[at:at + width] = assigned.encode('ascii')
    result = bytes(output)
    checked = AnimationIndex(envelope(result))
    require(checked.records == parsed.records and checked.model.pointers == model.pointers
            and checked.names == [assigned + n[width:] if n.startswith(original + '_') else n
                                  for n in parsed.names], 'Cinematic rename changed record ownership')
    return result


class CinematicTemplate:
    def __init__(self, data, expected_sha256, token, rig_sha256, bone_count):
        require(isinstance(data, bytes) and len(data) <= MAX_BYTES
                and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Cinematic compiler requires a verified local bundle')
        require(isinstance(token, str) and re.fullmatch(r'C[IE]_[A-Za-z0-9]{4}', token),
                'Unsupported simple cinematic template identifier')
        archive = Archive(data)
        suffixes = ('.o', '_f.o', '_h.o') + (('1_EYE.o', '1_TARGET.o', '2_EYE.o', '2_TARGET.o')
                                                   if token.startswith('CI_') else ('_EYE.o', '_TARGET.o'))
        require({e.name for e in archive.entries} == {token + s for s in suffixes},
                'Cinematic template has missing or unsupported helpers')
        self.members, decoded_bytes = {}, 0
        for entry in archive.entries:
            member = unpack(archive.read(entry.name))
            decoded_bytes += len(member)
            require(decoded_bytes <= MAX_BYTES, 'Decoded cinematic bundle exceeds budget')
            self.members[entry.name] = member
        for name, member in self.members.items():
            parsed = AnimationIndex(envelope(member))
            expected = token if name in (token + '.o', token + '_f.o', token + '_h.o') else name[:-2]
            require(parsed.envelope.bank == '__AnimationBank:::' + expected,
                    'Cinematic member has an unexpected bank export')
        body = envelope(self.members[token + '.o'], token)
        require(AnimationIndex(body).names == [token + '_s', token + '_t'],
                'Cinematic body must have one paired skeletal/root track')
        self.body = AnimationTemplate(body, hashlib.sha256(body.model.data).hexdigest(), rig_sha256, bone_count)
        self.archive, self.token, self.sha256 = archive, token, expected_sha256

    def compose(self, assigned, tracks):
        prefix = 'FI' if self.token.startswith('CI_') else 'FV'
        require(isinstance(assigned, str) and re.fullmatch(prefix + r'[0-9]{5}', assigned),
                'Cinematic assigned name differs from its intro/victory kind')
        if tracks is None:
            # Only the coordinator supplies this inheritance marker. Creator
            # sources still require a validated quaternion file.
            authored = None
            receipt = {'schema': 'fighter-cinematic-inherited-body-1',
                       'sha256': hashlib.sha256(self.members[self.token + '.o']).hexdigest(),
                       'runtime_ready': False}
        else:
            authored, receipt = self.body.compose({self.token: tracks})
        replacements, renames = {}, {}
        for name, member in self.members.items():
            if name == self.token + '.o' and authored is not None:
                member = authored.model.data
            replacements[name] = rename_bank(member, self.token, assigned)
            renames[name] = assigned + name[7:]
        result = self.archive.compose(renames=renames, replacements=replacements)
        require(len(result) <= MAX_BYTES, 'Compiled cinematic bundle exceeds budget')
        return result, {'schema': 'fighter-cinematic-template-1', 'template': self.token,
                        'source_sha256': self.sha256, 'native_name': assigned,
                        'sha256': hashlib.sha256(result).hexdigest(), 'animation': receipt,
                        'inherited_camera_face_hair_root_and_timing': True, 'runtime_ready': False}


class CinematicArchive:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Cinematic archive requires a verified local baseline')
        self.archive, self.sha256 = Archive(data), expected_sha256

    def compose(self, resources,*,graphs=None,hands=None):
        require(type(resources) is dict and 0 < len(resources) <= 4096
                and all(isinstance(k, str) and 0 < len(k) <= 255 for k in resources),
                'Cinematic resource population exceeds budget')
        occupied = set(self.archive.by_name)
        additions, bindings = {}, {}
        compiled_bytes = len(self.archive.data)
        next_number = {'FI': 0, 'FV': 0}
        for key, resource in sorted(resources.items()):
            require(type(resource) is dict and set(resource) == {'template', 'rig_sha256', 'bone_count', 'tracks'},
                    'Cinematic resource requires typed tracks and a verified template association')
            token = resource['template']
            require(isinstance(token, str) and re.fullmatch(r'C[IE]_[A-Za-z0-9]{4}', token),
                    'Unsupported cinematic template')
            source = unpack(self.archive.read(token + '.viv'))
            full=type(resource['tracks']) is dict
            if not full:
                compiler = CinematicTemplate(source, hashlib.sha256(source).hexdigest(), token,
                                             resource['rig_sha256'], resource['bone_count'])
            prefix = 'FI' if token.startswith('CI_') else 'FV'
            number = next_number[prefix]
            while number <= 99999 and (prefix + f'{number:05}.viv').lower() in occupied:
                number += 1
            require(number <= 99999, 'Cinematic native identifier capacity exhausted')
            assigned = prefix + f'{number:05}'
            native = assigned + '.viv'
            if full:
                require(graphs is not None,'Full cinematic needs its verified graph compiler')
                data,receipt=graphs.compose(resource['tracks'],assigned,resource['rig_sha256'],resource['bone_count'],hands)
                require(resource['tracks']['layout']==('intro' if prefix=='FI' else 'single-camera'),'Cinematic layout differs from resource category')
                receipt.update(native_name=assigned,template=token)
            else:data, receipt = compiler.compose(assigned, resource['tracks'])
            compiled_bytes += len(data)
            require(compiled_bytes <= MAX_ARCHIVE, 'Cinematic archive exceeds its byte budget')
            additions[native], bindings[key] = data, receipt
            occupied.add(native.lower()); next_number[prefix] = number + 1
        result = self.archive.compose(additions=additions)
        return result, {'schema': 'fighter-cinematic-archive-1', 'source_sha256': self.sha256,
                        'sha256': hashlib.sha256(result).hexdigest(), 'bindings': bindings,
                        'runtime_ready': False}


def bind_cinematics(banks, receipt, nis, expected_nis_sha256, cores):
    """Couple full core identities to typed intro/victory resources and XML.

    The generated lookup labels are independent of appearance names. The native
    adapter supplies them only for the explicitly requested participant.
    """
    require(isinstance(banks, bytes) and type(receipt) is dict
            and receipt.get('schema') == 'fighter-cinematic-archive-1'
            and receipt.get('sha256') == hashlib.sha256(banks).hexdigest()
            and type(receipt.get('bindings')) is dict,
            'Cinematic bindings require their compiled bank receipt')
    require(isinstance(nis, bytes) and hashlib.sha256(nis).hexdigest() == expected_nis_sha256,
            'Cinematic bindings require a verified native list archive')
    from fighter_behavior_identity import valid, CAF_BIT, population
    require(population(cores)
            and all(valid(core) for core in cores),
            'Cinematic bindings require bounded full core identities')
    archive, native = Archive(banks), Archive(nis)
    xml = unpack(native.read('assets/IntroExtro.xml'))
    compiler = Cinematics(xml, hashlib.sha256(xml).hexdigest())
    version=2 if any(type(value) is dict and value.get('full_graph') for value in receipt['bindings'].values()) else 1
    if any(core & CAF_BIT for core in cores):version=3
    entries, rows, report = [], bytearray(), {}
    caf_index=16384
    for core, pair in sorted(cores.items()):
        require(type(pair) is dict and set(pair) == {'intro', 'victory'},
                'Cinematic core needs explicit intro and victory resources')
        names = [];flags=0
        for kind, prefix in (('intro', 'FI'), ('victory', 'FV')):
            key = pair[kind]
            require(isinstance(key, str) and key in receipt['bindings'], 'Unknown cinematic resource')
            resource = receipt['bindings'][key]
            require(type(resource) is dict and isinstance(resource.get('native_name'), str)
                    and isinstance(resource.get('sha256'), str), 'Malformed cinematic resource receipt')
            name = resource['native_name']
            require(isinstance(name, str) and re.fullmatch(prefix + r'[0-9]{5}', name),
                    'Cinematic resource kind differs from its binding')
            require(hashlib.sha256(archive.read(name + '.viv')).hexdigest() == resource['sha256'],
                    'Cinematic resource bytes differ from their receipt')
            names.append(name)
            if resource.get('full_graph'):flags|=1<<(kind=='victory')
        index=core
        if core & CAF_BIT:index=caf_index;caf_index+=1
        label = f'fmc{index:05d}'
        entries.append(Cinematic(label, *names))
        rows.extend(struct.pack('<I8s8s', core, *(name.encode('ascii') for name in names)))
        if version>=2:rows.extend(struct.pack('<I',flags))
        report[str(core)] = {'label': label, 'intro': names[0], 'victory': names[1]}
    result = native.compose(replacements={'assets/IntroExtro.xml': compiler.compose(entries, {
        entry.name[:-4] for entry in archive.entries if entry.name.endswith('.viv')})})
    table = (struct.pack('<4s5I', b'FIC3' if version==3 else b'FIC2' if version==2 else b'FIC1', version, len(cores), len(banks), len(result), 0)
             + hashlib.sha256(banks).digest() + hashlib.sha256(result).digest() + rows)
    return result, bytes(table), {'schema': 'fighter-cinematic-bindings-1', 'bindings': report,
                                 'banks_sha256': hashlib.sha256(banks).hexdigest(),
                                 'nis_sha256': hashlib.sha256(result).hexdigest(), 'runtime_ready': False}
