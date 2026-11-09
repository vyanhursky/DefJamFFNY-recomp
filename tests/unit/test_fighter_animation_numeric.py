"""Lossless block reconstruction and independent numeric replay checks."""
import copy
import struct

import pytest

from test_fighter_animation_curves import curves
from test_fighter_animation_vectors import vector_fixture
from fighter_animation import AnimationEnvelope, AnimationIndex
from fighter_animation_compile import rebuild
from fighter_animation_curves import CurveLayouts
from fighter_animation_graphs import Writer
from fighter_animation_numeric import read_numeric, validate_numeric, write_numeric
from fighter_animation_quaternions import QuaternionCurve
from fighter_animation_vectors import VectorCurve
from fighter_assets import AssetError


def reconstruct(layout):
    value = read_numeric(layout, 56)
    section = layout.model.sections[1]
    payload = bytearray(layout.model.data[section[4]:section[4] + section[5]])
    pointers = {at: layout.model.local_pointer(at,1) for at in layout.model.pointers}
    writer = Writer(payload, pointers)
    record = write_numeric(writer, value, 0, 1128)
    writer.pointer(52, record)
    data, links = rebuild(layout.model, payload, pointers)
    result = CurveLayouts(AnimationIndex(AnimationEnvelope(data, links)))
    return value, result, record


@pytest.mark.parametrize('kind', [20, 21])
@pytest.mark.parametrize('shift,keys,channels,constants,timed', [
    (0, 3, 1, 1, True), (1, 3, 1, 1, False), (3, 9, 1, 1, False),
    (3, 3, 0, 1, False), (3, 1, 1, 0, False)])
def test_typed_blocks_rebuild_numeric_values(kind, shift, keys, channels, constants, timed):
    layout = vector_fixture(kind=kind, shift=shift, keys=keys, channels=channels,
                            constants=constants, timed=timed)
    value, result, record = reconstruct(layout)
    assert read_numeric(result, record) == value
    codec = QuaternionCurve if kind == 18 else VectorCurve
    original, rebuilt = codec(layout, 56), codec(result, record)
    assert original.destinations == rebuilt.destinations
    for key in range(original.keys):
        assert original.pose(key) == rebuilt.pose(key)
    for time in [0, .25, 1, 2.5, 65535]:
        assert original.sample(time) == rebuilt.sample(time)


def test_quaternion_static_and_partial_block_roundtrip():
    value, result, record = reconstruct(curves(18))
    assert read_numeric(result, record) == value
    original, rebuilt = QuaternionCurve(curves(18),56), QuaternionCurve(result,record)
    for time in [0, .25, 1, 2, 65535]:
        assert original.sample(time) == rebuilt.sample(time)


@pytest.mark.parametrize('shift,keys,channels', [(0,3,2),(1,5,1),(3,9,1),(3,3,0)])
def test_quaternion_full_and_partial_blocks_keep_quantized_bits(shift,keys,channels):
    layout = curves(18)
    value = read_numeric(layout,56)
    value.update(keys=keys, block_shift=shift, destinations=list(range(channels)),
                 constant_destinations=[4], coefficients=[[32768]*8 for _ in range(channels)],
                 static=[[2048,2048,2048,4095]], times=None)
    width = 1 << shift
    value['blocks'] = [{'seeds': [[2048,2000,2100,4095] for _ in range(channels)],
                        'deltas': [[[32,33,31,32] for _ in range(channels)]
                                   for _ in range(min(width,keys-key)-1)]}
                       for key in range(0,keys,width)]
    payload, pointers = bytearray(24), {}
    writer = Writer(payload,pointers)
    record = write_numeric(writer,value,0,1128)
    # Reuse only the invented envelope; fresh bank tables reference the new curve.
    records, names = writer.append(bytes(4)), writer.append(bytes(4))
    name = writer.append(b'A_s\0')
    struct.pack_into('<6I',payload,0,0,1,0,0,records,names)
    for field,target in [(16,records),(20,names),(records,record),(names,name)]:
        writer.pointer(field,target)
    data,links = rebuild(layout.model,payload,pointers)
    result = CurveLayouts(AnimationIndex(AnimationEnvelope(data,links)))
    assert read_numeric(result,record) == value
    decoded = QuaternionCurve(result,record)
    assert decoded.pose(0)[-1] == (0.0002442598342895508,)*3 + (1.0,)
    assert decoded.keys == keys and decoded.channels == channels


def test_nonzero_unused_vector_bytes_are_preserved():
    def change(data, record, start):
        data[record+18:record+20] = bytes([234, 19])
    value, result, record = reconstruct(vector_fixture(change=change))
    assert value['unused_header'] == [234,19]
    assert read_numeric(result,record)['unused_header'] == [234,19]


@pytest.mark.parametrize('change', [
    lambda v: v.update(kind=True), lambda v: v.update(block_shift=9),
    lambda v: v['constant_destinations'].__setitem__(0, v['destinations'][0]),
    lambda v: v['destinations'].__setitem__(0, 1128),
    lambda v: v['blocks'][0]['seeds'][0].__setitem__(0, 65536),
    lambda v: v['blocks'][0]['deltas'][0][0].__setitem__(0, 256),
    lambda v: v['coefficients'][0]['base'].__setitem__(0, float('nan')),
    lambda v: v.update(times=[2,2]), lambda v: v.update(pointer=123),
])
def test_invalid_numeric_documents_fail_before_writing(change):
    value = copy.deepcopy(read_numeric(vector_fixture(),56))
    change(value)
    with pytest.raises(AssetError):
        validate_numeric(value,1128)
