"""Check actual legacy finisher bindings, rebuilt appearances and all opponents.

Offline audit of a source folder with djv2.sod, coreid.txt, loose appearance
members and paired motions. Uses the ordinary appearance compiler and actual
matched retail finisher templates. Rebuilt motion bytes remain in memory; the
new output is only a hash/context report. This does not admit full graphs in
packages or prove native blending, camera transitions or playback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_compile import AnimationTemplate
from fighter_animation_graphs import FullMotionTemplate, read_motion
from fighter_appearance import Appearance, AppearanceBaseline
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_build import retail_catalog
from fighter_elf import Model
from fighter_face import FacePalettes
from fighter_motion import MotionIndex
from fighter_motion_contexts import MotionOutputContexts
from fighter_motion_matching import match_finishers
from fighter_registry import fingerprint
from fighter_rig import Skeleton
from fighter_sod import Database


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--game', type=Path, default=ROOT / 'game')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'Choose a new audit report path')
    source, game = args.source, args.game
    pins = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text())

    def original(path, pin):
        data = (game / path).read_bytes()
        require(digest(data) == pins[pin], 'Original differs from baseline: ' + path)
        return data

    catalog = retail_catalog(game / 'assets/djv2.sod')
    baseline = AppearanceBaseline({label: original('assets/' + name, pin) for label, name, pin in (
        ('models', 'v2ip.viv', 'v2ip_sha256'), ('shared', 'blingfx.viv', 'blingfx_sha256'),
        ('entities', 'entity.xml', 'entities_sha256'), ('cinematics', 'nis.viv', 'nis_sha256'),
        ('banks', 'v2ta.viv', 'v2ta_sha256'))}, pins)
    misc = Archive(original('assets/misc.viv', 'misc_sha256'))
    hand_data = unpack(misc.read('share_hp.o'))
    contexts = MotionOutputContexts(FacePalettes(Model(hand_data), 57, (32, 32)), pins['shared_hand_sha256'])
    targets = []
    for key, row in sorted(catalog.rows.items()):
        model = row['fields']['Model']['symbol']
        body, face = (unpack(baseline.models.read(model + suffix)) for suffix in ('.o', '_F.o'))
        contexts.add(key, body, face, model_sha256=digest(body), face_sha256=digest(face))
        targets.append(key)
    mapping = {}
    for line in (source / 'coreid.txt').read_text().splitlines():
        words = line.split('#', 1)[0].split()
        if words:
            core, donor, voice = map(int, words)
            require(core not in mapping, 'Duplicate legacy core mapping')
            mapping[core] = (donor, voice)
    originals = {r['name'] for r in catalog.rows.values()}
    added = [row for row in Database((source / 'assets/djv2.sod').read_bytes()).character_metadata()['characters']
             if row['name'] not in originals]
    require(added, 'No added source fighters found')
    by_core = {row['native_binding']['core_id']: (key, row) for key, row in catalog.rows.items()}
    source_motion = MotionIndex((source / 'motion/main_all.dat').read_bytes())
    retail_motion = MotionIndex(original('motion/main_all.dat', 'motion_sha256'))
    owners, fighters = {}, []
    for row in added:
        core, model = row['native_binding']['core_id'], row['fields']['Model']['symbol']
        donor_core, _voice = mapping[core]
        donor, donor_row = by_core[donor_core]
        files = {part: (source / 'assets/v2ip' / (model + suffix)).read_bytes()
                 for part, suffix in (('model', '.o'), ('textures', '.xsh'), ('face', '_F.o'))}
        spec = {'format': 'eagl-appearance-1', 'donor': donor,
                **{part: {'path': part + '.bin', 'sha256': digest(data)} for part, data in files.items()}}
        assigned = 'converted/fighter-' + str(core)
        origin = 'source/fighter-' + str(core)
        appearance = Appearance(assigned, spec, files, baseline, donor_row['fields']['Model']['symbol'])
        body, face = (unpack(appearance.files[appearance.name + suffix]) for suffix in ('.o', '_F.o'))
        source_body, source_face = unpack(files['model']), unpack(files['face'])
        # The source graph's joint identity must survive the actual compiler,
        # rather than merely stamping an arbitrary supplied rig hash on it.
        require(Skeleton(Model(source_body)).pose_sha256 == Skeleton(Model(body)).pose_sha256,
                'Appearance compiler changed the source motion rig')
        contexts.add(origin, source_body, source_face, model_sha256=digest(source_body), face_sha256=digest(source_face))
        context = contexts.add(assigned, body, face, model_sha256=digest(body), face_sha256=digest(face))
        targets.append(assigned)
        choices = source_motion.record('core', core - 1).values[88:92]
        for slot, choice in enumerate(choices):
            if choice >= 82:
                owners.setdefault(choice, []).append({'fighter': assigned, 'origin': origin, 'slot': slot})
        fighters.append({'source_symbol': row['name'], 'source_core': core, 'model': model,
                         'donor': donor, 'slots': list(choices), 'context': context})
    source_names = unpack((source / 'motion/blazin/blazin.mnl').read_bytes())
    count, reserved = struct.unpack_from('<2I', source_names)
    tokens = source_names[8:-1].decode('ascii').split('.')
    require(reserved == 0 and source_names.endswith(b'.') and count == len(tokens) and not count % 2,
            'Source paired name population is invalid')
    choices = list(range(82, count // 2))
    matched = match_finishers(retail_motion, source_motion, choices)
    require(set(choices) == set(owners), 'Source contains unowned or unaccounted added finishing choices')
    retail_pairs = Archive(original('motion/blazin.viv', 'blazin_sha256'))
    retail_tokens = unpack(retail_pairs.read('blazin.mnl'))[8:-1].decode('ascii').split('.')
    roles = []
    for choice in choices:
        template_choice = matched['mapping'][str(choice)]
        origin = owners[choice][0]['origin']
        rig, face, _identity = contexts.contexts[origin]
        for role, offset in (('subject', 0), ('counterpart', 1)):
            token, template = tokens[2 * choice + offset], retail_tokens[2 * template_choice + offset]
            source_parts = [unpack((source / 'motion/blazin' / (token + '.' + suffix)).read_bytes())
                            for suffix in ('ord', 'orl')]
            source_index = AnimationIndex(AnimationEnvelope(*source_parts, struct.pack('<2I', 1, 0) + token.encode() + b'.'))
            trusted = AnimationEnvelope(*(unpack(retail_pairs.read(template + '.' + suffix)) for suffix in ('ord', 'orl')),
                                        struct.pack('<2I', 1, 0) + template.encode() + b'.')
            compiler = FullMotionTemplate(AnimationTemplate(trusted, digest(trusted.model.data), rig.pose_sha256,
                                                            len(rig.rows)), face, contexts.hands)
            compiled, receipt = compiler.convert(source_index, token, template)
            value = read_motion(source_index, token, rig.pose_sha256, len(rig.rows))
            allowed = sorted({owner['fighter'] for owner in owners[choice]}) if role == 'subject' else sorted(targets)
            joined = contexts.join(value, origin, allowed)
            roles.append({'source_choice': choice, 'template_choice': template_choice, 'role': role,
                          'source_token': token, 'template_token': template, 'owners': owners[choice],
                          'source_sha256': digest(b''.join(source_parts)), 'compiled_sha256': receipt['sha256'],
                          'compiled_bytes': len(compiled.model.data), 'context_targets': allowed,
                          'context_join_sha256': joined['sha256'], 'typed_graph_sha256': fingerprint(value)})
    report = {'schema': 'fighter-conversion-motion-audit-1', 'fighters': fighters, 'roles': roles,
              'finisher_behavior': matched, 'hand_identity': contexts.hand_identity,
              'contexts': {name: identity for name, (_rig, _face, identity) in contexts.contexts.items()},
              'summary': {'fighters': len(fighters), 'choices': len(choices), 'rebuilt_roles': len(roles),
                          'target_joins': sum(len(row['context_targets']) for row in roles),
                          'normal_opponent_contexts': len(targets)},
              'package_admission': False, 'native_blending_validated': False, 'native_playtest': False,
              'created_fighter_dynamic_context': 'not established by normal appearance joins'}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as output:
        output.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary']))


if __name__ == '__main__':
    main()
