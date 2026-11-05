"""Full-channel scalar pose decoding for inspected type11/type13 curves.

This implements the ordinary offset=0,count=S FC3F0 route. Filtered subsets,
time interpolation, output mappings and runtime admission are separate gates.
The native unrolled lanes have different float32 addition orders; preserve them.
"""
import math
import struct

from fighter_animation import require
from fighter_animation_curves import CurveLayouts


def f32(value):
    try:
        result = struct.unpack('<f', struct.pack('<f', value))[0]
    except (OverflowError, struct.error) as error:
        raise ValueError('Animation scalar overflows float32') from error
    require(math.isfinite(result), 'Animation scalar becomes non-finite')
    return result


class ScalarCurve:
    def __init__(self, layouts, record, *, work_budget=16 * 1024**2):
        require(type(layouts) is CurveLayouts and record in layouts.records,
                'Scalar decoder requires an inspected curve')
        self.info = layouts.records[record]
        require(self.info['kind'] in (11, 13), 'Unsupported scalar codec record type')
        self.keys, self.scalars, self.bits = (self.info[key] for key in ('keys', 'scalars', 'bits'))
        require(type(work_budget) is int and 0 < self.keys * self.scalars <= work_budget,
                'Scalar decoding exceeds its work budget')
        descriptor = layouts.pointer(record + 4, 4)
        self.coefficients = tuple(zip(*[iter(layouts.values(descriptor + 4, self.scalars * 3, 'f'))] * 3))
        packed = descriptor + 4 + self.scalars * 12
        self.stride = (self.scalars * self.bits + 7) // 8
        size = (self.keys - 1) * self.stride
        start = layouts.numeric(packed, size)
        self.packed = layouts.model.data[start:start + size]

    def quantized(self, row, scalar):
        require(type(row) is int and 0 <= row < self.keys - 1
                and type(scalar) is int and 0 <= scalar < self.scalars,
                'Scalar delta index is out of range')
        offset = row * self.stride
        if self.bits == 16:
            return struct.unpack_from('<H', self.packed, offset + scalar * 2)[0]
        if self.bits == 8:
            return self.packed[offset + scalar]
        return self.packed[offset + scalar // 2] >> ((scalar & 1) * 4) & 15

    def poses(self):
        """Yield bounded finite full poses; each iteration replays from the base."""
        values = [triple[2] for triple in self.coefficients]
        yield tuple(values)
        for row in range(self.keys - 1):
            for scalar, (offset, scale, _) in enumerate(self.coefficients):
                delta = f32(self.quantized(row, scalar) * scale)
                if self.bits == 4 or scalar % 4 == 0:
                    values[scalar] = f32(f32(delta + values[scalar]) + offset)
                else:
                    values[scalar] = f32(f32(delta + offset) + values[scalar])
            yield tuple(values)

    def metadata(self):
        return {'kind': self.info['kind'], 'keys': self.keys, 'scalars': self.scalars,
                'bits': self.bits, 'full_channels_only': True,
                'interpolation_validated': False, 'output_context_validated': False,
                'runtime_ready': False}
