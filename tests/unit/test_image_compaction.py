"""Zero-range deallocation, OS writer exclusion and interrupted runs."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from test_setup_engine import engine, installer

MODULE = Path(__file__).resolve().parents[2] / 'setup/save_storage.py'
storage = engine.load_module('test_compaction_storage', MODULE)
windows = pytest.mark.skipif(os.name != 'nt', reason='Experimental apply is Windows-only')


def image(tmp_path):
    path = tmp_path / 'Partition1.img'
    with path.open('wb') as stream:
        stream.write(b'header')
        stream.write(bytes(4 * storage.BLOCK))
        stream.write(b'nonzero middle')
        stream.write(bytes(4 * storage.BLOCK))
        stream.write(b'end')
    return path


@windows
def test_compact_reclaims_allocation_preserves_contents_identity_time_and_ads(tmp_path, monkeypatch):
    path = image(tmp_path)
    ads = Path(str(path) + ':fixture')
    ads.write_bytes(b'alternate stream')
    before = path.stat()
    digest = storage.sha256(path)
    actual = storage.zero_range
    def checked(stream, first, end):
        stream.seek(first)
        assert stream.read(end - first) == bytes(end - first)
        actual(stream, first, end)
    monkeypatch.setattr(storage, 'zero_range', checked)
    result = storage.compact_image(path)
    assert result['changed'] and result['after'] < result['before']
    assert storage.sha256(path) == digest and path.stat().st_size == before.st_size
    assert path.stat().st_ino == before.st_ino and path.stat().st_mtime_ns == before.st_mtime_ns
    assert ads.read_bytes() == b'alternate stream'
    assert storage.compact_image(path)['after'] == result['after']


@windows
@pytest.mark.parametrize('failure', ['before-punch', 'partial-punch', 'unsupported'])
def test_failure_only_leaves_byte_identical_partially_compacted_image(tmp_path, monkeypatch, failure):
    path = image(tmp_path)
    digest = storage.sha256(path)
    actual = storage.zero_range
    def failed(stream, first, end):
        if failure == 'partial-punch':
            actual(stream, first, end)
        raise OSError('injected failure')
    monkeypatch.setattr(storage, 'zero_range', failed)
    if failure == 'unsupported':
        monkeypatch.setattr(storage, 'sparse_output', lambda stream: False)
    with pytest.raises((OSError, ValueError)):
        storage.compact_image(path)
    assert storage.sha256(path) == digest


@windows
def test_hard_kill_after_first_zero_range_keeps_bytes_and_rerun_is_safe(tmp_path):
    path = image(tmp_path)
    before = storage.sha256(path), path.stat().st_ino
    driver = tmp_path / 'crash.py'
    driver.write_text('import importlib.util,os,sys\n'
        'spec=importlib.util.spec_from_file_location("storage",sys.argv[1])\n'
        's=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)\n'
        'real=s.zero_range\n'
        'def crash(*args):\n real(*args)\n os._exit(17)\n'
        's.zero_range=crash\n'
        's.compact_image(s.Path(sys.argv[2]))\n')
    result = subprocess.run([sys.executable, str(driver), str(MODULE), str(path)], capture_output=True)
    assert result.returncode == 17
    assert before == (storage.sha256(path), path.stat().st_ino)
    storage.compact_image(path)
    assert before == (storage.sha256(path), path.stat().st_ino)


@windows
def test_writer_from_another_install_is_excluded_without_its_play_lock(tmp_path, monkeypatch):
    path = image(tmp_path)
    with path.open('r+b'):
        with pytest.raises(OSError):
            storage.compact_image(path)
    actual = storage.zero_range
    def attempt_writer(stream, first, end):
        with pytest.raises(OSError):
            with path.open('r+b'):
                pytest.fail('writer opened during compaction')
        actual(stream, first, end)
    monkeypatch.setattr(storage, 'zero_range', attempt_writer)
    storage.compact_image(path)


@windows
def test_multiple_hard_links_are_refused(tmp_path):
    path = image(tmp_path)
    os.link(path, tmp_path / 'other-link')
    with pytest.raises(ValueError, match='hard links'):
        storage.compact_image(path)


@windows
def test_compacted_image_can_grow_allocated_storage_on_new_writes(tmp_path):
    path = image(tmp_path)
    size = path.stat().st_size
    storage.compact_image(path)
    before = storage.allocated_bytes(path)
    with path.open('r+b') as stream:
        stream.seek(2 * storage.BLOCK)
        stream.write(b'new save data')
        stream.flush(); os.fsync(stream.fileno())
    assert storage.allocated_bytes(path) > before
    with path.open('rb') as stream:
        stream.seek(2 * storage.BLOCK)
        assert stream.read(13) == b'new save data'
    assert path.stat().st_size == size
    digest = storage.sha256(path)
    storage.compact_image(path)
    assert storage.sha256(path) == digest


def test_report_only_platform_guard_and_only_numbered_images(tmp_path, monkeypatch):
    obj = installer(tmp_path)
    (obj.data / 'save').mkdir()
    path = image(obj.data / 'save')
    other = obj.data / 'save/other.img'; other.write_bytes(b'leave alone')
    engine.write_json(obj.install / 'installed.json', dict(schema=1, source=str(obj.source), data=str(obj.data)))
    original_load = engine.load_module
    monkeypatch.setattr(engine, 'load_module', lambda name, file: storage if name == 'setup_save_storage' else original_load(name, file))
    before = path.stat().st_ino, path.stat().st_mtime_ns, storage.sha256(path)
    engine.compact_save_images(obj.install, report=lambda text: None)
    assert before == (path.stat().st_ino, path.stat().st_mtime_ns, storage.sha256(path))
    if os.name != 'nt':
        with pytest.raises(ValueError, match='Windows-only'):
            engine.compact_save_images(obj.install, apply=True)
        return
    with engine.game_lock(obj.install):
        with pytest.raises(engine.SetupError, match='Close the installed game'):
            engine.compact_save_images(obj.install, apply=True)
    result = engine.compact_save_images(obj.install, apply=True)
    assert len(result) == 1 and result[0]['changed']
    assert other.read_bytes() == b'leave alone'
