# Build-time experiment: Stream 1

Streams 2 and 3 are on hold; see [the scope](toolkit-optimization-streams.md).

The experimental toolkit adds `--workers N` (body emission in child processes)
and `--chunk-lines N` (a function-body line budget in addition to `--split`). Analysis,
boundary repair, naming, manual overrides, unresolved entry stubs and file
publication stay in the parent. Existing toolkit defaults remain unchanged.

Run `scripts/benchmark-build-time.py --help` for the cross-platform driver.
It records every phase's wall time, failures, exact commits, compiler flags,
Python/dependency versions, generated-source identities and Ninja action data.
It does not run the game or write saves. Configure includes dependency fetching
and is reported separately from compilation; `--clean` cleans only this
checkout's selected CMake preset through the build tool.

Windows: use the same VS developer shell, preset and `--jobs` for every arm.
Linux: use the same compiler/container/dependencies, preset and `--jobs`.
Start with two lifter workers on a low-memory machine. Each worker receives a
private snapshot of the finalized analysis, so more processes use more memory.

## Scope and controls

The toolkit changes only build tooling. Both options are opt-in; production
Setup and the regular pipeline keep their previous defaults. The process pool
always uses spawn, including on Linux. Each worker creates its own Capstone
engine, receives the already-finalized analysis/configuration and returns body
text and ordered reporting data. At most twice the worker count of 32-function
groups can be in flight. Warnings are replayed and deduplicated in input order;
the parent also preserves explicit worker failures and joins the pool.

Line budgeting keeps original function order, never divides a function, retains
the function-count ceiling and removes stale numeric chunks, including names
above 9999. It does not promise equal compiler cost per line. Unchanged-output
timestamp handling remains in place.

SIMD-header trimming was deliberately excluded: this toolkit's shared header
also uses intrinsics in scalar conversion and approximation helpers. It needs
separate dependency analysis and a measured benefit before pruning is justified.
No compiler optimization level, arithmetic/aliasing flags, runtime code, GPU
backend, shader persistence, fence behavior or render-state behavior is changed.

## Windows measurements

Host: i7-13700K (16 cores / 24 logical CPUs), 32 GiB RAM, Windows 11; Python
3.13.5, Capstone 5.0.9, pyxbe 1.0.4; MSVC 14.29.30133, CMake 3.20.21032501,
Ninja 1.10.2; `win-x64-release` / RelWithDebInfo, 12 compiler jobs throughout.
Game baseline `f80a792`, toolkit baseline `d108a64`; experimental toolkit
`e58a938`. Each compile was clean, including runtime/SDL dependencies; download
and configure time is separate. Results are observations on this host, not
Linux or gameplay FPS guarantees.

| Run | Workers | Body-line budget | Chunks | Init (s) | Body/output (s) | Whole lift (s) | Compile/link (s) |
|---|---:|---|---:|---:|---:|---:|---:|
| baseline-a, original pin | 1 | count only | 19 | 39.4 | 32.5 | 73.04 | 111.87 |
| baseline-b, original pin | 1 | count only | 19 | 38.2 | 31.2 | 70.32 | 104.36 |
| candidate-a | 4 | 20000 | 89 | 36.9 | 14.5 | 52.78 | 108.31 |
| candidate-b-60k | 4 | 60000 | 30 | 47.0 | 17.1 | 65.22 | 104.04 |
| control-c-serial, new pin/defaults | 1 | count only | 19 | 60.5 | 33.5 | 95.08 | 113.81 |
| restricted CPU set, serial | 1 | count only | 19 | 57.8 | 91.8 | 150.68 | 124.64 |
| same restricted CPU set, parallel | 4 | count only | 19 | 40.0 | 16.7 | 57.66 | 123.40 |

The original-pin two-run medians versus the first two candidate runs are:

- Body emission and output: **31.85 -> 15.80 s**, about **50% less time**.
- Whole lifting, including unchanged initialization: **71.68 -> 59.00 s**,
  about **18% less time**.
- Clean compile/link: **108.12 -> 106.17 s**, about 2%, within the baseline
  spread. **No repeatable Windows compilation improvement is established.**
- Lift plus clean compile/link: **179.80 -> 165.18 s**, about **8% less time**.
  This excludes analysis, verification and dependency/configure phases.

These are exploratory measurements, not a statistical acceptance gate. The
shared desktop was not globally idle: an installed game started near the end
of baseline-b, candidate-a overlapped game sessions, and other background work
remained in later runs. Unchanged initialization varied from 36.9 to 60.5 s.
The last two runs restrict only the benchmark shell and its descendants to
verified group-0 logical CPUs 0..15 (`0xffff`, the P-core CPU set); other
processes were untouched. This restriction also produced an unusually slow
serial body phase, so that pair is retained separately and its larger apparent
gain is not used as the headline estimate. No-op native builds were 0.08–0.09 s.
Analysis was 160.28 s baseline / 157.44 s candidate, with identical numeric
output hashes; analysis itself is not optimized here.

The practical recommendation is to test **parallel lifting first**, retaining
the original chunk layout. Keep both line budgets as explicit Linux experiments
where compiler concurrency and memory pressure differ. No production default
change is justified by these Windows chunking results.

[Machine-readable timings and qualifications](build-time-windows-2026-11-22.json)
retain all seven successful trials and the shared source identities.

Local artifacts are `logs/build-time/<label>/result.json`, each phase log,
`CMakeCache.txt` and `ninja_log`. Generated code and logs remain untracked.
Analysis's numeric output identity, generated body-text identity across chunk
boundaries, and support-file byte hashes are compared independently of timing.

## Validation and limits

- Every trial: 18,438 translated functions, zero failed translations; generated
  function text and support-file identities match the baseline. Both line
  budgets compile successfully. The final parallel/original-layout output is
  also byte-identical across **all 23 C/header files** to the original pin's
  generated sources.
- Toolkit MSVC compiled CPU/tool checks: **837 passed, 20 skipped, 133 subtests
  passed** (`logs/toolkit-msvc-tests.txt`). A separate non-developer-shell tool
  run had 740 passed / 117 skipped; the MSVC run supplies the additional native
  coverage and is not added to it as a unique-test total.
- Project unit suite: **1,999 passed, 845 skipped**
  (`logs/parent-unit-tests.txt`). Benchmark identity tests are included.
- Focused ownership/manual/spawn/chunk tests: 207 passed. Forced-spawn tests
  compare serial bytes and accounting, including manual and wrapped functions,
  entry hooks, custom memory layout, back-edge hooks and unresolved entry stubs.
- The source policy check passes. No generated game code, binaries, captures,
  saves or raw logs are published.
- Final parallel/original-layout build: **4/4 scoped game checks passed**
  (`logs/regress-20261122-112430.txt`): loading/title/menu goldens and a fight
  with 122 s observed combat, median 120 presents per 2 s, minimum 109. The
  separately passed unit suite completes the quick-check scope without rerunning
  it. This gameplay run qualifies the original chunk layout, not the two
  rechunked builds. An earlier launch was deferred for an unowned photo-mode
  session; no other process was stopped. This remains a draft, not full
  native/platform/installer qualification or a queued release.
- Linux/macOS CI now runs the synthetic spawn/chunk tests. Native low-spec
  Linux timing, memory and gameplay acceptance remain the owner's test.

## Low-spec Linux A/B

Use the same native compiler or existing build container, dependencies and
power profile for both worktrees. Close games and other compilation jobs for
the timed runs. This procedure compiles but does not run either game.

```bash
git clone --recursive --branch perf/build-time-stream1 \
  https://github.com/vyanhursky/DefJamFFNY-recomp.git defjam-build-time
cd defjam-build-time
git worktree add --detach ../defjam-build-time-base f80a792b434379cbf580a23240097c2fee4597b2
git -C ../defjam-build-time-base submodule update --init --recursive

# Each data root has a private save directory and a read-only-use dump link.
# Replace /path/to/your/extracted with your own supported extracted dump.
mkdir -p ../defjam-build-data-base/save ../defjam-build-data-candidate/save
ln -s /path/to/your/extracted ../defjam-build-data-base/extracted
ln -s /path/to/your/extracted ../defjam-build-data-candidate/extracted

# Run the same driver against the old source and the candidate.
# The baseline receives neither of the new toolkit options.
DEFJAM_DATA="$(realpath ../defjam-build-data-base)" \
  python3 scripts/benchmark-build-time.py --repo ../defjam-build-time-base \
  --label baseline-a --jobs 2 --analyze --clean
DEFJAM_DATA="$(realpath ../defjam-build-data-candidate)" \
  python3 scripts/benchmark-build-time.py \
  --label candidate-a --jobs 2 --workers 2 --analyze --clean
```

The first candidate isolates parallel lifting and retains the original chunk
layout. For additional candidates, keep `--jobs 2 --workers 2` and use new labels
with `--chunk-lines 20000` and `--chunk-lines 60000`. These line budgets are
experimental arms, not proven universal defaults. For repeats use new labels and omit
`--analyze`; verified existing analysis is reused. For compile-only repeats,
use `--skip-lift --clean` and omit `--workers` and `--chunk-lines`.

Do not combine host analysis with a different container Python at build time;
the pipeline correctly refuses mismatched interpreter/tool inputs. Run the
whole driver inside the normal build container when that is your environment.
Avoid compiler-cache hits in clean comparisons: use the same cache policy in
both arms, and disable ccache/sccache if measuring actual compile throughput.

Compare the two first-run records from the candidate checkout:

```bash
python3 - <<'PY'
import json
from pathlib import Path
base = json.loads(Path('../defjam-build-time-base/logs/build-time/baseline-a/result.json').read_text())
test = json.loads(Path('logs/build-time/candidate-a/result.json').read_text())
assert base['complete'] and test['complete']
assert base['generated']['body_text_sha256'] == test['generated']['body_text_sha256']
assert base['generated']['support_sha256'] == test['generated']['support_sha256']
for name in ('analyze', 'lift', 'configure', 'compile-link', 'no-op-build'):
    a = next(x['seconds'] for x in base['phases'] if x['name'] == name)
    b = next(x['seconds'] for x in test['phases'] if x['name'] == name)
    print(f'{name}: {a:.2f}s -> {b:.2f}s ({(a-b)/a*100:+.1f}% shorter)')
PY
```

Keep the JSON files, failed runs and machine/compiler details together. A warm
configure or a noisy single run does not establish an optimization gain.
The driver compares source text across chunk layouts; it does not assert that
the native machine code is identical after the compiler sees new boundaries.

After compilation, check the synthetic spawn tests:

```bash
(cd tools/xboxrecomp && python3 -m pytest -q tools/recomp/test_build_time.py)
```

For native game qualification, link the candidate's `game` to its dump and run
the usual quick regression from that candidate with its private data root,
when no other game test is running. Full native Linux acceptance and low-memory
worker/compile measurements remain the owner's test; CI has no game dump.
