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
from fighter_window import BANKS, FIRST_SELECTION, MAX_FIGHTERS, bank_key, build_window, encode_window

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

    def menu_record(self, donor, components, selection):
        # Raw member hashes/roles checked against native GetNextFighter's
        # CLOTH/FE_ID/LOCK/U/L/S/T/H/C/K formatter. No guessed schema names.
        roles = {'U': (0xE2824A3D, 17), 'L': (0xCD759ABA, 16)}
        stats = {}
        for role, (member, position) in roles.items():
            check(self.db.schema.get(member ^ CHARACTER) == (position, 2), 'native-menu-schema',
                  'Native menu power field differs from the audited layout')
            stats[role] = self.db.word(donor['record_offset'] + position * 4)
        stats.update({letter: components['stats'][name] for letter, name in
                      [('S', 'speed'), ('T', 'toughness'), ('H', 'health'), ('C', 'charisma')]})
        check(all(type(value) is int and 0 <= value <= 100 for value in stats.values()),
              'native-menu-stats', 'Native menu attributes exceed the supported range')
        check(self.db.schema.get(0xD841C77B ^ CHARACTER) == (18, 6), 'native-menu-schema',
              'Native primary fighting-style field differs from the audited layout')
        mask = donor['fields']['FightingStyle']['word']
        primary = self.db.word(donor['record_offset'] + 18 * 4)
        first = [index for index in range(5) if mask & primary & (1 << index)]
        check(0 < mask <= 31 and first, 'native-menu-style', 'Unsupported native fighting-style ordering')
        # Native 48270 exits its scan at the first matching primary bit;
        # 4829E then appends the other enabled styles in ascending order.
        first = first[:1]
        styles = first + [index for index in range(5) if mask & (1 << index) and index not in first]
        return {'selection_key': selection, 'stats': stats, 'styles': styles}

    def compile(self, packs, ledger=None, *, logical_menu=False, binding_window=False, appearances=None, portraits=None,
                behavior=None):
        check(not (logical_menu and binding_window), 'native-mode', 'Choose one logical binding mode')
        snapshot = resolve(self._baseline, packs)
        if behavior is not None:
            from fighter_behavior import BehaviorPlan
            check(type(behavior) is BehaviorPlan, 'native-behavior', 'Expected a validated behavior generation')
            behavior.validate(self, snapshot)
        appearances = {} if appearances is None else appearances
        check(type(appearances) is dict, 'native-resource', 'Expected validated appearance resources')
        from fighter_appearance import Appearance
        from fighter_portrait import Portrait
        portraits = {} if portraits is None else portraits
        check(type(portraits) is dict, 'native-resource', 'Expected validated portrait resources')
        for identifier, portrait in portraits.items():
            resource = snapshot['resources'].get(identifier, {})
            check(type(portrait) is Portrait and portrait.identifier == identifier
                  and portrait.donor in self.rows and resource.get('kind') == 'portrait'
                  and 'source' in resource and portrait.source_sha256 == fingerprint(resource['source']),
                  'native-resource', 'Portrait does not match its resolved source definition')
            check(portrait.donor_selection == self.rows[portrait.donor]['native_binding']['selection_key'],
                  'native-resource', 'Portrait was checked against a different donor layout')
        for identifier, appearance in appearances.items():
            resource = snapshot['resources'].get(identifier, {})
            check(type(appearance) is Appearance and appearance.identifier == identifier
                  and appearance.donor in self.rows and resource.get('kind') == 'appearance'
                  and 'source' in resource and appearance.source_sha256 == fingerprint(resource['source']),
                  'native-resource', 'Appearance does not match its resolved source definition')
            check(resource['compatibility']['skeleton'] == 'retail/binding-' + appearance.donor.split('/')[1],
                  'native-resource', 'Appearance declares a different inherited animation rig')
            check(appearance.donor_model == self.rows[appearance.donor]['fields']['Model']['symbol'],
                  'native-resource', 'Appearance was checked against a different donor model')
        ledger = allocate(seed(self.db, self.source_sha256, self.rows), snapshot['fighters'], ledger)
        original = {key: value for key, value in resolve(self._baseline, [])['fighters'].items()}
        additions, edits, donor_keys, localization, portrait_donors, menu_roster = [], [], {}, {}, {}, {}
        for identifier, fighter in snapshot['fighters'].items():
            components = fighter['components']
            unsupported = set(components) - set(RESOURCE_FIELDS) - {'moveset', 'stats'} - ({'ai', 'intro', 'victory', 'blazin'} if behavior else set())
            check(not unsupported, 'native-component', 'Native adapter does not yet implement these components',
                  {'fighter': identifier, 'components': sorted(unsupported)})
            check(set(components.get('stats', {})) == set(STATS), 'native-component',
                  'Native preview requires all four stats, explicitly or through inheritance',
                  {'fighter': identifier})
            for group, resource in components.items():
                if group != 'stats':
                    check(resource in self.bindings or group == 'appearance' and resource in appearances
                          or group == 'portrait' and resource in portraits
                          or behavior is not None and resource in behavior.sources,
                          'native-resource', 'Resource needs a native asset adapter',
                          {'fighter': identifier, 'component': group, 'resource': resource})
            donor_key = behavior.donors[identifier] if behavior and identifier in behavior.donors else self.bindings[components['moveset']]['donor']
            donor_keys[identifier] = donor_key
            donor = self.rows[donor_key]
            native_fields = {native: components['stats'][key] for key, native in STATS.items()
                             if key in components.get('stats', {})}
            for group, names in RESOURCE_FIELDS.items():
                check(group in components, 'native-component', 'Native preview needs a complete retail donor bundle',
                      {'fighter': identifier, 'component': group})
                if group == 'voice' and behavior and components[group] in behavior.voice_ids:
                    native_fields['SpeechId'] = behavior.voice_ids[components[group]]
                    continue
                appearance = appearances.get(components[group]) if group == 'appearance' else None
                authored = appearance or (portraits.get(components[group]) if group == 'portrait' else None)
                resource_row = self.rows[authored.donor if authored else self.bindings[components[group]]['donor']]
                for name in names:
                    field = resource_row['fields'][name]
                    native_fields[name] = field['symbol'] if field['descriptor'] == 1 else field['word']
                if appearance:
                    native_fields['Model'] = appearance.name
            if identifier in self.rows:
                check(components['portrait'] not in portraits, 'native-portrait-override',
                      'Authored retail portrait overrides need a separate ownership adapter')
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
                portrait = portraits.get(components['portrait'])
                portrait_donors[identifier] = portrait.donor if portrait else self.bindings[components['portrait']]['donor']
                # Public keys can be long and are never copied into bounded
                # native UI fields. Hash collisions are rejected by the builder.
                native_name = symbol(identifier)
                # Native DisplayName is a localization key, not literal text.
                # This cache requires a future merged localization registration.
                native_fields['DisplayName'] = native_name
                localization[native_name] = fighter['name']
                additions.append({'key': identifier, 'native_name': native_name,
                                  'template': donor['record_offset'], 'fields': native_fields})
                if logical_menu or binding_window:
                    menu_roster[identifier] = self.menu_record(donor, components, ledger['fighters'][identifier]['selection'])
        # Removing the last pack is a valid lifecycle transition. Keep its
        # historical ledger dormant, but do not invent native banks without
        # an active fighter/template or emit an empty window for the runtime.
        retail_only = binding_window and not additions
        if retail_only:
            binding_window = False
        native_additions = [] if logical_menu else additions
        if binding_window:
            check(0 < len(additions) <= MAX_FIGHTERS, 'native-window-count', 'Invalid logical fighter window population')
            native_additions = list(additions)
            first = additions[0]
            for index in range(BANKS):
                native_additions.append({'key': bank_key(index), 'native_name': f'fw-bank-{index}',
                                         'template': first['template'], 'fields': dict(first['fields'])})
        selections = {addition['key']: ledger['fighters'][addition['key']]['selection'] for addition in additions}
        if binding_window:
            selections.update({bank_key(index): FIRST_SELECTION + index for index in range(BANKS)})
        output, native = self.db.extend_character_records(native_additions, edits,
            selection_keys={addition['key']: selections[addition['key']] for addition in native_additions},
            deferred_keys={addition['key'] for addition in additions} if binding_window else None,
            character_cores={addition['key']: behavior.character_cores.get(addition['key'],
                behavior.character_cores[additions[0]['key']]) for addition in native_additions} if behavior else None)
        bindings = {key: dict(row['native_binding'], record_offset=row['record_offset'], native_name=row['name'])
                    for key, row in self.rows.items()}
        for key, binding in native['bindings'].items():
            if binding_window and key.startswith('runtime-bank/'):
                continue
            bindings[key] = {'selection_key': binding['selection_key'],
                             'core_id': binding['inherited_core_id'],
                             'record_offset': binding['record_offset'], 'native_name': binding['native_name']}
        if logical_menu:
            for addition in additions:
                key = addition['key']
                bindings[key] = {'selection_key': ledger['fighters'][key]['selection'],
                                 'core_id': behavior.character_cores[key] if behavior else self.rows[donor_keys[key]]['native_binding']['core_id'],
                                 'record_offset': 0, 'native_name': addition['native_name']}
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
        if appearances:
            report['appearance_resources'] = {key: value.summary for key, value in sorted(appearances.items())}
            report['blockers'].extend(['appearance-render-parameter-acceptance', 'appearance-ownership-acceptance'])
        if behavior:
            report['behavior_sources'] = dict(behavior.sources)
            report['behavior_receipts'] = behavior.receipts
            report['behavior_files'] = dict(behavior.file_hashes)
            report['blockers'].append('behavior-native-acceptance')
        if portraits:
            report['portrait_resources'] = {key: value.summary for key, value in sorted(portraits.items())}
            report['portrait_bindings'] = {key: fighter['components']['portrait']
                for key, fighter in snapshot['fighters'].items()
                if key not in self.rows and fighter['components']['portrait'] in portraits}
            report['blockers'].extend(['portrait-menu-acceptance', 'portrait-grid-artwork'])
        if logical_menu:
            report.update(binding_mode='logical-menu-only', native_character_count=len(self.rows), menu_roster=menu_roster)
            report['blockers'].append('logical-fighter-confirmation-unbound')
        if retail_only:
            report.update(binding_mode='retail-only', native_character_count=len(self.rows), menu_roster={})
        if binding_window:
            report.update(binding_mode='participant-window', native_character_count=len(self.rows) + BANKS,
                          menu_roster=menu_roster, window=build_window(output, native, additions, ledger))
            report['window_sha256'] = hashlib.sha256(encode_window(report['window'])).hexdigest()
            report['blockers'].extend(['window-lifetime-acceptance', 'window-save-extension'])
        if any(len(label.encode('utf-8')) > 19 for label in localization.values()):
            report['blockers'].append('native-label-buffer')
        report['names_sha256'] = hashlib.sha256(encode_names(localization)).hexdigest()
        report['bindings_sha256'] = hashlib.sha256(encode_bindings(report['handle_bindings'])).hexdigest()
        report['cache_key'] = fingerprint(report)
        return output, report
