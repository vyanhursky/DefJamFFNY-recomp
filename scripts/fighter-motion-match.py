"""Save exact offline finisher matches and a complete shared-table witness.

Use the owner's verified game and an explicit local source main_all.dat. This
outputs hashes/mapping evidence only, never accepts a legacy table at runtime.
Per-core data, source animations and native gameplay require separate checks.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'setup'))
from fighter_motion import MotionIndex, MAX_BYTES, require
from fighter_motion_matching import match_finishers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, default=ROOT / 'game')
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--first', type=int, required=True)
    parser.add_argument('--last', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(0 <= args.first <= args.last < 32768 and args.last - args.first < 4096,
            'Invalid source finisher range')
    require(args.source.stat().st_size <= MAX_BYTES, 'Source motion exceeds budget')
    original = args.game / 'motion/main_all.dat'
    pins = json.loads((ROOT / 'config/fighter-native-baseline.json').read_text())
    import hashlib
    data = original.read_bytes()
    require(hashlib.sha256(data).hexdigest() == pins['motion_sha256'], 'Original motion differs from verified dump')
    report = match_finishers(MotionIndex(data), MotionIndex(args.source.read_bytes()),
                             list(range(args.first, args.last + 1)))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open('x', encoding='utf-8') as output:
        output.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'matches': len(report['mapping']), 'shared_prefix_bytes': report['shared_prefix_bytes'],
                      'shared_unaccounted_bytes': report['shared_unaccounted_bytes']}))


if __name__ == '__main__':
    main()
