"""Invented Team movie verifies owned wrappers and strict native entry points."""
import struct
import pytest
from fighter_menu import Action, functions
from fighter_team_menu import compile_team
from fighter_assets import AssetError


def fixture():
    constants = b'Apt constant file' + bytes(3) + struct.pack('<III', 16, 0, 32)
    movie = bytearray(b'Apt Data' + bytes(92))
    struct.pack_into('<10I', movie, 16, 9, 0x09876543, 1, 80, 0, 0, 0, 640, 480, 16)
    struct.pack_into('<5I', movie, 80, 1, 88, 92, 1, 100)
    action = Action(100)
    for name in ('InitializeThumbs', 'InitializePortraits'):
        action.function(name, ['characterList'], lambda: (action.op('EA_PushUndefined'), action.op('Return')))
    return bytes(movie) + action.finish(), constants


def row():
    return dict(selection_key=100, stats=dict.fromkeys('ULSTHC', 50), styles=[0],
                outfit_count=3, outfit_portraits=[100, 0x60000000, 0x60000001])


def test_team_wrapper_preserves_originals_and_semantic_ids():
    movie, constants = fixture()
    assert compile_team(movie, constants, None) == (movie, constants)
    output, copied = compile_team(movie, constants, [row()])
    assert copied == constants
    assert output[:80] == movie[:80] and output[88:len(movie)] == movie[88:]
    names = [d['name'] for d in functions(output, copied)[2]]
    assert names.count('InitializeThumbs') == names.count('InitializePortraits') == 2
    assert b'_recompTeamPortraits\0' in output and b'_display\0' in output
    assert b'Fighters.Outfit' not in output and b'ml_CharacterIndex' not in output
    invalid = row(); invalid['outfit_portraits'][1] = True
    with pytest.raises(AssetError, match='outfits'):
        compile_team(movie, constants, [invalid])
    with pytest.raises(AssetError):
        compile_team(movie[:100], constants, [row()])
