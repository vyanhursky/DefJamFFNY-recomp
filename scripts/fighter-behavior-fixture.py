#!/usr/bin/env python3
"""Create ordinary data-only manifests for the local M2 acceptance fixtures.

Requires the reviewed appearance-alpha/beta folders in logs/fighter-appearance-packs
and the player's verified game junction. Writes JSON quaternion files and synthetic
PCM WAV tones alongside those local appearances; no native tables or code enter
the manifests. Use fighter-runtime-probe.py with the emitted behavior-full.json
paths. This synthetic rig exercise is a diagnostic, not finished fighter artwork.
"""
import hashlib
import argparse
import importlib.util
import io
import json
import math
from pathlib import Path
import struct
import sys
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_animation import AnimationEnvelope, AnimationIndex
from fighter_cinematic_compile import envelope
from fighter_elf import Model
from fighter_rig import Skeleton
from fighter_voice_bank import VoiceBankTemplate
from fighter_voice_compile import CATEGORIES
from mods import ordinary_path


def track(rig, bank, token, amplitude):
    parent = bank.records[bank.lookup[token + '_s']]
    at = bank.model.data_range(parent, 12)
    duration = struct.unpack_from('<H', bank.model.data, at + 10)[0]
    arm = rig.bones['__Bone:::root.L_arm1']
    poses = []
    for tick in range(duration + 1):
        values = [list(row[4:8]) for row in rig.rows]
        angle = amplitude * math.sin(2 * math.pi * tick / max(1, duration))
        s, c = math.sin(angle / 2), math.cos(angle / 2)
        x, y, z, w = values[arm]
        values[arm] = [x*c + w*s, y*c + z*s, z*c - y*s, w*c - x*s]
        poses.append(values)
    return {'schema': 'fighter-quaternions-1', 'rig_sha256': rig.pose_sha256,
            'bone_count': len(rig.rows), 'poses': poses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blazin', action='store_true', help='Include four typed activation shots per fighter')
    parser.add_argument('--finishers', action='store_true', help='Also author both roles of the inherited finisher')
    args = parser.parse_args()
    args.blazin = args.blazin or args.finishers
    pins = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text(encoding='utf-8'))
    def original(path, pin):
        data = (ROOT / 'game' / path).read_bytes()
        if hashlib.sha256(data).hexdigest() != pins[pin]:
            raise ValueError('Fixture original differs: ' + path)
        return data
    animation = Archive(original('motion/wres_all.viv', 'animation_sha256'))
    cinematic = Archive(original('assets/v2ta.viv', 'v2ta_sha256'))
    voice = Archive(original('audio/speech2.viv', 'speech_sha256'), native_separators=True)
    paired = Archive(original('motion/blazin.viv', 'blazin_sha256')) if args.finishers else None
    spec = importlib.util.spec_from_file_location('registry_fixture', ROOT / 'scripts/fighter-registry.py')
    registry = importlib.util.module_from_spec(spec); spec.loader.exec_module(registry)
    catalog = registry.retail_catalog(ROOT / 'game/assets/djv2.sod')
    donor = catalog.rows['retail/blaze']
    bank_number, voice_number = donor['native_binding']['core_id'], donor['fields']['SpeechId']['word']
    bank = AnimationIndex(AnimationEnvelope(*(unpack(animation.read(f'wres{bank_number:03d}.' + suffix))
                                             for suffix in ('ord', 'orl', 'mnl'))))
    for ordinal, owner in enumerate(('appearance-alpha', 'appearance-beta')):
        folder = ordinary_path(ROOT / 'logs/fighter-appearance-packs' / owner)
        pack = json.loads((folder / 'four-portraits-matched.json').read_text(encoding='utf-8'))
        rig = Skeleton(Model(unpack((folder / 'model.bin').read_bytes())))
        def write(name, data):
            ordinary_path(folder / name).write_bytes(data)
            return {'path': name, 'sha256': hashlib.sha256(data).hexdigest()}
        def json_file(name, value):
            return write(name, json.dumps(value, separators=(',', ':'), allow_nan=False).encode())
        def resource(name, kind, source):
            compatibility = {} if kind == 'ai' else {'events': 'retail/binding-blaze'}
            if kind in ('moveset', 'cinematic', 'blazin'):
                compatibility['skeleton'] = 'retail/binding-blaze'
            pack['resources'].append({'id': name, 'kind': kind, 'compatibility': compatibility, 'source': source})
            return owner + '/' + name
        tracks = {token: json_file('behavior-' + token + '.json', track(rig, bank, token, .2 + .1*ordinal))
                  for token in (*bank.envelope.tokens[:10], *bank.envelope.tokens[67:86])}
        moveset = resource('moves', 'moveset', {'format': 'fighter-moveset-1', 'donor': 'retail/blaze',
            'selections': {'6': 5, '54': 55} if ordinal == 0 else {'5': 6, '56': 54}, 'tracks': tracks})
        for index, fighter in enumerate(pack['fighters']):
            number = ordinal*2 + index
            local = fighter['id']
            rate, count, frequency = 24000, 4800, 997 + 502*number
            values = [int(2500*math.sin(2*math.pi*frequency*i/rate)*min(1, i/240, (count-1-i)/240))
                      for i in range(count)]
            output = io.BytesIO()
            with wave.open(output, 'wb') as audio:
                audio.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
                audio.writeframes(struct.pack('<' + 'h'*count, *values))
            sample = write('behavior-' + local + '.wav', output.getvalue())
            samples = {}
            family = 'Def_Jam_IP_Characters' if voice_number >= 500 else 'Def_Jam_Characters'
            for category in CATEGORIES:
                stem = f'speech/{category}/{family}/{voice_number:03d}'
                header, data = voice.read(stem + '.hdr'), voice.read(stem + '.dat')
                VoiceBankTemplate(header, data, hashlib.sha256(header).hexdigest(), hashlib.sha256(data).hexdigest())
                samples[category] = {str(i): sample for i in range(header[5])}
            components = fighter['components']
            components['moveset'] = moveset
            components['voice'] = resource(local + '-voice', 'voice', {'format': 'fighter-voice-1',
                'template_voice': voice_number, 'samples': samples, 'intro': sample, 'extro': sample})
            components['ai'] = resource(local + '-ai', 'ai', {'format': 'fighter-ai-1',
                'template_profile': f'char{bank_number:04d}', 'tendencies': {
                    d: {str(slot): {'Attack_versus_Defend': number+1, 'Blazin_Frequency': 5}
                        for slot in range(4)} for d in ('easy', 'normal', 'hard')}})
            for category, token in (('intro', 'CI_113A'), ('victory', 'CE_113A')):
                nested = Archive(unpack(cinematic.read(token + '.viv')))
                clips = AnimationIndex(envelope(unpack(nested.read(token + '.o')), token))
                pose = json_file('behavior-' + local + '-' + category + '.json', track(rig, clips, token, .35 + .15*number))
                components[category] = resource(local + '-' + category, 'cinematic', {
                    'format': 'fighter-cinematic-1', 'template': token, 'track': pose})
            if args.blazin:
                shots = []
                for phase, token in enumerate(('BT1_01', 'BT2_01', 'BT3_01', 'BT4C01')):
                    nested = Archive(unpack(cinematic.read(token + '.viv')))
                    clips = AnimationIndex(envelope(unpack(nested.read(token + '.o')), token))
                    pose = json_file(f'behavior-{local}-blazin-{phase}.json',
                                     track(rig, clips, token, .35 + .15*number))
                    shots.append({'template': token, 'track': pose})
                source = {'format': 'fighter-blazin-1', 'shots': shots}
                if paired is not None:
                    names = unpack(paired.read('blazin.mnl'))[8:-1].decode('ascii').split('.')
                    roles = {}
                    for role, choice in (('subject', 4), ('counterpart', 5)):
                        token = names[choice]
                        clips = AnimationIndex(AnimationEnvelope(*(unpack(paired.read(token + '.' + suffix))
                            for suffix in ('ord', 'orl')), struct.pack('<II', 1, 0) + token.encode('ascii') + b'.'))
                        roles[role] = json_file(f'behavior-{local}-finisher-{role}.json',
                            track(rig, clips, token, .2 + .1*number))
                    source['pairs'] = {'2': roles}
                components['blazin'] = resource(local + '-blazin', 'blazin', source)
        path = ordinary_path(folder / ('behavior-full-finishers.json' if args.finishers else
            'behavior-full-blazin.json' if args.blazin else 'behavior-full.json'))
        path.write_text(json.dumps(pack, indent=2), encoding='utf-8')
        print(path)


if __name__ == '__main__':
    main()
