"""recomplauncher.json must stay in step with the settings the game really has.

RecompLauncher writes the keys this file names straight into settings.ini, so a key renamed in
src/hooks/pc_settings_catalog.c (or a value spelled differently) would silently stop working in the
launcher. These tests read the game's own settings table and the Modern/Original preset table, and
check every key, value, default and slider range in the manifest against them. docs/recomplauncher.md.
"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / 'recomplauncher.json'
SOURCES = [REPO / 'src/hooks/pc_settings_catalog.c', REPO / 'src/hooks/pc_ui_settings.c']
CATALOG = REPO / 'src/hooks/pc_settings_catalog.c'


def manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def enum_arrays(text):
    """static const char *const k_name[] = { "a", "b", NULL }; -> {k_name: ['a', 'b']}"""
    found = {}
    for name, body in re.findall(r'static const char \*const (k_\w+)\[\]\s*=\s*\{(.*?)\};', text, re.S):
        found[name] = re.findall(r'"([^"]*)"', body)
    return found


def registry():
    """(section, key) -> {type, default, low, high, names} for every row the game registers."""
    text = ''.join(p.read_text(encoding='utf-8') for p in SOURCES)
    arrays = enum_arrays(text)
    rows = {}
    pattern = re.compile(r'(?:\{|ADD\()\s*"(\w+)",\s*"(\w+)",\s*RECOMP_SETTING_(BOOL|INT|ENUM|STRING),\s*([-\w]+),\s*(-?\w+),\s*(-?\w+),\s*(k_\w+|NULL)')
    for section, key, kind, default, low, high, names in pattern.findall(text):
        rows[(section, key)] = {'type': kind, 'default': default, 'low': low, 'high': high,
                                'names': arrays.get(names, [])}
    return rows


def experience():
    """pc_settings_catalog.c k_experience: key -> (original, modern), as the numbers the game stores."""
    text = CATALOG.read_text(encoding='utf-8')
    body = re.search(r'k_experience\[\]\s*=\s*\{(.*?)\};', text, re.S).group(1)
    return {k: (int(o), int(m)) for k, o, m in re.findall(r'\{"(\w+)",\s*(\d+),\s*(\d+)\}', body)}


def as_text(row, number):
    """The number the game stores as the word settings.ini holds."""
    if row['type'] == 'BOOL':
        return 'true' if int(number) else 'false'
    if row['type'] == 'ENUM':
        return row['names'][int(number)]
    return str(int(number))


def keys_of(setting):
    keys = set()
    for choice in setting.get('choices', []):
        keys |= set(choice['set'])
    if 'slider' in setting:
        keys.add(setting['slider']['key'])
    return keys


def test_the_file_is_a_format_1_manifest_for_this_repo():
    m = manifest()
    assert m['format'] == 1
    assert m['repo'] == 'vyanhursky/DefJamFFNY-recomp'
    assert m['config'][0]['format'] == 'ini'


def test_the_registry_reader_finds_the_rows_the_manifest_uses():
    rows = registry()
    assert rows[('display', 'aspect')]['names'][2] == 'widescreen (auto)'
    assert rows[('display', 'render_scale')]['type'] == 'INT'
    assert ('debug', 'skip_intro') in rows and ('textures', 'enabled') in rows


def test_every_key_value_and_default_exists_in_the_game():
    rows, problems = registry(), []
    for setting in manifest()['settings']:
        for key in keys_of(setting):
            section, name = key.split('/')
            row = rows.get((section, name))
            if row is None:
                problems.append(f'{key} is not a setting the game registers')
                continue
            default = setting['defaults'].get(key)
            if default is None:
                problems.append(f'{key} has no default')
            elif default.lower() != as_text(row, row['default']).lower():
                problems.append(f'{key} default {default!r} is not the game\'s {as_text(row, row["default"])!r}')
            for choice in setting.get('choices', []):
                value = choice['set'].get(key)
                if value is None:
                    continue
                if row['type'] == 'BOOL' and value not in ('true', 'false'):
                    problems.append(f'{key}={value} is not a boolean')
                if row['type'] == 'ENUM' and value not in row['names']:
                    problems.append(f'{key}={value} is not one of {row["names"]}')
                if row['type'] == 'INT' and not int(row['low']) <= int(value) <= int(row['high']):
                    problems.append(f'{key}={value} is outside {row["low"]}-{row["high"]}')
            if 'slider' in setting and setting['slider']['key'] == key:
                s = setting['slider']
                if (s['min'], s['max']) != (int(row['low']), int(row['high'])):
                    problems.append(f'{key} slider {s["min"]}-{s["max"]} is not the game\'s {row["low"]}-{row["high"]}')
    assert problems == []


def test_modern_and_original_are_exactly_the_games_own_presets():
    rows = registry()
    by_label = {c['label']: c['set'] for s in manifest()['settings'] if s['id'] == 'experience' for c in s['choices']}
    modern, original = dict(by_label['Modern']), dict(by_label['Original'])
    # Original also turns HD texture packs off, as pc_experience_apply does; Modern leaves them alone.
    assert original.pop('textures/enabled') == 'false'
    assert 'textures/enabled' not in modern
    preset = experience()
    assert {k.split('/')[1] for k in modern} == set(preset) == {k.split('/')[1] for k in original}
    for key, (was, now) in preset.items():
        row = rows[('display', key)]
        assert original['display/' + key].lower() == as_text(row, was).lower(), key
        assert modern['display/' + key].lower() == as_text(row, now).lower(), key


def test_the_launcher_is_never_skipped_or_forced():
    text = MANIFEST.read_text(encoding='utf-8')
    for word in ('"skip"', 'launcher/skip', 'RECOMP_NO_LAUNCHER', 'check_updates'):
        assert word not in text


def test_the_dump_check_is_optional_so_this_is_not_easy_setup():
    m = manifest()
    game = [i for i in m['inputs'] if i['id'] == 'game'][0]
    assert game['optional'] is True and 'start' not in m and 'prepare' not in m
    assert game['check'] == {'xdvdfs': 'default.xbe', 'file': 'default.xbe'}
    # The Redump values are the ones docs/research/disc-layout.md records.
    notes = (REPO / 'docs/research/disc-layout.md').read_text(encoding='utf-8')
    for dump in game['dumps']:
        assert f"{dump['size']:,}" in notes and dump['crc32'] in notes
