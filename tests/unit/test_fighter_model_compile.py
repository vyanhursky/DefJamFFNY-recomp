"""Geometry compilation retains trusted controls and discards input controls."""
import struct

import pytest

from test_fighter_geometry import geometry_fixture
from fighter_elf import Model, ModelError
from fighter_geometry import Geometry
from fighter_model_compile import compile_geometry, shape_bindings


def test_geometry_changes_survive_but_unvalidated_input_control_words_do_not():
    data, start, sites = geometry_fixture(with_skin=True)
    template = Model(bytes(data))
    changed = bytearray(data)
    struct.pack_into('<f', changed, start + sites['data0-0'], 9.)
    # Model+c0 is a native stride. This unvalidated source control must not leak.
    struct.pack_into('<I', changed, start + 0xc0, 0x7fffffff)
    output = compile_geometry(Model(bytes(changed)), template)
    geometry = Geometry(output)
    assert geometry.meshes[0]['bounds']['max'][0] == 9.
    assert output.data_words(output.export_offset('__Model:::TEST_alpha') + 0xc0, 1) == (0,)
    assert output.imports == template.imports
    assert compile_geometry(Model(bytes(changed)), template).data == output.data


def test_template_layout_mismatch_is_actionable():
    data, start, sites = geometry_fixture(with_skin=True)
    changed = bytearray(data)
    # Change a non-geometry command's operand; parsing still works, but its
    # program no longer matches the template selected by the caller.
    struct.pack_into('<I', changed, start + sites['program0'] + 4, 81)
    with pytest.raises(ModelError, match='same material and render layout'):
        compile_geometry(Model(bytes(changed)), Model(bytes(data)))


def test_relocated_streams_support_changed_vertex_counts_and_keep_skin_adjacency():
    data, start, sites = geometry_fixture(with_skin=True)
    changed = bytearray(data)
    for stream, stride in enumerate((12, 8, 4, 4, 2)):
        length = 3 * stride
        if stride == 2: length = (length + 3) & ~3
        struct.pack_into('<I', changed, start + sites[f'vb0-{stream}'] + 4, length)
        struct.pack_into('<I', changed, start + sites['rm0'] + 0x6c + stream * 8, 3)
    struct.pack_into('<6H', changed, start + sites['indices0'], 0, 1, 2, 2, 1, 0)
    source = Model(bytes(changed))
    result = compile_geometry(source, Model(bytes(data)))
    assert Geometry(result).meshes == Geometry(source).meshes
    assert Geometry(result).meshes[0]['vertex_count'] == 3


def test_compiled_model_uses_its_resource_namespace_for_internal_exports():
    data, _, _ = geometry_fixture(with_skin=True)
    model = Model(bytes(data))
    result = compile_geometry(model, model, 'FM0123456789ABCDEF')
    assert Geometry(result).name == 'FM0123456789ABCDEF_alpha'
    assert not any('TEST_alpha' in name for name in result.exports)
    assert result.bone_indices() == model.bone_indices()


def test_shape_keys_follow_remapped_textures_across_variable_length_records():
    data, start, sites = geometry_fixture(with_skin=True, with_bindings=True)
    template = Model(bytes(data))
    # Same-length change affects the source import and table key; no template
    # control, item count or bitmap is copied from this source table.
    source = Model(bytes(data).replace(b'SHAPENAME=TEST,1;', b'SHAPENAME=MOD1,1;'))
    result = compile_geometry(source, template)
    bindings = shape_bindings(result, Geometry(result))
    assert [(key, len(items)) for _, key, items in bindings] == [('MOD1', 1), ('MOD1', 9)]
    for at, _, items in bindings:
        assert all('SHAPENAME=MOD1,1;' in item for item in items)
        count = len(items)
        tail = at + 8 + count * 4
        assert result.data_words(tail, 1) == template.data_words(tail, 1)


def test_shape_table_rejects_short_bitmap_and_missing_terminator():
    data, start, sites = geometry_fixture(with_skin=True, with_bindings=True)
    struct.pack_into('<H', data, start + sites['shape-table'] + 12, 0)
    with pytest.raises(ModelError, match='bitmap is too short'):
        compile_geometry(Model(bytes(data)), Model(bytes(data)))
    data, start, sites = geometry_fixture(with_skin=True, with_bindings=True)
    struct.pack_into('<I', data, start + sites['shape-table'] + 68, 1)
    with pytest.raises(ModelError, match='Unterminated template shape table'):
        compile_geometry(Model(bytes(data)), Model(bytes(data)))
