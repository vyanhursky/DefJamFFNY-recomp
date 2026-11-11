"""The compiled CAF container has one definition, shared by the compiler and the runtime."""
import importlib.util
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'setup'))
import fighter_caf_layout as layout
from fighter_caf import encode
from test_fighter_caf_face import fixture as face_fixture
from test_fighter_caf_outfits import fixture as outfit_fixture


def generator():
    spec = importlib.util.spec_from_file_location('gen_fighter_caf_layout', ROOT / 'scripts/gen-fighter-caf-layout.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_committed_c_header_matches_the_python_layout():
    module = generator()
    committed = module.TARGET.read_bytes().decode('utf-8').replace('\r\n', '\n')
    assert committed == module.render(), 'run python scripts/gen-fighter-caf-layout.py'


@pytest.mark.parametrize('fields,stride,counts', [
    (layout.RECIPE, layout.RECIPE_STRIDE, {'training': 4 * layout.TRAINING, 'values': 4 * layout.VALUES, 'colors': layout.COLORS, 'styles': layout.STYLES,
                                           'selection': 4, 'core': 4, 'style_count': 4, 'retail': 1, 'voice': 4, 'outfit': 4, 'alias': 4}),
    (layout.EXTRA, layout.EXTRA_STRIDE, {'selection': 4, 'has_finishers': 4, 'finishers': 4 * layout.FINISHERS, 'atlases': 4 * layout.ATLASES, 'outfit': 4}),
    (layout.HD, layout.HD_STRIDE, {'selection': 4, 'outfit': 4, 'atlases': 4 * layout.ATLASES}),
    (layout.FACE, layout.FACE_STRIDE, {'selection': 4, 'outfit': 4, 'basis': 4 * layout.BASIS, 'vertices': layout.FACE_VERTICES * layout.FACE_VERTEX_BYTES}),
])
def test_named_fields_fit_their_row_without_overlapping(fields, stride, counts):
    assert set(fields) == set(counts), 'every named field needs a declared width'
    spans = sorted((offset, offset + counts[name], name) for name, offset in fields.items())
    for (start, end, name), (next_start, _, next_name) in zip(spans, spans[1:]):
        assert end <= next_start, name + ' overlaps ' + next_name
    assert spans[-1][1] <= stride
    # No padding after the last field: the stride is exactly where the layout ends.
    assert stride - spans[-1][1] == 0


def test_header_words_are_contiguous_after_the_magic_and_version():
    assert struct.calcsize(layout.HEADER_FORMAT) == layout.HEADER_BYTES
    header = layout.pack_header(3, 2, 5000, 1, 7000, 1)
    after_recipes = layout.HEADER_BYTES + 3 * layout.RECIPE_STRIDE
    assert layout.unpack_header(header) == dict(
        recipe_offset=layout.HEADER_BYTES, recipe_count=3, extras_offset=after_recipes, extras_count=2, extras_bytes=5000,
        hd_offset=after_recipes + 5000, hd_count=1, hd_bytes=7000,
        faces_offset=after_recipes + 12000, faces_count=1, total_bytes=after_recipes + 12000 + layout.FACE_STRIDE)


def test_a_compiled_container_splits_back_into_its_three_sections():
    face, recipe = face_fixture()
    recipe.update(stats=dict.fromkeys(('upper', 'lower', 'speed', 'toughness', 'health'), 10), styles=[0], caf_colors=[0] * 38)
    item = dict(core=87, audio_core=5, recipe=recipe, extras=None,
                outfits=[dict(id='default', name='Outfit 1', recipe=recipe, face=face,
                              extras=dict(finishers=[1, 2, 3, 4], atlases={}))])
    report = dict(bindings={'a/b': {'selection_key': 100}})
    raw = encode({'a/b': item}, report)
    header, recipes, extras, hd, faces = layout.split(raw)
    assert (header['recipe_count'], header['extras_count'], header['hd_count'], header['faces_count']) == (1, 1, 0, 1)
    assert hd == b''
    assert len(recipes) == layout.RECIPE_STRIDE and len(extras) == layout.EXTRA_STRIDE and len(faces) == layout.FACE_STRIDE
    assert struct.unpack_from('<I', faces, layout.FACE['selection']) == (100,)
    assert layout.split(raw[:-1]) is None and layout.split(b'FCA3' + raw[4:]) is None


def test_a_container_with_no_extras_or_faces_still_tiles():
    item, report = outfit_fixture()
    for outfit in item['outfits']:
        outfit['extras'] = None
    header, recipes, extras, hd, faces = layout.split(encode({'example/fighter': item}, report))
    assert (header['recipe_count'], header['extras_count'], header['hd_count'], header['faces_count']) == (3, 0, 0, 0)
    assert extras == b'' and hd == b'' and faces == b'' and len(recipes) == 3 * layout.RECIPE_STRIDE
