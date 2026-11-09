"""Rebuild every source cinematic numeric leaf without changing its codec.

An offline conversion audit only. Source control words remain trusted solely
for comparison here; neither this tool nor its receipt admits native resources.
Every quantized seed/delta, constant, destination, time and unused header byte
must survive a freshly emitted leaf, and decoded key poses must be identical.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / 'setup'))
from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_animation_compile import rebuild
from fighter_animation_curves import CurveLayouts
from fighter_animation_graphs import Writer
from fighter_animation_numeric import read_numeric, write_numeric
from fighter_animation_quaternions import QuaternionCurve
from fighter_animation_vectors import VectorCurve
from fighter_archive import Archive
from fighter_assets import unpack
from fighter_registry import fingerprint


def audit_member(data, camera):
    envelope = AnimationEnvelope.from_model(data)
    layout = CurveLayouts(AnimationIndex(envelope))
    model = layout.model
    section = model.sections[1]
    payload = bytearray(model.data[section[4]:section[4]+section[5]])
    pointers = {at: row['target'] for at,row in model.pointers.items()}
    writer = Writer(payload,pointers)
    replacements, values = {}, {}
    for record,info in layout.records.items():
        if info['kind'] not in (18,20,21):
            continue
        value = read_numeric(layout,record)
        control = layout.values(record+2,1)[0]
        replacements[record] = write_numeric(writer,value,control,64 if camera else 1128)
        values[record] = value
    # Redirect graph and bank-table edges; old leaf bytes are inert comparison
    # data, never an alternative execution path or an accepted package input.
    for field,target in list(pointers.items()):
        if target in replacements:
            writer.pointer(field,replacements[target])
    parts = rebuild(model,payload,pointers)
    rebuilt = CurveLayouts(AnimationIndex(AnimationEnvelope(*parts)))
    checks = 0
    types = Counter()
    for record,value in values.items():
        other = replacements[record]
        require(read_numeric(rebuilt,other) == value,'Rebuilt typed numeric leaf differs')
        types[value['kind']] += 1
        codec = QuaternionCurve if value['kind'] == 18 else VectorCurve
        before,after = codec(layout,record),codec(rebuilt,other)
        require(before.destinations == after.destinations,'Rebuilt destinations differ')
        for key in range(value['keys']):
            require(before.pose(key) == after.pose(key),'Rebuilt numeric pose differs')
            checks += 1
        for time in (0,.25,1,2.5,value['keys']-.5,65535):
            require(before.sample(time) == after.sample(time),'Rebuilt interpolated pose differs')
            checks += 1
    return {'source_sha256':hashlib.sha256(data).hexdigest(),
            'canonical_sha256':hashlib.sha256(model.data).hexdigest(),
            'rebuilt_sha256':hashlib.sha256(b''.join(parts)).hexdigest(),
            'typed_sha256':fingerprint(list(values.values())),
            'leaves':len(values),'types':dict(types),'pose_checks':checks,
            'output_bytes':256 if camera else 4512}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    require(not args.out.exists(),'Choose a new numeric audit report')
    bundles = sorted(p for p in (args.source / 'assets/v2ta').glob('*.viv')
                     if p.name.startswith(('CI_','CE_','BZ_','BY_')))
    require(0 < len(bundles) <= 4096,'Cinematic bundle population exceeds audit budget')
    results,types = [],Counter()
    for path in bundles:
        archive = Archive(path.read_bytes())
        for entry in archive.entries:
            if not entry.name.endswith('.o'):
                continue
            row = audit_member(unpack(archive.read(entry.name)),
                               '_EYE' in entry.name or '_TARGET' in entry.name)
            row.update(file=path.relative_to(args.source).as_posix()+'::'+entry.name)
            results.append(row)
            types.update(row['types'])
        print(path.name,flush=True)
    summary = {'bundles':len(bundles),'members':len(results),
               'numeric_leaves':sum(r['leaves'] for r in results),
               'types':dict(types),'pose_checks':sum(r['pose_checks'] for r in results)}
    report = {'schema':'fighter-cinematic-numeric-audit-1','summary':summary,'results':results,
              'package_admission':False,'native_playtest':False,
              'camera_scheduling_validated':False,'created_output_context_validated':False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with args.out.open('x',encoding='utf-8') as output:
        output.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
