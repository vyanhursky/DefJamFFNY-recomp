"""Build retention uses committed identity, never timestamps or directory ordering."""
import json
import os
import subprocess

import pytest

from test_setup_engine import engine, installer


def build(obj, digit, attempt=True):
    name = '1.2.1-' + digit * 12 + '-' + 'b' * 12
    if attempt:
        name += '-attempt-' + digit * 8
    folder = obj.install / 'versions' / name
    (folder / 'source').mkdir(parents=True)
    (folder / 'source/artifact').write_text(digit)
    return folder


def receipt(obj, active, previous=None):
    value = dict(schema=1, data=str(obj.data), source=str(active / 'source'))
    if previous:
        value['rollback_source'] = str(previous / 'source')
    engine.write_json(obj.install / 'installed.json', value)


def test_prune_keeps_committed_pair_and_removes_abandoned_and_legacy_builds(tmp_path):
    obj = installer(tmp_path)
    active, previous, abandoned, legacy = [build(obj, n, n != '4') for n in '1234']
    unknown = obj.install / 'versions/personal-backup'
    unknown.mkdir()
    receipt(obj, active, previous)
    messages = []
    engine.prune_builds(obj.install, obj.data, obj.dump, messages.append)
    assert active.is_dir() and previous.is_dir() and unknown.is_dir()
    assert not abandoned.exists() and not legacy.exists()
    assert len(messages) == 3  # includes the fixture's original unactivated build
    engine.prune_builds(obj.install, obj.data, obj.dump, messages.append)
    assert len(messages) == 3  # retry is harmless


@pytest.mark.parametrize('unsafe', ['journal', 'schema', 'active', 'rollback', 'data'])
def test_prune_refuses_untrusted_or_pending_receipts(tmp_path, unsafe):
    obj = installer(tmp_path)
    active, stale = build(obj, '1'), build(obj, '2')
    receipt(obj, active)
    path = obj.install / 'installed.json'
    value = json.loads(path.read_text())
    if unsafe == 'journal':
        (obj.install / engine.transaction.NAME).mkdir()
    elif unsafe == 'schema':
        value['schema'] = 2
    elif unsafe == 'data':
        value['data'] = str(tmp_path / 'other-data')
    else:
        value['source' if unsafe == 'active' else 'rollback_source'] = str(tmp_path / 'outside/source')
    engine.write_json(path, value)
    engine.prune_builds(obj.install, obj.data, obj.dump)
    assert stale.is_dir()


def test_cleanup_failure_does_not_fail_committed_install_and_can_retry(tmp_path, monkeypatch):
    obj = installer(tmp_path)
    active, stale = build(obj, '1'), build(obj, '2')
    receipt(obj, active)
    remove = engine.shutil.rmtree
    def denied(path):
        raise PermissionError('locked')
    messages = []
    monkeypatch.setattr(engine.shutil, 'rmtree', denied)
    engine.prune_builds(obj.install, obj.data, report=messages.append)
    assert stale.is_dir() and 'later cleanup' in messages[0]
    monkeypatch.setattr(engine.shutil, 'rmtree', remove)
    engine.prune_builds(obj.install, obj.data)
    assert not stale.exists()


@pytest.mark.parametrize('protected', ['data', 'dump'])
def test_player_paths_inside_a_build_are_preserved(tmp_path, protected):
    obj = installer(tmp_path)
    active, stale = build(obj, '1'), build(obj, '2')
    if protected == 'data':
        obj.data = stale / 'player-data'
        obj.data.mkdir()
    else:
        obj.dump = stale / 'source/artifact'
    receipt(obj, active)
    engine.prune_builds(obj.install, obj.data, obj.dump)
    assert stale.is_dir()


@pytest.mark.parametrize('host', ['engine', 'interpreter'])
def test_running_setup_host_inside_an_old_build_is_preserved(tmp_path, monkeypatch, host):
    obj = installer(tmp_path)
    active, stale = build(obj, '1'), build(obj, '2')
    receipt(obj, active)
    if host == 'engine':
        monkeypatch.setattr(engine, '__file__', str(stale / 'source/setup/engine.py'))
    else:
        monkeypatch.setattr(engine.sys, 'executable', str(stale / 'python/python.exe'))
    engine.prune_builds(obj.install, obj.data, obj.dump)
    assert stale.is_dir()


def test_redirected_build_and_nested_game_link_do_not_delete_dump(tmp_path):
    obj = installer(tmp_path)
    active, stale = build(obj, '1'), build(obj, '2')
    alias = obj.install / 'versions' / ('1.2.1-' + '3' * 12 + '-' + 'b' * 12)
    game = stale / 'source/game'
    if os.name == 'nt':
        for link in (alias, game):
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(link), str(obj.dump)], check=True, capture_output=True)
    else:
        alias.symlink_to(obj.dump, target_is_directory=True)
        game.symlink_to(obj.dump, target_is_directory=True)
    receipt(obj, active)
    try:
        engine.prune_builds(obj.install, obj.data, obj.dump)
        assert alias.exists() and not stale.exists()
        assert (obj.dump / 'default.xbe').read_bytes() == b'synthetic'
    finally:
        if os.name == 'nt':
            os.rmdir(alias)
        else:
            alias.unlink()


def test_activation_retains_actual_predecessor_and_never_prunes_on_rollback(tmp_path, monkeypatch):
    obj = installer(tmp_path)
    previous, stale = build(obj, '1'), build(obj, '2')
    receipt(obj, previous)
    (obj.payload / 'DefJamLauncher.exe').write_bytes(b'synthetic launcher')
    monkeypatch.setattr(engine, 'IS_WINDOWS', True)
    monkeypatch.setattr(engine, 'check_launcher_closed', lambda root: None)
    def fail(point):
        if point == 'receipt-json':
            raise OSError('interrupted activation')
    monkeypatch.setattr(engine.transaction, 'HOOK', fail)
    with pytest.raises(OSError, match='interrupted'):
        obj.activate()
    assert previous.is_dir() and stale.is_dir()
    assert json.loads((obj.install / 'installed.json').read_text())['source'] == str(previous / 'source')
    monkeypatch.setattr(engine.transaction, 'HOOK', None)
    obj.activate()
    value = json.loads((obj.install / 'installed.json').read_text())
    assert value['rollback_source'] == str(previous / 'source')
    assert previous.is_dir() and obj.source.is_dir() and not stale.exists()
    # Re-activation of the same build must not replace its predecessor with itself.
    obj.activate()
    assert json.loads((obj.install / 'installed.json').read_text())['rollback_source'] == str(previous / 'source')
    first_source = obj.source
    obj.source = build(obj, '3') / 'source'
    obj.activate()
    value = json.loads((obj.install / 'installed.json').read_text())
    assert value['rollback_source'] == str(first_source)
    assert first_source.is_dir() and obj.source.is_dir() and not previous.exists()
