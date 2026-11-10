"""Generate data-only AI profiles from a verified local profile/tendency set.

Native stage programs and trigger rules remain inherited. This bounded profile
permits canonical 1..5 tendency values; it is not a raw XML or script loader.
The range is an authoring policy, not a claim about every native consumer.
"""
import hashlib
import re
import struct
import xml.etree.ElementTree as ET

from fighter_archive import Archive
from fighter_assets import AssetError, unpack
from fighter_registry import key

DIFFICULTIES = ('easy', 'normal', 'hard')
FIELDS = (
    'Preferred_Fighting_Distance', 'Attack_versus_Defend', 'Strike_versus_Grapple',
    'Punch_versus_Kick', 'Strong_Punch_versus_Normal_Punch', 'Strong_Kick_versus_Normal_Kick',
    'Strong_Grapple_versus_Normal_Grapple', 'Shove_versus_Grapple_Move', 'Counter_Attempt_versus_Block',
    'Sticky_Grapple_versus_Strike', 'Env_Grapple_versus_Grapple_Move', 'Env_Attack_Frequency',
    'Weapon_Frequency', 'Climb_Object_Frequency', 'Running_Attack_Frequency', 'Combo_Attack_Frequency',
    'Grapple_Defense_Proficiency', 'Strike_Defense_Proficiency', 'Distance_Use_Proficiency',
    'Appeal_Frequency', 'Blazin_Frequency', 'Submit_use_Proficiency', 'Specification_environment',
    'Counter_Use_Frequency',
)
EDITABLE = frozenset(FIELDS) - {'Specification_environment'}


def require(condition, message):
    if not condition:
        raise AssetError(message)


def basename(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,31}', value),
            'AI resource basename is invalid or exceeds the native field')
    return value


def xml(data, root):
    require(isinstance(data, bytes) and 0 < len(data) <= 65536
            and b'<!DOCTYPE' not in data.upper() and b'<!ENTITY' not in data.upper(),
            'AI XML exceeds the bounded data-only profile')
    try:
        result = ET.fromstring(data)
    except ET.ParseError as error:
        raise AssetError('Invalid AI template XML') from error
    require(result.tag == root and all(not e.attrib for e in result.iter()),
            'Unsupported AI root or attributes')
    return result


def children(element, expected):
    require(element is not None and len(element) == len(expected)
            and {e.tag for e in element} == set(expected), 'AI template fields differ')


def encoded(element):
    result = ET.tostring(element, encoding='utf-8', xml_declaration=True)
    require(len(result) <= 65536, 'Generated AI XML exceeds budget')
    return result


class AIProfiles:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and hashlib.sha256(data).hexdigest() == expected_sha256,
                'AI templates require a verified local archive')
        self.archive, self.source_sha256 = Archive(data), expected_sha256
        self.names = {entry.name.casefold() for entry in self.archive.entries}

    def read(self, name):
        return unpack(self.archive.read('assets/ai/' + basename(name) + '.xml'))

    def compose(self, resources):
        require(type(resources) is dict and 0 < len(resources) <= 4096, 'AI profile population exceeds budget')
        for identifier in resources:
            key(identifier)
        additions, bindings = {}, {}

        def add(name, payload):
            path = 'assets/ai/' + name + '.xml'
            require(path.casefold() not in self.names and path not in additions, 'Generated AI resource collision')
            additions[path] = payload

        for identifier, resource in sorted(resources.items()):
            require(type(resource) is dict and set(resource) == {'template_profile', 'tendencies'},
                    'AI resource needs an explicit profile and typed tendencies')
            donor = basename(resource['template_profile'])
            require(re.fullmatch(r'cha(?:r\d{4}|\d{5})', donor), 'Unsupported retail AI profile family')
            profile = xml(self.read(donor), 'artficial_intelligence')
            children(profile, ('tendency_list', 'trigger_list', 'Attribute_list', 'AI_difficulty'))
            tendencies = profile.find('tendency_list')
            children(tendencies, DIFFICULTIES)
            for difficulty in DIFFICULTIES:
                children(tendencies.find(difficulty), [f'tendency{i}' for i in range(4)])
                for field in tendencies.find(difficulty):
                    require(not len(field), 'Nested AI tendency reference')
                    self.read(basename(field.text))  # No silent native fallback.
            triggers = profile.find('trigger_list')
            children(triggers, [f'stage{i:02}' for i in range(28)])
            for field in triggers:
                require(not len(field), 'Nested AI trigger reference')
                self.read(basename(field.text))  # Original bytes remain inherited.
            edits = resource['tendencies']
            require(type(edits) is dict and set(edits) <= set(DIFFICULTIES), 'Unknown AI difficulty')
            owned = {}
            for difficulty, slots in sorted(edits.items()):
                require(type(slots) is dict and len(slots) <= 4
                        and all(type(slot) is int and 0 <= slot < 4 for slot in slots), 'Invalid AI tendency slot')
                for slot, values in sorted(slots.items()):
                    require(type(values) is dict and values and set(values) <= EDITABLE,
                            'Unknown or inherited-only AI tendency field')
                    require(all(type(v) is int and 1 <= v <= 5 for v in values.values()),
                            'AI tendency values must be canonical integers in 1..5')
                    field = tendencies.find(difficulty + f'/tendency{slot}')
                    tendency = xml(self.read(field.text), 'tendencies')
                    children(tendency, FIELDS)
                    require(all(not len(item) and isinstance(item.text, str)
                                and re.fullmatch(r'[0-9]{1,3}', item.text) for item in tendency),
                            'Unsupported inherited tendency numeric fields')
                    for name, value in values.items():
                        tendency.find(name).text = str(value)
                    name = 'fmt' + hashlib.sha256(f'{identifier}/{difficulty}/{slot}'.encode()).hexdigest()[:24]
                    data = encoded(tendency); add(name, data); field.text = name
                    owned[name] = {'sha256': hashlib.sha256(data).hexdigest(), 'fields': values.copy()}
            name = 'fma' + hashlib.sha256(identifier.encode()).hexdigest()[:24]
            data = encoded(profile); add(name, data)
            bindings[identifier] = {'profile': name, 'template_profile': donor,
                                   'sha256': hashlib.sha256(data).hexdigest(), 'owned_tendencies': owned}
        result = self.archive.compose(additions=additions)
        return result, {'schema': 'fighter-ai-archive-1', 'source_sha256': self.source_sha256,
                        'sha256': hashlib.sha256(result).hexdigest(), 'bytes': len(result),
                        'bindings': bindings, 'runtime_ready': False}


def encode_ai_bindings(data, report, cores):
    from fighter_behavior_identity import valid, CAF_BIT, population
    require(type(report) is dict and report.get('schema') == 'fighter-ai-archive-1'
            and isinstance(data, bytes) and report.get('bytes') == len(data)
            and report.get('sha256') == hashlib.sha256(data).hexdigest(),
            'AI archive differs from its composition receipt')
    require(population(cores), 'AI binding requires an owned core or CAF identity within the supported population')
    archive, rows = Archive(data), []
    for core, identifier in sorted(cores.items()):
        require(valid(core) and identifier in report['bindings'],
                'AI binding requires an owned core and known profile')
        binding = report['bindings'][identifier]
        name = basename(binding['profile'])
        for target, expected in [(name, binding['sha256']),
                                 *((n, v['sha256']) for n, v in binding['owned_tendencies'].items())]:
            value = archive.read('assets/ai/' + basename(target) + '.xml')
            require(hashlib.sha256(value).hexdigest() == expected, 'AI resource differs from its receipt')
        rows.append(struct.pack('<I32s', core, name.encode('ascii')))
    version2=any(key & CAF_BIT for key in cores)
    return (b'FIA2' if version2 else b'FIA1') + struct.pack('<3I', 2 if version2 else 1, len(rows), len(data)) + bytes.fromhex(report['sha256']) + b''.join(rows)
