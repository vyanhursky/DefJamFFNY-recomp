"""Invented vertex/palette rows qualify transport ordering, never original models."""
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_appearance_authoring import preview_skin
from fighter_workshop_animation import retail_rigs


def test_compacted_vertices_retain_native_skin_rows_and_zero_weight_indices_are_safe():
    skin = SimpleNamespace(resources=[dict(resource='mesh', palette=[
        dict(bones=[3, 250, 200], weights=[1., 0., 0.]),
        dict(bones=[1, 2, 255], weights=[.25, .75, 0.]),
    ])], vertex_selectors={'mesh': [0, 1, 0, 1]})
    value = preview_skin(skin, 'mesh', [3, 0, 2])
    assert value['indices'] == [[1, 2, 0, 0], [3, 0, 0, 0], [3, 0, 0, 0]]
    assert value['weights'] == [[.25, .75, 0., 0], [1., 0., 0., 0], [1., 0., 0., 0]]
    with pytest.raises(ValueError, match='source vertex order'):
        preview_skin(skin, 'mesh', [4])
    with pytest.raises(ValueError, match='verified skin palette'):
        preview_skin(skin, 'missing', [0])


@pytest.mark.parametrize('names', [None, [], ['../model'], ['retail-body', 'retail-body'], ['v2cp_a']])
def test_retail_preview_rejects_unbound_model_requests_before_reading_files(names):
    with pytest.raises(ValueError, match='current retail preview body'):
        retail_rigs('unused', 'unused', names)
