"""Palette identity, ordered joint mapping and graph ownership stay separate."""
from copy import deepcopy
import hashlib
import struct

import pytest

from test_fighter_animation_graphs import palettes, motion
from test_fighter_rig import rig_fixture
from fighter_assets import AssetError
from fighter_elf import Model
from fighter_motion_contexts import MotionOutputContexts
from fighter_rig import Skeleton


def digest(data):
    return hashlib.sha256(data).hexdigest()


def context():
    hands = palettes()
    library = MotionOutputContexts(hands, digest(hands.model.data))
    model, start, _, _ = rig_fixture()
    face = palettes().model.data
    library.add('alpha/appearance', bytes(model), face, model_sha256=digest(model), face_sha256=digest(face))
    return library, model, start, face


def test_different_pose_and_face_identity_are_recorded_without_claiming_native_acceptance():
    library, model, start, face = context()
    struct.pack_into('<f', model, start + 32, 10.)
    changed = bytearray(face)
    # Change one active quaternion to another unit rotation.
    parsed = palettes()
    sample = parsed.model.local_pointer(parsed.model.local_pointer(parsed.root + 8, 12), 16)
    at = parsed.model.data_range(sample, 16)
    struct.pack_into('<4f', changed, at, 0., .6, 0., .8)
    library.add('beta/appearance', bytes(model), bytes(changed), model_sha256=digest(model), face_sha256=digest(changed))
    value = motion()
    value['rig_sha256'] = library.contexts['alpha/appearance'][0].pose_sha256
    before = deepcopy(value)
    receipt = library.join(value, 'alpha/appearance', ['alpha/appearance', 'beta/appearance'])
    assert receipt['targets']['alpha/appearance']['rig_sha256'] != receipt['targets']['beta/appearance']['rig_sha256']
    assert receipt['targets']['alpha/appearance']['face_sha256'] != receipt['targets']['beta/appearance']['face_sha256']
    assert value == before and receipt['bounds_and_identities_validated']
    assert not receipt['runtime_ready'] and not receipt['native_blending_validated']


def test_same_bone_count_with_a_different_permutation_cannot_join():
    library, model, start, face = context()
    struct.pack_into('<I', model, start + 32 + 44, 0)
    struct.pack_into('<I', model, start + 32 + 112 + 44, 1)
    library.add('beta/appearance', bytes(model), face, model_sha256=digest(model), face_sha256=digest(face))
    value = motion(); value['rig_sha256'] = library.contexts['alpha/appearance'][0].pose_sha256
    with pytest.raises(AssetError, match='ordered joint'):
        library.join(value, 'alpha/appearance', ['beta/appearance'])


def test_wrong_context_hash_or_origin_and_unknown_target_are_errors():
    library, model, _, face = context()
    with pytest.raises(AssetError, match='receipt'):
        library.add('beta/appearance', bytes(model), face, model_sha256='0' * 64, face_sha256=digest(face))
    with pytest.raises(AssetError, match='identity'):
        MotionOutputContexts(palettes(), '0' * 64)
    with pytest.raises(AssetError, match='verified rig'):
        library.join(motion(), 'alpha/appearance', ['alpha/appearance'])
    value = motion(); value['rig_sha256'] = library.contexts['alpha/appearance'][0].pose_sha256
    with pytest.raises(AssetError, match='Unknown motion'):
        library.join(value, 'alpha/appearance', ['missing/appearance'])
