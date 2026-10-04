# Toolkit rebase pipeline safeguards review

2026-10-03. Bounded source review of the current safeguard diff in `scripts/pipeline-state.py`, `scripts/{analyze,recomp,build,run}.ps1`, `scripts/harness.py`, `scripts/regress.py`, and `tests/unit/test_harness.py`. No source edits, tests, builds, or game runs were performed by this reviewer. Only this report was written. The main agent owns measurements and fixes; its active regression uses an absolute disposable save root and frozen compiled sources.

## Remaining findings

### P1: analysis/build finalizers can certify inputs that did not produce their output

`scripts/pipeline-state.py:156-158` records analysis inputs only after the analysis subprocesses finish. Likewise `:163-166` records current build inputs after CMake finishes. Neither finalizer receives the input snapshot from the beginning of its stage. In contrast, staged lifting correctly snapshots inputs at `:96` and checks them again at `:107-108`.

For analysis, a seed/tool change after disassembly has consumed its input can be paired with the old analysis output in a new manifest. For builds, a runtime or game-source change after the compiler has consumed it can be paired with the earlier executable. `verify_analysis`/`verify_build` will subsequently accept those mismatched pairs because the finalizer recorded the new input hashes. This is a source-level race finding, not evidence that the frozen candidate currently running has encountered it.

Capture an analysis/build input snapshot before starting the subprocesses, require it when completing the stage, and reject publication if the end snapshot differs. Record the same original snapshot in the final manifest. Keep the old completed certificate invalid while a new build is pending. For analysis, the current wrapper invalidates its manifest before writing outputs (`scripts/analyze.ps1:17-37`), which fails closed on a subprocess error; it does **not** stage and preserve the complete previous analysis output directory.

Targeted test: simulate output produced for input A, mutate a seed or runtime source to B during the mocked stage, and assert completion refuses to write a completed manifest. Also verify a failed analysis stage cannot mint a fresh manifest from remaining old JSON files.

### P1: `record-build` can certify a leftover executable after runtime-only work

`scripts/pipeline-state.py:163-166` accepts any existing `build/<preset>/defjam_recomp.exe` and hashes it with the current inputs. It does not establish that the game target was part of the successful build, or reject `ci-runtime-only`. A leftover executable plus a runtime-only build can therefore be blessed by invoking this finalizer; its byte hash establishes identity, not build provenance.

The normal wrapper already has useful protection: `scripts/build.ps1:11-17,24-30` explicitly selects game mode for normal presets, invalidates their old manifest, and skips recording for `ci-runtime-only`. Do not remove that protection. Its build invocation at `:26` still builds the preset's default target set. The root CMake also has a runtime-only fallback when the dispatcher is missing (`CMakeLists.txt:58-61`), so requesting `DEFJAM_BUILD_GAME=ON` alone is not proof that a game target exists.

For game builds, request `--target defjam_recomp` explicitly so a missing game target cannot produce a successful runtime-only build. Reject completion/verification for runtime-only presets and require the completed game-build context rather than allowing the finalizer to adopt an arbitrary leftover executable. Combine this with the start/end snapshot above. This avoids relying on a changed executable hash: a legitimate no-op build can leave identical bytes.

Targeted tests: leave an old executable in a runtime-only build folder and reject both certification and running; mock a successful runtime-only/default build with the game target absent and assert no game certificate is written; retain a valid unchanged-input no-op game build case.

### P2: lifter `ExtraArgs` can override the staged destination

`scripts/pipeline-state.py:101-104` places caller-supplied `extra` after the wrapper's `--gen-dir` and `--exclude-manual` arguments. The `scripts/recomp.ps1` interface continues to expose these extra arguments. A second `--gen-dir` selecting the live generated directory can make the translator write directly into it, after which the empty staging directory fails the completeness check at `:105-106`. The promised preservation of the previous generated set has then already been lost. A second manual-exclusion argument can likewise disconnect the recorded manual input from the file actually used.

Reject overrides of wrapper-owned destination/manual-input options before launching the translator, including their `--option=value` spelling. Continue allowing unrelated translator options. Retain the existing successful-exit, completeness, and unchanged-input checks before publication.

Targeted test: pass a conflicting generated destination/manual-input option and assert rejection occurs before the subprocess is invoked and before any live generated file changes. Existing `test_failed_lift_preserves_previous_set` only covers a subprocess that raises without writing to the live tree.

## Save/failure-policy findings addressed or handed to main

The first source snapshot had two fail-open backup checks. `trees_equal` inherited `filecmp.DEFAULT_IGNORES` and did not reject `common_funny`, so ignored names and file/directory shape mismatches could be accepted. Success metadata was also stored as `.restore-ok` inside the backed-up payload; a legitimate player file with that name was overwritten, and a failed/partial backup containing it could later be pruned. The current source now uses `ignore=[]`, rejects `common_funny`, and separates backup payload from external status metadata. Main reported 33 unit tests passing after these corrections; this reviewer checked the source and did not run them.

Two additional findings were delivered to main, which is implementing them:

- Normalize `DEFJAM_DATA` against the child's `REPO` working directory and reject/fill empty overrides. Otherwise a relative value protects the caller's save tree while the child writes a different one; an empty value makes the child use the runtime's local-app-data default while `SaveGuard` protects the external data root. See `harness.run_game` environment/guard setup and `src/main.c:605-614`.
- Count non-code ICALL skips as faults, separately from `[ICALL] Failed to resolve`. The other existing failure path emits `[ICALL] target ... is not code -- skipped ...` at `src/recomp_manual.c:627-630`. Any accepted baseline case needs an explicit exemption rather than exemption of the whole diagnostic form.

The normal completed-guard/launch-error path is correctly enclosed by `finally`: if `Popen` raises after entry, restoration still executes. A failed `__enter__` copy does not delete the original tree. Ordinary original absence is restored, and the revised cleanup handles a file replacing the save directory. Failed backups are excluded from the new success-marker pruning path. These observations need focused failure-injection tests, not another game run.

## Small remaining test set

Add a mocked launch failure after successful guard entry, checking original profiles **and caches** remain byte-identical; repeat with originally absent save roots. Inject a backup-copy failure before launch and a restore failure followed by four successful guards, checking the failed payload remains available. Cover relative/empty data roots and both ICALL diagnostic forms. Finish with the provenance, runtime-only certification, and conflicting-lifter-argument cases above. The current tests cover happy-path complete save restoration, original directory absence, subprocess lift failure, ordinary hash changes, shared faults, and missing route anchors; those are useful but do not establish the uncovered stage/provenance guarantees.

## Main-agent disposition, 2026-10-03 16:44

All source findings above have been addressed: analysis/build start and end input
snapshots; explicit game-target build; runtime-only configuration rejection;
protected lifter input/destination options, including abbreviated/equal spellings;
absolute/nonempty data roots; separate non-code ICALL failure count; exact save-tree
comparison and external backup status. Unit validation passes 46 tests
(`logs/rebase-work/pipeline-unit-tests.txt`), including launch failures for existing
and absent saves, profile/cache preservation, failed restore retention after four
successful runs, stage input mutation, runtime-only configuration and rejected
lifter overrides. These checks certify harness behavior; the candidate's active
game regression still has failures and is not accepted.

## Final actual-checkout validation

The subsequent switch and legacy-save repairs close the intermediate game
failures. Project tests pass 67/67 with MSVC; both freshly built presets have
complete certificates. Release `regress-20261003-191107.txt` and Debug
`regress-20261003-202026.txt` are 9/9, with 20/20 Debug boots and zero hangs/failures.
See `toolkit-rebase-acceptance.md` for final artifact/save evidence and the separate
owner play-test gate. These later results do not change the historical findings.
