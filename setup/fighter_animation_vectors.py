"""Finite type20/type21 vector replay; not native resource admission.

The ordinary F14F0 route uses float-slot destinations and rounded endpoint
interpolation. Each offline sample starts at its block seed. Filtered output,
cache-history differences and the meaning of each destination remain separate
contracts; this reader does not infer a rig or permit an arbitrary native bank.
"""
from bisect import bisect_right
import math
import struct

from fighter_animation import require
from fighter_animation_curves import CurveLayouts
from fighter_animation_scalars import f32


def constant(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


SEED_SCALE = constant(0x37800080)
DESCRIPTOR_SCALE = constant(0x38000080)
DELTA_SCALE = constant(0x3B808081)


class VectorCurve:
    def __init__(self, layouts, record, *, work_budget=16 * 1024**2):
        require(type(layouts) is CurveLayouts and record in layouts.records,
                'Vector decoder requires an inspected curve')
        self.info = layouts.records[record]
        require(self.info['kind'] in (20, 21), 'Unsupported vector codec record type')
        self.dimension = dimension = 3 if self.info['kind'] == 20 else 1
        self.keys, self.channels, self.constants = (self.info[k] for k in ('keys', 'channels', 'constants'))
        require(type(work_budget) is int and 0 < work_budget
                and self.keys * (self.channels + self.constants) * dimension <= work_budget,
                'Vector decoding exceeds its work budget')
        self.layouts, self.record = layouts, record
        self.width = 1 << self.info['block_shift']
        self.block_bytes = (dimension * self.channels * (self.width + 1) + 1) & ~1
        self.packed = record + 20 + 12 * dimension * self.channels
        self.coefficients = []
        for channel in range(self.channels):
            at = record + 20 + 12 * dimension * channel
            bases, extents = layouts.values(at, dimension, 'f'), layouts.values(at + 4 * dimension, dimension, 'f')
            offsets, ranges = layouts.values(at + 8 * dimension, dimension), layouts.values(at + 10 * dimension, dimension)
            self.coefficients.append(tuple(
                (base, f32(extent * SEED_SCALE),
                 f32(f32(f32(offset * extent) * DESCRIPTOR_SCALE) - extent),
                 f32(f32(f32(span * extent) * DESCRIPTOR_SCALE) * DELTA_SCALE))
                for base, extent, offset, span in zip(bases, extents, offsets, ranges)))
        end = self.packed + (self.keys // self.width) * self.block_bytes
        if self.keys % self.width:
            end = (end + dimension * self.channels * (self.keys % self.width + 1) + 1) & ~1
        if not self.channels:
            end = (end + 1) & ~1
        dynamic = layouts.values(layouts.pointer(record + 4, 2 * self.channels), self.channels) if self.channels else ()
        self.destinations = dynamic + layouts.values(end, self.constants)
        self.static = tuple(layouts.values((end + 2 * self.constants + 3) & ~3, self.constants * dimension, 'f'))
        self.times = layouts.times(record + 8, self.keys, transitions=True, optional=True)

    def pose(self, key):
        require(type(key) is int and 0 <= key < self.keys, 'Vector key exceeds its curve')
        block, local = divmod(key, self.width)
        start = self.packed + block * self.block_bytes
        result = []
        for channel, coefficients in enumerate(self.coefficients):
            seeds = self.layouts.values(start + channel * 2 * self.dimension, self.dimension)
            values = tuple(f32(f32(seed * scale) + base)
                           for seed, (base, scale, _, _) in zip(seeds, coefficients))
            for step in range(local):
                quantized = self.layouts.values(start + self.dimension * (2 * self.channels + step * self.channels + channel), self.dimension, 'B')
                values = tuple(f32(current + f32(f32(q * scale) + offset))
                               for current, q, (_, _, offset, scale) in zip(values, quantized, coefficients))
            result.append(values)
        result.extend(tuple(self.static[i:i + self.dimension]) for i in range(0, len(self.static), self.dimension))
        return tuple(result)

    def interpolated_pose(self, key, weight):
        require(type(key) is int and 0 <= key < self.keys - 1, 'Interpolation needs two vector keys')
        require(type(weight) in (int, float) and math.isfinite(weight) and 0 <= weight <= 1,
                'Vector interpolation weight is outside its interval')
        weight = f32(weight)
        first, second = self.pose(key), self.pose(key + 1)
        return tuple(tuple(f32(a + f32(f32(b - a) * weight)) for a, b in zip(left, right))
                     for left, right in zip(first[:self.channels], second[:self.channels])) + first[self.channels:]

    def sample(self, time):
        """Sample nonnegative child-time ticks, with no caller time transform."""
        require(type(time) in (int, float) and math.isfinite(time) and 0 <= time <= 65535,
                'Vector time exceeds the supported child-time domain')
        time = f32(time)
        key = min(int(time), self.keys - 1) if self.times is None else bisect_right(self.times, int(time))
        if key == self.keys - 1:
            return self.pose(key)
        low = key if self.times is None else (self.times[key - 1] if key else 0)
        high = key + 1 if self.times is None else self.times[key]
        return self.interpolated_pose(key, f32(f32(time - low) / (high - low)))

    def metadata(self):
        return {'kind': self.info['kind'], 'keys': self.keys, 'channels': self.channels, 'constants': self.constants,
                'block_seed_replay_only': True, 'cache_history_validated': False,
                'output_context_validated': False, 'runtime_ready': False}
