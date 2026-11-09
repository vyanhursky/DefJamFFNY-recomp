"""Invented type20 data exercises block layout, timing and numeric boundaries."""
import struct

import pytest

from test_fighter_animation_curves import curves
from fighter_animation_vectors import VectorCurve
from fighter_assets import AssetError


def vector_fixture(*, channels=1, constants=1, keys=3, shift=3, timed=True, change=None, kind=20):
    dimension = 3 if kind == 20 else 1
    def authored(data, pointers, record):
        data.extend(bytes(4096 - len(data)))
        data[4000:4008] = data[240:248]
        struct.pack_into('<2I', data, 32, 4000, 4004)
        data[56:3900] = bytes(3900 - 56)
        struct.pack_into('<HHIIHH4B', data, record, kind, 0, 3900, 3950 if timed else 0,
                         keys, channels, shift, constants, 0, 0)
        if not timed:
            pointers.remove(record + 8)
        elif keys > 1:
            struct.pack_into('<' + 'H' * (keys - 1), data, 3950, *(2 * (i + 1) for i in range(keys - 1)))
        struct.pack_into('<' + 'H' * channels, data, 3900, *(12 * i for i in range(channels)))
        for c in range(channels):
            struct.pack_into('<' + 'f' * (dimension * 2) + 'H' * (dimension * 2), data,
                             record + 20 + 12 * dimension * c,
                             *((10., 20., 30.)[:dimension]), *([1.] * dimension), *([0] * (dimension * 2)))
        width = 1 << shift
        start = record + 20 + 12 * dimension * channels
        end = start + (keys // width) * ((dimension * channels * (width + 1) + 1) & ~1)
        if keys % width:
            end = (end + dimension * channels * (keys % width + 1) + 1) & ~1
        end = (end + 1) & ~1
        struct.pack_into('<' + 'H' * constants, data, end, *(12 * channels for _ in range(constants)))
        struct.pack_into('<' + 'f' * (dimension * constants), data, (end + 2 * constants + 3) & ~3,
                         *((3., 4., 5.)[:dimension] * constants))
        if change:
            change(data, record, start)
    return curves(kind, authored)


def test_vector_seed_delta_timing_and_constant_channels():
    decoder = VectorCurve(vector_fixture(), 56)
    assert decoder.destinations == (0, 12)
    assert decoder.pose(0) == ((10., 20., 30.), (3., 4., 5.))
    assert decoder.pose(2) == ((8., 18., 28.), (3., 4., 5.))
    assert decoder.sample(1) == ((9.5, 19.5, 29.5), (3., 4., 5.))
    assert decoder.sample(2) == decoder.pose(1)
    assert decoder.sample(65535) == decoder.pose(2)
    assert not decoder.metadata()['runtime_ready']


def test_block_reset_and_odd_byte_alignment():
    def change(data, record, start):
        struct.pack_into('<3H', data, start + 10, 65535, 65535, 65535)
    decoder = VectorCurve(vector_fixture(shift=1, change=change), 56)
    assert decoder.pose(1)[0] == (9., 19., 29.)
    assert decoder.pose(2)[0] == (11., 21., 31.)
    assert decoder.interpolated_pose(1, .25)[0] == (9.5, 19.5, 29.5)


def test_untimed_single_key_and_static_only_records():
    one = VectorCurve(vector_fixture(keys=1, timed=False), 56)
    assert one.sample(.5) == one.sample(100) == one.pose(0)
    static = VectorCurve(vector_fixture(channels=0), 56)
    assert static.pose(2) == static.sample(.5) == ((3., 4., 5.),)
    untimed = VectorCurve(vector_fixture(timed=False), 56)
    assert untimed.sample(.5)[0] == (9.5, 19.5, 29.5)


@pytest.mark.parametrize('key', [-1, 3, True, .5])
def test_key_bounds(key):
    with pytest.raises(AssetError, match='key'):
        VectorCurve(vector_fixture(), 56).pose(key)


@pytest.mark.parametrize('time', [-1, 65536, True, float('nan'), float('inf')])
def test_time_bounds(time):
    with pytest.raises(AssetError, match='time'):
        VectorCurve(vector_fixture(), 56).sample(time)


def test_work_and_numeric_overflow_fail_before_native_loading():
    with pytest.raises(AssetError, match='budget'):
        VectorCurve(vector_fixture(), 56, work_budget=17)
    with pytest.raises(AssetError, match='record type'):
        VectorCurve(curves(18), 56)
    def change(data, record, start):
        struct.pack_into('<f', data, record + 32, 3e38)
        struct.pack_into('<H', data, record + 44, 65535)
    with pytest.raises(ValueError, match='float32'):
        VectorCurve(vector_fixture(change=change), 56)


def test_single_component_curve_uses_two_byte_seeds_one_byte_deltas():
    def change(data, record, start):
        struct.pack_into('<H', data, start + 4, 65535)
    decoder = VectorCurve(vector_fixture(kind=21, shift=1, change=change), 56)
    assert decoder.destinations == (0, 12)
    assert decoder.pose(0) == ((10.,), (3.,))
    assert decoder.pose(1) == ((9.,), (3.,))
    assert decoder.pose(2) == ((11.,), (3.,))
    assert decoder.sample(3) == ((10.,), (3.,))
    assert decoder.metadata()['kind'] == 21
