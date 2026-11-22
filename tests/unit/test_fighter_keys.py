"""The fighter key range can be moved by a fork (FFNY Online request 1), and defaults are unchanged.

fighter_keys.py and src/hooks/fighter_keys.h hold the first bank key and the first logical key of a
custom fighter. These tests check that the two files agree, that the compiler and the native window
decoder both work with another pair, and that a window compiled with one pair is refused by a decoder
built with another. Only the defaults are tested in the game.
"""
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'setup'))

import fighter_keys
from test_fighter_window import build_probe

ALTERNATE = (124, 1000)


def header_value(name):
    text = (ROOT / 'src/hooks/fighter_keys.h').read_text(encoding='utf-8')
    found = re.findall(r'#define ' + name + r' (\d+)u', text)
    assert len(found) == 1, name
    return int(found[0])


def test_python_and_native_definitions_agree_and_keep_todays_values():
    assert (fighter_keys.RETAIL_LIMIT, fighter_keys.BANK_FIRST, fighter_keys.LOGICAL_FIRST) == (100, 100, 100)
    assert header_value('DEFJAM_FIGHTER_RETAIL_LIMIT') == fighter_keys.RETAIL_LIMIT
    assert header_value('DEFJAM_FIGHTER_BANK_FIRST') == fighter_keys.BANK_FIRST
    assert header_value('DEFJAM_FIGHTER_LOGICAL_FIRST') == fighter_keys.LOGICAL_FIRST
    assert fighter_keys.manifest_value() == '100,100'


def test_no_fighter_module_spells_the_key_starts_as_a_literal():
    """Every 'is it ours' test uses the constants, so moving them moves every check."""
    pattern = re.compile(r'(>=|<|<=|>) ?100\b|\b100 ?(<=|<)|\b100u\b|max\(100\b')
    allowed = {'setup/fighter_keys.py', 'src/hooks/fighter_keys.h'}
    found = []
    for path in [*ROOT.glob('setup/fighter_*.py'), *ROOT.glob('src/hooks/fighter_*.[ch]'),
                 *ROOT.glob('src/patches/fighter_*.[ch]')]:
        name = path.relative_to(ROOT).as_posix()
        if name in allowed:
            continue
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            code = line.split('#')[0] if name.endswith('.py') else line.split('//')[0]
            # Percentages and stat ranges (0..100) are not selection keys.
            if pattern.search(code) and not re.search(r'0 <= \w+ <= 100\b|<= ?100\b(?!\d)', code):
                found.append(f'{name}:{number}: {line.strip()}')
    assert not found, 'Use fighter_keys / fighter_keys.h:\n' + '\n'.join(found)


COMPILE = r'''
import sys
import fighter_keys
fighter_keys.BANK_FIRST, fighter_keys.LOGICAL_FIRST = int(sys.argv[1]), int(sys.argv[2])
from test_fighter_native import catalog, pack
from fighter_window import encode_window
source, _, _ = catalog(menu=True)
_, report = source.compile([pack(count=300)], binding_window=True)
if len(sys.argv) > 4:
    parent, child = report['window']['fighters'][:2]
    child['reserved'] = parent['selection_key'] + 1
    child['core_id'] = parent['core_id']
open(sys.argv[3], 'wb').write(encode_window(report['window']))
ledger = report['binding_ledger']['fighters']
custom = sorted(entry['selection'] for key, entry in ledger.items() if not key.startswith('retail/'))
banks = [row['selection_key'] for row in report['window']['banks']]
print(custom[0], custom[-1], len(custom), *banks)
'''


def compile_window(tmp_path, bank, logical, outfit=False):
    """Compile the fixture roster with a key pair in a fresh process (modules read the pair at import)."""
    path = tmp_path / f'window-{bank}-{logical}-{outfit}.bin'
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(ROOT / 'setup'), str(ROOT / 'tests/unit')])}
    result = subprocess.run([sys.executable, '-c', COMPILE, str(bank), str(logical), str(path),
                             *(['outfit'] if outfit else [])],
                            capture_output=True, text=True, timeout=120, env=env, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    return path, [int(value) for value in result.stdout.split()]


def test_compiler_numbers_custom_fighters_and_banks_from_the_moved_starts(tmp_path):
    _, default = compile_window(tmp_path, 100, 100)
    assert default == [100, 399, 300, 100, 101, 102, 103]
    _, moved = compile_window(tmp_path, *ALTERNATE)
    assert moved == [1000, 1299, 300, 124, 125, 126, 127]


@pytest.fixture(scope='module')
def probes(tmp_path_factory):
    default = build_probe(tmp_path_factory.mktemp('keys-default'))
    moved = build_probe(tmp_path_factory.mktemp('keys-moved'),
                        (f'DEFJAM_FIGHTER_BANK_FIRST={ALTERNATE[0]}u', f'DEFJAM_FIGHTER_LOGICAL_FIRST={ALTERNATE[1]}u'))
    return default, moved


@pytest.mark.parametrize('outfit', [False, True])
def test_native_window_works_with_a_moved_range_and_refuses_the_other(probes, tmp_path, outfit):
    default_probe, moved_probe = probes
    default_window, _ = compile_window(tmp_path, 100, 100, outfit=outfit)
    moved_window, _ = compile_window(tmp_path, *ALTERNATE, outfit=outfit)
    assert default_window.read_bytes()[:4] == moved_window.read_bytes()[:4] == (b'FWR3' if outfit else b'FWR1')

    def run(probe, window):
        return subprocess.run([str(probe), str(window), 'bind'], capture_output=True, text=True, timeout=10).returncode

    assert run(default_probe, default_window) == 0
    assert run(moved_probe, moved_window) == 0
    # A window compiled for another range is refused at decode (exit 1), never half-used.
    assert run(moved_probe, default_window) == 1
    assert run(default_probe, moved_window) == 1


def test_a_bank_start_outside_the_supported_range_is_a_build_error(tmp_path):
    probe_dir = tmp_path / 'bad'
    probe_dir.mkdir()
    with pytest.raises(AssertionError, match='DEFJAM_FIGHTER_BANK_FIRST must be'):
        build_probe(probe_dir, ('DEFJAM_FIGHTER_BANK_FIRST=125u',))


def test_moved_logical_keys_keep_standalone_outfit_parents_and_order(monkeypatch):
    import fighter_menu
    monkeypatch.setattr(fighter_menu, 'LOGICAL_FIRST', ALTERNATE[1])
    record = dict(selection_key=1000, stats=dict.fromkeys('ULSTHC', 50), styles=[0],
                  outfit_parent=1001, outfit_order=1)
    assert 'FE_ID=1000' in fighter_menu.character_parameters(record)
    assert fighter_menu.character_parameters({**record, 'outfit_parent': 98})
    for changes in ({'outfit_parent': 100}, {'outfit_parent': 99}, {'outfit_order': 2},
                    {'selection_key': 100}):
        with pytest.raises(ValueError):
            fighter_menu.character_parameters({**record, **changes})
