"""Account for every source file and fighter without declaring a partial pack complete.

Consumes explicit local audit receipts and a hash inventory. Converted means
supported offline component conversion; native acceptance and complete package
admission are separate fields. Unresolved source art/globals remain blocked,
never silently excluded. Writes only a new private JSON report.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_build import retail_catalog
from fighter_sod import Database
from mods import safe_relative, ordinary_path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def document(path):
    if path.stat().st_size > 32 * 1024**2:
        raise ValueError('Accounting input exceeds report budget')
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--inventory', type=Path, required=True)
    parser.add_argument('--motion-report', type=Path, required=True)
    parser.add_argument('--portrait-report', type=Path, required=True)
    parser.add_argument('--voice-root', type=Path, required=True)
    parser.add_argument('--game', type=Path, default=ROOT / 'game')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Choose a new accounting report path')
    source = ordinary_path(args.source)
    inventory, motion, portraits = map(document, (args.inventory, args.motion_report, args.portrait_report))
    if motion.get('schema') != 'fighter-conversion-motion-audit-1' or portraits.get('schema') != 'fighter-conversion-portrait-audit-1':
        raise ValueError('Unsupported component audit receipts')
    files = {}
    total = 0
    for entry in inventory['entries']:
        if (len(files) >= 65536 or type(entry['bytes']) is not int
                or not 0 < entry['bytes'] <= 64 * 1024**2):
            raise ValueError('Source inventory exceeds file/population budget')
        total += entry['bytes']
        if total > 512 * 1024**2:
            raise ValueError('Source inventory exceeds aggregate budget')
        name = '/'.join(safe_relative(entry['path']))
        path = ordinary_path(source / name)
        if name in files or not path.is_relative_to(source):
            raise ValueError('Duplicate/escaping accounting input')
        with path.open('rb') as stream:
            data = stream.read(entry['bytes'] + 1)
        if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
            raise ValueError('Source changed since inventory: ' + name)
        files[name] = {'path': name, 'bytes': len(data), 'sha256': entry['sha256'],
                       'status': 'blocked', 'reason': 'Source semantics still need supported conversion/accounting'}
    actual = {p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()}
    if actual != files.keys():
        raise ValueError('Source file population differs from inventory')

    def classify(name, status, reason, evidence=None):
        if name not in files:
            raise ValueError('Receipt names a source file outside the inventory: ' + name)
        if status not in ('converted', 'exactly-inherited', 'explicit-dependency', 'excluded', 'blocked'):
            raise ValueError('Invalid accounting status')
        if files[name]['status'] != 'blocked':
            raise ValueError('Source has competing accounting claims: ' + name)
        files[name].update(status=status, reason=reason)
        if evidence:
            files[name]['evidence'] = evidence

    catalog = retail_catalog(args.game / 'assets/djv2.sod')
    pins = document(ROOT / 'config/fighter-native-baseline.json')
    def original(path, pin):
        data = (args.game / path).read_bytes()
        if digest(data) != pins[pin]:
            raise ValueError('Accounting original differs from verified baseline: ' + path)
        return Archive(data)
    raw_motion = original('motion/wres_all.viv', 'animation_sha256')
    raw_ai = original('assets/ai/ai.viv', 'ai_sha256')
    raw_models = original('assets/v2ip.viv', 'v2ip_sha256')
    legacy = {}
    for line in (source / 'coreid.txt').read_text().splitlines():
        words = line.split('#', 1)[0].split()
        if words:
            core, donor, voice = map(int, words)
            if core in legacy:
                raise ValueError('Duplicate source core mapping')
            legacy[core] = (donor, voice)
    original_names = {row['name'] for row in catalog.rows.values()}
    added = [row for row in Database((source / 'assets/djv2.sod').read_bytes()).character_metadata()['characters']
             if row['name'] not in original_names]
    actors = {row['source_core']: row for row in motion['fighters']}
    if set(actors) != {row['native_binding']['core_id'] for row in added}:
        raise ValueError('Motion report does not cover the actual added roster')
    portrait_rows = {row['source_core']: row for row in portraits['rows']}
    fighters, stable = [], set()
    for row in added:
        core = row['native_binding']['core_id']
        actor = actors[core]
        if actor['model'] != row['fields']['Model']['symbol']:
            raise ValueError('Motion report source appearance differs')
        donor = catalog.rows[actor['donor']]
        donor_core = donor['native_binding']['core_id']
        voice = legacy[core][1]
        if legacy[core][0] != donor_core:
            raise ValueError('Source core donor differs from motion report')
        voice_state = ('converted' if (args.voice_root / str(voice) / 'voice-export.json').is_file() else
                       'exactly-inherited' if voice == donor['fields']['SpeechId']['word'] else 'blocked')
        for suffix in ('.o', '.xsh', '_F.o'):
            name = 'assets/v2ip/' + actor['model'] + suffix
            classify(name, 'converted', 'Ordinary appearance compiler accepted actual model, textures and facial palette',
                     args.motion_report.name)
        for suffix in ('ord', 'orl', 'mnl'):
            name = f'motion/wres_all/wres{core:03d}.{suffix}'
            if unpack((source / name).read_bytes()) != unpack(raw_motion.read(f'wres{donor_core:03d}.{suffix}')):
                raise ValueError('Ordinary combat donor differs: ' + name)
            classify(name, 'exactly-inherited', 'Complete unpacked combat member equals mapped retail donor', actor['donor'])
        ai_name = f'assets/ai/char{core:04d}.xml'
        candidates = [entry.name for entry in raw_ai.entries if entry.name.lower().split('/')[-1] == f'char{donor_core:04d}.xml']
        if len(candidates) == 1 and unpack((source / ai_name).read_bytes()) == unpack(raw_ai.read(candidates[0])):
            classify(ai_name, 'exactly-inherited', 'Complete AI member equals mapped retail donor', actor['donor'])
        if portrait_rows.get(core, {}).get('passed'):
            for part, entry in portrait_rows[core]['inputs'].items():
                if files[entry['path']]['sha256'] != entry['sha256']:
                    raise ValueError('Portrait receipt differs from input inventory')
                classify(entry['path'], 'converted', 'Pixel-only ordinary six-slot portrait compilation: ' + part,
                         args.portrait_report.name)
        name = row['fields']['DisplayName']['symbol']
        local = re.sub('[^a-z0-9]+', '-', name.lower()).strip('-')
        if not local or local in stable:
            raise ValueError('Source needs an explicit stable identity decision: ' + name)
        stable.add(local)
        fighters.append({'stable_key': 'vendetta-roster/' + local, 'display_name': name,
                         'source_symbol': row['name'], 'source_core': core,
                         'source_selection': row['native_binding']['selection_key'], 'donor': actor['donor'],
                         'source_voice': voice,
                         'source_sod_speech_id': row['fields']['SpeechId']['word'],
                         'voice_authority': 'explicit legacy coreid mapping; SOD SpeechId retains its donor value',
                         'source_stats': {name.lower(): row['fields'][name]['word']
                                          for name in ('Health', 'Speed', 'Toughness', 'Charisma')},
                         'components': {'appearance': 'converted', 'ordinary_combat': 'exactly-inherited',
                             'voice': voice_state, 'stats': 'decoded; final ordinary manifest pending',
                             'ai': files[ai_name]['status'], 'portrait': 'converted' if portrait_rows.get(core, {}).get('passed') else 'blocked',
                             'paired_motion': 'typed rebuild/context joins pass; package/native admission blocked',
                             'intro': 'blocked', 'victory': 'blocked', 'activation': 'blocked'}})
    for folder in sorted(args.voice_root.iterdir()):
        if not folder.is_dir() or not re.fullmatch(r'0|[1-9][0-9]{0,4}', folder.name):
            continue
        voice = int(folder.name)
        report = document(folder / 'voice-export.json')
        if report.get('schema') != 'fighter-voice-export-1':
            raise ValueError('Unsupported voice export receipt')
        for category in ('Character', 'Taunts', 'Enviro'):
            bank = report['categories'][category]
            if bank['state'] == 'absent':
                continue
            for suffix, hash_field in (('hdr', 'header_sha256'), ('dat', 'data_sha256')):
                path = f'speech/{category}/Def_Jam_IP_Characters/{voice}.{suffix}'
                if files[path]['sha256'] != bank[hash_field]:
                    raise ValueError('Voice bank report differs from source')
                classify(path, 'converted', 'Explicit family/event template matched; every logical R2 clip exported; unindexed bytes reported',
                         f'{folder.name}/voice-export.json')
        for purpose in ('intro', 'extro'):
            path = f'speech/streams/{purpose}/{voice}.asf'
            if files[path]['sha256'] != report['categories'][purpose]['input_sha256']:
                raise ValueError('Cinematic voice report differs from source')
            classify(path, 'converted', 'Owned R2 cinematic stream exported with its original coded blocks',
                     f'{folder.name}/voice-export.json')
    for name, row in files.items():
        if row['status'] != 'blocked':
            continue
        if name.startswith('assets/v2ta/'):
            row['reason'] = 'Cinematic constants/block compression/empty parents/camera scalar outputs need a general typed adapter and native semantics'
        elif name.startswith('motion/blazin/'):
            row['reason'] = 'Actual matched five-role typed rebuild and output joins pass; versioned package/runtime admission and native playback remain'
        elif name.startswith('screens/'):
            row['reason'] = 'Ancillary artwork or native movie edits need explicit consumer/content accounting; whole source movies are not imported'
        elif name in ('assets/entity.xml', 'assets/IntroExtro.xml', 'audio/animtags.dat', 'motion/camera.xml', 'blazin_activation.txt'):
            row['reason'] = 'Shared source change may affect fighter behavior; must be decomposed and verified, not dismissed as unrelated'
        elif name == 'assets/djv2.sod':
            row['reason'] = '46 stable added definitions mapped; complete ordinary manifest/component conversion remains'
        elif name == 'motion/main_all.dat':
            row['reason'] = 'Shared-table exact matching proved; owned per-core/graph compilation and complete source-core accounting remain'
        elif name.startswith('assets/v2ip/'):
            member = name.split('/')[-1]
            if member.lower() in raw_models.by_name and unpack((source / name).read_bytes()) == unpack(raw_models.read(member)):
                classify(name, 'exactly-inherited', 'Complete unreferenced supplied model equals verified original')
            else:
                row['reason'] = 'Additional source model outside added appearance set requires explicit global/dependency analysis'
    for name in ('mod.ini', 'couverture.png'):
        classify(name, 'excluded', 'Legacy catalogue metadata or cover art; ordinary fighter package needs neither')
    classify('coreid.txt', 'converted', 'Legacy core/donor/voice association consumed outside the engine; stable keys recorded in this report')
    counts = collections.Counter(row['status'] for row in files.values())
    report = {'schema': 'fighter-conversion-source-accounting-1', 'archive_sha256': inventory['archive_sha256'],
              'source_bytes': sum(row['bytes'] for row in files.values()), 'summary': dict(counts),
              'files': [files[name] for name in sorted(files)], 'fighters': fighters,
              'identity_policy': 'Preserve these stable keys in subsequent pack versions; source core/selection are conversion metadata only',
              'converted_scope': 'offline supported component conversion; native visual/audio/lifetime acceptance remains separate',
              'complete_conversion': False, 'native_playtest': False, 'package_emitted': False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as output:
        output.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'files': len(files), 'fighters': len(fighters), 'bytes': report['source_bytes'], **dict(counts)}))


if __name__ == '__main__':
    main()
