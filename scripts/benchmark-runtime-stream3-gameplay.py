#!/usr/bin/env python3
"""Serial seeded fight/FFA CPU trials, using real fight-step telemetry.

Requires a local hashed save fixture. Each route gets a separate persistent
data/save root under logs/stream3/LABEL. No captures or player settings change.
CPU is measured during steps 601..2401 (approximately 10..40 seconds), not
menus/loading. Early match endings and missing telemetry invalidate a trial.
Frame rows use the same requested step interval. Log polling can shift CPU
boundaries by a telemetry-report interval; actual steps/duration are retained.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import time
from runtime_benchmark_affinity import affinity_mask, apply_owned_affinity

ROOT = Path(__file__).resolve().parents[1]
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
benchmark = load('stream3_gameplay_scene', 'benchmark-runtime-stream2.py')
suite = load('stream3_gameplay_suite', 'scenario_suite.py')
harness = benchmark.harness

class FightWindow:
    def __init__(self, start=601, end=2401, affinity=None):
        self.start, self.end = start, end
        self.pos, self.pending = 0, b''
        self.step = -1
        self.reason = None
        self.events = Counter()
        self.fighters = []
        self.samples, self.interference = [], []
        self.last_inventory = self.last_sample = -10.0
        self.affinity_mask, self.affinity = affinity, None

    def consume(self, data):
        lines = (self.pending + data).split(b'\n')
        self.pending = lines.pop()
        for line in lines:
            if b'[CRASH]' in line:
                self.reason = 'crash'
            if not line.startswith((b'[TEST-STATE] ', b'[TEST-EVENT] ')):
                continue
            try:
                event = json.loads(line.split(b'] ', 1)[1])
            except (ValueError, IndexError):
                continue
            if event.get('match') != 1:
                continue
            self.step = max(self.step, event.get('step', -1))
            self.events[event.get('event')] += 1
            if event.get('event') == 'match_start':
                self.fighters = event.get('fighters', [])
            if event.get('event') in ('match_over', 'result') and self.step < self.end:
                self.reason = 'fight ended before measurement completed'

    def poll(self, tail, elapsed):
        if self.affinity_mask is not None and self.affinity is None:
            self.affinity = apply_owned_affinity(harness,self.affinity_mask)
        now = time.monotonic()
        if now - self.last_inventory >= 2:
            self.last_inventory = now
            self.interference = benchmark.competing_workloads()
            if self.interference:
                self.reason = 'competing workload'
        with open(tail.path, 'rb') as stream:
            stream.seek(self.pos)
            data = stream.read()
        self.pos += len(data)
        self.consume(data)
        if self.reason:
            return True
        if self.step >= self.start and (now - self.last_sample >= 0.5 or self.step >= self.end):
            owned = [p for p in harness._OWNED_PROCESSES if p.poll() is None]
            if len(owned) != 1:
                raise RuntimeError('CPU sampling requires exactly one owned game')
            value = benchmark.cpu_seconds(owned[0].pid)
            if value is not None:
                self.samples.append(dict(wall_s=now, process_cpu_s=value, pid=owned[0].pid, step=self.step))
            self.last_sample = now
        if self.step >= self.end:
            self.reason = 'complete'
            return True
        return False

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--routes', nargs='+', choices=['fight', 'ffa'], default=['fight', 'ffa'])
    parser.add_argument('--hle', type=int, choices=[0], default=0)
    parser.add_argument('--bulk', type=int, choices=range(4), default=0)
    parser.add_argument('--affinity', type=affinity_mask, help='optional Windows child-only CPU mask')
    parser.add_argument('--env', action='append', default=[])
    args = parser.parse_args()
    if not args.label.replace('-', '').replace('_', '').isalnum():
        parser.error('label must be a simple directory name')
    fixture = suite.evidence.fixture_identity(args.fixture)
    out = ROOT / 'logs/stream3' / args.label
    out.mkdir(parents=True, exist_ok=False)
    shared_data = Path(harness.data_dir()).resolve()
    step_input = Path(suite.step_input(out / 'step-input.txt', seconds=60)).resolve()
    base_env = dict(benchmark.scene.PROFILES['stress'], RECOMP_RECORD='1', RECOMP_RECORD_FPS='0',
        RECOMP_TEST_OBSERVATIONS='1', RECOMP_TEST_RNG_SEED='20261006', RECOMP_TEST_INPUT=str(step_input),
        RECOMP_D3D_HLE=str(args.hle), RECOMP_D3D_HLE_BULK=str(args.bulk), RECOMP_D3D_HLE_STATS='0',
        RECOMP_PRESENT_PACING='0', RECOMP_STREAM2_STATS='0', RECOMP_FENCE_WAIT='0', RECOMP_FENCE_HOLD='1',
        RECOMP_D3D11_STATE_CACHE='1', RECOMP_D3D11_SHADER_CACHE='1',
        RECOMP_D3D11_SHADER_CACHE_DIR=str(shared_data / 'cache/d3d11'),
        RECOMP_SHADER_CACHE=str(shared_data / 'cache/vulkan'))
    for item in args.env:
        key, sep, value = item.partition('=')
        if not sep or not key.startswith('RECOMP_'):
            parser.error('--env requires RECOMP_NAME=VALUE')
        base_env[key] = value
    results = []
    bb = benchmark.scene.load('bug-bundle')
    for route in args.routes:
        if benchmark.competing_workloads():
            raise SystemExit('Competing game/build: gameplay trial refused')
        runtime = out / route / 'runtime'
        shutil.copytree(args.fixture / 'save', runtime / 'save')
        monitor = FightWindow(affinity=args.affinity)
        env = dict(base_env, DEFJAM_DATA=str(runtime.resolve()))
        run = harness.run_game('stream3-' + route, stages=suite.bootstrap_stages(route),
            secs=harness.ROUTES[route]['secs'], shots='', preset=harness.RELEASE_PRESET,
            env=env, quiet=True, controller=monitor, inherit_recomp=False)
        session = benchmark.scene.keep_session(benchmark.scene.session_of(run.log), out / route / 'session', route, False)
        faults = harness.run_faults(run)
        expected_fighters = 4 if route == 'ffa' else 2
        effective = run.identity['environment']
        wrong_flags = [key for key,value in base_env.items() if effective.get(key) != value]
        row = dict(route=route, identity=run.identity, log=os.path.relpath(run.log, ROOT),
            reason=monitor.reason, samples=monitor.samples, events=dict(monitor.events), fighters=monitor.fighters,
            fixture=fixture, input_sha256=hashlib.sha256(step_input.read_bytes()).hexdigest(),
            affinity=monitor.affinity,
            save_ok=run.save_ok, faults=faults, interference=monitor.interference, wrong_flags=wrong_flags)
        if len(monitor.samples) >= 2:
            first,last = monitor.samples[0],monitor.samples[-1]
            wall = last['wall_s'] - first['wall_s']
            row['cpu'] = dict(window_s=wall, first_step=first['step'], last_step=last['step'],
                percent_one_core=100 * (last['process_cpu_s']-first['process_cpu_s']) / wall)
        if session:
            frames = [r for r in bb.read_rows(session / 'frames.csv') if monitor.start <= r.get('step', -1) <= monitor.end]
            row['frames'] = bb.frame_stats(frames)
            if frames:
                row['audio_dry'] = max(r['audio_dry'] for r in frames)-min(r['audio_dry'] for r in frames)
        results.append(row)
        (out / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(route, row.get('cpu'), 'p99',row.get('frames',{}).get('p99_ms'), 'events',row['events'],flush=True)
        valid = (monitor.reason=='complete' and not faults and run.save_ok and not wrong_flags and
                 not monitor.interference and len(monitor.fighters)==expected_fighters and
                 monitor.events['attack'] and monitor.events['damage'] and monitor.events['movement'] and
                 row.get('frames',{}).get('frames',0)>=100)
        if (os.name=='nt' or Path('/proc').is_dir()) and len(monitor.samples)<2:
            valid = False
        if 'cpu' in row and (row['cpu']['window_s'] < 20 or len(monitor.samples) < 20 or
                             monitor.samples[-1]['step']-monitor.samples[0]['step'] < 1500):
            valid = False
        if not valid:
            raise SystemExit('Invalid gameplay trial; inspect results.json and triage the run')

if __name__ == '__main__':
    main()
