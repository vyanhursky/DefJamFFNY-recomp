"""Local semantic-to-SODB adapter preview. No installer or runtime capability.

Only the caller's hash-verified original database supplies native bindings.
Retail resources are conservative donor bundles, not decoded skeleton/event
proof. New asset resources and unimplemented components fail closed.
"""
from copy import deepcopy
import hashlib
import re

from fighter_registry import SCHEMA, check, fingerprint, resolve, slug
from fighter_sod import Database, CHARACTER
from fighter_names import encode_names
from fighter_bindings import seed, allocate, materialize, symbol, encode_bindings

ADAPTER = 'fighter-native-preview-1'
STATS = {'health': 'Health', 'speed': 'Speed', 'toughness': 'Toughness', 'charisma': 'Charisma'}
RESOURCE_FIELDS = {'appearance': ('Entity', 'Model', 'Shadow', 'BodySize', 'Sex', 'Ethnicity'),
                   'voice': ('SpeechId',), 'portrait': ('Thumb',)}


class RetailCatalog:
    def __init__(self, data, expected_sha256):
        digest = hashlib.sha256(data).hexdigest()
        check(isinstance(expected_sha256, str) and digest == expected_sha256,
              'baseline-hash', 'Native adapter requires the supported original SOD', {'actual_sha256': digest})
        self.db = Database(data)
        check(self.db.schema_fingerprint == 0x86f322ac, 'native-schema', 'Unsupported native schema fingerprint')
        self.source_sha256 = digest
        self._baseline = {'schema': SCHEMA, 'id': 'retail', 'version': '1.0.0',
                          'requires': {}, 'resources': [], 'fighters': [], 'overrides': []}
        self.rows, self.bindings = {}, {}
        for row in self.db.character_metadata()['characters']:
            # Derive public identity from the original native symbol, never its
            # index, display name, core number or file offset. Collisions fail.
            local = re.sub('[^a-z0-9]+', '-', row['name'].lower()).strip('-')
            slug(local)
            identifier = 'retail/' + local
            check(identifier not in self.rows, 'retail-identity', 'Ambiguous retail native names')
            self.rows[identifier] = row
            profile = 'retail/binding-' + local
            components = {'stats': {key: row['fields'][native]['word'] for key, native in STATS.items()}}
            for kind in ('appearance', 'moveset', 'voice', 'portrait'):
                resource_id = local + '-' + kind
                slug(resource_id)
                compatibility = {}
                if kind in ('appearance', 'moveset'):
                    compatibility['skeleton'] = profile
                if kind in ('moveset', 'voice'):
                    compatibility['events'] = profile
                self._baseline['resources'].append({'id': resource_id, 'kind': kind,
                                                     'compatibility': compatibility})
                resource_key = 'retail/' + resource_id
                components[kind] = resource_key
                self.bindings[resource_key] = {'kind': kind, 'donor': identifier}
            self._baseline['fighters'].append({'id': local,
                'name': row['fields']['DisplayName']['symbol'] or row['name'], 'components': components})
        for group in ('fighters', 'resources'):
            self._baseline[group].sort(key=lambda item: item['id'])
        # Also validates donor stats against the semantic schema; never clamp
        # a future native layout into the accepted draft's range.
        resolve(self._baseline, [])

    def baseline(self):
        return deepcopy(self._baseline)

    def compile(self, packs, ledger=None):
        snapshot = resolve(self._baseline, packs)
        ledger = allocate(seed(self.db, self.source_sha256, self.rows), snapshot['fighters'], ledger)
        original = {key: value for key, value in resolve(self._baseline, [])['fighters'].items()}
        additions, edits, donor_keys, localization, portrait_donors = [], [], {}, {}, {}
        for identifier, fighter in snapshot['fighters'].items():
            components = fighter['components']
            unsupported = set(components) - set(RESOURCE_FIELDS) - {'moveset', 'stats'}
            check(not unsupported, 'native-component', 'Native adapter does not yet implement these components',
                  {'fighter': identifier, 'components': sorted(unsupported)})
            check(set(components.get('stats', {})) == set(STATS), 'native-component',
                  'Native preview requires all four stats, explicitly or through inheritance',
                  {'fighter': identifier})
            for group, resource in components.items():
                if group != 'stats':
                    check(resource in self.bindings, 'native-resource', 'Resource needs a native asset adapter',
                          {'fighter': identifier, 'component': group, 'resource': resource})
            donor_key = self.bindings[components['moveset']]['donor']
            donor_keys[identifier] = donor_key
            donor = self.rows[donor_key]
            native_fields = {native: components['stats'][key] for key, native in STATS.items()
                             if key in components.get('stats', {})}
            for group, names in RESOURCE_FIELDS.items():
                check(group in components, 'native-component', 'Native preview needs a complete retail donor bundle',
                      {'fighter': identifier, 'component': group})
                resource_row = self.rows[self.bindings[components[group]]['donor']]
                for name in names:
                    field = resource_row['fields'][name]
                    native_fields[name] = field['symbol'] if field['descriptor'] == 1 else field['word']
            if identifier in self.rows:
                if fighter == original[identifier]:
                    continue
                check(components['moveset'] == original[identifier]['components']['moveset'],
                      'native-core-override', 'Retail core changes need the runtime binding adapter',
                      {'fighter': identifier})
                # Write only differences, preserving unrelated native fields.
                row = self.rows[identifier]
                changed = {name: value for name, value in native_fields.items()
                           if value != row['fields'][name].get('symbol', row['fields'][name]['word'])}
                if changed:
                    edits.append({'template': row['record_offset'], 'fields': changed})
            else:
                portrait_donors[identifier] = self.bindings[components['portrait']]['donor']
                # Public keys can be long and are never copied into bounded
                # native UI fields. Hash collisions are rejected by the builder.
                native_name = symbol(identifier)
                # Native DisplayName is a localization key, not literal text.
                # This cache requires a future merged localization registration.
                native_fields['DisplayName'] = native_name
                localization[native_name] = fighter['name']
                additions.append({'key': identifier, 'native_name': native_name,
                                  'template': donor['record_offset'], 'fields': native_fields})
        output, native = self.db.extend_character_records(additions, edits,
            selection_keys={addition['key']: ledger['fighters'][addition['key']]['selection'] for addition in additions})
        bindings = {key: dict(row['native_binding'], record_offset=row['record_offset'], native_name=row['name'])
                    for key, row in self.rows.items()}
        for key, binding in native['bindings'].items():
            bindings[key] = {'selection_key': binding['selection_key'],
                             'core_id': binding['inherited_core_id'],
                             'record_offset': binding['record_offset'], 'native_name': binding['native_name']}
        report = {'adapter': ADAPTER, 'cache_layout': 2, 'runtime_ready': False, 'launch_allowed': False,
                  'source_sha256': self.source_sha256, 'snapshot_sha256': snapshot['sha256'],
                  'cache_sha256': hashlib.sha256(output).hexdigest(), 'cache_bytes': len(output),
                  'fighter_count': len(snapshot['fighters']), 'added_count': len(additions),
                  'edited_count': len(edits), 'bindings': dict(sorted(bindings.items())),
                  'localization_entries': localization,
                  'moveset_donors': donor_keys, 'portrait_donors': portrait_donors, 'native': native,
                  'binding_ledger': ledger, 'handle_bindings': materialize(Database(output), ledger),
                  'blockers': ['native-selection-and-capacity', 'profile-lifecycle', 'asset-runtime-acceptance',
                               'localization-registration'],
                  'compatibility_policy': 'conservative-retail-donor-bundles'}
        if any(len(label.encode('utf-8')) > 19 for label in localization.values()):
            report['blockers'].append('native-label-buffer')
        report['names_sha256'] = hashlib.sha256(encode_names(localization)).hexdigest()
        report['bindings_sha256'] = hashlib.sha256(encode_bindings(report['handle_bindings'])).hexdigest()
        report['cache_key'] = fingerprint(report)
        return output, report
