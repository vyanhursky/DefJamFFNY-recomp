"""Verified reuse must preserve admission and reject altered inputs/results."""
from copy import deepcopy
import hashlib
import json
import os
import shutil

import pytest

from test_fighter_packages import manager, archive
from test_fighter_native import pack
import fighter_cache as cache
import fighter_packages as fighters


def equivalent(left, right):
    # A freshly compiled report may contain tuples; its persisted JSON uses lists.
    assert left[0] == right[0] and left[2:] == right[2:]
    assert cache.encoded(left[1]) == cache.encoded(right[1])


@pytest.fixture
def ready(manager, tmp_path, monkeypatch):
    calls = {'compile': 0, 'presentation': 0}
    compile_inputs, portraits = fighters.compile_inputs, fighters.prepare_portraits
    def compile(*args, **kwargs):
        calls['compile'] += 1
        return compile_inputs(*args, **kwargs)
    def present(*args, **kwargs):
        calls['presentation'] += 1
        return portraits(*args, **kwargs)
    monkeypatch.setattr(fighters, 'compile_inputs', compile)
    monkeypatch.setattr(fighters, 'prepare_portraits', present)
    manager.install_local(archive(tmp_path, pack()))
    manager.activate_fighter('alpha', True)
    result = fighters.build(manager, manager.state())
    return manager, calls, result


def test_cold_install_enable_and_warm_play_share_one_validated_composition(ready):
    manager, calls, result = ready
    before = deepcopy(manager.state())
    assert calls == {'compile': 1, 'presentation': 1}
    assert fighters.build(manager, manager.state()) == result
    assert manager.state() == before
    assert calls == {'compile': 1, 'presentation': 1}
    assert 'Reusing verified Fighter cache' in (manager.root / 'progress.ini').read_text()
    key = manager.root / 'fighter-cache-auth.key'
    assert key.stat().st_size == 32
    if os.name != 'nt':
        assert key.stat().st_mode & 0o777 == 0o600


def test_changed_pack_bytes_are_rejected_even_with_preserved_timestamp(ready):
    manager, calls, _ = ready
    path = manager.mods / 'alpha/fighters.json'
    stamp = path.stat()
    value = json.loads(path.read_text()); value['fighters'][0]['name'] = 'Changed'
    path.write_text(json.dumps(value)); os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    with pytest.raises(ValueError, match='changed or is missing'):
        fighters.build(manager, manager.state())
    assert calls['compile'] == 1


def test_warm_reuse_still_runs_existing_native_cache_validator(ready, monkeypatch):
    manager, calls, _ = ready
    validate = cache.write_preview
    checked = []
    def verify(*args, **kwargs):
        checked.append(kwargs['cache_root'])
        return validate(*args, **kwargs)
    monkeypatch.setattr(cache, 'write_preview', verify)
    fighters.build(manager, manager.state())
    assert checked == [manager.root / 'fighter-cache']
    assert calls['compile'] == 1


@pytest.mark.parametrize('which', ['compiler', 'original', 'ledger'])
def test_policy_original_content_and_identity_ledger_changes_invalidate(ready, monkeypatch, which):
    manager, calls, _ = ready
    state = manager.state()
    if which == 'compiler':
        monkeypatch.setattr(cache, 'compiler_identity', lambda: 'f' * 64)
    elif which == 'original':
        path = manager.game / 'assets/entity.xml'; path.parent.mkdir(parents=True)
        path.write_text('<original/>')
    else:
        state['fighter_ledger']['fighters']['alpha/fighter-0']['selection'] = 2000
    result = fighters.build(manager, state)
    assert calls == {'compile': 2, 'presentation': 2}
    equivalent(fighters.build(manager, state), result)
    assert calls['compile'] == 2


def test_disable_and_reenable_reuses_only_the_matching_roster(ready):
    manager, calls, before = ready
    manager.activate_fighter('alpha', False)
    assert fighters.build(manager, manager.state())[1]['binding_mode'] == 'retail-only'
    assert calls['compile'] == 2
    manager.activate_fighter('alpha', True)
    assert fighters.build(manager, manager.state()) == before
    assert calls['compile'] == 2


@pytest.mark.parametrize('relative', ['assets/djv2.sod', 'fighter-bindings.bin', 'fighter-ledger.json', 'report.json', 'screens'])
def test_modified_cached_bytes_fail_closed_without_recompiling(ready, relative):
    manager, calls, result = ready
    path = result[2] if relative == 'screens' else result[0] / relative
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='corrupt or changed'):
        fighters.build(manager, manager.state())
    assert calls['compile'] == 1


def test_forged_output_hashes_cannot_authenticate_a_modified_report(ready):
    manager, calls, result = ready
    path = result[0] / 'report.json'; path.write_bytes(path.read_bytes() + b' ')
    entry = next((manager.root / 'fighter-verified-cache').glob('*.json'))
    value = json.loads(entry.read_text()); value['receipt']['native_files']['report.json'] = hashlib.sha256(path.read_bytes()).hexdigest()
    entry.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='authentication failed'):
        fighters.build(manager, manager.state())
    assert calls['compile'] == 1


@pytest.mark.parametrize('kind', ['extra', 'missing', 'key'])
def test_partial_corruption_and_unexpected_files_never_become_hits(ready, kind):
    manager, calls, result = ready
    if kind == 'extra':
        (result[0] / 'unaccounted.bin').write_bytes(b'not a compiled resource')
    elif kind == 'missing':
        (result[0] / 'fighter-names.bin').unlink()
    else:
        (manager.root / 'fighter-cache-auth.key').write_bytes(b'bad')
    with pytest.raises((ValueError, OSError)):
        fighters.build(manager, manager.state())
    assert calls['compile'] == 1


def test_removing_the_entire_cache_rebuilds_through_the_full_compiler(ready):
    manager, calls, result = ready
    assert result[0].is_relative_to(manager.root)
    shutil.rmtree(result[0])
    equivalent(fighters.build(manager, manager.state()), result)
    assert calls['compile'] == 2


def test_a_failed_cold_validation_never_receives_an_authenticated_entry(ready, monkeypatch):
    manager, _, _ = ready
    before = set((manager.root / 'fighter-verified-cache').glob('*.json'))
    state = deepcopy(manager.state())
    monkeypatch.setattr(cache, 'compiler_identity', lambda: 'e' * 64)
    def reject(*args, **kwargs):
        raise ValueError('semantic source validation failed')
    monkeypatch.setattr(fighters, 'compile_inputs', reject)
    with pytest.raises(ValueError, match='semantic source validation failed'):
        fighters.build(manager, state)
    assert set((manager.root / 'fighter-verified-cache').glob('*.json')) == before
    assert manager.state() == state


def test_language_content_is_part_of_request_identity(tmp_path):
    game = tmp_path / 'game'; language = tmp_path / 'language'
    game.mkdir(); language.mkdir()
    delta = language / 'screens.djd'; delta.write_bytes(b'first')
    before = cache.request(game, {}, [], {}, language, None)
    stamp = delta.stat(); delta.write_bytes(b'other'); os.utime(delta, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert cache.request(game, {}, [], {}, language, None) != before


def test_compiler_identity_uses_relative_paths_and_content_under_logs(tmp_path, monkeypatch):
    root = tmp_path / 'logs/source'
    for name in ('setup', 'config', 'scripts', 'src/patches', 'src/hooks'):
        (root / name).mkdir(parents=True, exist_ok=True)
    for name in ('src/recomp_manual.c', 'CMakeLists.txt', '.gitmodules', 'setup/compiler.py'):
        (root / name).write_text('initial policy')
    monkeypatch.setattr(cache, 'ROOT', root)
    before = cache.compiler_identity()
    path = root / 'setup/compiler.py'; stamp = path.stat()
    path.write_text('changed policy'); os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    assert cache.compiler_identity() != before


def test_all_behavior_original_inputs_are_covered_by_cache_identity():
    from fighter_behavior import TARGETS
    assert {name for paths in TARGETS.values() for name in paths if '/' in name} <= set(cache.ORIGINALS)


def test_redirected_output_is_rejected(ready, tmp_path):
    manager, calls, result = ready
    path = result[0] / 'fighter-names.bin'; other = tmp_path / 'other.bin'
    other.write_bytes(path.read_bytes()); path.unlink()
    try:
        path.symlink_to(other)
    except OSError:
        pytest.skip('creating a symbolic link is unavailable on this host')
    with pytest.raises(ValueError, match='redirected|symlink'):
        fighters.build(manager, manager.state())
    assert calls['compile'] == 1
