#!/usr/bin/env python3
"""Does a match with a custom fighter play the same every time, and on every PC?

Runs the seed-pinned, step-timed fight of `regress.py --only replay` (scenario_suite's
--step-input default, --rng-seed 20261006, --observe-combat) but picks the fighters
through the menu, so a custom fighter can play. Each --data folder is a data root with
fighter packs installed and enabled (for example by `setup/mods.py`, docs/mod-manager.md)
and a save whose first-time hints have been seen: a fresh save stops the fight at the
first tutorial hint, which the step-timed input cannot dismiss. Every run records the
first --steps fight steps of game state (positions, health, buttons, events) and the runs
are compared record for record.

    python scripts/fighter-replay-check.py --data D:/one --data "D:/two" --runs 2 --isolate-crowd

--isolate-crowd also pins the base game's time-seeded generators (issue #98,
docs/research/deck-determinism-98.md). Without it, the CPU opponent's choices can follow
host timing on any fighter, retail or custom; with it, a difference is ours to explain.

Game runs are serial: this refuses to start while another game process is running.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
# The second custom tile with unlock-everything on; pass --pick for another fighter.
DEFAULT_PICK = 'getscreeninfo(battle/choosef2=down@10+1.2x12;right@26+1.2x5;a@35;a@40'
DEFAULT_CPU = 'controllersetup(0=right@4;a@7'
DEFAULT_VENUE = 'getscreeninfo(battle/chsvenue=a@8+4x4'


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), REPO / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def game_running():
    if os.name == 'nt':
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq defjam_recomp.exe', '/NH'], capture_output=True, text=True).stdout
        return 'defjam_recomp' in out
    return subprocess.run(['pgrep', '-x', 'defjam_recomp'], capture_output=True).returncode == 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', action='append', required=True, type=Path, help='data folder with packs enabled (repeatable)')
    parser.add_argument('--runs', type=int, default=1, help='runs per data folder (default 1)')
    parser.add_argument('--pick', default=DEFAULT_PICK, help='menu stage that chooses player 1')
    parser.add_argument('--steps', type=int, default=1800, help='fight steps compared (default 1800, thirty seconds)')
    parser.add_argument('--isolate-crowd', action='store_true', help="pin the base game's time-seeded generators (#98)")
    parser.add_argument('--unlock', choices=('1', '0'), default='1', help='RECOMP_UNLOCK_ALL for the runs (default 1)')
    parser.add_argument('--preset', default='win-x64-release')
    parser.add_argument('--output', type=Path, default=REPO / 'logs' / 'fighter-replay-check')
    args = parser.parse_args(argv)
    os.chdir(REPO)
    harness, suite, evidence = load('harness'), load('scenario_suite'), load('test_evidence')
    args.output.mkdir(parents=True, exist_ok=True)
    step_file = suite.step_input(args.output / 'step-input.txt')
    _, display_env = suite.scenario_settings()
    route = harness.ROUTES['fighter-roster-result']
    stages = list(route['stages']) + [args.pick, DEFAULT_CPU, DEFAULT_VENUE, 'game.startgame(=back@9999']
    runs = []
    for folder in args.data:
        for number in range(args.runs):
            if game_running():
                raise SystemExit('another game is running; game runs are serial')
            env = {'DEFJAM_DATA': str(folder.resolve()), 'RECOMP_SETTINGS': 'none', 'RECOMP_PAD_HOST': '0',
                   'RECOMP_PRESENT_PACING': '1', 'RECOMP_UNLOCK_ALL': args.unlock, 'RECOMP_TEST_OBSERVATIONS': '1',
                   'RECOMP_TEST_INPUT': str(step_file.resolve()), 'RECOMP_TEST_RNG_SEED': '20261006'}
            if args.isolate_crowd:
                env['RECOMP_TEST_ISOLATE_CROWD'] = '1'
            env.update(display_env)
            run = harness.run_game('fighter-roster-result', stages=stages, secs=route['secs'], shots='', preset=args.preset,
                                   env=env, quiet=True, until=route.get('until'), after=route.get('after', 0), inherit_recomp=False)
            lines = evidence.state_stream(run.text, args.steps)
            label = f'{folder.name}-{number + 1}'
            (args.output / f'stream-{label}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
            picked = next((line for line in run.text.splitlines() if '[FIGHTERS] participant=0' in line), '')
            row = {'run': label, 'records': len(lines), 'sha256': hashlib.sha256('\n'.join(lines).encode()).hexdigest(),
                   'picked': picked.strip(), 'reached_result': bool(harness.reached(run.summary, route['until'])),
                   'log': str(run.log)}
            runs.append((row, lines))
            print(json.dumps(row), flush=True)
    reference, first = runs[0]
    same = True
    for row, lines in runs[1:]:
        at = next((i for i, (x, y) in enumerate(zip(first, lines)) if x != y), None)
        if at is None and len(first) == len(lines):
            print(f"{reference['run']} vs {row['run']}: identical, {len(lines)} records")
            continue
        same = False
        at = at if at is not None else min(len(first), len(lines))
        print(f"{reference['run']} vs {row['run']}: DIFFER at record {at}")
    if not all(row['picked'] for row, _ in runs):
        print('note: a run picked no custom fighter (check --pick)')
    return 0 if same and all(row['reached_result'] for row, _ in runs) else 1


if __name__ == '__main__':
    sys.exit(main())
