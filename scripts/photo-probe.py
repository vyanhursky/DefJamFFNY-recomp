#!/usr/bin/env python3
"""Run the Photo Mode freeze/camera proof on an isolated, guarded save root.

DEFJAM_DATA must refer to this checkout's disposable runtime-data directory.
Captures and the JSON receipt stay under ignored logs/. Never commit game images.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

import harness


def analyse_photo(stream, context):
    records, poses = [], set()
    active = False
    steps_during = steps_after = 0
    module = flags = exit_flags = None
    for line in stream:
        if '[PHOTO]' in line:
            records.append(line.strip())
        if '[PHOTO] enter ' in line:
            active = True
            m = re.search(r' module=(\d+)', line)
            module = int(m[1]) if m else None
            m = re.search(r' flags=([0-9A-Fa-f]+)', line)
            flags = int(m[1], 16) if m else None
        if '[PHOTO] exit ' in line:
            active = False
            m = re.search(r' flags=([0-9A-Fa-f]+)', line)
            exit_flags = int(m[1], 16) if m else None
        if '[PHOTO] draw=' in line:
            m = re.search(r' pos=([^\s]+)', line)
            if m:
                poses.add(m[1])
        if '[TEST-STATE]' in line:
            if active:
                steps_during += 1
            elif any('[PHOTO] exit ' in record for record in records):
                steps_after += 1
    result = dict(records=records, entered=any('[PHOTO] enter ' in r for r in records),
        exited=any('[PHOTO] exit ' in r for r in records),
        camera_samples=sum('[PHOTO] draw=' in r for r in records),
        camera_moved=len(poses) > 1,
        state_changed=any('frozen=NO' in r for r in records),
        steps_during=steps_during, steps_after=steps_after, entry_module=module,
        entry_flags=flags, exit_flags=exit_flags)
    result['passed'] = result['entered'] and result['exited'] and result['camera_samples'] >= 3 \
        and result['camera_moved'] and not result['state_changed'] and not steps_during \
        and (steps_after == 0 if context == 'paused' else steps_after > 0) \
        and (flags is not None and flags & 0x40 and exit_flags == flags if context == 'paused' else True)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('context', choices=['live', 'paused', 'entrance', 'victory'])
    args = ap.parse_args()
    data = Path(os.environ.get('DEFJAM_DATA', '')).resolve()
    expected = Path(harness.REPO) / 'logs/runtime-data'
    if data != expected.resolve():
        ap.error('set DEFJAM_DATA to this checkout\'s logs/runtime-data')
    route = harness.ROUTES['fight']
    tail = harness.FIGHT_TAIL
    if args.context == 'paused':
        tail = '@game.startgame(,start:18:18.3'
    run = harness.run_game('photo-' + args.context, stages=route['stages'], tail=tail,
        shots='@game.startgame(,10,12,14,16,19,21,23,25,28', secs=420,
        until='game.startgame(', after=40,
        env={'RECOMP_PHOTO_TEST': args.context, 'RECOMP_TEST_OBSERVATIONS': '1',
             'RECOMP_TRANS_SHOT_NATIVE': '1', 'RECOMP_ASPECT': '16:9'})
    # Read the bounded PHOTO records; leave the large raw log to triage.py.
    log = Path(run.log)
    with log.open(encoding='utf-8', errors='replace') as stream:
        receipt = dict(context=args.context, log=str(log), **analyse_photo(stream, args.context))
    receipt['save_restored'] = run.save_ok is True
    receipt['runtime_clean'] = not any(run.summary[k] for k in
        ('crashes', 'watchdogs', 'debug_layer', 'icall_failures', 'unimplemented')) \
        and not run.hung and not run.unexpected_exit and not run.missing_anchor
    receipt['passed'] = receipt['passed'] and receipt['save_restored'] and receipt['runtime_clean']
    out = Path(harness.REPO) / ('logs/photo-' + args.context + '.json')
    out.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
