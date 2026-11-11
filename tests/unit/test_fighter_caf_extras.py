"""Bounded, hash-bound CAF art admission and independent compiled sidecars."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_caf_extras import encode_section, load, PIXELS, finishers
from fighter_caf_layout import EXTRA as E, EXTRA_STRIDE as ROW
from fighter_caf import source


def atlas(root, size=(256, 256)):
    stream = io.BytesIO(); Image.new('RGBA', size, (11, 22, 33, 44)).save(stream, format='PNG')
    raw = stream.getvalue(); (root / 'atlas.png').write_bytes(raw)
    return {'path': 'atlas.png', 'sha256': hashlib.sha256(raw).hexdigest()}


def test_v2_source_and_atlas_hash_dimensions_channels(tmp_path):
    source({'format': 'caf-fighter-1', 'selection': {'path': 'fighter.json', 'sha256': 'a' * 64}})
    descriptor = atlas(tmp_path)
    result = load(tmp_path, {'atlases': {'a': descriptor}}, None)
    assert result['finishers'] is None and result['atlases']['a'][:4] == bytes((33, 22, 11, 44))
    (tmp_path / 'atlas.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash'):
        load(tmp_path, {'atlases': {'a': descriptor}}, None)
    descriptor = atlas(tmp_path, (128, 128))
    with pytest.raises(ValueError, match='256x256'):
        load(tmp_path, {'atlases': {'a': descriptor}}, None)


def test_atlas_descriptor_traversal_unknown_slot_and_field_refused(tmp_path):
    descriptor = atlas(tmp_path)
    for value in ({'atlases': {'other': descriptor}}, {'executable': 'run'},
                  {'atlases': {'a': dict(descriptor, path='../atlas.png')}}):
        with pytest.raises(ValueError):
            load(tmp_path, value, None)


def test_sidecar_deduplicates_art_but_retains_independent_fighter_choices():
    pixels = bytes((1, 2, 3, 4)) * (256 * 256)
    entries = {'pack/first': {'extras': {'finishers': [3, 5, 7, 11], 'atlases': {'a': pixels}}},
               'pack/second': {'extras': {'finishers': None, 'atlases': {'d1': pixels}}}}
    report = {'bindings': {'pack/first': {'selection_key': 100}, 'pack/second': {'selection_key': 101}}}
    count, raw = encode_section(entries, report)
    assert count == 2 and len(raw) == 2 * ROW + PIXELS
    first, second = (struct.unpack_from('<12I', raw, i * ROW) for i in range(2))
    assert first[:6] == (100, 1, 3, 5, 7, 11) and second[:6] == (101, 0, 0, 0, 0, 0)
    # Atlas offsets count from the start of the extras section, and one block serves both fighters.
    assert first[6] == second[10] == 2 * ROW
    assert struct.unpack_from('<I', raw, E['outfit'])[0] == 0
    assert encode_section({'old': {'recipe': {}}}, {}) == (0, b'')


def test_finisher_identity_join_refuses_unknown_rows_and_schema():
    from types import SimpleNamespace
    class Database:
        schema = {0x47D305FD ^ 0x6FC83815: (4, 2)}
        directory = {0x47D305FD: 100}
        def table(self, table):
            assert table == 0x47D305FD
        def index(self, at, tagged=False):
            return SimpleNamespace(keys=(0x47D305FD,), values=((200,),)) if at == 116 else SimpleNamespace(keys=(123,), values=((300,),))
        def word(self, at):
            assert at == 316
            return 17
    database = Database()
    assert finishers(['0000007b'] * 4, database) == [17] * 4
    with pytest.raises(ValueError, match='absent'):
        finishers(['0000007c'] * 4, database)
    database.schema = {}
    with pytest.raises(ValueError, match='schema'):
        finishers(['0000007b'] * 4, database)


@pytest.mark.parametrize('damage', [None, 'png', 'recipe', 'undeclared', 'traversal'])
def test_package_inventory_follows_only_hash_bound_declared_atlases(tmp_path, damage):
    from fighter_packages import inventory
    descriptor = atlas(tmp_path)
    recipe = {'atlases': {'a': descriptor}}
    if damage == 'traversal':
        descriptor['path'] = '../atlas.png'
    raw = json.dumps(recipe).encode()
    (tmp_path / 'fighter.json').write_bytes(raw)
    manifest = {'schema': 'fighter-registry-draft-1', 'id': 'example', 'version': '1.0.0', 'requires': {},
                'resources': [{'id': 'caf', 'kind': 'caf', 'compatibility': {},
                  'source': {'format': 'caf-fighter-1', 'selection': {'path': 'fighter.json', 'sha256': hashlib.sha256(raw).hexdigest()}}}],
                'fighters': [{'id': 'fighter', 'name': 'Example', 'inherits': 'retail/blaze', 'components': {'caf': 'example/caf'}}], 'overrides': []}
    (tmp_path / 'fighters.json').write_text(json.dumps(manifest))
    if damage == 'png':
        (tmp_path / 'atlas.png').write_bytes(b'changed')
    elif damage == 'recipe':
        (tmp_path / 'fighter.json').write_bytes(b'{}')
    elif damage == 'undeclared':
        (tmp_path / 'extra.png').write_bytes(b'undeclared')
    if damage:
        with pytest.raises(ValueError):
            inventory(tmp_path)
    else:
        assert inventory(tmp_path)['id'] == 'example'
