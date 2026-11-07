"""Typed five-role motion reconstruction, deliberately outside pack admission.

The initial profile covers independent block seeds (type18/20), one timed
rotation helper (type13), and explicit face/hand palette selections (type25).
It preserves quantized values rather than resampling into another codec. Only
the verified template supplies opaque parent controls. All pointers, wrappers
and attribute records are freshly emitted; source addresses never become input.
"""
import copy
import hashlib
import math
import struct

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_compile import AnimationTemplate, rebuild
from fighter_animation_curves import CurveLayouts
from fighter_animation_scalars import ScalarCurve, f32
from fighter_animation_timed_quaternions import TimedQuaternionCurve
from fighter_face import FacePalettes
from fighter_elf import MAX_BYTES

FORMAT = 'fighter-motion-graph-draft-1'
ROLES = {'body': '_s', 'root': '_t', 'helper': '_d', 'face': '_f', 'hands': '_h'}
MAX_KEYS = 4096


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()), 'Motion fields differ from the typed schema')


def integer(value, low, high):
    require(type(value) is int and low <= value <= high, 'Motion integer exceeds its supported range')
    return value


def array(value, low, high):
    require(type(value) is list and low <= len(value) <= high, 'Motion array exceeds its supported length')
    return value


def matrix(value, rows, columns, maximum):
    return [[integer(v, 0, maximum) for v in array(row, columns, columns)]
            for row in array(value, rows, rows)]


def floats(value, count):
    for v in array(value, count, count):
        require(type(v) in (int, float) and math.isfinite(v) and abs(v) <= 1_000_000,
                'Motion scalar must be bounded and finite')
        f32(v)


def times(value, count, optional=False, transitions=True):
    if value is None and optional:
        return
    require(count > 0, 'Explicit motion times need at least one entry')
    values = [integer(v, 1 if transitions else 0, 65534 if transitions else 65535)
              for v in array(value, count, count)]
    require(all(a < b for a, b in zip(values, values[1:])), 'Motion times must strictly increase')


def unpack_seed(words):
    return [word >> 4 for word in words] + [((words[0] & 15) << 8) | ((words[1] & 15) << 4) | (words[2] & 15)]


def pack_seed(values):
    a, b, c, d = values
    return struct.pack('<3H', (a << 4) | (d >> 8), (b << 4) | ((d >> 4) & 15), (c << 4) | (d & 15))


def parent_profile(layout, parent):
    """Known one-entry scale attributes; opaque control/padding must match donor."""
    require(layout.index.record_types[parent] == 15, 'Motion role requires a type15 parent')
    control = layout.values(parent + 2, 1)[0]
    duration = layout.values(parent + 10, 1)[0]
    attributes = layout.pointer(parent + 4, 12)
    count, key_size, value = layout.values(attributes, 3, 'I')
    require(count == 1 and key_size == 65537 and value & 255, 'Unsupported motion parent scale attributes')
    return control, value & 0xFFFFFF00, duration, value & 255


def read_leaf(layout, record):
    info = layout.records[record]
    kind, keys = info['kind'], info['keys']
    require(keys <= MAX_KEYS, 'Motion key count exceeds the typed profile')
    if kind in (18, 20):
        require(info['block_shift'] == 0 and info['constants'] == 0 and info['channels'] > 0,
                'Typed seed profile requires dynamic channels and independent block seeds')
        channels = info['channels']
        if kind == 18:
            destinations = list(layout.values(layout.pointer(record + 12, channels), channels, 'B'))
            coefficients = [list(layout.values(record + 18 + 16 * c, 8)) for c in range(channels)]
            start = record + 18 + 16 * channels
            samples = [[unpack_seed(layout.values(start + (k * channels + c) * 6, 3))
                        for c in range(channels)] for k in range(keys)]
        else:
            require(layout.values(record + 18, 2, 'B') == (0, 0), 'Unsupported vector header controls')
            destinations = list(layout.values(layout.pointer(record + 4, channels * 2), channels))
            coefficients = [{'base': list(layout.values(record + 20 + 36 * c, 3, 'f')),
                             'extent': list(layout.values(record + 32 + 36 * c, 3, 'f')),
                             'offset': list(layout.values(record + 44 + 36 * c, 3)),
                             'range': list(layout.values(record + 50 + 36 * c, 3))} for c in range(channels)]
            start = record + 20 + 36 * channels
            samples = [[list(layout.values(start + (k * channels + c) * 6, 3))
                        for c in range(channels)] for k in range(keys)]
        stamps = layout.times(record + 8, keys, transitions=True, optional=True)
        return {'kind': kind, 'destinations': destinations, 'coefficients': coefficients,
                'times': None if stamps is None else list(stamps), 'samples': samples}
    if kind == 13:
        curve = ScalarCurve(layout, record)
        descriptor = layout.pointer(record + 4, 4)
        require(layout.values(descriptor + 3, 1, 'B') == (0,), 'Unsupported timed descriptor control')
        return {'kind': kind, 'destinations': list(layout.values(record + 14, curve.scalars // 4)),
                'times': list(layout.times(record + 8, keys, transitions=True)), 'bits': curve.bits,
                'coefficients': [list(row) for row in curve.coefficients],
                'deltas': [[curve.quantized(k, c) for c in range(curve.scalars)] for k in range(keys - 1)]}
    require(kind == 25, 'Unsupported palette curve type')
    return {'kind': 25, 'selector': info['sample_bank_selector'],
            'samples': list(layout.values(layout.pointer(record + 8, keys), keys, 'B')),
            'times': list(layout.times(record + 12, keys))}


def read_motion(index, token, rig_sha256, bone_count):
    """Export numeric data for review, without trusting its source controls."""
    layout = CurveLayouts(index)
    graphs = {}
    for role, suffix in ROLES.items():
        require(token + suffix in index.lookup, 'Motion is missing a required graph role')
        parent = index.records[index.lookup[token + suffix]]
        _, _, duration, scale = parent_profile(layout, parent)
        graphs[role] = {'duration_ticks': duration, 'time_scale': scale,
                        'children': [read_leaf(layout, child) for child in index.children[parent]]}
    return {'format': FORMAT, 'rig_sha256': rig_sha256, 'bone_count': bone_count, 'graphs': graphs}


def validate_motion(value, rig_sha256, bone_count, face, hands):
    fields(value, 'format rig_sha256 bone_count graphs')
    require(value['format'] == FORMAT and value['rig_sha256'] == rig_sha256
            and type(value['bone_count']) is int and value['bone_count'] == bone_count,
            'Motion differs from the verified rig')
    require(type(face) is FacePalettes and face.bone_count == bone_count and type(hands) is FacePalettes,
            'Motion needs validated face and hand output contexts')
    fields(value['graphs'], 'body root helper face hands')
    for role, graph in value['graphs'].items():
        fields(graph, 'duration_ticks time_scale children')
        integer(graph['duration_ticks'], 0, 65535)
        integer(graph['time_scale'], 1, 255)
        count = 2 if role in ('face', 'hands') else 1
        for ordinal, leaf in enumerate(array(graph['children'], count, count)):
            expected_kind = {'body': 18, 'root': 20, 'helper': 13, 'face': 25, 'hands': 25}[role]
            require(type(leaf) is dict and type(leaf.get('kind')) is int and leaf['kind'] == expected_kind,
                    'Motion codec does not match its output role')
            if expected_kind in (18, 20):
                fields(leaf, 'kind destinations coefficients times samples')
                destinations = array(leaf['destinations'], 1, min(bone_count, 256) if role == 'body' else 1)
                channels = len(destinations)
                require(all(type(v) is int for v in destinations)
                        and (len(set(destinations)) == channels and all(0 <= v < min(bone_count, 256) for v in destinations)
                             if role == 'body' else destinations == [8]),
                        'Motion destinations escape the output contract')
                keys = len(array(leaf['samples'], 1, MAX_KEYS))
                times(leaf['times'], keys - 1, optional=True)
                for row in leaf['samples']:
                    matrix(row, channels, 4 if role == 'body' else 3, 4095 if role == 'body' else 65535)
                if role == 'body':
                    matrix(leaf['coefficients'], channels, 8, 65535)
                else:
                    for row in array(leaf['coefficients'], channels, channels):
                        fields(row, 'base extent offset range')
                        floats(row['base'], 3); floats(row['extent'], 3)
                        matrix([row['offset'], row['range']], 2, 3, 65535)
            elif expected_kind == 13:
                fields(leaf, 'kind destinations times bits coefficients deltas')
                require(leaf['destinations'] == [4] and type(leaf['destinations'][0]) is int,
                        'Helper must write one quaternion within its 48-byte output')
                require(type(leaf['bits']) is int and leaf['bits'] in (4, 8, 16), 'Unsupported timed delta width')
                keys = len(array(leaf['deltas'], 1, MAX_KEYS - 1)) + 1
                times(leaf['times'], keys - 1)
                matrix(leaf['deltas'], keys - 1, 4, (1 << leaf['bits']) - 1)
                for row in array(leaf['coefficients'], 4, 4):
                    floats(row, 3)
            else:
                fields(leaf, 'kind selector samples times')
                require(type(leaf['selector']) is int and leaf['selector'] == ordinal,
                        'Palette roles require ordered selectors zero and one')
                samples = [integer(v, 0, 255) for v in array(leaf['samples'], 1, MAX_KEYS)]
                times(leaf['times'], len(samples), transitions=False)
                (face if role == 'face' else hands).require_samples(ordinal, tuple(samples))


class Writer:
    def __init__(self, payload, pointers):
        self.payload, self.pointers = payload, pointers

    def append(self, data):
        require(len(self.payload) + len(data) + 4 <= MAX_BYTES, 'Motion exceeds compiled byte budget')
        self.payload.extend(bytes(-len(self.payload) % 4))
        at = len(self.payload); self.payload.extend(data)
        return at

    def pointer(self, field, target):
        self.pointers[field] = target
        struct.pack_into('<I', self.payload, field, target)

    def leaf(self, leaf, control=0, palette_padding=0):
        kind = leaf['kind']
        samples = leaf.get('samples', [])
        if kind in (18, 20):
            channels = len(leaf['destinations'])
            if kind == 18:
                data = bytearray(struct.pack('<HHHBBIIBB', kind, control, len(samples), channels, 0, 0, 0, 0, 0))
                data.extend(b''.join(struct.pack('<8H', *c) for c in leaf['coefficients']))
                data.extend(b''.join(pack_seed(c) for row in samples for c in row))
                destination_data = bytes(leaf['destinations'])
                destination_field = 12
            else:
                data = bytearray(struct.pack('<HHIIHH4B', kind, control, 0, 0, len(samples), channels, 0, 0, 0, 0))
                data.extend(b''.join(struct.pack('<6f6H', *c['base'], *c['extent'], *c['offset'], *c['range']) for c in leaf['coefficients']))
                data.extend(b''.join(struct.pack('<3H', *c) for row in samples for c in row))
                destination_data = struct.pack('<' + 'H' * channels, *leaf['destinations'])
                destination_field = 4
            at = self.append(data)
            self.pointer(at + destination_field, self.append(destination_data))
            if leaf['times'] is not None:
                self.pointer(at + 8, self.append(struct.pack('<' + 'H' * len(leaf['times']), *leaf['times'])))
            return at
        if kind == 13:
            bits = leaf['bits']
            data = bytearray(struct.pack('<HBB', 4, bits, 0))
            data.extend(b''.join(struct.pack('<3f', *c) for c in leaf['coefficients']))
            for row in leaf['deltas']:
                data.extend(bytes([row[0] | (row[1] << 4), row[2] | (row[3] << 4)]) if bits == 4
                            else struct.pack('<' + ('B' if bits == 8 else 'H') * 4, *row))
            descriptor = self.append(data)
            stamps = self.append(struct.pack('<' + 'H' * len(leaf['times']), *leaf['times']))
            at = self.append(struct.pack('<HHIIHH', 13, control, 0, 0, len(leaf['deltas']) + 1, 4))
            self.pointer(at + 4, descriptor); self.pointer(at + 8, stamps)
            return at
        samples_at = self.append(bytes(samples))
        stamps = self.append(struct.pack('<' + 'H' * len(leaf['times']), *leaf['times']))
        start = self.append(struct.pack('<5IHHHBBII', 0, 0, 25, 0, 0, 25, control, len(samples), leaf['selector'], palette_padding, 0, 0))
        at = start + 20
        self.pointer(at + 8, samples_at); self.pointer(at + 12, stamps)
        return at


class FullMotionTemplate:
    def __init__(self, template, face, hands):
        require(type(template) is AnimationTemplate, 'Motion requires a verified animation template')
        self.template, self.face, self.hands = template, face, hands

    def compose(self, token, value):
        template = self.template
        index, model = template.index, template.index.model
        require(token in index.envelope.tokens and token + '_s' in index.lookup, 'Unknown motion token')
        layout = CurveLayouts(index)
        validate_motion(value, template.rig_sha256, template.bone_count, self.face, self.hands)
        value = copy.deepcopy(value)
        for row in value['graphs']['root']['children'][0]['coefficients']:
            for name in ('base', 'extent'):
                row[name] = list(map(f32, row[name]))
        value['graphs']['helper']['children'][0]['coefficients'] = [list(map(f32, row))
            for row in value['graphs']['helper']['children'][0]['coefficients']]
        payload = bytearray(model.data[model.sections[1][4]:model.sections[1][4] + model.sections[1][5]])
        pointers = {at: row['target'] for at, row in model.pointers.items()}
        writer = Writer(payload, pointers)
        root = model.export_offset(index.envelope.bank)
        table = model.local_pointer(root + 16, len(index.records) * 4)
        for role, suffix in ROLES.items():
            require(token + suffix in index.lookup, 'Template lacks a motion graph role')
            slot = index.lookup[token + suffix]
            old = index.records[slot]
            control, padding, _, _ = parent_profile(layout, old)
            graph = value['graphs'][role]
            expected_types = [leaf['kind'] for leaf in graph['children']]
            require(role == 'body' or [index.record_types[child] for child in index.children[old]] == expected_types,
                    'Template graph differs from the supported role shape')
            controls = [layout.values(child + 2, 1)[0] for child in index.children[old]]
            require(controls and (role != 'body' or len(set(controls)) == 1), 'Template body controls differ')
            children = [writer.leaf(leaf, controls[i], layout.values(index.children[old][i] + 7, 1, 'B')[0]
                                   if leaf['kind'] == 25 else 0)
                        for i, leaf in enumerate(graph['children'])]
            attributes = writer.append(struct.pack('<3I', 1, 65537, padding | graph['time_scale']))
            parent = writer.append(struct.pack('<HHIHH', 15, control, 0, len(children), graph['duration_ticks']) + bytes(4 * len(children)))
            writer.pointer(parent + 4, attributes)
            for i, child in enumerate(children):
                writer.pointer(parent + 12 + 4 * i, child)
            writer.pointer(table + 4 * slot, parent)
        payload.extend(bytes(-len(payload) % 4))
        data, links = rebuild(model, payload, pointers)
        names = struct.pack('<2I', len(index.envelope.tokens), 0) + '.'.join(index.envelope.tokens).encode('ascii') + b'.'
        result = AnimationEnvelope(data, links, names)
        parsed = AnimationIndex(result)
        actual = read_motion(parsed, token, template.rig_sha256, template.bone_count)
        # Exact typed values after float32 canonicalization; no resampling claim.
        require(actual == value, 'Rebuilt motion differs from its typed values')
        helper_parent = parsed.records[parsed.lookup[token + '_d']]
        helper = TimedQuaternionCurve(CurveLayouts(parsed), parsed.children[helper_parent][0])
        for pose in helper.scalar.poses():
            require(0.000001 <= sum(v * v for v in pose) <= 1_000_000,
                    'Helper quaternion has a degenerate or unbounded norm')
        # Native interpolation normalizes; ensure neither precision profile can
        # divide by zero on an admitted interval after quantized reconstruction.
        for low, high in zip((0, *helper.times[:-1]), helper.times):
            for precision in (24, 53):
                helper.sample((low + high) / 2, precision_bits=precision)
        return result, {'schema': FORMAT, 'source_sha256': template.sha256,
                        'sha256': hashlib.sha256(result.model.data).hexdigest(),
                        'roles': list(ROLES), 'source_parent_timing_preserved': True,
                        'unwritten_pose_channels_validated': False,
                        'native_playtest': False, 'runtime_ready': False}

    def convert(self, source, source_token, template_token):
        """Explicit source conversion refuses unknown controls instead of dropping them."""
        require(type(source) is AnimationIndex and set(source.names) == {source_token + suffix for suffix in ROLES.values()},
                'Source motion contains missing or unaccounted named graphs')
        before, after = CurveLayouts(source), CurveLayouts(self.template.index)
        for suffix in ROLES.values():
            require(source_token + suffix in source.lookup and template_token + suffix in after.index.lookup,
                    'Conversion is missing a required graph role')
            a = source.records[source.lookup[source_token + suffix]]
            b = after.index.records[after.index.lookup[template_token + suffix]]
            require(parent_profile(before, a)[:2] == parent_profile(after, b)[:2],
                    'Source motion has unsupported parent controls')
            source_controls = [before.values(c + 2, 1)[0] for c in source.children[a]]
            template_controls = [after.values(d + 2, 1)[0] for d in after.index.children[b]]
            require((len(source_controls) == 1 and set(source_controls) == set(template_controls))
                    if suffix == '_s' else source_controls == template_controls,
                    'Source motion has unsupported child controls')
            if suffix in ('_f', '_h'):
                require([before.values(c + 7, 1, 'B') for c in source.children[a]]
                        == [after.values(c + 7, 1, 'B') for c in after.index.children[b]],
                        'Source motion has unsupported palette padding')
        value = read_motion(source, source_token, self.template.rig_sha256, self.template.bone_count)
        return self.compose(template_token, value)
