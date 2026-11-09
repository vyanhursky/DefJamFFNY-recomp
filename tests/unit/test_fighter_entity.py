"""Native entity registration composition without game data or pack XML."""
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_entity import Entities, Entity, AssetError

SOURCE = b'<?xml version="1.0"?><entitylist><? Retail note ?><entity><name>Original</name></entity></entitylist>\r\nunused example'


def catalog(source=SOURCE):
    return Entities(source, hashlib.sha256(source).hexdigest())


def test_emits_only_typed_registration_and_preserves_original_bytes():
    source = catalog()
    assert source.compose([]) == SOURCE
    entries = [Entity('Second', 'MeshB', 'TexB'), Entity('First', 'MeshA', 'TexA')]
    output = source.compose(entries)
    assert output == source.compose(list(reversed(entries)))
    assert output.replace(entries[0].xml(), b'').replace(entries[1].xml(), b'') == SOURCE
    assert catalog(output).names == ('Original', 'First', 'Second')


@pytest.mark.parametrize('name', ['Original', 'original', 'ORIGINAL'])
def test_rejects_case_collisions(name):
    with pytest.raises(AssetError, match='collides'):
        catalog().compose([Entity(name, 'Mesh', 'Tex')])


def test_rejects_distinct_names_with_same_native_hash():
    # djb2: 33*'A'+'b' == 33*'B'+'A', including the terminating NUL.
    with pytest.raises(AssetError, match='collides'):
        catalog().compose([Entity('Ab', 'Mesh', 'Tex'), Entity('BA', 'Mesh', 'Tex')])


@pytest.mark.parametrize('value', ['', '../Mesh', 'a/b', 'a\\b', 'A' * 32, '<model>', 'a\0b', 5])
def test_rejects_unrepresentable_names_before_emission(value):
    with pytest.raises(AssetError): catalog().compose([Entity('Fine', value, 'Tex')])
    with pytest.raises(AssetError): catalog().compose([Entity('Fine', 'Mesh', 'Tex'), Entity(value, 'Mesh', 'Tex')])


def test_rejects_arbitrary_xml_and_unverified_or_ambiguous_baselines():
    with pytest.raises(AssetError): catalog().compose(['<entity/>'])
    with pytest.raises(AssetError, match='hash-verified'): Entities(SOURCE, '0' * 64)
    for data in (b'<entitylist/>', b'<entitylist><entity/></entitylist>',
                 b'<!DOCTYPE entitylist><entitylist></entitylist>', SOURCE + b'</entitylist>'):
        with pytest.raises(AssetError): catalog(data)
