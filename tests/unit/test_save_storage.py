"""Byte preservation and failure-before-uninstall, using only synthetic saves."""
import json
import os
from pathlib import Path

import pytest

from test_setup_engine import engine, installer

storage = engine.load_module('test_save_storage_impl', Path(__file__).resolve().parents[2] / 'setup/save_storage.py')


def saves(data):
    (data / 'save/TitleData/empty').mkdir(parents=True)
    (data / 'save/UserData').mkdir()
    (data / 'save/TitleData/profile').write_bytes(b'profile')
    (data / 'fighter-state').mkdir()
    (data / 'fighter-state/unlocks.ini').write_bytes(b'[unlock]\nfighter=1\n')
    (data / 'settings.ini').write_bytes(b'; settings\r\n')
    (data / 'save/Partition1.img').write_bytes(b'header' + bytes(2 * storage.BLOCK) + b'end' + bytes(storage.BLOCK))


@pytest.mark.parametrize('content', [b'', bytes(3 * 1024 * 1024), b'head' + bytes(3 * 1024 * 1024),
                                    bytes(1024 * 1024) + b'last', b'abc\x00xyz'],
                         ids=['empty', 'all-zero', 'trailing-hole', 'leading-hole', 'mixed'])
def test_sparse_copy_preserves_every_byte_and_length(tmp_path, content):
    original, copy = tmp_path / 'original', tmp_path / 'copy'
    original.write_bytes(content)
    storage.sparse_copy(original, copy)
    assert copy.read_bytes() == content and original.read_bytes() == content
    with pytest.raises(FileExistsError):
        storage.sparse_copy(original, copy)


def test_dense_fallback_preserves_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, 'sparse_output', lambda stream: False)
    source = tmp_path / 'source'
    source.write_bytes(bytes(storage.BLOCK) + b'tail')
    assert storage.sparse_copy(source, tmp_path / 'target') is False
    assert source.read_bytes() == (tmp_path / 'target').read_bytes()


def test_zero_image_really_uses_less_disk_space(tmp_path):
    source, target = tmp_path / 'dense', tmp_path / 'sparse'
    source.write_bytes(bytes(8 * storage.BLOCK))
    if not storage.sparse_copy(source, target):
        pytest.skip('Filesystem does not support sparse output')
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetCompressedFileSizeW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
        kernel.GetCompressedFileSizeW.restype = ctypes.c_ulong
        high = ctypes.c_ulong()
        low = kernel.GetCompressedFileSizeW(str(target), ctypes.byref(high))
        assert low != 0xffffffff or ctypes.get_last_error() == 0
        allocated = low + (high.value << 32)
    else:
        allocated = target.stat().st_blocks * 512
    assert allocated < storage.BLOCK
    assert storage.sha256(source) == storage.sha256(target)


def test_backup_includes_all_save_bytes_unlocks_settings_and_empty_directories(tmp_path):
    data = tmp_path / 'data'
    saves(data)
    backup = storage.backup(data, tmp_path / 'backup')
    manifest = json.loads((backup / 'backup.json').read_text())
    assert set(manifest['files']) == {'save/TitleData/profile', 'save/Partition1.img', 'fighter-state/unlocks.ini', 'settings.ini'}
    for name, digest in manifest['files'].items():
        assert storage.sha256(data / name) == storage.sha256(backup / name) == digest
    assert (backup / 'save/TitleData/empty').is_dir()
    with pytest.raises(FileExistsError):
        storage.backup(data, backup)


@pytest.mark.parametrize('placement', ['data', 'install', 'ancestor'])
def test_backup_never_goes_in_a_tree_uninstall_might_delete(tmp_path, placement):
    data, install = tmp_path / 'data', tmp_path / 'install'
    data.mkdir(); install.mkdir()
    destination = data / 'backup' if placement == 'data' else install / 'backup' if placement == 'install' else tmp_path
    with pytest.raises(ValueError, match='outside'):
        storage.backup(data, destination, forbidden=(install,))


def test_link_in_save_tree_fails_without_following_external_files(tmp_path):
    data = tmp_path / 'data'
    (data / 'save').mkdir(parents=True)
    outside = tmp_path / 'outside'; outside.mkdir()
    (outside / 'private').write_bytes(b'keep')
    link = data / 'save/redirect'
    if os.name == 'nt':
        import _winapi
        _winapi.CreateJunction(str(outside), str(link))
    else:
        link.symlink_to(outside, target_is_directory=True)
    try:
        with pytest.raises(ValueError, match='link'):
            storage.backup(data, tmp_path / 'backup')
        assert not (tmp_path / 'backup').exists()
        assert (outside / 'private').read_bytes() == b'keep'
    finally:
        if os.name == 'nt':
            os.rmdir(link)
        else:
            link.unlink()


@pytest.mark.parametrize('failure', ['copy', 'corruption', 'new-file', 'changed-source'])
def test_backup_failure_never_authorizes_uninstall(tmp_path, monkeypatch, failure):
    obj = installer(tmp_path)
    saves(obj.data)
    engine.write_json(obj.install / 'installed.json', dict(schema=1, source=str(obj.source), data=str(obj.data)))
    (obj.install / 'DefJamLauncher.exe').write_bytes(b'launcher')
    original_load = engine.load_module
    monkeypatch.setattr(engine, 'load_module', lambda name, path: storage if name == 'setup_save_storage' else original_load(name, path))
    original_copy = storage.sparse_copy
    def corrupt(source, target):
        if failure == 'copy':
            raise OSError('disk full')
        result = original_copy(source, target)
        if failure == 'corruption':
            target.write_bytes(b'corrupt')
        elif failure == 'new-file':
            (obj.data / 'save/new-profile').write_bytes(b'new')
        elif failure == 'changed-source':
            source.write_bytes(b'changed')
        return result
    monkeypatch.setattr(storage, 'sparse_copy', corrupt)
    with pytest.raises((OSError, ValueError)):
        engine.uninstall(obj.install, backup_dir=tmp_path / 'backup')
    assert obj.source.is_dir() and (obj.install / 'installed.json').is_file()
    assert (obj.install / 'DefJamLauncher.exe').read_bytes() == b'launcher'
    assert not (tmp_path / 'backup/backup.json').exists()


def test_successful_uninstall_backs_up_while_locks_are_held(tmp_path, monkeypatch):
    obj = installer(tmp_path); saves(obj.data)
    engine.write_json(obj.install / 'installed.json', dict(schema=1, source=str(obj.source), data=str(obj.data)))
    monkeypatch.setattr(engine.subprocess, 'run', lambda *a, **k: None)
    original_load = engine.load_module
    monkeypatch.setattr(engine, 'load_module', lambda name, path: storage if name == 'setup_save_storage' else original_load(name, path))
    original_backup = storage.backup
    def locked(data, destination, report, forbidden):
        for folder in (obj.install, obj.data):
            with pytest.raises(engine.SetupError, match='Another setup'):
                with engine.install_lock(folder):
                    pass
        return original_backup(data, destination, report, forbidden)
    monkeypatch.setattr(storage, 'backup', locked)
    engine.uninstall(obj.install, backup_dir=tmp_path / 'backup')
    assert not (obj.install / 'installed.json').exists()
    assert (tmp_path / 'backup/fighter-state/unlocks.ini').read_bytes() == b'[unlock]\nfighter=1\n'
    assert (obj.data / 'save/Partition1.img').is_file()
