#!/usr/bin/env python3
"""Time isolated lifting/configure/clean compilation/no-op builds on Windows or Linux.

Run from a VS developer shell on Windows, or the normal Linux build environment.
Needs the usual verified analysis (or --analyze), dump and build dependencies.
Does not run the game or change saves. Results and compiler output stay in logs/.
Use identical --jobs, compiler, preset and inputs for all arms. --clean asks CMake
to clean this checkout's preset before the timed compilation; dependency fetching
is part of the separately reported configure phase.
"""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]


def generated_identity(folder):
    """Compare lifted text across chunk layouts, retaining every nonblank line.

    Ignore only generated chunk prologues and blank separator lines. Header,
    dispatch and unresolved stubs are hashed verbatim. This is source equivalence,
    not proof that different translation units compile to identical machine code.
    """
    digest = hashlib.sha256()
    chunks = sorted((p for p in folder.iterdir() if re.fullmatch(r'recomp_[0-9]{4,}\.c', p.name)),
                    key=lambda p: int(p.stem.split('_')[-1]))
    for path in chunks:
        text = path.read_text(encoding='utf-8')
        marker = '#include <math.h>\n'
        if marker not in text:
            raise ValueError(f'Unrecognized generated chunk: {path.name}')
        for line in text.split(marker, 1)[1].splitlines():
            if line.strip():
                digest.update((line + '\n').encode('utf-8'))
    return {
        'chunks': len(chunks),
        'chunk_bytes': [p.stat().st_size for p in chunks],
        'body_text_sha256': digest.hexdigest(),
        'support_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in sorted(folder.iterdir())
                           if p.suffix in {'.h', '.c'} and p not in chunks},
    }


def capture(command, cwd):
    return subprocess.check_output(command, cwd=cwd, text=True).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--repo', type=Path, default=REPO)
    ap.add_argument('--label', required=True, help='Unique result folder name under logs/build-time')
    ap.add_argument('--preset', default='win-x64-release' if os.name == 'nt' else 'posix-release')
    ap.add_argument('--jobs', type=int, default=2, help='Native compiler concurrency, identical in both arms')
    ap.add_argument('--workers', type=int, help='Opt-in parallel lifter; omit for the baseline toolkit')
    ap.add_argument('--chunk-lines', type=int, help='Opt-in line budget per generated C chunk')
    ap.add_argument('--split', type=int, default=1000)
    ap.add_argument('--analyze', action='store_true', help='Run and time normal analysis before lifting')
    ap.add_argument('--skip-lift', action='store_true', help='Reuse verified generated sources for compile repeats')
    ap.add_argument('--clean', action='store_true', help='Clean this preset before compilation')
    args = ap.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.label) or args.label in {'.', '..'}:
        ap.error('--label must be a simple folder name')
    if args.jobs < 1 or args.split < 1 or any(v is not None and v < 1 for v in (args.workers, args.chunk_lines)):
        ap.error('jobs, split, workers and chunk-lines must be positive')
    if args.skip_lift and (args.workers is not None or args.chunk_lines is not None):
        ap.error('lifter options cannot be combined with --skip-lift')
    repo = args.repo.resolve()
    tk = repo / 'tools/xboxrecomp'
    output = repo / 'logs/build-time' / args.label
    output.mkdir(parents=True, exist_ok=False)
    state = [sys.executable, str(repo / 'scripts/pipeline-state.py')]
    results = {
        'label': args.label, 'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'platform': platform.platform(), 'processor': platform.processor(),
        'logical_cpus': os.cpu_count(), 'python': sys.version,
        'packages': {n: importlib.metadata.version(n) for n in ('pyxbe', 'capstone')},
        'game_commit': capture(['git', 'rev-parse', 'HEAD'], repo),
        'toolkit_commit': capture(['git', 'rev-parse', 'HEAD'], tk),
        'toolkit_diff_sha256': hashlib.sha256(subprocess.check_output(['git', 'diff', 'HEAD'], cwd=tk)).hexdigest(),
        'preset': args.preset, 'jobs': args.jobs, 'workers': args.workers,
        'chunk_lines': args.chunk_lines, 'split': args.split, 'clean_requested': args.clean,
        'cmake': capture(['cmake', '--version'], repo).splitlines()[0], 'phases': [],
    }

    def save():
        (output / 'result.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')

    def run(name, command):
        print(f'{args.label}: {name}', flush=True)
        start = time.perf_counter()
        with (output / f'{name}.log').open('w', encoding='utf-8') as log:
            status = subprocess.run(list(map(str, command)), cwd=repo, stdout=log, stderr=subprocess.STDOUT).returncode
        elapsed = time.perf_counter() - start
        results['phases'].append({'name': name, 'seconds': elapsed, 'exit_code': status,
                                  'command': list(map(str, command))})
        save()
        print(f'  {elapsed:.3f}s (exit {status})', flush=True)
        if status:
            raise SystemExit(f'{name} failed: {output / (name + ".log")}')

    if args.analyze:
        run('analyze', [sys.executable, repo / 'scripts/pipeline.py', 'analyze', '--no-archive'])
    if not args.skip_lift:
        extra = []
        if args.workers is not None:
            extra += ['--workers', str(args.workers)]
        if args.chunk_lines is not None:
            extra += ['--chunk-lines', str(args.chunk_lines)]
        run('lift', state + ['lift', '--split', str(args.split), '--', *extra])
        run('manual-addresses', [sys.executable, repo / 'scripts/check-manual-addresses.py'])
    run('verify-lift', state + ['verify-lift'])
    results['generated'] = generated_identity(repo / 'src/recomp/gen')
    run('begin-build', state + ['begin-build', '--preset', args.preset])
    run('configure', ['cmake', '--preset', args.preset, '-DDEFJAM_BUILD_GAME=ON', f'-DXBOXRECOMP_DIR={tk}'])
    build = ['cmake', '--build', '--preset', args.preset]
    if args.clean:
        run('clean', build + ['--target', 'clean'])
    run('compile-link', build + ['--target', 'defjam_recomp', '--parallel', str(args.jobs)])
    run('record-build', state + ['record-build', '--preset', args.preset])
    run('no-op-build', build + ['--target', 'defjam_recomp', '--parallel', str(args.jobs)])
    build_dir = repo / 'build' / args.preset
    for name in ('.ninja_log', 'CMakeCache.txt'):
        if (build_dir / name).is_file():
            shutil.copyfile(build_dir / name, output / name.lstrip('.'))
    cache = (build_dir / 'CMakeCache.txt').read_text(encoding='utf-8')
    results['compiler_cache'] = [line for line in cache.splitlines()
                                 if line.startswith(('CMAKE_C_COMPILER:', 'CMAKE_CXX_COMPILER:',
                                                     'CMAKE_BUILD_TYPE:', 'CMAKE_C_FLAGS_RELWITHDEBINFO:'))]
    results['complete'] = True
    save()
    print(f'Results: {output / "result.json"}', flush=True)


if __name__ == '__main__':
    main()
