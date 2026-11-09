"""Invented PCM samples, malformed chunks and native-width boundaries."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_assets import AssetError
from fighter_voice import chunk, encode_stream, parse_stream, property_value, PROPERTIES


def header(**changes):
    values = dict(zip(PROPERTIES, (8, 1, 24000, 3)))
    values.update({int(k): v for k, v in changes.items()})
    return chunk(b'SCHl', b'PT\x07\x00' + b''.join(property_value(k, v)
                 for k, v in values.items()) + b'\xff')


def packet(samples=(-32768, 0, 32767), relative=0):
    return chunk(b'SCDl', struct.pack('<2I', len(samples), relative)
                 + struct.pack('<' + 'h' * len(samples), *samples))


@pytest.mark.parametrize('rate', [8000, 11025, 24000, 32768, 48000])
@pytest.mark.parametrize('packet_samples', [1, 7, 4096, 16384])
def test_signed_samples_survive_packet_boundaries(rate, packet_samples):
    pcm = struct.pack('<9h', -32768, -32767, -1, 0, 1, 127, 128, 32766, 32767)
    result = parse_stream(encode_stream(pcm, rate, packet_samples))
    assert result.pcm16 == pcm
    assert result.sample_count == 9 and result.sample_rate == rate
    assert result.packet_count == (9 + packet_samples - 1) // packet_samples
    assert not result.metadata()['runtime_ready']


def test_optional_count_chunk_and_one_byte_signed_property():
    data = header().replace(property_value(0xA0, 8), bytes((0xA0, 1, 8)))
    data = data[:4] + struct.pack('<I', len(data)) + data[8:]
    assert parse_stream(data + packet() + chunk(b'SCEl', b'')).sample_count == 3


@pytest.mark.parametrize('bad', [
    b'', b'SCHl', chunk(b'SCDl', b''), header(),
    header() + chunk(b'SCEl', b''),
    header() + packet() + chunk(b'SCEl', b'x'),
    header() + packet() + chunk(b'SCEl', b'') + b'\0',
    header() + packet() + chunk(b'SCDl', b''),
    header() + packet() + chunk(b'code', b''),
    header() + header() + packet() + chunk(b'SCEl', b''),
    header() + packet(relative=2) + chunk(b'SCEl', b''),
    header() + packet(()) + chunk(b'SCEl', b''),
    header() + packet((1, 2)) + chunk(b'SCEl', b''),
    header() + packet((1, 2, 3, 4)) + chunk(b'SCEl', b''),
    header() + chunk(b'SCCl', struct.pack('<I', 2)) + packet() + chunk(b'SCEl', b''),
    header() + packet() + chunk(b'SCCl', struct.pack('<I', 1)) + chunk(b'SCEl', b''),
    header(**{'160': 10}) + packet() + chunk(b'SCEl', b''),
    header(**{'130': 2}) + packet() + chunk(b'SCEl', b''),
    header(**{'132': -1}) + packet() + chunk(b'SCEl', b''),
    header(**{'133': 0}) + packet() + chunk(b'SCEl', b''),
])
def test_invalid_stream_is_rejected_before_native_code(bad):
    with pytest.raises(AssetError):
        parse_stream(bad)


@pytest.mark.parametrize('size', [0, 7, 0x1000000, 0xFFFFFFFF])
def test_chunk_length_cannot_wrap_or_become_stream_tag(size):
    data = encode_stream(b'\0\0', 24000)
    with pytest.raises(AssetError, match='length'):
        parse_stream(data[:4] + struct.pack('<I', size) + data[8:])


@pytest.mark.parametrize('pcm,rate,budget', [
    (b'', 24000, 4096), (b'\0', 24000, 4096), (b'\0\0', True, 4096),
    (b'\0\0', 48001, 4096), (b'\0\0', 24000, 0), (b'\0\0', 24000, True),
    (b'\0\0', 24000, 16385),
])
def test_invalid_authoring_arguments(pcm, rate, budget):
    with pytest.raises(AssetError):
        encode_stream(pcm, rate, budget)


def test_all_truncations_and_header_tag_mutations_fail():
    data = encode_stream(b'\x00\x80\xff\x7f', 24000)
    for size in range(len(data)):
        with pytest.raises(AssetError):
            parse_stream(data[:size])
    for offset, value in ((12, 0x81), (18, 0xA0), (13, 255), (36, 0), (11, 1)):
        altered = bytearray(data)
        altered[offset] = value
        with pytest.raises(AssetError):
            parse_stream(bytes(altered))
