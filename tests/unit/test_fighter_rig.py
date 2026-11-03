"""Synthetic inline skeleton resources; no game geometry or matrices."""
import math
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_elf import Model, ModelError
from fighter_rig import Skeleton, HEADER_TAG
from test_fighter_elf import fixture


def rig_fixture(count=2, bones=2):
    original, sections, table = fixture()
    image = bytearray(original)
    image += bytes(-len(image) % 16)
    start = len(image)
    payload = bytearray(16 + 16 + count * 112)
    for index in range(bones): struct.pack_into('<I', payload, index * 4, index)
    struct.pack_into('<4I', payload, 16, HEADER_TAG, 0, count, 0)
    for index in range(count):
        values = (1., 1., 1., -1 if index == 0 else index - 1,
                  0., 0., 0., 1., 0., float(index), 0., count - index - 1,
                  *(1. if row == column else 0. for row in range(4) for column in range(4)))
        struct.pack_into('<3fi4f3fI16f', payload, 32 + index * 112, *values)
    image += payload
    rows = list(sections)
    rows[1] = (*rows[1][:4], start, len(payload), *rows[1][6:])
    names = bytearray(b'\0'); symbols = bytearray(16)
    for index, (name, offset) in enumerate([*(('__Bone:::root.bone' + str(i), i * 4) for i in range(bones)),
                                           ('__Skeleton:::root', 16)]):
        symbols += struct.pack('<IIIBBH', len(names), offset, 4, 17, 0, 1)
        names += name.encode('ascii') + b'\0'
    rows[3] = (*rows[3][:4], len(image), len(names), *rows[3][6:]); image += names
    image += bytes(-len(image) % 4)
    rows[4] = (*rows[4][:4], len(image), len(symbols), *rows[4][6:]); image += symbols
    rows[5] = (*rows[5][:4], len(image), 0, *rows[5][6:])
    for index, row in enumerate(rows): struct.pack_into('<10I', image, table + index * 40, *row)
    return image, start, table, rows


def test_inline_skeleton_preserves_the_authored_pose_and_opaque_permutation():
    image, start, _, _ = rig_fixture()
    model = Model(bytes(image)); rig = Skeleton(model)
    assert rig.parents == (-1, 0) and rig.permutation == (1, 0)
    assert rig.rows[1][9] == 1.
    metadata = model.metadata()['skeleton']
    assert metadata['bone_count'] == 2 and metadata['record_bytes'] == 112
    assert metadata['stored_matrices_preserved']
    assert not metadata['skin_joint_mapping_validated']
    assert not metadata['animation_compatibility_validated']
    assert image[start + 16:start + 20] == struct.pack('<I', HEADER_TAG)


def test_same_topology_does_not_imply_same_pose_or_animation_compatibility():
    image, start, _, _ = rig_fixture()
    first = Skeleton(Model(bytes(image)))
    # A finite authored correction matrix is preserved, without forcing an inverse-TRS relation.
    struct.pack_into('<f', image, start + 32 + 48 + 12, 42.)
    second = Skeleton(Model(bytes(image)))
    assert first.topology_sha256 == second.topology_sha256
    assert first.pose_sha256 != second.pose_sha256
    assert second.rows[0][15] == 42.
    assert second.metadata()['animation_compatibility_validated'] is False


@pytest.mark.parametrize('offset,format,value', [
    (16, '<I', 0), (20, '<I', 1), (24, '<I', 0), (24, '<I', 4097), (28, '<I', 1),
    (32 + 12, '<i', 0), (32 + 112 + 12, '<i', 1), (32 + 112 + 12, '<i', -1),
    (32, '<f', math.inf), (32 + 16, '<f', math.nan), (32 + 32, '<f', -math.inf),
    (32 + 48, '<f', math.nan), (32 + 28, '<f', 0.), (32 + 112 + 44, '<I', 1),
])
def test_rejects_invalid_headers_trees_transforms_and_permutations(offset, format, value):
    image, start, _, _ = rig_fixture()
    struct.pack_into(format, image, start + offset, value)
    with pytest.raises(ModelError): Skeleton(Model(bytes(image)))


def test_rejects_count_mismatch_and_truncated_records():
    image, _, _, _ = rig_fixture(count=3)
    with pytest.raises(ModelError, match='count differs'): Skeleton(Model(bytes(image)))
    image, _, table, rows = rig_fixture()
    struct.pack_into('<I', image, table + 40 + 20, rows[1][5] - 1)
    with pytest.raises(ModelError, match='data range'): Skeleton(Model(bytes(image)))


def test_scalar_skeleton_data_cannot_hide_a_relocated_pointer():
    image, _, table, _ = rig_fixture()
    relocation = len(image); image += struct.pack('<II', 64, 1 << 8 | 2)
    struct.pack_into('<II', image, table + 5 * 40 + 16, relocation, 8)
    model = Model(bytes(image))
    with pytest.raises(ModelError, match='cannot contain pointer relocations'): Skeleton(model)
