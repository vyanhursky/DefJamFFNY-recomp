"""Synthetic native selector templates and generated presentation structure."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
import fighter_apt as apt
from fighter_menu import Action, AssetError, compile_menu, functions


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
        action.function('', [], visual); action.op('SetMember')
    action.function('updateChar', ['nPlayer'], lambda: (action.op('EA_PushUndefined'), action.op('Return')))
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
    assert [(entry.type, entry.value) for entry in values[:-1]] == [(entry.type, entry.value) for entry in old_constants]
    assert values[-1].value == 'getThumbID'
    assert report['methods'] == ['redraw', 'deselectChar', 'selectChar']
    # Both old and new definitions remain; the visual replacements include an
    # isolated pool prefix, then every original body byte at equal alignment.
    replacements = [definition for definition in definitions if definition['owner'] == 'CThumbGrid'][3:]
    assert len(replacements) == 3
    for before, after in zip(old_definitions[:3], replacements):
        original_body = source[before['start']:before['start'] + before['size']]
        changed_body = output[after['start'] + 12:after['start'] + after['size']]
        assert sum(left != right for left, right in zip(original_body, changed_body)) == (before['method'] == 'selectChar')
        assert after['pool'] == () or after['start'] % 4 == before['start'] % 4
    assert not any(definition['owner'] == 'CCharacter' and definition['method'] == 'getID' for definition in definitions)
    generated = apt.disassemble_block(output, report['action_offset'], values)
    assert all(not instruction.note for instruction in generated)
    assert any(instruction.name == 'DefineFunction' and "name='updateChar'" in ' '.join(instruction.operands) for instruction in generated)
    assert all(instruction.branch_target is None or report['action_offset'] <= instruction.branch_target < len(output) for instruction in generated)
    # The created-player comparison still invokes the identity getter; only
    # calls feeding thumbnail frame arithmetic use the presentation getter.
    selected = next(definition for definition in replacements if definition['method'] == 'selectChar')
    body = apt.disassemble_block(output, selected['start'], values, selected['size'])
    getters = [operand for instruction in body if instruction.name in ('EA_PushConstantByte', 'EA_PushConstantWord')
               for operand in instruction.operands if "='getID'" in operand or "='getThumbID'" in operand]
    assert len(getters) == 2 and "='getID'" in getters[0] and "='getThumbID'" in getters[1]


def test_labels_are_literal_data_and_invalid_bindings_fail_closed():
    movie, constants = selector_fixture()
    label = "Name'); Controller.ControllerSetup(0,0,7,0); //"
    output, changed, report = compile_menu(movie, constants, {100: 7}, {100: label})
    assert label.encode() + b'\0' in output
    assert functions(output, changed)[0] == 16
    for pairs, names in (({}, {}), ({100: 7}, {}), ({100: 7}, {100: 'bad\0name'})):
        with pytest.raises(AssetError): compile_menu(movie, constants, pairs, names)
    with pytest.raises(AssetError): compile_menu(b'not a movie', constants, {100: 7}, {100: 'A'})
