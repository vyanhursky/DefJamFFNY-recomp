"""The titlecard ID getter needs an outfit argument; other ID queries do not."""
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_assets import AssetError
from fighter_menu_outfits import titlecard_outfit_argument


def block(prefix, *, arguments='EA_PushZero', start=0):
    """Native call stack: prefix, argument count, receiver, method, CallMethod."""
    rows = [('EA_PushString', ["value='" + prefix + "'"]), ('Add2', []),
            (arguments, []), ('EA_PushValueOfVar', ["const[3]='oChar'"]),
            ('EA_PushConstantWord', ["const[4]='getID'"]), ('CallMethod', [])]
    return [SimpleNamespace(offset=start + index * 4, name=name, operands=operands)
            for index, (name, operands) in enumerate(rows)]


def test_only_zero_argument_titlecard_call_gets_participant_outfit():
    trace = block('UPDATE: Character number ')
    portrait = block('p_CF_', arguments='EA_PushOne', start=100)
    logo = block('l_CF_', start=200)
    assert titlecard_outfit_argument(trace + portrait + logo) == 208


@pytest.mark.parametrize('rows', [block('p_CF_'), block('l_CF_', arguments='EA_PushOne'),
    block('l_CF_') + block('l_CF_', start=100)])
def test_changed_or_ambiguous_loader_contract_fails_closed(rows):
    with pytest.raises(AssetError, match='titlecard loader differs'):
        titlecard_outfit_argument(rows)


def test_explicit_participant_argument_lookup_is_not_a_global_outfit_override():
    # The distinct zero-arg hero/trace lookup after the logo is intentionally
    # left untouched, even though it is still renamed to the safe alias getter.
    logo = block('l_CF_')
    unrelated = block('CHAR_HERO', start=100)
    assert titlecard_outfit_argument(logo + unrelated) == 8
