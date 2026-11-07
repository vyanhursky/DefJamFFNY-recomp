"""Synthetic type25 external sample contexts, with no native game data."""
import struct

import pytest

from test_fighter_elf import fixture
from fighter_elf import Model, ModelError
from fighter_face import FacePalettes, EXPORT, VERSION, compile_palettes


def face_model(change=None):
    original, original_rows, _ = fixture(EXPORT, VERSION)
    payload = bytearray(80)
    struct.pack_into('<IHHI', payload, 0, 0, 1, 0, 16)
    struct.pack_into('<IIBBBB', payload, 16, 32, 64, 2, 1, 0, 0)
    struct.pack_into('<8f', payload, 32, 0, 0, 0, 1, 0, 0, 0, 1)
    struct.pack_into('<H', payload, 64, 4)
    if change:
        change(payload)
    pieces = [b''] + [original[r[4]:r[4] + r[5]] for r in original_rows[1:]]
    pieces[1] = bytes(payload)
    symbols = bytearray(pieces[4])
    struct.pack_into('<IIIBBH', symbols, 32, len(EXPORT) + 2, 0, 4, 33, 0, 1)
    pieces[4] = bytes(symbols)
    pieces[5] = b''.join(struct.pack('<II', at, 258) for at in (8, 16, 20))
    image, rows = bytearray(original[:52]), [original_rows[0]]
    for i in range(1, 6):
        row = list(original_rows[i]); image.extend(bytes(-len(image) % row[8]))
        row[4:6] = [len(image), len(pieces[i])]
        image.extend(pieces[i]); rows.append(tuple(row))
    image.extend(bytes(-len(image) % 4))
    struct.pack_into('<I', image, 32, len(image))
    image.extend(b''.join(struct.pack('<10I', *r) for r in rows))
    return Model(bytes(image))


def test_face_context_uses_explicit_capacity_and_matched_body_channels():
    face = FacePalettes(face_model(), 1, (2,))
    assert face.palettes[0].frames == (((0., 0., 0., 1.),),) * 2
    assert face.palettes[0].quaternion_destinations == (4,)
    face.require_samples(0, b'\x01\x00\x01')  # Three keys can address two frames.
    assert not face.metadata()['native_playtest']
    assert not face.metadata()['animation_sample_joins_validated']


@pytest.mark.parametrize('selector,samples', [(1, b'\0'), (0, b'\2'), (0, b'\xff'), (0, b''), (-1, (0,))])
def test_face_sample_indices_are_not_bounded_by_time_key_count(selector, samples):
    with pytest.raises(ModelError):
        FacePalettes(face_model(), 1, (2,)).require_samples(selector, samples)


@pytest.mark.parametrize('change', [
    lambda p: struct.pack_into('<H', p, 64, 16),  # Bone1 exceeds the matched one-bone rig.
    lambda p: struct.pack_into('<H', p, 64, 3),   # Misaligned quaternion channel.
    lambda p: struct.pack_into('<f', p, 32, float('nan')),
    lambda p: struct.pack_into('<f', p, 44, 2),
    lambda p: struct.pack_into('<I', p, 16, 76), # In-section pointer, incomplete sample range.
    lambda p: struct.pack_into('<I', p, 20, 32), # Destination table aliases numeric samples.
    lambda p: p.__setitem__(24, 3),             # Capacity contract mismatch.
    lambda p: p.__setitem__(27, 1),             # Unhandled control byte.
])
def test_invalid_facial_data_is_rejected_before_native_use(change):
    with pytest.raises(ModelError):
        FacePalettes(face_model(change), 1, (2,))


def test_face_compilation_copies_typed_samples_but_uses_trusted_header():
    template = face_model()
    def authored(payload):
        struct.pack_into('<I', payload, 0, 0xDEADBEEF)  # Opaque source control must not be emitted.
        struct.pack_into('<4f', payload, 48, 0, 0.6, 0, 0.8)
    source = face_model(authored)
    before = source.data
    result, receipt = compile_palettes(source, template, 1, (2,))
    parsed = FacePalettes(result, 1, (2,))
    assert parsed.palettes == FacePalettes(source, 1, (2,)).palettes
    assert result.data_words(parsed.root, 1) == template.data_words(0, 1)
    assert source.data == before
    assert not receipt['source_controls_preserved'] and not receipt['native_playtest']
    with pytest.raises(ModelError, match='sample context'):
        compile_palettes(source, template, 1, (3,))
