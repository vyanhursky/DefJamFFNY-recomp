"""Game-free native cinematic registration and inheritance checks."""
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_cinematics import Cinematic, Cinematics, AssetError

SOURCE = (b'<tauntslist><taunt><name>Donor</name><name>Alternate</name>'
          b'<intro>Intro</intro><extro>Victory</extro></taunt></tauntslist>\r\n')
BANKS = {'Intro', 'Victory'}


def catalog(source=SOURCE):
    return Cinematics(source, hashlib.sha256(source).hexdigest())


def test_inherits_each_alias_and_preserves_original_bytes():
    source = catalog()
    assert source.compose([], BANKS) == SOURCE
    a, b = source.inherit('Alpha', 'Donor'), source.inherit('Beta', 'Alternate')
    output = source.compose([b, a], BANKS)
    assert output == source.compose([a, b], BANKS)
    assert output.replace(a.xml(), b'').replace(b.xml(), b'') == SOURCE
    assert catalog(output).bindings['alpha'] == a


def test_missing_donor_or_animation_is_actionable():
    with pytest.raises(AssetError, match='donor'): catalog().inherit('New', 'Missing')
    with pytest.raises(AssetError, match='missing animation'):
        catalog().compose([Cinematic('New', 'Intro', 'Absent')], BANKS)


def test_preserves_created_fighter_variants_without_choosing_one():
    variant = (b'<taunt><name>Created</name><intro><count>2</count><name>I1</name><name>I2</name></intro>'
               b'<extro><count>2</count><name>E1</name><name>E2</name></extro></taunt>')
    data = SOURCE.replace(b'</tauntslist>', variant + b'</tauntslist>')
    source = catalog(data)
    assert source.compose([], BANKS) == data
    with pytest.raises(AssetError, match='variants'): source.inherit('New', 'Created')
    with pytest.raises(AssetError, match='collides'):
        source.compose([Cinematic('Created', 'Intro', 'Victory')], BANKS)
    with pytest.raises(AssetError, match='variants'): catalog(data.replace(b'<count>2', b'<count>3'))


@pytest.mark.parametrize('name', ['Donor', 'DONOR', 'alternate'])
def test_existing_aliases_cannot_be_replaced(name):
    with pytest.raises(AssetError, match='collides'):
        catalog().compose([Cinematic(name, 'Intro', 'Victory')], BANKS)


def test_multiple_packs_cannot_claim_same_native_name():
    with pytest.raises(AssetError, match='collides'):
        catalog().compose([Cinematic('New', 'Intro', 'Victory'), Cinematic('NEW', 'Intro', 'Victory')], BANKS)


@pytest.mark.parametrize('value', ['../clip', '<name>', 'x' * 32, '', None, 7])
def test_rejects_non_names_before_emitting_xml(value):
    with pytest.raises(AssetError): catalog().compose([Cinematic('New', value, 'Victory')], BANKS)


def test_rejects_xml_injection_and_unverified_or_ambiguous_baselines():
    with pytest.raises(AssetError): catalog().compose(['<taunt/>'], BANKS)
    with pytest.raises(AssetError, match='hash-verified'): Cinematics(SOURCE, '0' * 64)
    for data in (b'<tauntslist/>', b'<!DOCTYPE tauntslist>' + SOURCE,
                 SOURCE.replace(b'<intro>Intro</intro>', b''),
                 SOURCE.replace(b'<intro>Intro</intro>', b'<intro>Intro</intro><intro>Again</intro>'),
                 SOURCE.replace(b'Alternate', b'Donor'),
                 SOURCE.replace(b'<name>Donor</name>', b'<name><nested/></name>')):
        with pytest.raises(AssetError): catalog(data)
