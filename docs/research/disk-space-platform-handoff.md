# Disk-space work: Windows / macOS / Linux hand-off (v1.3.0)

The owner requested all three operating systems, and explicit PR notes for work that cannot
be safely completed on this Windows host. This file separates shared implementation from
native acceptance and the remaining POSIX compaction implementation. No HD work is included.

## #299: build retention — implemented on all three

The shared Python engine retains active + actual immediate predecessor after durable
activation and removes older generated builds/abandoned attempts. Windows junction and
POSIX symlink containment use canonical path checks; rmtree does not traverse nested game links.
Windows real install/uninstall and units passed. Existing CI passed all 35 checks, including
Linux/macOS game-free packaging/runtime fixtures and available Python tests.

macOS/Deck agents: use a disposable real installation, produce three successive update/repair
builds plus a killed attempt, activate the next build, verify only active + actual predecessor
remain and source dump/save hashes are unchanged. Exercise a nested external game symlink and
an unreadable obsolete build; activation success must not become failure because cleanup fails.
No additional POSIX retention algorithm is pending; native install acceptance is pending.

## #300: sparse-preserving backup — implemented on all three

POSIX copies seek over all-zero blocks and ftruncate to exact logical length, with hashes and
inventory verified before removing game builds. Windows uses FSCTL_SET_SPARSE + SetEndOfFile
because CRT truncate filled the holes in the first experiment. Every payload includes the helper.
Backups preserve all save bytes, caches/raw images, fighter-state unlocks and settings; failure
does not authorize data deletion. Existing 35-check CI passed all three package builds.

macOS/APFS and Linux/Deck agents: use real disposable dense images with nonzero islands and
trailing zeros; record st_size versus st_blocks*512 before/after backup, verify SHA-256 equality,
empty directories and metadata. Run actual app uninstall with data deletion and restore to a
disposable data root; save/load/play profiles and custom unlocks. Test unsupported/full volumes,
link refusal and interrupted backup (no completed backup.json; original game/data retained).
APFS clones/volume semantics can affect accounting; report actual allocation rather than assuming
logical size equals occupied space. Do not omit TitleData or raw partition images.

## #301: optimization UI and compaction

`app_optimize.cpp` is compiled on all three OSes. Maintenance's **Optimize disk usage** and
the offer after a successful update open a nonmutating inspection first. A successful explicit
apply writes data/disk-optimization.json; subsequent updates suppress the one-time offer, while
Maintenance remains available. Cancellation/failure does not write a completion marker. Shared
app/engine result JSON carries kind/status/message/apply_supported; no OS-specific UI fork is needed.

Windows apply is implemented and tested. macOS/Linux currently inspect and report allocation,
then show that apply is unavailable, without writing image data or a completion marker. This is
an implementation gap, not merely an untested native build. Keep #301 draft until resolved or
explicitly accepted as a release limitation. The shared UI is ready for a POSIX backend.

### Why an advisory lock alone is insufficient

Pinned toolkit d108a64's POSIX `kernel_file.c:xbox_NtCreateFile` ignores ShareAccess and uses
plain open(); NtWriteFile writes that fd. `kernel_path.c:xbox_path_init` also opens/resizes the
partition images directly at startup. Existing app play.lock covers one install root, not all
installs sharing data. A maintenance flock would not exclude old runtimes that never acquire it.

Windows obtains an OS handle denying write/deletion sharing. POSIX needs a qualified equivalent
or runtime cooperation/migration policy before the existing guard may be removed. Do not enable
apply based only on a successful flock taken by maintenance.

### Suggested native implementation work

1. Add a stable lock associated with the canonical save root. Updated runtimes hold a shared
   lock for their lifetime, **before** startup touches any Partition*.img. Maintenance holds it
   exclusively and nonblocking. It must cover different install roots using the same data.
2. Account for older uncooperative runtimes: define and qualify a gating/migration or reliable
   OS writer-exclusion strategy. Install-root locks/process-name checks alone leave a race.
   Merely pinning a newer toolkit does not prevent an older retained binary using the same data.
3. Dispatch exclusive_image, zero_range and restore_times to native POSIX implementations.
   Linux: [fallocate(PUNCH_HOLE | KEEP_SIZE)](https://man7.org/linux/man-pages/man2/fallocate.2.html),
   not ZERO_RANGE (which may allocate extents). macOS: [F_PUNCHHOLE / fpunchhole_t](https://github.com/apple/darwin-xnu/blob/main/bsd/sys/fcntl.h)
   with filesystem-block-aligned offsets/lengths; retain unaligned edge blocks. Use Apple headers
   from the native SDK for ABI/constants. Unsupported filesystems must be reported as unavailable.
4. Preserve file size, identity, full hash and timestamps; only ranges read as all zero under
   the writer exclusion may be punched. A failed/partial/interrupted operation must keep all bytes.
   APFS clone/COW metadata allocation can fail too; test and report rather than claiming success.
5. Replace the Windows-only apply guards/capability in engine.compact_save_images,
   engine.run_disk_optimization and save_storage.exclusive_image **only after** native exclusion
   is established. The UI follows apply_supported automatically. Keep marker kind/version and
   cancellation/result contracts consistent; expand native tests rather than bypassing skips.

### Required native fixtures

- Two live runtime/install processes sharing one save root: exclude maintenance while either
  writer is active, including startup image normalization. Attempt a new writer during punching.
- Dense/sparse images with mixed nonzero/zero blocks, trailing zeros and unaligned EOF; full
  hash/length/identity/mtime preserved, allocated bytes reduced on supporting filesystems.
- Unsupported filesystem, partial failure, hard kill after the first real punch, retry, and new
  writes into holes. No image replacement or truncation, and no blind zeroing of nonzero bytes.
- Actual app inspect/apply/cancel/failure/no-savings flows, optional post-update offer and persisted
  success suppressing it. Report-only mode must not compact or mark completion.
- Native save/load/play from the compacted disposable root. Record original failures/platform
  limitations honestly; CI compilation alone is not this acceptance.
