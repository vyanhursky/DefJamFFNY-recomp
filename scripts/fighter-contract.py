#!/usr/bin/env python3
"""Read-only authoring bridge to the recomp's actual Fighter package contract.

Creator commands live in DefJam-Modding-Tools. This API keeps validation and
native format admission in the runtime repository, without installing a pack
or writing settings/profiles. Generated resources exist only in a temporary
validation workspace. Success is compilation evidence, not an in-game test.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_build import retail_catalog, compile_inputs, write_preview, unique, non_finite, MAX_DOCUMENT, MAX_INPUT, MAX_PACKS
from fighter_packages import inventory, descriptors
from fighter_presentation import prepare_portraits, prepare_language_screens
from mods import ordinary_path

PROTOCOL = 'fighter-authoring-api-1'


def voice_catalog(game):
    """Only emit event identities for templates accepted by the actual compiler."""
    import re
    from fighter_voice_compile import VoiceCompiler
    from fighter_voice_bank import VoiceBankTemplate, event_identity, FAMILIES
    pin = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text())
    path = game / 'audio/speech2.viv'
    if path.stat().st_size > 512 * 1024**2:
        raise ValueError('Voice archive exceeds budget')
    compiler = VoiceCompiler(path.read_bytes(), pin['speech_sha256'])
    rows = []
    for entry in compiler.archive.entries:
        name = compiler.archive.name_key(entry.name)
        match = re.fullmatch(r'speech/(character|taunts|enviro)/def_jam_(?:ip_)?characters/(\d+)\.hdr', name)
        if not match:
            continue
        category = next(c for c in FAMILIES if c.lower() == match[1])
        header, data = compiler.archive.read(name), compiler.archive.read(name[:-4] + '.dat')
        try:
            template = VoiceBankTemplate(header, data, hashlib.sha256(header).hexdigest(), hashlib.sha256(data).hexdigest())
        except ValueError:
            # Unsupported original profiles are unavailable conversion templates.
            continue
        if template.first_key not in FAMILIES[category] or template.voice_key != int(match[2]):
            continue
        rows.append({'category': category, 'template_voice': template.voice_key,
                     'event_identity': event_identity(header, include_family=False),
                     'entries': template.count})
    return {'protocol': PROTOCOL, 'ok': True, 'archive_sha256': pin['speech_sha256'],
            'identity': 'fighter-voice-events-1', 'templates': sorted(rows, key=lambda r: (r['category'], r['template_voice']))}


def validate_voice(game, path):
    """Compile an export staging source through the actual shared voice path."""
    from fighter_behavior_files import Reader, MAX_FILE
    from fighter_voice_compile import VoiceCompiler, encode_voice_bindings
    path = ordinary_path(path)
    with path.open('rb') as stream:
        before = stream.read(MAX_DOCUMENT + 1)
    if len(before) > MAX_DOCUMENT:
        raise ValueError('Voice source exceeds document budget')
    source = json.loads(before, object_pairs_hook=unique, parse_constant=non_finite)
    voice = Reader().resource(path.parent, 'voice', source)
    pin = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text())
    archive = game / 'audio/speech2.viv'
    if archive.stat().st_size > 512 * 1024**2:
        raise ValueError('Voice archive exceeds budget')
    data, report = VoiceCompiler(archive.read_bytes(), pin['speech_sha256']).compose({'authoring/voice': voice})
    table = encode_voice_bindings(data, report, {141: 'authoring/voice'})
    with path.open('rb') as stream:
        after = stream.read(MAX_DOCUMENT + 1)
    if after != before:
        raise ValueError('Voice source changed during compilation')
    for spec in descriptors(source):
        asset = ordinary_path(path.parent / spec['path'])
        if not asset.is_relative_to(path.parent):
            raise ValueError('Voice file escapes source folder')
        with asset.open('rb') as stream:
            current = stream.read(MAX_FILE + 1)
        if len(current) > MAX_FILE or hashlib.sha256(current).hexdigest() != spec['sha256']:
            raise ValueError('Voice files changed during compilation')
    return {'protocol': PROTOCOL, 'ok': True, 'component_compilation': True, 'native_playtest': False,
            'source_sha256': hashlib.sha256(before).hexdigest(),
            'archive_sha256': report['sha256'], 'binding_sha256': hashlib.sha256(table).hexdigest()}


def validate(game, folders, language=None):
    folders = [ordinary_path(Path(folder)) for folder in folders]
    if not 0 < len(folders) <= MAX_PACKS or sum((folder / 'fighters.json').stat().st_size for folder in folders) > MAX_INPUT:
        raise ValueError('Pack manifests exceed the combined validation budget')
    packs = [inventory(folder) for folder in folders]
    paths = [folder / 'fighters.json' for folder in folders]
    if len({pack['id'] for pack in packs}) != len(packs):
        raise ValueError('Duplicate pack ID in validation set')
    before = [{p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in folder.rglob('*') if p.is_file()} for folder in folders]
    data, report, resources = compile_inputs(game / 'assets/djv2.sod', paths, packs, binding_window=True)
    with tempfile.TemporaryDirectory(prefix='fighter-validation-', dir=Path(tempfile.gettempdir()).resolve()) as temporary:
        cache = Path(write_preview(data, report, resources, cache_root=Path(temporary) / 'native'))
        screens = game / 'screens/screens.viv'
        composed = prepare_language_screens(screens, language) if language else None
        prepare_portraits(screens, report, language=composed, resource_cache=cache,
                         cache_root=Path(temporary) / 'menus')
    for folder, files in zip(folders, before):
        after = {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in folder.rglob('*') if p.is_file()}
        if after != files:
            raise ValueError('Pack changed during validation; retry from a stable workspace')
    return {'protocol': PROTOCOL, 'ok': True, 'native_compilation': True,
            'native_playtest': False, 'schema': 'fighter-registry-draft-1',
            'cache_key': report['cache_key'], 'added_fighters': report['added_count'],
            'binding_mode': report['binding_mode'],
            'packs': [{'id': pack['id'], 'version': pack['version'], 'files': files}
                      for pack, files in zip(packs, before)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('catalog','tag-catalog', 'voice-catalog', 'validate-voice', 'export-pair','export-cinematic', 'export-caf-portrait','export-ui-reference', 'validate', 'workshop-catalog','workshop-check','workshop-audio','workshop-animation','workshop-export'))
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--pack', type=Path, action='append', default=[])
    parser.add_argument('--language', type=Path)
    parser.add_argument('--portrait-png', type=Path)
    parser.add_argument('--portrait-out', type=Path)
    parser.add_argument('--donor',default='retail/blaze')
    parser.add_argument('--voice-source', type=Path)
    parser.add_argument('--pair-request',type=Path)
    parser.add_argument('--cinematic-request',type=Path)
    parser.add_argument('--workshop-request',type=Path)
    parser.add_argument('--workshop-out',type=Path)
    args = parser.parse_args()
    try:
        if args.command.startswith('workshop-'):
            import fighter_workshop as workshop
            request=None
            if args.command!='workshop-catalog':
                if args.workshop_request is None:raise ValueError('Choose an authoring request')
                path=ordinary_path(args.workshop_request)
                with path.open('rb') as stream:raw=stream.read(96*1024**2+1)
                if len(raw)>96*1024**2:raise ValueError('Authoring request exceeds budget')
                request=json.loads(raw,object_pairs_hook=unique,parse_constant=non_finite)
            if args.command=='workshop-catalog':payload=workshop.catalog(args.game)
            elif args.command=='workshop-check':payload=workshop.check(request,workshop.catalog(args.game))
            elif args.command=='workshop-audio':payload=workshop.audio(args.game,request)
            elif args.command=='workshop-export':
                if args.workshop_out is None:raise ValueError('Choose a new performance output folder')
                payload=workshop.export_performance(args.game,request,args.workshop_out)
            else:
                from fighter_workshop_animation import animation
                payload=animation(args.game,request)
            result={'protocol':PROTOCOL,'ok':True,**payload}
        elif args.command == 'catalog':
            catalog=retail_catalog(args.game/'assets/djv2.sod')
            result = {'protocol': PROTOCOL, 'ok': True,
                      'baseline': catalog.baseline(),
                      'native_models':{row['fields']['Model']['symbol']:key for key,row in catalog.rows.items()}}
        elif args.command=='export-ui-reference':
            if args.portrait_out is None:raise ValueError('Choose a new UI reference output folder')
            from fighter_ui_art import export_reference
            pin=json.loads((ROOT/'config/fighter-native-baseline.json').read_text())
            result={'protocol':PROTOCOL,'ok':True,**export_reference(args.game,args.donor,args.portrait_out,retail_catalog(args.game/'assets/djv2.sod'),pin)}
        elif args.command=='export-caf-portrait':
            if args.portrait_png is None or args.portrait_out is None:raise ValueError('Choose a PNG and a new portrait output folder')
            from fighter_caf_portrait import export_png
            pin=json.loads((ROOT/'config/fighter-native-baseline.json').read_text())
            result={'protocol':PROTOCOL,'ok':True,**export_png(args.game,args.portrait_png,args.portrait_out,retail_catalog(args.game/'assets/djv2.sod'),pin)}
        elif args.command=='tag-catalog':
            from fighter_timelines import TagTimelines
            pins=json.loads((ROOT/'config/fighter-native-baseline.json').read_text())
            tags=TagTimelines((args.game/'audio/animtags.dat').read_bytes(),pins['tags_sha256'])
            result={'protocol':PROTOCOL,'ok':True,'rows':{row['name']:hashlib.sha256(row['raw']).hexdigest() for row in tags.rows}}
        elif args.command == 'voice-catalog':
            result = voice_catalog(args.game)
        elif args.command == 'validate-voice':
            if args.voice_source is None:
                raise ValueError('Choose a voice source JSON file')
            result = validate_voice(args.game, args.voice_source)
        elif args.command == 'export-pair':
            if args.pair_request is None:
                raise ValueError('Choose a pair export request')
            from fighter_pair_export import export_pair
            pins=json.loads((ROOT/'config/fighter-native-baseline.json').read_text())
            result={'protocol':PROTOCOL,'ok':True,**export_pair(args.game,args.pair_request,pins)}
        elif args.command=='export-cinematic':
            if args.cinematic_request is None:raise ValueError('Choose a cinematic export request')
            from fighter_film_export import export_film
            pins=json.loads((ROOT/'config/fighter-native-baseline.json').read_text())
            result={'protocol':PROTOCOL,'ok':True,**export_film(args.game,args.cinematic_request,pins)}
        else:
            if not args.pack:
                raise ValueError('Choose at least one pack folder')
            result = validate(args.game, args.pack, args.language)
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as error:
        print(json.dumps({'protocol': PROTOCOL, 'ok': False, 'error': str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
