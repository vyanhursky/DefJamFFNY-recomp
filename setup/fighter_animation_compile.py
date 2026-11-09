"""Compose owned quaternion animation into a hash-verified local bank.

Only typed tracks enter the generated record. Other animations, motion names,
parent timing/attributes and paired event/root-motion records remain inherited.
The caller supplies the verified template/rig association, never a package's
self-asserted trust hash. Native admission remains a separate gate.
"""
import hashlib
import struct

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_curves import CurveLayouts
from fighter_animation_scalars import ScalarCurve
from fighter_animation_tracks import QuaternionTracks
from fighter_elf import MAX_BYTES


def rebuild(template, payload, pointers):
    """Emit only local data relocations while preserving trusted symbol names."""
    require(not template.imports, 'Animation template must be self-contained')
    # A dedicated section symbol makes every emitted pointer section-relative.
    symbols = [('', 0, 0, 0, 0), ('', 0, 0, 3, 1), *template.symbols[1:]]
    strings, table, relocations = bytearray(b'\0'), bytearray(), bytearray()
    for name, value, size, info, section in symbols:
        at = len(strings) if name else 0
        if name:
            strings.extend(name.encode('ascii') + b'\0')
        table.extend(struct.pack('<IIIBBH', at, value, size, info, 0, section))
    for at, target in pointers.items():
        struct.pack_into('<I', payload, at, target)
        relocations.extend(struct.pack('<II', at, 258))
    names = template.sections[2]
    pieces = [b'', bytes(payload), template.data[names[4]:names[4] + names[5]],
              bytes(strings), bytes(table), bytes(relocations)]
    image, rows = bytearray(template.data[:52]), [(0,) * 10]
    for i in range(1, 6):
        row = list(template.sections[i])
        image.extend(bytes(-len(image) % row[8]))
        row[4:6] = [len(image), len(pieces[i])]
        if i == 4:
            row[7] += 1
        image.extend(pieces[i]); rows.append(tuple(row))
    image.extend(bytes(-len(image) % 4))
    struct.pack_into('<I', image, 32, len(image))
    image.extend(b''.join(struct.pack('<10I', *row) for row in rows))
    split = rows[1][4] + rows[1][5]
    require(split == rows[2][4], 'Generated animation split requires contiguous links')
    return bytes(image[:split]), bytes(image[split:])


class AnimationTemplate:
    def __init__(self, envelope, expected_sha256, rig_sha256, bone_count):
        require(type(envelope) is AnimationEnvelope
                and hashlib.sha256(envelope.model.data).hexdigest() == expected_sha256,
                'Animation compiler requires a verified local bank')
        # Validate rig identity and its numeric capacity without an input track.
        QuaternionTracks(rig_sha256, bone_count, (0,), (((0., 0., 0., 1.),),)).validate()
        self.index = AnimationIndex(envelope)
        require(envelope.tokens is not None, 'Animation compiler requires its motion-name list')
        self.rig_sha256, self.bone_count = rig_sha256, bone_count
        self.sha256 = expected_sha256

    def compose(self, replacements):
        require(type(replacements) is dict and 0 < len(replacements) <= 1000,
                'Animation compiler needs a bounded set of motion tokens')
        index, model = self.index, self.index.model
        payload = bytearray(model.data[model.sections[1][4]:model.sections[1][4] + model.sections[1][5]])
        pointers = {at: value['target'] for at, value in model.pointers.items()}
        root = model.export_offset(index.envelope.bank)
        record_table = model.local_pointer(root + 16, len(index.records) * 4)
        report = {}

        def append(data):
            require(len(payload) + len(data) + 4 <= MAX_BYTES,
                    'Composed animation exceeds its byte budget')
            payload.extend(bytes(-len(payload) % 4))
            start = len(payload); payload.extend(data)
            return start

        for token, tracks in sorted(replacements.items()):
            require(isinstance(token, str) and token in index.envelope.tokens
                    and index.envelope.tokens.index(token) < 1000,
                    'Unknown or unaddressable participant motion token')
            require(type(tracks) is QuaternionTracks and tracks.rig_sha256 == self.rig_sha256
                    and tracks.bone_count == self.bone_count,
                    'Animation tracks differ from the verified template rig')
            require(tracks.bones == tuple(range(self.bone_count)),
                    'Replacing a skeletal record requires full rig quaternion coverage')
            paired = [index.lookup.get(token + suffix, -1) for suffix in ('_s', '_t')]
            require(all(row >= 0 for row in paired), 'Animation token has a missing paired record')
            old = index.records[paired[0]]
            require(index.record_types[old] == 15, 'Quaternion replacement needs a type15 parent')
            at = model.data_range(old, 12)
            header = bytearray(model.data[at:at + 12])
            duration, = struct.unpack_from('<H', header, 10)
            require(len(tracks.poses) == duration + 1,
                    'Authored samples must cover every inherited child-time tick including the endpoint')
            descriptor, receipt = tracks.encode()
            descriptor_at = append(descriptor)
            destinations = receipt['destinations']
            child = append(struct.pack('<HHIH', 11, 0, descriptor_at, len(tracks.poses))
                           + struct.pack('<' + 'H' * len(destinations), *destinations))
            pointers[child + 4] = descriptor_at
            struct.pack_into('<H', header, 8, 1)
            parent = append(header + struct.pack('<I', child))
            if old + 4 in pointers:
                pointers[parent + 4] = pointers[old + 4]
            else:
                require(struct.unpack_from('<I', header, 4)[0] == 0,
                        'Animation parent attributes require an explicit relocation')
            pointers[parent + 12] = child
            pointers[record_table + paired[0] * 4] = parent
            report[token] = {**receipt, 'parent': parent, 'child': child, 'duration_ticks': duration,
                             'inherited_paired_record': index.records[paired[1]]}
        payload.extend(bytes(-len(payload) % 4))
        data, links = rebuild(model, payload, pointers)
        names = struct.pack('<2I', len(index.envelope.tokens), 0) + '.'.join(index.envelope.tokens).encode('ascii') + b'.'
        result = AnimationEnvelope(data, links, names)
        parsed = AnimationIndex(result)
        curves = CurveLayouts(parsed)
        for token, receipt in report.items():
            curve = ScalarCurve(curves, receipt['child'])
            require(curve.info['required_output_floats'] <= 12 * self.bone_count,
                    'Authored animation writes outside its rig pose')
            # Reparse emitted bytes, then compare all decoded keys with the
            # creator input rather than trusting the writer's receipt alone.
            expected = replacements[token].poses
            for actual, pose in zip(curve.poses(), expected):
                require(max(abs(a - b) for a, b in zip(actual, (v for q in pose for v in q))) <= 0.000101,
                        'Emitted animation differs from authored quaternion tracks')
        return result, {'schema': 'fighter-animation-template-1', 'source_sha256': self.sha256,
                        'sha256': hashlib.sha256(result.model.data).hexdigest(), 'bindings': report,
                        'motion_names_preserved': True, 'inherited_timing_preserved': True,
                        'runtime_ready': False}
