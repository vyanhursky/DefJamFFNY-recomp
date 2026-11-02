"""Game-free BIG composition tests: payload ownership, bounds and invariants."""
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_archive import Archive, AssetError, portrait_aliases, store
from fighter_assets import unpack


def fixture(entries, footer=b'L253\x15\x05\x00\x01', alignment=128):
    directory = 16 + sum(9 + len(name) for name in entries)
    at = directory + len(footer)
    at += -at % alignment
    descriptors, payload = [], bytearray()
    for name, data in entries.items():
        pad = -at % alignment
        payload += bytes(pad) + data
        at += pad
        descriptors.append(struct.pack('>II', at, len(data)) + name.encode('ascii') + b'\0')
        at += len(data)
    header = b'BIG4' + struct.pack('<I', at) + struct.pack('>II', len(entries), directory + len(footer))
    first = struct.unpack_from('>I', descriptors[0])[0]
    return header + b''.join(descriptors) + footer + bytes(first - directory - len(footer)) + payload


def test_composition_preserves_payloads_order_footer_and_alignment():
    original = fixture({'one.apt': b'first payload', 'other/long-name.xsh': bytes(range(256))})
    source = Archive(original)
    assert source.compose() is original
    changed = Archive(source.compose({'a/new.const': b'added'}, {'one.apt': 'a-much-longer-new-basename.apt'}))
    assert [e.name for e in changed.entries] == ['a-much-longer-new-basename.apt', 'other/long-name.xsh', 'a/new.const']
    assert changed.read('A-MUCH-LONGER-NEW-BASENAME.APT') == b'first payload'
    assert changed.read('other/long-name.xsh') == bytes(range(256))
    assert changed.read('a/new.const') == b'added'
    assert changed.data[changed.directory_end:changed.directory_end + 8] == b'L253\x15\x05\x00\x01'
    assert all(e.offset % source.alignment == 0 for e in changed.entries)
    assert changed.compose({'z': b'last'}) == changed.compose({'z': b'last'})
    replaced = Archive(changed.compose(replacements={'a/new.const': b'new constant data'}))
    assert replaced.read('a/new.const') == b'new constant data'
    assert replaced.read('other/long-name.xsh') == bytes(range(256))
    with pytest.raises(AssetError, match='missing'):
        changed.compose(replacements={'missing': b'not an addition'})


@pytest.mark.parametrize('name', ('../escape', '/absolute', 'a//b', 'a/./b', 'a\\b', 'a:b', 'a\0b', '\N{SNOWMAN}'))
def test_rejects_unsafe_names(name):
    with pytest.raises(AssetError):
        Archive(fixture({'valid': b'ok'})).compose({name: b'bad'})


def test_rejects_conflicts_and_malformed_directory():
    original = fixture({'one': b'one', 'two': b'two'})
    archive = Archive(original)
    with pytest.raises(AssetError, match='conflicting'):
        archive.compose({'ONE': b'collision'})
    with pytest.raises(AssetError, match='conflicting'):
        archive.compose(renames={'two': 'ONE'})
    with pytest.raises(AssetError, match='missing'):
        archive.compose(renames={'absent': 'new'})
    variants = []
    for offset, value in ((4, len(original) + 1), (8, 100001), (12, 17), (16, len(original)), (20, len(original))):
        variant = bytearray(original)
        struct.pack_into('<I' if offset == 4 else '>I', variant, offset, value)
        variants.append(bytes(variant))
    overlap = bytearray(original)
    second_directory = 16 + 9 + len('one')
    struct.pack_into('>I', overlap, second_directory, archive.entries[0].offset)
    variants.append(bytes(overlap))
    for data in variants:
        with pytest.raises(AssetError):
            Archive(data)


def test_portrait_alias_keeps_movie_data_and_texture_payloads_exact():
    inners = {}
    for players in (2, 3, 4):
        stem = f'p_cf_8_{players}p'
        inners[f'screens/portrait/p_CF/{stem}.big'] = store(fixture({stem + suffix: suffix.encode() for suffix in ('.apt', '.const', '.o', '.xsh')}))
    source = fixture(inners)
    result = Archive(portrait_aliases(source, {100: 7}))
    assert len(result.entries) == 6
    for name, payload in inners.items():
        assert result.read(name) == payload
        new = name.replace('p_cf_8_', 'p_cf_101_')
        aliased = Archive(unpack(result.read(new)))
        assert {e.name for e in aliased.entries} == {f'p_cf_101_{name[-6]}p' + suffix for suffix in ('.apt', '.const', '.o', '.xsh')}
        assert sorted(aliased.read(e.name) for e in aliased.entries) == sorted(s.encode() for s in ('.apt', '.const', '.o', '.xsh'))
    with pytest.raises(AssetError, match='already owned'):
        portrait_aliases(result.data, {100: 7})


@pytest.mark.parametrize('size', (1, 3, 4, 111, 112, 113, 1024))
def test_literal_refpack_roundtrip(size):
    data = bytes(i % 256 for i in range(size))
    assert unpack(store(data)) == data


def test_result_alias_uses_exact_id_for_portrait_and_blank_custom_name_logo():
    entries = {'screens/trans/empty2.big': fixture({'empty2.apt': b'blank', 'empty2.const': b'constants'})}
    for count in (2, 3, 4):
        for prefix, stem in [('screens/portrait/p_CF/', f'p_cf_8_{count}p'),
                             ('screens/portrait/t_MS/', f't_MS_7_{count}p')]:
            entries[prefix + stem + '.big'] = fixture({stem + suffix: suffix.encode() for suffix in ('.apt', '.const', '.o', '.xsh')})
    source = Archive(fixture(entries))
    changed = Archive(portrait_aliases(source.data, {256: 7}, results=True))
    assert all(changed.read(e.name) == source.read(e.name) for e in source.entries)
    for count in (2, 3, 4):
        portrait = Archive(unpack(changed.read(f'screens/portrait/t_MS/t_MS_256_{count}p.big')))
        assert portrait.read(f't_MS_256_{count}p.xsh') == b'.xsh'
        logo = Archive(unpack(changed.read(f'screens/portrait/l_MS_256_{count}p.big')))
        assert {e.name for e in logo.entries} == {f'l_MS_256_{count}p.apt', f'l_MS_256_{count}p.const'}
        assert logo.read(f'l_MS_256_{count}p.apt') == b'blank'
