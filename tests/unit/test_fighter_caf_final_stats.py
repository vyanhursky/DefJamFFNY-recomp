"""Explicit final attributes, independent of training and shared across outfits."""
import copy
import hashlib
import json
import struct
import pytest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"setup"))
import fighter_caf
from fighter_caf_layout import RECIPE as R
from test_fighter_caf_outfits import fixture

ATTRIBUTES = dict(zip(fighter_caf.STAT_KEYS, (30, 47, 37, 27, 47, 30)))


@pytest.mark.parametrize('bad', [None, {}, dict(ATTRIBUTES, charisma=True), dict(ATTRIBUTES, charisma=101),
                               dict(ATTRIBUTES, charisma=-1), dict(ATTRIBUTES, upper=1.5), dict(ATTRIBUTES, unknown=1)])
def test_invalid_final_attributes_refused(bad):
    with pytest.raises(ValueError):
        fighter_caf.final_stats(bad)


def test_final_attributes_encode_exact_menu_values_and_all_outfits():
    item, report = fixture()
    baseline = fighter_caf.encode_rows({'example/fighter': item}, report)[1]
    for outfit in item['outfits']:
        outfit['recipe']['final_stats'] = dict(ATTRIBUTES)
    count, raw = fighter_caf.encode_rows({'example/fighter': item}, report)
    for i in range(count):
        row = raw[i*240:(i+1)*240]
        assert row[R['final_stats']] == 1 and row[R['charisma']] == 30
        assert struct.unpack_from('<5I', row, R['training']) == (30,47,37,27,47)
        menu = fighter_caf.menu_record(item['outfits'][i]['recipe'], 100)
        assert menu['stats'] == dict(zip('ULSTHC', ATTRIBUTES.values()))
        # No other compiled fields change; old rows remain byte-for-byte stable.
        expected = bytearray(baseline[i*240:(i+1)*240])
        expected[R['training']:R['training']+20] = struct.pack('<5I',30,47,37,27,47)
        expected[R['final_stats']] = 1; expected[R['charisma']] = 30
        assert row == bytes(expected)


def test_optional_shared_field_wraps_every_existing_loader(tmp_path, monkeypatch):
    catalog = type('Catalog', (), {'rows': {}})()
    # Exercise the real top-level admission with synthetic lower loaders, including legacy single-outfit recipes.
    for section in ({}, {'outfits': []}, {'retail_moveset': 'retail/example'}):
        clean = dict(stats={}, styles=[0], caf_values=[], caf_colors=[], **section)
        document = dict(clean, final_stats=ATTRIBUTES)
        raw = json.dumps(document).encode(); (tmp_path/'fighter.json').write_bytes(raw)
        def lower(root, value, cat, game):
            assert value == clean
            recipe = {'stats': {}, 'styles': [0]}
            return {'recipe': recipe, 'outfits': [{'recipe': recipe}, {'recipe': copy.deepcopy(recipe)}]}
        monkeypatch.setattr(fighter_caf, 'load_flat', lower)
        import fighter_caf_face, fighter_caf_moveset
        monkeypatch.setattr(fighter_caf_face, 'load_recipe', lower)
        monkeypatch.setattr(fighter_caf_moveset, 'load_recipe', lower)
        result = fighter_caf.load(tmp_path, {'format': fighter_caf.FORMAT,
            'selection': {'path':'fighter.json','sha256':hashlib.sha256(raw).hexdigest()}}, catalog, tmp_path)
        assert all(o['recipe']['final_stats'] == ATTRIBUTES for o in result['outfits'])
