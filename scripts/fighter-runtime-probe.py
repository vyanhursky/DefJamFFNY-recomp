#!/usr/bin/env python3
"""Internal donor-roster acceptance driver; never activates an installed mod.

Recompile reviewed definitions from the verified original database, then run one
harness route with a disposable, guarded save root under logs. This deliberately
does not consume a package-supplied native database or allow normal profiles.
The draft adapter's shipping gates remain in force.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import uuid
import shutil

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fighter_registry_cli', ROOT / 'scripts/fighter-registry.py')
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)
from fighter_archive import MAX_ARCHIVE, portrait_aliases
from fighter_archive import Archive, store
from fighter_assets import unpack
from fighter_composition import language_base, MAX_DELTA_BYTES
from fighter_registry import fingerprint
from fighter_menu import compile_menu
from fighter_results import compile_results
from fighter_bindings import seed
from fighter_profile_store import Store
from fighter_save_journal import Monitor, initialize, encode_unlock_state, bounded, closed_record, decode
from mods import atomic_json, language_manifest, ordinary_path, validate_textures


def require_idle_game():
    # harness.py's normal interactive convenience can stop a stale game. This
    # research lane must never terminate another checkout's play/test session.
    if os.name == 'nt':
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq defjam_recomp.exe', '/FO', 'CSV', '/NH'],
                                capture_output=True, text=True, timeout=10)
        if result.returncode or '"defjam_recomp.exe"' in result.stdout.lower():
            raise ValueError('Close the running game before starting a fighter probe')
    else:
        result = subprocess.run(['pgrep', '-x', 'defjam_recomp'], capture_output=True, timeout=10)
        if result.returncode != 1:
            raise ValueError('Close the running game before starting a fighter probe')


def prepare(sod, packs, ledger_path=None, logical_menu=False, binding_window=False):
    if not packs or len(packs) > registry.MAX_PACKS:
        raise ValueError('Probe requires one or more bounded draft packs')
    parsed, used = [], 0
    ledger = None
    if ledger_path is not None:
        ledger, used = registry.document(ledger_path, registry.MAX_INPUT)
    for path in packs:
        pack, count = registry.document(path, registry.MAX_INPUT - used)
        parsed.append(pack)
        used += count
    options = {'logical_menu': True} if logical_menu else {'binding_window': True} if binding_window else {}
    data, report, resources = registry.compile_inputs(sod, packs, parsed, ledger, **options)
    if not report['added_count']:
        raise ValueError('Probe needs at least one added fighter')
    # This is an internal vertical slice, not a declared product capacity.
    # The signed selection-byte path has not been widened yet.
    custom = {key: row for key, row in report['bindings'].items() if not key.startswith('retail/')}
    if not logical_menu and not binding_window and any(not 0 <= row['selection_key'] < 128 or row['selection_key'] in (98, 99) for row in custom.values()):
        raise ValueError('Research probe has not adapted the signed selection-byte boundary')
    cache = Path(registry.write_preview(data, report, resources))
    return cache, report


def start_fighters(report, keys):
    if not 2 <= len(keys) <= 4 or len(set(keys)) != len(keys):
        raise ValueError('Combat probe needs two to four distinct stable fighter keys')
    try:
        return ','.join(str(report['bindings'][key]['selection_key']) for key in keys)
    except KeyError as error:
        raise ValueError('Combat probe fighter is missing: ' + str(error.args[0])) from error


def expected_fighters(report, keys):
    """@created asserts the profile-owned sentinel; it is never a pack binding."""
    if not 2 <= len(keys) <= 4 or len(set(keys)) != len(keys):
        raise ValueError('Menu evidence needs two to four distinct participant identities')
    try:
        return [99 if key == '@created' else report['bindings'][key]['selection_key'] for key in keys]
    except KeyError as error:
        raise ValueError('Expected menu fighter is missing: ' + str(error.args[0])) from error


def custom_key(key):
    return key != '@created' and not key.startswith('retail/')


def verify_combat(log, matches, *, humans=1, require_result=False):
    """Check each native match without loading the much larger diagnostic log."""
    spec = importlib.util.spec_from_file_location('fighter_test_evidence', Path(__file__).with_name('test_evidence.py'))
    evidence = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(evidence)
    lines, used, retained = [], 0, 0
    with Path(log).open('r', encoding='utf-8', errors='replace') as stream:
        while line := stream.readline(65537):
            used += len(line)
            if len(line) > 65536 or used > 512 * 1024**2:
                raise ValueError('Combat evidence exceeds inspection budget')
            if '[TEST-EVENT]' in line or 'game.getmatchsummary(' in line.lower():
                retained += len(line)
                if retained > 16 * 1024**2:
                    raise ValueError('Combat telemetry exceeds inspection budget')
                lines.append(line)
    text, checks = ''.join(lines), []
    for ordinal, fighters in enumerate(matches, 1):
        checks.extend(dict(check, match=ordinal) for check in evidence.combat_checks(
            text, fighters=len(fighters), match=ordinal, humans=humans, require_result=require_result))
    if not checks or any(check['status'] != 'pass' for check in checks):
        failed = [str(c['match']) + ':' + c['name'] for c in checks if c['status'] != 'pass']
        raise ValueError('Native combat acceptance failed: ' + ', '.join(failed or ['no expected matches']))
    return checks


def verify_menu_matches(log, report, matches, *, immutable=False):
    """Check each selection epoch independently, including post-StartGame cores."""
    expected = [expected_fighters(report, keys) for keys in matches]
    submissions, bound, epochs, current, released = {}, {}, [], None, 0
    used = 0
    with Path(log).open('r', encoding='utf-8', errors='replace') as stream:
        while line := stream.readline(65537):
            used += len(line)
            if len(line) > 65536 or used > 512 * 1024**2:
                raise ValueError('Native menu evidence exceeds inspection budget')
            match = re.search(r'\[FUNCCALL\] Controller\.ControllerSetup\(\s*(-?\d+)\s*,\s*-?\d+\s*,\s*(-?\d+)\s*,\s*-?\d+\s*\)', line)
            if match:
                if int(match[1]) == -1:
                    submissions, bound = {}, {}
                else:
                    submissions[int(match[1])] = int(match[2])
            match = re.search(r'\[START\] venue\(script\)=-?\d+ fighters\(gd\+1aaa step 5\):((?: -?\d+){4})', line)
            if match:
                current = {'native': [int(value) for value in match[1].split()],
                           'submissions': dict(submissions), 'bound': dict(bound), 'materialized': {}, 'released': released}
                epochs.append(current)
                submissions, bound = {}, {}
            match = re.search(r'\[FIGHTERS\] participant=(\d+) logical=(\d+) stable=([0-9A-F]{8}) native=(\d+) core=(\d+)', line)
            if match:
                bound[int(match[1])] = (int(match[2]), int(match[3], 16), int(match[4]), int(match[5]))
            match = re.search(r'\[FIGHTERS\] materialized participant=(\d+) stable=([0-9A-F]{8}) logical=(\d+) core=(\d+) immutable=1', line)
            if match and current is not None:
                current['materialized'][int(match[1])] = (int(match[3]), int(match[2], 16), int(match[4]))
            if '[FIGHTERS] selection ownership finished after native Game.Quit; immutable records retained' in line:
                released += 1
    if len(epochs) != len(matches):
        raise ValueError('Native menu did not start exactly the expected number of matches')
    if immutable and any(epoch['released'] < index for index, epoch in enumerate(epochs)):
        raise ValueError('Native repeated matches lack immutable selection ownership release evidence')
    for keys, wanted_ids, epoch in zip(matches, expected, epochs):
        native_expected = [100 + i if custom_key(key) else value for i, (key, value) in enumerate(zip(keys, wanted_ids))] \
            if report.get('binding_mode') == 'participant-window' else wanted_ids
        if epoch['native'][:len(wanted_ids)] != native_expected:
            raise ValueError('Native menu did not start a match with the expected fighter identities')
        if any(epoch['submissions'].get(index) != value for index, value in enumerate(wanted_ids)):
            raise ValueError('Native menu did not submit every expected participant identity')
        if report.get('binding_mode') == 'participant-window':
            for index, key in enumerate(keys):
                if custom_key(key):
                    wanted = (wanted_ids[index], report['binding_ledger']['fighters'][key]['handle'], 100 + index, report['bindings'][key]['core_id'])
                    if epoch['bound'].get(index) != wanted:
                        raise ValueError('Native participant bank did not bind the expected stable identity and core')
                    if immutable and epoch['materialized'].get(index) != (wanted[0], wanted[1], wanted[3]):
                        raise ValueError('Native immutable fighter core was not materialized for every expected participant')
    return expected


def verify_menu_selection(log, report, keys):
    """Single-match control preserves the stricter original one-start contract."""
    return verify_menu_matches(log, report, [keys])[0]


def original_screens(screens):
    pin = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text(encoding='utf-8'))
    with screens.open('rb') as stream:
        source = stream.read(MAX_ARCHIVE + 1)
    if len(source) > MAX_ARCHIVE or hashlib.sha256(source).hexdigest() != pin['screens_sha256']:
        raise ValueError('Portrait adapter requires the supported original screens archive')
    return source


def pack_folder(folder):
    folder = ordinary_path(folder)
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,63}', folder.name) or '..' in folder.name:
        raise ValueError('Composition needs an ordinary supported pack folder')
    return folder


def texture_environment(folders, language=None):
    """Use the native pack order/root; never copy installed packs into the probe."""
    folders = [pack_folder(folder) for folder in folders]
    language = pack_folder(language) if language is not None else None
    roots = {folder.parent for folder in [*folders, *([language] if language else [])]}
    if len(roots) > 1:
        raise ValueError('Native language/texture composition needs one shared pack root')
    names = [folder.name for folder in folders]
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError('Texture composition lists a pack twice')
    for folder in folders:
        validate_textures(folder)
    if language is not None and (language / 'manifest.ini').exists() and language not in folders:
        validate_textures(language)
    # pc_language may prepend its own image layer. Account for that before the
    # native texture loader's 1024-byte list would silently drop a trailing pack.
    total = list(names)
    if language is not None and (language / 'manifest.ini').exists() and language.name not in total:
        total.insert(0, language.name)
    if len(';'.join(total).encode('ascii')) >= 1024:
        raise ValueError('Texture composition exceeds the native pack-list budget')
    environment = {'RECOMP_TEXTURE_ROOT': str(next(iter(roots)))} if roots else {}
    if names:
        environment.update(RECOMP_TEXTURE_PACKS=';'.join(names), RECOMP_TEXTURE_TRACE='1')
    if language is not None:
        environment['RECOMP_LANGUAGE_PACK'] = language.name
    return environment


def prepare_language_screens(screens, folder):
    folder = pack_folder(folder)
    parser = language_manifest(folder)
    edits, used = [], 0
    for target, delta in parser['files'].items():
        parts = tuple(part.strip() for part in target.split('|'))
        if parts[0].lower() == 'assets/djv2.sod':
            raise ValueError('Language changes to the fighter database need a semantic composition adapter')
        if parts[0].lower() != 'screens/screens.viv':
            continue  # The native language loader retains its other files and data-only XBE patch.
        path = folder / delta.strip()
        with path.open('rb') as stream:
            data = stream.read(MAX_DELTA_BYTES - used + 1)
        used += len(data)
        if used > MAX_DELTA_BYTES:
            raise ValueError('Language composition deltas exceed byte budget')
        edits.append((parts[1:], data))
    if not edits:
        return None
    source = original_screens(screens)
    return language_base(source, edits, hashlib.sha256(source).hexdigest())


def prepare_portraits(screens, report, *, language=None, resource_cache=None):
    root = ordinary_path(ROOT / 'logs/fighter-ui-preview')
    source = original_screens(screens)
    original = source
    if language is not None:
        composed, receipt = language
        if set(receipt) != {'schema', 'source_sha256', 'base_sha256', 'edits', 'cache_key'} \
                or receipt['schema'] != 'fighter-language-base-1' \
                or receipt['source_sha256'] != hashlib.sha256(source).hexdigest() \
                or receipt['base_sha256'] != hashlib.sha256(composed).hexdigest() \
                or receipt['cache_key'] != fingerprint({key: value for key, value in receipt.items() if key != 'cache_key'}):
            raise ValueError('Language screens provenance does not match its composed bytes')
        source = composed
    pairs = {report['bindings'][key]['selection_key']: report['bindings'][donor]['selection_key']
             for key, donor in report['portrait_donors'].items()}
    result = portrait_aliases(source, pairs, results=True)
    artwork = {}
    if report.get('portrait_resources'):
        from fighter_portrait import apply_portraits
        if resource_cache is None:
            raise ValueError('Authored portraits require their compiled cache')
        resources = {}
        for relative in report['portrait_files']:
            from mods import safe_relative
            path = ordinary_path(resource_cache.joinpath(*safe_relative(relative)))
            with path.open('rb') as stream:
                data = stream.read(16 * 1024**2 + 1)
            if len(data) > 16 * 1024**2:
                raise ValueError('Compiled portrait exceeds its budget')
            resources[relative] = data
        bindings = {report['bindings'][key]['selection_key']: (identifier, report['portrait_files'])
                    for key, identifier in report['portrait_bindings'].items()}
        if not set(bindings) <= set(pairs):
            raise ValueError('Authored portrait binding is not an owned custom alias')
        result = apply_portraits(result, bindings, resources)
        if bindings:
            from fighter_grid import compose_grid
            from fighter_portrait import PortraitBaseline
            result, artwork = compose_grid(result, report, PortraitBaseline(original, hashlib.sha256(original).hexdigest()))
    archive, replacements = Archive(result), {}
    names = {report['bindings'][key]['selection_key']: report['localization_entries'][report['bindings'][key]['native_name']]
             for key in report['portrait_donors']}
    for count in (2, 3, 4):
        stem = f'chooseF{count}'
        path = 'screens/battle/' + stem + '.big'
        inner = Archive(unpack(archive.read(path)))
        records = list(report['menu_roster'].values()) if report.get('binding_mode') in ('logical-menu-only', 'participant-window') else None
        movie, constants, _ = compile_menu(inner.read(stem + '.apt'), inner.read(stem + '.const'), pairs, names, records, participants=count, artwork=artwork)
        replacements[path] = store(inner.compose(replacements={stem + '.apt': movie, stem + '.const': constants}))
        stem = f'matchSm{count}'
        path = 'screens/battle/' + stem + '.big'
        inner = Archive(unpack(archive.read(path)))
        movie, constants, _ = compile_results(inner.read(stem + '.apt'), inner.read(stem + '.const'), names, participants=count)
        replacements[path] = store(inner.compose(replacements={stem + '.apt': movie, stem + '.const': constants}))
    result = archive.compose(replacements=replacements)
    digest = hashlib.sha256(result).hexdigest()
    root.mkdir(parents=True, exist_ok=True)
    destination = ordinary_path(root / digest)
    if not destination.exists():
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            stage = Path(temporary) / 'cache'
            (stage / 'screens').mkdir(parents=True)
            (stage / 'screens/screens.viv').write_bytes(result)
            try:
                os.rename(stage, destination)
            except OSError:
                if not ordinary_path(destination).is_dir():
                    raise
    path = ordinary_path(destination / 'screens/screens.viv')
    with path.open('rb') as stream:
        actual = stream.read(MAX_ARCHIVE + 1)
    if len(actual) != len(result) or hashlib.sha256(actual).hexdigest() != digest:
        raise ValueError('Existing portrait cache is corrupt')
    return path


def verify_saved_kind(journal, committed, kind):
    """Count only this run's committed batches with valid native close receipts."""
    size = {'options': 0x1490, 'profile': 0x5904}[kind]
    names = []
    for number, _ in committed:
        batch = decode(bounded(Path(journal) / f'{number:06}.batch'))
        if batch['number'] != number:
            raise ValueError('Crossed native save acceptance batch')
        for index, record in enumerate(batch['records']):
            if len(record['payload']) == size:
                if closed_record(journal, number, index, record) is None:
                    raise ValueError('Native save acceptance lost its close receipt')
                names.append(record['name'])
    if not names:
        raise ValueError('Native run did not commit an acknowledged ' + kind + ' save')
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sod', type=Path)
    parser.add_argument('packs', nargs='+', type=Path)
    parser.add_argument('--route', choices=('boot', 'fight', 'ffa', 'versus', 'crib', 'gym', 'intro', 'fighter-roster', 'fighter-roster-3', 'fighter-roster-4', 'fighter-roster-4-human', 'fighter-roster-4-human-browse', 'fighter-roster-3-save', 'fighter-roster-4-save', 'fighter-roster-result', 'fighter-roster-save', 'fighter-roster-two-matches'), default='boot')
    parser.add_argument('--secs', type=int, default=60)
    parser.add_argument('--shots', default='25')
    parser.add_argument('--to-end', action='store_true', help='Use the complete duration for long native-menu acceptance')
    parser.add_argument('--stage', action='append', default=[])
    parser.add_argument('--start-fighter', action='append', default=[],
                        help='Internal StartGame control, by stable key; not menu-selection acceptance')
    parser.add_argument('--expect-fighter', action='append', default=[],
                        help='Assert native menu identities in participant order; @created requires the real profile-owned fighter')
    parser.add_argument('--expect-match', action='append', default=[],
                        help='Repeated-match assertion: comma-separated stable keys, once per match in order')
    parser.add_argument('--trace-assets', action='store_true')
    parser.add_argument('--trace-cinematics', action='store_true', help='Observe cinematic names, parser entry and file loads')
    parser.add_argument('--observe-combat', action='store_true', help='Record native match, movement, attack and damage telemetry')
    parser.add_argument('--require-combat', action='store_true', help='Require observed movement, input-linked attacks and damage in each expected match')
    parser.add_argument('--require-result', action='store_true', help='Also require a decisive result and results screen in each expected match')
    parser.add_argument('--combat-humans', type=int, choices=(1, 2, 3, 4), default=1)
    parser.add_argument('--record', action='store_true', help='Record frame/resource metrics through the existing play-test recorder')
    parser.add_argument('--trace-profiles', action='store_true')
    parser.add_argument('--trace-lifetime', action='store_true', help='Watch reviewed participant model reset/load boundaries; no lifecycle override')
    parser.add_argument('--trace-appearance-lifetime', action='store_true', help='Watch model registration, instance cleanup and resource release; no lifecycle override')
    parser.add_argument('--logical-menu', action='store_true', help='Browsing-only logical roster prototype; native confirmation blocked')
    parser.add_argument('--binding-window', action='store_true', help='Internal four-participant native binding prototype')
    parser.add_argument('--immutable-reuse', action='store_true', help='Research repeated selections using immutable records after native Game.Quit')
    parser.add_argument('--profile-store', type=Path, default=ROOT / 'logs/fighter-profile-store', help='Internal isolated generation store under logs')
    parser.add_argument('--fresh-profiles', action='store_true', help='Create a new isolated namespace from native defaults instead of importing a fixture')
    parser.add_argument('--import-profiles', type=Path, help='Read-only verified save fixture for the first isolated generation; never replaces an existing store')
    parser.add_argument('--no-unlock', action='store_true', help='Disable the harness unlock-everything control for native progress/save acceptance')
    parser.add_argument('--expect-save', choices=('options', 'profile'), help='Require a committed native write/close receipt of this kind in this run')
    parser.add_argument('--ledger', type=Path, help='Internal historical ledger from a previous research cache')
    parser.add_argument('--language-pack', type=Path, help='Existing language pack; compose its verified screens before fighter presentation')
    parser.add_argument('--texture-pack', type=Path, action='append', default=[], help='Existing texture pack under the same native mods root; repeat in precedence order')
    args = parser.parse_args()
    try:
        if not 10 <= args.secs <= 900:
            raise ValueError('Probe duration must be 10..900 seconds')
        matches = [value.split(',') for value in args.expect_match] if args.expect_match else ([args.expect_fighter] if args.expect_fighter else [])
        if (args.require_combat or args.require_result) and not matches:
            raise ValueError('Combat acceptance requires explicit expected native menu identities')
        if args.expect_match and (args.expect_fighter or not args.immutable_reuse):
            raise ValueError('Repeated-match expectations require immutable reuse and cannot mix single-match assertions')
        if matches and args.start_fighter:
            raise ValueError('Native menu expectations cannot use a StartGame fighter override')
        if args.binding_window and (args.logical_menu or args.start_fighter):
            raise ValueError('Binding window requires native menu selection and no other binding mode')
        if args.immutable_reuse and not args.binding_window:
            raise ValueError('Immutable record reuse requires the isolated binding window')
        if args.fresh_profiles and not args.binding_window:
            raise ValueError('Fresh profile research requires the binding window')
        if args.import_profiles and (not args.binding_window or args.fresh_profiles):
            raise ValueError('Profile import requires the binding window and cannot use fresh defaults')
        if args.expect_save and not args.binding_window:
            raise ValueError('Save acceptance requires the isolated binding window')
        if sum((args.trace_assets, args.trace_cinematics, args.trace_profiles, args.trace_lifetime,
                args.trace_appearance_lifetime)) > 1:
            raise ValueError('Select one four-breakpoint trace domain per probe')
        if args.logical_menu:
            if args.route not in ('fighter-roster', 'fighter-roster-4') or args.start_fighter or args.expect_fighter:
                raise ValueError('Logical menu prototype permits browsing routes only')
            allowed = {'up', 'down', 'left', 'right', 'back'}
            if any(press.split('@')[0] not in allowed for stage in args.stage for press in stage.split('=', 1)[-1].split(';')):
                raise ValueError('Logical menu prototype permits direction/back input only')
        require_idle_game()
        # Validate every output root before cache/store/session creation. Child
        # paths are checked again immediately before their own reads/writes.
        for relative in ('fighter-native-preview', 'fighter-ui-preview', 'fighter-runtime-probe',
                         'fighter-window-runs', 'fighter-probe-captures'):
            ordinary_path(ROOT / 'logs' / relative)
        layers = texture_environment(args.texture_pack, args.language_pack)
        store, monitor = None, None
        if args.binding_window:
            destination = ordinary_path(args.profile_store)
            if not destination.is_relative_to((ROOT / 'logs').resolve()):
                raise ValueError('Research profile generations must stay under logs')
            source = registry.retail_catalog(args.sod)
            store = Store(destination, seed(source.db, source.source_sha256, source.rows))
            previous = store.load()
            if args.import_profiles and previous is not None:
                raise ValueError('Profile import requires an empty isolated store')
            if args.fresh_profiles and previous is not None:
                raise ValueError('Fresh profile research requires an empty store; choose a new research path')
            if previous is not None and args.ledger is None:
                args.ledger = ordinary_path(destination / 'next-ledger.json')
                atomic_json(args.ledger, previous['ledger'])
        cache, report = prepare(args.sod, args.packs, args.ledger, args.logical_menu, args.binding_window)
        for keys in matches:
            expected_fighters(report, keys)  # reject missing/duplicate keys before launching
        screens = args.sod.resolve().parents[1] / 'screens/screens.viv'
        language = prepare_language_screens(screens, args.language_pack) if args.language_pack else None
        portraits = prepare_portraits(screens, report, language=language, resource_cache=cache)
        data_root = ordinary_path(ROOT / 'logs/fighter-runtime-probe')
        if store is not None:
            generation = None if args.fresh_profiles else initialize(store, args.import_profiles or data_root / 'save', report['binding_ledger'])
            session = ordinary_path(ROOT / 'logs/fighter-window-runs' / uuid.uuid4().hex)
            data_root = ordinary_path(session / 'fighter-runtime-probe')
            for name, data in (generation['files'] if generation else {}).items():
                path = ordinary_path(data_root / 'save' / name)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            journal = ordinary_path(session / 'journal'); journal.mkdir(parents=True)
            unlock_state = ordinary_path(session / 'fighter-unlocks.bin')
            unlock_state.write_bytes(encode_unlock_state(generation, store.baseline))
            monitor = Monitor(store, data_root / 'save', journal, report['binding_ledger'])
        data_root.mkdir(parents=True, exist_ok=True)
        if language is not None:
            atomic_json(ordinary_path(data_root / 'fighter-composition.json'), {'language': language[1],
                        'screens_sha256': hashlib.sha256(portraits.read_bytes()).hexdigest()})
        environment = {k: v for k, v in os.environ.items() if not k.startswith('RECOMP_')}
        environment['DEFJAM_DATA'] = str(data_root)
        command = [sys.executable, str(ROOT / 'scripts/harness.py'), 'run', args.route,
                   '--secs', str(args.secs), '--shots', args.shots, '--png',
                   '--env', 'RECOMP_FIGHTER_NAMES=' + str(cache / 'fighter-names.bin'),
                   '--env', 'RECOMP_FIGHTER_BINDINGS=' + str(cache / 'fighter-bindings.bin'),
                   '--env', 'RECOMP_FIGHTER_NAMES_PROBE=1',
                   '--env', 'RECOMP_FIGHTER_RESEARCH_SOD=' + str(cache / 'assets/djv2.sod'),
                   '--env', 'RECOMP_FIGHTER_RESEARCH_SCREENS=' + str(portraits),
                   '--env', 'RECOMP_START_LOG=1', '--env', 'RECOMP_TEST_OBSERVATIONS=1']
        if args.record:
            command += ['--env', 'RECOMP_RECORD=1']
        if args.start_fighter:
            command += ['--env', 'RECOMP_START_FIGHTERS=' + start_fighters(report, args.start_fighter)]
        if report.get('appearance_files'):
            for field, relative in [('MODELS', 'assets/v2ip.viv'), ('ENTITIES', 'assets/entity.xml'), ('CINEMATICS', 'assets/nis.viv')]:
                command += ['--env', 'RECOMP_FIGHTER_RESEARCH_' + field + '=' + str(cache / relative)]
                command += ['--env', 'RECOMP_FIGHTER_RESEARCH_' + field + '_SHA256=' + report['appearance_files'][relative]]
        if report.get('behavior_files'):
            from fighter_behavior import environment as behavior_environment
            for name, value in behavior_environment(cache, report).items():
                command += ['--env', name + '=' + value]
        if args.no_unlock:
            command += ['--env', 'RECOMP_UNLOCK_ALL=0']
        for key, value in layers.items():
            command += ['--env', key + '=' + value]
        if language is not None:
            command += ['--env', 'RECOMP_FIGHTER_RESEARCH_LANGUAGE_BASE=' + language[1]['base_sha256'],
                        '--env', 'RECOMP_FIGHTER_RESEARCH_SCREENS_SHA256=' + hashlib.sha256(portraits.read_bytes()).hexdigest()]
        if args.to_end:
            command += ['--to-end']
        if args.binding_window:
            command += ['--env', 'RECOMP_FIGHTER_WINDOW=' + str(cache / 'fighter-window.bin')]
            if args.immutable_reuse:
                command += ['--env', 'RECOMP_FIGHTER_IMMUTABLE_REUSE=1']
            command += ['--env', 'RECOMP_FIGHTER_SAVE_JOURNAL=' + str(journal), '--env', 'RECOMP_FIGHTER_UNLOCKS=' + str(unlock_state)]
            command += ['--supervisor', str(journal / 'supervisor.json')]
        if args.trace_assets:
            command += ['--env', 'RECOMP_WATCH_EXEC=0x001E3FB0,0x00109F80',
                        '--env', 'RECOMP_WATCH_EXEC_ALL=1', '--env', 'RECOMP_WATCH_EXEC_STR=1',
                        '--env', 'RECOMP_WATCH_EXEC_FIELD=0x10']
        if args.trace_cinematics:
            command += ['--env', 'RECOMP_WATCH_EXEC=0x000A3830,0x000A3E80,0x000A1F60,0x001E3FB0',
                        '--env', 'RECOMP_WATCH_EXEC_ALL=1', '--env', 'RECOMP_WATCH_EXEC_STR=1',
                        '--env', 'RECOMP_WATCH_EXEC_FIELD=0x4']
        if args.observe_combat:
            command += ['--env', 'RECOMP_TEST_OBSERVATIONS=1']
        if args.trace_profiles:
            command += ['--env', 'RECOMP_WATCH_EXEC=0x000144B0,0x00014540,0x00016810,0x000D2300',
                        '--env', 'RECOMP_WATCH_EXEC_ALL=1', '--env', 'RECOMP_WATCH_EXEC_FIELD=0x4']
        if args.trace_lifetime:
            command += ['--env', 'RECOMP_WATCH_EXEC=0x0009ADC0,0x0009D340,0x000AD910,0x0008B730',
                        '--env', 'RECOMP_WATCH_EXEC_ALL=1', '--env', 'RECOMP_WATCH_EXEC_FIELD=0xA234']
        if args.trace_appearance_lifetime:
            command += ['--env', 'RECOMP_WATCH_EXEC=0x00097710,0x00097BF0,0x000709B0,0x0006EDC0',
                        '--env', 'RECOMP_WATCH_EXEC_ALL=1', '--env', 'RECOMP_WATCH_EXEC_FIELD=0x8']
        for stage in args.stage:
            command += ['--stage', stage]
        print(json.dumps({'probe': 'donor-roster', 'cache_key': report['cache_key'],
                          'data_root': str(data_root), 'custom_bindings': custom_bindings(report),
                          'shipping_gates': report['blockers']}, indent=2), flush=True)
        if monitor is not None:
            monitor.start()
        try:
            result = subprocess.run(command, cwd=ROOT, env=environment,
                                    capture_output=bool(matches), text=True)
            if matches:
                print(result.stdout, end=''); print(result.stderr, end='', file=sys.stderr)
            shots = ROOT / 'logs/shots' / args.route
            captured = list(shots.glob('*.png')) if shots.is_dir() else []
            if captured:
                preserved = ordinary_path((session if store is not None else ROOT / 'logs/fighter-probe-captures' / uuid.uuid4().hex) / 'captures')
                preserved.mkdir(parents=True)
                for path in captured:
                    shutil.copyfile(path, preserved / path.name)
                print('preserved fighter captures: ' + str(preserved), flush=True)
        finally:
            if monitor is not None:
                monitor.stop()
                print('verified fighter save generations: ' + str(len(monitor.committed)), flush=True)
                if 'result' in locals() and result.returncode == 0 and (journal / f'{monitor.next:06}.batch').exists():
                    raise ValueError('Native run ended with an unverified fighter save batch; committed generation was preserved')
        if matches:
            if result.returncode:
                return result.returncode
            paths = re.findall(r'^log\s+(.+)$', result.stdout, re.M)
            if len(paths) != 1:
                raise ValueError('Harness did not report a unique native evidence log')
            log = (ROOT / paths[0].strip()).resolve()
            if not log.is_relative_to((ROOT / 'logs').resolve()):
                raise ValueError('Harness evidence log is outside the research directory')
            expected = verify_menu_matches(log, report, matches, immutable=bool(args.expect_match))
            print('native menu identities verified: ' + '; '.join(','.join(map(str, values)) for values in expected))
            if args.require_combat or args.require_result:
                checks = verify_combat(log, matches, humans=args.combat_humans, require_result=args.require_result)
                print('native combat assertions passed: ' + str(len(checks)))
        if args.expect_save and result.returncode == 0:
            names = verify_saved_kind(journal, monitor.committed, args.expect_save)
            print('native acknowledged ' + args.expect_save + ' saves verified: ' + ', '.join(names))
        return result.returncode
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


def custom_bindings(report):
    return {key: row for key, row in report['bindings'].items() if not key.startswith('retail/')}


if __name__ == '__main__':
    sys.exit(main())
