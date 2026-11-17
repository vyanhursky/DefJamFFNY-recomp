"""The compiler reads its base game files and their pins in one place (FFNY Online request 2).

fighter_base.path() and fighter_base.pins() are the only way the launcher's compile path reaches a
game file or a baseline pin, so a fork that patches one of the five base files changes one module.
This build returns the dump's files and the retail pins.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'setup'))

import fighter_base

# The modules the launcher runs when it compiles enabled packs (mods.py fighter-enable / fighter-prepare).
LAUNCHER_PATH = ('fighter_packages', 'fighter_build', 'fighter_behavior', 'fighter_presentation',
                 'fighter_cache', 'fighter_manifest')
BYPASS = re.compile(r"fighter-native-baseline\.json"                 # loading the pins directly
                    r"|game\s*/\s*['\"](assets|screens)/"             # game / 'assets/...'
                    r"|\.parents?(\[\d\])?\s*/\s*['\"]?(name|['\"](assets|screens))"  # sod.parent / name
                    r"|\bgame\s*\)?\s*/\s*(name|relative)\b"            # game / name, (game / relative)
                    r"|\bsod\.parents?\b")                               # the game folder taken from djv2.sod
# Tools that pass a dump's assets/djv2.sod alone get its game folder; the launcher passes game.
ALLOWED = {'fighter_build.py: game = Path(game) if game is not None else sod.parents[1]'}


def test_the_five_base_files_and_their_pins():
    assert set(fighter_base.FILES) == {'assets/djv2.sod', 'screens/screens.viv', 'assets/entity.xml',
                                       'assets/nis.viv', 'assets/v2ip.viv'}
    pins = fighter_base.pins()
    assert all(re.fullmatch('[0-9a-f]{64}', pins[name]) for name in fighter_base.FILES.values())


def test_this_build_reads_the_dump_and_the_retail_pins(tmp_path):
    for relative in (*fighter_base.FILES, 'motion/camera.xml'):
        assert fighter_base.path(tmp_path, relative) == tmp_path / relative
    pin = tmp_path / 'pins.json'
    pin.write_text('{"sha256": "x"}')
    assert fighter_base.pins(pin) == {'sha256': 'x'}


def test_launcher_compile_path_reads_game_files_and_pins_only_through_the_resolver():
    found = []
    for module in LAUNCHER_PATH:
        path = ROOT / 'setup' / (module + '.py')
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            if BYPASS.search(line.split('#')[0]) and f'{module}.py: {line.strip()}' not in ALLOWED:
                found.append(f'{module}.py:{number}: {line.strip()}')
    assert not found, 'Read base files through fighter_base.path() and pins through fighter_base.pins():\n' + \
        '\n'.join(found)
