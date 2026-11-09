"""Offline graph/output joins with exact palette and appearance identities.

Bounds and identity checks do not establish native blending or playback. The
caller supplies trusted compiled appearance bytes (or verified retail bytes),
and a separately verified hand resource with its audited output allocation.
This module does not change package admission or the legacy native type11 guard.
"""
import hashlib

from fighter_animation import require
from fighter_animation_graphs import validate_motion
from fighter_elf import Model
from fighter_face import FacePalettes, declared_capacities
from fighter_registry import fingerprint, key
from fighter_rig import Skeleton


def digest(data):
    return hashlib.sha256(data).hexdigest()


class MotionOutputContexts:
    def __init__(self, hands, expected_sha256):
        require(type(hands) is FacePalettes and len(hands.palettes) == 2
                and digest(hands.model.data) == expected_sha256,
                'Motion hand context differs from its verified identity')
        self.hands = hands
        self.hand_identity = {'sha256': expected_sha256, 'output_items': hands.bone_count,
                              'frames': list(hands.frame_counts)}
        self.contexts = {}

    def add(self, identifier, model, face, *, model_sha256, face_sha256):
        key(identifier)
        require(identifier not in self.contexts and isinstance(model, bytes) and isinstance(face, bytes)
                and digest(model) == model_sha256 and digest(face) == face_sha256,
                'Motion appearance context is duplicate or differs from its receipt')
        rig = Skeleton(Model(model))
        palette_model = Model(face)
        palettes = FacePalettes(palette_model, len(rig.rows), declared_capacities(palette_model))
        require(len(palettes.palettes) == 2, 'Motion face context needs both palette selectors')
        identity = {'model_sha256': model_sha256, 'face_sha256': face_sha256,
                    'rig_sha256': rig.pose_sha256, 'topology_sha256': rig.topology_sha256,
                    'permutation_sha256': fingerprint(rig.permutation), 'bone_count': len(rig.rows),
                    'face_frames': list(palettes.frame_counts)}
        self.contexts[identifier] = (rig, palettes, identity)
        return dict(identity)

    def join(self, value, origin, targets):
        require(origin in self.contexts and type(targets) in (tuple, list) and targets
                and len(targets) <= 16384 and len(set(targets)) == len(targets),
                'Motion needs a known origin and explicit unique target contexts')
        rig, face, identity = self.contexts[origin]
        validate_motion(value, rig.pose_sha256, len(rig.rows), face, self.hands)
        joined = {}
        for target in sorted(targets):
            require(target in self.contexts, 'Unknown motion opponent/output context: ' + str(target))
            other, palette, other_identity = self.contexts[target]
            require(other.topology_sha256 == rig.topology_sha256 and other.permutation == rig.permutation
                    and len(other.rows) == len(rig.rows), 'Motion output has a different ordered joint layout')
            # Body/root destinations have the same allocation and ordered joints.
            # Faces borrow each actual actor's exact palette, never the origin's.
            for leaf in value['graphs']['face']['children']:
                palette.require_samples(leaf['selector'], tuple(leaf['samples']))
            joined[target] = dict(other_identity)
        receipt = {'schema': 'fighter-motion-context-joins-1', 'origin': origin,
                   'origin_identity': dict(identity), 'targets': joined, 'hands': dict(self.hand_identity),
                   'graph_sha256': fingerprint(value), 'bounds_and_identities_validated': True,
                   'native_blending_validated': False, 'runtime_ready': False, 'native_playtest': False}
        return {**receipt, 'sha256': fingerprint(receipt)}
