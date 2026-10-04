# Handoffs, October 2026

## Superseded by public publication completion, 2026-10-04

## 7. Hand-off

### Public publication authorized, 2026-10-04
Vlad approved a fresh PUBLIC `vyanhursky/DefJamFFNY-recomp` (D58).
Keep `vyanhursky/DJFFNY-recomp` PRIVATE, with its original name/history.
Do not push private history to public. Local working game checkout remains
`C:/Users/Vlad/code/defjam-recomp`; clean public checkout is
`C:/Users/Vlad/code/DJFFNY-public-preview`. Accepted game binary/toolkit pin
`aa1a1b9` unchanged; no game runs/rebuilds for docs/release work.

README feedback applied: playable and FUN, owner reports over an hour of Story
Mode without additional graphical glitches, macOS/native Linux future roadmap,
removed fork-consolidation paragraph from What Comes Next. Root README/setup/
release links now target the approved public name. Screenshots and GIF are
explicit owner-approved D58 exceptions; the two exact SHA-256 fingerprints in
`scripts/check-source-tree.py` are the only permitted media. Matching
AGENTS/CLAUDE and contributor/release rules updated. Source archives include
these two README visuals; game executable/data/lifted code remain excluded.

Private CI/release proof: PR #2 merged at `43a2b07`; CI 7/7, Source release
`37221619994` 9/9, v0.1.0 private draft unpublished/zero uploaded assets.
Tests: project92, toolkit533 and107 subtests (one skip), saves19, all five
native CTest cases pass. MSVC-only; initial Clang failures documented.

Current next steps: test approved-media boundary and matching instructions,
commit/push private main, refresh one-root-commit public preview, verify no
private parent history and exact toolkit pin, create requested public repo,
push main, wait all seven CI jobs, push approved v0.1.0 tag, wait all nine
source-release jobs, inspect draft, publish source Release. Record URLs and
final results here in the same turn. No extra permission needed for this
approved publication. Each upstream PR still requires separate approval.

History audit/redaction evidence: `docs/research/publication-history-audit.md`;
132 Markdown guest-code fences redacted in 21 current documents, historical
copies retained privately. Ignored snapshot manifest/archive in
`logs/rebase-work/`; it records exact hashes and public-source inventory.

### Standing gameplay backlog
Two-pad gameplay, long-session memory, rare `sub_001A3310` crash/silent boot,
loading bar, black profile thumbnails, Blazin' film grain and half-pixel alignment.
Next feature work: agree M6 PC slice, then M5 Proton and M9 macOS.

## Superseded by owner publication approval, 2026-10-04

## 7. Hand-off

### Public preview ready for approval, 2026-10-04
Rebase accepted (D56); accepted optimized game build and toolkit `aa1a1b9`
remain unchanged. No game run or rebuild during this documentation/CI work.
Vlad selected v0.1.0 and supplied Mercenaries/Burnout 3 README examples.
README, portable setup, docs index, known issues, contribution/release guides
and release notes are complete. Milestone definitions remain unchanged.

- Private PR #2 merged at `43a2b079f0ae8c51f71f34671b4c3d2c0bf04176`.
  PR CI `37221395036` and merged-main CI `37221615496` both pass 7/7.
  Hosted project tests 92/92; toolkit CPU/disassembly tests 533 passed,
  1 skipped and 107 subtests passed; native save cases 19/19 and all four
  Release fixture projects pass (five registered CTest targets).
- Private annotated v0.1.0 points to that merge. Source release workflow
  `37221619994` passes 9/9, including exact-tag/version/main ancestry policy,
  reusable CI and draft creation. Release remains PRIVATE and DRAFT, with
  zero uploaded assets and no publishedAt. Do not publish this old-history tag.
- History audit: 251 original reachable commits / 697 UTF-8 blobs at the
  audited base. No detected secrets or binary assets; copied guest bodies
  and disassembly existed inside Markdown. 132 mapped fences in 21 current
  docs have been redacted, retaining surrounding findings. Old blobs remain.
- Owner approval is still required for the proposed transition: rename the
  original PRIVATE repository to `DJFFNY-recomp-history`, create fresh PUBLIC
  `DJFFNY-recomp` from the reviewed clean snapshot, then publish a source-only
  v0.1.0 after its own CI succeeds. Never make the old history public.
  No rename/new public repository/public Release has occurred.
- Unpublished preview: `C:/Users/Vlad/code/DJFFNY-public-preview`, one root
  commit, no remote, exact public toolkit pin, no original parent history.
  Review `README.md` there. Ignored archive/manifest:
  `logs/rebase-work/public-source-preview-v0.1.0.zip` and
  `logs/rebase-work/public-preview-manifest.json`; manifest carries exact
  preview/source SHA, archive hash and file inventory. Refresh from final
  private documentation commit before asking approval. Its origin/main is
  only a local policy-test ref; public remote CI has not yet run.
- Supported compiler is MSVC. Initial hosted CPU helper chose Clang and
  exposed two documented failures. Reviewed helper fingerprint now selects
  cl without changing assertions, sources, optimization or skip gates;
  changed-helper synthetic test fails closed. Clang remains unsupported.
- Preserve local game data, saves, generated C, certificates and rollback
  refs. Public releases ship maintained source/tools/docs, never the game EXE.
  After approval, use a recursive clone for toolkit content, re-run public CI
  and source-release workflow, inspect draft and publish it. Update original
  and public remotes deliberately; keep private history available locally.
- Next feature work: agree M6 PC slice, then M5 Proton and M9 macOS.
  Every upstream PR or named batch still needs separate approval.

### Standing gameplay backlog
Two-pad gameplay, long-session memory, rare `sub_001A3310` crash/silent boot,
loading bar, black profile thumbnails, Blazin' film grain and half-pixel alignment.
Owner acceptance is bounded; keep these separate from release/doc cleanup.

## Superseded by private release validation, 2026-10-04

## 7. Hand-off

### Public source/docs and v0.1.0 preparation, 2026-10-04
Rebase accepted and merged (D56): private PR #1 at `c23b44a`, main CI 3/3 green.
Vlad reports perfect play, much better audio, smooth frames and no observed graphical
glitches. Closure docs published at `5bffcba`; toolkit remains clean `aa1a1b9`.

Current work is D57, before any upstream PR: public README/docs and working CI/Release.
Branch `public-readiness`. Vlad selected v0.1.0. New public guides lead with supported
play, portable build setup, known issues, credits and source-only release instructions.
The accepted game Release preset stays optimized RelWithDebInfo; no runtime source,
toolkit pin or build fingerprint changed. Hosted runtime/fixtures use actual Release.

- Audit: `docs/research/publication-history-audit.md`. 251 original reachable commits,
  697 UTF-8 blobs, no detected secrets/binary assets; copied guest bodies/disassembly
  existed inside Markdown. 132 mapped excerpts in 21 current docs are replaced with
  notices retaining surrounding findings. Original historical blobs remain reachable.
- Never change the original repository to public. Proposed final transition requires
  owner approval: retain it privately as `DJFFNY-recomp-history`, create a clean public
  `DJFFNY-recomp` from the sanitized source snapshot, publish v0.1.0 after CI.
  No history rewrite, rename or public repository creation has been done.
- Workflows: CI is reusable; source policy scans tracked paths/content; MSVC checks
  native saves, CPU/disassembly semantics and Release runtime. Four separate Release
  fixture projects register kernel bridge/directory, USB and VSH/WARP tests; empty
  suites fail. Tag workflow checks version/notes/exact tag/main ancestry, reuses CI
  and creates a source-only draft Release. Private CI and draft-release validation next.
- Local source checks: source policy has zero failures; 92 project
  tests pass under MSVC (25 focused source-release cases). Accepted Release build
  certificate verifies; actionlint 1.7.12 passes both workflows. Official
  actionlint archive checksum verified. Native save tests need MSVC in hosted CI.
- Initial expanded hosted CI `37220447054`: 6/7 jobs pass; all native Release
  fixtures and runtime build pass. Shared CPU helper chose Clang, exposing NEG32
  optimized flag behavior and a switch-fixture declaration failure. Select MSVC
  explicitly with a reviewed helper fingerprint; assertions, sources and /O2
  remain unchanged. Focused cases plus negative control pass 3/3. Clang remains
  unsupported and documented; hosted revalidation follows.
- Preserve ignored snapshot, generated C/build certificates, original saves and
  rollback refs. Do not rebuild or launch games for documentation/release changes.
  Clean export/synthetic Git validation is source-only and uses ignored scratch.
- Next after this publication work: agree M6 PC feature slice, then M5 Proton and
  M9 macOS. Every upstream PR or named batch still requires separate approval.

### Standing gameplay backlog
Two-pad gameplay, long-session memory, rare `sub_001A3310` crash/silent boot,
loading bar, black profile thumbnails, Blazin' film grain and half-pixel alignment.
Owner acceptance is bounded; keep these separate from the release/doc cleanup.

## Superseded by public release preparation, 2026-10-04

### Rebase accepted and merged, 2026-10-04
Vlad accepted the Release play-test: it plays perfectly to him, audio is much
better than before, frames are smooth and he observed no graphical glitches.
D56 closes the integration acceptance gate. Private PR
#1 (private development record) is merged at
`c23b44a51c11333017b94f47c7276aba8bb11b33`; local checkout is now main.
The launcher fix `c70f86d` passed 3/3 CI before merging. Merged-main
CI (private development record) is
also 3/3 green: hygiene, scripts/unit tests and Windows native save/runtime build.

- Toolkit fork: `vyanhursky/xboxrecomp`, branch `defjam/rebase-2026-10`, clean
  detached pin `aa1a1b91dea9fd266acb3a3fe51dfcec3b2e6bbc`. All 108 historical
  patches map to 15 published topics; replay is retired and the archive retained.
- Both final game regressions 9/9; Release fight 120/112 presents per 2 seconds,
  Debug 120/66; 20/20 Debug boots, zero hangs/failures. Extra routes 5/5, 13
  captures reviewed, nine PNGs byte-identical. Project tests 67; CPU suite 464
  passed / 26 existing skips / 57 compiled subtests; native runtime fixtures green.
  Full evidence and limits: `docs/research/toolkit-rebase-acceptance.md` and ledger.
- Correct upstream SHRD retained; read-only exact-metadata legacy save compatibility
  preserves old profile folders. Original save rehash stayed identical: 18 files /
  5,243,503,676 bytes. Manual play used the disposable snapshot `runtime-data` root.
- Fresh-shell launcher now supplies absent vblank/push-buffer/D3D11/USB defaults.
  Windows PowerShell 5.1 real-window/render/controller verification:
  `logs/run-20261004-094353.log.err`. Use `scripts/run.ps1`, with the review-save
  command in the acceptance report. Do not run builds or automated game tests
  while Vlad is using the machine. No new local runs are needed for this closure.
- Rollback: toolkit `ours-on-pin` = `dc32f30b303c79e1f2aaa592e2138fb933be93cf`;
  pre-rebase parent `1a2e2b4`; snapshot pointer `logs/rebase-work/baseline-path.txt`.
  Preserve snapshot, generated code, build certificates and ignored test evidence.
- Next: agree the first M6 PC feature slice, then M5 Proton and M9 macOS.
  Each upstream PR or named batch needs Vlad's separate approval. No upstream PR
  has been opened. CPU vertex fallback performance remains unmeasured.

### Standing items
M4 closed (D45). Backlog: two-pad gameplay, memory over three fights, rare
`sub_001A3310` crash, loading-bar glitch, rare silent boot, black profile thumbnails,
Blazin' film grain and half-pixel alignment. Owner acceptance does not constitute
exhaustive testing of these backlog items. See docs/03 and docs/05.

## Superseded by accepted rebase, 2026-10-04

### Rebase ready for owner play-test, 2026-10-04
The fresh-shell owner command exposed a launcher gap: `run.ps1` omitted the four
runtime flags always supplied by the harness. Two windowless processes were
stopped; the launcher now supplies absent graphics/vblank/USB settings, preserves
explicit overrides and restores added settings after exit. Windows PowerShell 5.1
launch verified a real window, D3D11 and controller initialization, and rendering
in `logs/run-20261004-094353.log.err`, using the disposable `runtime-data` root.
The game was left running for Vlad. Do not start builds or automated game runs
while he play-tests. Manual acceptance and main merge remain pending; toolkit
pin and certified executable are unchanged. See `docs/research/launcher-defaults-review.md`.

Vlad approved fork/rebase/retests, unattended game runs and the exact public source publication.
Claude is not editing for two days. Parent branch `toolkit-rebase`; leave main unmerged until the
Release play-test. The parent pin/retirement commit is `7068110`, published on the private topic.
Draft PR #1 (private development record) is open and attached to this chat.
Fresh-checkout CI (private development record) is 3/3 green:
67 Ubuntu tests, 19 MSVC compatibility cases, runtime build and hygiene. Final documentation follows
that source checkpoint; leave the draft unmerged until Vlad's Release play-test.

- Published toolkit fork `vyanhursky/xboxrecomp`, branch `defjam/rebase-2026-10`, exact SHA
  `aa1a1b91dea9fd266acb3a3fe51dfcec3b2e6bbc`. Actual submodule is clean and detached at that pin.
  All 108 patches map to 15 logical commits; archive retained, replay scripts and CI replay removed.
  Generic changes use fork topics/publish-before-gitlink; game-specific changes stay in src/.
- Fresh actual-checkout analysis 17,876 functions; lift 17,886 translated / 4 manual / 111 same stubs,
  20 C files / 87 MB. Seeds unchanged. 409 local tables / zero missing arms; 15 foreign arms separately
  verified. Coverage 87.95%, +9 bytes. Both hooks and PB scanner preserved; census changes explained.
  Both MSVC presets certified, and their certificates still verify after final game runs.
- Final Release `logs/regress-20261003-191107.txt`: 9/9, fight median/minimum 120/112, 3/3 boots.
  Final Debug `logs/regress-20261003-202026.txt`: 9/9, fight 120/66, 20/20 boots, zero hangs/failures.
  Debug early dips exist in pre-rebase logs too; later minimum 107 vs previous 119/116/117.
  Full cadence-window evidence is retained; do not claim exact Debug timing parity.
- Project tests 67/67; CPU suite 464 passed / 26 existing skips / 57 compiled subtests. Native
  kernel/audio fixtures 9/9, USB 1/1, VSH WARP 2/2 including 60 numeric cases and state checks.
  D52 retains correct SHRD and uses read-only canonical-first/exact-metadata legacy save compatibility;
  19 native cases cover wrapper ABI, collisions, bounds, shared root policy and Unicode paths.
- Extra Release intro/fight/crib/gym/unlock 5/5, 13 captures, all save restores equal and fault lists empty.
  Nine PNGs byte-identical, including all four Unlock Fighters selections. Four movie/gameplay frames
  differ in phase/pose/camera; sampled materials/layout are consistent. Both 110s fight HUDs read 1:53.
  Audio: 121 post-game-start level reports, 120 nonzero, zero dropped/dry events. Whole run retains ten
  dry events in the first six reports before game start. PCM has no full-scale samples. Perceptual
  fidelity and startup audio remain listening checks; no equivalent baseline PCM/counters exist.
  Full report: `docs/research/toolkit-rebase-acceptance.md`; artifacts stay in ignored logs/.
- Final original-save rehash identical: 18 files / 5,243,503,676 bytes (`original-save-verified.json`).
  All tests used disposable snapshot runtime-data. Serial runner 73907 completed with exit 0; no game
  was left by that automated runner. The corrected manual launch is now running for Vlad; the acceptance report contains the Release command using the review copy.
- Rollback: `ours-on-pin` = `dc32f30b303c79e1f2aaa592e2138fb933be93cf`, exact original live 108-patch
  toolkit state. Snapshot pointer `logs/rebase-work/baseline-path.txt` preserves source/builds/analysis,
  generated code, original saves and captures. Migration worktree/branch retains the published topics.
- Next: Vlad's Release play-test of
  existing profiles, Story/creator, a fight, menus/Unlock Fighters and audio before main merge.
  Upstream PRs require separate approval. M6 PC features follow the rebase, then M5 Proton and M9 macOS.

### Standing items
M4 closed (D45). Backlog: two-pad gameplay, memory over three fights, rare `sub_001A3310` crash,
loading-bar glitch, rare silent boot, black profile thumbnails, Blazin' film grain, half-pixel alignment.
Keep these outside the rebase. See docs/03 and docs/05 for diagnostics and standing rules.

## Superseded by owner launch fix, 2026-10-04

### Rebase ready for owner play-test, 2026-10-03
Vlad approved fork/rebase/retests, unattended game runs and the exact public source publication.
Claude is not editing for two days. Parent branch `toolkit-rebase`; leave main unmerged until the
Release play-test. The parent pin/retirement commit is `7068110`, published on the private topic.
Draft PR #1 (private development record) is open and attached to this chat.
Fresh-checkout CI (private development record) is 3/3 green:
67 Ubuntu tests, 19 MSVC compatibility cases, runtime build and hygiene. Final documentation follows
that source checkpoint; leave the draft unmerged until Vlad's Release play-test.

- Published toolkit fork `vyanhursky/xboxrecomp`, branch `defjam/rebase-2026-10`, exact SHA
  `aa1a1b91dea9fd266acb3a3fe51dfcec3b2e6bbc`. Actual submodule is clean and detached at that pin.
  All 108 patches map to 15 logical commits; archive retained, replay scripts and CI replay removed.
  Generic changes use fork topics/publish-before-gitlink; game-specific changes stay in src/.
- Fresh actual-checkout analysis 17,876 functions; lift 17,886 translated / 4 manual / 111 same stubs,
  20 C files / 87 MB. Seeds unchanged. 409 local tables / zero missing arms; 15 foreign arms separately
  verified. Coverage 87.95%, +9 bytes. Both hooks and PB scanner preserved; census changes explained.
  Both MSVC presets certified, and their certificates still verify after final game runs.
- Final Release `logs/regress-20261003-191107.txt`: 9/9, fight median/minimum 120/112, 3/3 boots.
  Final Debug `logs/regress-20261003-202026.txt`: 9/9, fight 120/66, 20/20 boots, zero hangs/failures.
  Debug early dips exist in pre-rebase logs too; later minimum 107 vs previous 119/116/117.
  Full cadence-window evidence is retained; do not claim exact Debug timing parity.
- Project tests 67/67; CPU suite 464 passed / 26 existing skips / 57 compiled subtests. Native
  kernel/audio fixtures 9/9, USB 1/1, VSH WARP 2/2 including 60 numeric cases and state checks.
  D52 retains correct SHRD and uses read-only canonical-first/exact-metadata legacy save compatibility;
  19 native cases cover wrapper ABI, collisions, bounds, shared root policy and Unicode paths.
- Extra Release intro/fight/crib/gym/unlock 5/5, 13 captures, all save restores equal and fault lists empty.
  Nine PNGs byte-identical, including all four Unlock Fighters selections. Four movie/gameplay frames
  differ in phase/pose/camera; sampled materials/layout are consistent. Both 110s fight HUDs read 1:53.
  Audio: 121 post-game-start level reports, 120 nonzero, zero dropped/dry events. Whole run retains ten
  dry events in the first six reports before game start. PCM has no full-scale samples. Perceptual
  fidelity and startup audio remain listening checks; no equivalent baseline PCM/counters exist.
  Full report: `docs/research/toolkit-rebase-acceptance.md`; artifacts stay in ignored logs/.
- Final original-save rehash identical: 18 files / 5,243,503,676 bytes (`original-save-verified.json`).
  All tests used disposable snapshot runtime-data. Serial runner 73907 completed with exit 0; no game
  remains running. The acceptance report contains the Release launch command using that review copy.
- Rollback: `ours-on-pin` = `dc32f30b303c79e1f2aaa592e2138fb933be93cf`, exact original live 108-patch
  toolkit state. Snapshot pointer `logs/rebase-work/baseline-path.txt` preserves source/builds/analysis,
  generated code, original saves and captures. Migration worktree/branch retains the published topics.
- Next: Vlad's Release play-test of
  existing profiles, Story/creator, a fight, menus/Unlock Fighters and audio before main merge.
  Upstream PRs require separate approval. M6 PC features follow the rebase, then M5 Proton and M9 macOS.

### Standing items
M4 closed (D45). Backlog: two-pad gameplay, memory over three fights, rare `sub_001A3310` crash,
loading-bar glitch, rare silent boot, black profile thumbnails, Blazin' film grain, half-pixel alignment.
Keep these outside the rebase. See docs/03 and docs/05 for diagnostics and standing rules.

## Superseded 2026-10-03 20:47

## 7. Hand-off

### Active rebase, 2026-10-03
Vlad approved the fork/rebase/retests and unattended game runs (D48); Claude is not editing for two days.
Parent branch `toolkit-rebase`, committed checkpoint `87af9e2`; leave main unmerged until Vlad's release play-test.

- Rollback ref `ours-on-pin` = `dc32f30`, exact 108-patch baseline; parent gitlink still `6f55eaa`.
  Actual `tools/xboxrecomp` working checkout is detached at published `aa1a1b9` (D53/D54), clean.
  Candidate `logs/rebase-work/migration`, branch `defjam/rebase-2026-10`, published tip `aa1a1b9`.
  All 15 logical topics committed with an explicit source allowlist, no game data; working tree clean.
  Public fork `https://github.com/vyanhursky/xboxrecomp` branch is published. Vlad explicitly approved
  the source payload; remote SHA verified exactly `aa1a1b91dea9fd266acb3a3fe51dfcec3b2e6bbc` (D54).
- Baseline snapshot pointer `logs/rebase-work/baseline-path.txt`: executables/PDB/maps, generated C,
  analysis, save tree and five capture routes. Fresh pre-rebase Release 9/9 (`regress-20261003-123017.txt`).
  Run only with `DEFJAM_DATA` set to snapshot `runtime-data`; all runs guard its complete save root.
  Original 18 save files / 5,243,503,676 bytes rehashed identical after the clean candidate run.
- Clean candidate Release: `logs/regress-20261003-180239.txt`, 9/9 in 28 min, goldens match,
  fight median 120 / minimum 112 presents per two seconds, clean Story creator/crib/gym routes,
  3/3 soak boots. Initial 4/9 failure evidence retained in `regress-20261003-165713.txt`.
  Candidate Debug full regression `regress-20261003-183307.txt`: 9/9 in 28 min, 67 unit tests,
  goldens/Story routes pass and 3/3 boots. Fight median 120, minimum 53; dips at intervals 1/2 after
  Game.StartGame, after the first 16 s minimum 116. Preserve the full minimum and repeat it in the
  final actual-checkout regression. No timing-run diagnostics. Final actual-checkout analysis/lift/audits and both builds complete. Release `regress-20261003-191107.txt` and Debug `regress-20261003-202026.txt` are 9/9; Debug 20/20 boots clean. Extra Release routes run on session `73907`.
- D52: baseline zero-count SHRD produced legacy VY2/VY3/Options name hashes. Correct CPU semantics
  retained; game replacement `sub_001F8360` uses canonical-first, exact-metadata-verified legacy fallback,
  with no folder migration. 19 native compatibility tests, including ABI, collisions, bounds and Unicode.
- Project unit suite 67/67. Toolkit CPU suite 464 passed, 26 existing compiler-dependent skips,
  57 compiled subtests; final segment-rejection switch fixture 5/5. Kernel/audio CTest 9/9,
  USB 1/1, VSH WARP 2/2 (60 numeric cases plus state/cache checks).
- Fresh analysis 17876 functions; lift 17886 translated / 111 identical unresolved stubs / 4 manual,
  20 C files / 87 MB. Same seed file. Local jump audit 409 tables / zero missing arms; all 15 recovered
  foreign arms verified separately. Coverage 87.95%, +9 bytes; manual replacement explains new gap.
  Hooks precede guest instructions; 16 added definitions and two changed extents explained in
  `docs/research/toolkit-rebase-fresh-lift-audit.md`. PB scanner byte-identical to original baseline.
- Local `.gitmodules`, AGENTS/CLAUDE, docs/05 and patch-archive README are prepared; replay scripts
  and CI replay step removed locally. Windows CI gains the native save fixture; CTest failures propagate.
  Public approval, publication and remote-SHA verification are complete; commit the gitlink after final gates.
  New Windows-header integration also uses proper LARGE_INTEGER performance-counter types in the old
  fence hook; timing arithmetic unchanged. Analysis reads the validated original extracted dump; only
  game runs use the disposable save root (which intentionally contains no extracted dump).
  Actual-checkout 67 project tests and 464 CPU tests / 57 compiled subtests pass; both builds certified.
  Final Release 9/9 (`regress-20261003-191107.txt`), Debug 9/9 (`regress-20261003-202026.txt`) with
  20/20 boots clean. Serial runner `73907` now runs five extra PNG/audio routes. Do not start another game or build. Compare baseline
  captures, cadence and audio counters; reverify original saves. No source edits during game/build gates.
- Then publish private parent topic for review/CI. Final gates: Vlad's release play-test before main
  merge; each upstream PR requires separate approval. M6 follows rebase, then M5 Proton and M9 macOS.

### Standing items
M4 closed (D45). Backlog: two-pad gameplay, memory over three fights, rare `sub_001A3310` crash,
loading-bar glitch, rare silent boot, black profile thumbnails, Blazin' film grain, half-pixel alignment.
Keep these outside the rebase. See docs/03 and docs/05 for diagnostics and standing rules.

## Superseded 2026-10-03 18:07

## 7. Hand-off

### Active rebase, 2026-10-03
Vlad approved initial fork/rebase/retests and unattended game runs (D48); Claude will not edit for two days.
Parent branch `toolkit-rebase`, current committed checkpoint `1fd0b50`. Public fork
`https://github.com/vyanhursky/xboxrecomp` exists; no topic branch published yet.

- Original toolkit checkout remains `ours-on-pin` at `dc32f30` (all 108 patches reconstructed exactly).
  Candidate: `logs/rebase-work/migration`, branch `defjam/rebase-2026-10` atop upstream `1409a7d`.
  Eight CPU commits through `7f7eef9`; runtime integration still uncommitted. Both candidate game presets built successfully after reporter integration. Initial release regression completed 4/9; do not publish or switch the parent pin until retests are green.
- Baseline snapshot pointer `logs/rebase-work/baseline-path.txt`: full original save, generated sources,
  both executable/PDB/map sets and captures preserved. Fresh release baseline 9/9 (`regress-20261003-123017.txt`),
  120 presents/2 s median, minimum 112; five extra routes pass. Run only with `DEFJAM_DATA` set to its
  `runtime-data` disposable copy. Original save hashes verified unchanged.
- Candidate full recompiler suite 464 passed, 26 compiler-dependent skips, 57 compiled subtests
  (`logs/rebase-work/foreign-switch-full-tests.txt`); final switch fixture 5/5 with MSVC. All runtime libraries build (`runtime-build.txt`).
  VSH CTest 2/2 (`vsh-test-results.txt`), including 60 numeric WARP shader cases and cache/state checks.
  USB CTest 1/1 (`usb-test-results.txt`): hub + four pads, partial transfers, rumble, failed DMA retry,
  indexed resets, shared done chain and WDH acknowledgement. Kernel/audio CTest 9/9 (`runtime-fixtures-results.txt`), including 1025 physical mappings. Project pipeline/save-guard/save-compatibility unit tests 67/67 (`pipeline-save-compat-tests.txt`): complete payload restore, failed-backup retention, absolute/empty roots, both ICALL failure forms, start/end provenance and protected lifter arguments.
- Parent source changes: defaults for anchored-seconds pad scripts and six-channel audio; frame-end callback
  registration; runtime-owned indirect-tail site compatible with the baseline toolkit.
- Fresh analysis: 17876 functions; fresh lift after D52: 17886 translated, 111 stubs, 4 manual functions, 20 C files / 87 MB. Coverage audit: 16 added definitions (15 recovered foreign switch arms, one existing seeded thunk), one new game replacement (001F8360); two extent deltas. Entry hooks precede guest work; all 111 unresolved stub identities match the baseline.
- Current measurements: debug `run-20261003-161055.log.err` reached the main menu with identical save restoration.
  Initial release regression (`logs/rebase-work/candidate-release-regress.txt`) matches M2/M3 goldens, but M4a
  `run-20261003-162319.log.err` never captured the menu; fight `run-20261003-162654.log.err` stops at Battle ID;
  intro `run-20261003-163410.log.err` times out before Story. Keep these failures; do not dismiss as boot variance.
  Intro had live thread-stack sampling and is not a clean timing/performance run; rerun without diagnostics.
  Live diagnostics in `logs/rebase-work/regress-{intro,live}-*`; slow FIFO/fence progress and tick clock stalls.
  GPU scanner is byte-identical to the preserved baseline. Inspect ISR/DPC integration and fresh-lift deltas.
  Profile cause proven: baseline `sub_002032A0` SHRD count zero ORed both hash words, creating old folder spellings
  `005600590036/37` and `...4ADF`. Correct spellings are `005600590032/33` and `...4ADD`.
  Exact optimized fixture reproduces all three (`save-hash-fixture-results.txt`). D52 keeps corrected CPU
  behavior and uses a read-only, metadata-verified game replacement at `sub_001F8360`; relift and both builds certified; clean full Release regression passes goldens, fight and intro so far. Fight median/minimum 120/112 matches the baseline; remaining checks running.
  GPU source audit finds no dropped acknowledgement; ISR/DPC changes remain a separate contract risk.
- Next: finish save-compatibility relift and both builds, repeat affected routes, then full regression and debug soak. All 108 ledger
  rows have source outcomes; full game acceptance remains pending. Commit logical runtime topics only when green,
  publish clean fork branch; switch parent submodule to its published
  commit and retire old patch replay. Re-analyze and re-lift with existing seeds unchanged, audit coverage,
  build debug and release, full regressions + extra routes + 20 debug boots, compare captures/audio/cadence.
- Final gates: Vlad's release play-test before merging the private parent branch; confirm each upstream PR
  separately before opening. M6 remains after the rebase, then M5 Proton, then M9 macOS (D45).

### Standing items
M4 closed on Vlad's play-test (D45). Backlog: two-pad game play, private bytes over three fights,
rare `sub_001A3310` crash, loading-bar glitch, rare silent boot; black profile thumbnails; Blazin' film grain;
half-pixel alignment needs evidence. Do not add these features during the rebase. Full reference and
diagnostics remain in `docs/05-reference.md` and `docs/03-workflows.md`.

# Hand-off archive, 2026-10

## Superseded at 2026-10-03 15:46

## 7. Hand-off: exact next steps

### State as of 2026-10-02 17:30 (read this first; earlier hand-offs are in `docs/worklog/2026-09-handoffs.md`)

**Where it stands.** M0-M4 are closed (M4 and M4f on Vlad's play-test, D45). The game is playable end to
end in the release build: menus, a One on One fight, Story mode from a new ID through the cutscenes,
creator and tutorial, the crib, shops, Stapleton Athletics, and saved Story progress with two profiles.
Vlad's words on 2026-10-02: the intro "near perfect", Story fights "look good", "definitely playable and
feels good to play". Toolkit patches run to 0108. `python scripts/regress.py` is 9 of 9 on the release
build (`logs/regress-20261002-162043.txt`). Nothing is uncommitted; everything is pushed to `origin main`.

**Start here: the toolkit rebase (D46).** Vlad approved moving our toolkit changes onto upstream
xboxrecomp's latest code, retesting, and then offering our generic fixes upstream as pull requests. The
work plan is `docs/06-toolkit-rebase-plan.md` (phases 0-4, the ledger to keep, what "done" means); the
background is `docs/research/upstream-xboxrecomp-2026-10.md` (255 upstream commits since our pin, at least
15 of our patch topics fixed upstream too, upstream fixes we lack). The fork is decided (Vlad,
2026-10-02): on his account `vyanhursky`, **public** from the start (`gh repo fork sp00nznet/xboxrecomp
--clone=false`). Opening each pull request upstream still needs his OK first.
Do the rebase on a branch of this repo too (`toolkit-rebase`) and merge to `main` only when Phase 3 is
green and Vlad has play-tested.

**After the rebase, in Vlad's order** (D45): M6 PC features and enhancements (the list is to be agreed with
him feature by feature; already in: 2x render scale `RECOMP_RENDER_SCALE`, the gamma ramp), then M5 Steam
Deck via Proton, then M9 macOS (needs a second graphics backend: the renderer is Direct3D 11 only; keep M6
from deepening that dependency). Before M6 touches them, split `src/kernel/nv2a_pb_exec.c` (3,100 lines)
and `src/kernel/kernel_bridge.c` (10,000) -- after the rebase, not before, or the split conflicts with it.

**Confirmed by Vlad on 2026-10-02**: the darker picture (the gamma ramp) matches the console as far as he
can tell, and X in Learn Moves plays the move's movie. Every item of his 2026-10-01 and 2026-10-02 lists
is closed.

**How to run and check it.** CLAUDE.md §4 and §4b, `docs/05-reference.md` "Running it, and checking it":
- `python scripts/regress.py [--quick] [--only fight,intro]`: the regression run (25 minutes in full).
- `python scripts/harness.py run <boot|fight|crib|gym|unlock|intro> [--png] [--stage ...] [--shots ...]
  [--env NAME=VALUE]`: one scripted route with captures in `logs/shots/<route>/`. Story routes run inside a
  save guard (`$DEFJAM_DATA/save-guard/` keeps the last three copies of the save area).
- `python scripts/harness.py soak --boots N`: boots until one stops presenting, then dumps stacks and device
  state to `logs/hang-<stamp>/`.
- `python scripts/toolkit-patch.py cut|verify`: until the rebase retires the patch files.
- `python scripts/worklog-add.py <entry file>`: a §6 entry, older ones archived to `docs/worklog/`.
- `python scripts/prune-logs.py [--delete]`: clears run logs older than three days that the notes do not cite.

What the routes press, for extending them (the stage syntax is in `scripts/harness.py`'s docstring):
- fight: Battle -> One on One with defaults, then a fighter that walks right and throws every attack.
  With more than one user ID in the save area Battle asks for one first (the route handles it).
- crib: Story with the first profile in the list; the crib opens on a "Messages Waiting" prompt (down, A
  for NO); its bar is Map, Messages, Wardrobe, Options, Trophies, Exit.
- gym: crib -> Map -> A (Shop District) -> down -> A (Stapleton Athletics) -> Learn Moves -> X previews.
  The map: Shop District -> right Club 357 -> right The Limit; up from Shop District is the Foundation.
- unlock: Main Menu -> Unlock Rewards -> Unlock Fighters, moving the selector (nothing is bought).
- intro: Story from a new ID ("AAA"); the escort shot is ~16 s after `game.startstorymode(` in release, the
  car crash 46-62 s, the creator is `getscreeninfo(story/chardec`. Past it: A through the creator,
  `game.continueload(`, `game.showfightingmovie(=a@6;left@9;a@11` (the style prompt defaults to NO),
  `@game.entertutorialmode(`.

**Other open items.**
- A one-off full freeze of a debug boot about 30 s in (`run-20261002-110917`): the log stops mid-frame,
  the timer thread included, no crash record. Not seen in ~70 boots since. An overnight
  `harness.py soak --boots 100 --preset win-x64-debug --keep-going` would settle it.
- The D3D11 debug layer's exception 0x87D (two debug runs on 2026-10-01); patch 0091 reports it as
  `[D3D11-DEBUG]`; not seen since, and `regress.py` fails on it.
- M4d items never formally met (D45, backlog): two pads, private bytes over three fights, the rare
  `sub_001A3310` crash at a fight's start, the loading-bar glitch, a rare boot with no sound.
- Profile thumbnails on Select User ID are black squares. Film grain in Blazin' (no separate pass found).
- Half-pixel alignment of screen-space quads: tried and taken back (§6 2026-10-02 12:30); needs evidence
  from hardware or from xemu's source.
- The fence hold (0095) engages ~500 times a second in a release fight and never timed out; if a scene
  stutters in release, `RECOMP_FENCE_HOLD=0` says whether it is the hold.

**Known loose ends in the GPU model.** Modelled: depth, stencil, blend (constant colour and equation
included), alpha test, combiners, four texture stages, palettes, address modes, min and mag filters, the
surface clip, indexed and array draws, point sprites, the display's gamma ramp. Not modelled: polygon
offset (enabled with zero factor and bias), fog (set, but no final combiner seen reads it), float depth,
texture-shader modes beyond plain 2D/3D/cube, render targets sampled as textures, mip levels (only level 0
is uploaded), the G8B8/R8B8 channel mapping, lines and points on the CPU vertex path, batches over 32,768
indices (truncated, with a log line). Upstream's executor has some of these; see the rebase plan.

**Diagnostics** (all in `docs/03-workflows.md` and `docs/05-reference.md`): `RECOMP_PB_BATCH_DUMP=shot`,
`RECOMP_PB_PROBE=x,y;...`, `RECOMP_PB_UNHANDLED_ALL=1`, `RECOMP_PAL_DUMP=<addr>[~<mask>],<file>`,
`RECOMP_GAMMA=0`, `scripts/peek-guest.py`, `scripts/hang-peek.py`, `scripts/native-stacks.py`,
`scripts/sample-threads.py`, `scripts/guest-stack.py`, `scripts/apt-dump.py` (a screen's ActionScript;
needs `DEFJAM_DATA` set), `scripts/window-shot.ps1` (what the window shows, after presentation).

### Reference
How the rendering works, the object addresses, the diagnostic tools, the standing items and how to run
and check a build are in `docs/05-reference.md`.
