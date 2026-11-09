"""Research activation is rebuilt from semantic inputs and stays isolated."""
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
import sys

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


def test_live_pad_file_is_scoped_and_checked_before_profile_work(tmp_path,monkeypatch):
    probe=driver(tmp_path,monkeypatch);root=tmp_path/'logs';root.mkdir();path=root/'pad.txt';path.write_text('a:300\n')
    assert probe.live_pad_path(path)==path
    outside=tmp_path/'outside.txt';outside.write_text('a:300\n')
    for invalid in (outside,root,root/'missing'):
        with pytest.raises(ValueError,match='Live pad input'):probe.live_pad_path(invalid)
    path.write_bytes(b'x'*(1024**2+1))
    with pytest.raises(ValueError,match='Live pad input'):probe.live_pad_path(path)


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


def test_profile_probe_accepts_last_pack_removal_with_dormant_history(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    source, original, _ = catalog(menu=True)
    monkeypatch.setattr(probe.registry, 'retail_catalog', lambda _: source)
    path = tmp_path / 'alpha.json'; path.write_text(json.dumps(pack(count=2)))
    _, active = probe.prepare(tmp_path / 'unused.sod', [path], binding_window=True)
    ledger = tmp_path / 'ledger.json'; ledger.write_text(json.dumps(active['binding_ledger']))
    cache, removed = probe.prepare(tmp_path / 'unused.sod', [], ledger, binding_window=True)
    assert removed['binding_mode'] == 'retail-only' and removed['added_count'] == 0
    assert removed['binding_ledger'] == active['binding_ledger']
    assert all(not row['available'] for key, row in removed['handle_bindings'].items() if key.startswith('alpha/'))
    assert (cache / 'assets/djv2.sod').read_bytes() == original
    assert not (cache / 'fighter-window.bin').exists()


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


def test_combat_acceptance_requires_each_match_and_explicit_results(tmp_path, monkeypatch):
    from test_scenario_evidence import played_fight, fight_log
    probe = driver(tmp_path, monkeypatch)
    path = tmp_path / 'combat.log'
    path.write_text(fight_log(played_fight()))
    matches = [['alpha/first', 'beta/first']]
    assert len(probe.verify_combat(path, matches, require_result=True)) == 7
    with pytest.raises(ValueError, match='2:combat.setup'):
        probe.verify_combat(path, matches * 2, require_result=True)
    path.write_text(fight_log(played_fight()[:5], summary=False))
    assert len(probe.verify_combat(path, matches)) == 5
    with pytest.raises(ValueError, match='combat.result'):
        probe.verify_combat(path, matches, require_result=True)
    path.write_text('unrelated diagnostic line\n')
    with pytest.raises(ValueError, match='combat.telemetry'):
        probe.verify_combat(path, matches)


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


@pytest.mark.parametrize('boundary', ['Game.Quit', 'match teardown'])
def test_repeated_matches_require_fresh_submissions_release_and_actual_cores(tmp_path, monkeypatch, boundary):
    probe = driver(tmp_path, monkeypatch)
    report = {'binding_mode': 'participant-window',
              'bindings': {'alpha/one': {'selection_key': 100, 'core_id': 4},
                           'alpha/two': {'selection_key': 101, 'core_id': 5},
                           'beta/one': {'selection_key': 102, 'core_id': 23}},
              'binding_ledger': {'fighters': {key: {'handle': 0x0700004b + index} for index, key in enumerate(
                  ('alpha/one', 'alpha/two', 'beta/one'))}}}
    def epoch(ids):
        text = '[FUNCCALL] Controller.ControllerSetup( -1, 0, 99, 0 )\n'
        for slot, key in enumerate(ids):
            binding = report['bindings'][key]; stable = report['binding_ledger']['fighters'][key]['handle']
            text += f'[FUNCCALL] Controller.ControllerSetup({slot},0,{binding["selection_key"]},{slot})\n'
            text += f'[FIGHTERS] participant={slot} logical={binding["selection_key"]} stable={stable:08X} native={100 + slot} core={binding["core_id"]}\n'
        text += '[START] venue(script)=1 fighters(gd+1aaa step 5): 100 101 -99 -99\n'
        for slot, key in enumerate(ids):
            binding = report['bindings'][key]; stable = report['binding_ledger']['fighters'][key]['handle']
            text += f'[FIGHTERS] materialized participant={slot} stable={stable:08X} logical={binding["selection_key"]} core={binding["core_id"]} immutable=1\n'
        return text
    matches = [['alpha/two', 'beta/one'], ['alpha/one', 'alpha/two']]
    first, second = map(epoch, matches)
    release = f'[FIGHTERS] selection ownership finished after native {boundary}; immutable records retained\n'
    path = tmp_path / 'repeated.log'; path.write_text(first + release + second)
    assert probe.verify_menu_matches(path, report, matches, immutable=True) == [[101, 102], [100, 101]]
    for invalid in (first + second + release, first + release + second.replace('logical=100 core=4 immutable=1', 'logical=100 core=5 immutable=1'),
                    first + release + second.replace('[FUNCCALL] Controller.ControllerSetup(1,0,101,1)\n', ''),
                    first + release + second.replace('stable=0700004B native=100 core=4', 'stable=0700004C native=100 core=4'),
                    first + release + first):
        path.write_text(invalid)
        with pytest.raises(ValueError):
            probe.verify_menu_matches(path, report, matches, immutable=True)


def test_created_fighter_assertion_preserves_the_native_profile_owned_sentinel(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    report = {'binding_mode': 'participant-window',
              'bindings': {'alpha/new': {'selection_key': 256, 'core_id': 5}},
              'binding_ledger': {'fighters': {'alpha/new': {'handle': 0x0700004b}}}}
    evidence = ('[FUNCCALL] Controller.ControllerSetup(0,0,99,0)\n'
                '[FUNCCALL] Controller.ControllerSetup(1,-1,256,1)\n'
                '[FIGHTERS] participant=1 logical=256 stable=0700004B native=101 core=5\n'
                '[START] venue(script)=1 fighters(gd+1aaa step 5): 99 101 -99 -99\n')
    path = tmp_path / 'created.log'; path.write_text(evidence)
    assert probe.verify_menu_selection(path, report, ['@created', 'alpha/new']) == [99, 256]
    with pytest.raises(ValueError, match='fighter is missing'):
        probe.start_fighters(report, ['@created', 'alpha/new'])
    path.write_text(evidence.replace('99', '98'))
    with pytest.raises(ValueError, match='Native menu'):
        probe.verify_menu_selection(path, report, ['@created', 'alpha/new'])


def portrait_inputs(tmp_path):
    from test_fighter_archive import fixture
    from test_fighter_menu import selector_fixture
    from test_fighter_results import fitted_result_fixture
    entries = {'screens/language-marker.txt': b'original language bytes'}
    entries['screens/trans/empty2.big'] = fixture({'empty2.apt': b'blank movie', 'empty2.const': b'blank constants'})
    for count in (2, 3, 4):
        stem = f'p_cf_8_{count}p'
        entries[f'screens/portrait/p_CF/{stem}.big'] = fixture({stem + suffix: suffix.encode() for suffix in ('.apt', '.const', '.o', '.xsh')})
        for prefix, start in [('screens/portrait/t_MS/', 't_MS_'), ('screens/portrait/', 'l_MS_')]:
            stem = f'{start}7_{count}p'
            entries[prefix + stem + '.big'] = fixture({stem + suffix: suffix.encode() for suffix in ('.apt', '.const', '.o', '.xsh')})
        movie, constants = selector_fixture(participants=count)
        name = f'chooseF{count}'
        entries[f'screens/battle/{name}.big'] = fixture({name + '.apt': movie, name + '.const': constants})
        movie, constants, _ = fitted_result_fixture(count)
        name = f'matchSm{count}'
        entries[f'screens/battle/{name}.big'] = fixture({name + '.apt': movie, name + '.const': constants})
    source = tmp_path / 'screens.viv'
    source.write_bytes(fixture(entries))
    pin = tmp_path / 'config/fighter-native-baseline.json'
    pin.parent.mkdir()
    pin.write_text(json.dumps({'screens_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}))
    report = {'bindings': {'retail/donor': {'selection_key': 7}, 'alpha/new': {'selection_key': 100, 'native_name': 'fm-new'}},
              'portrait_donors': {'alpha/new': 'retail/donor'}, 'localization_entries': {'fm-new': 'Example'}}
    return source, report


def test_portrait_cache_verifies_source_and_existing_output(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    source, report = portrait_inputs(tmp_path)
    output = probe.prepare_portraits(source, report)
    assert probe.prepare_portraits(source, report) == output
    from fighter_composition import language_base
    from fighter_archive import Archive
    from test_langpack import lp
    language = language_base(source.read_bytes(), [(('screens/language-marker.txt',),
                              lp.delta_make(b'original language bytes', b'translated language bytes'))],
                              hashlib.sha256(source.read_bytes()).hexdigest())
    composed = probe.prepare_portraits(source, report, language=language)
    assert composed != output
    assert Archive(composed.read_bytes()).read('screens/language-marker.txt') == b'translated language bytes'
    assert Archive(source.read_bytes()).read('screens/language-marker.txt') == b'original language bytes'
    with pytest.raises(ValueError, match='provenance'):
        probe.prepare_portraits(source, report, language=(source.read_bytes(), language[1]))
    output.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='cache is corrupt'):
        probe.prepare_portraits(source, report)
    source.write_bytes(b'unverified')
    with pytest.raises(ValueError, match='original screens'):
        probe.prepare_portraits(source, report)


def test_last_pack_removal_restores_original_native_menus(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    source, _ = portrait_inputs(tmp_path)
    report = {'binding_mode': 'retail-only', 'bindings': {}, 'portrait_donors': {}, 'localization_entries': {}}
    output = probe.prepare_portraits(source, report)
    assert output.read_bytes() == source.read_bytes()


def directory_link(target, path):
    if sys.platform == 'win32':
        import _winapi
        _winapi.CreateJunction(str(target), str(path))
    else:
        path.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize('relative', ['logs', 'logs/fighter-ui-preview', 'logs/fighter-native-preview',
                                      'logs/fighter-runtime-probe', 'logs/fighter-window-runs',
                                      'logs/fighter-probe-captures'])
def test_probe_rejects_redirected_output_roots_before_any_output(tmp_path, monkeypatch, capsys, relative):
    probe = driver(tmp_path, monkeypatch)
    outside = tmp_path / 'outside'; outside.mkdir()
    path = tmp_path / relative; path.parent.mkdir(parents=True, exist_ok=True)
    directory_link(outside, path)
    monkeypatch.setattr(probe, 'require_idle_game', lambda: None)
    monkeypatch.setattr(sys, 'argv', ['fighter-runtime-probe.py', 'unused.sod', 'unused.json'])
    assert probe.main() == 1
    assert 'redirected path' in capsys.readouterr().err
    assert list(outside.iterdir()) == []
    if relative in ('logs', 'logs/fighter-ui-preview'):
        with pytest.raises(ValueError, match='redirected path'):
            probe.prepare_portraits(tmp_path / 'nonexistent.viv', {})
    if relative in ('logs', 'logs/fighter-native-preview'):
        with pytest.raises(ValueError, match='redirected path'):
            probe.registry.write_preview(b'', {})


@pytest.mark.parametrize('child', ['', 'screens', 'screens/screens.viv'])
def test_portrait_cache_rejects_existing_redirected_children(tmp_path, monkeypatch, child):
    probe = driver(tmp_path, monkeypatch)
    source, report = portrait_inputs(tmp_path)
    output = probe.prepare_portraits(source, report)
    destination = output.parents[1]
    path = destination / child if child else destination
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    outside = tmp_path / 'outside'; outside.mkdir()
    directory_link(outside, path)
    with pytest.raises(ValueError, match='redirected path'):
        probe.prepare_portraits(source, report)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize('child', ['', 'assets', 'fighter-names.bin', 'assets/djv2.sod'])
def test_native_cache_rejects_existing_redirected_children(tmp_path, monkeypatch, child):
    probe = driver(tmp_path, monkeypatch)
    definition = tmp_path / 'alpha.json'; definition.write_text(json.dumps(pack()))
    cache, _ = probe.prepare(tmp_path / 'unused.sod', [definition])
    path = cache / child if child else cache
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    outside = tmp_path / 'outside'; outside.mkdir()
    directory_link(outside, path)
    with pytest.raises(ValueError, match='redirected path'):
        probe.prepare(tmp_path / 'unused.sod', [definition])
    assert list(outside.iterdir()) == []


def test_language_pack_preparation_keeps_other_native_files_and_rejects_sod_overlap(tmp_path, monkeypatch):
    from test_fighter_archive import fixture
    from test_langpack import lp
    probe = driver(tmp_path, monkeypatch)
    source = tmp_path / 'screens.viv'
    source.write_bytes(fixture({'text.bin': b'original'}))
    pin = tmp_path / 'config/fighter-native-baseline.json'; pin.parent.mkdir()
    pin.write_text(json.dumps({'screens_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}))
    folder = tmp_path / 'mods/xx-test'; (folder / 'patches').mkdir(parents=True)
    (folder / 'patches/one.djd').write_bytes(lp.delta_make(b'original', b'translated'))
    ini = folder / 'language.ini'
    header = '[language]\nschema=1\nname=Test\nlanguage=xx\n[files]\n'
    ini.write_text(header + 'screens/screens.viv|text.bin = patches/one.djd\n')
    composed, receipt = probe.prepare_language_screens(source, folder)
    assert probe.Archive(composed).read('text.bin') == b'translated'
    assert receipt['base_sha256'] == hashlib.sha256(composed).hexdigest()
    ini.write_text(header + 'gconfig.xml = patches/one.djd\n')
    assert probe.prepare_language_screens(source, folder) is None
    ini.write_text(header + 'assets/djv2.sod = patches/one.djd\n')
    with pytest.raises(ValueError, match='semantic composition adapter'):
        probe.prepare_language_screens(source, folder)
    ini.write_text(header + 'screens/screens.viv|text.bin = patches/one.djd\n')
    monkeypatch.setattr(probe, 'MAX_DELTA_BYTES', 8)
    with pytest.raises(ValueError, match='byte budget'):
        probe.prepare_language_screens(source, folder)


def texture_layer(root, name):
    from PIL import Image
    folder = root / name; folder.mkdir(parents=True)
    Image.new('RGBA', (4, 4), 'blue').save(folder / 'image.png')
    (folder / 'manifest.ini').write_text('[pack]\nschema=1\n[textures]\n' + 'a' * 64 + '=image.png\n')
    return folder


def test_texture_environment_preserves_native_pack_precedence_and_shared_language_root(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    first = texture_layer(tmp_path / 'mods', 'first')
    last = texture_layer(tmp_path / 'mods', 'last')
    language = tmp_path / 'mods/xx-test'; language.mkdir()
    assert probe.texture_environment([], None) == {}
    environment = probe.texture_environment([first, last], language)
    assert environment == {'RECOMP_TEXTURE_ROOT': str(first.parent), 'RECOMP_TEXTURE_PACKS': 'first;last',
                           'RECOMP_TEXTURE_TRACE': '1', 'RECOMP_LANGUAGE_PACK': 'xx-test'}
    with pytest.raises(ValueError, match='pack twice'): probe.texture_environment([first, first])
    other = texture_layer(tmp_path / 'other', 'other')
    with pytest.raises(ValueError, match='shared pack root'): probe.texture_environment([first, other])
    with pytest.raises(ValueError, match='shared pack root'): probe.texture_environment([other], language)
    # A language pack's own images are validated even when automatically prepended.
    (language / 'manifest.ini').write_text('[pack]\nschema=1\n[textures]\n' + 'b' * 64 + '=missing.png\n')
    with pytest.raises(ValueError, match='Missing image'): probe.texture_environment([first], language)


def test_texture_environment_rejects_redirected_images_and_native_list_truncation(tmp_path, monkeypatch):
    probe = driver(tmp_path, monkeypatch)
    first = texture_layer(tmp_path / 'mods', 'first')
    (first / 'manifest.ini').write_text('[pack]\nschema=1\n[textures]\n' + 'a' * 64 + '=images/image.png\n')
    outside = tmp_path / 'outside'; outside.mkdir()
    directory_link(outside, first / 'images')
    with pytest.raises(ValueError, match='Redirected pack file path'):
        probe.texture_environment([first])
    monkeypatch.setattr(probe, 'validate_textures', lambda _: None)
    folders = []
    for index in range(17):
        folder = tmp_path / 'mods' / (str(index).zfill(3) + 'x' * 60); folder.mkdir(); folders.append(folder)
    assert len(probe.texture_environment(folders[:16])['RECOMP_TEXTURE_PACKS']) == 1023
    with pytest.raises(ValueError, match='pack-list budget'): probe.texture_environment(folders)
    language = tmp_path / 'mods/xx-test'; language.mkdir(); (language / 'manifest.ini').write_text('placeholder')
    with pytest.raises(ValueError, match='pack-list budget'): probe.texture_environment(folders[:16], language)


def test_native_save_acceptance_requires_the_requested_kind_in_a_committed_closed_batch(tmp_path, monkeypatch):
    from test_fighter_save_journal import batch, put_acks, state, OPTIONS, PROFILE
    probe = driver(tmp_path, monkeypatch)
    journal = tmp_path / 'journal'; journal.mkdir()
    _, _, _, files, _ = state()
    (journal / '000001.batch').write_bytes(batch({OPTIONS: files[OPTIONS]}, {}))
    put_acks(journal, {OPTIONS: files[OPTIONS]})
    committed = [(1, 'verified-generation')]
    assert probe.verify_saved_kind(journal, committed, 'options') == ['Options']
    with pytest.raises(ValueError, match='acknowledged profile'):
        probe.verify_saved_kind(journal, committed, 'profile')
    (journal / '000002.batch').write_bytes(batch({PROFILE: files[PROFILE]}, {}, 2))
    put_acks(journal, {PROFILE: files[PROFILE]}, 2)
    with pytest.raises(ValueError, match='acknowledged profile'):
        probe.verify_saved_kind(journal, committed, 'profile')
    committed.append((2, 'next-verified-generation'))
    assert probe.verify_saved_kind(journal, committed, 'profile') == [PROFILE.rsplit('/', 1)[1]]
    (journal / '000002-00.closed').unlink()
    with pytest.raises(ValueError, match='close receipt'):
        probe.verify_saved_kind(journal, committed, 'profile')
