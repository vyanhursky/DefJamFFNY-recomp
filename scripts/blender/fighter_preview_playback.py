"""Temporary audio-master playback; native frames, strips and files are never retimed."""
import io
import math
import wave

import numpy as np

SOURCE_FPS = 30


def timeline_pcm(raw, voice_start_tick, duration):
    """Pad a preview-only mono buffer to the unchanged native source timeline."""
    if (type(voice_start_tick) is not int or voice_start_tick < 0
            or not math.isfinite(duration) or duration <= 0):
        raise ValueError('Invalid preview timeline')
    with wave.open(io.BytesIO(raw), 'rb') as sound:
        rate, count = sound.getframerate(), sound.getnframes()
        if (sound.getnchannels() != 1 or sound.getsampwidth() != 2
                or sound.getcomptype() != 'NONE' or not 8000 <= rate <= 48000):
            raise ValueError('Preview requires the validated mono PCM16 voice')
        pcm = sound.readframes(count)
    if len(pcm) != count * 2:
        raise ValueError('Truncated preview voice')
    start, length = round(voice_start_tick * rate / SOURCE_FPS), round(duration * rate / SOURCE_FPS)
    if start + count > length:
        raise ValueError('Preview voice extends beyond the source timeline')
    samples = np.zeros((length, 1), dtype=np.float32)
    samples[start:start + count, 0] = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768
    return samples, rate


class PreviewAudio:
    """Use the slowed sound's playback position as the sole preview clock.

    Sound.pitch changes only this temporary reader. Resampling before pitch
    makes 50% exactly representable even for odd input sample rates. Position
    is in slowed-output seconds, so multiply it by speed to recover source time.
    """
    def __init__(self, raw, voice_start_tick, duration, start_tick, speed, device=None):
        if speed not in (0.5, 1.0) or not math.isfinite(start_tick) or not 0 <= start_tick <= duration:
            raise ValueError('Choose 50% or 100% preview inside the source clip')
        import aud
        self.samples, rate = timeline_pcm(raw, voice_start_tick, duration)
        self.speed, self.duration = speed, duration
        self.sound = aud.Sound.buffer(self.samples, rate).resample(48000).pitch(speed)
        self.device = device if device is not None else aud.Device(buffer_size=256)
        self.handle = None
        self.device.lock()
        try:
            self.handle = self.device.play(self.sound, keep=True)
            self.handle.position = start_tick / SOURCE_FPS / speed
        except Exception:
            self.close()
            raise
        finally:
            self.device.unlock()

    @property
    def tick(self):
        position = float(self.handle.position)
        if not math.isfinite(position):
            raise ValueError('Preview audio clock is unavailable')
        return max(0., min(self.duration, position * self.speed * SOURCE_FPS))

    @property
    def playing(self):
        return self.handle is not None and bool(self.handle.status)

    def close(self):
        if self.handle is not None:
            self.handle.stop()
            self.handle = None
