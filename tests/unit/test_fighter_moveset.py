"""Action substitutions must preserve neighboring motion/event ownership."""
import hashlib
import struct

import pytest

from test_fighter_motion import stream, table, chunk
from test_fighter_animation_compile import template
from fighter_assets import AssetError
from fighter_motion import MotionIndex
from fighter_moveset import MovesetPlan


def fixture(change=None):
    parts = table() + table()
    parts[1] = chunk(b'FZUI', struct.pack('<2I', 39, 4) + bytes(156))
    data = bytearray(stream(parts, cores=3))
    start = MotionIndex(bytes(data)).core_spans[2]
    for row in range(130):
        struct.pack_into('<3H', data, start + 72 + row * 6, 0xffff, 2, 0)
    struct.pack_into('<3H', data, start + 78, 0, 0, 0)
    struct.pack_into('<3H', data, start + 84, 1, 1, 2)
    if change:
        change(data, start)
    envelope, _ = template()
    plan = MovesetPlan(MotionIndex(bytes(data)), 2, envelope, hashlib.sha256(envelope.model.data).hexdigest())
    return bytes(data), start, plan


def test_selection_copies_behavior_and_names_without_moving_boundaries():
    original, start, plan = fixture()
    pair, names, receipt = plan.compose({2: 1})
    assert struct.unpack_from('<3H', pair, 92) == (0, 1, 0)
    assert names == struct.pack('<2I', 2, 0) + b'A.A.'
    before = bytearray(original[start - 8:start + 852])
    struct.pack_into('<3H', before, 92, 0, 1, 0)
    assert pair == bytes(before)
    assert receipt['motion_aliases'] == {1: 0}
    assert not receipt['runtime_ready']


@pytest.mark.parametrize('selection', [{}, {2: 2}, {0: 1}, {2: 31}, {38: 1},
                                      {125: 1}, {True: 2}, {2: '1'}, {2: -1}])
def test_special_missing_or_untyped_actions_cannot_be_selected(selection):
    _, _, plan = fixture()
    with pytest.raises(AssetError):
        plan.compose(selection)


def test_control_flags_and_ambiguous_ranges_are_not_blindly_copied():
    _, _, plan = fixture(lambda data, start: struct.pack_into('<H', data, start + 84, 0x8001))
    with pytest.raises(AssetError, match='control flags'):
        plan.compose({2: 1})
    _, _, plan = fixture(lambda data, start: struct.pack_into('<H', data, start + 86, 0))
    with pytest.raises(AssetError, match='unambiguous'):
        plan.compose({2: 1})


def test_missing_paired_motion_and_unverified_bank_fail():
    _, _, plan = fixture()
    with pytest.raises(AssetError, match='paired record'):
        plan.compose({1: 2})
    with pytest.raises(AssetError, match='verified local'):
        MovesetPlan(plan.links.index, 2, plan.bank.envelope, '0' * 64)


def test_nonowning_action_alias_cannot_silently_change_behavior():
    _, _, plan = fixture(lambda data, start: struct.pack_into('<3H', data, start + 72 + 98 * 6, 1, 1, 2))
    with pytest.raises(AssetError, match='Another action aliases'):
        plan.compose({2: 1})


def test_selected_cores_have_separate_proofs_and_retain_inherited_resources():
    from fighter_motion_compile import MotionCoreTemplates
    from fighter_moveset import compose_selected_cores
    data, _, plan = fixture()
    templates = MotionCoreTemplates(data, hashlib.sha256(data).hexdigest())
    compiled, report, proof = compose_selected_cores(templates, {
        'alpha/moves': {'donor': 2, 'envelope': plan.bank.envelope,
                        'bank_sha256': hashlib.sha256(plan.bank.envelope.model.data).hexdigest(),
                        'selections': {2: 1}}, 'beta/moves': 2})
    assert compiled[:len(data)] == data
    assert proof[:4] == b'FMC2' and len(proof) == 56 + 280 * 2
    assert proof[24:56] == hashlib.sha256(compiled).digest()
    assert struct.unpack_from('<I', proof, 56 + 16) == (2,)
    assert struct.unpack_from('<H', proof, 56 + 20 + 2 * 2) == (1,)
    assert proof[56 + 280 + 20:] == bytes([255]) * 260
    assert report['selections']['alpha/moves']['motion_aliases'] == {1: 0}
    assert 'beta/moves' not in report['selections']


def test_animation_aliases_are_emitted_from_the_same_verified_action_plan():
    from test_fighter_archive import fixture as archive_fixture
    from fighter_animation_archive import AnimationArchive
    from fighter_archive import Archive
    _, _, plan = fixture()
    envelope = plan.bank.envelope
    split = envelope.model.sections[2][4]
    source = archive_fixture({'wres003.ord': envelope.model.data[:split],
                              'wres003.orl': envelope.model.data[split:],
                              'wres003.mnl': struct.pack('<2I', 2, 0) + b'A.B.'})
    compiler = AnimationArchive(source, hashlib.sha256(source).hexdigest())
    request = {'template_bank': 3, 'rig_sha256': 'a' * 64, 'bone_count': 4,
               'replacements': {}, 'moveset': {'plan': plan, 'selections': {2: 1}}}
    data, report = compiler.compose({'alpha/motion': request})
    assert Archive(data).read('wres1000.mnl') == struct.pack('<2I', 2, 0) + b'A.A.'
    assert report['bindings']['alpha/motion']['moveset']['motion_aliases'] == {1: 0}
    assert Archive(data).read('wres003.mnl') == struct.pack('<2I', 2, 0) + b'A.B.'
    request['moveset'] = {'plan': {}, 'selections': {2: 1}}
    with pytest.raises(AssetError, match='typed moveset'):
        compiler.compose({'alpha/motion': request})


def test_slot_edits_preserve_every_other_packed_bit_and_ordinary_action():
    from fighter_motion_compile import MotionCoreTemplates
    from fighter_moveset import compose_selected_cores
    data, _, plan = fixture()
    templates = MotionCoreTemplates(data, hashlib.sha256(data).hexdigest())
    resources = {'alpha/core': {'donor': 2, 'finisher_slots': {0: 81, 1: 2, 3: 2}}, 'beta/core': 2}
    compiled, report, proof = compose_selected_cores(templates, resources)
    assert proof[:8] == b'FMC3\x03\0\0\0' and len(proof) == 56 + 296 * 2
    assert struct.unpack_from('<4I', proof, 56 + 280) == (81, 2, 0xffffffff, 2)
    index = MotionIndex(compiled)
    before, after = templates.index.record('core', 2), index.record('core', 3)
    assert after.values[:88] == before.values[:88] and after.values[92:] == before.values[92:]
    assert after.values[88:92] == (81, 2, before.values[90], 2) and after.tail == before.tail
    assert compiled[:len(data)] == data
    assert index.data[index.core_spans[3] + 64:index.core_spans[3] + 852] == data[templates.index.core_spans[2] + 64:templates.index.core_spans[2] + 852]
    resources['alpha/core'].update(envelope=plan.bank.envelope,
        bank_sha256=hashlib.sha256(plan.bank.envelope.model.data).hexdigest(), selections={2: 1})
    compiled, _, proof = compose_selected_cores(templates, resources)
    assert struct.unpack_from('<H', proof, 56 + 24) == (1,)
    assert MotionIndex(compiled).record('core', 3).values[88] == 81


@pytest.mark.parametrize('edits', [{}, {True: 1}, {4: 1}, {0: True}, {0: 82}, {'0': 1}, {0: -1}])
def test_finisher_slot_choices_are_bounded(edits):
    from fighter_motion_compile import MotionCoreTemplates
    from fighter_moveset import compose_selected_cores
    data, _, _ = fixture()
    templates = MotionCoreTemplates(data, hashlib.sha256(data).hexdigest())
    with pytest.raises(AssetError):
        compose_selected_cores(templates, {'alpha/core': {'donor': 2, 'finisher_slots': edits}})
