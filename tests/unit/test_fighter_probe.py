"""Research activation is rebuilt from semantic inputs and stays isolated."""
import importlib.util
import hashlib
import json
from pathlib import Path

import pytest

from test_fighter_native import catalog, pack

ROOT = Path(__file__).resolve().parents[2]


def driver(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('fighter_probe', ROOT / 'scripts/fighter-runtime-probe.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, _, _ = catalog()
    monkeypatch.setattr(module.registry, 'retail_catalog', lambda _: source)
    monkeypatch.setattr(module.registry, 'ROOT', tmp_path)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    return module


def test_probe_uses_ordinary_adapter_and_immutable_cache(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    paths = [tmp_path / 'alpha.json', tmp_path / 'beta.json']
    for path, value in zip(paths, [pack(count=2), pack('beta', 'retail/test-beta')]):
        path.write_text(json.dumps(value))
    cache, report = probe.prepare(tmp_path / 'unused.sod', paths)
    assert cache.is_relative_to(tmp_path / 'logs')
    assert len(probe.custom_bindings(report)) == 3
    assert (cache / 'fighter-names.bin').is_file()
    assert not report['launch_allowed']
    assert probe.prepare(tmp_path / 'unused.sod', paths)[0] == cache
    (cache / 'assets/djv2.sod').write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='cache is corrupt'):
        probe.prepare(tmp_path / 'unused.sod', paths)


def test_probe_refuses_unadapted_width_and_empty_packs(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    path = tmp_path / 'alpha.json'
    with pytest.raises(ValueError, match='one or more'):
        probe.prepare(tmp_path / 'unused.sod', [])
    path.write_text(json.dumps(pack(count=300)))
    with pytest.raises(ValueError, match='signed selection-byte'):
        probe.prepare(tmp_path / 'unused.sod', [path])
    assert not (tmp_path / 'logs').exists()
    path.write_text(json.dumps(pack(count=0)))
    with pytest.raises(ValueError, match='at least one'):
        probe.prepare(tmp_path / 'unused.sod', [path])


def test_browsing_large_logical_roster_does_not_expand_native_tables(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    source, original, _ = catalog(menu=True)
    monkeypatch.setattr(probe.registry, 'retail_catalog', lambda _: source)
    path = tmp_path / 'alpha.json'; path.write_text(json.dumps(pack(count=300)))
    cache, report = probe.prepare(tmp_path / 'unused.sod', [path], logical_menu=True)
    assert (cache / 'assets/djv2.sod').read_bytes() == original
    assert report['binding_mode'] == 'logical-menu-only'
    assert report['native_character_count'] == 2 and len(report['menu_roster']) == 300
    assert sum(binding['available'] for binding in report['handle_bindings'].values()) == 2


def test_probe_refuses_to_stop_another_game(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    class Running:
        returncode = 0
        stdout = '"defjam_recomp.exe","123"'
    monkeypatch.setattr(probe.subprocess, 'run', lambda *args, **kwargs: Running())
    with pytest.raises(ValueError, match='Close the running game'):
        probe.require_idle_game()


def test_combat_control_uses_stable_keys_and_keeps_identity_domains_separate(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    report = {'bindings': {'retail/donor': {'selection_key': 7, 'core_id': 111},
                           'alpha/new': {'selection_key': 100, 'core_id': 7}}}
    assert probe.start_fighters(report, ['retail/donor', 'alpha/new']) == '7,100'
    for keys in ([], ['alpha/new'], ['alpha/new', 'alpha/new'], ['alpha/new', 'missing/new']):
        with pytest.raises(ValueError):
            probe.start_fighters(report, keys)


def test_menu_acceptance_requires_real_submissions_and_matching_match(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    report = {'bindings': {'alpha/new': {'selection_key': 101}, 'beta/new': {'selection_key': 102}}}
    path = tmp_path / 'native.log'
    submissions = ('[FUNCCALL] Controller.ControllerSetup(0,0,101,0)\n'
                   '[FUNCCALL] Controller.ControllerSetup(1,-1,102,1)\n')
    start = '[START] venue(script)=1 fighters(gd+1aaa step 5): 101 102 -99 -99\n'
    path.write_text(submissions + start)
    assert probe.verify_menu_selection(path, report, ['alpha/new', 'beta/new']) == [101, 102]
    for evidence in (submissions, start, submissions + start.replace('101 102', '16 102'),
                     submissions.replace('(1,-1,102,1)', '(1,-1,16,1)') + start, submissions + start * 2):
        path.write_text(evidence)
        with pytest.raises(ValueError, match='Native menu'):
            probe.verify_menu_selection(path, report, ['alpha/new', 'beta/new'])


def test_window_acceptance_requires_full_logical_identity_and_the_bound_core(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    report = {'binding_mode': 'participant-window',
              'bindings': {'alpha/new': {'selection_key': 256, 'core_id': 5}, 'retail/blaze': {'selection_key': 7}},
              'binding_ledger': {'fighters': {'alpha/new': {'handle': 0x0700004b}}}}
    evidence = ('[FUNCCALL] Controller.ControllerSetup(0,0,256,1)\n'
                '[FIGHTERS] participant=0 logical=256 stable=0700004B native=100 core=5 unlocks=76\n'
                '[FUNCCALL] Controller.ControllerSetup(1,-1,7,1)\n'
                '[START] venue(script)=1 fighters(gd+1aaa step 5): 100 7 -99 -99\n')
    path = tmp_path / 'window.log'; path.write_text(evidence)
    assert probe.verify_menu_selection(path, report, ['alpha/new', 'retail/blaze']) == [256, 7]
    for text in (evidence.replace('core=5', 'core=4'), evidence.replace('stable=0700004B', 'stable=0700004C'),
                 evidence.replace('logical=256', 'logical=255')):
        path.write_text(text)
        with pytest.raises(ValueError, match='participant bank'):
            probe.verify_menu_selection(path, report, ['alpha/new', 'retail/blaze'])


def test_portrait_cache_verifies_source_and_existing_output(tmp_path, monkeypatch):
    from test_fighter_archive import fixture
    from test_fighter_menu import selector_fixture
    from test_fighter_results import result_fixture
    probe = driver(tmp_path, monkeypatch)
    entries = {}
    for count in (2, 3, 4):
        stem = f'p_cf_8_{count}p'
        entries[f'screens/portrait/p_CF/{stem}.big'] = fixture({stem + suffix: suffix.encode() for suffix in ('.apt', '.const', '.o', '.xsh')})
        for prefix, start in [('screens/portrait/t_MS/', 't_MS_'), ('screens/portrait/', 'l_MS_')]:
            stem = f'{start}7_{count}p'
            entries[prefix + stem + '.big'] = fixture({stem + suffix: suffix.encode() for suffix in ('.apt', '.const', '.o', '.xsh')})
        movie, constants = selector_fixture()
        name = f'chooseF{count}'
        entries[f'screens/battle/{name}.big'] = fixture({name + '.apt': movie, name + '.const': constants})
        movie, constants = result_fixture()
        name = f'matchSm{count}'
        entries[f'screens/battle/{name}.big'] = fixture({name + '.apt': movie, name + '.const': constants})
    source = tmp_path / 'screens.viv'
    source.write_bytes(fixture(entries))
    pin = tmp_path / 'config/fighter-native-baseline.json'
    pin.parent.mkdir()
    pin.write_text(json.dumps({'screens_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}))
    report = {'bindings': {'retail/donor': {'selection_key': 7}, 'alpha/new': {'selection_key': 100, 'native_name': 'fm-new'}},
              'portrait_donors': {'alpha/new': 'retail/donor'}, 'localization_entries': {'fm-new': 'Example'}}
    output = probe.prepare_portraits(source, report)
    assert probe.prepare_portraits(source, report) == output
    output.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='cache is corrupt'):
        probe.prepare_portraits(source, report)
    source.write_bytes(b'unverified')
    with pytest.raises(ValueError, match='original screens'):
        probe.prepare_portraits(source, report)
