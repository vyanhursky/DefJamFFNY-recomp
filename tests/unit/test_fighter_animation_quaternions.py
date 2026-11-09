"""Invented type18 channels: independent seed endpoints and replay boundaries."""
import pytest

from test_fighter_animation_curves import curves
from fighter_animation_quaternions import QuaternionCurve, seed
from fighter_assets import AssetError


def test_six_byte_seed_interleaves_four_components():
    assert seed(bytes(6)) == (-1.,) * 4
    assert seed(bytes([255] * 6)) == (1.,) * 4
    assert seed(bytes.fromhex('f0ff00000000')) == (1., -1., -1., -1.)
    assert seed(bytes.fromhex('0f000f000f00')) == (-1., -1., -1., 1.)


def test_forward_replay_preserves_unnormalized_components_and_static_channels():
    decoder = QuaternionCurve(curves(18), 56)
    assert decoder.pose(0) == ((-1.,) * 4, (-1.,) * 4)
    assert decoder.pose(1) == ((-2.,) * 4, (-1.,) * 4)
    assert decoder.pose(2) == ((-3.,) * 4, (-1.,) * 4)
    assert decoder.interpolated_pose(0, .25) == ((-1.25,) * 4, (-1.,) * 4)
    assert not decoder.metadata()['runtime_ready']


def test_second_block_restarts_seed_and_respects_alignment():
    def authored(data, pointers, record):
        data[record + 7] = 0  # no constant channels
        data[record + 16] = 1  # two keys per block, 9 bytes rounded to10
        data[100:106] = bytes([255] * 6)
    decoder = QuaternionCurve(curves(18, authored), 56)
    assert decoder.pose(1) == ((-2.,) * 4,)
    assert decoder.pose(2) == ((1.,) * 4,)
    assert decoder.interpolated_pose(1, .5) == ((-.5,) * 4,)


@pytest.mark.parametrize('key', [-1, 3, True, 1.5])
def test_invalid_keys_fail_before_reads(key):
    with pytest.raises(AssetError, match='key'):
        QuaternionCurve(curves(18), 56).pose(key)


@pytest.mark.parametrize('weight', [-.1, 1.1, float('nan'), float('inf'), True])
def test_invalid_interpolation_weights(weight):
    with pytest.raises(AssetError, match='weight'):
        QuaternionCurve(curves(18), 56).interpolated_pose(0, weight)


def test_work_budget_and_type_are_independent_gates():
    with pytest.raises(AssetError, match='budget'):
        QuaternionCurve(curves(18), 56, work_budget=23)
    with pytest.raises(AssetError, match='record type'):
        QuaternionCurve(curves(19), 56)


def test_timed_sampling_and_element_destinations_preserve_static_channels():
    import struct
    def change(data, pointers, record):
        struct.pack_into('<2H', data, 208, 2, 5)
    decoder = QuaternionCurve(curves(18, change), 56)
    assert decoder.destinations == (2, 4)
    assert decoder.sample(0) == decoder.pose(0)
    assert decoder.sample(1) == decoder.interpolated_pose(0, .5)
    assert decoder.sample(2) == decoder.pose(1)
    assert decoder.sample(3.5) == decoder.interpolated_pose(1, .5)
    assert decoder.sample(5) == decoder.sample(65535) == decoder.pose(2)


def test_implicit_time_uses_key_ticks():
    import struct
    def change(data, pointers, record):
        pointers.remove(record + 8)
        struct.pack_into('<I', data, record + 8, 0)
    decoder = QuaternionCurve(curves(18, change), 56)
    assert decoder.times is None
    assert decoder.sample(.25) == decoder.interpolated_pose(0, .25)
    assert decoder.sample(1) == decoder.pose(1)
    assert decoder.sample(65535) == decoder.pose(2)


@pytest.mark.parametrize('time', [-1, 65536, True, float('inf'), float('nan'), '1'])
def test_sampling_rejects_invalid_time_before_reads(time):
    with pytest.raises(AssetError, match='time'):
        QuaternionCurve(curves(18), 56).sample(time)
