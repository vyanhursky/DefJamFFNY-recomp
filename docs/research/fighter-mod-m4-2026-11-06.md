# Fighter Mod Support: M4 launcher integration

The owner authorized continuing after the M3 handoff on 2026-11-06. Work stays
local on `research/custom-fighter-mods`; no public push or PR. M4 implementation
and focused Windows acceptance are complete locally.

## Implemented

- Shared compiler and presentation modules serve both the research driver and
  launcher. Existing native/cache/probe fixtures pass 38/38 after extraction.
- `fighters.json` identifies a one- or multi-fighter ZIP. Only declared resource
  files, bounded README/LICENSE text and the manifest are admitted. Their hashes,
  typed formats, dependencies and native composition are checked before install.
  Native hooks, arbitrary patches and package-supplied binding tables are absent.
- Existing mod-manager receipts, staging, writer/runtime locks, journal recovery
  and rollback are reused. Whole-pack activation is an atomic manager-state
  update after complete roster validation. Active updates validate the proposed
  roster before replacement. Failed operations retain prior state and files;
  enabled dependents prevent disabling/updating incompatible requirements.
- Fighters have a separate tab alongside Textures and Languages. ZIP import,
  whole-pack enable/disable, prior-version restore and removal use the helper.
  Fighter packs never enter texture priority. Local ZIP installation needs no
  catalogue publication; signed catalogue capability filtering also recognizes
  `fighters-v1`.
- The native launcher starts a Python profile supervisor after Play, retaining
  the original settings/data/mod roots. Only guest save storage uses its new
  verified workspace. The helper prepares the M3 Store/session, imports once,
  preserves dormant progression with zero active packs, and refuses missing
  adopted heads instead of re-importing an old career. Native startup checks
  readiness and workspace containment; save barriers check supervisor health.
  A normal exit requests final acknowledgement; a dead parent leaves recovery
  at the last complete generation. No platform installer wrapper is required.

## Evidence so far

- Package/transaction tests: **56 passed** in `logs/fighter-m4-manager-unit.txt`.
  The first collection attempt lacked the setup import path; the corrected test
  imports the existing native fixture before the new modules.
- Combined compiler/probe/manager/launch/bridge/model checks: **142 passed** in
  `logs/fighter-m4-focused-unit.txt`.
- Windows CRT read locks proved exclusive in a native/Python shared-lock
  reproducer. Both sides now use shared `LockFileEx`; an exclusive installer
  remains excluded. **80 related checks passed** after that correction in
  `logs/fighter-m4-shared-lock-fixed.txt`. A real running game also refused an
  activation change with byte-identical state (`logs/fighter-m4-live-lock.txt`).
- Final close/launch bridge/model checks: **45 passed**, followed by **9 bridge
  checks** including stale supervisor refusal, explicit final acknowledgement
  and rejection of diagnostic switches from a ready projection. Logs are
  `logs/fighter-m4-final-bridge-unit.txt` and
  `logs/fighter-m4-supervisor-bridge-unit.txt`.
- Import/adoption checks: **7 passed** in `logs/fighter-m4-adoption-unit.txt`.
  An initially empty adoption also remains import-once; later source-folder
  files cannot silently become the adopted career. Pending install journals
  refuse launch before adoption. Parent loss preserves the committed Store.
- Release builds pass, including final native changes in
  `logs/fighter-m4-managed-build.txt`. No toolkit pin change.
- Real authored Alpha installed into `logs/fighter-m4-managed-data`, using a
  copied VY3 fixture. Beta's first installation failed on a transient Windows
  rename denial while publishing its immutable menu cache; Alpha and the
  original source save remained intact. Shared cache publication now uses the
  existing bounded durable-rename retry. Beta retry passed in
  `logs/fighter-m4-prepare-retry.txt`.
- Real Windows launcher: both full-resource packs enabled through their
  checkboxes, version/counts inspected, then Quit. Exit 0; complete original
  save tree identical. Capture: `logs/fighter-m4-launcher-enabled.png`.
- Real full-resource active Alpha 1.0.0 -> 1.0.1 -> rollback 1.0.0 retained
  activation and exact identity ledger, restored the original resource hashes,
  and refused a corrupt 1.0.2 without changing state/files. Both packs then
  disabled with their historical ledger intact. `logs/fighter-m4-transactions.txt`.
- Managed native gameplay: `logs/run-20261106-181331.log.err`, summary
  `logs/fighter-m4-managed-native-retry.txt`. Normal copied settings, native
  child supervisor, no externally supplied fighter runtime artifacts. Signed-in
  VY3 selected Beta second (logical 103, private core 145) against Crack (17).
  Menu identities, immutable materialization, movement/attack/damage and a
  decisive result verified; two FSC1-acknowledged save batches retain all six
  profile files, ledger and custom extension. 113 two-second presentation
  samples: min 103, median/max 120; no crash/watchdog/debug-layer/unresolved-call
  signatures. Source save bytes identical. Evidence:
  `logs/fighter-m4-managed-evidence.json`; combat teaser:
  `logs/fighter-m4-managed-combat.jpg`. The harness ends the run by terminating
  its owned process; the helper retained the last committed generation.
- The first gameplay command supplied a nonexistent Python path and correctly
  refused startup with the repair message. It did not adopt or modify profiles.
  The corrected command used the installed interpreter. This failed setup run
  (`logs/fighter-m4-managed-native.txt`) is not counted as gameplay acceptance.
- Zero-pack Story continuation: `logs/fighter-m4-zero-ui.log` and
  `logs/fighter-m4-zero-ui-evidence.json`. The same VY3 entered the Crib, saved
  VY3/Options, and returned through `Game.StartMainMenu(3)`. A new acknowledged
  generation retains the same six files, all 79 stable identities and the exact
  dormant custom extension. Clicking the game window's Close returned exit 0
  and `managed profile session completed`; original source hashes still match
  the import fixture. 45 two-second presentation samples: min 105, median/max
  120. Triage still labels inherited kernel/file-lookup messages unclassified
  (including the existing NtFsControlFile stub and optional asset/music opens);
  this is not a claim that the generic digest is entirely clean. No new fault
  suppression or ignore rule was introduced.

## Integration decisions

- D-new: keep the native launcher as parent, start the helper after Play and
  before guest boot. This uses the same source/bundled Python discovery on each
  platform and lets launcher pack changes finish before freezing the roster.
  The child owns profile verification and the exclusive session lock; parent
  and child share the runtime lock. No installer-specific launch wrapper.
- D-new: exact managed ready settings are allowlisted; inherited Fighter test
  variables are cleared. Explicit isolated research launches retain their
  existing guarded path. Native readiness checks PID, UUID and canonical leaf
  containment. Same-user malicious concurrent filesystem mutation is not a new
  sandbox boundary.
- D-new: native window close explicitly requests profile finalization because
  Windows `TerminateProcess` and POSIX `_Exit` bypass `atexit`. A stale heartbeat
  or failed ready state blocks native save acknowledgement. Abandoned workspaces
  are never replayed. Last durable head is the recovery point.
- D-new: after adoption, Open saves points to authoritative profile history.
  The original source remains an import-time backup; disabling all packs never
  switches to it. Document whole-history backups and restoration. There is no
  arbitrary post-adoption save merge/import UI in M4.

## Handoff

- Local implementation commits: `77aeb4a` shared compilation/presentation and
  `b6716d3` package manager, supervised native launch and Fighters UI. The
  Release binary contains all final native changes. Later edits only tightened
  host adoption behavior, added focused checks and recorded acceptance.
- M4 uses the M1/M2 adapters and M3 profile backend through ordinary installed
  packages. The full-resource fixtures in `logs/fighter-m4-managed-data` are
  left installed and disabled after acceptance; no native process remains.
  Its original `save` folder is untouched. No game bytes, captures or builds
  are tracked in source.
- The launcher workflow and whole-history backup guidance are in
  `docs/fighter-mod-support.md`. Source packaging already inventories tracked
  setup modules and configuration, so the new shared modules use the existing
  bundled helper layout; an actual installer rebuild remains release coverage.
- M5 owns creator inspect/convert/validate/package tools, game-free examples,
  final schema documentation and ordinary-format Vendetta conversion. No
  pack-specific runtime was added, and Vendetta is not yet declared compatible.
- M6 owns macOS/Steam Deck native acceptance, installer coverage, longer
  performance/resource soaks and owner playtest. POSIX close wiring is present
  but has not been exercised here. In-process/termination checks do not prove
  power-loss durability on every filesystem. Windows language/texture native
  composition uses the already-tested M1/M2 adapters; M4 did not repeat that
  entire compatibility matrix.
- No additional owner decision is needed before creator-tool work. No routine
  broad regression was run, per the owner's instruction. All publication stays
  deferred until requested.
