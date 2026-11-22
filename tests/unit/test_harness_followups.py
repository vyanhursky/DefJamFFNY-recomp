"""Negative controls for Story identity, structured verdicts and build provenance."""
import importlib.util
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


suite, ev, state = [load(n) for n in ('scenario_suite', 'test_evidence', 'pipeline-state')]


def profiles(root, names=('ABC', 'VY2', 'Options')):
    for i, name in enumerate(names):
        folder = root / 'UserData/45410049' / ('%012d' % i)
        folder.mkdir(parents=True)
        (folder / 'SaveMeta.xbx').write_bytes(('Name=' + name + '\r\n').encode('utf-16'))
        (folder / name).write_bytes(b'prepared career or options')


def test_story_fixture_selects_identity_without_touching_source(tmp_path):
    src, fixture = tmp_path / 'source', tmp_path / 'fixture'
    profiles(src)
    before = ev.tree_manifest(src)
    identity = suite.create_fixture(src, fixture, 'prepared gym career', 'VY2', ['crib', 'gym'])
    selected = ev.story_fixture(fixture, ['crib', 'gym'], fixture / 'save')
    assert selected['profile']['name'] == 'VY2'
    assert selected['fixture_manifest_sha256'] == identity['manifest_sha256']
    assert ev.tree_manifest(src) == before
    assert len(ev.saved_profiles(fixture / 'save')) == 1
    assert (fixture / 'save/UserData/45410049/000000000002/Options').is_file()
    stages = suite.harness.story_stages(suite.harness.ROUTES['gym']['stages'])
    assert 'getscreeninfo(options/userid=down@4;a@9' in stages


def test_story_refuses_legacy_multiple_changed_or_incompatible_profiles(tmp_path):
    src, legacy, fixture = (tmp_path / p for p in ('source', 'legacy', 'fixture'))
    profiles(src)
    suite.create_fixture(src, legacy, 'uncalibrated list')
    with pytest.raises(ValueError, match='single-profile'):
        ev.story_fixture(legacy, ['crib'])
    suite.create_fixture(src, fixture, 'prepared crib', 'VY2', ['crib'])
    with pytest.raises(ValueError, match='progression'):
        ev.story_fixture(fixture, ['gym'])
    run_save = tmp_path / 'run-save'
    shutil.copytree(fixture / 'save', run_save)
    profiles(run_save, ('TRANSFERRED',))
    with pytest.raises(ValueError, match='differs'):
        ev.story_fixture(fixture, ['crib'], run_save)
    path = fixture / 'save' / ev.saved_profiles(fixture / 'save')[0]['path']
    (path / 'VY2').write_bytes(b'different progression')
    with pytest.raises(ValueError, match='contents differ'):
        ev.story_fixture(fixture, ['crib'])
    with pytest.raises(ValueError, match='uncalibrated'):
        suite.harness.story_stages(['getscreeninfo(options/userid=down@4;down@6;down@8;a@9'])


def test_story_prerequisite_fails_before_build_verification_or_launch(tmp_path, monkeypatch):
    src, fixture = tmp_path / 'source', tmp_path / 'fixture'
    profiles(src)
    suite.create_fixture(src, fixture, 'old fixture with several careers')
    monkeypatch.setattr(suite, 'source_identity', lambda _: {})
    def forbidden(*args, **kwargs):
        pytest.fail('incompatible fixture must be rejected before build or launch')
    monkeypatch.setattr(suite.harness.pipeline_state, 'verify_build', forbidden)
    monkeypatch.setattr(suite.harness, 'run_route', forbidden)
    output = tmp_path / 'report'
    assert suite.main(['run', 'gym', '--fixture', str(fixture), '--output', str(output)]) == 1
    report = json.loads((output / 'report.json').read_text())
    assert 'single-profile' in report['assertions'][0]['detail']
    assert not list(output.glob('runtime-*'))


def test_story_refuses_unhashed_empty_profile_directory(tmp_path):
    src, fixture = tmp_path / 'source', tmp_path / 'fixture'
    profiles(src, ('VY2', 'Options'))
    suite.create_fixture(src, fixture, 'crib', 'VY2', ['crib'])
    (fixture / 'save/UserData/45410049/EMPTY').mkdir()
    with pytest.raises(ValueError, match='unusable saved profile directory'):
        ev.story_fixture(fixture, ['crib'])


def test_story_observes_the_backend_selection_before_story_starts():
    calls = ['Control.GetScreenInfo(options/userID.swf)', 'MemCard.GetUserData(0)',
             'MemCard.SetCurrentUserIndex(0,0)', 'Game.StartStoryMode(0,0)']
    log = '\n'.join('[FUNCCALL] ' + c for c in calls)
    assert ev.story_selection_check(log)['status'] == 'pass'
    assert ev.story_selection_check(log.replace('GetUserData(0)', 'GetUserData(1)'))['status'] == 'fail'
    assert ev.story_selection_check(log.replace('SetCurrentUserIndex(0,0)', 'SetCurrentUserIndex(0,1)'))['status'] == 'fail'
    assert ev.story_selection_check('\n'.join(log.splitlines()[:-1]))['status'] == 'fail'
    assert ev.story_selection_check(log.replace('[FUNCCALL]', '[FE-INJECT]'))['status'] == 'fail'


@pytest.mark.parametrize('character,expected', [(4, 'pass'), (5, 'fail'), (None, 'fail')])
def test_existing_fighter_verdict_reaches_json_junit_and_html(tmp_path, character, expected):
    run = suite.harness.Run('fight', '', '')
    run.text = '' if character is None else '[TEST-EVENT] ' + json.dumps({
        'event': 'match_start', 'fighters': [{'slot': 0, 'character': character, 'cpu': False}]})
    run.summary, run.save_ok = suite.harness.summarise(run.text), True
    checks = suite.route_assertions('fight', run, 'win-x64-release', {0: 4})
    check = next(c for c in checks if c['name'] == 'identity.fighters')
    assert check['status'] == expected
    report = {'name': 'identity', 'identity': {}, 'assertions': [check]}
    ok = ev.write_report(tmp_path, report)
    assert ok == (expected == 'pass')
    assert json.loads((tmp_path / 'report.json').read_text())['assertions'][0] == json.loads(json.dumps(check))
    case = ET.parse(tmp_path / 'junit.xml').find('testcase')
    assert (case.find('failure') is None) == (expected == 'pass')
    assert check['detail'] in (tmp_path / 'index.html').read_text()


@pytest.mark.parametrize('log,expected', [('', 'fail'),
    ('[FUNCCALL] Game.ChooseVenue(6)', 'fail'),
    ('[START] venue(script)=14 fighters: 4 9', 'fail'),
    ('[START] venue(script)=6 fighters: 4 9', 'pass')])
def test_venue_needs_observed_identity(log, expected):
    assert ev.venue_check(log, 6)['status'] == expected


def test_final_menu_is_ordered_and_bounded():
    calls = ['GetScreenInfo(intMain/mainMenu)', 'Game.StartGame()', 'Game.GetMatchSummary()',
             'GetScreenInfo(battle/cmtype)', 'GetScreenInfo(intMain/mainMenu)']
    timeline = [{'call': c, 'observed_seconds': t} for c, t in zip(calls, [0, 60, 180, 200, 210])]
    assert ev.final_menu_check(timeline)['status'] == 'pass'
    assert ev.final_menu_check(timeline + [{'call': 'GetScreenInfo(battle/cmtype)',
                                           'observed_seconds': 212}])['status'] == 'fail'
    assert ev.final_menu_check(timeline[:-1])['status'] == 'fail'
    assert ev.final_menu_check(timeline[:2] + timeline[3:] + timeline[2:3])['status'] == 'fail'
    timeline[-1]['observed_seconds'] = 271
    assert ev.final_menu_check(timeline)['status'] == 'fail'


@pytest.mark.parametrize('suffix', ['', '-MSVC_2'])
def test_toolchain_comes_from_active_cmake_configuration(tmp_path, monkeypatch, suffix):
    (tmp_path / 'CMakeCache.txt').write_text('''CMAKE_CACHE_MAJOR_VERSION:INTERNAL=3
CMAKE_CACHE_MINOR_VERSION:INTERNAL=20
CMAKE_CACHE_PATCH_VERSION:INTERNAL=0
CMAKE_GENERATOR:INTERNAL=Ninja
CMAKE_BUILD_TYPE:STRING=RelWithDebInfo
CMAKE_TOOLCHAIN_FILE:FILEPATH=/bundled/toolchain.cmake
''')
    folder = tmp_path / ('CMakeFiles/3.20.0' + suffix)
    folder.mkdir(parents=True)
    (folder / 'CMakeCCompiler.cmake').write_text('''set(CMAKE_C_COMPILER "/bundled/clang")
set(CMAKE_C_COMPILER_ID "Clang")
set(CMAKE_C_COMPILER_VERSION "19.1.7")
''')
    # A newer stale configure and today's PATH must not alter recorded identity.
    stale = tmp_path / 'CMakeFiles/4.0.0'
    stale.mkdir()
    (stale / 'CMakeCCompiler.cmake').write_text('set(CMAKE_C_COMPILER_ID "Wrong")')
    monkeypatch.setenv('PATH', 'irrelevant')
    receipt = state.build_toolchain(tmp_path)
    assert receipt['status'] == 'available'
    assert receipt['compilers']['C']['compiler_version'] == '19.1.7'
    assert receipt['toolchain_file'] == '/bundled/toolchain.cmake'
    assert ev.toolchain_identity({'exe': 'hash', 'toolchain': receipt}) == receipt
    (folder / 'CMakeCCompiler.cmake').unlink()
    assert state.build_toolchain(tmp_path)['status'] == 'unavailable'


def test_legacy_toolchain_is_explicit_and_does_not_change_verdict(tmp_path):
    ident = ev.toolchain_identity({'exe': 'old hash'})
    assert ident['status'] == 'unavailable' and 'older build-state' in ident['reason']
    report = {'name': 'legacy', 'identity': {'toolchain': ident},
              'assertions': [ev.assertion('runtime', True, 'unchanged')]}
    assert ev.write_report(tmp_path, report)
    assert ident['reason'] in (tmp_path / 'index.html').read_text()


def test_record_build_binds_compiler_receipt_to_executable_hash(tmp_path, monkeypatch):
    folder = tmp_path / 'build/test-preset'
    folder.mkdir(parents=True)
    (folder / 'CMakeCache.txt').write_text('DEFJAM_BUILD_GAME:BOOL=ON\n')
    executable = folder / state.EXE_NAME
    executable.write_bytes(b'synthetic game-free test executable')
    inputs = {'sources': 'verified'}
    state.begin_stage(folder / 'build-state.json', inputs)
    monkeypatch.setattr(state, 'build_inputs', lambda *a: inputs)
    receipt = {'status': 'available', 'compilers': {'C': {'compiler_version': '19.1.7'}}}
    monkeypatch.setattr(state, 'build_toolchain', lambda p: receipt)
    assert state.main(['record-build', '--repo', str(tmp_path), '--preset', 'test-preset']) == 0
    recorded = state.verify_build(tmp_path, 'test-preset')
    assert recorded['exe'] == ev.digest(executable) and recorded['toolchain'] == receipt
    executable.write_bytes(b'replaced executable')
    with pytest.raises(ValueError, match='stale'):
        state.verify_build(tmp_path, 'test-preset')
