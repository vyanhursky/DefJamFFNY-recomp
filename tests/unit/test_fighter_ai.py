"""AI authoring emits bounded data and keeps original trigger/stage ownership."""
import hashlib
import struct
import xml.etree.ElementTree as ET

import pytest

from test_fighter_archive import fixture
from fighter_ai import AIProfiles, DIFFICULTIES, FIELDS, encode_ai_bindings
from fighter_archive import Archive
from fighter_assets import AssetError


def source():
    root = ET.Element('artficial_intelligence')
    tendencies = ET.SubElement(root, 'tendency_list')
    for difficulty in DIFFICULTIES:
        level = ET.SubElement(tendencies, difficulty)
        for slot in range(4):
            ET.SubElement(level, f'tendency{slot}').text = 'tend0001'
    triggers = ET.SubElement(root, 'trigger_list')
    for stage in range(28):
        ET.SubElement(triggers, f'stage{stage:02}').text = 'trig0001'
    ET.SubElement(root, 'Attribute_list')
    ET.SubElement(root, 'AI_difficulty')
    tend = ET.Element('tendencies')
    for field in FIELDS:
        ET.SubElement(tend, field).text = '3'
    data = fixture({'assets/ai/char0005.xml': ET.tostring(root),
                    'assets/ai/tend0001.xml': ET.tostring(tend),
                    'assets/ai/trig0001.xml': b'<original_trigger/>',
                    'assets/ai/stage000.ai': b'original-stage-data'})
    return data, AIProfiles(data, hashlib.sha256(data).hexdigest())


def profile(value=5):
    return {'template_profile': 'char0005', 'tendencies': {'normal': {0: {'Attack_versus_Defend': value}}}}


def test_two_profiles_have_distinct_names_and_tendencies_without_replacing_originals():
    original, compiler = source()
    data, report = compiler.compose({'alpha/ai': profile(), 'beta/ai': profile(1)})
    before, after = Archive(original), Archive(data)
    assert all(after.read(e.name) == before.read(e.name) for e in before.entries)
    names = []
    for key, expected in (('alpha/ai', '5'), ('beta/ai', '1')):
        binding = report['bindings'][key]; names.append(binding['profile'])
        parsed = ET.fromstring(after.read('assets/ai/' + binding['profile'] + '.xml'))
        replacement = parsed.findtext('tendency_list/normal/tendency0')
        tendency = ET.fromstring(after.read('assets/ai/' + replacement + '.xml'))
        assert tendency.findtext('Attack_versus_Defend') == expected
        assert tendency.findtext('Specification_environment') == '3'
        assert parsed.findtext('tendency_list/normal/tendency1') == 'tend0001'
        assert parsed.findtext('trigger_list/stage00') == 'trig0001'
    assert names[0] != names[1] and all(len(name) <= 31 for name in names)
    table = encode_ai_bindings(data, report, {256: 'alpha/ai', 257: 'beta/ai', 1000: 'alpha/ai'})
    assert table[:4] == b'FIA1' and struct.unpack_from('<3I', table, 4) == (1, 3, len(data))
    assert len(table) == 48 + 3 * 36
    assert struct.unpack_from('<I32s', table, 48) == (256, names[0].encode().ljust(32, b'\0'))


@pytest.mark.parametrize('value', [0, 6, True, 3.5, '3', '3; run()', '9' * 256])
def test_numeric_authoring_rejects_parser_truncation_overflow_and_expressions(value):
    _, compiler = source()
    with pytest.raises(AssetError, match='canonical integers'):
        compiler.compose({'alpha/ai': profile(value)})


@pytest.mark.parametrize('edits', [{'nightmare': {}}, {'normal': {4: {'Attack_versus_Defend': 3}}},
    {'normal': {True: {'Attack_versus_Defend': 3}}}, {'normal': {0: {'Specification_environment': 3}}},
    {'normal': {0: {'native_code': 3}}}])
def test_unimplemented_fields_difficulties_and_slots_fail(edits):
    _, compiler = source()
    with pytest.raises(AssetError):
        compiler.compose({'alpha/ai': {'template_profile': 'char0005', 'tendencies': edits}})


def test_pure_inheritance_and_shared_profile_are_explicit():
    _, compiler = source()
    data, report = compiler.compose({'alpha/ai': {'template_profile': 'char0005', 'tendencies': {}}})
    assert not report['bindings']['alpha/ai']['owned_tendencies']
    table = encode_ai_bindings(data, report, {256: 'alpha/ai', 257: 'alpha/ai'})
    assert table[52:84] == table[88:120]


def test_archive_and_resource_receipts_are_revalidated():
    original, compiler = source()
    with pytest.raises(AssetError, match='verified'):
        AIProfiles(original, '0' * 64)
    data, report = compiler.compose({'alpha/ai': profile()})
    with pytest.raises(AssetError, match='owned core'):
        encode_ai_bindings(data, report, {140: 'alpha/ai'})
    report['bindings']['alpha/ai']['sha256'] = '0' * 64
    with pytest.raises(AssetError, match='resource differs'):
        encode_ai_bindings(data, report, {256: 'alpha/ai'})


def test_raw_xml_and_stage_programs_cannot_enter_the_authoring_request():
    _, compiler = source()
    with pytest.raises(AssetError, match='typed tendencies'):
        compiler.compose({'alpha/ai': {**profile(), 'script': b'anything'}})
