"""Bounded external pose palettes used by the native type25 evaluator.

24430 -> 22010 -> 22150 passes the resolved PosePaletteBank to FDB40.
The native evaluator does not bound sample indices or destinations. This reader
requires an explicit frame-capacity contract and the matched body's bone count;
neither is inferred from an untrusted pointer or the type25 key count.
This module alone does not admit an appearance or authorize native playback.
"""
from dataclasses import dataclass
import math
import struct

from fighter_elf import Model, ModelError

EXPORT = '__PosePaletteBank:::PosePaletteBank'
VERSION = '__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4'
MAX_VALUES = 4 * 1024**2
# Supported retail _f contexts select at most frames12 and14 respectively.
# Measured across base00/wres/blazin and cinematic face banks; this is an
# adapter contract, not a bounds check supplied by the original evaluator.
REQUIRED_FRAMES = (13, 15)


def require(condition, message):
    if not condition:
        raise ModelError(message)


@dataclass(frozen=True)
class Palette:
    quaternion_destinations: tuple
    vector_destinations: tuple
    frames: tuple


class FacePalettes:
    def __init__(self, model, bone_count, frame_counts):
        require(type(model) is Model and not model.imports
                and model.exports == {EXPORT, VERSION}, 'Unsupported facial palette exports/imports')
        require(type(bone_count) is int and 0 < bone_count <= 4096,
                'Facial palettes require a bounded matched body rig')
        require(type(frame_counts) is tuple and 0 < len(frame_counts) <= 256
                and all(type(n) is int and 0 < n <= 256 for n in frame_counts),
                'Facial palettes require explicit sample-frame capacities')
        self.model, self.bone_count = model, bone_count
        self.frame_counts = frame_counts
        self.root = root = model.export_offset(EXPORT)
        self._spans, self._pointers = [], set()
        self._span(root, 8 + len(frame_counts) * 4)
        # +4 is retained as a structural population check, not a native bounds
        # guard: FDB40 directly indexes root+8+4*selector without consulting it.
        require(self._values(root + 4, 1, 'H')[0] == len(frame_counts),
                'Facial palette population differs from its context contract')
        self._values(root, 1, 'I')
        self._values(root + 6, 1, 'H')
        palettes, used = [], 0
        for index, frames in enumerate(frame_counts):
            palette = self._pointer(root + 8 + index * 4, 12)
            self._span(palette, 12)
            declared, quaternions, vectors, reserved = self._values(palette + 8, 4, 'B')
            # Frame capacity comes from the caller. The serialized +8 byte is
            # checked for agreement; it is not used by FDB40 to prevent overread.
            require(declared == frames and reserved == 0 and quaternions + vectors > 0,
                    'Facial palette header differs from the supported capacity contract')
            channels = quaternions + vectors
            used += frames * channels * 4
            require(used <= MAX_VALUES, 'Facial palette sample budget exceeded')
            destinations = self._pointer(palette + 4, channels * 2)
            self._span(destinations, channels * 2)
            dest = self._values(destinations, channels, 'H')
            occupied = set()
            for channel, offset in enumerate(dest):
                width = 4 if channel < quaternions else 3
                require(offset + width <= 12 * bone_count
                        and offset % 12 in ((4,) if width == 4 else (0, 8)),
                        'Facial palette destination is outside a supported body channel')
                slots = set(range(offset, offset + width))
                require(not occupied & slots, 'Facial palette channels overlap')
                occupied.update(slots)
            samples = self._pointer(palette, frames * channels * 16)
            self._span(samples, frames * channels * 16)
            rows = []
            for frame in range(frames):
                row = []
                for channel in range(channels):
                    values = self._values(samples + (frame * channels + channel) * 16, 4, 'f')
                    width = 4 if channel < quaternions else 3
                    active = values[:width]
                    require(all(math.isfinite(v) and abs(v) <= 1_000_000 for v in active),
                            'Facial palette contains invalid numeric samples')
                    if width == 4:
                        require(abs(sum(v * v for v in active) - 1) <= 0.002,
                                'Facial palette quaternion is not unit length')
                    row.append(active)
                rows.append(tuple(row))
            palettes.append(Palette(tuple(dest[:quaternions]), tuple(dest[quaternions:]), tuple(rows)))
        require(set(model.pointers) == self._pointers, 'Facial palette contains unrelated relocations')
        self.palettes = tuple(palettes)

    def _span(self, offset, size):
        self.model.data_range(offset, size)
        require(all(offset + size <= start or offset >= end for start, end in self._spans),
                'Facial palette data spans overlap')
        self._spans.append((offset, offset + size))

    def _values(self, offset, count, kind):
        size = struct.calcsize('<' + kind) * count
        at = self.model.data_range(offset, size)
        require(not any(offset < p + 4 and p < offset + size for p in self.model.pointers),
                'Facial palette numeric data contains a relocation')
        return self.model.unpack('<' + kind * count, at)

    def _pointer(self, field, size):
        target = self.model.local_pointer(field, size)
        self._pointers.add(field)
        return target

    def require_samples(self, selector, samples):
        """Check actual type25 sample bytes independently of its time-key count."""
        require(type(selector) is int and 0 <= selector < len(self.palettes),
                'Facial animation selects an unavailable palette')
        require(type(samples) in (bytes, tuple) and len(samples) > 0
                and all(type(sample) is int and 0 <= sample < self.frame_counts[selector] for sample in samples),
                'Facial animation sample exceeds the palette capacity')

    def metadata(self):
        return {'schema': 'fighter-face-palette-inspection-1', 'bone_count': self.bone_count,
                'palettes': [{'frames': count, 'quaternion_destinations': list(p.quaternion_destinations),
                              'vector_destinations': list(p.vector_destinations)}
                             for p, count in zip(self.palettes, self.frame_counts)],
                'native_playtest': False, 'animation_sample_joins_validated': False}


def declared_capacities(model):
    """Read candidate capacities; the full reader must then bound every array.

    These bytes are exporter metadata, not a native safety mechanism. Never
    use this helper alone to trust samples or to satisfy a context minimum.
    """
    root = model.export_offset(EXPORT)
    at = model.data_range(root + 4, 2)
    count, = model.unpack('<H', at)
    require(0 < count <= 256, 'Facial palette count exceeds its supported budget')
    model.data_range(root + 8, count * 4)
    return tuple(model.unpack('<B', model.data_range(model.local_pointer(root + 8 + i * 4, 12) + 8, 1))[0]
                 for i in range(count))


def compile_palettes(source, template, bone_count, minimum_frames=REQUIRED_FRAMES):
    """Rebuild typed samples/destinations inside a trusted local face envelope.

    Caller must obtain template from the verified original game. Source ELF
    controls, pointers, padding and extra bytes are never copied to the output.
    A larger declared capacity cannot substitute for bounds/numeric validation.
    """
    from fighter_animation_compile import rebuild
    authored = FacePalettes(source, bone_count, declared_capacities(source))
    original = FacePalettes(template, bone_count, declared_capacities(template))
    require(len(authored.palettes) == len(original.palettes) == len(minimum_frames)
            and all(n >= required for n, required in zip(authored.frame_counts, minimum_frames)),
            'Facial palette cannot cover the supported animation sample context')
    offset, size = template.sections[1][4:6]
    payload = bytearray(template.data[offset:offset + size])
    pointers = {}

    def append(data, alignment=4):
        payload.extend(bytes(-len(payload) % alignment))
        at = len(payload); payload.extend(data)
        return at

    for index, palette in enumerate(authored.palettes):
        packed = b''.join(struct.pack('<4f', *(channel if len(channel) == 4 else (*channel, 0.)))
                          for frame in palette.frames for channel in frame)
        samples = append(packed, 16)
        destinations = palette.quaternion_destinations + palette.vector_destinations
        target = append(struct.pack('<' + 'H' * len(destinations), *destinations))
        record = append(struct.pack('<IIBBBB', 0, 0, len(palette.frames),
                                    len(palette.quaternion_destinations), len(palette.vector_destinations), 0))
        pointers[record] = samples
        pointers[record + 4] = target
        pointers[original.root + 8 + index * 4] = record
    payload.extend(bytes(-len(payload) % 4))
    data, links = rebuild(template, payload, pointers)
    result = Model(data + links)
    checked = FacePalettes(result, bone_count, authored.frame_counts)
    require(checked.palettes == authored.palettes, 'Rebuilt facial palette differs from authored samples')
    return result, {'schema': 'fighter-face-palette-compile-1',
                    'frame_capacities': list(authored.frame_counts),
                    'required_frame_capacities': list(minimum_frames),
                    'source_controls_preserved': False, 'native_playtest': False}
