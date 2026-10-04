# Public CI and source-release readiness review

The peer review's compiler-guard finding below is closed: the runner validates
normalized helper SHA-256 `c33ecc8c573b4690df4b454ace87c99c57f8910323bb0860a8ee6871a6697a1b`
before replacement. A synthetic changed-helper case proves fail-closed behavior.
Project tests now pass 92/92 under MSVC; the two disputed cases and an existing
negative control pass 3/3 with `cl`. Hosted CI revalidation passed 7/7,
with 533 toolkit tests and 107 subtests passing (one skipped). The merged-main
CI also passed 7/7. Private v0.1.0 release workflow passed 9/9 and created
a draft with zero uploaded assets; it remains unpublished. Public snapshot
CI and publication await the repository transition approval.

## Implementation and first hosted-run finding

Vlad selected v0.1.0. The prepared workflow adds reusable CI, four registered
Release native-fixture projects and tag-checked source Release drafts. Initial
hosted run `37220447054` passed 6/7 jobs: hygiene, project tests and all four native
projects. Runtime Release build passed, but the CPU helper selected Clang from
the runner rather than MSVC: 531 tests and 107 subtests passed, one skipped, two
failed. One NEG32 join case disagreed under Clang optimization; a switch fixture
also lacked a PUSH32 declaration under Clang's C rules. This is recorded, not
silently excluded or classified as game parity evidence.

The parent now uses `scripts/test-toolkit-msvc.py` to select `cl` for the shared
fixture helper without altering sources, assertions, optimization or skip gates.
It validates a reviewed SHA-256 of the normalized helper source and fails on a
different helper before replacement. The port and release are MSVC-only;
Clang portability remains a documented limitation. No toolkit pin, production
runtime/lifter code or accepted game build was changed for this CI correction.

2026-10-04. Bounded source review. Read AGENTS.md, current status in PROGRESS.md, CI/CMake files, env/build/extract/analyze/recomp/run/pipeline scripts, setup documentation and relevant fixture projects. No source/workflow edits, builds, tests, game runs, generated-code reads or publication. This report is the only write. The version/tag decision remains with Vlad; CMake currently declares 0.1.0 but that does not approve a v0.1.0 release.

## Findings that matter before publication

1. **The game Release preset is intentionally RelWithDebInfo.** [CMakePresets.json:36](C:/Users/Vlad/code/defjam-recomp/CMakePresets.json:36) selects the optimized configuration accepted in Vlad's Release play-test; ci-runtime-only already selects exact Release at [line 52](C:/Users/Vlad/code/defjam-recomp/CMakePresets.json:52). The main agent's implementation decision is to retain that game preset and its build certificate, while using exact Release for hosted runtime/fixture gates. Default build/run invocations still select Debug ([build.ps1:4](C:/Users/Vlad/code/defjam-recomp/scripts/build.ps1:4), [run.ps1:5](C:/Users/Vlad/code/defjam-recomp/scripts/run.ps1:5)); make the public quick start explicitly use win-x64-release. Changing CMake presets would invalidate the existing [build input hashes](C:/Users/Vlad/code/defjam-recomp/scripts/pipeline-state.py:145), so do not rename/reconfigure the accepted local build merely for CI naming consistency.

2. **Current root CTest has no registered tests.** The parent and toolkit root CMake files do not enable testing. The imported [d3d8_smoke project](C:/Users/Vlad/code/defjam-recomp/tools/xboxrecomp/tests/d3d8_smoke/CMakeLists.txt:6) builds gamma/format/state/A8 executables but has no add_test calls. Kernel/USB/VSH fixtures are separate projects that enable/register their own tests, and current CI does not configure them. Therefore the [root CTest step](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:51) is a source-established coverage gap, even though its failure suppression was removed. Add actual test registration or configure the existing standalone fixture projects; do not treat a successful empty invocation as a test pass. CMake documents that [enable_testing belongs at the top level](https://cmake.org/cmake/help/latest/command/enable_testing.html). Use --no-tests=error with hosted CMake 3.26+; for the supported local 3.20, verify the discovered count before running CTest instead ([CTest documentation](https://cmake.org/cmake/help/latest/manual/ctest.1.html)).

3. **CI does not test the toolkit Python lifter/disassembler.** The [Ubuntu job](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:22) checks out no submodule and runs only parent tests/unit. This is valid for its existing synthetic tests, but does not exercise the consolidated CPU fixes. Add a separate recursive checkout/capstone/pytest job for the pinned toolkit's tools/recomp and tools/disasm suites. Keep the working Windows native save-compatibility gate and real CTest failures fatal.

4. **There is no tagged release workflow or artifact verification.** Current CI triggers only main pushes and pull requests ([ci.yml:4](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:4)); tracked workflow inventory contains only ci.yml. A tag must run validation against its own commit before publishing a release, rather than relying on a green run from another main commit.

5. **Hygiene is narrower than the requested artifact policy.** [ci.yml:17](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:17) checks selected asset/archive suffixes and generated C in parent Git entries, but not binaries/logs/saves or submodule contents. The pinned toolkit tracks tools/conformance/test.xbe (read-only Git filename inventory confirmed). It is an authored conformance fixture, but an artifact advertised as source-only should exclude it as a binary XBE. Build a package from approved tracked source entries, never by recursively archiving the dirty checkout or relying on .gitignore alone.

## Minimum hosted Release matrix

| Job | Platform/configuration | Meaningful gate |
|---|---|---|
| Hygiene/package policy | Ubuntu, Python 3.12 | Tracked parent policy plus verified package inventory; no EA/generated/build/save content |
| Parent Python tests | Ubuntu, Python 3.12 | Existing synthetic tests/unit; compiler-backed save tests must execute rather than silently skip |
| Toolkit Python tests | Ubuntu or Windows with native compiler, Python 3.12 | Recursive checkout of exact gitlink; tools/recomp and tools/disasm pytest suites |
| Runtime libraries | Windows x64/MSVC, Release | Existing ci-runtime-only preset, explicit DEFJAM_BUILD_GAME=OFF; default targets build all real libraries |
| Synthetic runtime fixtures | Windows x64/MSVC, Release | Matrix: nv2a_vsh (CPU + WARP adapter), usb_transfer, kernel_bridge and kernel_directory; add audio/physical-address/object-path fixtures already used for rebase validation |
| Tagged public source checkout | Windows x64/MSVC, Release | Fresh recursive checkout of tag and published gitlink, runtime-only build without game data; automatic archive inventory verified separately |

Use isolated build directories per matrix row and fail-fast false so all diagnostics are collected. The standalone fixtures have their own project()/runtime inclusion; do not blindly add all of them below the parent's already-added toolkit because several would add the same runtime twice. Their existing standalone configure/build/CTest commands are the smallest integration.

The first native runtime matrix should remain Windows, matching the public port's supported host. An Ubuntu full-runtime row additionally requires SDL2/libepoxy/pkg-config ([D3D CMake:25](C:/Users/Vlad/code/defjam-recomp/tools/xboxrecomp/src/d3d/CMakeLists.txt:25)) and does not validate the Windows D3D11 path. Do not imply native Linux game readiness from the existing Ubuntu Python job.

## Tagged source-only release design

Trigger on approved version tags (for example v* after the version is decided). Check out the tag and exact recursive submodule commit. Run the same hygiene, parent/toolkit tests and Release gates at that tag. The publication job needs all validation jobs, runs only for tag pushes, and receives contents:write; ordinary test jobs retain contents:read. GitHub documents the release endpoint's [Contents write permission](https://docs.github.com/en/rest/releases/releases#create-a-release). Guard tag syntax, project-version agreement, nonempty release notes and main ancestry. Tag the intended published main commit so workflow changes do not unexpectedly differ from the default branch's release context.

The selected implementation is a source-only GitHub Release using its automatic source archives, with no uploaded game executable, generated code, runtime binaries, logs or saves. GitHub documents that these are [git archive source snapshots](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives). They omit the submodule contents and Git metadata, so release notes must explicitly say to clone the tagged public repository recursively for a complete build tree. This is a documented source snapshot, not a self-contained game/build package. Record the parent tag/commit and published toolkit gitlink in the release notes. No custom ZIP/checksum asset is required by this selected scope.

Meaningful archive verification still matters: inspect the exact tagged parent tree and a locally generated source archive for forbidden paths/suffixes, binaries, lifted C, unexpected nested archives, missing README/license/setup files and unexpected symlink entries. Parent Git records only the toolkit gitlink, so the toolkit's conformance XBE is not inside that parent automatic archive. The recursive CI checkout must independently prove the pinned public toolkit revision can be fetched and its runtime/tests build. Download and inspect the resulting GitHub source archive when validating the release end to end; do not claim it includes dependencies. If a self-contained source bundle is added later, it will need its own sanitized toolkit inventory, license checks, content manifest and clean-extraction build gate.

The main agent additionally identified historical copied guest snippets as a public-history blocker. Preserve the private history and prepare a clean public source snapshot instead of assuming current-tree hygiene proves all old commits safe. This audit did not inspect or rewrite history.

## Exact bounded fixture recipe and prior timing evidence

Use MSVC x64 activation plus Ninja and run these commands from the parent root, with fixture substituted by nv2a_vsh, usb_transfer, kernel_bridge or kernel_directory:

```powershell
cmake -S tools/xboxrecomp/tests/<fixture> -B build/ci-<fixture> -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build/ci-<fixture>
ctest --test-dir build/ci-<fixture> --output-on-failure --no-tests=error
```

These existing standalone projects provide nonempty registered CTest sets without rewriting the published toolkit:

| Fixture directory | Registered tests | Prior local Release execution time |
|---|---|---:|
| tests/nv2a_vsh | nv2a-vsh-epilogue; nv2a-vsh-adapter-warp | 0.02 s; 0.35 s; 0.37 s total |
| tests/usb_transfer | usb-transfers | 0.04 s |
| tests/kernel_bridge | kernel_bridge_test | 0.03 s in prior aggregate fixture run |
| tests/kernel_directory | kernel_directory_test | 0.03 s in prior aggregate fixture run |

Read evidence: [VSH results](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/vsh-test-results.txt), [USB results](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/usb-test-results.txt), [nine runtime results](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/runtime-fixtures-results.txt). All three preserved CMakeCache files independently confirm Release with /O2 /Ob2 /DNDEBUG. These are test execution times, not configure/build durations or hosted-runner estimates. The nine runtime tests took 0.29 s total in that aggregate project; standalone CTest names differ from its shortened names.

The [WARP adapter](C:/Users/Vlad/code/defjam-recomp/tools/xboxrecomp/tests/nv2a_vsh/adapter_test.c:89) requests D3D_DRIVER_TYPE_WARP with device flags zero. It creates no window, needs no physical GPU or debug-layer installation, and requires no special environment variables. Failure to create WARP is a test failure, not an accepted skip. Bridge/directory CMake set RECOMP_GPU_PREEMPT=0 themselves. USB disables host pad input, removes minimum hold time and supplies seconds-format four-pad input internally. Release checks remain meaningful: USB undefines NDEBUG; VSH/WARP/bridge/directory use explicit failure/return checks.

For the toolkit CPU/disassembler gate, use working-directory tools/xboxrecomp and run:

```text
python -m pip install capstone pytest
python -m pytest -q -p no:cacheprovider tools/recomp tools/disasm
```

No game input or additional compiler installation is required. With the existing Windows MSVC activation, the shared [compiled fixture helper](C:/Users/Vlad/code/defjam-recomp/tools/xboxrecomp/tools/recomp/test_lifter_result_clobber.py:76) falls back to cl and uses /O2 /Fe. Some older cases depend on another compiler and can skip; print/report skip counts. The historical full CPU run reported 26 such skips. Parent tests also need pyxbe; toolkit CPU/disasm tests use capstone/pytest and the checked-out toolkit. These commands are recommendations, not execution by this audit.

## Clean-clone setup gaps

- [README.md:17](C:/Users/Vlad/code/defjam-recomp/README.md:17) promises Python 3.10+, but pipeline-state uses hashlib.file_digest, requiring Python 3.11+. Recommend Python 3.12+ in the supported setup instructions. Include pytest for validation.
- [env.ps1:16](C:/Users/Vlad/code/defjam-recomp/scripts/env.ps1:16), [extract-disc.ps1:8](C:/Users/Vlad/code/defjam-recomp/scripts/extract-disc.ps1:8) and analyze defaults use Vlad's absolute directory. Set an explicit user-chosen external DEFJAM_DATA in the public instructions and/or derive a portable default; document that it must stay outside the repo.
- Extraction requires a separately installed extract-xiso.exe at a very specific external path ([extract-disc.ps1:12](C:/Users/Vlad/code/defjam-recomp/scripts/extract-disc.ps1:12)) and 7-Zip for archive input. Expose a direct extractor path or document the installation exactly. Check each native extractor/verifier exit status so a failed operation cannot appear successful because earlier output already exists.
- README omits the game junction required by [run.ps1:12](C:/Users/Vlad/code/defjam-recomp/scripts/run.ps1:12). docs/03-workflows includes it, but with Vlad's hard-coded path. Use a PowerShell junction instruction derived from the selected external data root. Analysis itself correctly reads DataDir/extracted/default.xbe; it does not require that junction.
- The C++ workload alone does not document the CMake/Ninja installation assumed by [env.ps1:13](C:/Users/Vlad/code/defjam-recomp/scripts/env.ps1:13). Specify the Visual Studio CMake tools component or separate CMake/Ninja installations, and validate availability.
- README's no-renderer status and roadmap are obsolete ([README.md:6](C:/Users/Vlad/code/defjam-recomp/README.md:6)); replace them with the accepted playable Windows status, supported dump requirements, Release build steps, known backlog and source-only release instructions. The fork pin already supports recursive clean clones without historical patch replay.

## Ten-line handoff summary

1. Keep all hosted gates game-data-free; distribute only source/tools/docs/licenses.
2. ci-runtime-only is already Release; retain the accepted optimized RelWithDebInfo game preset.
3. Use win-x64-release explicitly for the local game; do not disturb its current certificate for CI naming.
4. Current root CTest registers no tests; make discovery nonempty and failures fatal.
5. Add the pinned toolkit's synthetic CPU/disassembler pytest suites to CI.
6. Run existing Windows native save tests plus standalone Release GPU/USB/kernel fixtures.
7. Create a tag-triggered publication job gated on validation of the same tagged commit.
8. Selected release uses automatic source archives; clearly document recursive cloning for the omitted toolkit.
9. Verify tagged parent/archive hygiene and exact public gitlink fetch/build; preserve private history separately.
10. Fix Python/tool/data-root/junction/README setup gaps; v0.1.0 remains unapproved until Vlad answers.

## MSVC CPU-fixture selector follow-up, 2026-10-04

Bounded read-only review of the new parent [test-toolkit-msvc.py](C:/Users/Vlad/code/defjam-recomp/scripts/test-toolkit-msvc.py) and [CI invocation](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:60). No source edits, tests, builds or game runs. The parent reports hosted run 37220447054 passed six of seven jobs, including every native Release fixture; the CPU job reported 531 passed, 107 subtests, one skip and two failures when the shared helper selected its hard-coded Windows Clang. Those hosted counts/failures were not independently measured by this reviewer.

**Disposition: the current replacement is appropriately scoped to the supported MSVC gate and does not suppress semantic assertions. One fail-on-change guard is weaker than stated.**

- [Lines 20–29](C:/Users/Vlad/code/defjam-recomp/scripts/test-toolkit-msvc.py:20) identify helper modules by their exact resolved source path and replace only their _cc selector. No collection items are deleted or changed, and no skip/xfail markers, assertion changes, expected-result changes or generated C edits are introduced. Matching duplicate import aliases by file path avoids relying on a single pytest module name.
- The existing [shared builder](C:/Users/Vlad/code/defjam-recomp/tools/xboxrecomp/tools/recomp/test_lifter_result_clobber.py:130) looks up _cc through its own module globals on each call. Tests importing _build_and_run therefore observe the replacement while retaining the original compile/execute path. Its /O2, compiler-success assertion and returned process status remain intact. The wrapper returns pytest.main's exit code and raises SystemExit with it; failures are not converted to success.
- [Dynamic mixed-join predicates](C:/Users/Vlad/code/defjam-recomp/tools/xboxrecomp/tools/recomp/test_dynamic_flags.py:70) still compare the compiled results with independent expected answers and assert process success. [Switch fixtures](C:/Users/Vlad/code/defjam-recomp/tools/xboxrecomp/tools/recomp/test_switch_slot_fallback.py:10) retain value/index/outside-slot/frame checks. Selecting another compiler changes the result under test, not those expected answers.
- **P2 guard weakness:** [lines 27–28](C:/Users/Vlad/code/defjam-recomp/scripts/test-toolkit-msvc.py:27) reject a missing/non-callable _cc only. A future callable with changed selection semantics/signature, or a changed _build_and_run compiler contract, passes this check and is overwritten. This does not satisfy the stated intent to error on a changed helper. Minimal remedy: validate a reviewed source fingerprint, or explicit fingerprints/contracts for the selector and builder, before replacing the selector. Update that expectation only when deliberately reviewing a toolkit pin change. Focused synthetic checks should cover missing/changed callable refusal and propagation of an intentional pytest failure.
- [CI](C:/Users/Vlad/code/defjam-recomp/.github/workflows/ci.yml:40) activates MSVC x64 before invoking the wrapper; compiler absence and non-Windows execution fail early. The wrapper itself does not independently verify target architecture, but the present job does select x64 explicitly. Other compiler-selection helpers remain untouched, which is consistent with the declared narrow scope.

This is compiler-specific validation of the Windows port, not proof of compiler-independent lifted C. A passing MSVC run does not fix or disprove the reported optimized Clang NEG32/80000000 predicate mismatch or the switch fixture's undeclared PUSH32 compile failure. Keep those observations recorded as separate cross-compiler/fixture issues instead of calling them false positives. The main agent owns the local/hosted rerun and acceptance evidence.

### Ten-line selector summary

1. The wrapper selects cl only for modules matching the exact shared-helper path.
2. It leaves pytest's collected item set and semantic assertions unchanged.
3. Imported builder aliases continue using the helper's replaced global selector.
4. Original /O2 compilation and compiler-success assertions remain active.
5. Compiled predicate, switch mapping and guest-frame expectations remain active.
6. Pytest failure exit codes propagate to the process and hosted job.
7. Present CI explicitly activates MSVC x64 and recursively checks out the toolkit.
8. Missing compiler/helper errors are fatal; other compiler helpers are untouched.
9. The changed-helper guard checks callability only; add a reviewed fingerprint/contract.
10. MSVC success would validate the supported compiler, not resolve the two Clang failures.
