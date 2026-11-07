"""Offline five-role roundtrip audit against the owner's verified local archive.

Requires explicit source motion directory and matched appearance model/face.
Uses one retail template per participant role to test graph reconstruction only;
this is NOT a behavior mapping, source rig association proof, installed mod or
native playtest. Receipts contain hashes/numbers, never game bytes. Generated
graphs are checked in memory and discarded. Normal shared hand context is the
traced 57-item output with two 32-frame palettes.
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
from fighter_animation_graphs import FullMotionTemplate
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_elf import Model
from fighter_face import FacePalettes, declared_capacities
from fighter_rig import Skeleton


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--face', type=Path, required=True)
    parser.add_argument('--game', type=Path, default=ROOT / 'game')
    parser.add_argument('--template-subject')
    parser.add_argument('--template-counterpart')
    args = parser.parse_args()
    pins = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text())
    raw = (args.game / 'motion/blazin.viv').read_bytes()
    require(digest(raw) == pins['blazin_sha256'], 'Audit requires the verified local animation archive')
    archive = Archive(raw)
    tokens = unpack(archive.read('blazin.mnl'))[8:-1].decode('ascii').split('.')
    model_data, face_data = unpack(args.model.read_bytes()), unpack(args.face.read_bytes())
    rig = Skeleton(Model(model_data))
    face_model = Model(face_data)
    face = FacePalettes(face_model, len(rig.rows), declared_capacities(face_model))
    hand_data = unpack(Archive((args.game / 'assets/misc.viv').read_bytes()).read('share_hp.o'))
    hands = FacePalettes(Model(hand_data), 57, (32, 32))
    compilers = {}
    for role, token in [('A', args.template_subject or tokens[0]), ('B', args.template_counterpart or tokens[1])]:
        require(token in tokens and token.endswith('_' + role), 'Audit template has the wrong participant role')
        envelope = AnimationEnvelope(*(unpack(archive.read(token + '.' + suffix)) for suffix in ('ord', 'orl')),
                                     struct.pack('<2I', 1, 0) + token.encode('ascii') + b'.')
        template = AnimationTemplate(envelope, digest(envelope.model.data), rig.pose_sha256, len(rig.rows))
        compilers[role] = (token, FullMotionTemplate(template, face, hands))
    rows = []
    for path in sorted(args.source.glob('*.ord')):
        row = {'token': path.stem}
        try:
            require(path.stem.endswith(('_A', '_B')), 'Unknown participant suffix')
            token, compiler = compilers[path.stem[-1]]
            data, links = unpack(path.read_bytes()), unpack(path.with_suffix('.orl').read_bytes())
            source = AnimationIndex(AnimationEnvelope(data, links, struct.pack('<2I', 1, 0) + path.stem.encode('ascii') + b'.'))
            compiled, receipt = compiler.convert(source, path.stem, token)
            row.update(passed=True, template_token=token, source_sha256=digest(data + links),
                       compiled_sha256=receipt['sha256'], bytes=len(compiled.model.data),
                       link_bytes=len(compiled.model.data) - compiled.model.sections[2][4])
        except (ValueError, OSError) as error:
            row.update(passed=False, error=str(error))
        rows.append(row)
    require(rows, 'No source animation pairs found')
    summary = {'passed': sum(row['passed'] for row in rows), 'total': len(rows),
               'maximum_link_bytes': max((row['link_bytes'] for row in rows if row['passed']), default=0)}
    report = {'schema': 'fighter-full-graph-audit-1', 'summary': summary,
              'model_sha256': digest(model_data), 'face_sha256': digest(face_data), 'hand_sha256': digest(hand_data),
              'rig_sha256': rig.pose_sha256, 'bone_count': len(rig.rows), 'face_frames': face.frame_counts,
              'hand_frames': hands.frame_counts, 'rows': rows,
              'scope': 'Exact typed five-role roundtrip with one representative appearance; template behavior mapping, other actor joins, unwritten-channel/blend semantics and native playback remain separate gates',
              'runtime_ready': False}
    (ROOT / 'logs/fighter-full-graph-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(summary))
    return 0 if summary['passed'] == summary['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
