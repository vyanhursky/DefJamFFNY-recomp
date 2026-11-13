"""Fighter Mod Support may only stop the game in fewer places over time (review 2026-11-12, E3).

Each line below calls (or defines) a function that ends the process through
defjam_fighter_fatal. The numbers are a ceiling: a change may lower one and
must then lower the ceiling here too, so the gain cannot be spent elsewhere.
A new stop needs a reason a fallback cannot work, written beside the raised
number. Classes, in order of preference (docs/fighter-mod-support.md):

1. start-up validation: refuse the packs and start the game without them;
2. in-match mismatch: give that fighter to the game's retail handling and log;
3. only a state that would write a corrupt save may stop.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
STOP = re.compile(r'\b(fighter_stop|stop|motion_stop|cin_stop|fin_stop|voice_stop|ui_stop|cpu_stop|hd_stop|defjam_fighter_fatal)\(')

# 2026-11-12: 224 lines before the save redesign (#243) and this change; 191 after.
CEILING = {
    'src/patches/fighter_ai.c': 1,
    'src/patches/fighter_caf.c': 17,
    'src/patches/fighter_caf_face.c': 12,
    'src/patches/fighter_caf_hd.c': 6,
    'src/patches/fighter_cinematic.c': 28,
    'src/patches/fighter_cpu_pool.c': 10,
    'src/patches/fighter_fatal.c': 1,
    'src/patches/fighter_film_async.c': 3,
    'src/patches/fighter_finishers.c': 25,
    'src/patches/fighter_motion.c': 19,
    'src/patches/fighter_runtime.c': 49,
    'src/patches/fighter_ui.c': 10,
    'src/patches/fighter_voice.c': 10,
}


def counts():
    result = {}
    for path in sorted([*ROOT.glob('src/patches/fighter_*.c'), *ROOT.glob('src/hooks/fighter_*.c')]):
        lines = sum(1 for line in path.read_text(encoding='utf-8').splitlines() if STOP.search(line))
        if lines:
            result[path.relative_to(ROOT).as_posix()] = lines
    return result


def test_fighter_stops_only_go_down():
    actual = counts()
    over = {name: (count, CEILING.get(name, 0)) for name, count in actual.items() if count > CEILING.get(name, 0)}
    assert not over, 'New fighter stops (count, ceiling): ' + repr(over)
    lowered = {name: (actual.get(name, 0), ceiling) for name, ceiling in CEILING.items() if actual.get(name, 0) < ceiling}
    assert not lowered, 'Stops were removed; lower these ceilings to match (count, ceiling): ' + repr(lowered)


def test_story_adapter_cannot_stop_on_save_contents():
    """The Story CAF adapter runs on every Story fight; nothing in a save may close the game there."""
    source = (ROOT / 'src/patches/fighter_caf.c').read_text(encoding='utf-8')
    start = source.index('void defjam_fighter_caf_story(')
    body = source[start:source.index('\n}\n', start)]
    assert not STOP.search(body)
    assert 'if(!defjam_fighter_runtime_active())return;' in body.replace(' ', '')


def test_unknown_saved_unlock_is_not_fatal():
    source = (ROOT / 'src/patches/fighter_runtime.c').read_text(encoding='utf-8')
    assert 'Saved fighter unlock has no historical identity binding' not in source
