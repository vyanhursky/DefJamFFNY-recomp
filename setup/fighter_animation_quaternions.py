"""Finite type18 quaternion-channel replay, separate from runtime admission.

The original codec interpolates four scalars without normalization or hemisphere
correction. Replay starts at each block seed; reverse cache traversal and timing
selection are separate validation gates. All arithmetic follows SSE float32.
"""
import math
import struct

from fighter_animation import require
from fighter_animation_curves import CurveLayouts
from fighter_animation_scalars import f32


def constant(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


SEED_SCALE = constant(0x3A000801)
DESCRIPTOR_SCALE = constant(0x38000080)
DELTA_UNIT = constant(0x3C820821)


def seed(data):
    require(isinstance(data, bytes) and len(data) == 6, 'Quaternion seed needs six bytes')
    components = [word >> 4 for word in struct.unpack('<3H', data)]
    components.append((data[0] & 15) << 8 | (data[2] & 15) << 4 | (data[4] & 15))
    return tuple(f32(f32(value * SEED_SCALE) - 1) for value in components)


class QuaternionCurve:
    def __init__(self, layouts, record, *, work_budget=16 * 1024**2):
        require(type(layouts) is CurveLayouts and record in layouts.records,
                'Quaternion decoder requires an inspected curve')
        self.info = layouts.records[record]
        require(self.info['kind'] == 18, 'Unsupported quaternion codec record type')
        self.keys, self.channels, self.constants = (self.info[k] for k in ('keys', 'channels', 'constants'))
        require(type(work_budget) is int and 0 < work_budget
                and self.keys * (self.channels + self.constants) * 4 <= work_budget,
                'Quaternion decoding exceeds its work budget')
        self.layouts, self.record = layouts, record
        self.width = 1 << self.info['block_shift']
        self.block_bytes = (3 * self.channels * (self.width + 1) + 1) & ~1
        self.packed = record + 18 + 16 * self.channels
        self.coefficients = []
        for channel in range(self.channels):
            values = layouts.values(record + 18 + channel * 16, 8)
            self.coefficients.append((tuple(f32(f32(v * DESCRIPTOR_SCALE) - 1) for v in values[:4]),
                                      tuple(f32(v * DESCRIPTOR_SCALE) for v in values[4:])))
        end = self.packed + (self.keys // self.width) * self.block_bytes
        if self.keys % self.width:
            end += 3 * self.channels * (self.keys % self.width + 1)
        self.static = (end + self.constants + 1) & ~1

    def read(self, offset, size):
        start = self.layouts.numeric(offset, size)
        return self.layouts.model.data[start:start + size]

    def pose(self, key):
        require(type(key) is int and 0 <= key < self.keys, 'Quaternion key exceeds its curve')
        block, local = divmod(key, self.width)
        start = self.packed + block * self.block_bytes
        result = []
        for channel, (offsets, ranges) in enumerate(self.coefficients):
            values = seed(self.read(start + channel * 6, 6))
            for step in range(local):
                packed = self.read(start + 6 * self.channels + (step * self.channels + channel) * 3, 3)
                quantized = (packed[0] >> 2, packed[1] >> 2, packed[2] >> 2,
                             (packed[0] & 3) << 4 | (packed[1] & 3) << 2 | (packed[2] & 3))
                values = tuple(f32(current + f32(f32(f32(q * scale) * DELTA_UNIT) + offset))
                               for current, q, scale, offset in zip(values, quantized, ranges, offsets))
            result.append(values)
        result.extend(seed(self.read(self.static + channel * 6, 6)) for channel in range(self.constants))
        return tuple(result)

    def interpolated_pose(self, key, weight):
        require(type(key) is int and 0 <= key < self.keys - 1, 'Interpolation needs two quaternion keys')
        require(type(weight) in (int, float) and math.isfinite(weight) and 0 <= weight <= 1,
                'Quaternion interpolation weight is outside its interval')
        weight = f32(weight)
        first, second = self.pose(key), self.pose(key + 1)
        dynamic = tuple(tuple(f32(a + f32(f32(b - a) * weight)) for a, b in zip(left, right))
                        for left, right in zip(first[:self.channels], second[:self.channels]))
        return dynamic + first[self.channels:]

    def metadata(self):
        return {'kind': 18, 'keys': self.keys, 'channels': self.channels, 'constants': self.constants,
                'block_seed_replay_only': True, 'forward_replay_validated': True,
                'interpolation_arithmetic_validated': True,
                'cache_history_validated': False, 'output_context_validated': False, 'runtime_ready': False}
