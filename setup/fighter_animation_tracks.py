"""Compile bounded quaternion tracks into the native type11 scalar codec.

Bone ordinals belong to an explicitly matched rig. They are never inferred from
matching bone counts. Tracks use integer child-time ticks; parent time scaling,
event timing, bank composition and native admission remain separate gates.
"""
from dataclasses import dataclass
import math
import struct

from fighter_animation import require
from fighter_animation_scalars import f32

MAX_SCALARS = 16384
MAX_VALUES = 4 * 1024**2


@dataclass(frozen=True)
class QuaternionTracks:
    rig_sha256: str
    bone_count: int
    bones: tuple
    poses: tuple

    def validate(self):
        require(isinstance(self.rig_sha256, str) and len(self.rig_sha256) == 64
                and all(c in '0123456789abcdef' for c in self.rig_sha256),
                'Animation needs an explicit rig identity')
        require(type(self.bone_count) is int and 0 < self.bone_count <= 4096,
                'Animation rig exceeds its bone budget')
        require(type(self.bones) is tuple and 0 < len(self.bones) * 4 <= MAX_SCALARS
                and all(type(b) is int and 0 <= b < self.bone_count for b in self.bones)
                and list(self.bones) == sorted(set(self.bones)),
                'Quaternion tracks need unique ordered rig bone ordinals')
        require(type(self.poses) is tuple and 1 <= len(self.poses) <= 65535
                and len(self.poses) * len(self.bones) * 4 <= MAX_VALUES,
                'Animation sample population exceeds budget')
        for frame, pose in enumerate(self.poses):
            require(type(pose) is tuple and len(pose) == len(self.bones),
                    'Animation pose differs from its track population')
            for channel, q in enumerate(pose):
                require(type(q) is tuple and len(q) == 4
                        and all(type(v) in (int, float) and math.isfinite(v) for v in q)
                        and abs(sum(v * v for v in q) - 1) <= 0.001,
                        'Authored quaternion must be finite and unit length')
                # Native scalar interpolation does not choose a hemisphere.
                # Reject antipodal interpolation instead of silently rewriting it.
                if frame:
                    require(sum(a * b for a, b in zip(self.poses[frame - 1][channel], q)) >= 0,
                            'Adjacent quaternions cross hemispheres')

    def encode(self):
        """Return descriptor bytes and a measured quantization receipt.

        Sixteen-bit unsigned deltas use a per-scalar offset/scale. Error is
        checked after replaying the exact native float32 accumulation order;
        no unbounded drift or silently degraded track is emitted.
        """
        self.validate()
        frames = [tuple(f32(v) for q in pose for v in q) for pose in self.poses]
        count = len(self.bones) * 4
        coefficients, columns = [], []
        for scalar in range(count):
            deltas = [frames[i][scalar] - frames[i - 1][scalar] for i in range(1, len(frames))]
            low, high = (min(deltas), max(deltas)) if deltas else (0., 0.)
            offset = f32(low)
            scale = f32((high - low) / 65535)
            quantized = [min(65535, max(0, round((value - offset) / scale)))
                         if scale else 0 for value in deltas]
            coefficients.append((offset, scale, frames[0][scalar]))
            columns.append(quantized)
        descriptor = bytearray(struct.pack('<HBB', count, 16, 0))
        descriptor.extend(struct.pack('<' + 'f' * count * 3,
                                      *(v for triple in coefficients for v in triple)))
        current, maximum_error = list(frames[0]), 0.
        for row in range(len(frames) - 1):
            descriptor.extend(struct.pack('<' + 'H' * count, *(column[row] for column in columns)))
            for scalar, (offset, scale, _) in enumerate(coefficients):
                delta = f32(columns[scalar][row] * scale)
                current[scalar] = (f32(f32(delta + current[scalar]) + offset) if scalar % 4 == 0
                                   else f32(f32(delta + offset) + current[scalar]))
                maximum_error = max(maximum_error, abs(current[scalar] - frames[row + 1][scalar]))
        require(maximum_error <= 0.0001, 'Quaternion quantization exceeds the supported error bound')
        return bytes(descriptor), {
            'kind': 11, 'keys': len(frames), 'scalars': count, 'bits': 16,
            'destinations': tuple(b * 12 + 4 for b in self.bones),
            'rig_sha256': self.rig_sha256, 'bone_count': self.bone_count,
            'maximum_component_error': maximum_error, 'runtime_ready': False,
        }
