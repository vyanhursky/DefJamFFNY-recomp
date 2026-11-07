"""Shared bounded fighter compiler and immutable cache publication."""
import argparse
import json
import hashlib
import os
from pathlib import Path
import sys
import tempfile

from fighter_sod import Database, MAX_IMAGE, SodError
from fighter_registry import resolve, suggest_compatibility, RegistryError, MAX_PACKS, fingerprint
from fighter_native import RetailCatalog, ADAPTER
from fighter_names import encode_names
from fighter_bindings import encode_bindings
from fighter_window import encode_window
from fighter_assets import unpack as unpack_asset, MAX_ASSET
from fighter_elf import Model
from mods import ordinary_path, durable_rename
from fighter_archive import MAX_ARCHIVE

MAX_DOCUMENT = 8 * 1024**2
MAX_INPUT = 32 * 1024**2
MAX_REPORT = 32 * 1024**2
ROOT = Path(__file__).resolve().parents[1]


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def non_finite(value):
    raise ValueError('Non-finite JSON number: ' + value)


def document(path, remaining=MAX_DOCUMENT):
    limit = min(MAX_DOCUMENT, remaining)
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Draft registry document exceeds budget')
    return json.loads(data, object_pairs_hook=unique, parse_constant=non_finite), len(data)


def documents(baseline_path, pack_paths):
    if len(pack_paths) > MAX_PACKS:
        raise ValueError('Enabled pack count exceeds budget')
    baseline, used = document(baseline_path)
    packs = []
    for path in pack_paths:
        pack, size = document(path, MAX_INPUT - used)
        used += size
        packs.append(pack)
    return baseline, packs


def retail_catalog(path, *, pin_path=None):
    pin = json.loads((pin_path or ROOT / 'config/fighter-native-baseline.json').read_text(encoding='utf-8'))
    if pin['adapter'] != ADAPTER:
        raise ValueError('Native adapter/baseline pin mismatch')
    with path.open('rb') as stream:
        data = stream.read(MAX_IMAGE + 1)
    if len(data) > MAX_IMAGE:
        raise ValueError('SODB exceeds image budget')
    return RetailCatalog(data, pin['sha256'])


def compile_inputs(sod, paths, packs, ledger=None, *, catalog=None, pin_path=None, **options):
    """Resolve whole packs, validate their data, then compose native resources."""
    if len(paths) != len(packs):
        raise ValueError('Each fighter pack needs exactly one source manifest path')
    catalog = catalog or retail_catalog(sod, pin_path=pin_path)
    snapshot = resolve(catalog.baseline(), packs)
    sourced = {name: resource for name, resource in snapshot['resources'].items() if 'source' in resource}
    appearances, portraits, resources = {}, {}, {}
    roots = {pack['id']: path.parent for pack, path in zip(packs, paths)}
    appearance_sources = {key: value for key, value in sourced.items() if value['kind'] == 'appearance'}
    portrait_sources = {key: value for key, value in sourced.items() if value['kind'] == 'portrait'}
    if sourced:
        pin = json.loads((pin_path or ROOT / 'config/fighter-native-baseline.json').read_text(encoding='utf-8'))
    if appearance_sources:
        from fighter_appearance import Appearance, AppearanceBaseline, MAX_APPEARANCE_BYTES
        from fighter_resource_files import read_appearance
        originals = {}
        for key, name in [('models', 'v2ip.viv'), ('shared', 'blingfx.viv'), ('entities', 'entity.xml'),
                          ('cinematics', 'nis.viv'), ('banks', 'v2ta.viv')]:
            with (sod.parent / name).open('rb') as stream:
                originals[key] = stream.read(MAX_ARCHIVE + 1)
            if len(originals[key]) > MAX_ARCHIVE:
                raise ValueError('Original appearance archive exceeds budget')
        baseline = AppearanceBaseline(originals, pin)
        remaining = MAX_APPEARANCE_BYTES
        for name, resource in sorted(appearance_sources.items()):
            source = resource['source']
            if source['donor'] not in catalog.rows:
                raise ValueError('Appearance rig donor is missing: ' + source['donor'])
            files = read_appearance(roots[resource['owner']], source, remaining)
            model = catalog.rows[source['donor']]['fields']['Model']['symbol']
            appearances[name] = Appearance(name, source, files, baseline, model, remaining)
            remaining -= appearances[name].byte_count
        resources = baseline.compose(appearances)
    appearance_files = {path: hashlib.sha256(payload).hexdigest() for path, payload in resources.items()}
    portrait_files = {}
    if portrait_sources:
        from fighter_portrait import Portrait, PortraitBaseline
        from fighter_resource_files import read_portrait
        with (sod.parents[1] / 'screens/screens.viv').open('rb') as stream:
            screens = stream.read(MAX_ARCHIVE + 1)
        if len(screens) > MAX_ARCHIVE:
            raise ValueError('Original screens archive exceeds budget')
        baseline = PortraitBaseline(screens, pin['screens_sha256'])
        remaining = 256 * 1024**2
        for name, resource in sorted(portrait_sources.items()):
            source = resource['source']
            if source['donor'] not in catalog.rows:
                raise ValueError('Portrait layout donor is missing: ' + source['donor'])
            files = read_portrait(roots[resource['owner']], source, min(remaining, 16 * 1024**2))
            selection = catalog.rows[source['donor']]['native_binding']['selection_key']
            portrait = Portrait(name, source, files, baseline, selection, min(remaining, 16 * 1024**2))
            remaining -= portrait.byte_count
            if resources.keys() & portrait.files.keys():
                raise ValueError('Compiled portrait resource names collide')
            portraits[name] = portrait
            resources.update(portrait.files)
            portrait_files.update({path: hashlib.sha256(payload).hexdigest() for path, payload in portrait.files.items()})
    behavior = None
    if any(value['kind'] not in ('appearance', 'portrait') for value in sourced.values()):
        from fighter_behavior import BehaviorPlan
        behavior = BehaviorPlan(catalog, snapshot, roots, sod.parents[1], pin, appearances, resources)
        resources.update(behavior.files)
        appearance_files = {path: hashlib.sha256(resources[path]).hexdigest() for path in appearance_files}
    data, report = catalog.compile(packs, ledger, appearances=appearances, portraits=portraits,
                                   behavior=behavior, **options)
    if appearance_files:
        report['appearance_files'] = appearance_files
    if portrait_files:
        report['portrait_files'] = portrait_files
    if resources:
        report.pop('cache_key', None)
        report['cache_key'] = fingerprint(report)
    return data, report, resources


def write_preview(data, report, resources=None, *, cache_root=None, max_report=MAX_REPORT):
    """Write a verified content-addressed cache; never activate or edit originals."""
    resources = {} if resources is None else resources
    from fighter_resource_files import PORTRAIT_PARTS, resource_name
    appearance_targets = {'assets/v2ip.viv', 'assets/entity.xml', 'assets/nis.viv'} if report.get('appearance_resources') else set()
    portrait_targets = {f'portraits/{resource_name(identifier)}/{part}.big'
                        for identifier in report.get('portrait_resources', {}) for part in PORTRAIT_PARTS}
    behavior_targets = set()
    if report.get('behavior_files') or report.get('behavior_receipts'):
        from fighter_behavior import targets
        behavior_targets = targets(report.get('behavior_receipts'))
        if set(report.get('behavior_files', {})) != behavior_targets:
            raise ValueError('Behavior resources require their exact composed files')
    if bool(report.get('appearance_resources')) != bool(report.get('appearance_files')):
        raise ValueError('Appearance resources require their complete composed files')
    if type(resources) is not dict or set(resources) != appearance_targets | portrait_targets | behavior_targets:
        raise ValueError('Invalid composed appearance targets')
    if any(not isinstance(payload, bytes) or not 0 < len(payload) <= MAX_ARCHIVE for payload in resources.values()):
        raise ValueError('Composed appearance file exceeds budget')
    if report.get('appearance_files', {}) != {path: hashlib.sha256(resources[path]).hexdigest() for path in appearance_targets}:
        raise ValueError('Composed appearance receipt differs from its bytes')
    if report.get('portrait_files', {}) != {path: hashlib.sha256(resources[path]).hexdigest() for path in portrait_targets}:
        raise ValueError('Composed portrait receipt differs from its bytes')
    if report.get('behavior_files', {}) != {path: hashlib.sha256(resources[path]).hexdigest() for path in behavior_targets}:
        raise ValueError('Composed behavior receipt differs from its bytes')
    serialized = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('utf-8')
    if len(serialized) > max_report:
        raise ValueError('Generated preview report exceeds budget')
    root = ordinary_path(cache_root or ROOT / 'logs/fighter-native-preview')
    root.mkdir(parents=True, exist_ok=True)
    destination = ordinary_path(root / report['cache_key'])
    if not destination.exists():
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            stage = Path(temporary) / 'cache'
            (stage / 'assets').mkdir(parents=True)
            (stage / 'assets/djv2.sod').write_bytes(data)
            for relative, payload in resources.items():
                (stage / relative).parent.mkdir(parents=True, exist_ok=True)
                (stage / relative).write_bytes(payload)
            (stage / 'fighter-names.bin').write_bytes(encode_names(report['localization_entries']))
            (stage / 'fighter-bindings.bin').write_bytes(encode_bindings(report['handle_bindings']))
            if 'window' in report:
                (stage / 'fighter-window.bin').write_bytes(encode_window(report['window']))
            (stage / 'fighter-ledger.json').write_text(json.dumps(report['binding_ledger'], sort_keys=True, indent=2) + '\n', encoding='utf-8')
            (stage / 'report.json').write_bytes(serialized)
            try:
                durable_rename(stage, destination)
            except OSError:
                if not ordinary_path(destination).is_dir():
                    raise
    # Check exact leaves too: an existing cache may contain redirected children.
    for relative in ('assets/djv2.sod', 'fighter-names.bin', 'fighter-bindings.bin',
                     'fighter-window.bin', 'fighter-ledger.json', 'report.json'):
        ordinary_path(destination / relative)
    for relative, payload in resources.items():
        path = ordinary_path(destination / relative)
        with path.open('rb') as stream:
            actual = stream.read(len(payload) + 1)
        if actual != payload:
            raise ValueError('Existing preview appearance cache is corrupt; original data was not changed')
    cached = destination / 'assets/djv2.sod'
    with cached.open('rb') as stream:
        actual = stream.read(MAX_IMAGE + 1)
    if len(actual) != len(data) or hashlib.sha256(actual).hexdigest() != report['cache_sha256']:
        raise ValueError('Existing preview cache is corrupt; original data was not changed')
    with (destination / 'fighter-names.bin').open('rb') as stream:
        names = stream.read(2 * 1024**2)
    if names != encode_names(report['localization_entries']):
        raise ValueError('Existing preview name bindings are corrupt; original data was not changed')
    with (destination / 'fighter-bindings.bin').open('rb') as stream:
        bindings = stream.read(1024**2)
    if bindings != encode_bindings(report['handle_bindings']):
        raise ValueError('Existing preview fighter bindings are corrupt; original data was not changed')
    if 'window' in report:
        with (destination / 'fighter-window.bin').open('rb') as stream:
            window = stream.read(1024**2)
        if window != encode_window(report['window']):
            raise ValueError('Existing preview fighter window is corrupt; original data was not changed')
    with (destination / 'fighter-ledger.json').open('rb') as stream:
        ledger = stream.read(max_report + 1)
    if len(ledger) > max_report or json.loads(ledger, object_pairs_hook=unique) != report['binding_ledger']:
        raise ValueError('Existing preview identity ledger is corrupt; original data was not changed')
    with (destination / 'report.json').open('rb') as stream:
        saved = stream.read(max_report + 1)
    if len(saved) > max_report or json.loads(saved, object_pairs_hook=unique) != json.loads(serialized):
        raise ValueError('Existing preview report is corrupt; original data was not changed')
    return str(destination)
