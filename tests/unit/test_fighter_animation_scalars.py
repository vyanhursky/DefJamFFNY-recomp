"""Scalar codec examples independent of packed-file ownership validation."""
import struct

import pytest

from test_fighter_animation_curves import curves
from fighter_animation_scalars import ScalarCurve
from fighter_assets import AssetError


@pytest.mark.parametrize('kind', [11, 13])
@pytest.mark.parametrize('bits', [4, 8, 16])
def test_unsigned_deltas_low_nibble_first_and_replay(kind, bits):
    def authored(data, pointers, record):
        struct.pack_into('<HBB12f', data, 100, 4, bits, 0, *([-.5, .25, 1.] * 4))
        quantized = [0, 1, 2, 15, 3, 2, 1, 0]
        if bits == 4:
            packed = bytes(a | b << 4 for a, b in zip(quantized[::2], quantized[1::2]))
        elif bits == 8:
            packed = bytes(quantized)
        else:
            packed = struct.pack('<8H', *quantized)
        data[152:152 + len(packed)] = packed
        if kind == 13:
            struct.pack_into('<I', data, 64, 208)
            struct.pack_into('<2H', data, 208, 1, 2)
    decoder = ScalarCurve(curves(kind, authored), 56)
    expected = [(1., 1., 1., 1.), (.5, .75, 1., 4.25), (.75, .75, .75, 3.75)]
    assert list(decoder.poses()) == expected == list(decoder.poses())
    assert not decoder.metadata()['runtime_ready']


@pytest.mark.parametrize('bits', [4, 8, 16])
def test_float32_lane_order_is_observable_and_preserved(bits):
    def authored(data, pointers, record):
        data[102] = bits
        struct.pack_into('<12f', data, 104, *([-16777216., 16777216., 1.] * 4))
        packed = bytes([0x11] * 4) if bits == 4 else bytes([1] * 8) if bits == 8 else struct.pack('<8H', *([1] * 8))
        data[152:152 + len(packed)] = packed
    poses = list(ScalarCurve(curves(11, authored), 56).poses())
    assert poses[1] == ((0., 0., 0., 0.) if bits == 4 else (0., 1., 1., 1.))


def test_overflow_and_resource_exhaustion_fail_without_native_loading():
    with pytest.raises(AssetError, match='work budget'):
        ScalarCurve(curves(11), 56, work_budget=1)
    def authored(data, pointers, record):
        struct.pack_into('<f', data, 108, 3e38)
        data[152] = 255
    with pytest.raises(ValueError, match='float32'):
        list(ScalarCurve(curves(11, authored), 56).poses())
    with pytest.raises(AssetError, match='record type'):
        ScalarCurve(curves(25), 160)
