"""Wrap native summary behavior without moving original bytecode or pointers."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
import fighter_apt as apt
from fighter_assets import AssetError
from fighter_menu import Action
from fighter_results import compile_results, scan_action


def result_fixture():
    movie = bytearray(b'Apt Data' + bytes(248))
    struct.pack_into('<10I', movie, 16, 9, 0x09876543, 1, 80, 0, 1, 96, 640, 480, 16)
    struct.pack_into('<I', movie, 96, 104)
    struct.pack_into('<4I', movie, 104, 5, 0x09876543, 2, 120)
    struct.pack_into('<6I', movie, 120, 1, 136, 1, 140, 144, 152)
    struct.pack_into('<II', movie, 144, 1, 256)
    struct.pack_into('<III', movie, 152, 3, 32, 1)
    struct.pack_into('<I', movie, 204, 224)
    movie[224:242] = b'szFighterNameMov\0'.ljust(18, b'\0')
    action = Action(256)
    action.string('Game.GetMatchSummary('); action.op('Pop')
    action.function('fillStats', ['playerId'], lambda: (action.local('iFighterID', lambda: action.integer(256)), action.op('EA_PushUndefined'), action.op('Return')))
    action.function('original', ['value'], lambda: (action.variable('value'), action.op('Return')))
    done = action.unique()
    action.integer(0); action.branch('BranchIfTrue', done)
    action.integer(12); action.op('Pop'); action.label(done)
    movie += action.finish()
    constants = b'Apt constant file' + bytes(3) + struct.pack('<III', 16, 0, 32)
    return bytes(movie), constants


def test_summary_keeps_original_code_and_adds_literal_label_after_native_field_creation():
    original, constants = result_fixture()
    label = "Name'); FuncCall('unsafe'); //"
    output, unchanged, report = compile_results(original, constants, {256: label})
    assert unchanged == constants and report['label_frames'] == [1]
    _, entries = apt.parse_const(constants)
    before, end = scan_action(original, 256, entries)
    assert output[256:len(original)] == original[256:]
    after, _ = scan_action(output, 256, entries)
    assert [(i.offset, i.name, i.operands, i.function_size, i.branch_target) for i in after] == \
           [(i.offset, i.name, i.operands, i.function_size, i.branch_target) for i in before]
    assert struct.unpack_from('<I', output, 148)[0] == 256
    record = apt.parse_character(output, 16)
    sprite = apt.read_characters_list(output, record)[0]
    assert len(sprite['frames'][1]) == 2 and sprite['frames'][1][0][0] == 'PlaceObject'
    assert sprite['frames'][1][-1][1]['instructions_at'] == report['label_action']
    assert label.encode() + b'\0' in output
    generated = apt.disassemble_block(output, report['label_action'], entries)
    assert all(not ins.note for ins in generated)
    wrapper = apt.disassemble_block(output, report['wrapper_action'], entries)
    assert any(ins.function_size is not None and "name='fillStats' params=(playerId)" in ' '.join(ins.operands) for ins in wrapper)
    assert b'nLastPlayerID\0' in output and b'_recompFillStats\0' in output


def test_summary_requires_a_unique_supported_native_panel_and_valid_labels():
    movie, constants = result_fixture()
    for names in ({}, {99: 'reserved'}, {256: 'bad\0label'}):
        with pytest.raises(AssetError):
            compile_results(movie, constants, names)
    with pytest.raises(AssetError, match='panel differs'):
        compile_results(movie.replace(b'Game.GetMatchSummary(', b'Game.GetWrongSummary('), constants, {256: 'A'})
