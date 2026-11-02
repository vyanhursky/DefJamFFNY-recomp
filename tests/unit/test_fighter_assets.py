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
