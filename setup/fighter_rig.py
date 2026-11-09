"""Typed validation of the observed inline EAGL Skeleton data resource.

Preserves local transforms, the opaque permutation and every stored matrix.
This does not decode skin weights or establish moveset/animation compatibility.
"""
import hashlib
import math

from fighter_elf import Model, ModelError
from fighter_registry import fingerprint

MAX_BONES = 4096
RECORD_BYTES = 112
HEADER_TAG = 0x03ac3f23


def require(condition, message):
    if not condition:
        raise ModelError(message)


class Skeleton:
    def __init__(self, model):
        require(isinstance(model, Model), 'Skeleton requires a validated model envelope')
        roots = {name for name in model.exports if name.startswith('__Skeleton:::')}
        require(roots == {'__Skeleton:::root'}, 'Unsupported model skeleton exports')
        root = model.export_offset('__Skeleton:::root')
        tag, flags, count, reserved = model.data_words(root, 4)
        require(tag == HEADER_TAG and flags == reserved == 0 and 0 < count <= MAX_BONES,
                'Unsupported model skeleton header/count')
        length = 16 + count * RECORD_BYTES
        at = model.data_range(root, length)
        require(not any(root <= offset < root + length for offset in model.pointers),
                'Skeleton scalar records cannot contain pointer relocations')
        bones = model.bone_indices()
        require(len(bones) == count, 'Skeleton count differs from exported bone indices')
        rows = tuple(model.unpack('<3fi4f3fI16f', at + 16 + index * RECORD_BYTES) for index in range(count))
        for index, row in enumerate(rows):
            require(row[3] == -1 if index == 0 else 0 <= row[3] < index,
                    'Skeleton parents must form one ordered tree')
            require(all(math.isfinite(value) for value in (*row[:3], *row[4:11], *row[12:])),
                    'Skeleton transforms must be finite')
            require(abs(sum(value * value for value in row[4:8]) - 1) <= 0.001,
                    'Skeleton quaternion is not normalized')
        require({row[11] for row in rows} == set(range(count)), 'Invalid skeleton permutation')
        self.bones, self.rows = bones, rows
        self.parents = tuple(row[3] for row in rows)
        self.permutation = tuple(row[11] for row in rows)
        self.pose_sha256 = hashlib.sha256(model.data[at:at + length]).hexdigest()
        self.topology_sha256 = fingerprint({'bones': bones, 'parents': self.parents})

    def metadata(self):
        return {'format': 'fighter-skeleton-draft-1', 'bone_count': len(self.rows),
                'record_bytes': RECORD_BYTES, 'topology_sha256': self.topology_sha256,
                'pose_sha256': self.pose_sha256, 'stored_matrices_preserved': True,
                'skin_joint_mapping_validated': False, 'animation_compatibility_validated': False}


def skeleton_metadata(model):
    if not any(name.startswith('__Skeleton:::') for name in model.exports):
        return None
    return Skeleton(model).metadata()
