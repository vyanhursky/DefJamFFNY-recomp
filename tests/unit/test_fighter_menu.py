"""Synthetic native selector templates and generated presentation structure."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
import fighter_apt as apt
from fighter_menu import Action, AssetError, character_parameters, compile_menu, functions


def selector_fixture():
    values = ['getID', 'CThumbGrid', 'prototype', 'redraw', 'deselectChar', 'selectChar', 'CHAR_HERO']
    constants = bytearray(b'Apt constant file' + bytes(3) + struct.pack('<III', 16, len(values), 32))
    pool_end = 32 + len(values) * 8
    text = bytearray()
    for value in values:
        constants += struct.pack('<II', 1, pool_end + len(text)); text += value.encode() + b'\0'
    constants += text
    action = Action(100)
    action.constant_pool(range(len(values)))
    for index in (3, 4, 5):
        action.op('EA_PushValueOfVar'); action.code.append(1)
        action.op('EA_PushConstantByte'); action.code.append(2)
        action.op('GetMember')
        action.op('EA_PushConstantByte'); action.code.append(index)
        def visual(index=index):
            if index == 5:
                action.integer(0); action.op('EA_PushThisVar')
                action.op('EA_PushConstantByte'); action.code.append(0)
                action.op('CallMethod'); action.op('EA_PushConstantByte'); action.code.append(6)
                action.op('Equals2'); action.op('Pop')
            action.integer(0); action.op('EA_PushThisVar')
            action.op('EA_PushConstantByte'); action.code.append(0)
            action.op('CallMethod'); action.op('Pop')
            skip = action.unique()
            action.integer(0); action.branch('BranchIfTrue', skip)
            action.integer(1); action.op('Pop')
            action.label(skip); action.op('EA_PushUndefined'); action.op('Return')
        action.function('', [], visual); action.op('SetMember')
    action.function('updateChar', ['nPlayer'], lambda: (action.op('EA_PushUndefined'), action.op('Return')))
    action.function('getCharData', [], lambda: (action.op('EA_PushUndefined'), action.op('Return')))
    action.function('keyBackHandler', ['nConID'], lambda: (action.op('EA_PushUndefined'), action.op('Return')))
    movie = bytearray(b'Apt Data' + bytes(92))
    struct.pack_into('<10I', movie, 16, 9, 0x09876543, 1, 80, 0, 0, 0, 640, 480, 16)
    struct.pack_into('<5I', movie, 80, 1, 88, 92, 1, 100)
    movie += action.finish()
    return bytes(movie), bytes(constants)


def test_generated_adapter_preserves_original_instructions_and_identity_getter():
    source, constants = selector_fixture()
    output, changed_constants, report = compile_menu(source, constants, {100: 7, 101: 8}, {100: 'Alpha', 101: 'Beta'})
    assert output[:80] == source[:80] and output[88:len(source)] == source[88:]
    old_entry, old_constants, old_definitions = functions(source, constants)
    entry, values, definitions = functions(output, changed_constants)
    assert old_entry == entry
    assert changed_constants == constants
    assert report['methods'] == ['redraw', 'deselectChar', 'selectChar']
    # Both old and new definitions remain. Original pool values are unchanged;
    # rewritten literal calls retain the instruction sequence and branch graph.
    replacements = [definition for definition in definitions if definition['owner'] == 'CThumbGrid'][3:]
    assert len(replacements) == 3
    for before, after in zip(old_definitions[:3], replacements):
        original_body = apt.disassemble_block(source, before['start'], old_constants, before['size'], before['pool'])
        changed_body = apt.disassemble_block(output, after['start'], values, after['size'], after['pool'])
        assert after['pool'] == before['pool']
        assert all(instruction.name != 'ConstantPool' for instruction in changed_body)
        assert len(changed_body) == len(original_body)
        old_positions = {ins.offset: i for i, ins in enumerate(original_body)}
        new_positions = {ins.offset: i for i, ins in enumerate(changed_body)}
        for left, right in zip(original_body, changed_body):
            assert left.name == right.name or (left.name == 'EA_PushConstantByte' and right.name == 'EA_PushString')
            if left.branch_target is not None:
                assert old_positions[left.branch_target] == new_positions[right.branch_target]
    assert not any(definition['owner'] == 'CCharacter' and definition['method'] == 'getID' for definition in definitions)
    generated = apt.disassemble_block(output, report['action_offset'], values)
    assert all(not instruction.note for instruction in generated)
    assert any(instruction.name == 'DefineFunction' and "name='updateChar'" in ' '.join(instruction.operands) for instruction in generated)
    assert all(instruction.branch_target is None or report['action_offset'] <= instruction.branch_target < len(output) for instruction in generated)
    # The created-player comparison still invokes the identity getter; only
    # calls feeding thumbnail frame arithmetic use the presentation getter.
    selected = next(definition for definition in replacements if definition['method'] == 'selectChar')
    body = apt.disassemble_block(output, selected['start'], values, selected['size'], list(selected['pool']))
    getters = [operand for instruction in body if instruction.name in ('EA_PushConstantByte', 'EA_PushConstantWord', 'EA_PushString')
               for operand in instruction.operands if "='getID'" in operand or "='getThumbID'" in operand]
    assert len(getters) == 2 and "='getID'" in getters[0] and "='getThumbID'" in getters[1]


@pytest.mark.parametrize('value,opcode', [(127, 'EA_PushByte'), (128, 'EA_PushLong'), (255, 'EA_PushLong'),
                                       (256, 'EA_PushLong'), (257, 'EA_PushLong')])
def test_generated_positive_integer_boundaries(value, opcode):
    action = Action(0); action.integer(value)
    instructions = apt.disassemble_block(action.finish(), 0, [])
    assert instructions[0].name == opcode and instructions[0].operands == [f'value={value}']


def test_labels_are_literal_data_and_invalid_bindings_fail_closed():
    movie, constants = selector_fixture()
    label = "Name'); Controller.ControllerSetup(0,0,7,0); //"
    output, changed, report = compile_menu(movie, constants, {100: 7}, {100: label})
    assert label.encode() + b'\0' in output
    assert functions(output, changed)[0] == 16
    for pairs, names in (({}, {}), ({100: 7}, {}), ({100: 7}, {100: 'bad\0name'})):
        with pytest.raises(AssetError): compile_menu(movie, constants, pairs, names)
    with pytest.raises(AssetError): compile_menu(b'not a movie', constants, {100: 7}, {100: 'A'})


def test_logical_entries_above_255_use_original_constructor_and_shared_list():
    movie, constants = selector_fixture()
    records = [dict(selection_key=identity, stats=dict(U=20, L=21, S=22, T=23, H=24, C=25), styles=[4, 1])
               for identity in (254, 255, 256, 257)]
    output, changed, report = compile_menu(movie, constants, dict.fromkeys((254, 255, 256, 257), 7),
                                            dict.fromkeys((254, 255, 256, 257), 'Visible name'), records)
    assert character_parameters(records[-1]) == 'CLOTH=1&FE_ID=257&LOCK=1&U=20&L=21&S=22&T=23&H=24&C=25&K=4&K=1'
    assert character_parameters(records[-1]).encode() + b'\0' in output
    _, values, definitions = functions(output, changed)
    assert len([d for d in definitions if d['name'] == '_recompAppendFighters']) == 1
    assert len([d for d in definitions if d['name'] == 'getCharData']) == 2
    assert len([d for d in definitions if d['name'] == 'keyBackHandler']) == 2
    assert b'Fighters.KeepReady(\0' in output and b'iTakenBy\0' in output
    assert not any(d['owner'] == 'CCharacter' and d['method'] == 'getID' for d in definitions)
    instructions = apt.disassemble_block(output, report['action_offset'], values)
    assert all(not instruction.note for instruction in instructions)
    assert all(instruction.branch_target is None or report['action_offset'] <= instruction.branch_target < len(output) for instruction in instructions)
    for bad in (dict(records[0], selection_key=[]), dict(records[0], stats={'H': 1}), dict(records[0], styles=[1, 1]),
                dict(records[0], styles=[True]), dict(records[0], extra='unrecognized')):
        with pytest.raises(AssetError): character_parameters(bad)


def test_logical_roster_refuses_an_unreviewed_back_handler():
    movie, constants = selector_fixture()
    movie = movie.replace(b'keyBackHandler\0', b'keyBackChanged\0')
    records = [dict(selection_key=100, stats=dict.fromkeys('ULSTHC', 50), styles=[1])]
    with pytest.raises(AssetError, match='Back handler differs'):
        compile_menu(movie, constants, {100: 7}, {100: 'Custom'}, records)
