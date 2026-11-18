"""Game-free fixtures for native pose conventions and bounded Blender cue export."""
import math
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'setup'))
np=pytest.importorskip('numpy')
from fighter_face import Palette
from fighter_blender_preview import Preview,palette_sample,global_matrices,deform,C


def pose(scale=(1,1,1),q=(0,0,0,1),translation=(0,0,0)):
    return (*scale,0,*q,*translation,0)


def test_sqt_channels_and_parent_order_are_not_swapped():
    q=(0,0,math.sqrt(.5),math.sqrt(.5))
    matrices=global_matrices([pose((2,3,4),q,(4,5,6)),pose(translation=(1,0,0))],[-1,0])
    assert matrices[0][:3,3]==pytest.approx((4,5,6))
    assert matrices[1][:3,3]==pytest.approx((4,7,6))


def test_native_nonunit_key_is_not_silently_normalized_for_affine_skinning():
    m=global_matrices([pose(q=(0,0,1,1))],[-1])[0]
    assert m[:3,:3]==pytest.approx(np.array(((-1,-2,0),(2,-1,0),(0,0,1))))


def test_skinning_uses_physical_bones_three_weights_and_reversible_axis_map():
    m=np.array([np.eye(4),np.eye(4)]);m[0,0,3]=2;m[1,0,0]=2
    positions,normals=deform([(1,2,3)],[(0,1,0)],[(1,0,0)],[(.25,.75,0)],m)
    assert positions[0]==pytest.approx((2.75,-3,2))
    assert normals[0]==pytest.approx((0,0,1))
    assert np.array((2.75,-3,2))@C[:3,:3]==pytest.approx((2.75,2,3))


def test_type25_exact_keys_keep_raw_values_but_interior_uses_smoothstep():
    palette=Palette((4,),(8,),(((0,0,0,2),(0,0,0)),((0,0,0,3),(4,8,12))))
    leaf={'times':[0,4],'samples':[0,1]}
    assert palette_sample(leaf,palette,0)==palette.frames[0]
    assert palette_sample(leaf,palette,4)==palette.frames[1]
    assert palette_sample(leaf,palette,7)==palette.frames[1]
    middle=palette_sample(leaf,palette,1)
    assert middle[0]==pytest.approx((0,0,0,1))
    assert middle[1]==pytest.approx((.625,1.25,1.875))
    with pytest.raises(ValueError):palette_sample(leaf,palette,1,[0,2])


def fixture():
    p=object.__new__(Preview);p.token='CI_132A';p.cues=[[4],[1]];return p


def test_export_retains_closed_native_source_and_only_existing_sample_changes():
    p=fixture();assert p.source([[4],[1]])['edits']==[]
    assert p.source([[7],[1]])['edits']==[dict(selector=0,key=0,expected=4,sample=7)]
    assert p.cues==[[4],[1]]


@pytest.mark.parametrize('cues',[[[True],[1]],[[13],[1]],[[4],[15]],[[4,5],[1]],[[4]],[[4],[1.5]]])
def test_malformed_blender_cues_cannot_enter_native_export(cues):
    with pytest.raises(ValueError):fixture().source(cues)
