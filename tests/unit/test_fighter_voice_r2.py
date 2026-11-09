"""Invented predictive/literal R2 blocks; no source recordings."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_assets import AssetError
from fighter_voice import chunk, property_value
from fighter_voice_r2 import inspect_source, canonical_r2, parse_r2, packet_blocks


def source(counts=(28, 25), blocks=None):
    count = sum(counts)
    header = b'PT\x07\0\x06\x01\x65\xfd\x80\x01\x03'
    header += property_value(0x85, count) + b'\xa0\x01\x0a\x8c\x01\x24\xff'
    parts = [chunk(b'SCHl', header), chunk(b'SCCl', struct.pack('<I', len(counts)))]
    for i, count in enumerate(counts):
        coded = blocks[i] if blocks else b'\x0c' + bytes(range(14))
        coded += bytes((-len(coded)) % 4)
        parts.append(chunk(b'SCDl', struct.pack('<II', count, 0) + coded))
    return b''.join(parts) + chunk(b'SCEl', b'')


def test_canonical_rebuild_preserves_coded_values_counts_and_packet_history():
    data = source()
    before = inspect_source(data)
    after = parse_r2(canonical_r2(data))
    assert after.packets == before.packets and after.sample_count == 53
    assert after.sample_rate == 24000 and after.packet_count == 2
    assert canonical_r2(canonical_r2(data)) == canonical_r2(data)
    assert after.metadata()['native_codec'] == 10 and not after.metadata()['runtime_ready']
    with pytest.raises(AssetError, match='canonical header'):
        parse_r2(data)


def test_literal_blocks_keep_big_endian_histories_and_all_tail_samples():
    literal = b'\xee' + struct.pack('>30h', -32768, 32767, *range(-14, 14))
    decoded = inspect_source(source((1,), [literal]))
    assert decoded.packets == ((1, literal),)
    assert parse_r2(canonical_r2(source((1,), [literal]))).packets == decoded.packets


@pytest.mark.parametrize('selector', [0x40, 0x80, 0xE0, 0xEF, 0xFF])
def test_predictor_cannot_index_beyond_native_coefficient_table(selector):
    with pytest.raises(AssetError, match='predictor'):
        packet_blocks(bytes([selector]) + bytes(14), 28)


@pytest.mark.parametrize('data,count', [(bytes(14), 28), (b'\xee' + bytes(59), 28),
    (bytes(15) + b'\x01', 28), (bytes(19), 28), (bytes(15), 29), (bytes(15), 0),
    (bytes(15), 16385)])
def test_block_spans_and_zero_padding_are_bounded(data, count):
    with pytest.raises(AssetError):
        packet_blocks(data, count)


def test_all_truncations_unknown_properties_and_nonfinal_partial_packets_fail():
    data = source()
    for size in range(len(data)):
        with pytest.raises(AssetError):
            inspect_source(data[:size])
    for before, after in [(b'\x8c\x01\x24', b'\x8d\x01\x24'),
                          (b'\x80\x01\x03', b'\x80\x01\x02'),
                          (b'\x06\x01\x65', b'\x06\x01\x64')]:
        with pytest.raises(AssetError):
            inspect_source(data.replace(before, after))
    with pytest.raises(AssetError, match='Non-final partial'):
        inspect_source(source((25, 28)))
    with pytest.raises(AssetError):
        inspect_source(data + b'\0')


@pytest.mark.parametrize('before,after', [
    (b'\x06\x01\x65\xfd', b'\xfd\x06\x01\x65'),
    (b'\xfd\x80\x01\x03', b'\x80\x01\x03\xfd'),
])
def test_property_sections_cannot_be_reinterpreted_by_canonicalization(before, after):
    with pytest.raises(AssetError, match='header section'):
        canonical_r2(source().replace(before, after))


@pytest.mark.parametrize('encoded', [b'\x80', b'\x80\x00', b'\x80\x00\x00'])
def test_short_sample_counts_follow_native_signed_integer_semantics(encoded):
    data = source()
    header_size, = struct.unpack_from('<I', data, 4)
    changed = bytearray(data.replace(property_value(0x85, 53), bytes((0x85, len(encoded))) + encoded))
    struct.pack_into('<I', changed, 4, header_size + len(encoded) - 4)
    with pytest.raises(AssetError, match='sample budget'):
        inspect_source(bytes(changed))
