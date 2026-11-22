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
import tempfile
import struct
import hashlib
from PIL import Image

import harness


def analyse_photo(stream, context):
    records, poses = [], set()
    active = False
    steps_during = steps_after = 0
    module = flags = exit_flags = scale = exit_scale = origin_paused = entry_state = None
    return_context_changed = False
    for line in stream:
        if '[PHOTO]' in line:
            records.append(line.strip())
        if '[PHOTO] enter ' in line:
            active = True
            m = re.search(r' state=(\d+)', line)
            entry_state = int(m[1]) if m else None
            m = re.search(r' module=(\d+)', line)
            module = int(m[1]) if m else None
            m = re.search(r' flags=([0-9A-Fa-f]+)', line)
            flags = int(m[1], 16) if m else None
            m = re.search(r' scale=([-\d.]+)', line)
            scale = float(m[1]) if m else None
            m = re.search(r' origin_paused=(\d+)', line)
            origin_paused = int(m[1]) if m else None
        if '[PHOTO] exit ' in line:
            active = False
            m = re.search(r' flags=([0-9A-Fa-f]+)', line)
            exit_flags = int(m[1], 16) if m else None
            m = re.search(r' scale=([-\d.]+)', line)
            exit_scale = float(m[1]) if m else None
        if '[PHOTO] draw=' in line:
            m = re.search(r' pos=([^\s]+)', line)
            if m:
                poses.add(m[1])
        if '[PHOTO] context ' in line and any('[PHOTO] exit ' in r for r in records):
            m = re.search(r' state=(\d+)', line)
            if m and entry_state is not None and int(m[1]) != entry_state:
                return_context_changed = True
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
        entry_flags=flags, exit_flags=exit_flags, entry_scale=scale, exit_scale=exit_scale,
        origin_paused=origin_paused, entry_state=entry_state, return_context_changed=return_context_changed)
    result['passed'] = result['entered'] and result['exited'] and result['camera_samples'] >= 3 \
        and result['camera_moved'] and not result['state_changed'] and not steps_during \
        and (steps_after == 0 if context == 'paused' else
             (steps_after > 0 or return_context_changed) if context == 'victory' else steps_after > 0) \
        and (origin_paused == 1 and exit_scale == scale if context == 'paused' else True)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('context', choices=['live', 'paused', 'entrance', 'controller', 'controller-paused',
                                       'reject-menu', 'reject-cutscene'])
    ap.add_argument('--expect-save-failure', action='store_true')
    args = ap.parse_args()
    data = Path(os.environ.get('DEFJAM_DATA', '')).resolve()
    expected = Path(harness.REPO) / 'logs/runtime-data'
    if data != expected.resolve():
        ap.error('set DEFJAM_DATA to this checkout\'s logs/runtime-data')
    stages = harness.ONE_ON_ONE_SETUP[:7] + [
        'getscreeninfo(battle/choosef2=right@5;a@8;left@12;a@15;a@20+3x8',
        'getscreeninfo(battle/chsvenue=a@5+3x8']
    tail = harness.FIGHT_TAIL
    expected_pause = args.context in ('paused', 'controller-paused')
    negative = args.context.startswith('reject-')
    virtual = args.context.startswith('controller') or negative
    if expected_pause:
        tail = '@game.startgame(,start:18:18.3'
    env = {'RECOMP_PHOTO_TEST': args.context, 'RECOMP_TEST_OBSERVATIONS': '1',
           'RECOMP_TRANS_SHOT_NATIVE': '1', 'RECOMP_ASPECT': '16:9', 'RECOMP_PHOTO_TRACE': '1'}
    if virtual:
        tail = '@game.startgame(,' + ('start:18:18.3,' if expected_pause else '') + \
            'rs:20:20.8,down:20:20.8,lright:21:21.8,rright:22:22.25,rt:23:23.2,' \
            'white:23.3:23.6,a:24:24.15,x:25:25.15,a:26:26.15,y:27:27.15,' \
            'down:27.3:27.45,right:27.7:27.85,down:28.1:28.25,right:28.5:28.65,' \
            'down:28.9:29.05,right:29.3:29.45,down:29.7:29.85,right:30.1:30.25,' \
            'down:30.5:30.65,right:30.9:31.05,down:31.3:31.45,right:31.7:31.85,' \
            'down:32.1:32.25,right:32.5:32.65,down:32.9:33.05,a:33.3:33.45,' \
            'b:34:34.15,a:35:35.15,b:37:37.2'
        env.update(RECOMP_PHOTO_MODE='1', RECOMP_INPUT_HOST='1', RECOMP_INPUT_IGNORE_FOCUS='1',
            RECOMP_PAD_HOST='1', RECOMP_INPUT_NO_PADS='1', RECOMP_INPUT_VIRTUAL_PADS='1',
            RECOMP_PAD_SCRIPT_VIRTUAL='1')
    if negative:
        stages = []
        anchor = 'sc05.viv#1' if args.context == 'reject-cutscene' else 'getscreeninfo(intmain/mainmenu'
        tail = '@' + anchor + ',rs:4:4.9,down:4:4.9,rs:10:10.9,down:10:10.9'
        if args.context == 'reject-cutscene':
            env['RECOMP_SCENE'] = 'sc05'
    outputs = Path(harness.REPO) / 'logs/photo-output'
    outputs.mkdir(exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix=args.context + '-', dir=outputs))
    env['RECOMP_PHOTO_DIR'] = str(output)
    if args.expect_save_failure:
        invalid = output / 'not-a-directory'
        invalid.write_text('photo failure fixture', encoding='utf-8')
        env['RECOMP_PHOTO_DIR'] = str(invalid)
    live_file = Path(harness.REPO) / 'logs/photo-probe-live-input.txt'
    live_file.write_text('', encoding='utf-8')
    env['RECOMP_PAD_LIVE'] = str(live_file)
    run = harness.run_game('photo-' + args.context, stages=stages, tail=tail,
        shots=('@' + anchor + ',6,12' if negative else '@game.startgame(,10,12,14,16,19,21,23,25,28,33,36,39'),
        secs=150 if negative else 420, until=None if negative else 'game.startgame(',
        after=40, env=env,
        until_file=str(Path(harness.REPO) / 'logs/shots' / ('photo-' + args.context) /
                       ('photo-' + args.context + '-12s.bmp')) if negative else None)
    # Read the bounded PHOTO records; leave the large raw log to triage.py.
    log = Path(run.log)
    with log.open(encoding='utf-8', errors='replace') as stream:
        receipt = dict(context=args.context, log=str(log), **analyse_photo(stream, 'paused' if expected_pause else args.context))
    receipt['save_restored'] = run.save_ok is True
    receipt['runtime_clean'] = not any(run.summary[k] for k in
        ('crashes', 'watchdogs', 'debug_layer', 'icall_failures', 'icall_noncode', 'truncated', 'unimplemented')) \
        and not run.hung and not run.unexpected_exit and not run.missing_anchor
    receipt['passed'] = receipt['passed'] and receipt['save_restored'] and receipt['runtime_clean']
    photos = []
    for path in sorted(output.glob('*.png')):
        data = path.read_bytes()
        valid = len(data) > 32 and data[:8] == b'\x89PNG\r\n\x1a\n'
        width, height = struct.unpack('>II', data[16:24]) if valid else (0, 0)
        if valid:
            try:
                with Image.open(path) as photo:
                    photo.load()
                    valid = photo.size == (width, height) and any(lo != hi for lo, hi in photo.convert('RGB').getextrema())
            except (OSError, ValueError):
                valid = False
        photos.append(dict(path=str(path), width=width, height=height, valid=valid,
                           sha256=hashlib.sha256(data).hexdigest()))
    receipt['photos'] = photos
    if negative:
        receipt['rejection_passed'] = not receipt['entered'] and '[PAD] script: rs sampled' in run.text \
            and ('[SCENE] playing sc05 ' in run.text if args.context == 'reject-cutscene' else 'getscreeninfo(intmain/mainmenu' in run.text.lower())
        receipt['passed'] = receipt['rejection_passed'] and receipt['save_restored'] and receipt['runtime_clean'] and not photos
    elif virtual:
        if args.expect_save_failure:
            receipt['capture_passed'] = '[PHOTO] save failed:' in run.text and not photos
        else:
            # First two photos use the same pose with the help panel shown/hidden.
            # The third follows reset, with HUD/guides enabled in the preview.
            receipt['capture_passed'] = len(photos) == 3 and all(p['valid'] and p['width'] > p['height'] > 0 for p in photos) \
                and photos[0]['sha256'] == photos[1]['sha256'] != photos[2]['sha256']
        receipt['controls_passed'] = all(any('[PHOTO] setting row=' + str(row) + ' ' in r for r in receipt['records'])
                                         for row in range(1, 8)) \
            and any('[PHOTO] reset ' in r for r in receipt['records'])
        receipt['passed'] = receipt['passed'] and receipt['capture_passed'] and receipt['controls_passed']
    out = Path(harness.REPO) / ('logs/photo-' + args.context + '.json')
    out.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))
    return 0 if receipt['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
