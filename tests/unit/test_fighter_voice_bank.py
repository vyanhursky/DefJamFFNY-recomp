"""Invented event metadata and owned PCM; no retail audio in fixtures."""
import hashlib
import struct

import pytest

from test_fighter_voice import encode_stream
from fighter_assets import AssetError
from fighter_voice_bank import VoiceBankTemplate


def hashes(*values):
    return [hashlib.sha256(v).hexdigest() for v in values]


def template():
    streams = [encode_stream(struct.pack('<h', n), 24000) for n in (-10, 20, 30)]
    data = b''.join(s + bytes(256 - len(s)) for s in streams)
    h = bytearray(44)
    struct.pack_into('<2H4B2H', h, 0, 16625, 22, 2, 3, 3, 0, 3, 2)
    for n in range(3):
        struct.pack_into('>H2B', h, 12 + n * 4, n, n, 0)
    struct.pack_into('<2I', h, 24, 7, 1)
    h[32:36] = bytes((0, 255, 255, 255))  # recent-selection cursor/history
    h[36] = 0x3F  # two request rows, three entries each
    return bytes(h), data


def load(header, data):
    return VoiceBankTemplate(header, data, *hashes(header, data))


def test_rekey_and_replace_keep_event_contract_and_fallback_samples():
    h, d = template()
    source = load(h, d)
    replacement = encode_stream(struct.pack('<300h', *range(300)), 48000)
    ch, cd, report = source.compose(600, {1: replacement})
    result = load(ch, cd)
    assert result.voice_key == 600 and result.first_key == 16625
    assert result.streams == (source.streams[0], replacement, source.streams[2])
    assert ch[24:] == h[24:] and report['authored_entries'] == [1]
    for n in range(3):
        assert ch[14 + n * 4:16 + n * 4] == h[14 + n * 4:16 + n * 4]
    assert source.header == h and source.data == d and not report['runtime_ready']


def test_two_packs_get_independent_keys_without_mutating_donor():
    source = load(*template())
    a = source.compose(600, {})
    b = source.compose(601, {0: encode_stream(b'\x01\x00', 8000)})
    assert load(*a[:2]).voice_key == 600 and load(*b[:2]).voice_key == 601
    assert a[0][2:4] != b[0][2:4] and source.voice_key == 22


@pytest.mark.parametrize('key,replacements', [
    (-1, {}), (65535, {}), (True, {}), (600, []), (600, {3: b''}),
    (600, {True: b''}), (600, {0: b'SCHl'}),
])
def test_invalid_registration_or_replacement(key, replacements):
    with pytest.raises(AssetError):
        load(*template()).compose(key, replacements)


@pytest.mark.parametrize('offset,value', [(5, 0), (12, 1), (17, 0), (8, 0),
                                         (6, 255), (10, 255), (11, 255)])
def test_bad_header_dimensions_and_offsets(offset, value):
    header, data = template()
    h = bytearray(header)
    h[offset] = value
    assert bytes(h) != header
    with pytest.raises(AssetError):
        load(bytes(h), data)


def test_invalid_padding_and_template_digest():
    h, d = template()
    with pytest.raises(AssetError, match='verified'):
        VoiceBankTemplate(h, d, '0' * 64, hashes(d)[0])
    with pytest.raises(AssetError, match='padding'):
        load(h, d[:-1] + b'\1')
    with pytest.raises(AssetError, match='history'):
        load(h[:32], d)


def test_offset_units_expand_without_changing_samples():
    source = load(*template())
    # Three 6MB authored entries cross the original 16-bit/256-byte envelope.
    voice = encode_stream(bytes(6_000_000), 24000)
    header, data, _ = source.compose(600, dict.fromkeys(range(3), voice))
    assert header[7] == 1  # 512-byte units, not a truncated 16-bit offset
    assert load(header, data).streams == (voice,) * 3
