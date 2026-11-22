# Sparse-preserving uninstall backups (#180)

Target: v1.3.0. Toolkit unchanged (`d108a64`). No HD texture behavior changes.

The app now asks the setup engine to make its backup with `--uninstall --backup-dir PATH`.
The engine takes the existing install, data and play locks, recovers pending activation,
backs up and verifies the data, and only then removes game builds. The optional data-folder
deletion remains in the app after engine success. The inherited Steam shortcut-removal step
still precedes the engine; failure preservation here refers to game builds and player data,
not to an already removed Steam shortcut.

Backups include **all of save/** (including raw partition images and caches), **fighter-state/**
(custom fighter unlocks), and **settings.ini**. No raw-image ranges are assumed disposable.
Only all-zero blocks become holes; nonzero blocks are copied verbatim. Logical lengths and
SHA-256 hashes of every source/copy are verified, the source inventory is rechecked, and
`backup.json` is published only after verification. A new destination is required; failures
keep the original installation/data and any partial backup. Links/junctions and special files
inside the selected trees are refused. Basic file metadata and empty directories are preserved.

Windows requests FSCTL_SET_SPARSE, then uses SetEndOfFile for final sizing. Python's CRT-backed
truncate can physically fill a zero-only extension despite the sparse flag: the first full-size
trial exposed that defect (byte-equal but allocated 5,243,469,824 bytes). The final allocation test
guards against it. POSIX seeks/truncates sparse-capable files normally. An unsupported Windows
volume falls back to an ordinary verified copy, retaining existing disk-full failure safety.
Savings depend on the destination filesystem and on how much of the source is zero.

## Windows experiment, 2026-11-21

Six raw images were read from the existing development root and copied to a disposable dense
fixture; source hashes were checked before and after copying. Owner images were never modified.
The fixture contains synthetic settings/unlocks, not copied profile directories.

| Metric | Dense fixture | Final verified backup |
|---|---:|---:|
| Raw-image logical bytes | 5,243,406,848 | 5,243,406,848 |
| Raw-image allocated bytes | 5,243,408,384 | 1,114,112 |
| All image bytes/hashes | original copy | identical |

The final copy plus repeated verification took **40.23 seconds**; reclaimed allocation versus
a dense copy is **5,242,294,272 bytes**. Windows allocation was measured with
GetFileInformationByHandleEx(FileStandardInfo). This is one local NTFS fixture, not an estimate
for every installation or another platform. Full logical scans still cost time even when
the result occupies very little disk. Evidence: local `logs/storage-probe-final.json`.

## Validation / hand-off

- Available Python suite before the final SetEndOfFile refinement: 2,012 passed, 845 skipped,
  one slow test deselected (`sparse-units.log`). Final focused checks: 78 passed, six skipped
  (`sparse-focused-final.log`), including an actual-allocation assertion, byte equality,
  dense fallback, links, corruption/disk-full/source-mutation failures and held locks.
- Windows native app/setup packaging passes; final package and packaged CLI acceptance are
  recorded in the PR. Explicit payload validation now requires engine/save_storage.py;
  Windows/macOS/Linux staging all include it. Existing app argument-contract coverage includes
  uninstall and backup-dir. The UI reports a completed manifest even if a later uninstall step fails.
- Release gate: native macOS/Deck filesystem and uninstall acceptance, restore the backup to a
  disposable data root and play-test profiles/custom unlocks. No new game runtime regression or
  fresh game compilation is claimed for this app/setup-only change. The earlier retention
  lane's fresh install qualification remains evidence only for unchanged install behavior.

D-new: back up all save bytes plus custom unlocks, use zero-skipping copies and verify before
removing game builds. Avoid narrowing the survival set without a game-specific raw-write audit.

D-new: perform backup in the engine under install/data/play locks; exclusive destinations and
a post-verification manifest distinguish incomplete copies from backups safe to restore.
