"""Invented five-role graphs: preservation, output joins and trust boundaries."""
import hashlib
import struct

import pytest

from test_fighter_animation import index_fixture
from test_fighter_face import face_model
from fighter_animation import AnimationEnvelope, AnimationIndex
from fighter_animation_compile import AnimationTemplate, rebuild
from fighter_animation_graphs import FORMAT, ROLES, Writer, FullMotionTemplate, read_motion
from fighter_animation_curves import CurveLayouts
from fighter_animation_quaternions import QuaternionCurve
from fighter_animation_vectors import VectorCurve
from fighter_animation_timed_quaternions import TimedQuaternionCurve
from fighter_assets import AssetError
from fighter_elf import Model, ModelError
from fighter_face import FacePalettes

RIG = 'a' * 64


def palettes():
    original = face_model()
    payload = bytearray(144)
    struct.pack_into('<IHH2I', payload, 0, 0, 2, 0, 16, 80)
    for offset, samples, destinations in ((16, 32, 64), (80, 96, 128)):
        struct.pack_into('<IIBBBB', payload, offset, samples, destinations, 2, 1, 0, 0)
        struct.pack_into('<8f', payload, samples, 0, 0, 0, 1, 0, 0, 0, 1)
        struct.pack_into('<H', payload, destinations, 4)
    pointers = {8: 16, 12: 80, 16: 32, 20: 64, 80: 96, 84: 128}
    data, links = rebuild(original, payload, pointers)
    return FacePalettes(Model(data + links), 2, (2, 2))


def motion():
    body = {'kind': 18, 'destinations': [0, 1], 'times': [2],
            'coefficients': [[32768] * 8 for _ in range(2)],
            'samples': [[[2048, 2048, 2048, 4095], [2048, 2048, 2048, 4095]],
                        [[4095, 2048, 2048, 2048], [2048, 4095, 2048, 2048]]]}
    root = {'kind': 20, 'destinations': [8], 'times': None,
            'coefficients': [{'base': [0., 0., 0.], 'extent': [1., 1., 1.], 'offset': [0] * 3, 'range': [65535] * 3}],
            'samples': [[[0, 0, 0]], [[65535, 32768, 0]]]}
    helper = {'kind': 13, 'destinations': [4], 'times': [2], 'bits': 8,
              'coefficients': [[0., 0., 0.], [0., 0., 0.], [0., 0., 0.], [0., 0., 1.]],
              'deltas': [[0, 0, 0, 0]]}
    children = {'body': [body], 'root': [root], 'helper': [helper]}
    for role in ('face', 'hands'):
        children[role] = [{'kind': 25, 'selector': s, 'samples': [0, 1, 0], 'times': [0, 2, 4]} for s in (0, 1)]
    return {'format': FORMAT, 'rig_sha256': RIG, 'bone_count': 2,
            'graphs': {role: {'duration_ticks': 12, 'time_scale': 60, 'children': leaves} for role, leaves in children.items()}}


def graph_template():
    base = index_fixture().model
    payload = bytearray(24)
    pointers = {}
    writer = Writer(payload, pointers)
    records, names = [], []
    value = motion()
    for i, (role, suffix) in enumerate(sorted(ROLES.items(), key=lambda row: row[1])):
        children = [writer.leaf(leaf) for leaf in value['graphs'][role]['children']]
        attribute = writer.append(struct.pack('<3I', 1, 65537, 0x3030303C))
        parent = writer.append(struct.pack('<HHIHH', 15, 100 + i, 0, len(children), 12) + bytes(4 * len(children)))
        writer.pointer(parent + 4, attribute)
        for c, child in enumerate(children):
            writer.pointer(parent + 12 + 4 * c, child)
        records.append(parent)
        names.append(writer.append(('A' + suffix).encode() + b'\0'))
    record_table, name_table = writer.append(bytes(20)), writer.append(bytes(20))
    struct.pack_into('<6I', payload, 0, 0, 5, 0, 0, record_table, name_table)
    pointers.update({16: record_table, 20: name_table})
    for i in range(5):
        writer.pointer(record_table + 4 * i, records[i]); writer.pointer(name_table + 4 * i, names[i])
    payload.extend(bytes(-len(payload) % 4))
    data, links = rebuild(base, payload, pointers)
    envelope = AnimationEnvelope(data, links, struct.pack('<2I', 1, 0) + b'A.')
    verified = AnimationTemplate(envelope, hashlib.sha256(envelope.model.data).hexdigest(), RIG, 2)
    return FullMotionTemplate(verified, palettes(), palettes())


def test_all_roles_rebuild_with_independent_parent_timing_and_local_pointers():
    compiler = graph_template()
    value = motion()
    for i, graph in enumerate(value['graphs'].values()):
        graph['duration_ticks'] = 70 + i
        graph['time_scale'] = 12 + i
    result, receipt = compiler.compose('A', value)
    index = AnimationIndex(result)
    assert read_motion(index, 'A', RIG, 2) == value
    assert index.names == compiler.template.index.names
    assert result.tokens == ('A',)
    assert not receipt['runtime_ready'] and not receipt['native_playtest']
    assert all(not row['imported'] for row in result.model.pointers.values())
    assert not set(index.records) & set(compiler.template.index.records)
    layout = CurveLayouts(index)
    def child(suffix):
        return index.children[index.records[index.lookup['A' + suffix]]][0]
    # Independent known numerical expectations check the encoded layouts.
    body = QuaternionCurve(layout, child('_s'))
    assert body.pose(0)[0][3] == 1 and body.pose(1)[0][0] == 1
    root = VectorCurve(layout, child('_t'))
    assert root.pose(0) == ((0., 0., 0.),)
    assert root.pose(1)[0][0] == 1
    assert TimedQuaternionCurve(layout, child('_d')).sample(1, precision_bits=24) == ((0., 0., 0., 1.),)


@pytest.mark.parametrize('change,match', [
    (lambda v: v.update(rig_sha256='b' * 64), 'verified rig'),
    (lambda v: v.update(code='run.dll'), 'typed schema'),
    (lambda v: v['graphs']['body'].update(time_scale=0), 'integer'),
    (lambda v: v['graphs']['body'].update(duration_ticks=True), 'integer'),
    (lambda v: v['graphs']['body']['children'][0].update(destinations=[0, 2]), 'destinations'),
    (lambda v: v['graphs']['root']['children'][0].update(destinations=[9]), 'destinations'),
    (lambda v: v['graphs']['helper']['children'][0].update(destinations=[12]), '48-byte'),
    (lambda v: v['graphs']['helper']['children'][0].update(times=[0]), 'integer'),
    (lambda v: v['graphs']['body']['children'][0]['samples'][0][0].__setitem__(0, 4096), 'integer'),
    (lambda v: v['graphs']['root']['children'][0]['coefficients'][0]['base'].__setitem__(0, float('nan')), 'finite'),
    (lambda v: v['graphs']['face']['children'][0].update(samples=[0, 2, 0]), 'capacity'),
    (lambda v: v['graphs']['hands']['children'][1].update(selector=0), 'selectors'),
    (lambda v: v['graphs']['face']['children'][0].update(times=[0, 0, 1]), 'strictly increase'),
    (lambda v: v['graphs']['root']['children'][0].update(address=123), 'typed schema'),
])
def test_untrusted_numbers_shapes_and_context_mismatches_are_rejected(change, match):
    value = motion(); change(value)
    with pytest.raises((AssetError, ModelError), match=match):
        graph_template().compose('A', value)


def test_source_conversion_checks_unknown_controls_instead_of_silently_dropping_them():
    compiler = graph_template()
    source = compiler.template.index
    converted, _ = compiler.convert(source, 'A', 'A')
    assert read_motion(AnimationIndex(converted), 'A', RIG, 2) == motion()
    model = source.model
    payload = bytearray(model.data[model.sections[1][4]:model.sections[1][4] + model.sections[1][5]])
    struct.pack_into('<H', payload, source.records[0] + 2, 999)
    data, links = rebuild(model, payload, {at: p['target'] for at, p in model.pointers.items()})
    changed = AnimationIndex(AnimationEnvelope(data, links, struct.pack('<2I', 1, 0) + b'A.'))
    with pytest.raises(AssetError, match='parent controls'):
        compiler.convert(changed, 'A', 'A')


@pytest.mark.parametrize('bits', [4, 8, 16])
def test_helper_quantized_values_survive_without_resampling(bits):
    value = motion()
    leaf = value['graphs']['helper']['children'][0]
    leaf.update(bits=bits, deltas=[[0, 1, (1 << bits) - 1, 2]])
    output, _ = graph_template().compose('A', value)
    assert read_motion(AnimationIndex(output), 'A', RIG, 2) == value


def test_palette_child_controls_must_match_by_ordinal_not_as_a_set():
    compiler = graph_template()
    index, model = compiler.template.index, compiler.template.index.model
    parent = index.records[index.lookup['A_f']]
    children = index.children[parent]
    def change(controls):
        payload = bytearray(model.data[model.sections[1][4]:model.sections[1][4] + model.sections[1][5]])
        for child, control in zip(children, controls):
            struct.pack_into('<H', payload, child + 2, control)
        data, links = rebuild(model, payload, {at: p['target'] for at, p in model.pointers.items()})
        return AnimationEnvelope(data, links, struct.pack('<2I', 1, 0) + b'A.')
    template = change([123, 456])
    compiler = FullMotionTemplate(AnimationTemplate(template, hashlib.sha256(template.model.data).hexdigest(), RIG, 2), palettes(), palettes())
    with pytest.raises(AssetError, match='child controls'):
        compiler.convert(AnimationIndex(change([456, 123])), 'A', 'A')


def test_float32_canonicalization_does_not_mutate_authored_input():
    value = motion()
    value['graphs']['root']['children'][0]['coefficients'][0]['base'][0] = .1
    output, _ = graph_template().compose('A', value)
    actual = read_motion(AnimationIndex(output), 'A', RIG, 2)
    assert value['graphs']['root']['children'][0]['coefficients'][0]['base'][0] == .1
    assert actual['graphs']['root']['children'][0]['coefficients'][0]['base'][0] == struct.unpack('<f', struct.pack('<f', .1))[0]


def test_degenerate_helper_cannot_reach_native_normalization():
    value = motion()
    value['graphs']['helper']['children'][0]['coefficients'] = [[0., 0., 0.]] * 4
    with pytest.raises(AssetError, match='norm'):
        graph_template().compose('A', value)


def test_conversion_refuses_unaccounted_named_graphs():
    compiler = graph_template()
    model, index = compiler.template.index.model, compiler.template.index
    payload = bytearray(model.data[model.sections[1][4]:model.sections[1][4] + model.sections[1][5]])
    pointers = {at: p['target'] for at, p in model.pointers.items()}
    writer = Writer(payload, pointers)
    old_names = model.local_pointer(20, 20)
    records, names = writer.append(bytes(24)), writer.append(bytes(24))
    for i in range(5):
        writer.pointer(records + 4 * i, index.records[i])
        writer.pointer(names + 4 * i, model.local_pointer(old_names + 4 * i, 1))
    writer.pointer(records + 20, index.records[0])
    writer.pointer(names + 20, writer.append(b'Z_s\0'))
    writer.pointer(16, records); writer.pointer(20, names)
    struct.pack_into('<I', payload, 4, 6)
    data, links = rebuild(model, payload, pointers)
    source = AnimationIndex(AnimationEnvelope(data, links, struct.pack('<2I', 1, 0) + b'A.'))
    with pytest.raises(AssetError, match='unaccounted'):
        compiler.convert(source, 'A', 'A')
