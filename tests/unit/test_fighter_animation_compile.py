"""Owned curves retain native timing and isolate changes to one named record."""
from dataclasses import replace
import hashlib
import math
import struct

import pytest

from test_fighter_animation_curves import curves
from fighter_animation import AnimationIndex
from fighter_animation_compile import AnimationTemplate
from fighter_animation_tracks import QuaternionTracks
from fighter_assets import AssetError


RIG = 'a' * 64


def template(duration=12):
    layout = curves(11, lambda data, pointers, record: struct.pack_into('<H', data, 50, duration))
    envelope = layout.index.envelope
    return envelope, AnimationTemplate(envelope, hashlib.sha256(envelope.model.data).hexdigest(), RIG, 4)


def track(duration=12):
    return QuaternionTracks(RIG, 4, (0, 1, 2, 3), tuple(
        ((0., 0., math.sin(i / 80), math.cos(i / 80)),
         (0., 0., 0., 1.), (0., 0., 0., 1.),
         (math.sin(i / 100), 0., 0., math.cos(i / 100))) for i in range(duration + 1)))


def test_authored_quaternions_preserve_paired_records_names_and_duration():
    source, compiler = template()
    result, report = compiler.compose({'A': track()})
    before, after = AnimationIndex(source), AnimationIndex(result)
    assert result.tokens == source.tokens and after.names == before.names
    # Both original names alias one record. Only A_s is replaced; A_t keeps
    # its original pointer and serialized record despite that alias.
    assert after.records[1] == before.records[1] == 40
    assert after.records[0] != after.records[1]
    assert result.model.data[result.model.data_range(40, 16):][:16] == source.model.data[source.model.data_range(40, 16):][:16]
    row = report['bindings']['A']
    assert row['duration_ticks'] == 12 and row['keys'] == 13
    assert row['destinations'] == (4, 16, 28, 40) and row['maximum_component_error'] < .0001
    assert row['rig_sha256'] == RIG and not report['runtime_ready']


def test_animation_requires_source_pin_and_exact_rig_identity():
    source, compiler = template()
    with pytest.raises(AssetError, match='verified'):
        AnimationTemplate(source, '0' * 64, RIG, 4)
    with pytest.raises(AssetError, match='template rig'):
        compiler.compose({'A': replace(track(), rig_sha256='b' * 64)})
    with pytest.raises(AssetError, match='template rig'):
        compiler.compose({'A': replace(track(), bone_count=5)})


@pytest.mark.parametrize('name,frames,message', [('B', 12, 'paired'), ('../A', 12, 'Unknown'),
                                               ('A', 11, 'every inherited')])
def test_missing_links_and_timing_mismatch_reject_before_publication(name, frames, message):
    _, compiler = template()
    with pytest.raises(AssetError, match=message):
        compiler.compose({name: track(frames)})


@pytest.mark.parametrize('bones', [(0, 0), (3, 0), (0, 4), (False, 3), ()])
def test_pose_destinations_cannot_overlap_or_escape_the_declared_rig(bones):
    with pytest.raises(AssetError, match='bone ordinals'):
        replace(track(), bones=bones).encode()


@pytest.mark.parametrize('value', [float('nan'), float('inf'), 2.])
def test_nonfinite_or_nonunit_quaternion_rejected(value):
    with pytest.raises(AssetError, match='finite and unit'):
        QuaternionTracks(RIG, 1, (0,), (((value, 0., 0., 1.),),)).encode()


def test_antipodal_keys_are_not_silently_interpolated_through_zero():
    with pytest.raises(AssetError, match='hemispheres'):
        QuaternionTracks(RIG, 1, (0,), (((0., 0., 0., 1.),), ((0., 0., 0., -1.),))).encode()


def test_partial_tracks_cannot_replace_a_complete_skeletal_record():
    _, compiler = template()
    with pytest.raises(AssetError, match='full rig'):
        compiler.compose({'A': replace(track(), bones=(0,))})


def test_constant_single_key_and_long_curves_stay_within_error_budget():
    _, compiler = template(0)
    _, report = compiler.compose({'A': track(0)})
    assert report['bindings']['A']['maximum_component_error'] == 0
    _, compiler = template(900)
    _, report = compiler.compose({'A': track(900)})
    assert report['bindings']['A']['maximum_component_error'] <= .0001
