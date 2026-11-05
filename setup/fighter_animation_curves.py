"""Bounded inspection of established curve layouts; never runtime admission.

Lengths and references follow the native consumers documented in the animation
audits. Numerical decoding, output-context compatibility and ownership of
overlapping serialized spans are independent gates.
"""
from bisect import bisect_left
import math
import struct

from fighter_animation import AnimationIndex, require


class CurveLayouts:
    SUPPORTED = {13, 20, 21, 25}

    def __init__(self, index):
        require(type(index) is AnimationIndex, 'Expected a validated animation index')
        self.index, self.model = index, index.model
        self.relocations = sorted(self.model.pointers)
        self.records = {offset: self.inspect(offset, kind) for offset, kind in index.record_types.items()
                        if kind in self.SUPPORTED}

    def numeric(self, offset, size):
        at = self.model.data_range(offset, size)
        position = bisect_left(self.relocations, max(0, offset - 3))
        require(position == len(self.relocations) or self.relocations[position] >= offset + size or not size,
                'Curve numeric data contains a pointer relocation')
        return at

    def values(self, offset, count, kind='H'):
        size = struct.calcsize('<' + kind)
        at = self.numeric(offset, count * size)
        values = self.model.unpack('<' + kind * count, at)
        if kind == 'f':
            require(all(math.isfinite(value) for value in values), 'Curve contains non-finite scalars')
        return values

    def pointer(self, field, size):
        return self.model.local_pointer(field, size)

    def times(self, field, keys, *, transitions=False, optional=False):
        if optional and field not in self.model.pointers:
            require(self.values(field, 1, 'I') == (0,), 'Curve time field needs a local relocation or zero')
            return None
        count = keys - 1 if transitions else keys
        require(count > 0, 'Timed curve has too few keys')
        values = self.values(self.pointer(field, count * 2), count)
        require(all(a < b for a, b in zip(values, values[1:])), 'Curve times must strictly increase in the supported profile')
        if transitions:
            require(values[0] > 0 and values[-1] < 65535, 'Curve transition time would collapse or wrap its duration')
        return values

    def inspect(self, record, kind):
        self.values(record, 2)
        if kind == 25:
            require(self.values(record - 20, 5, 'I') == (0, 0, 25, 0, 0),
                    'Curve embedded wrapper must have the inert type25 seed')
            keys = self.values(record + 4, 1)[0]
            selector = self.values(record + 6, 2, 'B')[0]
            require(keys > 0, 'Curve has no keys')
            samples = self.values(self.pointer(record + 8, keys), keys, 'B')
            self.times(record + 12, keys)
            return {'kind': kind, 'keys': keys, 'sample_bank_selector': selector,
                    'required_samples': max(samples) + 1, 'external_context_required': True}
        if kind == 13:
            keys = self.values(record + 12, 1)[0]
            descriptor = self.pointer(record + 4, 4)
            scalars = self.values(descriptor, 1)[0]
            bits = self.values(descriptor + 2, 2, 'B')[0]
            require(keys >= 2 and scalars > 0 and scalars % 4 == 0 and bits in (4, 8, 16),
                    'Unsupported compressed four-scalar curve layout')
            self.values(descriptor + 4, scalars * 3, 'f')
            packed = descriptor + 4 + scalars * 12
            self.numeric(packed, (keys - 1) * ((scalars * bits + 7) // 8))
            self.times(record + 8, keys, transitions=True)
            destinations = self.values(record + 14, scalars // 4)
            return {'kind': kind, 'keys': keys, 'scalars': scalars, 'bits': bits,
                    'required_output_floats': max(destinations) + 4}
        keys, channels = self.values(record + 12, 2)
        shift, constants, _, _ = self.values(record + 16, 4, 'B')
        require(keys > 0 and shift <= 8, 'Curve key count or block shift exceeds the supported profile')
        dimension, stride = (3, 36) if kind == 20 else (1, 12)
        destinations = self.values(self.pointer(record + 4, channels * 2), channels) if channels else ()
        if not channels:
            require(record + 4 not in self.model.pointers and self.values(record + 4, 1, 'I') == (0,),
                    'Empty curve destination table needs a zero field')
        self.times(record + 8, keys, transitions=True, optional=True)
        for channel in range(channels):
            offset = record + 20 + stride * channel
            self.values(offset, dimension * 2, 'f')
            self.values(offset + dimension * 8, dimension * 2)
        packed = record + 20 + stride * channels
        width = 1 << shift
        block = (dimension * channels * (width + 1) + 1) & ~1
        end = packed + (keys >> shift) * block
        remainder = keys & (width - 1)
        if remainder:
            end = (end + dimension * channels * (remainder + 1) + 1) & ~1
        if not channels:
            end = (end + 1) & ~1
        self.numeric(packed, end - packed)
        destinations += self.values(end, constants)
        self.values((end + constants * 2 + 3) & ~3, dimension * constants, 'f')
        return {'kind': kind, 'keys': keys, 'channels': channels, 'constants': constants, 'block_shift': shift,
                'required_output_floats': max(destinations) + dimension if destinations else 0}

    def metadata(self):
        return {'inspected_records': len(self.records),
                'uninspected_records': sum(kind not in self.SUPPORTED and kind != 15
                                          for kind in self.index.record_types.values()),
                'supported_layout_types': sorted(self.SUPPORTED),
                'numerical_decoder_validated': False, 'output_context_validated': False,
                'exclusive_span_ownership_validated': False, 'runtime_ready': False}
