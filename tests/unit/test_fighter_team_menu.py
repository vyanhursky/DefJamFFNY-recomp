"""Invented Team movie verifies owned wrappers and strict native entry points."""
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "setup"))
import pytest
from fighter_menu import Action, functions
from fighter_team_menu import compile_team
from fighter_assets import AssetError


def fixture():
    constants = b'Apt constant file' + bytes(3) + struct.pack('<III', 16, 1, 32) + struct.pack('<II', 1, 40) + b'Initialize\0'
    movie = bytearray(b'Apt Data' + bytes(92))
    struct.pack_into('<10I', movie, 16, 9, 0x09876543, 1, 80, 0, 0, 0, 640, 480, 16)
    struct.pack_into('<5I', movie, 80, 1, 88, 92, 1, 100)
    action = Action(100)
    for name in ('InitializeThumbs', 'InitializePortraits'):
        action.function(name, ['characterList'], lambda: (action.op('EA_PushUndefined'), action.op('Return')))
    action.constant_pool([0]); action.integer(0); action.op('EA_PushThisVar'); action.op('EA_CallNamedMethodPop'); action.code.append(0)
    return bytes(movie) + action.finish(), constants


def row():
    return dict(selection_key=100, stats=dict.fromkeys('ULSTHC', 50), styles=[0],
                outfit_count=3, outfit_portraits=[100, 0x60000000, 0x60000001])


def test_team_wrapper_preserves_originals_and_semantic_ids():
    movie, constants = fixture()
    assert compile_team(movie, constants, None) == (movie, constants)
    output, copied = compile_team(movie, constants, [row()])
    assert copied == constants
    assert output[:80] == movie[:80]
    changed = [i for i in range(88, len(movie)) if output[i] != movie[i]]
    assert len(changed) == 2 and changed[1] == changed[0] + 1
    assert output[changed[0]:changed[1]+1] == b'\x17\x17'
    names = [d['name'] for d in functions(output, copied)[2]]
    assert names.count('InitializeThumbs') == names.count('InitializePortraits') == 2
    assert b'_recompTeamPortraits\0' in output and b'_display\0' in output
    assert b'Fighters.Outfit' not in output and b'ml_CharacterIndex' not in output
    invalid = row(); invalid['outfit_portraits'][1] = True
    with pytest.raises(AssetError, match='outfits'):
        compile_team(movie, constants, [invalid])
    with pytest.raises(AssetError):
        compile_team(movie.replace(b'InitializeThumbs\0', b'XnitializeThumbs\0'), constants, [row()])
