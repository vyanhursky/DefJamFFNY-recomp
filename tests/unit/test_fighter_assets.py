"""Bound decompression before passing any asset to native format validators."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_assets import unpack, AssetError


def test_literal_and_overlapping_back_reference():
    assert unpack(b'raw asset') == b'raw asset'
    assert unpack(b'\x10\xfb\x00\x00\x04\xe0ABCD\xfc') == b'ABCD'
    assert unpack(b'\x10\xfb\x00\x00\x08\xe0ABCD\x04\x03\xfc') == b'ABCDABCD'
    assert unpack(b'\x10\xfb\x00\x00\x03\xe0ABCx\xfc') == b'ABC'


@pytest.mark.parametrize('data', [b'', b'\x10\xfb', b'\x10\xfb\xff\xff\xff\xfc',
                                b'\x10\xfb\x00\x00\x04\xe0ABC',
                                b'\x10\xfb\x00\x00\x04\xe0ABCD',
                                b'\x10\xfb\x00\x00\x04\x00\x00\xfc',
                                b'\x10\xfb\x00\x00\x04\xe0ABCD\xe0ABCD\xfc',
                                b'\x10\xfb\x00\x00\x04\xc0\x00'])
def test_refuses_bad_expansion_before_materializing_large_output(data):
    with pytest.raises(AssetError):
        unpack(data, maximum=1024)


@pytest.mark.parametrize('kind,minimum,maximum,far', [(0, 3, 10, 1024), (1, 4, 67, 16384), (2, 5, 1028, 131072)])
def test_back_references_match_bytewise_decoder_at_overlap_and_encoding_boundaries(kind, minimum, maximum, far):
    import random
    rng = random.Random(31337 + kind)
    for length in sorted({minimum, maximum, (minimum + maximum) // 2}):
        for distance in sorted({1, 2, 3, length - 1, length, length + 1, far}):
            distance = min(distance, far)
            seed = bytes(rng.randrange(256) for _ in range((distance + 3) // 4 * 4))
            encoded = bytearray()
            for at in range(0, len(seed), 112):
                literal = seed[at:at + 112]
                encoded.extend(bytes([0xe0 + (len(literal) - 4) // 4]) + literal)
            offset = distance - 1
            if kind == 0:
                encoded.extend(bytes([((offset >> 8) << 5) | ((length - 3) << 2), offset & 255]))
            elif kind == 1:
                encoded.extend(bytes([0x80 | (length - 4), offset >> 8, offset & 255]))
            else:
                encoded.extend(bytes([0xc0 | ((offset >> 16) << 4) | (((length - 5) >> 8) << 2),
                                      (offset >> 8) & 255, offset & 255, (length - 5) & 255]))
            expected = bytearray(seed)
            for _ in range(length):
                expected.append(expected[-distance])
            packed = b'\x10\xfb' + len(expected).to_bytes(3, 'big') + encoded + b'\xfc'
            assert unpack(bytes(packed)) == expected, (kind, length, distance)
