#!/usr/bin/env python3
"""Compare default-off Stream 3 submissions/bulk decoding using the scene runner.

Examples (run serially, fresh labels, identical settings in both arms):
  python scripts/benchmark-runtime-stream3.py --label s3-control
  python scripts/benchmark-runtime-stream3.py --label s3-bulk --bulk 3

Other options, including --scenes and --env, pass to the existing Stream 2
runner. Fence waits remain off unless explicitly requested there. For a CPU
comparison on top of Stream 2, use the same explicit cache/fence flags in every
arm. Output stays under logs/stream2/LABEL with effective flags and identities.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
from runtime_benchmark_affinity import affinity_mask, apply_owned_affinity

def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--hle', type=int, choices=[0], default=0)
    parser.add_argument('--bulk', type=int, choices=range(4), default=0)
    parser.add_argument('--stats', action='store_true')
    parser.add_argument('--affinity', type=affinity_mask, help='optional Windows child-only CPU mask; identical in both arms')
    args, forwarded = parser.parse_known_args()
    metadata = argparse.ArgumentParser(add_help=False)
    metadata.add_argument('--label')
    label = metadata.parse_known_args(forwarded)[0].label
    filename = Path(__file__).with_name('benchmark-runtime-stream2.py')
    spec = importlib.util.spec_from_file_location('stream3_scene_runner', filename)
    benchmark = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(benchmark)
    applied = {}
    if args.affinity is not None:
        original = benchmark.MeasuredScene
        class AffinityScene(original):
            affinity_done = False
            def poll(self, tail, elapsed):
                if not self.affinity_done:
                    record = apply_owned_affinity(benchmark.harness,args.affinity)
                    applied[record['pid']] = record
                    self.affinity_done = True
                return super().poll(tail,elapsed)
        benchmark.MeasuredScene = AffinityScene
    sys.argv = [str(filename), '--env', f'RECOMP_D3D_HLE={args.hle}',
                '--env', f'RECOMP_D3D_HLE_BULK={args.bulk}',
                '--env', f'RECOMP_D3D_HLE_STATS={int(args.stats)}', *forwarded]
    if args.affinity is not None:
        sys.argv[1:1] = ['--env',f'RECOMP_BENCH_AFFINITY={hex(args.affinity)}']
    try:
        benchmark.main()
    finally:
        if args.affinity is not None and label is not None:
            if label.replace('-','').replace('_','').isalnum():
                folder = benchmark.ROOT / 'logs/stream2' / label
                if folder.exists():
                    (folder/'affinity.json').write_text(json.dumps(applied,indent=2),encoding='utf-8')

if __name__ == '__main__':
    main()
