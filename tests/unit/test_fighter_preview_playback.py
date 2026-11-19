"""Preview uses an independent audio clock and leaves native authored timing alone."""
import io
from pathlib import Path
import sys
from types import SimpleNamespace
import wave

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/blender'))
from fighter_preview_playback import PreviewAudio, timeline_pcm


def voice():
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as output:
        output.setnchannels(1); output.setsampwidth(2); output.setframerate(24000)
        output.writeframes(np.arange(2400, dtype='<i2').tobytes())
    return buffer.getvalue()


def test_preview_padding_preserves_voice_and_source_offset():
    raw = voice(); original = bytes(raw)
    samples, rate = timeline_pcm(raw, 5, 30)
    assert rate == 24000 and samples.shape == (24000, 1)
    assert np.count_nonzero(samples[:4000]) == np.count_nonzero(samples[6400:]) == 0
    assert np.array_equal(samples[4000:6400, 0] * 32768, np.arange(2400))
    assert raw == original


@pytest.mark.parametrize('start,duration', [(-1, 30), (30, 30), (0, 0), (0, float('nan'))])
def test_preview_rejects_invalid_or_truncated_timeline(start, duration):
    with pytest.raises(ValueError): timeline_pcm(voice(), start, duration)


class Sound:
    @staticmethod
    def buffer(samples, rate): return Sound()
    def resample(self, rate): assert rate == 48000; return self
    def pitch(self, speed): self.speed = speed; return self


class Device:
    def __init__(self): self.locks = 0; self.stopped = 0
    def lock(self): self.locks += 1
    def unlock(self): self.locks -= 1
    def play(self, sound, keep):
        assert keep
        self.sound = sound
        def stop(): self.stopped += 1
        self.handle = SimpleNamespace(position=0., status=True, stop=stop)
        return self.handle


@pytest.mark.parametrize('speed', [.5, 1.])
def test_audio_clock_seek_and_cleanup_do_not_depend_on_timer_frequency(monkeypatch, speed):
    monkeypatch.setitem(sys.modules, 'aud', SimpleNamespace(Sound=Sound))
    device = Device(); player = PreviewAudio(voice(), 5, 30, 9., speed, device)
    assert device.locks == 0 and device.sound.speed == speed
    assert device.handle.position == pytest.approx(9 / 30 / speed)
    device.handle.position = .8
    assert player.tick == pytest.approx(.8 * speed * 30)
    device.handle.position = 999
    assert player.tick == 30
    device.handle.position = float('nan')
    with pytest.raises(ValueError): _ = player.tick
    player.close(); player.close()
    assert device.stopped == 1 and not player.playing


@pytest.mark.parametrize('speed', [0, -.5, .25, 2, float('nan')])
def test_only_explicit_preview_rates_are_admitted(speed):
    with pytest.raises(ValueError): PreviewAudio(voice(), 5, 30, 0, speed)


def modal_fixture():
    # Blender4.5's Event has type/value but no public timer attribute.
    import ast
    source = Path(__file__).resolve().parents[2] / 'scripts/blender/fighter_voice_controls.py'
    tree = ast.parse(source.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FFNY_OT_preview_play')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'modal')
    player = object(); calls = []
    env = dict(PREVIEW=player, stop_preview=lambda: calls.append('stop'),
               step_preview=lambda context, current: calls.append('step') or True)
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), env)
    operator = SimpleNamespace(player=player, report=lambda *args: calls.append('error'))
    return env, operator, calls


def test_modal_timer_works_with_actual_blender45_event_fields():
    env, operator, calls = modal_fixture()
    assert env['modal'](operator, None, SimpleNamespace(type='TIMER', value='NOTHING')) == {'PASS_THROUGH'}
    assert calls == ['step']
    assert env['modal'](operator, None, SimpleNamespace(type='SPACE', value='PRESS')) == {'FINISHED'}
    assert calls == ['step', 'stop']


def test_modal_error_and_replaced_player_cleanup():
    env, operator, calls = modal_fixture()
    def broken(*args): raise RuntimeError('invalid editing state')
    env['step_preview'] = broken
    assert env['modal'](operator, None, SimpleNamespace(type='TIMER', value='NOTHING')) == {'CANCELLED'}
    assert calls == ['stop', 'error']
    env['PREVIEW'] = object(); calls.clear()
    assert env['modal'](operator, None, SimpleNamespace(type='TIMER', value='NOTHING')) == {'FINISHED'}
    assert not calls
