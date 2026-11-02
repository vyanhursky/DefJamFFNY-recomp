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

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fighter_registry_cli', ROOT / 'scripts/fighter-registry.py')
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)
from fighter_archive import MAX_ARCHIVE, portrait_aliases
from fighter_archive import Archive, store
from fighter_assets import unpack
from fighter_menu import compile_menu


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


def prepare(sod, packs, ledger_path=None):
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
    data, report = registry.retail_catalog(sod).compile(parsed, ledger)
    if not report['added_count']:
        raise ValueError('Probe needs at least one added fighter')
    # This is an internal vertical slice, not a declared product capacity.
    # The signed selection-byte path has not been widened yet.
    custom = {key: row for key, row in report['bindings'].items() if not key.startswith('retail/')}
    if any(not 0 <= row['selection_key'] < 128 or row['selection_key'] in (98, 99) for row in custom.values()):
        raise ValueError('Research probe has not adapted the signed selection-byte boundary')
    cache = Path(registry.write_preview(data, report))
    return cache, report


def start_fighters(report, keys):
    if not 2 <= len(keys) <= 4 or len(set(keys)) != len(keys):
        raise ValueError('Combat probe needs two to four distinct stable fighter keys')
    try:
        return ','.join(str(report['bindings'][key]['selection_key']) for key in keys)
    except KeyError as error:
        raise ValueError('Combat probe fighter is missing: ' + str(error.args[0])) from error


def verify_menu_selection(log, report, keys):
    """Require original menu submission and actual match setup, not just frames."""
    expected = [int(value) for value in start_fighters(report, keys).split(',')]
    submissions, starts = {}, []
    used = 0
    with Path(log).open('r', encoding='utf-8', errors='replace') as stream:
        while line := stream.readline(65537):
            used += len(line)
            if len(line) > 65536 or used > 512 * 1024**2:
                raise ValueError('Native menu evidence exceeds inspection budget')
            match = re.search(r'\[FUNCCALL\] Controller\.ControllerSetup\((\d+),-?\d+,(-?\d+),-?\d+\)', line)
            if match:
                submissions[int(match[1])] = int(match[2])
            match = re.search(r'\[START\] venue\(script\)=-?\d+ fighters\(gd\+1aaa step 5\):((?: -?\d+){4})', line)
            if match:
                starts.append([int(value) for value in match[1].split()])
    if len(starts) != 1 or starts[0][:len(expected)] != expected:
        raise ValueError('Native menu did not start exactly one match with the expected fighter identities')
    if any(submissions.get(index) != value for index, value in enumerate(expected)):
        raise ValueError('Native menu did not submit every expected participant identity')
    return expected


def prepare_portraits(screens, report):
    pin = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text(encoding='utf-8'))
    with screens.open('rb') as stream:
        source = stream.read(MAX_ARCHIVE + 1)
    if len(source) > MAX_ARCHIVE or hashlib.sha256(source).hexdigest() != pin['screens_sha256']:
        raise ValueError('Portrait adapter requires the supported original screens archive')
    pairs = {report['bindings'][key]['selection_key']: report['bindings'][donor]['selection_key']
             for key, donor in report['portrait_donors'].items()}
    result = portrait_aliases(source, pairs)
    archive, replacements = Archive(result), {}
    names = {report['bindings'][key]['selection_key']: report['localization_entries'][report['bindings'][key]['native_name']]
             for key in report['portrait_donors']}
    for count in (2, 3, 4):
        stem = f'chooseF{count}'
        path = 'screens/battle/' + stem + '.big'
        inner = Archive(unpack(archive.read(path)))
        movie, constants, _ = compile_menu(inner.read(stem + '.apt'), inner.read(stem + '.const'), pairs, names)
        replacements[path] = store(inner.compose(replacements={stem + '.apt': movie, stem + '.const': constants}))
    result = archive.compose(replacements=replacements)
    digest = hashlib.sha256(result).hexdigest()
    root = ROOT / 'logs/fighter-ui-preview'
    root.mkdir(parents=True, exist_ok=True)
    destination = root / digest
    if not destination.exists():
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            stage = Path(temporary) / 'cache'
            (stage / 'screens').mkdir(parents=True)
            (stage / 'screens/screens.viv').write_bytes(result)
            try:
                os.rename(stage, destination)
            except OSError:
                if not destination.is_dir():
                    raise
    path = destination / 'screens/screens.viv'
    with path.open('rb') as stream:
        actual = stream.read(MAX_ARCHIVE + 1)
    if len(actual) != len(result) or hashlib.sha256(actual).hexdigest() != digest:
        raise ValueError('Existing portrait cache is corrupt')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sod', type=Path)
    parser.add_argument('packs', nargs='+', type=Path)
    parser.add_argument('--route', choices=('boot', 'fight', 'ffa', 'versus', 'fighter-roster', 'fighter-roster-4'), default='boot')
    parser.add_argument('--secs', type=int, default=60)
    parser.add_argument('--shots', default='25')
    parser.add_argument('--stage', action='append', default=[])
    parser.add_argument('--start-fighter', action='append', default=[],
                        help='Internal StartGame control, by stable key; not menu-selection acceptance')
    parser.add_argument('--expect-fighter', action='append', default=[],
                        help='Assert native menu and StartGame identities in participant order; no override')
    parser.add_argument('--trace-assets', action='store_true')
    parser.add_argument('--ledger', type=Path, help='Internal historical ledger from a previous research cache')
    args = parser.parse_args()
    try:
        if not 10 <= args.secs <= 900:
            raise ValueError('Probe duration must be 10..900 seconds')
        if args.expect_fighter and args.start_fighter:
            raise ValueError('Native menu expectations cannot use a StartGame fighter override')
        require_idle_game()
        cache, report = prepare(args.sod, args.packs, args.ledger)
        if args.expect_fighter:
            start_fighters(report, args.expect_fighter)  # reject missing/duplicate keys before launching
        portraits = prepare_portraits(args.sod.resolve().parents[1] / 'screens/screens.viv', report)
        data_root = ROOT / 'logs/fighter-runtime-probe'
        data_root.mkdir(parents=True, exist_ok=True)
        # A redirected parent of logs/data could accidentally reach player files.
        for path in (ROOT / 'logs', data_root):
            if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
                raise ValueError('Probe data root must be an ordinary local directory')
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
        if args.start_fighter:
            command += ['--env', 'RECOMP_START_FIGHTERS=' + start_fighters(report, args.start_fighter)]
        if args.trace_assets:
            command += ['--env', 'RECOMP_WATCH_EXEC=0x001E3FB0,0x00109F80',
                        '--env', 'RECOMP_WATCH_EXEC_ALL=1', '--env', 'RECOMP_WATCH_EXEC_STR=1',
                        '--env', 'RECOMP_WATCH_EXEC_FIELD=0x10']
        for stage in args.stage:
            command += ['--stage', stage]
        print(json.dumps({'probe': 'donor-roster', 'cache_key': report['cache_key'],
                          'data_root': str(data_root), 'custom_bindings': custom_bindings(report),
                          'shipping_gates': report['blockers']}, indent=2), flush=True)
        result = subprocess.run(command, cwd=ROOT, env=environment,
                                capture_output=bool(args.expect_fighter), text=True)
        if args.expect_fighter:
            print(result.stdout, end=''); print(result.stderr, end='', file=sys.stderr)
            if result.returncode:
                return result.returncode
            paths = re.findall(r'^log\s+(.+)$', result.stdout, re.M)
            if len(paths) != 1:
                raise ValueError('Harness did not report a unique native evidence log')
            log = (ROOT / paths[0].strip()).resolve()
            if not log.is_relative_to((ROOT / 'logs').resolve()):
                raise ValueError('Harness evidence log is outside the research directory')
            expected = verify_menu_selection(log, report, args.expect_fighter)
            print('native menu identities verified: ' + ','.join(map(str, expected)))
        return result.returncode
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1


def custom_bindings(report):
    return {key: row for key, row in report['bindings'].items() if not key.startswith('retail/')}


if __name__ == '__main__':
    sys.exit(main())
