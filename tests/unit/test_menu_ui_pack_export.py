"""Synthetic checks for the source-shaped menu pack export table (no artwork needed)."""
import copy
import importlib.util
import json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('menu_pack', REPO/'scripts/export-menu-ui-pack.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

SID = 'a' * 64


def tables(size=(64, 128), art='x/tile.png', pinned='x/tile.png'):
    catalogue = {'schema': 1, 'approval_records': [{'files': [{'path': pinned, 'sha256': 'b' * 64}]}],
                 'reviewed_sources': [{'source_id': SID, 'aliases': [{'width': 16, 'height': 32}]}]}
    exports = {'schema': 1, 'components': {'menu-test': {'name': 'Test', 'png_mips': 'opacity', 'status': 'test',
               'entries': [{'source_id': SID, 'label': 't', 'art': art, 'crop': None, 'size': list(size)}]}}}
    return exports, catalogue


def test_valid_plan_records_pin_and_scale():
    work = mod.plan(*tables())
    assert work['menu-test'][0]['scale'] == 4 and work['menu-test'][0]['pin'] == 'b' * 64


@pytest.mark.parametrize('size', [(64, 64), (48, 128), (144, 288)])
def test_non_uniform_or_out_of_range_scale_is_rejected(size):
    with pytest.raises(ValueError, match='uniform'):
        mod.plan(*tables(size=size))


def test_unpinned_artwork_is_rejected():
    with pytest.raises(ValueError, match='approved pin'):
        mod.plan(*tables(art='x/other.png'))


def test_duplicate_source_ids_are_rejected():
    exports, catalogue = tables()
    exports['components']['menu-second'] = copy.deepcopy(exports['components']['menu-test'])
    with pytest.raises(ValueError, match='twice'):
        mod.plan(exports, catalogue)


def test_tracked_table_matches_tracked_catalogue():
    exports = json.loads((REPO/'config/menu-ui-source-shaped-exports.json').read_text())
    catalogue = json.loads((REPO/'config/menu-ui-approved-artwork.json').read_text())
    work = mod.plan(exports, catalogue)
    assert {k: len(v) for k, v in work.items()} == {'menu-ui-restored-test-v1': 39, 'menu-ui-mode-conditional-test-v1': 8}
