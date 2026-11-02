"""Draft semantic fighter resolver; independent of native IDs and game execution.

This is the compiler/resolver layer, not an installer or advertised runtime
capability. Native asset decoding, engine bindings and save bridges remain
separate acceptance gates. No input specifies addresses, executable hooks or
whole-database replacements. Conflict reports are data suitable for a helper UI.
"""
from copy import deepcopy
import hashlib
import json
import re


SCHEMA = 'fighter-registry-draft-1'
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
VERSION = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\Z')
GROUPS = {'appearance': 'appearance', 'moveset': 'moveset', 'voice': 'voice',
          'ai': 'ai', 'portrait': 'portrait', 'intro': 'cinematic',
          'victory': 'cinematic', 'blazin': 'cinematic'}
COMPATIBILITY = {'appearance': {'skeleton'}, 'moveset': {'skeleton', 'events'},
                 'voice': {'events'}, 'ai': set(), 'portrait': set(),
                 'cinematic': {'skeleton', 'events'}}
STATS = {'health', 'speed', 'toughness', 'charisma'}
MAX_DEFINITIONS = 16384
MAX_PACKS = 1024
MAX_DEPTH = 128


class RegistryError(ValueError):
    def __init__(self, code, message, details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}

    def report(self):
        return {'code': self.code, 'message': str(self), 'details': self.details}


def check(condition, code, message, details=None):
    if not condition:
        raise RegistryError(code, message, details)


def fields(value, required, optional=()):
    check(isinstance(value, dict) and set(required) <= value.keys()
          and value.keys() <= set(required) | set(optional), 'schema',
          'Missing or unknown fields', {'required': sorted(required)})


def slug(value):
    check(isinstance(value, str) and len(value) <= 80 and SLUG.fullmatch(value),
          'identity', 'Invalid stable identity')
    return value


def key(value):
    check(isinstance(value, str) and value.count('/') == 1, 'identity', 'Expected pack-id/local-id')
    for part in value.split('/'):
        slug(part)
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def components(value):
    check(isinstance(value, dict) and value.keys() <= GROUPS.keys() | {'stats'},
          'component', 'Unknown fighter component')
    for group, content in value.items():
        if group == 'stats':
            check(isinstance(content, dict) and content and content.keys() <= STATS,
                  'stats', 'Unknown or empty stats group')
            check(all(type(v) is int and 0 <= v <= 100 for v in content.values()),
                  'stats', 'Stats must be integers from 0 to 100')
        else:
            key(content)


def validate_pack(pack, builtin=False):
    fields(pack, {'schema', 'id', 'version', 'requires', 'resources', 'fighters', 'overrides'})
    check(pack['schema'] == SCHEMA, 'schema', 'Unsupported fighter draft schema')
    owner = slug(pack['id'])
    check((owner == 'retail') == builtin, 'identity', 'The retail namespace is reserved')
    check(isinstance(pack['version'], str) and VERSION.fullmatch(pack['version']),
          'version', 'Expected a stable semantic version')
    check(isinstance(pack['requires'], dict), 'dependency', 'Expected dependency version map')
    for dependency, version in pack['requires'].items():
        slug(dependency)
        check(dependency not in (owner, 'retail') and isinstance(version, str) and VERSION.fullmatch(version),
              'dependency', 'Invalid dependency/version')
    for group in ('resources', 'fighters', 'overrides'):
        check(isinstance(pack[group], list) and len(pack[group]) <= MAX_DEFINITIONS,
              'budget', 'Invalid/oversized definitions list')
    seen = set()
    for resource in pack['resources']:
        fields(resource, {'id', 'kind', 'compatibility'})
        identifier = slug(resource['id'])
        check(identifier not in seen, 'duplicate-resource', 'Duplicate resource identity')
        seen.add(identifier)
        kind = resource['kind']
        check(isinstance(kind, str) and kind in COMPATIBILITY, 'resource', 'Unknown resource kind')
        fields(resource['compatibility'], COMPATIBILITY[kind])
        for value in resource['compatibility'].values():
            key(value)
    seen = set()
    for fighter in pack['fighters']:
        fields(fighter, {'id', 'name', 'components'}, {'inherits'})
        identifier = slug(fighter['id'])
        check(identifier not in seen, 'duplicate-fighter', 'Duplicate fighter identity')
        seen.add(identifier)
        check(isinstance(fighter['name'], str) and 0 < len(fighter['name']) <= 256
              and not any(ord(c) < 32 or 0xd800 <= ord(c) <= 0xdfff for c in fighter['name']),
              'name', 'Invalid fighter display name')
        if 'inherits' in fighter:
            key(fighter['inherits'])
        components(fighter['components'])
    seen = set()
    for override in pack['overrides']:
        fields(override, {'target', 'components', 'supersedes'})
        key(override['target'])
        components(override['components'])
        check(override['components'], 'component', 'Empty override')
        check(isinstance(override['supersedes'], list) and len(override['supersedes']) <= 1024,
              'override', 'Invalid supersedes list')
        for previous in override['supersedes']:
            slug(previous)
            check(previous in pack['requires'], 'override', 'A superseded pack must be an exact dependency')
        check(len(set(override['supersedes'])) == len(override['supersedes']),
              'override', 'Duplicate superseded pack')
        for group in override['components']:
            claim = (override['target'], group)
            check(claim not in seen, 'duplicate-override', 'One pack edits a component twice')
            seen.add(claim)
    check(not builtin or not pack['requires'] and not pack['overrides'],
          'schema', 'Retail baseline cannot depend on or override packs')
    return pack


def resolve(baseline, packs):
    """Resolve whole enabled packs. Inputs are never modified; no native IDs allocated."""
    validate_pack(baseline, builtin=True)
    check(isinstance(packs, list) and len(packs) <= MAX_PACKS, 'budget', 'Invalid enabled pack list')
    documents = {'retail': deepcopy(baseline)}
    total = sum(len(baseline[k]) for k in ('fighters', 'resources', 'overrides'))
    check(total <= MAX_DEFINITIONS, 'budget', 'Resolved registry exceeds definition budget')
    for pack in packs:
        validate_pack(pack)
        check(pack['id'] not in documents, 'duplicate-pack', 'Pack identity enabled twice')
        total += sum(len(pack[k]) for k in ('fighters', 'resources', 'overrides'))
        check(total <= MAX_DEFINITIONS, 'budget', 'Resolved registry exceeds definition budget')
        documents[pack['id']] = deepcopy(pack)
    for owner, pack in documents.items():
        for required, version in pack['requires'].items():
            check(required in documents, 'missing-dependency', f'{owner} requires {required}',
                  {'pack': owner, 'dependency': required, 'version': version})
            check(documents[required]['version'] == version, 'dependency-version',
                  f'{owner} requires {required} version {version}',
                  {'pack': owner, 'dependency': required, 'required': version,
                   'enabled': documents[required]['version']})
    visiting, completed = set(), set()

    def visit(owner, depth=0):
        check(depth <= MAX_DEPTH and owner not in visiting, 'dependency-cycle', 'Dependency cycle/depth limit')
        if owner in completed:
            return
        visiting.add(owner)
        for required in sorted(documents[owner]['requires']):
            visit(required, depth + 1)
        visiting.remove(owner)
        completed.add(owner)

    for owner in sorted(documents):
        visit(owner)
    resources, definitions = {}, {}
    for owner, pack in documents.items():
        for resource in pack['resources']:
            resources[owner + '/' + resource['id']] = dict(resource, owner=owner)
        for fighter in pack['fighters']:
            definitions[owner + '/' + fighter['id']] = dict(fighter, owner=owner)

    def reference(owner, target):
        provider = key(target).split('/')[0]
        check(provider in (owner, 'retail') or provider in documents[owner]['requires'],
              'undeclared-dependency', f'{owner} must declare resource/fighter provider {provider}')

    resolved, ancestry = {}, set()

    def fighter(identifier, depth=0):
        check(depth <= MAX_DEPTH and identifier not in ancestry, 'inheritance-cycle', 'Fighter inheritance cycle/depth limit')
        check(identifier in definitions, 'missing-fighter', f'Unknown fighter {identifier}')
        if identifier in resolved:
            return resolved[identifier]
        source = definitions[identifier]
        ancestry.add(identifier)
        values = {}
        if 'inherits' in source:
            reference(source['owner'], source['inherits'])
            values = deepcopy(fighter(source['inherits'], depth + 1)['components'])
        for group, value in source['components'].items():
            if group == 'stats':
                values.setdefault(group, {}).update(deepcopy(value))
            else:
                values[group] = deepcopy(value)
        for group, value in source['components'].items():
            if group != 'stats':
                reference(source['owner'], value)
        ancestry.remove(identifier)
        resolved[identifier] = {'name': source['name'], 'components': values}
        return resolved[identifier]

    for identifier in sorted(definitions):
        fighter(identifier)
    # Inheritance copies the authored donor definition before patching. Patching
    # a donor must not silently mutate an independently added fighter's components.
    claims = {}
    for owner in sorted(documents):
        for override in documents[owner]['overrides']:
            target = override['target']
            reference(owner, target)
            check(target in resolved, 'missing-fighter', f'Unknown override target {target}')
            for group, value in override['components'].items():
                if group != 'stats':
                    reference(owner, value)
                claims.setdefault((target, group), []).append((owner, value, set(override['supersedes'])))
    conflicts, winners = [], {}
    for (target, group), rows in sorted(claims.items()):
        live = [row for row in rows if not any(row[0] in other[2] for other in rows)]
        if not live or len({canonical(row[1]) for row in live}) != 1:
            conflicts.append({'fighter': target, 'component': group,
                              'providers': sorted(row[0] for row in rows),
                              'choices': [{'pack': row[0], 'value': row[1]} for row in rows],
                              'resolution': 'Disable a conflicting pack or add a declared compatibility override.'})
            continue
        value = deepcopy(live[0][1])
        if group == 'stats':
            resolved[target]['components'].setdefault(group, {}).update(value)
        else:
            resolved[target]['components'][group] = value
        winners[target + ':' + group] = sorted(row[0] for row in live)
    check(not conflicts, 'component-conflict', 'Fighter components have incompatible edits', {'conflicts': conflicts})
    for identifier, value in sorted(resolved.items()):
        refs = {}
        for group, resource_key in value['components'].items():
            if group == 'stats':
                continue
            check(resource_key in resources, 'missing-resource', f'{identifier} references missing {resource_key}')
            resource = resources[resource_key]
            check(resource['kind'] == GROUPS[group], 'resource-kind', f'{identifier} has wrong resource kind for {group}')
            refs[group] = resource['compatibility']
        skeletons = {r['skeleton'] for r in refs.values() if 'skeleton' in r}
        events = {r['events'] for r in refs.values() if 'events' in r}
        check(len(skeletons) <= 1, 'skeleton-conflict', f'{identifier} has incompatible model/animation skeletons')
        check(len(events) <= 1, 'event-conflict', f'{identifier} has incompatible voice/animation event sets')
        check('appearance' in refs and 'moveset' in refs, 'incomplete-fighter', f'{identifier} needs appearance and moveset')
    lock = {owner: {'version': p['version'], 'sha256': fingerprint(p)} for owner, p in sorted(documents.items())}
    snapshot = {'schema': SCHEMA, 'runtime_ready': False, 'packages': lock,
                'fighters': dict(sorted(resolved.items())), 'resources': dict(sorted(resources.items())),
                'overrides': winners}
    snapshot['sha256'] = fingerprint(snapshot)
    return snapshot


def suggest_compatibility(baseline, packs, identifier, choices):
    """Build a draft patch from explicit conflict choices; never install it.

    Every conflicting target/component needs a provider choice. The final
    composition is resolved again, so choosing components cannot bypass the
    skeleton/event checks. Dependencies pin release versions; the preview hash
    also records exact document content. Asset adaptation remains outside this helper.
    """
    slug(identifier)
    check(identifier != 'retail', 'identity', 'Compatibility pack needs a new identity')
    check(isinstance(choices, dict), 'choice', 'Expected explicit conflict choices')
    try:
        resolve(baseline, packs)
    except RegistryError as error:
        if error.code != 'component-conflict':
            raise
        conflicts = error.details['conflicts']
    else:
        raise RegistryError('no-conflicts', 'Enabled packs do not need a component compatibility patch')
    check(all(p['id'] != identifier for p in packs), 'identity',
          'Compatibility pack needs a new identity')
    required = {row['fighter'] + ':' + row['component'] for row in conflicts}
    check(set(choices) == required, 'choice', 'Choose one provider for every conflicting component',
          {'required': sorted(required)})
    documents = {p['id']: p for p in packs}
    patch = {'schema': SCHEMA, 'id': identifier, 'version': '1.0.0', 'requires': {},
             'resources': [], 'fighters': [], 'overrides': []}
    for row in conflicts:
        selected = choices[row['fighter'] + ':' + row['component']]
        candidates = {choice['pack']: choice['value'] for choice in row['choices']}
        check(isinstance(selected, str) and selected in candidates, 'choice',
              'Choice must name a provider listed in the conflict', {'providers': row['providers']})
        value = deepcopy(candidates[selected])
        providers = set(row['providers']) | {row['fighter'].split('/')[0]}
        if row['component'] != 'stats':
            providers.add(value.split('/')[0])
        for provider in sorted(providers - {'retail'}):
            patch['requires'][provider] = documents[provider]['version']
        patch['overrides'].append({'target': row['fighter'], 'components': {row['component']: value},
                                   'supersedes': row['providers']})
    preview = resolve(baseline, packs + [patch])
    return {'runtime_ready': False, 'patch': patch, 'preview_sha256': preview['sha256']}
