"""Synthetic model surfaces, variable material lists and cross-resource checks."""
import math
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_elf import Model, ModelError
from fighter_geometry import Geometry, ANIMATION_BUFFER
from fighter_xsh import Textures
from test_fighter_elf import fixture
from test_fighter_xsh import texture


def geometry_fixture(with_skin=False):
    original, sections, table = fixture()
    payload, pointers, exports, sites = bytearray(0xd0), {}, {'__Model:::TEST_alpha': 0}, {}

    def allocate(data):
        payload.extend(bytes(-len(payload) % 4)); at = len(payload); payload.extend(data); return at

    def word(at, value): struct.pack_into('<I', payload, at, value)

    def pointer(at, target):
        pointers[at] = target
        word(at, 0 if isinstance(target, str) else target)

    if with_skin:
        from fighter_rig import HEADER_TAG
        bone_words = allocate(struct.pack('<2I', 0, 1))
        exports.update({'__Bone:::root': bone_words, '__Bone:::root.child': bone_words + 4})
        rig = allocate(struct.pack('<4I', HEADER_TAG, 0, 2, 0) + bytes(224))
        exports['__Skeleton:::root'] = rig
        for i in range(2):
            struct.pack_into('<3fi4f3fI16f', payload, rig + 16 + i * 112,
                             1., 1., 1., -1 if i == 0 else 0, 0., 0., 0., 1., 0., 0., 0., i,
                             *(float(j // 4 == j % 4) for j in range(16)))

    struct.pack_into('<16f', payload, 12, *(float(i // 4 == i % 4) for i in range(16)))
    name = allocate(b'TEST_alpha\0'); pointer(0xb4, name)
    materials = allocate(bytes(8)); pointer(0xa0, materials); word(0x9c, 2)
    for i, name in enumerate(('surface', 'extras')):
        pointer(materials + i * 4, allocate(name.encode() + b'\0'))
    sites['group'] = group = allocate(bytes(24)); pointer(0xcc, group)
    word(group + 4, 1); word(group + 12, 2)
    vertices = ((0., 0., 0.), (1., 0., 0.), (0., 1., 0.), (1., 1., 0.))
    layouts = ((12, 8, 4, 4, 2), (12, 4, 4), (12, 2, 4, 4))
    parents = ('ParentRM_IrradTexture_Skin', 'ParentRM_LitGouraud', 'ParentRM_DJFXSparkle_Skin')
    for index, strides in enumerate(layouts):
        rm = allocate(bytes(0xa0)); exports[f'__RM:::__GP_RM_TEST_alpha_{index}'] = rm
        sites[f'rm{index}'] = rm
        pointer(rm + 0x38, rm); pointer(group + (8 if index == 0 else 12 + index * 4), rm + 0x38)
        pointer(rm + 0x1c, parents[index]); pointer(rm + 0x2c, parents[index])
        count = 3 if index == 2 else 4
        for stream, stride in enumerate(strides):
            vb = allocate(bytes(20)); exports[f'__VB:::__GPvb_{stream}_{index}_TEST_alpha'] = vb
            sites[f'vb{index}-{stream}'] = vb
            if not stream:
                data = b''.join(struct.pack('<3f', *v) for v in vertices[:count])
            else:
                length = count * stride
                data = bytes((length + 3) & ~3 if stride == 2 else length)
            vertex_data = allocate(data); sites[f'data{index}-{stream}'] = vertex_data
            word(vb + 4, len(data)); word(vb + 8, stride); word(vb + 12, 1)
            header = allocate(bytes(8)); word(header, 1); pointer(header + 4, vertex_data)
            pointer(vb, header); pointer(vb + 16, vertex_data)
        if index != 2:
            field = rm + 0x50
            if index == 0:
                pointer(field, ANIMATION_BUFFER); field += 8
            indices = allocate(struct.pack('<6H', 0, 1, 2, 2, 1, 3)); sites[f'indices{index}'] = indices
            header = allocate(struct.pack('<4I', 6, 0, 0, 0)); sites[f'index-header{index}'] = header
            pointer(field, header); word(field + 4, 6); pointer(field + 8, indices)
        if index == 0:
            pointer(rm + 0x40, '__EAGL::TAR:::RUNTIME_ALLOC::UID=1;SHAPENAME=TEST,1;')
            pointer(rm + 0x48, '__EAGL::TAR:::spectexture1')
        # Explicit commands establish each parameter's role. Native RM records
        # can omit a draw-count command and inherit state from another RM.
        if index == 0:
            commands = [(15, (80, 0)), (15, (0, 1)), (29, (0, -96, 56, -36, 104)),
                        (2, (0,)), (14, (0,)), (26, (0, 5))]
            word(rm + 0x3c, 1); word(rm + 0x44, 1); word(rm + 0x4c, 40); word(rm + 0x54, 1)
        elif index == 1:
            commands = [(1, ()), (1, ()), (2, (0,)), (14, (0,)), (26, (0, 3))]
            word(rm + 0x4c, 1)
        else:
            commands = [(4, (0,)), (25, (0, 4))]
        if with_skin and index == 0:
            palette = allocate(struct.pack('<8f', 1., 0., 0., 0., .5, .5, 0., float(1 << 24)))
            sites['palette'] = palette
            commands = [(15, (80, 0)), (15, (0, 1)), (31, (0,)), (29, (0, -96, 56, -36, 104)),
                        (2, (0,)), (14, (0,)), *((9, (0, i, stride)) for i, stride in enumerate(strides)),
                        (26, (0, 5))]
            word(rm + 0x4c, 2); pointer(rm + 0x50, palette)
            word(rm + 0x54, 40); pointer(rm + 0x58, ANIMATION_BUFFER)
            word(rm + 0x5c, 1); pointer(rm + 0x60, sites['index-header0'])
            word(rm + 0x64, 6); pointer(rm + 0x68, sites['indices0'])
            for i in range(len(strides)):
                word(rm + 0x6c + i * 8, count)
                pointer(rm + 0x70 + i * 8, sites[f'data0-{i}'])
            struct.pack_into('<4h', payload, sites['data0-4'], -96, -92, -96, -92)
        encoded = b''.join(struct.pack('<' + 'I' * (1 + len(args)),
                                     op << 16 | (1 + len(args)), *(value & 0xffffffff for value in args))
                           for op, args in commands) + bytes(4)
        program = allocate(encoded); sites[f'program{index}'] = program
        pointer(rm, program); pointer(rm + 8, allocate(bytes(4)))

    image = bytearray(original); image.extend(bytes(-len(image) % 16)); start = len(image); image.extend(payload)
    rows = list(sections); rows[1] = (*rows[1][:4], start, len(payload), *rows[1][6:])
    strings, symbols, indices = bytearray(b'\0'), bytearray(16), {}
    for name, value, section in [(n, v, 1) for n, v in exports.items()] + [(n, 0, 0) for n in sorted({v for v in pointers.values() if isinstance(v, str)})]:
        indices[name] = len(symbols) // 16
        symbols.extend(struct.pack('<IIIBBH', len(strings), value, 4 if section else 0, 17 if section else 16, 0, section))
        strings.extend(name.encode() + b'\0')
    relocations = b''.join(struct.pack('<II', at, ((indices[target] if isinstance(target, str) else 1) << 8) | 2)
                           for at, target in sorted(pointers.items()))
    for index, data in ((3, strings), (4, symbols), (5, relocations)):
        if index >= 4: image.extend(bytes(-len(image) % 4))
        rows[index] = (*rows[index][:4], len(image), len(data), *rows[index][6:]); image.extend(data)
    for index, row in enumerate(rows): struct.pack_into('<10I', image, table + index * 40, *row)
    return image, start, sites


def test_geometry_checks_variable_material_lists_streams_and_triangle_indices():
    image, _, _ = geometry_fixture()
    parsed = Geometry(Model(bytes(image))); report = parsed.metadata()
    assert [g['render_resources'] for g in report['material_groups']] == [[0], [1, 2]]
    assert [m['kind'] for m in report['meshes']] == ['triangle-strip', 'triangle-strip', 'points']
    assert [m['vertex_count'] for m in report['meshes']] == [4, 4, 3]
    assert [m['nondegenerate_triangles'] for m in report['meshes']] == [2, 2, 0]
    assert report['meshes'][0]['bounds'] == {'min': [0., 0., 0.], 'max': [1., 1., 0.]}
    assert report['texture_shapes'] == ['TEST']
    assert report['external_texture_bindings'] == ['__EAGL::TAR:::spectexture1']
    assert not report['runtime_ready'] and not report['render_commands_validated'] and not report['skin_weights_validated']
    parsed.require_textures(Textures(texture()))
    other = Textures(Textures(texture()).renamed({'TEST': 'OTHR'}))
    with pytest.raises(ModelError, match='Missing model texture shapes: TEST'): parsed.require_textures(other)
    parsed.require_textures(other, baseline_shapes={'TEST'})
    with pytest.raises(ModelError, match='validated texture data'): parsed.require_textures(texture())


@pytest.mark.parametrize('site,offset,format,value', [
    (None, 12, '<f', math.nan), (None, 0x9c, '<I', 257),
    ('group', 0, '<I', 1), ('group', 4, '<I', 0), ('group', 12, '<I', 3),
    ('vb0-0', 4, '<I', 1_000_001 * 12), ('vb0-0', 8, '<I', 16), ('vb0-0', 12, '<I', 0),
    ('vb0-1', 4, '<I', 24), ('vb0-4', 4, '<I', 12),
    ('data0-0', 0, '<f', math.inf), ('data0-1', 0, '<f', -math.inf),
    ('indices0', 0, '<H', 4), ('index-header0', 4, '<I', 1),
    ('rm0', 0x5c, '<I', 3_000_001),
])
def test_geometry_rejects_bad_counts_nonfinite_values_and_index_bounds(site, offset, format, value):
    image, start, sites = geometry_fixture()
    struct.pack_into(format, image, start + (sites[site] if site else 0) + offset, value)
    with pytest.raises(ModelError): Geometry(Model(bytes(image)))


def test_material_wrappers_cannot_alias_or_reference_arbitrary_inline_words():
    image, start, sites = geometry_fixture()
    struct.pack_into('<I', image, start + sites['group'] + 20, sites['rm0'] + 0x38)
    with pytest.raises(ModelError, match='uniquely reference'): Geometry(Model(bytes(image)))
    image, start, sites = geometry_fixture()
    struct.pack_into('<I', image, start + sites['group'] + 8, sites['rm0'])
    with pytest.raises(ModelError): Geometry(Model(bytes(image)))


def test_unrecognized_inline_index_data_is_rejected_instead_of_guessed():
    image, start, sites = geometry_fixture()
    # A superficially valid local pointer is not sufficient evidence of the header schema.
    struct.pack_into('<I', image, start + sites['rm0'] + 0x58, sites['indices0'])
    with pytest.raises(ModelError, match='index header'): Geometry(Model(bytes(image)))


def test_scalar_vertex_stream_cannot_carry_a_relocated_pointer():
    image, start, sites = geometry_fixture()
    table = struct.unpack_from('<I', image, 32)[0]
    rel = struct.unpack_from('<10I', image, table + 5 * 40)
    at = len(image); image.extend(image[rel[4]:rel[4] + rel[5]])
    # A valid local ELF pointer relocation is still forbidden inside a float stream.
    struct.pack_into('<I', image, start + sites['data0-0'], 0)
    image.extend(struct.pack('<II', sites['data0-0'], 1 << 8 | 2))
    struct.pack_into('<II', image, table + 5 * 40 + 16, at, rel[5] + 8)
    with pytest.raises(ModelError, match='scalar data contains a pointer'): Geometry(Model(bytes(image)))


def test_geometry_cli_checks_texture_references_without_granting_runtime_support(tmp_path, monkeypatch, capsys):
    import json
    from test_fighter_probe import driver
    cli = driver(tmp_path, monkeypatch).registry
    model = tmp_path / 'model.o'; model.write_bytes(geometry_fixture()[0])
    images = tmp_path / 'textures.xsh'; images.write_bytes(texture())
    monkeypatch.setattr(sys, 'argv', ['fighter-registry.py', 'inspect-geometry', str(model), '--textures', str(images)])
    assert cli.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert not report['runtime_ready'] and not report['geometry']['runtime_ready']
    assert report['geometry']['texture_shapes'] == ['TEST']
    images.write_bytes(Textures(texture()).renamed({'TEST': 'OTHR'}))
    assert cli.main() == 1
    assert 'Missing model texture shapes' in json.loads(capsys.readouterr().out)['error']['message']
