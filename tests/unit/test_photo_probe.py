"""The evidence parser must reject a frozen timer without camera/resume proof."""
import importlib.util
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('photo_probe', SCRIPTS / 'photo-probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def trace(paused=False):
    return ['[PHOTO] enter module=0 flags=0 origin_paused=' + str(int(paused)) + ' scale=1.00',
            '[PHOTO] draw=60 frozen=yes pos=0,1,2',
            '[PHOTO] draw=120 frozen=yes pos=1,1,2',
            '[PHOTO] draw=180 frozen=yes pos=1,1,2',
            '[PHOTO] exit frozen=yes flags=0 scale=1.00'] + ([] if paused else ['[TEST-STATE] {"step":300}'])


@pytest.mark.parametrize('context', ['live', 'paused'])
def test_accepts_camera_motion_freeze_and_correct_return(context):
    assert probe.analyse_photo(trace(context == 'paused'), context)['passed']


@pytest.mark.parametrize('change', ['no_camera', 'moving_world', 'simulation_during', 'no_resume'])
def test_rejects_incomplete_proof(change):
    lines = trace()
    if change == 'no_camera':
        lines = [line.replace('pos=1,1,2', 'pos=0,1,2') for line in lines]
    elif change == 'moving_world':
        lines[2] = lines[2].replace('frozen=yes', 'frozen=NO')
    elif change == 'simulation_during':
        lines.insert(2, '[TEST-STATE] {"step":200}')
    else:
        lines.pop()
    assert not probe.analyse_photo(lines, 'live')['passed']


def test_rejects_paused_exit_that_resumes_or_was_never_paused():
    assert not probe.analyse_photo(trace() + ['[TEST-STATE] {}'], 'paused')['passed']
    assert not probe.analyse_photo(trace(True) + ['[TEST-STATE] {}'], 'paused')['passed']


def test_pause_does_not_require_zero_time_scale():
    result = probe.analyse_photo(trace(True), 'paused')
    assert result['entry_scale'] == 1.0
    assert result['passed']


def test_rejects_pause_with_changed_scale_on_return():
    lines = trace(True)
    lines[-1] = lines[-1].replace('scale=1.00', 'scale=0.00')
    assert not probe.analyse_photo(lines, 'paused')['passed']


def test_victory_must_progress_after_camera_exit():
    lines = trace(True)
    lines[0] += ' state=10'
    assert not probe.analyse_photo(lines, 'victory')['passed']
    lines.append('[PHOTO] context state=11 screen24=0')
    assert probe.analyse_photo(lines, 'victory')['passed']
