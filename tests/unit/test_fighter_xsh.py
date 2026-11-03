"""Asset ranges and shape references are checked before native texture loading."""
import struct
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_assets import AssetError
from fighter_xsh import Textures


def texture(*, kind=0x7b, width=4, height=4, indirect=False):
    pixels = bytes(width * height * (4 if kind == 0x7d else 1))
    extra = 4 if indirect else 0
    palette = kind == 0x7b
    root = 32
    tail = root + 16 + extra + len(pixels)
    data = bytearray(tail + (24 if palette else 0) + 16)
    data[:4] = b'SHPX'
    struct.pack_into('<II', data, 4, len(data), 1)
    struct.pack_into('<4sI', data, 16, b'TEST', root)
    data[root] = kind
    data[root + 1:root + 4] = (16 + extra + len(pixels)).to_bytes(3, 'little')
    struct.pack_into('<HH', data, root + 4, width, height)
    struct.pack_into('<I', data, root + 12, 0x2000 | (0x1000 if indirect else 0))
    if indirect:
        struct.pack_into('<I', data, root + 16, 20)
    data[root + 16 + extra:tail] = pixels
    if palette:
        data[tail] = 0x2a; data[tail + 1:tail + 4] = (24).to_bytes(3, 'little')
        struct.pack_into('<H', data, tail + 4, 2)
        data[tail + 16:tail + 24] = bytes.fromhex('112233ff445566ff')
        tail += 24
    data[tail] = 0x70
    data[tail + 4:tail + 8] = b'TEST'
    return bytes(data)


@pytest.mark.parametrize('kind,indirect', [(0x7b, False), (0x7b, True), (0x7d, False)])
def test_texture_checks_palette_and_scopes_shape_names_without_touching_pixels(kind, indirect):
    data = texture(kind=kind, indirect=indirect)
    parsed = Textures(data)
    assert parsed.images[0]['width'] == 4 and parsed.images[0]['height'] == 4
    assert parsed.images[0]['palette_entries'] == (2 if kind == 0x7b else 0)
    renamed = parsed.renamed({'TEST': 'A123'})
    assert Textures(renamed).images[0]['name'] == 'A123'
    sites = {position + offset for position in parsed.name_sites['TEST'] for offset in range(4)}
    assert all(a == b for index, (a, b) in enumerate(zip(data, renamed)) if index not in sites)
    assert parsed.renamed({}) == data and not parsed.metadata()['runtime_ready']
    for mapping in ({'OTHER': 'A123'}, {'TEST': '../x'}, {'TEST': 'é123'}):
        with pytest.raises(AssetError):
            parsed.renamed(mapping)


def test_texture_rejects_bounds_aliases_unsupported_flags_and_invalid_palette_indices():
    original = texture()
    cases = [b'', original[:-1], original.replace(b'SHPX', b'ELF!', 1)]
    for position, format, value in [(8, '<I', 4097), (20, '<I', 16), (33, '<B', 1),
                                    (36, '<H', 4097), (44, '<I', 0x10002000),
                                    (48, '<B', 2), (68, '<H', 0), (88, '<B', 0x90)]:
        changed = bytearray(original); struct.pack_into(format, changed, position, value); cases.append(bytes(changed))
    # Correctly framed, but a material refers to a different shape owner.
    changed = bytearray(original); changed[-12:-8] = b'WRNG'; cases.append(bytes(changed))
    for data in cases:
        with pytest.raises(AssetError):
            Textures(data)


def test_texture_rejects_indirect_pixel_pointer_into_header():
    data = bytearray(texture(indirect=True))
    struct.pack_into('<I', data, 48, 16)
    with pytest.raises(AssetError, match='indirect pixel'):
        Textures(bytes(data))


@pytest.mark.parametrize('kind,size', [(0x60, 8), (0x61, 16), (0x62, 16)])
def test_compressed_texture_uses_complete_four_by_four_blocks(kind, size):
    data = bytearray(24 + 16 + size)
    data[:4] = b'SHPX'
    struct.pack_into('<II', data, 4, len(data), 1)
    struct.pack_into('<4sI', data, 16, b'DXT1', 24)
    data[24] = kind
    struct.pack_into('<HH', data, 28, 4, 4)
    image, = Textures(bytes(data)).images
    assert image['pixels_offset'] == 40 and image['pixels_bytes'] == size
    data.pop(); struct.pack_into('<I', data, 4, len(data))
    with pytest.raises(AssetError, match='exceeds its bounds'):
        Textures(bytes(data))


def test_duplicate_roots_and_shape_rename_collision_are_rejected():
    first, second = texture(), Textures(texture()).renamed({'TEST': 'TWO2'})
    # Rebase the second chain's root and directory; relative links need no edit.
    data = bytearray(first + second[32:])
    struct.pack_into('<II', data, 4, len(data), 2)
    struct.pack_into('<4sI', data, 24, b'TWO2', len(first))
    parsed = Textures(bytes(data))
    assert len(parsed.images) == 2
    with pytest.raises(AssetError, match='renames collide'):
        parsed.renamed({'TEST': 'TWO2'})
    struct.pack_into('<I', data, 28, 32)
    with pytest.raises(AssetError, match='Aliased'):
        Textures(bytes(data))
