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


def fitted_result_fixture(participants):
    movie, constants = result_fixture()
    movie = bytearray(movie); movie += bytes(-len(movie) % 4)
    font = len(movie); movie += struct.pack('<II', 3, 0x09876543)
    text = len(movie); movie += struct.pack('<II4fIIIf5I', 2, 0x09876543, -2, -2, 112, 33,
                                          2, 0, 0xff000000, 20 if participants == 4 else 26, 1, 0, 0, 242, 242)
    placement = len(movie)
    movie += struct.pack('<4I6f6I', 3, 38, 31, 1, 1, 0, 0, 1, 46, -20, 0, 0, 0, 224, 0xffffffff, 0)
    pointers = len(movie); movie += struct.pack('<3I', 104, text, font)
    struct.pack_into('<II', movie, 36, 3, pointers)
    frame = len(movie); movie += struct.pack('<2I', 144, placement)
    struct.pack_into('<II', movie, 120, 2, frame)
    struct.pack_into('<I', movie, 140, placement)
    return bytes(movie), constants, text


@pytest.mark.parametrize('participants,height', [(2, 14), (3, 12), (4, 9)])
def test_long_result_names_have_independent_bounded_lines_and_clear_on_retail(participants, height):
    original, constants, native_text = fitted_result_fixture(participants)
    output, _, report = compile_results(original, constants, {256: 'W' * 19}, participants=participants)
    root = apt.parse_character(output, 16); chars = apt.read_characters_list(output, root)
    assert output[native_text:native_text + 60] == original[native_text:native_text + 60]
    assert report['label_frames'] == [0, 1] and len(chars) == 5
    assert [struct.unpack_from('<f', output, row['offset'] + 36)[0] for row in chars[-2:]] == [height, height]
    assert [apt.read_cstr(output, struct.unpack_from('<I', output, row['offset'] + 56)[0]) for row in chars[-2:]] == [
        '_recompResultText0', '_recompResultText1']
    _, entries = apt.parse_const(constants)
    code = apt.disassemble_block(output, report['label_action'], entries)
    first_branch = next(index for index, ins in enumerate(code) if ins.name == 'BranchIfTrue')
    assert sum(ins.name == 'SetMember' for ins in code[:first_branch]) == 2
    assert b'_recompResultID\0' in output and b'_xscale\0' not in output
    sprite = chars[0]
    overlays = [item for kind, item in sprite['frames'][0] if kind == 'PlaceObject' and
                (item.get('name') or '').startswith('_recompResultLine')]
    assert len(overlays) == 2 and len({row['depth'] for row in overlays}) == 2
    assert overlays[1]['matrix'][5] - overlays[0]['matrix'][5] == height + 2
    with pytest.raises(AssetError, match='line budget'):
        compile_results(original, constants, {256: 'W' * 40}, participants=participants)


@pytest.mark.parametrize('participants', [2, 3, 4])
def test_repeated_label_frames_survive_native_in_place_action_relocation(participants):
    original, constants, _ = fitted_result_fixture(participants)
    output, _, report = compile_results(original, constants, {256: 'Custom Fighter'}, participants=participants)
    movie = bytearray(output)
    root = apt.parse_character(output, 16)
    panel = apt.read_characters_list(output, root)[0]
    frames = struct.unpack_from('<I', output, panel['offset'] + 12)[0]
    _, entries = apt.parse_const(constants)
    base = 0x8004F280
    records, actions, literal_fields = [], [], []
    for frame in report['label_frames']:
        count, items = struct.unpack_from('<II', output, frames + frame * 8)
        record = struct.unpack_from('<I', output, items + (count - 1) * 4)[0]
        action = struct.unpack_from('<I', output, record + 4)[0]
        records.append(record); actions.append(action)
        # 17DD70@17DE55 adds base on EVERY frame occurrence, without a
        # visited-record guard. Duplicate records corrupt both frame pointers.
        previous = struct.unpack_from('<I', movie, record + 4)[0]
        struct.pack_into('<I', movie, record + 4, (previous + base) & 0xffffffff)
        for instruction in apt.disassemble_block(output, action, entries):
            if instruction.name == 'EA_PushString':
                field = apt.align4(instruction.offset + 1)
                literal_fields.append(field)
                pointer = struct.unpack_from('<I', movie, field)[0]
                struct.pack_into('<I', movie, field, (pointer + base) & 0xffffffff)
    assert len(records) == 2
    assert len(set(records)) == len(records)
    assert len(set(actions)) == len(actions)
    assert len(set(literal_fields)) == len(literal_fields)
    assert actions == report['label_actions']
    for record, action in zip(records, actions):
        assert struct.unpack_from('<I', movie, record + 4)[0] == base + action
    for field in literal_fields:
        pointer = struct.unpack_from('<I', movie, field)[0] - base
        assert 0 <= pointer < len(output)
        assert pointer == struct.unpack_from('<I', output, field)[0]
