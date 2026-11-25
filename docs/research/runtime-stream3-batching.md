# Stream 3: packet batching on top of Stream 2

This branch contains only the common NV2A packet decoder optimization and its
measurement/validation tooling. It builds on Stream 2 (PR #306). The separate
experimental Xbox D3D entry hooks and direct GPU draw bridge are excluded.

`RECOMP_D3D_HLE_BULK=3` enables constant-register upload batching (mask value 1) and
packed 16-bit index batching (mask value 2). `RECOMP_D3D_HLE=0` is the tested setting.
All runtime optimizations remain off by default. Fence notifications remain
independently opt-in (`RECOMP_FENCE_WAIT=0` unless explicitly enabled).

The scanner batches only complete, contiguous, eligible packets. Partial PUTs,
unsupported methods, debug dumping, survey execution and invalid ranges retain
the scalar path. It preserves register contents, constant versions/cursors,
index order, timer word counts, translator counters and the original draw END.
The runtime source is shared by D3D11 and Vulkan, including MoltenVK.

## Test on Linux or macOS

Use the normal [native build guide](../build-macos-linux.md) and your own dump.
Check out this branch and initialize its exact published submodule pin:

```bash
git fetch origin perf/runtime-stream3-batching
git switch --detach origin/perf/runtime-stream3-batching
git submodule update --init --recursive
export DEFJAM_DATA=/absolute/path/to/your/disposable-test-data
python scripts/pipeline.py analyze
python scripts/pipeline.py recomp
python scripts/pipeline.py build --preset posix-release
python scripts/check-runtime-stream2.py --env RECOMP_D3D_HLE=0 --env RECOMP_D3D_HLE_BULK=3 --quick
```

The data folder must have `extracted/` pointing to your dump and a disposable
copy of your saves. Native CI builds contain no game executable or assets.
Compare the same scenes serially, with the same settings and warm caches:

```bash
python scripts/benchmark-runtime-stream3.py --label batching-control-a --hle 0 --bulk 0 --env RECOMP_D3D11_SHADER_CACHE=1 --env RECOMP_D3D11_STATE_CACHE=1 --env RECOMP_STREAM2_STATS=0 --env RECOMP_PRESENT_PACING=0
python scripts/benchmark-runtime-stream3.py --label batching-candidate-b --hle 0 --bulk 3 --env RECOMP_D3D11_SHADER_CACHE=1 --env RECOMP_D3D11_STATE_CACHE=1 --env RECOMP_STREAM2_STATS=0 --env RECOMP_PRESENT_PACING=0
```

Repeat B then A with fresh labels to reduce order/temperature effects. Fence
waits are off in both commands. D3D11 cache flags affect Windows; Vulkan uses
its existing shader/pipeline cache. Share the JSON summaries, machine/GPU,
driver and effective settings; do not publish logs containing private data.
The CPU sampler supports Windows and Linux. On macOS CPU is unavailable in this
runner; frame-time measurements still work and missing CPU is not zero usage.
Native Linux/macOS gameplay and performance remain owner qualification items.

## Evidence

Toolkit pin: `46981e0e9cd60fba94663c3fda9b3297f5d64592`, published on
[vyanhursky/xboxrecomp](https://github.com/vyanhursky/xboxrecomp/tree/perf/runtime-stream3-bulk).
Focused fixtures compare scalar/batched constants, complete vertex output,
method counters, packet traversal and debug/survey behavior. Native CI includes
these fixtures on Windows, Linux and macOS.

Fresh Windows verified lift/build succeeded (MSVC 19.29, RelWithDebInfo).
Executable SHA-256: `6b702cb65331ac29a56cfef7a32cd42e198c0575e3b14904e1b9b7510ee782db`.
Python checks: 2,007 passed, 845 skipped, one slow test deselected. Game gates
and new CPU comparisons are in progress; two initial rows were rejected because
an unrelated game-testing session started during them. Exclude those trials.
Historical November 24 prototype measurements used a different executable with
disabled experimental entry hooks: about 7–12% lower scene CPU with fence waits
on, and one fence-off pair about 2–7% lower. Isolated-crowd/P-core results were
about 21%, and are not ordinary gameplay measurements. These figures are not a
promise of performance on another machine. Frame rate remained capped at 60.

Retained historical qualifications: the story visual reference gate was 2/4 in
all modes, although candidate/control screenshots were byte-identical. One
unseeded combat assertion failed in a combined experimental mode; a bulk-only
rerun and seeded controls passed. Never update the references to hide a failure.
