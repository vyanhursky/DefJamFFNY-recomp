# Windows without Visual Studio Build Tools: issue #189 spike

Dates: 2026-11-22–23. Source base `f80a792` (public main, project 1.2.1),
toolkit base `d108a64c0f272da2ab29016914f473018c3e2347` plus the qualified,
published TLS fix `274e6fbd63de904562d73c960aad674ace2caf6a`.
Issue: <https://github.com/vyanhursky/DefJamFFNY-recomp/issues/189>.

## Recommendation and scope

Continue with native x64 UCRT LLVM-MinGW (option A). The current runtime is
substantially more portable than the issue's November 5 checklist: it already
has MinGW support, compiler-selected guest TLS and XInput 1.4 linkage. No actual
`__try/__except` block remains in the current game/runtime source search.
Do not replace production Setup's MSVC path until qualification and
clean-machine installation are complete. Option B is not necessary to resolve
the measured compile failures; keep it as a fallback if option A fails runtime
or performance gates. SDK alone is insufficient for clang-cl C++: MSVC's C++
headers/libraries and runtime development files also need a supported source.

D-new: keep this an isolated option-A prototype and retain production MSVC
until the runtime, diagnostic and install gates below are complete.

The player-side dependency and the release builder are separate: release CI can
keep building the game-free app/wrapper with MSVC while the payload builds the
player's game with LLVM-MinGW. Migrating both is possible, but is not required
to eliminate Build Tools from a player's PC.

This branch is an **opt-in build prototype**. `setup/engine.py`, prerequisite
installation, release packaging and the Windows defaults are unchanged. The
parent gitlink pins the published, qualified toolkit TLS fix. No release or
game binary was published. Qualification uses this lane's independent saves
and serial games. The gameplay/performance evidence applies to the stated
v1.2.1 source base, not subsequent v1.2.2 runtime changes on main.

## Reproducible inputs

| Input | Version / SHA-256 |
|---|---|
| Native compiler | `llvm-mingw-20261117-ucrt-x86_64.zip`, LLVM 23.1.6 |
| Compiler archive | `4d002e330a0f703625aa5ccbc37e96f8f824413e163bfc7336774aabd2c3a412` |
| Standalone CMake | `cmake-3.31.6-windows-x86_64.zip` |
| CMake archive | `d163cd3ab4959b0a53fa8988f2ddbd2e6c501658201e6a154386bad9dbe4f836` |
| Standalone Ninja | `ninja-win.zip`, release v1.11.1 |
| Ninja archive | `524b344a1a9a55005eaf868d991e090ab8ce07fa109f1820d40e74642e289abc` |

Compiler download: <https://github.com/mstorsjo/llvm-mingw/releases/tag/20261117>.
Compiler SHA-256 was checked against GitHub's asset digest. CMake/Ninja hashes
above identify the actual official release archives used in this local trial.
The first runtime trial used VS's CMake/Ninja executables as build drivers;
subsequent app/source/fixture/full-game checks use the standalone copies above.
No VS developer environment supplies compiler headers, resource tools or link
libraries to those standalone checks. This host still has VS installed;
this is not a clean-Windows VM qualification.

The compiler archive is **191,082,415 bytes (182.2 MiB)**. Extracted inventory:
**9,069 files / 752,994,883 bytes (718.1 MiB)**, across multiple target
architectures and debugging/development tools. This exceeds the proposal's
rough 100 MB figure for the full prebuilt distribution. The subsequently tested
x64-only subset, including standalone CMake/Ninja and supplied notices, is
**83.3 MiB compressed / 331.8 MiB expanded**; its inventory and actual full-game
build are recorded below. This is a local measured prototype, not a shipped
payload. Measure peak disk use across downloaded, unpacked and staged update
copies during installer integration.

## Measured failures and prototype fixes

| Group | Original result | Prototype change / remaining concern |
|---|---|---|
| Runtime libraries | Default build succeeded: 334 Ninja actions | Existing MinGW portability work covers most of the original proposal |
| Game sources | Compile errors in two files | Match `LoadCursor` with `IDC_ARROW`'s selected encoding; select Windows 10 API declarations for `GetDpiForWindow` |
| App compiler flags | `/utf-8` interpreted as an input filename | Restrict that flag to MSVC; GNU Clang defaults to UTF-8 |
| Resource compiler | Failed creating a temporary file in the inherited temp location | Give the experiment its own writable TMP/TEMP, restore environment afterwards |
| Thread-local state | Clang warns and **ignores** `__declspec(thread)` in GNU mode | Select `HOST_TLS` by compiler; separate local toolkit fix for `NV_TLS` in `nv2a_pb_exec.c` |
| Native imports | Parent game still requests plain `xinput` | Select `xinput1_4` under MinGW, matching the toolkit; static libc++/unwind linkage |
| Arithmetic | GNU Windows branch lacks the POSIX compiler contract | Apply `-fno-strict-aliasing -fwrapv -ffp-contract=off` to lifted/game source |
| Application manifest | Direct `.manifest` source was absent from the linked app's resources | Embed it through `.rc` under MinGW; resource type 24 verified after the fix |
| Symbols | Existing Windows options are MSVC-only | Emit game CodeView/PDB and a map; actual crash/stack/map tooling remains a separate gate |

The generic toolkit fix was qualified in the isolated local worktree
`C:/Users/Vlad/code/defjam-toolchain-189-toolkit`, branch
`spike/windows-toolchain-189`, in `src/kernel/nv2a_pb_exec.c` (two inserted
preprocessor lines). It separates including Windows headers from selecting
MSVC's TLS spelling. It is now published as
[`274e6fb`](https://github.com/vyanhursky/xboxrecomp/commit/274e6fbd63de904562d73c960aad674ace2caf6a)
and pinned by the parent. Committing it did not change the qualified source
bytes. The initial runtime build passes
without this fix but has an ignored-TLS warning, which is not runtime safety.

Effort by group is small for the measured source changes: flags/linkage require
one game CMake branch and one app flag guard; Windows API declarations require
two cursor calls and two minimum-version definitions; TLS requires one host
qualifier and two toolkit preprocessor lines; manifest embedding requires the
shared resource helper/template. Diagnostic compatibility needed compatible
LLD map output, followed by live-process qualification. The larger follow-up is
installer integration and platform qualification, not a broad runtime rewrite.

## Validation ledger

Local evidence (ignored, never publish game bytes/binaries):

- `logs/toolchain/build-runtime.log`: original runtime build passed.
- `logs/toolchain/game-sources.log`: original game-side compile failures listed above.
- `logs/toolchain/build-app.log`: original app failures; `build-app-patched.log`
  and `logs/windows-toolchain-spike/app/`: patched app links successfully.
- `logs/toolchain/cpu-fixtures.json`: **7/7 fixture projects passed**:
  `fp_precision`, `stack_ops`, `mmx_integer`, `mmx_rounding`, `x87_trig`,
  `mmio_decode`, `input_xinput_imports`.
- Native host TLS isolation fixture: **passes LLVM-MinGW and MSVC**, using
  actual `host.h`, two Windows worker threads and the main thread.
- **33 Python tests passed / 2 skipped**: app-package/setup-contract,
  game-source-compiler helper and agent-instruction checks.
- Graphics fixtures: format/swizzle and state-object smoke pass. `d3d8_a8`
  fails 120 checks and `d3d8_gamma` fails 9 checks under **both** compilers
  with the same output. These are retained baseline failures, not green gates
  and not demonstrated compiler regressions. They ran before the initial PC
  reservation; later tests below use the owner's explicit gameplay handover.
- **Full game builds and links**, 442 Ninja actions, from a fresh 18,446-function
  analysis and lift (21 generated C files / approximately 67 MB). Standalone
  compiler/CMake/Ninja and the local toolkit TLS fix were used. Build identity
  verification passes (`pipeline-state.py verify-build --preset llvm-mingw-game`).
  EXE 35,715,584 bytes; PDB 36,315,136 bytes; map 6,874,541 bytes.
- The full game's PDB GUID and age match its executable; PDB contains public
  guest names including `sub_0021EB90` and runtime `xbox_VehMmioFault`. The game
  imports XINPUT1_4, XAudio2_8 and Windows system/UCRT libraries, without a
  separately deployed compiler runtime DLL. App imports were checked likewise.
- Data-only resource inspection (no entry points executed) verifies **byte-exact
  embedded manifests in both app and game**. `artifact-inspection.json` records it.
- **Initial diagnostic failure:** `sample-threads.py`'s existing map parser read
  **zero symbols / no preferred base** from the new LLD map. It needs adaptation
  or compatible linker output before map-dependent tooling is usable. PDB
  presence did not fix this. Evidence: `logs/toolchain/artifact-inspection.json`,
  `game-pe.txt`, `game-pdb-summary.txt`, `game-publics.txt`.
- The initial assessment did not include game boot, quick regression, replay,
  frame-time comparison, launcher UI, install/update/repair or clean-VM/offline
  acceptance. Authorized handover results are recorded below.
- The opt-in Windows CI workflow is implemented; remote execution evidence is
  recorded with the associated PR checks, separately from this local ledger.

## Repeating the build checks

Unpack the pinned UCRT toolchain, standalone CMake and Ninja into scratch.
From the checkout, run (substitute the three absolute local paths):

```powershell
./scripts/windows-toolchain-spike.ps1 -Mode runtime -ToolchainRoot <LLVM-root> -CMakePath <cmake.exe> -NinjaPath <ninja.exe>
./scripts/windows-toolchain-spike.ps1 -Mode game-sources -ToolchainRoot <LLVM-root> -CMakePath <cmake.exe> -NinjaPath <ninja.exe>
./scripts/windows-toolchain-spike.ps1 -Mode app -ToolchainRoot <LLVM-root> -CMakePath <cmake.exe> -NinjaPath <ninja.exe>
```

`game-sources` needs a checkout without generated guest code; its existing
helper refuses to overwrite a real lift. `game` mode requires a real fresh
lift; `-ToolkitDir` can select another isolated toolkit checkout. The default
submodule now contains the published fix. The script clears
inherited MSVC include/library/injected-flag variables, uses explicit tools,
and restores the environment. Full-game mode verifies the actual lift and
records/verifies the build identity, with an explicit toolkit path so an old
CMake cache cannot silently select another checkout. It only builds; it never launches an executable
or installs prerequisites. Logs go to `logs/windows-toolchain-spike/<mode>/`.
The manual workflow downloads a checksum-pinned compiler and runs the three
game-free modes plus the native TLS check, uploading logs only.

The full build used for the authorized gameplay handover is at
`build/llvm-mingw-game/defjam_recomp.exe`. Use only this lane's data root
`C:/Users/Vlad/code/defjam-toolchain-189-data` (independent save fixture, shared read-only
dump through its `extracted` junction), never another agent's save/session.
The initial quick and replay checks were run with the normal harness:

```powershell
$env:DEFJAM_DATA = 'C:/Users/Vlad/code/defjam-toolchain-189-data'
python scripts/regress.py --preset llvm-mingw-game --quick
python scripts/regress.py --preset llvm-mingw-game --only replay,repeat
```

These commands passed after the initial build-only assessment. Check that other lanes
have released the PC first; prepare the appropriate disposable save/baseline
fixtures before interpreting failures. No clean-VM installation claim is implied.

## Authorized handover qualification, 2026-11-22

The completed local qualifications and their exceptions are recorded below.

- Direct MS-style map output is available through
  `-Wl,--Xlink=/map:<path>`. This replaces the incompatible map; a separate raw
  `.lld.map` is retained. Existing parsers now read **42,550 symbols**, preferred
  base `0x140000000`, all eight guest-register TLS offsets and `_tls_index`.
  Evidence: `logs/toolchain/artifact-inspection-native-map.json`. No parser
  rewrite or extra post-link dependency was needed. Initial failure is retained above.
- A matching MSVC reference was built in `build/msvc-reference` from the same
  source/lift/toolkit, with verified build state, for controlled comparisons.
- Full parent unit suite: **2,782 passed / 59 skipped / 1 slow deselected**.
- LLVM app UI smoke: actual first setup screen captured from its backbuffer,
  visually inspected, scripted clean exit; scratch install/payload/user-base
  only, no installation started. `logs/toolchain/app-ui/result.json`.
- **Quick regression 5/5 passes**: unit, loading/title/menu goldens, normal legal
  and EA/THX/intro playback, and 116 seconds of fight at median 120 presents per
  two seconds. `logs/regress-20261122-182008.txt`, `logs/toolchain/quick.log`.
- The entire initial 5.24 GB independent save copy matches its pre-run hash
  manifest exactly. Subsequent tests use the harness's documented small-fixture
  pattern: only the same `UserData` (18 files, 150,916 bytes), with caches and
  partition images recreated in disposable runs. The initial complete copy is
  retained under this lane's data root, never moved from the owner's real data.
- **Live diagnostics pass** on the actual LLVM game: native stacks name lifted
  functions, guest-register inspection reads real per-thread register values,
  and thread sampling resolves map symbols. A process-memory-only deliberate
  null write at the named guest entry `sub_00021500` in the verified disposable
  child produced the normal handler's access-violation report and
  `in sub_00021500+0x2`. Saves restore exactly. The executable on disk was not
  modified; its normal build-state hash still verifies. The child used a minimal
  Windows/Python PATH without either compiler toolchain. Evidence:
  `logs/toolchain/game-diagnostics/result.json`, `native-stacks.txt`,
  `guest-regs.txt`, `sample-threads.txt`, `injection.json`, and
  `logs/run-20261122-182202.log.err`. This was an intentional diagnostic fault,
  not an observed gameplay failure.
- Replay, repeatability, remaining native/game coverage and performance
  comparisons were initially pending. Subsequent results:
  **replay and repeat 2/2 pass**: 80 records over 1,800 steps match the existing
  golden; both repeat runs are byte-identical and match that hash.
  `logs/regress-20261122-183304.txt`, `logs/toolchain/replay.log`.
- **Windows CI native matrix: 25/25 projects, 46 registered tests pass** under
  LLVM-MinGW. This includes kernel bridges, directory/object/dispatch/event and
  memory cases, USB, Windows guest layout, D3D readback/format/placement,
  NV2A, settings, input edges and game-side AC97 startup. The earlier seven CPU
  fixture projects and native TLS checks remain separate passing evidence.
  `logs/toolchain/native-matrix.json` and `native-<fixture>.log`.
- **Pruned tools measured and tested**: 6,834 files, 347,965,059 unpacked bytes
  (331.8 MiB), an 87,353,173-byte ZIP (83.3 MiB), including standalone CMake and
  Ninja. SHA-256 `6cf6404959d9f163c115c93ea079d45b295d8f934773e9feff58d036d57c4762`.
  This is a conservative x64 subset of the verified compiler archive, retaining
  compiler DLL closure, configs, Win32/C++ headers, all x64 import/static
  libraries, resource/PDB/map tooling and supplied notices. No binary was
  published. `logs/toolchain/pruned-tools-inventory.json` contains file hashes.
- The pruned copy builds C/C++, a static archive, Windows resources and PDB/map
  output from a source folder named `Café probe`, using a minimal PATH and no
  SDK include/library environment. Its program runs with only Windows on PATH,
  verifies native TLS and byte-correct Unicode filesystem access, and checks
  the UTF-8 process code page from its embedded manifest. An initial synthetic
  probe incorrectly tried to remove its own still-open input file; closing that
  stream fixed the probe without any product/toolchain change. Original and
  corrected logs are retained (`pruned-probe-run.log`,
  `pruned-probe-run-corrected.log`, `pruned-probe-build.log`).
- A **fresh full game build also passes with the pruned tools**, CMake and Ninja,
  minimal PATH, cleared MSVC environment, and already pinned local SDL/ImGui
  sources (no dependency download). It has verified build state in
  `build/llvm-pruned-game`. Its entire `.text` and `.tls` sections hash identically
  to the earlier qualified LLVM build: `logs/toolchain/pruned-code-comparison.json`.
  `configure-pruned-game.log` and `build-pruned-game.log` preserve the build.
- All **18,484 named guest entry points have distinct addresses** in the linked
  LLVM game; no identical-code folding loses guest identities.
  `logs/toolchain/guest-symbol-uniqueness.json`.
- Broad remaining gameplay and repeated performance comparisons are queued.
  Another active chat (`Review Xbox recompilation optimizations`, lane
  `defjam-runtime-stream2`) has repeatedly launched games. A local test runner
  waits before launches and invalidates overlapping runs by stopping **only its
  own children**; it never stops foreign lanes. Hardware overlap evidence is
  retained in `logs/toolchain/game-overlap.jsonl`, and remaining results in
  `logs/toolchain/remaining.log`. Pending/skipped checks are not passes.
- **Owner-directed wait:** on 2026-11-22 the owner asked to wait until that
  optimization chat finishes. The remaining driver was stopped, only this
  lane's game children were eligible for termination, and its outstanding save
  guard was recovered with `harness.py save-recover --restore`. The 18-file
  fixture matches `save-userdata-before.json` exactly; no active guard remains.
  The interrupted attempt recorded four non-applicable Windows UI skips and
  two invalidated rows: `skipintro` (startup child killed when the Photo Mode
  lane launched) and `ffa` (52 seconds of fight before a second Photo Mode
  overlap). These are retained environment-interference failures, **not compiler
  regressions or passes**. Rerun these and the uncompleted rows only after the
  requested PC handback; no valid earlier gate needs repetition.
- Another lane briefly started a game after handover. Our regression parent
  was paused before it could launch a game, then resumed only after confirming
  the desktop/game was idle. No performance measurement overlaps that run.
- **Resumed broad game suite: 12/13 checks pass**. Startup/skip-intro (five
  cases), FFA, four-minute Terrordome, combat, two-pad versus, Story intro,
  crib, gym movie, three boots, French, English subtitles and rapid 20 ms input
  with late refresh off/on pass. Combat has 28/28 assertions; versus 27/27,
  including PCM/audio, pacing, memory and exact fixture/save restoration.
  French menu and English subtitle captures were visually inspected.
  `logs/regress-20261122-221913.txt`, `logs/toolchain/remaining-resumed.log`.
- **Visual exception, aligned with closed issue #181:** the local images come
  from `<data>/test-baselines/story-tour-v1/manifest.json`, approved on October 6
  for v0.2.3. The first automatic fixture used current profiles (15/82 moves,
  85 development points) instead of the baseline's curated `vy2-hour-v1`
  profile (20/82, 465 points); that failure is retained. The exact six-file
  curated fixture was then copied into this lane and tested with **both**
  compilers. Both still fail the same two old Learn Moves comparisons (2/4
  historical comparisons pass). These are row-background differences already
  covered by [issue #181's owner closure](https://github.com/vyanhursky/DefJamFFNY-recomp/issues/181#issuecomment-7083129115):
  the Xbox reference contains grey LOCKED backgrounds, so their presence needs
  no rendering fix. That reference does not establish exact shade/opacity.
  The owner also accepted the shown current screenshot in this conversation.
  No approved image, threshold or mask was changed.
- **Direct compiler visual comparison: all three captures are byte-identical**
  (crib, Learn Moves list and movie preview), hence MAE and changed fraction
  are zero for all four comparison variants. This is evidence of compiler
  equivalence, not a reclassification of the stale historical goldens.
  `logs/scenarios/regress-visual-20261122-222042/` (MSVC),
  `regress-visual-20261122-222225/` (LLVM),
  `logs/toolchain/compiler-visual-comparison/comparison.json`.
- **Real game Unicode paths pass:** the verified executable launched through
  `build/Café LLVM` with independent `DEFJAM_DATA=…/Café data` and matched the
  existing main-menu golden. `logs/toolchain/unicode-game-result.json`.
- **Toolkit Python/compiled-C suite under LLVM: 851 passed, 134 subtests
  passed, one skipped**, in 26.81 seconds. No `cl` was on PATH; the shared
  compiled-fixture selector resolved this LLVM-MinGW `clang.exe`. The skip is
  `test_fpdiff`, which requires a separate 32-bit MSVC oracle; it is not counted
  as passing. `logs/toolchain/toolkit-llvm.log`.
- **Owner-authorized #181 baseline refresh completed:** the two Learn Moves
  images and hashes were replaced in the canonical data folder and this lane,
  using the already reviewed, byte-identical MSVC/LLVM captures. Previous
  images/manifest are preserved under
  `<data>/test-baselines/archive/story-tour-v1-before-181-refresh-20261123-150004`.
  The crib image, all thresholds and masks remain unchanged. Each manifest now
  pins a co-located six-file profile snapshot by content fingerprint, and
  `regress.py` selects it instead of changing live profiles. Explicit fixture
  overrides and older manifests retain their behavior; modified snapshots fail
  preflight. **86 focused unit tests pass** (scenario evidence and agent
  instructions, including the two new fixture-selection negative controls).
  No further visual check or game run was performed after the owner's request
  to stop them. Hash/fixture verification only:
  `logs/toolchain/baseline-refresh-181.json`. Artwork and saves stay local.

## Parallel startup path issue and resolution

The deliberately aliased scratch layout (`Café tools`, `Café DefJam 189` and
`Café build`) configured successfully and built serially, but two parallel
attempts stalled compiler children at startup. Process inspection/termination
also stalled; later host restarts cleared the children. These attempts remain
failures, not timeouts rewritten as successful builds. The underlying Windows
startup/alias interaction was not diagnosed at kernel level.

Controlled isolation retained the Unicode source alias and output paths:

| Compiler/tool layout | Four-way parallel build and executable |
|---|---|
| Physical ASCII tool directory | pass |
| Physical Unicode tool directory, complete pruned copy | pass |
| Original aliased compiler/CMake/Ninja paths, compiler root normalized | pass |

`file(REAL_PATH ...)` in the toolchain now resolves the compiler directory
before selecting the compiler, resource and archive programs. This avoids
launching them through a junction prefix. The exact previously failing layout
passes after that change; ordinary Unicode directories are supported by the
measured test. This is a tested workaround for the observed layout, not a claim
that all Windows loader causes are understood.

The new game-free `tests/windows_toolchain_paths` project also passes locally:
parallel C/C++/resource compilation, static archive, Windows API imports,
PDB/MS map, actual host TLS isolation and manifest-driven UTF-8 file access.
It uses the actual shared resource helper; manifest changes are explicit build
dependencies. The Windows CI workflow repeats this through Unicode/junction
source and tool paths and asserts the generated compiler path is physical.
No screenshot, device playback or game data is involved.

Evidence: `logs/toolchain/path-canonical-ascii/`, `path-physical-unicode/`,
`path-original-alias-normalized/`, `path-ci-fixture-normalized/`; each retains
commands, timings, exit status and logs. Original failed probe logs remain in
`unicode-tools-*`. Both qualified full-game build identities still verify;
the path normalization does not change their already physical compiler paths,
compiler options or game executable bytes. Earlier gameplay and performance
evidence is retained without another full regression.

The final public game-build command was also exercised with the qualified
checkout and completed with **no compilation needed**, then recorded and
verified its build identity. Before/after `.text`, `.tls` and `.rsrc` section
hashes are identical (`logs/toolchain/qualified-sections-{before,after}.json`).
The new path fixture passes CTest 1/1. The source publication-policy check
passes for 1,018 tracked files, with no build output, game data, save snapshots
or screenshots staged. The baseline fixture selection and agent-instruction
tests pass 86/86. These focused checks cover the final build-script/CI changes;
no new gameplay or visual run was made.

## Controlled performance comparison

Six solo Power Plant Free For All runs completed with no faults and exact save
restoration: MSVC, LLVM, LLVM, MSVC, MSVC, LLVM. Both builds use the same source,
fresh lift, toolkit fix, saved profiles, fixed input and RNG seed `20261006`,
four-fighter roster, stock textures, 16:9, render scale 2 and vsync. Venue 7 was
selected before `StartGame`, and the Power Plant asset `V2BG_03A` was observed.
This is the Power Plant FFA route, not a claim of a Story campaign benchmark.
There were no screenshot captures in the measured intervals, no foreign game
overlap, and no compiler/build processes observed in start/periodic checks.

Every run is reanalyzed from retained raw frame records using **15–65 seconds
after observed match start**. The initial proposed 15–75-second window was
truncated by the run stop; the common 50-second window was chosen after only
the first MSVC run, before comparing LLVM. All six cover the whole window,
contain at least 2,900 frames, and have identical observed roster/start state
and no match boundary in the window. Original interim results are retained.

Values below are the median of three per-run values; brackets show their range.
Executor busy time is the median of the native executor's approximately
two-second reporting-window medians contained in the measurement interval.

| Metric | MSVC 19.29 | LLVM-MinGW / Clang 23.1.6 |
|---|---:|---:|
| Median frame interval (ms) | 16.666 | 16.666 |
| p95 frame interval (ms) | 16.717 [16.708–16.723] | 16.720 [16.704–16.721] |
| p99 frame interval (ms) | 16.814 [16.750–16.819] | 16.797 [16.733–16.929] |
| 1% low (fps) | 59.12 [58.97–59.39] | 59.02 [58.79–59.70] |
| Executor busy median (ms) | 5.410 [5.240–5.445] | 4.690 [4.620–4.715] |

Both hold the 60 fps cap with similar frame pacing. LLVM's executor busy metric
is **13.3% lower** here, suggesting CPU headroom; it is not a 13.3% overall fps
claim. One fast PC does not establish slower CPU performance or every venue.
The reference compiler is installed VS 2019/MSVC 19.29, not the latest VS 2022.
No controlled clean-build time or peak-build-memory comparison was performed.

Host: Windows 11 Pro `10.0.26200`, Core i7-13700K (16 cores / 24 logical),
32 GB RAM, RTX 4070 Ti SUPER, NVIDIA driver `32.0.16.1088`. Evidence:
`logs/toolchain/benchmark/comparison-50s.json` (method, identities, coverage,
per-run statistics and executor windows), original `results.json`, retained
`frames.csv` / session metadata, and `benchmark-driver.log`.

## Remaining gates before changing Setup

1. Review the opt-in spike and run its Windows CI job remotely. Local game,
   diagnostic, path, fixture and performance qualifications are complete with
   the retained historical exceptions above; no production cutover is implied.
2. Keep the generic TLS fix pinned to its published fork commit when integrating
   this PR with later toolkit/runtime changes; qualify those changes on their
   actual release candidate rather than claiming the older game evidence anew.
3. Implement payload toolchain selection in engine and app preflight, toolchain
   fingerprints/cache invalidation, staging, package inventory and notices.
   Existing Windows policy rejects top-level `tools/`; staging currently copies
   Windows `source/` and `python/`. Cover first transition and historical releases.
4. Run scratch non-admin/offline install, repair, update, cancellation/rollback
   and a clean Windows 10/11 VM with no VS/SDK/compiler on PATH. Audit imports
   of the packaged compiler and resulting game, plus compressed/expanded size,
   entry limits and peak disk use. Preserve game-free release asset checks and
   audit the final redistributed notices, including Ninja's separate license.
5. Broaden performance/manual acceptance beyond this fast Windows 11 PC before
   a default cutover. Physical-controller feel and audible quality were not
   independently judged by a human; scripted input/PCM checks are separate
   evidence. Include slower CPUs and a current MSVC reference, and collect
   clean-build time and peak memory during actual installer trials.

The payoff is worthwhile: removing a multi-GB prerequisite installer, elevation
and possible reboot directly improves first-run setup. The required remaining
work is an installer/toolchain qualification project, not just changing a CMake
compiler flag. Keep MSVC available until those gates pass.
