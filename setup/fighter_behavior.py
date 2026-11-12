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
from fighter_face import FacePalettes
from fighter_motion_contexts import MotionOutputContexts

TARGETS = {
    'motion': ('motion/main_all.dat', 'fighter-motion.bin'),
    'animation': ('motion/wres_all.viv', 'fighter-animations.bin'),
    'voice': ('audio/speech2.viv', 'fighter-voices.bin'),
    'ai': ('assets/ai/ai.viv', 'fighter-ai.bin'),
    'cinematic': ('assets/v2ta.viv', 'assets/nis.viv', 'assets/v2ip.viv', 'assets/entity.xml', 'fighter-cinematics.bin'),
    'blazin': ('fighter-blazin.bin',),
    'finishers': ('motion/blazin.viv', 'fighter-finishers.bin'),
    'timelines': ('audio/animtags.dat','motion/camera.xml','fighter-timelines.bin'),
    'film_proofs': ('fighter-film-proofs.bin',),
}


def targets(receipts):
    require(type(receipts) is dict and (not {'animation','finishers'} & set(receipts) or 'motion' in receipts)
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
    if 'timelines' in receipts:
        for name,path in (('TAGS','audio/animtags.dat'),('CAMERAS','motion/camera.xml')):
            result['RECOMP_FIGHTER_'+name]=str(ordinary_path(cache/path))
            result['RECOMP_FIGHTER_'+name+'_SHA256']=hashes[path]
        result['RECOMP_FIGHTER_TIMELINE_BINDINGS']=str(ordinary_path(cache/'fighter-timelines.bin'))
    if 'film_proofs' in receipts:result['RECOMP_FIGHTER_FILM_PROOFS']=str(ordinary_path(cache/'fighter-film-proofs.bin'))
    return result


def require(condition, message):
    if not condition:
        raise AssetError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class BehaviorPlan:
    """Internal validated result consumed by the native database compiler."""
    def __init__(self, catalog, snapshot, roots, game, pins, appearances, composed,*,caf=None,ledger=None):
        caf={} if caf is None else caf
        self.snapshot_sha256 = snapshot['sha256']
        self.source_sha256 = catalog.source_sha256
        self.donors, self.character_cores, self.voice_ids = {}, {}, {}
        self.retail_voices={}
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
        global_tag_overrides={};global_tag_owners={}
        for key,resource in snapshot['resources'].items():
            if resource['kind']!='tag-override':continue
            value=typed[key];name=value['target'];replacement={k:value[k] for k in ('original_sha256','template','timeline')}
            require(name not in global_tag_overrides or global_tag_overrides[name]==replacement,
                    'Conflicting animation tag override '+name+' between '+global_tag_owners.get(name,'')+' and '+key)
            global_tag_overrides[name]=replacement;global_tag_owners[name]=key
        added = {key: row['components'] for key, row in snapshot['fighters'].items()
                 if key not in catalog.rows}
        require(added, 'Behavior composition requires an added fighter')
        for key, row in snapshot['fighters'].items():
            require(key not in catalog.rows or not any(value in typed for group, value in row['components'].items()
                                                      if group not in ('stats', 'tier')),
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

        graph_contexts=None
        film_graphs=None;film_hands=None;film_tags={}
        if any(type(source.get('tracks')) is dict and source['tracks'].get('format')=='fighter-cinematic-graph-1'
               or any(type(shot.get('tracks')) is dict for shot in source.get('shots',[]))
               for source in typed.values()):
            from fighter_cinematic_graphs import CinematicGraphs
            film_graphs=CinematicGraphs(original('assets/v2ta.viv','v2ta_sha256'),pins['v2ta_sha256'])
            misc=Archive(original('assets/misc.viv','misc_sha256'))
            film_hands=FacePalettes(Model(unpack(misc.read('share_hp.o'))),57,(32,32))
        if any(source.get('slots') and any(pair.get('profile')=='graph-1' for pair in source['slots'].values())
               for source in typed.values()):
            misc=Archive(original('assets/misc.viv','misc_sha256'))
            hands=FacePalettes(Model(unpack(misc.read('share_hp.o'))),57,(32,32))
            graph_contexts=MotionOutputContexts(hands,pins['shared_hand_sha256'])
            archive=Archive(original('assets/v2ip.viv','v2ip_sha256'))
            for fighter,row in sorted(snapshot['fighters'].items()):
                if 'caf' in row['components']:
                    continue
                appearance_key=row['components']['appearance']
                if appearance_key in appearances:
                    appearance=appearances[appearance_key]
                    body,face=(unpack(appearance.files[appearance.name+suffix]) for suffix in ('.o','_F.o'))
                else:
                    binding=catalog.bindings[appearance_key]
                    name=catalog.rows[binding['donor']]['fields']['Model']['symbol']
                    body,face=(unpack(archive.read(name+suffix)) for suffix in ('.o','_F.o'))
                graph_contexts.add(fighter,body,face,model_sha256=digest(body),face_sha256=digest(face))
            if any('caf' in row['components'] for row in snapshot['fighters'].values()):
                from fighter_caf import output_contexts
                for context, (body, face) in output_contexts(game).items():
                    graph_contexts.add(context, body, face, model_sha256=digest(body), face_sha256=digest(face))

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
            if fighter in caf:
                if not any(components.get(group) in typed for group in ('voice','ai','intro','victory')):
                    continue
                voice=components['voice']
                if voice in typed:
                    if 'retail_donor' in typed[voice]:
                        donor=typed[voice]['retail_donor']
                        require(donor in catalog.rows and 1<=catalog.rows[donor]['native_binding']['core_id']<=86,'CAF voice preset is unavailable')
                        require(caf[fighter].get('voice_donor')==donor,'CAF voice preset differs from voice_donor')
                        self.retail_voices[voice]=donor
                    else:voice_keys[fighter]=voice
                if 'ai' in components:
                    require(components['ai'] in typed,'CAF AI needs a validated source')
                    ai_keys[fighter]=components['ai']
                if 'intro' in components or 'victory' in components:
                    rig=rig_for(components)
                    model=catalog.rows[catalog.bindings[components['appearance']]['donor']]['fields']['Model']['symbol']
                    nis=Archive(original('assets/nis.viv','nis_sha256'))
                    inherited=Cinematics(unpack(nis.read('assets/IntroExtro.xml')),pins['intro_extro_sha256']).inherit(model,model)
                    pair={}
                    for role in ('intro','victory'):
                        ref=components.get(role);source=typed.get(ref)
                        require(ref is None or source is not None and source.get('tracks') is None,'CAF presentation currently selects original sequences')
                        token=source['template'] if source else getattr(inherited,role)
                        require(token.startswith('CI_' if role=='intro' else 'CE_'),'CAF cinematic category differs')
                        internal='@caf-retail/'+fingerprint([token,rig.pose_sha256])
                        cinematic_resources[internal]=dict(template=token,tracks=None,rig_sha256=rig.pose_sha256,bone_count=len(rig.rows))
                        pair[role]=internal
                    cinematic_keys[fighter]=pair
                continue
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
                if 'retail_donor' in typed[voice]:
                    chosen=typed[voice]['retail_donor']
                    require(family==expected_family and chosen in catalog.rows and 1<=catalog.rows[chosen]['native_binding']['core_id']<=86,
                            'Retail voice preset differs from its declared event namespace')
                    self.retail_voices[voice]=chosen
                else:
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
                    choices = dict(typed[resource_key].get('retail_slots', {}))
                    for slot, pair in typed[resource_key]['slots'].items():
                        pair_key = resource_key.split('/')[0] + '/pair-' + fingerprint([resource_key, 'slot', slot])[:32]
                        pair_resources[pair_key] = {'rig_sha256': rig.pose_sha256,
                                                   'bone_count': len(rig.rows), **pair}
                        if pair.get('profile')=='graph-1':
                            require(graph_contexts is not None,'Full graphs require actual output contexts')
                            origin=graph_contexts.contexts[fighter]
                            joins={role:graph_contexts.join(pair[role],fighter,
                                   [fighter] if role=='subject' else sorted(graph_contexts.contexts))
                                   for role in ('subject','counterpart')}
                            pair_resources[pair_key]['graph_contexts']={'face':origin[1],
                                'hands':graph_contexts.hands,
                                'allowed_rigs':{role:sorted({identity['rig_sha256'] for identity in join['targets'].values()})
                                                for role,join in joins.items()}}
                        pair_keys.setdefault(fighter, {})[slot] = pair_key
                        choices[slot] = pair['template_choice']
                    if choices:
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
                if type(tracks) is dict:film_tags[internal]=(source['tags'],'cinematic-'+category+'-1')
                if internal in cinematic_resources:
                    require(cinematic_resources[internal]['rig_sha256'] == rig.pose_sha256,
                            'Shared cinematic is bound to different appearance rigs')
                else:
                    cinematic_resources[internal] = {'template': token, 'tracks': tracks,
                        'rig_sha256': rig.pose_sha256, 'bone_count': len(rig.rows)}
                pair[category] = internal
            cinematic_keys[fighter] = pair

        if motion_resources:
            motion, receipt, table = compose_selected_cores(templates, motion_resources)
            self.files.update({'motion/main_all.dat': motion, 'fighter-motion.bin': table})
            self.receipts['motion'] = receipt
            self.character_cores = {key: row['character_core'] for key, row in receipt['bindings'].items()}

        def cores(mapping):
            from fighter_behavior_identity import caf_key
            return {(caf_key(ledger['fighters'][key]['selection']) if key in caf else self.character_cores[key] - 1): value for key, value in mapping.items()}

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
        tag_additions,camera_additions,timeline_claims={},{},{name:1 for name in global_tag_overrides}
        if pair_resources:
            source = original('motion/blazin.viv', 'blazin_sha256')
            data, receipt = BlazinPairs(source, pins['blazin_sha256']).compose(pair_resources)
            pair_timeline_claims=None
            if any('timelines' in resource for resource in pair_resources.values()):
                from fighter_timelines import TagTimelines,CameraTimelines,encode_timeline_bindings
                tags=TagTimelines(original('audio/animtags.dat','tags_sha256'),pins['tags_sha256'])
                cameras=CameraTimelines(original('motion/camera.xml','camera_sha256'),pins['camera_sha256'])
                for identifier,resource in sorted(pair_resources.items()):
                    if 'timelines' not in resource:continue
                    pair=receipt['bindings'][identifier]
                    for role in ('subject','counterpart'):
                        info=pair['roles'][role];name=info['native_name']
                        tag_additions[name]={'template':info['template'],'timeline':resource['timelines'][role+'_tags']}
                        timeline_claims[name]=1
                    name=pair['roles']['subject']['native_name']
                    camera_additions[name]=resource['timelines']['camera'];timeline_claims[name]=3
                tag_data=tags.compose(tag_additions,overrides=global_tag_overrides);camera_data=cameras.compose(camera_additions)
                table=encode_timeline_bindings(tag_data,camera_data,timeline_claims)
                pair_timeline_claims=timeline_claims
                self.files.update({'audio/animtags.dat':tag_data,'motion/camera.xml':camera_data,'fighter-timelines.bin':table})
                self.receipts['timelines']={'schema':'fighter-event-timelines-1','claims':timeline_claims,
                    'tags_sha256':digest(tag_data),'cameras_sha256':digest(camera_data),'bindings_sha256':digest(table)}
            self.files.update({'motion/blazin.viv': data,
                               'fighter-finishers.bin': encode_pair_bindings(data, receipt, cores(pair_keys), slots=slot_bindings,
                                                                           timeline_claims=pair_timeline_claims)})
            self.receipts['finishers'] = receipt
        if cinematic_resources:
            source = original('assets/v2ta.viv', 'v2ta_sha256')
            if blazin_resources:
                source, blazin_receipt = BlazinArchive(source, pins['v2ta_sha256']).compose(blazin_resources,graphs=film_graphs,hands=film_hands)
                self.receipts['blazin'] = blazin_receipt
            data, receipt = CinematicArchive(source, digest(source)).compose(cinematic_resources,graphs=film_graphs,hands=film_hands)
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
            full_films={}
            for key,info in receipt['bindings'].items():
                if not info.get('full_graph'):continue
                timeline,profile=film_tags[key];name=info['native_name']
                full_films[name]={**info,'tags':int(timeline is not None)};timeline_claims[name]=int(timeline is not None)
                if timeline is not None:tag_additions[name]={'profile':profile,'timeline':timeline}
            if blazin_resources:
                for key,shots in blazin_receipt['bindings'].items():
                    for phase,info in enumerate(shots):
                        if not info.get('full_graph'):continue
                        timeline=blazin_resources[key]['shots'][phase]['tags'];name=info['native_name']
                        full_films[name]={**info,'tags':int(timeline is not None)};timeline_claims[name]=int(timeline is not None)
                        if timeline is not None:tag_additions[name]={'profile':'cinematic-activation-1','timeline':timeline}
            if full_films:
                from fighter_film_proof import encode_film_proofs
                from fighter_timelines import TagTimelines,CameraTimelines,encode_timeline_bindings
                table=encode_film_proofs(data,full_films);self.files['fighter-film-proofs.bin']=table
                self.receipts['film_proofs']={'sha256':digest(table),'members':sum(info['members'] for info in full_films.values())}
                tags=TagTimelines(original('audio/animtags.dat','tags_sha256'),pins['tags_sha256'])
                cameras=CameraTimelines(original('motion/camera.xml','camera_sha256'),pins['camera_sha256'])
                tag_data=tags.compose(tag_additions,overrides=global_tag_overrides) if tag_additions or global_tag_overrides else tags.data
                camera_data=cameras.compose(camera_additions) if camera_additions else cameras.data
                table=encode_timeline_bindings(tag_data,camera_data,timeline_claims)
                self.files.update({'audio/animtags.dat':tag_data,'motion/camera.xml':camera_data,'fighter-timelines.bin':table})
                self.receipts['timelines']={'schema':'fighter-event-timelines-1','claims':timeline_claims,
                    'tags_sha256':digest(tag_data),'cameras_sha256':digest(camera_data),'bindings_sha256':digest(table)}
        if global_tag_overrides:
            from fighter_timelines import TagTimelines,CameraTimelines,encode_timeline_bindings
            tags=TagTimelines(original('audio/animtags.dat','tags_sha256'),pins['tags_sha256'])
            cameras=CameraTimelines(original('motion/camera.xml','camera_sha256'),pins['camera_sha256'])
            tag_data=tags.compose(tag_additions,overrides=global_tag_overrides)
            camera_data=cameras.compose(camera_additions) if camera_additions else cameras.data
            table=encode_timeline_bindings(tag_data,camera_data,timeline_claims)
            self.files.update({'audio/animtags.dat':tag_data,'motion/camera.xml':camera_data,'fighter-timelines.bin':table})
            self.receipts['timelines']={'schema':'fighter-event-timelines-1','claims':timeline_claims,
                'global_overrides':global_tag_owners,'tags_sha256':digest(tag_data),'cameras_sha256':digest(camera_data),'bindings_sha256':digest(table)}
        require(sum(map(len, self.files.values())) <= 1024**3, 'Behavior generation exceeds its aggregate output budget')
        self.file_hashes = {path: digest(data) for path, data in self.files.items()}
        self.seal = self.binding_fingerprint()

    def binding_fingerprint(self):
        return fingerprint({'donors': self.donors, 'character_cores': self.character_cores,
                            'voice_ids': self.voice_ids, 'retail_voices':self.retail_voices, 'receipts': self.receipts,
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
