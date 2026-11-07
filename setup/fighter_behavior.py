"""Compose resolved, data-only behavior resources as one research generation.

Core identities belong to fighters. Animation, voice, AI and cinematic resource
identities remain independently shareable. All native tables are generated
here from verified originals; a pack cannot supply a native binding table.
"""
import hashlib
import struct

from fighter_assets import AssetError, unpack
from fighter_archive import Archive, MAX_ARCHIVE
from fighter_behavior_files import Reader, KINDS
from fighter_registry import fingerprint
from fighter_motion_compile import MotionCoreTemplates
from fighter_moveset import compose_selected_cores, MovesetPlan
from fighter_animation import AnimationEnvelope
from fighter_animation_archive import AnimationArchive, encode_animation_bindings
from fighter_voice_compile import VoiceCompiler, encode_voice_bindings
from fighter_ai import AIProfiles, encode_ai_bindings
from fighter_cinematic_compile import CinematicArchive, bind_cinematics
from fighter_blazin_compile import BlazinArchive, encode_blazin_bindings
from fighter_blazin_pairs import BlazinPairs, encode_pair_bindings
from fighter_cinematics import Cinematics
from fighter_elf import Model
from fighter_rig import Skeleton

TARGETS = {
    'motion': ('motion/main_all.dat', 'fighter-motion.bin'),
    'animation': ('motion/wres_all.viv', 'fighter-animations.bin'),
    'voice': ('audio/speech2.viv', 'fighter-voices.bin'),
    'ai': ('assets/ai/ai.viv', 'fighter-ai.bin'),
    'cinematic': ('assets/v2ta.viv', 'assets/nis.viv', 'assets/v2ip.viv', 'assets/entity.xml', 'fighter-cinematics.bin'),
    'blazin': ('fighter-blazin.bin',),
    'finishers': ('motion/blazin.viv', 'fighter-finishers.bin'),
}


def targets(receipts):
    require(type(receipts) is dict and 'motion' in receipts
            and set(receipts) <= TARGETS.keys() | {'cinematic_bindings'}
            and ('blazin' not in receipts or 'cinematic' in receipts)
            and ('cinematic' in receipts) == ('cinematic_bindings' in receipts),
            'Invalid behavior artifact receipt set')
    return {path for kind, paths in TARGETS.items() if kind in receipts for path in paths}


def environment(cache, report):
    """Research launch arguments for the exact composed artifact set."""
    from mods import ordinary_path
    hashes, receipts = report['behavior_files'], report['behavior_receipts']
    require(set(hashes) == targets(receipts), 'Behavior launch artifact set differs')
    result = {}
    for kind, archive_var, binding_var in (
            ('motion', 'MOTION', 'MOTION_BINDINGS'),
            ('animation', 'ANIMATIONS', 'ANIMATION_BINDINGS'),
            ('voice', 'VOICES', 'VOICE_BINDINGS'),
            ('ai', 'AI', 'AI_BINDINGS'),
            ('finishers', 'FINISHERS', 'FINISHER_BINDINGS'),
            ('cinematic', 'CINEMATIC_BANKS', 'CINEMATIC_BINDINGS')):
        if kind not in receipts:
            continue
        archive, *_, table = TARGETS[kind]
        result['RECOMP_FIGHTER_' + archive_var] = str(ordinary_path(cache / archive))
        result['RECOMP_FIGHTER_' + archive_var + '_SHA256'] = hashes[archive]
        result['RECOMP_FIGHTER_' + binding_var] = str(ordinary_path(cache / table))
    if 'cinematic' in receipts:
        for name, path in (('CINEMATICS', 'assets/nis.viv'), ('MODELS', 'assets/v2ip.viv'), ('ENTITIES', 'assets/entity.xml')):
            result['RECOMP_FIGHTER_RESEARCH_' + name] = str(ordinary_path(cache / path))
            result['RECOMP_FIGHTER_RESEARCH_' + name + '_SHA256'] = hashes[path]
    if 'blazin' in receipts:
        require('cinematic' in receipts, 'Blazin needs the composed cinematic archive')
        result['RECOMP_FIGHTER_BLAZIN_BINDINGS'] = str(ordinary_path(cache / 'fighter-blazin.bin'))
    return result


def require(condition, message):
    if not condition:
        raise AssetError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class BehaviorPlan:
    """Internal validated result consumed by the native database compiler."""
    def __init__(self, catalog, snapshot, roots, game, pins, appearances, composed):
        self.snapshot_sha256 = snapshot['sha256']
        self.source_sha256 = catalog.source_sha256
        self.donors, self.character_cores, self.voice_ids = {}, {}, {}
        self.files, self.receipts, self.sources = {}, {}, {}
        reader, typed, originals = Reader(), {}, {}

        def original(relative, pin):
            if relative not in originals:
                with (game / relative).open('rb') as stream:
                    data = stream.read(MAX_ARCHIVE + 1)
                require(0 < len(data) <= MAX_ARCHIVE and digest(data) == pins[pin],
                        'Behavior original differs from its supported baseline: ' + relative)
                originals[relative] = data
            return originals[relative]

        for key, resource in snapshot['resources'].items():
            if resource['kind'] in KINDS and 'source' in resource:
                typed[key] = reader.resource(roots[resource['owner']], resource['kind'], resource['source'])
                self.sources[key] = fingerprint(resource['source'])
        added = {key: row['components'] for key, row in snapshot['fighters'].items() if key not in catalog.rows}
        require(added, 'Behavior composition requires an added fighter')
        for key, row in snapshot['fighters'].items():
            require(key not in catalog.rows or not any(value in typed for group, value in row['components'].items()
                                                      if group != 'stats'),
                    'Authored retail behavior overrides need a separate identity adapter')
        rigs = {}

        def rig_for(components):
            key = components['appearance']
            if key not in rigs:
                if key in appearances:
                    appearance = appearances[key]
                    model = unpack(appearance.files[appearance.name + '.o'])
                else:
                    require(key in catalog.bindings, 'Behavior needs a validated appearance rig')
                    donor = catalog.rows[catalog.bindings[key]['donor']]
                    archive = Archive(original('assets/v2ip.viv', 'v2ip_sha256'))
                    model = unpack(archive.read(donor['fields']['Model']['symbol'] + '.o'))
                rigs[key] = Skeleton(Model(model))
            return rigs[key]

        motion_source = original('motion/main_all.dat', 'motion_sha256')
        templates = MotionCoreTemplates(motion_source, pins['motion_sha256'])
        animation_source = None
        motion_resources, animation_resources, animation_keys = {}, {}, {}
        voice_keys, ai_keys, cinematic_keys = {}, {}, {}
        cinematic_resources = {}
        blazin_keys, blazin_resources = {}, {}
        pair_keys, pair_resources = {}, {}
        slot_bindings = any('slots' in source for source in typed.values())
        for fighter, components in sorted(added.items()):
            moveset = components['moveset']
            authored = typed.get(moveset)
            require(authored is not None or moveset in catalog.bindings, 'Moveset needs a validated source')
            donor_key = authored['donor'] if authored else catalog.bindings[moveset]['donor']
            require(donor_key in catalog.rows, 'Unknown moveset donor')
            donor = catalog.rows[donor_key]['native_binding']['core_id'] - 1
            self.donors[fighter] = donor_key
            motion_resources[fighter] = donor
            if authored:
                resource = snapshot['resources'][moveset]
                require(resource['compatibility'] == {'skeleton': 'retail/binding-' + donor_key.split('/')[1],
                                                     'events': 'retail/binding-' + donor_key.split('/')[1]},
                        'Moveset source differs from its declared rig/event family')
                rig = rig_for(components)
                if animation_source is None:
                    animation_source = original('motion/wres_all.viv', 'animation_sha256')
                archive = Archive(animation_source)
                envelope = AnimationEnvelope(*(unpack(archive.read(f'wres{donor + 1:03d}.' + suffix))
                                               for suffix in ('ord', 'orl', 'mnl')))
                animation = {'template_bank': donor + 1, 'rig_sha256': rig.pose_sha256,
                             'bone_count': len(rig.rows), 'replacements': authored['tracks']}
                if authored['selections']:
                    plan = MovesetPlan(templates.index, donor, envelope, digest(envelope.model.data))
                    animation['moveset'] = {'plan': plan, 'selections': authored['selections']}
                    motion_resources[fighter] = {'donor': donor, 'envelope': envelope,
                        'bank_sha256': digest(envelope.model.data), 'selections': authored['selections']}
                if moveset in animation_resources:
                    require(animation_resources[moveset]['rig_sha256'] == rig.pose_sha256,
                            'Shared moveset is bound to different appearance rigs')
                else:
                    animation_resources[moveset] = animation
                animation_keys[fighter] = moveset
            voice = components['voice']
            if voice in typed:
                family = snapshot['resources'][voice]['compatibility']['events']
                expected_family = 'retail/binding-' + donor_key.split('/')[1]
                # Version3 names each category's verified template and exact
                # family. The declared event namespace still joins the moveset;
                # bank identity is no longer inferred from one donor SpeechId.
                require(family == expected_family and ('banks' in typed[voice] or
                        typed[voice]['template_voice'] == catalog.rows[donor_key]['fields']['SpeechId']['word']),
                        'Voice template differs from the inherited event family')
                voice_keys[fighter] = voice
            if 'ai' in components:
                require(components['ai'] in typed, 'AI needs a validated source')
                ai_keys[fighter] = components['ai']
            rig = rig_for(components)
            if 'blazin' in components:
                resource_key = components['blazin']
                require(resource_key in typed, 'Blazin needs a validated source')
                if resource_key in blazin_resources:
                    require(blazin_resources[resource_key]['rig_sha256'] == rig.pose_sha256,
                            'Shared Blazin is bound to different appearance rigs')
                else:
                    blazin_resources[resource_key] = {'rig_sha256': rig.pose_sha256,
                        'bone_count': len(rig.rows), 'shots': typed[resource_key]['shots']}
                blazin_keys[fighter] = resource_key
                native = templates.index.record('core', donor).native_bytes()
                inherited_choices = struct.unpack_from('<4I', native, 0xD4)
                for choice, tracks in typed[resource_key]['pairs'].items():
                    require(choice in inherited_choices,
                            'Authored finisher is not selected by this moveset template')
                    pair_key = resource_key.split('/')[0] + '/pair-' + fingerprint([resource_key, choice])[:32]
                    pair_resources[pair_key] = {'template_choice': choice, 'rig_sha256': rig.pose_sha256,
                                               'bone_count': len(rig.rows), **tracks}
                    for selection in ([slot for slot, value in enumerate(inherited_choices) if value == choice]
                                      if slot_bindings else [choice]):
                        pair_keys.setdefault(fighter, {})[selection] = pair_key
                if 'slots' in typed[resource_key]:
                    choices = {}
                    for slot, pair in typed[resource_key]['slots'].items():
                        pair_key = resource_key.split('/')[0] + '/pair-' + fingerprint([resource_key, 'slot', slot])[:32]
                        pair_resources[pair_key] = {'rig_sha256': rig.pose_sha256,
                                                   'bone_count': len(rig.rows), **pair}
                        pair_keys.setdefault(fighter, {})[slot] = pair_key
                        choices[slot] = pair['template_choice']
                    if type(motion_resources[fighter]) is int:
                        motion_resources[fighter] = {'donor': donor}
                    motion_resources[fighter]['finisher_slots'] = choices
            appearance = components['appearance']
            appearance_donor = appearances[appearance].donor if appearance in appearances else catalog.bindings[appearance]['donor']
            model = catalog.rows[appearance_donor]['fields']['Model']['symbol']
            nis = Archive(original('assets/nis.viv', 'nis_sha256'))
            inherited = Cinematics(unpack(nis.read('assets/IntroExtro.xml')), pins['intro_extro_sha256']).inherit(model, model)
            pair = {}
            for category, prefix in (('intro', 'CI_'), ('victory', 'CE_')):
                resource_key = components.get(category)
                if resource_key is not None:
                    require(resource_key in typed, 'Cinematic needs a validated source')
                    source = typed[resource_key]
                    token, tracks = source['template'], source['tracks']
                else:
                    token, tracks = getattr(inherited, category), None
                require(token.startswith(prefix), 'Cinematic resource has the wrong category')
                # Shared pack resources compile once. The inherited namespace
                # contains a character forbidden in package identity slugs.
                internal = resource_key or '@inherited/' + fingerprint([token, rig.pose_sha256])
                if internal in cinematic_resources:
                    require(cinematic_resources[internal]['rig_sha256'] == rig.pose_sha256,
                            'Shared cinematic is bound to different appearance rigs')
                else:
                    cinematic_resources[internal] = {'template': token, 'tracks': tracks,
                        'rig_sha256': rig.pose_sha256, 'bone_count': len(rig.rows)}
                pair[category] = internal
            cinematic_keys[fighter] = pair

        motion, receipt, table = compose_selected_cores(templates, motion_resources)
        self.files.update({'motion/main_all.dat': motion, 'fighter-motion.bin': table})
        self.receipts['motion'] = receipt
        self.character_cores = {key: row['character_core'] for key, row in receipt['bindings'].items()}

        def cores(mapping):
            return {self.character_cores[key] - 1: value for key, value in mapping.items()}

        if animation_resources:
            data, receipt = AnimationArchive(animation_source, pins['animation_sha256']).compose(animation_resources)
            self.files.update({'motion/wres_all.viv': data,
                               'fighter-animations.bin': encode_animation_bindings(data, receipt, cores(animation_keys))})
            self.receipts['animation'] = receipt
        if voice_keys:
            source = original('audio/speech2.viv', 'speech_sha256')
            data, receipt = VoiceCompiler(source, pins['speech_sha256']).compose({key: typed[key] for key in set(voice_keys.values())})
            self.files.update({'audio/speech2.viv': data,
                               'fighter-voices.bin': encode_voice_bindings(data, receipt, cores(voice_keys))})
            self.receipts['voice'] = receipt
            self.voice_ids = {key: row['voice_id'] for key, row in receipt['bindings'].items()}
        if ai_keys:
            source = original('assets/ai/ai.viv', 'ai_sha256')
            data, receipt = AIProfiles(source, pins['ai_sha256']).compose({key: typed[key] for key in set(ai_keys.values())})
            self.files.update({'assets/ai/ai.viv': data,
                               'fighter-ai.bin': encode_ai_bindings(data, receipt, cores(ai_keys))})
            self.receipts['ai'] = receipt
        if pair_resources:
            source = original('motion/blazin.viv', 'blazin_sha256')
            data, receipt = BlazinPairs(source, pins['blazin_sha256']).compose(pair_resources)
            self.files.update({'motion/blazin.viv': data,
                               'fighter-finishers.bin': encode_pair_bindings(data, receipt, cores(pair_keys), slots=slot_bindings)})
            self.receipts['finishers'] = receipt
        if cinematic_resources:
            source = original('assets/v2ta.viv', 'v2ta_sha256')
            if blazin_resources:
                source, blazin_receipt = BlazinArchive(source, pins['v2ta_sha256']).compose(blazin_resources)
                self.receipts['blazin'] = blazin_receipt
            data, receipt = CinematicArchive(source, digest(source)).compose(cinematic_resources)
            if blazin_resources:
                self.files['fighter-blazin.bin'] = encode_blazin_bindings(
                    data, blazin_receipt, cores(blazin_keys), extension=receipt)
            nis = composed.get('assets/nis.viv')
            if nis is None:
                nis = original('assets/nis.viv', 'nis_sha256')
            nis, table, binding = bind_cinematics(data, receipt, nis, digest(nis), cores(cinematic_keys))
            self.files.update({'assets/v2ta.viv': data, 'assets/nis.viv': nis, 'fighter-cinematics.bin': table})
            for path, pin in (('assets/v2ip.viv', 'v2ip_sha256'), ('assets/entity.xml', 'entities_sha256')):
                self.files[path] = composed[path] if path in composed else original(path, pin)
            self.receipts.update(cinematic=receipt, cinematic_bindings=binding)
        require(sum(map(len, self.files.values())) <= 1024**3, 'Behavior generation exceeds its aggregate output budget')
        self.file_hashes = {path: digest(data) for path, data in self.files.items()}
        self.seal = self.binding_fingerprint()

    def binding_fingerprint(self):
        return fingerprint({'donors': self.donors, 'character_cores': self.character_cores,
                            'voice_ids': self.voice_ids, 'receipts': self.receipts,
                            'files': self.file_hashes, 'sources': self.sources})

    def validate(self, catalog, snapshot):
        require(self.source_sha256 == catalog.source_sha256 and self.snapshot_sha256 == snapshot['sha256'],
                'Behavior plan belongs to a different resolved fighter generation')
        require(self.sources == {key: fingerprint(resource['source']) for key, resource in snapshot['resources'].items()
                                 if resource['kind'] in KINDS and 'source' in resource},
                'Behavior source changed after validation')
        require(self.file_hashes == {path: digest(data) for path, data in self.files.items()},
                'Behavior output changed after composition')
        require(self.seal == self.binding_fingerprint(), 'Behavior bindings changed after composition')
