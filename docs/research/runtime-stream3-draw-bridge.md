# Stream 3: ordered raw GPU draw bridge

Owner authorized this follow-up on November 25, 2026, after the batching-only
[draft PR #322](https://github.com/vyanhursky/DefJamFFNY-recomp/pull/322).
This is a separate default-off prototype on Stream 2 plus packet batching.
The Windows prototype has passed scoped correctness checks and serial performance
comparisons. Vulkan fallback stress checks also pass. Whole-frame fight captures
retain the crowd-variation qualification below. Keep it default-off pending
native Linux/macOS acceptance. This draft builds on the published batching-only
PR #322 and pins the published bridge toolkit for native cross-machine testing.

## Boundary

The executor remains the sole authority for state, resources and fence ordering.
At an eligible draw END it snapshots the raw vertex streams instead
of deduplicating indices and expanding every used attribute into CPU float4s.
D3D11 or Vulkan uploads that owned snapshot and draws the same expanded index
list using native vertex formats. A shader input adapter performs the NV2A
packed-format conversion on the GPU. There is no persistent guest vertex-buffer
content cache, and no mutable guest pointer is queued across texture preparation,
shader compilation or submission. Rejected native draws gather the same snapshot.

This bypasses CPU vertex gathering. The guest command ring, its NV2A decoder,
texture translation, render state and original completion stores still run.
It does not issue a host graphics call from the guest producer thread.

## Controls

| Variable | Default | Meaning |
|---|---|---|
| `RECOMP_GPU_DRAW_BRIDGE=1` | Off | Eligible raw vertex uploads and GPU input conversion |
| `RECOMP_GPU_DRAW_STATS=1` | Off | Attempts, planned spans, accepted calls, backend fallbacks and planned bytes; use only for coverage, not final timing |
| `RECOMP_GPU_DRAW_FORCE_FALLBACK=1` | Off | Test-only rejection of native raw draws to validate snapshot gathering |
| `RECOMP_D3D_HLE_BULK=3` | Off | Independent common packet batching from #322 |
| `RECOMP_D3D_HLE=0` | Off | Experimental guest D3D entry hooks remain excluded |
| `RECOMP_FENCE_WAIT=1` | Off | Independent opt-in Stream 2 fence notifications |

## Eligibility and limits

Only the existing GPU-compatible, non-constant-writing vertex programs qualify.
Points, debug/batch traces, missing/current attributes, unsupported
formats, out-of-range memory and sparse or oversized uploads use the existing
gather path. Up to 16 streams qualify; nearby interleaved attributes share a
binding. Each source stride is at most 2,048 bytes. Packed source rows are copied
as bytes into native records padded to four-byte stride alignment and sufficient
native fetch width. In particular, SHORT3 source rows use six bytes and native
rows use eight, with zero padding. Validation reads only the original CPU-visible
source elements. Each source span must lie in allowed guest memory or the bounded
inline payload. All native spans are owned before texture/shader preparation.

The index range must fit 16 bits and span at most four times the submitted index
count. Each raw snapshot is capped at 4 MiB and cannot exceed the uncompressed
float4 cost of the submitted indices. These are conservative bandwidth guards,
not guarantees that raw uploads are smaller than the deduplicated old path.
One reusable 4 MiB host snapshot avoids per-draw allocations. No unused padding
or extra vertex can change the original draw's primitive/index order.

Native formats use float1..4, byte4 UINT, short1/2/4 SINT and packed UINT. The
shader explicitly restores missing components to 0,0,0,1, reorders D3DCOLOR,
divides bytes by 255 and shorts by 32,767 without SNORM clipping, and sign-decodes
11:11:10 normals with the original divisors. Native format support is checked;
unsupported layouts fall back without blacklisting the gathered program.

## Stream 2 and platform interaction

Adapted shader source goes through the existing persistent bytecode/SPIR-V
cache. Its full source distinguishes conversion variants; the normal gathered
shader source is unchanged. D3D11's immutable render-state cache remains active,
and every context binding still occurs. Constants, textures, clipping, combiners,
widescreen placement and side redraws use the existing order. Fence waits and
notifications retain the same predicates/stores and remain opt-in.

Raw input layouts/programs have separate bounded caches so they cannot evict
the normal path's entries. D3D11 keeps at most 128 raw program/layout entries.
Vulkan keeps 128 raw program entries, 128 raw shader modules, 256 raw pipelines
and 256 immutable layout IDs. Raw exhaustion falls back, preserving the normal
path's existing capacity. Complete layouts, not program hashes alone, determine
identity. Vulkan checks the whole draw's upload-ring capacity before allocating
any span, preventing an intermediate flush from changing frame slots underneath
previously allocated vertex/index/constant offsets. This also protects gathered
fallback draws, instanced points and fixed-function draws. Pipeline availability
is checked before uploads, so exhausted or unsupported raw pipelines can reject
the draw without consuming its upload space.

The implementation has D3D11 and Vulkan code paths. Vulkan checks portability
driver stride alignment and rejects unsupported record access. Native Linux/macOS
gameplay and hardware performance remain unqualified. Ubuntu/WSL software Vulkan
tests exercise the actual backend, but cannot establish MoltenVK acceptance.

## Windows measurements

The serial ABBA scene comparison uses the same executable with the bridge set
to 0/1/1/0, packet batching at 3, D3D entry hooks at 0, and both Stream 2 caches
enabled. Fence waits, optional counters and experimental presentation pacing
are off. The host is an i7-13700K with 32 GiB RAM and an RTX 4070 Ti SUPER;
the profile is 16:9, scale 3, 1920x1080, a 60 FPS cap and a 144 Hz display.

| Scene | Control process CPU | Bridge process CPU | Relative reduction |
|---|---:|---:|---:|
| sc00 | 129.29% | 127.12% | 1.67% |
| sc07b | 132.40% | 127.99% | 3.33% |

Process CPU sums all threads; 100% means one logical core. These are the means
of two arms per configuration, not whole-machine CPU percentages or FPS gains.
All eight scene windows sustain 60 FPS, with p99 frame times of 16.75–16.86 ms,
no hitches and no audio starvation. Median draws are unchanged at 385/443;
mean draw/vertex volume differs by less than 0.1%. Candidate CPU ranges are
125.69–128.56% for sc00 and 126.55–129.42% for sc07b. The small sc00 result is
close to run variation. The prototype therefore supports a modest CPU benefit
on this host, not a large or universal improvement.

The [numeric evidence](runtime-stream3-draw-bridge-results.json) retains each arm,
timing window, executable/source fingerprints and local log references.
The tested Windows executable SHA-256 is
`6453ce24d2e8c95bc6d88c0a446389a0933705f155b2c6b7ea786a7c0a00a67e`.

A separate coverage run accepted 2,133,945 of 2,154,496 attempted draws (99.05%),
with zero backend fallbacks. Coverage instrumentation is excluded from timing.
Stream 2 recorded shader cache hits and immutable-state reuse. An opt-in fence
run recorded 48,228 waits, 28,155 signals and zero timeouts. These observations
show the features running together; they do not measure fence-related savings.

The separate gameplay ABBA uses fresh disposable saves, identical step-timed
inputs/RNG seed, P-core affinity `0xffff` and crowd isolation. It samples steps
601–2401 (about 34 wall-clock seconds including hit pauses). These controlled
conditions are separate from ordinary crowd gameplay and the unrestricted
scene results above.

| Route | Control process CPU | Bridge process CPU | Relative reduction |
|---|---:|---:|---:|
| Two-player fight | 123.86% | 118.69% | 4.17% |
| Four-player fight | 129.86% | 129.01% | 0.65% |

All eight windows complete without faults or audio starvation. Their canonical
simulation state through step 2401 matches exactly across all four arms per
route: 102 records for fight, 122 for four-player. Control CPU ranges are
120.37–127.35% and 126.63–133.08%; bridge ranges are 118.03–119.35% and
128.04–129.97%. Substantial control spread limits confidence. Both bridge
two-player trials are lower than both controls, but four-player trials overlap
the controls and do not establish a clear performance win. No capture or
instrumented diagnostic run contributes to these averages.

## Correctness evidence

Windows golden-frame checks pass 3/3. The scoped gameplay gate passes 4/4:
120 seconds of fighting, 150 seconds of four-player fighting, a replay with
80 records over 1,800 steps matching the existing golden hash, and two fresh
repeat runs with the same 80 records and golden hash. Fight/FFA median presents
are 120 per two seconds, with minima of 113/102. Logs are
`logs/bridge-goldens.txt`, `logs/bridge-game-gate.txt` and
`logs/regress-20261125-175819.txt`. Both caches are enabled and fence waits are off.

Four further capture-only fights exercise control, native bridge, repeated
control and forced native rejection. Every capture lands exactly at steps 600,
1200 and 1800; all four state streams match the 102-record fight hash through
step 2401. Forced rejection records 1,275,317 gathered fallbacks and zero native
acceptances at the last counter sample, without faults or save failures.

Whole-frame fight parity is **qualified**, not a pass. The crowd's appearance
differs even between the two bridge-disabled controls, as documented in
[crowd nondeterminism](crowd-nondeterminism.md). At 640x480, control-versus-control
mean absolute RGB error is 4.53/6.81/5.53 out of 255 at the three steps;
native-versus-control is 4.85/7.12/5.64, and forced-fallback-versus-control is
5.03/6.41/5.39. These similar magnitudes support crowd variation as the main
visible difference, but do not prove every pixel equivalent. All twelve captures
and their differences stay private; numeric results and hashes are retained.
No masks, reviewed reference frames or golden state hashes were rewritten.

Windows game-free fixtures pass 17/17, including planner bounds/formats, executor primitive/index order,
packet batching, reused guest addresses, guest mutation during state preparation,
forced native rejection and GPU input conversion versus gathered reference using
WARP (288 format comparisons). Ubuntu/WSL portable tests pass with address and
undefined-behavior sanitizers (4/4 portable fixtures). Seven native Linux focused
tests pass, including the validation-runner oracle and two Vulkan fixtures using
Lavapipe and validation layers: packed-format/size/sign comparisons, split bindings,
layout changes, uniform/index/vertex ring wraps, cache exhaustion/fallback and
MSAA, gathered fallback index wraps and instanced-point upload wraps. The final
run has zero validation messages. Windows scripted game results do
not replace native Linux/macOS gameplay and GPU-driver qualification.

The Vulkan validation run found an inherited startup-clear bug: color and MSAA
targets lacked transfer-destination usage. Both now declare the usage required
by their existing clear commands. See the [Vulkan clear-image specification](https://docs.vulkan.org/refpages/latest/refpages/source/vkCmdClearColorImage.html).
The original three validation errors and fixed rerun remain in local logs.

A new fallback stress test reproduced another inherited Vulkan hazard: the
normal draw copied vertices, then a full index ring switched frame slots, leaving
the draw with an offset into the wrong vertex buffer. Both normal and MSAA pixel
comparisons failed before the fix (`logs/bridge-linux-fallback-before.txt`).
Complete-draw reservation fixes both, including raw rejection followed by gather,
and the fixture repeats after raw cache exhaustion. The final evidence is
`logs/bridge-linux-final.txt` and `logs/bridge-linux-final-LastTest.txt`. The test
wrapper also rejects validation errors when the driver exits zero. These
Vulkan-only changes leave the tested Windows executable byte-for-byte unchanged;
the final official build and all 17 Windows fixtures pass.

Initial game pilots rejected the first design: interleaved-only coverage was
14 draws out of tens of thousands, and separate streams alone still rejected
packed six-byte rows. The current planner also repacks those source rows. No
gain is claimed from these profiled pilots; the first pilot's CPU window also
overlapped a Linux test build and is explicitly excluded from timing evidence.
Retain the existing visual-reference and timing-sensitive combat qualifications;
never replace reference images or simulation hashes to make a candidate pass.

Potential costs include extra shader variants and first-use compilation, bounded
host/GPU cache memory, more upload bytes for some draws and additional GPU input
conversion work. Low-spec GPUs can behave differently from this Windows host.
Keep the feature off until measurements and native acceptance justify adoption.

On Vulkan, exhausted raw layout/module/pipeline capacity keeps using the normal
path for unavailable variants; 99% coverage in one scene is not a whole-game
coverage guarantee. The bounded caches favor correctness over unbounded growth.

## Native Linux/macOS hand-off

Toolkit commit [`79d27867c4c4e4728ad5c2be83c197ee6f927a8a`](https://github.com/vyanhursky/xboxrecomp/commit/79d27867c4c4e4728ad5c2be83c197ee6f927a8a)
is published on `perf/runtime-stream3-draw-bridge` and pinned by this game branch.
The game PR is stacked on batching PR #322, which remains batching-only. Checking
out this bridge branch gives Stream 2, packet batching and the raw GPU bridge.

Use the [native build prerequisites](../build-macos-linux.md) and your own dump:

```bash
git fetch origin perf/runtime-stream3-draw-bridge
git switch --detach origin/perf/runtime-stream3-draw-bridge
git submodule sync --recursive
git submodule update --init --recursive
git -C tools/xboxrecomp rev-parse HEAD
# Must print 79d27867c4c4e4728ad5c2be83c197ee6f927a8a.

export DEFJAM_DATA=/absolute/path/to/your/disposable-test-data
python scripts/pipeline.py analyze
python scripts/pipeline.py recomp
python scripts/pipeline.py build --preset posix-release
python scripts/check-runtime-stream2.py --quick --env RECOMP_D3D_HLE=0 --env RECOMP_D3D_HLE_BULK=3 --env RECOMP_GPU_DRAW_BRIDGE=1
```

Use a disposable copy of your saves, with `extracted/` pointing to your dump.
The fixture/save bytes used on Windows are private and are not in the PR. For
longer gameplay/replay checks use your local hashed fixture:

```bash
python scripts/check-runtime-stream2.py --only fight,ffa,replay,repeat --fixture /absolute/path/to/fixture --env RECOMP_D3D_HLE=0 --env RECOMP_D3D_HLE_BULK=3 --env RECOMP_GPU_DRAW_BRIDGE=1
```

Run the game-free fixtures too. CI includes the portable fixtures on Linux and
macOS, WARP on Windows, and validation-enabled software Vulkan on Linux:

```bash
cmake -S tools/xboxrecomp/tests/nv2a_raw_draw -B build/raw-draw -DCMAKE_BUILD_TYPE=Release
cmake --build build/raw-draw
ctest --test-dir build/raw-draw --output-on-failure
```

The [toolkit fixture guide](../../tools/xboxrecomp/tests/nv2a_raw_draw/README.md)
also covers actual offscreen Vulkan/MSAA and sanitizer testing. For a scene
comparison, use the same settings and cache directory in both configurations:

```bash
common=(--hle 0 --bulk 3 --env RECOMP_D3D11_SHADER_CACHE=1 --env RECOMP_D3D11_STATE_CACHE=1
        --env RECOMP_FENCE_WAIT=0 --env RECOMP_GPU_DRAW_STATS=0 --env RECOMP_STREAM2_STATS=0
        --env RECOMP_PRESENT_PACING=0 --env "RECOMP_SHADER_CACHE=$DEFJAM_DATA/cache/vulkan")
python scripts/benchmark-runtime-stream3.py --label bridge-warm-control --env RECOMP_GPU_DRAW_BRIDGE=0 "${common[@]}"
python scripts/benchmark-runtime-stream3.py --label bridge-warm-native --env RECOMP_GPU_DRAW_BRIDGE=1 "${common[@]}"
python scripts/benchmark-runtime-stream3.py --label bridge-a1 --env RECOMP_GPU_DRAW_BRIDGE=0 "${common[@]}"
python scripts/benchmark-runtime-stream3.py --label bridge-b1 --env RECOMP_GPU_DRAW_BRIDGE=1 "${common[@]}"
python scripts/benchmark-runtime-stream3.py --label bridge-b2 --env RECOMP_GPU_DRAW_BRIDGE=1 "${common[@]}"
python scripts/benchmark-runtime-stream3.py --label bridge-a2 --env RECOMP_GPU_DRAW_BRIDGE=0 "${common[@]}"
```

Exclude the two warm-up runs from measurements. Run serially and use fresh labels
if repeating. Results go under `logs/stream2/LABEL`. The CPU sampler supports
Linux and Windows; on macOS CPU is unavailable in this runner, so use a native
profiler for CPU and retain its frame-time results. Missing CPU is not zero usage.
D3D11 cache flags affect Windows; native Vulkan uses its existing shader/pipeline
cache. Share machine/GPU/driver, effective flags and summaries with the results.

Native acceptance still needs Linux hardware and macOS/MoltenVK builds, focused
fixtures, game correctness/visual checks and repeated CPU/frame-time comparisons.
Use `RECOMP_D3D_HLE=0`, `RECOMP_D3D_HLE_BULK=3` and toggle only
`RECOMP_GPU_DRAW_BRIDGE=0/1` for the primary comparison. Keep optional counters
off, warm both configurations, retain the same renderer/settings and leave
fence waits opt-in. The toolkit fixture README includes portable, Vulkan and
sanitizer commands. Native hardware success is required before making platform
parity or low-spec performance claims.
