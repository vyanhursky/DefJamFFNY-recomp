"""The one definition of the compiled CAF container shared by the Python compiler and the C runtime.

`fighter-caf.bin` is a 64-byte header followed by four sections laid end to end, in this order:

    recipes   count * RECIPE_STRIDE bytes   one row per fighter outfit
    extras    count * EXTRA_STRIDE bytes    finisher choices and atlas pointers, then the 256px atlas pixel blocks
    hd        count * HD_STRIDE bytes       host-side 512..2048px RGB per outfit, then the pixel blocks
    faces     count * FACE_STRIDE bytes     one sculpt per fighter outfit

Every number is a little-endian u32 unless the field says otherwise. The section offsets are recorded in the header
and must tile the file exactly. The C side reads these names through `src/patches/fighter_caf_layout.h`, which
`scripts/gen-fighter-caf-layout.py` writes from this module; a unit test fails if the two drift apart.
"""
import struct

MAGIC = b'FCAF'
VERSION = 1
HEADER_BYTES = 64
HD_MAX_BYTES = 128 * 1024 ** 2
MAX_FILE = 64 * 1024 ** 2 + HD_MAX_BYTES

# Header words, in order after the magic and version.
HEADER = ('recipe_offset', 'recipe_count', 'extras_offset', 'extras_count', 'extras_bytes',
          'hd_offset', 'hd_count', 'hd_bytes', 'faces_offset', 'faces_count', 'total_bytes')
HEADER_FORMAT = '<4sI11I12x'

RECIPE_STRIDE = 240
VALUES = 38        # CAF appearance values, u32 each
COLORS = 38        # CAF colour indexes, one byte each
TRAINING = 5       # upper, lower, speed, toughness, health
STYLES = 3         # style ids, one byte each, 255 when unused
RECIPE = {
    'selection': 0,   # logical fighter selection key
    'core': 4,        # motion core: 87..141 for a CAF combination, 1..86 for a retail moveset
    'training': 8,    # TRAINING u32
    'style_count': 28,
    'values': 32,     # VALUES u32
    'colors': 184,    # COLORS bytes
    'styles': 222,    # STYLES bytes
    'retail': 225,    # byte: 1 when `core` is a retail moveset
    'voice': 228,     # retail voice core, 1..86
    'outfit': 232,    # outfit index 0..2
    'alias': 236,     # presentation alias the selector shows for this outfit
}

EXTRA_STRIDE = 52
FINISHERS = 4
ATLASES = 6
EXTRA = {
    'selection': 0,
    'has_finishers': 4,
    'finishers': 8,   # FINISHERS u32, retail choice numbers below 82
    'atlases': 24,    # ATLASES u32 offsets from the extras section start, 0 when unused
    'outfit': 48,
}
ATLAS_BYTES = 256 * 256 * 4

HD_STRIDE = 32
HD_EDGES = (512, 1024, 2048)   # each block is an edge u32 then edge * edge BGRA pixels
HD_MAX_BLOCKS = 128
HD = {
    'selection': 0,
    'outfit': 4,
    'atlases': 8,     # ATLASES u32 block offsets from the hd section start, 0 when the slot has no HD art
}

FACE_VERTICES = 710
FACE_VERTEX_BYTES = 24   # x y z floats, then the delta of x y z
FACE_VERTEX_DELTA = 12
FACE_STRIDE = 32 + FACE_VERTICES * FACE_VERTEX_BYTES
BASIS = 6
FACE = {
    'selection': 0,
    'outfit': 4,
    'basis': 8,       # BASIS u32 appearance values this sculpt was made against
    'vertices': 32,   # FACE_VERTICES * FACE_VERTEX_BYTES
}


def pack_header(recipe_count, extras_count, extras_bytes, hd_count, hd_bytes, faces_count):
    """The header for sections that follow it back to back. Offsets are derived, never supplied."""
    recipe_offset = HEADER_BYTES
    extras_offset = recipe_offset + recipe_count * RECIPE_STRIDE
    hd_offset = extras_offset + extras_bytes
    faces_offset = hd_offset + hd_bytes
    total = faces_offset + faces_count * FACE_STRIDE
    return struct.pack(HEADER_FORMAT, MAGIC, VERSION, recipe_offset, recipe_count, extras_offset, extras_count,
                       extras_bytes, hd_offset, hd_count, hd_bytes, faces_offset, faces_count, total)


def split(raw):
    """(header, recipes, extras, hd, faces): the container's sections as byte strings, or None if it is malformed."""
    header = unpack_header(raw)
    if header is None or header['total_bytes'] != len(raw):
        return None
    expected = pack_header(header['recipe_count'], header['extras_count'], header['extras_bytes'],
                           header['hd_count'], header['hd_bytes'], header['faces_count'])
    if raw[:HEADER_BYTES] != expected:
        return None
    extras, hd, faces = header['extras_offset'], header['hd_offset'], header['faces_offset']
    return header, raw[HEADER_BYTES:extras], raw[extras:hd], raw[hd:faces], raw[faces:]


def unpack_header(raw):
    """Header fields as a dict, or None if the bytes are not a well-formed container header."""
    if len(raw) < HEADER_BYTES:
        return None
    magic, version, *words = struct.unpack_from(HEADER_FORMAT, raw)
    if magic != MAGIC or version != VERSION:
        return None
    return dict(zip(HEADER, words))
