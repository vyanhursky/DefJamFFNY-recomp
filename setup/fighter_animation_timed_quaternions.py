"""Type13 timed quaternion reading, separate from native resource admission.

The unfiltered ED300 path copies exact keys and normalizes only interpolated
poses. Its EA010 blend selects the quaternion sign, unlike type18's linear
four-scalar interpolation. Keep floating-point precision an explicit input.
"""
from bisect import bisect_right
import math

from fighter_animation import require
from fighter_animation_scalars import ScalarCurve, f32


def round24(value):
    """x87's 24-bit significand retains its extended exponent range."""
    if value == 0:
        return value
    mantissa, exponent = math.frexp(value)
    return math.ldexp(f32(mantissa), exponent)


def blend(first, second, weight, *, precision_bits):
    require(precision_bits in (24, 53) and type(precision_bits) is int,
            'Type13 requires explicit 24- or 53-bit x87 precision')
    require(len(first) == len(second) == 4
            and all(type(v) in (int, float) and math.isfinite(v) for v in (*first, *second))
            and type(weight) in (int, float) and math.isfinite(weight) and 0 <= weight <= 1,
            'Type13 blend requires finite quaternion components and interval weight')
    a, b, w = tuple(map(f32, first)), tuple(map(f32, second)), f32(weight)
    products = [f32(x * y) for x, y in zip(a, b)]
    dot = f32(f32(f32(products[0] + products[2]) + products[1]) + products[3])
    values = (tuple(f32(x + f32(f32(y - x) * w)) for x, y in zip(a, b)) if dot > 0
              else tuple(f32(x - f32(f32(x + y) * w)) for x, y in zip(a, b)))
    rounding = round24 if precision_bits == 24 else float
    squares = [rounding(v * v) for v in values]
    norm = rounding(rounding(rounding(squares[2] + squares[3]) + squares[0]) + squares[1])
    require(math.isfinite(norm) and norm > 0, 'Type13 interpolation has a degenerate quaternion')
    reciprocal = rounding(1.0 / rounding(math.sqrt(norm)))
    return tuple(f32(rounding(v * reciprocal)) for v in values)


class TimedQuaternionCurve:
    def __init__(self, layouts, record, *, work_budget=16 * 1024**2):
        self.scalar = ScalarCurve(layouts, record, work_budget=work_budget)
        require(self.scalar.info['kind'] == 13, 'Timed quaternion decoder requires type13')
        # Native FC3F0's four-bit subset offset is in bytes. For multiple groups
        # it can read beyond the nominal packed extent; never infer safe reads
        # from the full-channel decoder's successful inspection.
        require(self.scalar.bits != 4 or self.scalar.scalars == 4,
                'Multi-quaternion four-bit interpolation needs a separate span adapter')
        self.times = layouts.times(record + 8, self.scalar.keys, transitions=True)
        self.destinations = layouts.values(record + 14, self.scalar.scalars // 4)

    def sample(self, time, *, precision_bits):
        require(type(time) in (int, float) and math.isfinite(time) and 0 <= time <= 65535,
                'Timed quaternion time exceeds the supported child-time domain')
        require(type(precision_bits) is int and precision_bits in (24, 53),
                'Type13 requires explicit 24- or 53-bit x87 precision')
        time = f32(time)
        key = bisect_right(self.times, int(time))
        poses = self.scalar.poses()
        for _ in range(key + 1):
            first = next(poses)
        low = self.times[key - 1] if key else 0
        if time == low or key == self.scalar.keys - 1:
            return tuple(first[i:i + 4] for i in range(0, len(first), 4))
        second = next(poses)
        weight = f32(f32(time - low) / (self.times[key] - low))
        return tuple(blend(first[i:i + 4], second[i:i + 4], weight, precision_bits=precision_bits)
                     for i in range(0, len(first), 4))

    def metadata(self):
        return {'kind': 13, 'keys': self.scalar.keys, 'scalars': self.scalar.scalars,
                'bits': self.scalar.bits, 'explicit_x87_precision': True,
                'filtered_evaluation_validated': False, 'output_context_validated': False,
                'runtime_ready': False}
