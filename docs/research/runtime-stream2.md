# Stream 2: runtime overhead experiments

Owner authorized this stream on 2026-11-22 after the Stream 1 draft
[PR #304](https://github.com/vyanhursky/DefJamFFNY-recomp/pull/304).
Stream 3 (higher-level D3D interception) remains on hold.

Base: game `f80a792b434379cbf580a23240097c2fee4597b2`, released toolkit
`d108a64c0f272da2ab29016914f473018c3e2347`. This experiment starts from the
released runtime and does not depend on Stream 1's build changes. Implemented
independently against this toolkit; no code was copied from XboxXBERecomp or
DirectXbox-Recomp ([XboxXBERecomp](https://github.com/TGP482/XboxXBERecomp),
[DirectXbox-Recomp](https://github.com/phobos665/DirectXbox-Recomp)). Permission,
attribution and adoption remain owner decisions;
no author was contacted and no upstream PR was opened.

## Controls and implementation

All three changes are opt-in, per process. Set a switch to `0` for its control.

| Switch | Scope | Implementation |
|---|---|---|
| `RECOMP_D3D11_SHADER_CACHE=1` | Windows D3D11 only | Persistent successful DXBC, covering the ten current renderer compile sites. Key includes exact source bytes, source name (NULL distinct from empty), entry, target, both compiler flags and a hash of the actual compiler DLL bytes. Defines/includes bypass the disk cache. |
| `RECOMP_D3D11_STATE_CACHE=1` | Windows D3D11 only | Bounded 32-entry LRU per immutable blend, depth/stencil, rasterizer and sampler object type. Full zeroed translated descriptors are keys; stencil reference and blend factor remain dynamic bindings. All context bindings still occur, including after overlay changes. |
| `RECOMP_FENCE_WAIT=1` | Windows and POSIX host path | The game's existing fence-insert hold waits on an epoch/condition variable after testing the same unsigned lag predicate. Executor notifications occur after existing completion stores, never advance a fence, and cannot lose a check-to-sleep completion. A 2 ms fallback discovers direct guest writes; the existing approximately 100 ms escape remains. POSIX drops the guest CPU turn before taking the progress lock and restores it after unlocking. |
| `RECOMP_STREAM2_STATS=1` | Diagnostics | Cumulative `[S2SHADER]`, `[S2STATE]` and `[S2FENCE]` counters. Use the same setting in both comparison arms. |

The shader directory defaults to `$DEFJAM_DATA/cache/d3d11` and can be overridden
with `RECOMP_D3D11_SHADER_CACHE_DIR`. Bad magic/version, mismatched complete keys,
truncation, oversized payloads, invalid DXBC container bounds and payload digest
changes cause a fresh compile. Writes use unique same-directory temporary files
and atomic replacement; unavailable/unwritable storage falls back to compilation.
Failed compiles are not saved. Delete the cache directory while the game is closed
to reset it. Vulkan's existing disk cache and indexed sampler cache are unchanged.
This persists HLSL-to-DXBC output; GPU-specific driver compilation remains.

COM references held by state-cache entries are independent of active/context
references. Shutdown releases entries before the device is released. The current
device Reset behavior is unchanged. This does not skip state binding, move draws
above the push-buffer executor, or implement Stream 3.

## Local method

Windows 11, i7-13700K (16 cores / 24 logical CPUs), 32 GB RAM, RTX 4070 Ti SUPER;
MSVC 19.29 / CMake 3.20 / Ninja 1.10.2, release preset (`RelWithDebInfo`).
Isolated game/toolkit worktrees and private saves/cache; extracted dump shared
read-only. All game trials are serial. Do not run another game, build or benchmark
at the same time. Shared-desktop observations are not low-spec predictions.
On Windows/Linux the driver detects a defined list of compiler/build process
names and foreign game processes at launch and every two seconds during a trial.
The local queue additionally waits for other pytest, native-fixture and regression
jobs. Unlisted workloads may escape detection; macOS has no workload inventory.
This does not make the desktop an isolated lab.

`scripts/benchmark-runtime-stream2.py` uses the existing save-guarded harness and
scene recorder, without image capture. It plays `sc00` and `sc07b` to their ends at
16:9, render scale 3, vsync on, the game's normal 60 fps pacing. The window is
configurable; these Windows sessions record an effective 1920x1080 in their
session metadata and summary. The driver stores the harness's effective run
identity/environment, not just the requested overrides. It records
frame distributions, scene-load frames, audio underruns, and process CPU sampled
across all threads during scene playback. CPU percent uses one logical CPU as
100%; it is not total-machine utilization or GPU time. Windows uses GetProcessTimes,
Linux uses `/proc/PID/stat`; macOS still reports frame results without CPU residency.
CPU intervals and sampling cadence use a monotonic clock and one owned game PID.
Recorder summary errors, unexpected exits, shared fault-policy failures and failed
save restoration invalidate a trial. Periodic/sparse runtime counters are the
latest logged observations, not exact shutdown totals.

At a 60 fps cap, a lower CPU percentage is useful headroom, not an FPS increase.
Scene-load time includes unrelated loading and cannot be called shader time.
`[S2SHADER] compile_ms` measures compiler wall time; `io_ms` measures cache read/write
work. Cold and warm cache directories must be explicit.

## Native checks and retained failures

- New `tests/nv2a_progress`: 100 notifications in the check-to-sleep gap, timed
  no-progress return, and broadcast to two simultaneous waiters: pass on Windows.
- Consolidated CTest at `0080b5b`: **6/6 pass**. Parent CI now includes the
  game-free progress fixture on Windows/Linux/macOS; Windows also runs the state
  and shader cache fixtures. The PR carries the cross-platform CI status.
- Existing `d3d8_states_smoke` in both default and `cache` modes: pass on WARP.
  Cache mode adds unchanged-draw factory counts, A/B/A reuse, bounded eviction,
  anisotropy changes, shutdown/reinit and rebinding after context ClearState.
- New `d3d8_shader_cache` in enabled and disabled modes: pass on WARP. Covers
  byte-identical blobs, real shader creation, cold/warm counters, payload corruption,
  truncated headers, mismatched stored keys, key-field changes, concurrent
  publication, unavailable directory fallback, and non-persistence of macro-driven
  and failed compiles. Expanded tests pass at `313195a`.
- Broader pre-existing `d3d8_a8`: **120 failures / 336 A8 draws**, RHW **0 / 4**;
  `d3d8_gamma`: **9 failures / 9 captured + 1 real presents**. The released `d108a64`
  and candidate `905cf95` with all switches off produce these same counts. They
  remain failures, not passes. Stock logs: review workspace toolkit
  `build/stock-a8.txt`, `build/stock-gamma.txt`.

## Measurements on this machine

The numbers-only [trial results](runtime-stream2-results.json) retain controls,
individual features, cold/warm cache trials and repeats. All measured clean-series
runs use the same executable. CPU values below are percent of **one logical CPU**.

| Configuration | Trials | sc00 CPU % | sc07b CPU % |
|---|---:|---:|---:|
| Control, profiling on | 2 | 136.17–144.17 | 138.43–145.22 |
| State reuse only | 2 | 137.83–138.46 | 133.60–139.97 |
| Fence wait only | 1 | 77.16 | 59.30 |
| Shader cache warm only | 1 | 133.72 | 135.75 |
| All three, warm cache | 2 | 79.16–80.72 | 55.64–57.84 |
| Control, profiling off | 1 | 135.07 | 133.08 |
| All three, warm cache, profiling off | 1 | 74.28 | 58.32 |

The combined profiled pairs use approximately **41–45% less process CPU in sc00**
and **58–62% less in sc07b** than their controls. This is headroom at the existing
60 fps cap, not an FPS increase. Combined p99 frame intervals remain around
16.86–16.94 ms; controls range around 16.77–16.99 ms. No steady-state frame-time
improvement is established. Audio-dry counters are zero in these scene windows.
The profiling-disabled confirmation saves **45.0% / 56.2%** process CPU, with
frame p99 **16.82 / 16.82 ms** versus control **16.82 / 16.89 ms**. This confirms
the CPU reduction without attributing a material frame-time gain.

**The preliminary standalone 4–8% state-cache CPU claim is not reproduced.**
The first pair improved, but the second state-only pair used approximately 1–2%
more CPU than its preceding control. Controls themselves varied. Treat standalone
CPU benefit on this GPU as uncertain. The certain result is fewer factory API
requests: about 4.04 requests per draw becomes approximately 0.00001, without
skipping context bindings. D3D11 may already intern equivalent state objects, so
this does not mean millions of real driver allocations were removed.

Warm persistent caching hits all **31 / 32** shader requests in the two fresh game
processes: **zero D3DCompile calls**, versus about **0.9 seconds inside the compiler**
per control process. Timed warm cache I/O is about **3 ms** per process; that timer
excludes compiler-DLL identity setup, shader-object creation and driver work.
The initially empty shared cache writes 31 entries in sc00; the following sc07b
process reuses 30 and adds two. The warm cache has 33 files / 237,202 bytes (about
232 KiB). Do not call the compiler-time saving a measured FPS or total-load-time
improvement. Cache size is currently unbounded across additional content.

State-cache bookkeeping is approximately 66 KiB plus up to 128 cached driver state
objects (32 per kind), with bounded eviction. Descriptor lookup has a CPU cost;
wrong identity/lifecycle handling could cause rendering regressions. The fence
change has greater timing/synchronization risk and remains explicitly opt-in,
including in the validation runner. Other-machine gameplay/timing acceptance is
still required, especially the POSIX guest-turn path.

The fixture-only pin change `313195a` -> `0080b5b` leaves the game executable
byte-identical (SHA-256 `5add232bde102cacc00f43cbf7f74ed23377f7d508406f7b7beb7589621e3d7b`),
recorded in `logs/stream2/fixture-only-pin-identity.json`. The game source base is
`f80a792` plus this branch's manual fence hook; each trial records the worktree
HEAD, manual-source hash and toolkit pin. Early measurements precede the parent
source commit but use the same runtime source/binary.

Project unit check: **1,996 passed / 845 skipped / 1 slow test deselected** in
97.47 s, `logs/stream2-unit.txt`, plus **4/4** new runner regression tests in
`logs/stream2-runner-unit.txt`. Native conformance is 6/6. The PR's Testing section
records the game-gate results (loading/title/menu, fight, FFA, approved visuals,
replay and repeat), remaining owner acceptance, and any focused reruns.

### Retained interference and validity limits

The unmodified stock reference completed both scenes in
`logs/stream2/baseline-stock`. Initial candidate `control-1` / `states-1` timings
were quarantined after external builds/native fixtures/pytest were observed; the
initial `fence-1` was explicitly stopped only in this lane. No foreign process was
stopped. Its scene did not end. Triage's first unclassified kernel/file diagnostic
was inspected (line 414), with no explained crash signature. This is not a pass.
See `logs/stream2/initial-series-contamination.txt` and the interrupted-trial digest.

The first profiling-disabled combined confirmation was also invalidated when a
foreign CMake/Ninja/MSVC job appeared. Its `runs.json` records that interference;
it is excluded and retried under a new label. Never silently include partial
trials or label these interruptions game crashes.

An early correctness-runner attempt applied switches only to the cached harness
module. Existing checks exec fresh copies, so its three successful goldens are
all-off controls, not enabled-feature evidence. The runner now instruments fresh
copies, shares child ownership, asserts each effective environment and fails if
no game is intercepted. Four regression tests cover that failure mode and fence
opt-in. The obsolete attempt was stopped only in this lane; its private save was
restored with the existing save-recovery command and verified resolved. A later
enabled menu capture was invalidated by a foreign game opening; the effective
flags and interference are retained in the validation audit, not counted as a pass.

The two early clean trials (`quiet-control-1`, `quiet-states-1`) used harness
wall-clock CPU intervals and later received explicit validity audits: normal
harness termination, no shared-policy faults, valid recordings, approximately six
seconds of post-scene frames, and observed save restoration. Audit files are
`logs/stream2/early-quiet-validity.json`, `early-quiet-boundaries.json` and copied
save-guard markers. Later trials use monotonic CPU intervals, one owned PID and
explicit fault/save/session checks. Periodic/sparse state and fence reports are
nearest logged observations, not exact exit totals. This is shared-desktop,
small-sample evidence, not a controlled cross-hardware performance guarantee.

## Retesting

Use a fresh checkout and writable data/build/save roots for this experiment:

```sh
git clone --branch perf/runtime-stream2 --recurse-submodules https://github.com/vyanhursky/DefJamFFNY-recomp.git DefJamFFNY-stream2
cd DefJamFFNY-stream2
```

Follow the normal [Windows](../build-and-play.md) or
[macOS/Linux](../build-macos-linux.md) source-build guide using your own dump.
On Linux, the release build command is
`python scripts/pipeline.py build --preset posix-release` after analysis/lifting.
This branch starts from the released toolkit; it does not include Stream 1's
build-time changes. Do not reuse another worktree's writable saves or build files.

Build the branch normally with its matching toolkit pin, then run from the game
repository with your own `DEFJAM_DATA` set. Use a fresh label for every trial:

```text
python scripts/benchmark-runtime-stream2.py --label control-1
python scripts/benchmark-runtime-stream2.py --label states-1 --env RECOMP_D3D11_STATE_CACHE=1
python scripts/benchmark-runtime-stream2.py --label fence-1 --env RECOMP_FENCE_WAIT=1
python scripts/benchmark-runtime-stream2.py --label shaders-cold --env RECOMP_D3D11_SHADER_CACHE=1 --env RECOMP_D3D11_SHADER_CACHE_DIR=ABSOLUTE_NEW_PRIVATE_CACHE
python scripts/benchmark-runtime-stream2.py --label shaders-warm --env RECOMP_D3D11_SHADER_CACHE=1 --env RECOMP_D3D11_SHADER_CACHE_DIR=SAME_PRIVATE_CACHE
python scripts/benchmark-runtime-stream2.py --label combined-1 --env RECOMP_D3D11_STATE_CACHE=1 --env RECOMP_FENCE_WAIT=1 --env RECOMP_D3D11_SHADER_CACHE=1 --env RECOMP_D3D11_SHADER_CACHE_DIR=SAME_PRIVATE_CACHE
python scripts/benchmark-runtime-stream2.py --label control-2
```

The script explicitly zeros all three switches before applying `--env` overrides
and enables diagnostics in every arm. Results stay under `logs/stream2/LABEL`.
Repeat controls and combined trials in alternating order. On Linux only the fence
switch changes this prototype's runtime; both D3D11 switches have no effect on the
Vulkan renderer. On a low-spec GPU, add `--env RECOMP_RENDER_SCALE=1` to **every**
comparison arm if desired; compare like settings on the same machine. Retest
ordinary fights/FFA, rendering, startup/shutdown, audio and
replay/repeatability in addition to these cinematic workloads.

Enabled-feature correctness runner (also applies switches to isolated startup
checks, which normally strip inherited `RECOMP_*` variables):

```text
python scripts/check-runtime-stream2.py --quick
python scripts/check-runtime-stream2.py --only ffa,visual,replay,repeat --fixture ABSOLUTE_PRIVATE_FIXTURE
python scripts/check-runtime-stream2.py --env RECOMP_FENCE_WAIT=1 --only fight,ffa,visual,replay,repeat --fixture ABSOLUTE_PRIVATE_FIXTURE
```

It uses the existing shared fault/save policy, records each effective run identity
under `logs/stream2/validation-*.json`, and waits for detected foreign games/builds.
The correctness runner enables the two Windows caches but **defaults fence waits
to 0**. Only the explicit final command opts into notified fence waits. The game
itself defaults all three feature switches to 0. A fixture and approved local
visual baselines are needed for the scenario checks; keep save bytes local.
Approved local visual baselines were copied read-only from the established data
root into this lane's private test-baseline directory; originals are unchanged.

## Decisions

- D-new: Keep independently switchable, default-off experiments until native
  cross-machine correctness and performance are established.
- D-new: Use complete translated descriptors and bounded COM ownership rather
  than the old XOR identities or suppressing context state binding.
- D-new: Keep fence semantics and escape, add notifications plus a timed recheck;
  direct guest writes prevent relying on notifications alone.
- D-new: Preserve stock fixture failures and shared-host limitations alongside
  successful new tests. This is not release qualification.
