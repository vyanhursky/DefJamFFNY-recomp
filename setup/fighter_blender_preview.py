"""Native-channel cinematic preview for the bounded Blender bridge.

This is offline display, not runtime admission. Export accepts only existing
palette-sample changes through fighter_caf_cinematic's closed donor contract.
Native matrices and weights are retained; Blender's automatic bind rebuilding
is deliberately not used to replace the serialized inverse bind matrices.
"""
import base64
from bisect import bisect_right
import copy
import hashlib
import json
import math
import numpy as np
from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_curves import CurveLayouts
from fighter_animation_timed_quaternions import TimedQuaternionCurve, blend
from fighter_animation_vectors import VectorCurve
from fighter_animation_scalars import f32
from fighter_caf_cinematic import parse, validate, FORMAT
from fighter_elf import Model
from fighter_rig import Skeleton
from fighter_face import FacePalettes, declared_capacities

C = np.array(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)), dtype=float)


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def palette_sample(leaf, palette, tick, samples=None):
    """FDB40 clamp/exact-key copy; smoothstep for both Q and vector channels."""
    times = leaf['times']; samples = leaf['samples'] if samples is None else samples
    require(len(samples) == len(times) and all(type(v) is int and 0 <= v < len(palette.frames) for v in samples),
            'Preview cue exceeds its original palette')
    tick = f32(tick)
    low = max(0, bisect_right(times, tick) - 1)
    if tick <= times[0] or tick >= times[-1] or tick == times[low]:
        return palette.frames[samples[low]]
    t = f32(f32(tick - times[low]) / (times[low + 1] - times[low]))
    weight = f32(f32(f32(3. - f32(t * 2.)) * t) * t)
    a, b = palette.frames[samples[low]], palette.frames[samples[low + 1]]
    count = len(palette.quaternion_destinations)
    return tuple(blend(x, y, weight, precision_bits=24) if i < count else
                 tuple(f32(v + f32(f32(w - v) * weight)) for v, w in zip(x, y))
                 for i, (x, y) in enumerate(zip(a, b)))


def global_matrices(poses, parents):
    """Column-vector transpose of native row-vector S*R*T and local*parent.

    Quaternions are not silently normalized: native exact type13 keys can be
    slightly nonunit. Full raw affine matrices are retained for CPU skinning.
    """
    result = []
    for pose, parent in zip(poses, parents):
        sx, sy, sz = pose[:3]; x, y, z, w = pose[4:8]
        m = np.array(((1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w), pose[8]),
                      (2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w), pose[9]),
                      (2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y), pose[10]),
                      (0, 0, 0, 1)), dtype=float)
        m[:3, :3] *= (sx, sy, sz)
        result.append(m if parent < 0 else result[parent] @ m)
    return np.array(result)


def deform(positions, normals, indices, weights, matrices):
    """The native three-influence linear matrix blend, physical bone indices."""
    p = np.column_stack((np.asarray(positions), np.ones(len(positions))))
    ids, w = np.asarray(indices, dtype=int), np.asarray(weights)
    mixed = np.sum(matrices[ids] * w[:, :, None, None], axis=1)
    xyz = np.einsum('nij,nj->ni', mixed[:, :3], p)
    n = np.einsum('nij,nj->ni', mixed[:, :3, :3], np.asarray(normals))
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return xyz @ C[:3, :3].T, n @ C[:3, :3].T


class Preview:
    def __init__(self, document):
        require(document['schema'] in ('fighter-blender-preview-1','fighter-blender-preview-2'), 'Unsupported Blender source')
        self.document = document; self.token = document['token']
        if document['schema']=='fighter-blender-preview-2':
            from fighter_caf_mouth import FORMAT as MOUTH_FORMAT,DURATIONS,neutral_mouth
            require(self.token in DURATIONS and document['duration_ticks']==DURATIONS[self.token], 'Voice donor duration differs')
            validate(dict(format=MOUTH_FORMAT,template=self.token,edits=[],mouth=neutral_mouth(document['duration_ticks']),speech_tick=0))
        else:validate(dict(format=FORMAT, template=self.token, edits=[]))
        self.skeleton = Skeleton(Model(base64.b64decode(document['skeleton'])))
        require(len(self.skeleton.rows) == 94, 'Blender source requires reviewed CAF rig')
        self.defaults = np.array([(*r[:3], 0., *r[4:8], *r[8:11], 0.) for r in self.skeleton.rows])
        self.inverse_bind = np.array([np.array(r[12:]).reshape(4, 4).T for r in self.skeleton.rows])
        self.face = FacePalettes(Model(base64.b64decode(document['face_palette'])), 94, (13, 15))
        self.hands = FacePalettes(Model(base64.b64decode(document['hand_palette'])), 94, (32, 32))
        self.curves = []; self.face_leaves = []; self.hand_leaves = []
        for role, encoded in document['members'].items():
            raw = base64.b64decode(encoded); index, layout, graphs = parse(raw)
            if role in ('face', 'hands'):
                leaves = graphs[self.token + '_p']['children']
                require(len(leaves) == 2 and [l['selector'] for l in leaves] == [0, 1], 'Unreviewed cue layout')
                setattr(self, 'face_leaves' if role == 'face' else 'hand_leaves', leaves)
            else:
                for suffix in ('_s', '_t'):
                    parent = index.records[index.lookup[self.token + suffix]]
                    for child in index.children[parent]:
                        kind = index.record_types[child]
                        require(kind in (13, 20), 'Unsupported source body/root preview curve')
                        curve = TimedQuaternionCurve(layout, child) if kind == 13 else VectorCurve(layout, child)
                        self.curves.append((kind, curve))
        self.cues = [copy.deepcopy(leaf['samples']) for leaf in self.face_leaves]
        self.duration = document['duration_ticks']

    def source(self, cues, mouth=None, speech_tick=0):
        require(type(cues) is list and len(cues) == 2, 'Expected two original face selectors')
        edits = []
        for selector, (original, values) in enumerate(zip(self.cues, cues)):
            require(len(original) == len(values), 'Cue key count changed')
            for key, (old, new) in enumerate(zip(original, values)):
                if old != new: edits.append(dict(selector=selector, key=key, expected=old, sample=new))
                require(type(new) is int, 'Cue sample must be an integer')
        if mouth is not None or self.token=='CI_113A':
            from fighter_caf_mouth import FORMAT as MOUTH_FORMAT,PUBLIC_FORMAT,neutral_mouth,DURATIONS
            value=dict(format=MOUTH_FORMAT,template=self.token,edits=edits,mouth=mouth if mouth is not None else neutral_mouth(DURATIONS[self.token]),speech_tick=speech_tick)
            validate(value);return dict(value,format=PUBLIC_FORMAT)
        value = dict(format=FORMAT, template=self.token, edits=edits); validate(value)
        return dict(value, format='fighter-cinematic-caf-donor-1')

    def pose(self, tick, cues=None, mouth=None):
        require(type(tick) in (int, float) and math.isfinite(tick) and 0 <= tick <= self.duration,
                'Preview time outside cinematic')
        poses = self.defaults.copy()
        for kind, curve in self.curves:
            values = curve.sample(tick, precision_bits=24) if kind == 13 else curve.sample(tick)
            for destination, value in zip(curve.destinations, values):
                bone, channel = divmod(destination, 12)
                poses[bone, channel:channel + len(value)] = value
        for leaves, palettes, edited in ((self.face_leaves, self.face, cues or self.cues),
                                          (self.hand_leaves, self.hands, None)):
            for i, leaf in enumerate(leaves):
                palette = palettes.palettes[i]
                if mouth is not None and leaves is self.face_leaves and i==1:
                    leaf=dict(leaf,times=[r[0] for r in mouth['lips']],samples=[r[1] for r in mouth['lips']])
                    selected=None
                else:selected=None if edited is None else edited[i]
                values = palette_sample(leaf,palette,tick,selected)
                for destination, value in zip(palette.quaternion_destinations + palette.vector_destinations, values):
                    bone, channel = divmod(destination, 12)
                    poses[bone, channel:channel + len(value)] = value
        if mouth is not None:
            from fighter_caf_mouth import validate_mouth,sample_jaw
            validate_mouth(mouth,self.duration);poses[69,4:8]=sample_jaw(mouth['jaw'],tick)
        return poses

    def matrices(self, tick, cues=None, mouth=None):
        worlds = global_matrices(self.pose(tick,cues,mouth), self.skeleton.parents)
        return worlds, worlds @ self.inverse_bind
