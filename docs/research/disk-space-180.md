# Disk-space review: issue #180, excluding HD textures

Reviewed 2026-11-21 against public main `f80a792`, toolkit `d108a64`.
This is an assessment and implementation record for
[issue #180](https://github.com/vyanhursky/DefJamFFNY-recomp/issues/180), not a replacement backlog.
The issue's macOS/Windows sizes are historical observations, not new measurements.

## Recommendations

| Idea | Benefit | Effort / risk | Recommendation |
|---|---|---|---|
| Retain only active build and immediate predecessor | Stops approximately 600 MB accumulating per operation in the issue's Windows example; also removes obsolete partial attempts | Small setup-only change; deletion must follow durable activation and preserve redirected/user paths | Implemented on this branch; native runtime unchanged |
| Remove compiler intermediates after activation | Current Windows acceptance build holds 178,544,317 bytes in `.obj`, `.lib`, `.pch` under `source/build` | Small-to-medium: those files are not runtime inputs and Repair currently does not reuse them, but explicit allowlists must preserve DLLs, diagnostic PDBs, executable, CMake cache and build-state verification | Good next small PR; qualify `verify-build`, launch, Repair and each platform's dynamic dependencies before deletion |
| Sparse partition images | Logical capacity is 5.24 GB / 4.88 GiB; physical savings depend on allocated blocks | Already implemented on Windows and POSIX at the pinned toolkit; old dense copies are not automatically compacted | Measure allocated bytes before proposing a new image format |
| Compact existing dense partition images | Can reclaim zero-filled ranges while preserving every byte; one local Windows development root still occupies 5.24 GB | Medium maintenance change: exclusive play lock, temporary sparse file, full verification, atomic promotion and failure recovery; destination must support holes | Worth a separate focused PR after backup work; never just truncate images or assume they are empty |
| Uninstall backup without materializing images | Avoids a potential multi-GB temporary allocation; can preserve custom unlocks currently omitted | Small-to-medium app change; save-loss consequences require explicit restore verification | Next focused PR: sparse-preserving copy or a verified compressed archive; preserve all image bytes initially |
| Lower operation free-space requirement | Lets users repair/update on fuller disks; changes admission rather than final installed size | Medium: Repair still compiles native objects in a new attempt; every operation can invalidate reused analysis/lift | Measure peak working space per platform before reducing 12 GiB; do not assume Repair needs no build |
| Read an external extracted folder | Saves the duplicate extracted tree (~2.8 GB in the issue) when the player keeps another extracted copy | Medium/high: source identity, writable overlays, many hardcoded consumers, missing/moved source, uninstall ownership | Optional later mode only; keep managed copy as default |
| Read ISO directly | Avoids extraction while retaining player's original image | High: runtime currently opens ordinary host files; tooling and mod resolvers also need a directory | Defer; larger virtual filesystem project |

See the supporting [dump/path review](disk-space-dump-research.md) and
[save/image review](disk-space-save-research.md). No HD texture changes are included.

Metadata-only Windows observation on 2026-11-21: one existing development save root's Partition0–5
total **5,243,406,848 logical bytes and 5,243,408,384 allocated bytes**, using
`GetFileInformationByHandleEx(FileStandardInfo)` per file with error checks; all six lack
`FILE_ATTRIBUTE_SPARSE_FILE`. `GetCompressedFileSizeW` also reports the full logical lengths.
This is a historical development root, not a fresh
install of the candidate. No save content was read or changed by that measurement. It demonstrates
that existing installations can still have dense images despite sparse creation code; it does not
establish the prevalence of this condition or macOS/Deck allocation. Setting a sparse flag alone does
not reclaim already allocated zero ranges. A verified zero-skipping rewrite is the relevant follow-up.

## What other recomp projects do

The owner asked to follow established project practice rather than choose an external-folder mode by preference.
Three representative source checks support a managed-data default. This is a small comparative sample,
not a statistical survey of every recomp project:

| Project / inspected source | Behavior |
|---|---|
| [Unleashed Recompiled installer](https://github.com/hedge-dev/UnleashedRecomp/blob/700bbd2c0d331a11b86e0a4c1c38ec62db667228/UnleashedRecomp/install/installer.cpp) | Accepts ISO/container/extracted-directory inputs, verifies data, writes a managed `game/` tree. The ISO reader serves installation; this does not demonstrate running directly from ISO. |
| [Marathon Recompiled installer](https://github.com/sonicnext-dev/MarathonRecomp/blob/f60b2f8152dbf20986614eda18f19727fc19e240/MarathonRecomp/install/installer.cpp) | Copies verified base files to `targetDirectory/game`, then prepares a decrypted executable locally. |
| [Zelda's N64ModernRuntime dependency](https://github.com/N64Recomp/N64ModernRuntime/blob/e4342ae030a9d94aa97a81aafd3368ed7daa74df/librecomp/src/recomp.cpp) | ROM validation writes a normalized ROM under `config_path`; later loading reads that stored file. Zelda's README's lack of a separate extraction step does not mean it depends on the originally selected file's location. |

Recommendation: retain one managed, verified game-data copy across releases. Do not require the player's
original input path to remain available. An advanced external-folder mode can be evaluated separately;
it is not necessary to follow these projects' install pattern. This recommendation leaves the player's
original dump untouched and does not automatically delete it after installation.

## Implemented retention policy

`Engine.activate()` commits `rollback_source` alongside the new receipt, recording the actual previously
active build. Only after the activation journal has committed and recovered does `prune_builds()` remove
older Engine-shaped version directories. A cancelled or failed activation never invokes pruning.
Hard-killed abandoned attempts become eligible after the next successful activation. This deliberately
does not promise to reclaim space before a low-space operation begins.

Cleanup requires a schema-1 receipt with the expected data root and direct, canonical `versions/*/source`
paths. It preserves both referenced builds, unknown names, redirected version roots/builds, and any
candidate physically containing the current data, supplied dump or running setup engine/interpreter. Nested game symlinks/junctions are
removed without traversing their targets. Locked/unreadable obsolete builds produce a diagnostic and
can be retried after a subsequent successful activation. Root/data/play locks remain held by `execute()`.

An extra receipt field is compatible with current readers and does not change the updater/data schema.
There is no new automatic rollback UI: retaining a predecessor preserves recovery material.
The open one-folder Windows PR #290 also uses the engine; integrate and exercise retention in that
layout before release. Its Windows UI/data-removal changes are not part of this branch.

## Validation and hand-off

- Focused setup/retention/update/engine/Linux/app-contract suite: **154 passed, 25 skipped** on Windows.
- New tests cover committed-pair retention, abandoned/legacy names, unknown folders, invalid receipts,
  pending journals, deletion refusal/retry, protected data/dump paths, real Windows junctions, activation
  failure recovery and retry. Existing subprocess crash-recovery coverage remains applicable.
- Full available Python suite: **2,007 passed, 845 skipped, one slow test deselected**, Windows Python
  3.13.5 (`unit-disk-space-final.log`). Initial run exposed two synthetic activation fixtures missing
  the normally initialized `dump` attribute; fixed the fixture and reran. HD behavior is unchanged.
- Final conservative refinement also preserves any obsolete build hosting the running engine/interpreter;
  retention/update/engine/activation focused rerun: **161 passed, 10 skipped**, including its two new
  protection cases. The prior full suite precedes this refinement; it was not repeated.
- Windows `scripts/build-setup.ps1 -Development`: **passed**, including app build, embedded runtime /
  fighter-import checks and game-free asset validation (`build-setup-disk-space.log`).
  Final payload/app rebuild after the setup-host protection also **passed**
  (`build-setup-disk-space-final.log`, embedded runtime imports OK, 95 fighter imports, assets verified).
- Disposable Windows silent installation: **passed in 468.4 seconds** (analysis 204.5 s, lift 79.7 s,
  configure 11.2 s, compile/link 141.5 s, activation 0.6 s). The fixture's pre-existing abandoned
  Engine-shaped attempt was removed after activation; the active executable/receipt/build were present.
  It used an isolated install/data root, no HD generation and no shortcuts; no owner saves were used.
  Log: `build/disk-space-acceptance/install.log`, copied to `logs/disk-space-real-install.log` before cleanup.
  This normal packaged-install path is unchanged by the later protection for manually running old setup
  engines; the two newly protected cases have focused fixture coverage.
- Final acceptance version contents (excluding the game junction): **638,321,553 bytes**;
  extracted data: **3,023,108,477 bytes**. Build extension totals: `.obj` 122,905,397,
  `.lib` 32,439,176, `.pch` 23,199,744, `.pdb` 52,912,128, `.exe` 27,764,736.
  These are logical file totals, not a full peak-working-space measurement. No macOS/Deck install
  acceptance or new game regression is claimed for this setup-only change.
- Disposable install's uninstall also passed and removed the 638 MB active build, preserving its data
  as specified (`logs/disk-space-real-uninstall.log`). Automatic approval review blocked the subsequent
  recursive cleanup of the remaining `build/disk-space-acceptance` fixture, without a more specific
  reason. Its ~3.02 GB extracted copy and staging payload remain local; no owner data was deleted.
- No push, PR publication, merge, tag or release is performed by this branch's implementation work.

D-new: retain active and immediately previous activated build only after durable activation; cleanup
failures are nonfatal. This caps routine retention without weakening activation rollback or deleting a
build the current receipt still names.

D-new: keep managed game-data import as the default, consistent with the inspected recomp projects;
external-folder and ISO runtime access remain separate proposals requiring broader path/ownership tests.
