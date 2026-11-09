"""Invented quaternion keys cover sign, normalization and time boundaries."""
import math
import struct

import pytest

from test_fighter_animation_curves import curves
from fighter_animation_timed_quaternions import TimedQuaternionCurve, blend, round24
from fighter_assets import AssetError


def timed_fixture(groups=1, bits=8, change=None):
    def authored(data, pointers, record):
        data.extend(bytes(2048 - len(data)))
        struct.pack_into('<II', data, 60, 300, 1800)
        struct.pack_into('<' + 'H'*groups, data, 70, *(4 + 8*i for i in range(groups)))
        struct.pack_into('<HBB', data, 300, groups*4, bits, 0)
        struct.pack_into('<' + 'f'*(groups*12), data, 304, *([0., .001, 2.] * (groups*4)))
        struct.pack_into('<2H', data, 1800, 2, 5)
        if change:
            change(data, groups, bits)
    return curves(13, authored)


def test_multi_group_nibble_offsets_are_rejected_but_byte_groups_are_independent():
    with pytest.raises(AssetError, match='four-bit interpolation'):
        TimedQuaternionCurve(timed_fixture(groups=2, bits=4), 56)
    for bits in (8, 16):
        decoder = TimedQuaternionCurve(timed_fixture(groups=3, bits=bits), 56)
        assert decoder.destinations == (4, 12, 20)
        assert decoder.sample(.5, precision_bits=24) == ((.5,)*4,)*3


@pytest.mark.parametrize('precision', [24, 53])
def test_sign_choice_normalization_and_zero_dot(precision):
    assert blend((0, 0, 0, 2), (0, 0, 0, -3), .5, precision_bits=precision) == (0, 0, 0, 1)
    value = blend((2, 0, 0, 0), (0, 3, 0, 0), .5, precision_bits=precision)
    assert value[0] > 0 and value[1] < 0  # Zero dot selects the negative sign.
    assert sum(v*v for v in value) == pytest.approx(1, abs=3e-7)
    with pytest.raises(AssetError, match='degenerate'):
        blend((0,)*4, (0,)*4, .5, precision_bits=precision)


@pytest.mark.parametrize('bits', [4, 8, 16])
@pytest.mark.parametrize('precision', [24, 53])
def test_exact_keys_keep_nonunit_values_but_intermediate_times_normalize(bits, precision):
    def authored(data, pointers, record):
        struct.pack_into('<HBB12f', data, 100, 4, bits, 0, *([0, 0, 2.] * 4))
        data[152:152 + bits] = bytes(bits)
        struct.pack_into('<2H', data, 208, 2, 5)
        struct.pack_into('<I', data, 64, 208)
    decoder = TimedQuaternionCurve(curves(13, authored), 56)
    for time in (0, 2, 5, 65535):
        assert decoder.sample(time, precision_bits=precision) == ((2.,)*4,)
    for time in (.5, 1.999, 2.25, 4.999):
        assert decoder.sample(time, precision_bits=precision) == ((.5,)*4,)
    assert not decoder.metadata()['runtime_ready']


def test_extended_exponent_and_invalid_precision_time():
    assert round24(2.0**200) == 2.0**200
    assert round24(2.0**-200) == 2.0**-200
    decoder = TimedQuaternionCurve(curves(13), 56)
    for time, precision in ((-1, 24), (math.nan, 24), (65536, 24), (1, 64), (1, True)):
        with pytest.raises(AssetError):
            decoder.sample(time, precision_bits=precision)
    with pytest.raises(AssetError, match='requires type13'):
        TimedQuaternionCurve(curves(11), 56)
