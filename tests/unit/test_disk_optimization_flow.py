"""Shared app contract: inspect, explicit apply, cancellation and one-time completion."""
from argparse import Namespace
import json
from pathlib import Path

import pytest

from test_setup_engine import engine, installer


def fixture(tmp_path):
    obj = installer(tmp_path)
    (obj.data / 'save').mkdir()
    path = obj.data / 'save/Partition1.img'
    path.write_bytes(b'header' + bytes(4 * 1024**2))
    engine.write_json(obj.install / 'installed.json', dict(schema=1, source=str(obj.source), data=str(obj.data)))
    args = Namespace(install_dir=str(obj.install), apply_compaction=False, log=str(tmp_path / 'log.txt'),
                     cancel_file=str(tmp_path / 'cancel'), optimization_result=str(tmp_path / 'result.json'))
    return obj, path, args


def test_inspect_reports_space_and_capability_but_never_creates_completion_marker(tmp_path):
    obj, path, args = fixture(tmp_path)
    before = path.read_bytes()
    result = engine.run_disk_optimization(args)
    assert result['allocated_bytes'] > 0
    assert result['apply_supported'] == engine.IS_WINDOWS
    assert result['status'] == ('ready' if engine.IS_WINDOWS else 'unavailable')
    assert path.read_bytes() == before and not (obj.data / 'disk-optimization.json').exists()
    assert json.loads(Path(args.optimization_result).read_text()) == result


@pytest.mark.skipif(not engine.IS_WINDOWS, reason='Apply awaits native POSIX runtime cooperation')
def test_apply_publishes_success_and_one_time_marker_only_after_verification(tmp_path):
    obj, path, args = fixture(tmp_path)
    before = path.read_bytes()
    args.apply_compaction = True
    result = engine.run_disk_optimization(args)
    assert result['status'] == 'complete' and result['freed_bytes'] > 0
    assert path.read_bytes() == before
    marker = json.loads((obj.data / 'disk-optimization.json').read_text())
    assert marker['kind'] == 'disk-optimization-v1' and marker['status'] == 'complete'
    assert engine.run_disk_optimization(args)['freed_bytes'] == 0


def test_cancelled_inspection_reports_cancelled_and_cannot_suppress_future_offer(tmp_path):
    obj, path, args = fixture(tmp_path)
    Path(args.cancel_file).touch()
    with pytest.raises(engine.SetupError) as error:
        engine.run_disk_optimization(args)
    assert error.value.code == 6
    assert json.loads(Path(args.optimization_result).read_text())['status'] == 'cancelled'
    assert not (obj.data / 'disk-optimization.json').exists()


def test_non_windows_apply_reports_unavailable_without_marking_success(tmp_path, monkeypatch):
    obj, path, args = fixture(tmp_path)
    before = path.read_bytes()
    monkeypatch.setattr(engine, 'IS_WINDOWS', False)
    args.apply_compaction = True
    with pytest.raises(engine.SetupError, match='not available'):
        engine.run_disk_optimization(args)
    assert json.loads(Path(args.optimization_result).read_text())['status'] == 'failed'
    assert path.read_bytes() == before and not (obj.data / 'disk-optimization.json').exists()


@pytest.mark.skipif(not engine.IS_WINDOWS, reason='Apply awaits native POSIX runtime cooperation')
def test_locked_image_failure_has_result_but_no_completion_marker(tmp_path):
    obj, path, args = fixture(tmp_path)
    args.apply_compaction = True
    with path.open('r+b'):
        with pytest.raises(OSError):
            engine.run_disk_optimization(args)
    assert json.loads(Path(args.optimization_result).read_text())['status'] == 'failed'
    assert not (obj.data / 'disk-optimization.json').exists()
