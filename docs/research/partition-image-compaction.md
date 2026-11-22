# Experimental partition-image compaction (#180)

Target: v1.3.0, draft dependent on sparse-backup PR #300. Toolkit unchanged (`d108a64`).
Report-only allocation inspection works on all supported hosts; **apply is Windows-only**
until equivalent OS writer exclusion and deallocation are implemented and qualified elsewhere.
No HD texture changes or raw-image format/size changes are included.

## Design and safety

The engine accepts `--compact-save-images`, defaulting to metadata reporting only. Applying
requires the additional explicit `--apply-compaction`. It uses the receipt's data root under
the existing install/data/play locks and operates only on save/Partition0.img through
Partition5.img. Links/junctions, nonregular files and multiple hardlinks are refused.

Install-scoped play locks alone cannot exclude another installation sharing the same data.
Each Windows image is therefore opened with read/write access but only read sharing: existing
writers prevent opening, and new writers/deleters cannot open until compaction closes its
handle. This covers older runtime versions without requiring them to understand a new lock.

The file is hashed and fully scanned **before** deallocation. Only contiguous blocks read as
all zero become candidates; mixed blocks, even mostly zero, are retained. FSCTL_SET_SPARSE
and [FSCTL_SET_ZERO_DATA](https://learn.microsoft.com/windows/win32/api/winioctl/ni-winioctl-fsctl_set_zero_data)
then deallocate those proved-zero ranges without extending/changing logical content.
The latter's [range structure](https://learn.microsoft.com/windows/win32/api/winioctl/ns-winioctl-file_zero_data_information)
uses a first offset and an exclusive end. Another full hash and length check verifies the result.

There is no image replacement or temporary full-size copy. The same file identity, ownership,
ACLs and alternate streams remain; access/write times are restored via SetFileTime on the
already-owned handle. Data and timestamp changes are flushed. A failure/hard kill can leave
some zero ranges compacted and others dense; every affected range already contained zeros.
Nonzero ranges are never passed to the deallocation operation. This permits safe rerunning
after an interruption without a promotion journal or an interpretation of image contents.

The current prototype scans the whole logical image, including an already sparse image.
Allocation queries/range enumeration may later reduce that work. Unsupported Windows volumes,
read-only/locked images and unsupported apply platforms fail without changing image bytes.
Do not generalize the NTFS measurements below to other filesystems.

## Measured Windows NTFS result, 2026-11-21

The six historical raw images were first copied into a disposable dense fixture. The source
development save root was never modified. Compaction then ran through the engine's installed
receipt path on that lane's own fixture. SHA-256 hashes of all six images matched afterwards.

| Metric | Before | After |
|---|---:|---:|
| Logical image bytes | 5,243,406,848 | 5,243,406,848 |
| Allocated image bytes | 5,243,408,384 | 1,052,672 |
| File-content hashes | pinned fixture | identical |

The in-place scan/deallocation/verification took **22.18 seconds**, reclaiming
**5,242,355,712 bytes** on this fixture. Windows FileStandardInfo measured allocation.
The later SetFileTime-on-owned-handle refinement has focused timestamp/identity/ADS coverage;
it does not change the zero-range discovery/deallocation measured here.
Evidence: local `logs/compact-probe-final.json`, `compact-practical-final.log`.

This shows practical viability for zero-heavy dense images on the tested Windows filesystem.
An image that contains mostly nonzero data will reclaim much less. Removing images or shrinking
their logical geometry is neither needed nor supported by this prototype.

## Using the draft CLI

From reviewed source with an inspected setup payload:

```text
python setup/engine.py --payload <payload> --install-dir <install> --compact-save-images
python setup/engine.py --payload <payload> --install-dir <install> --compact-save-images --apply-compaction
```

No automatic run and no app Maintenance button are included. The payload's bundled Python
and engine can run the same arguments. There is no prerequisite to supply the original dump.

## Validation and remaining draft gates

- Focused engine/setup/backup/compaction checks: **163 passed, 10 skipped** before the final
  timestamp flush; original byte/hash/size, file identity, timestamps and alternate streams
  are preserved. Tests cover existing and racing writers from another install, partial ioctl
  failure, unsupported sparse support, same-root play lock, report-only default, hardlinks,
  numbered-image scope, hard kill after the first real zero-range deallocation and retry.
- A write-after-compaction test proves new nonzero data can allocate storage in a hole and
  remains intact after another compaction. No new format/geometry is introduced.
- Full available unit suite and final packaged CLI qualification are recorded in the PR;
  native game/runtime recompilation is not repeated for this setup-only prototype.
- Before ready/merge: owner-approved native save/load/play qualification from a compacted
  disposable data root, native Mac/Deck report-only checks, and a decision on non-Windows
  apply plus app UI. No original player images have been compacted by this work.

D-new: experimental compaction is report-only by default and explicitly applied only on
Windows. Use OS writer exclusion across install roots and deallocate proved-zero ranges in
place, preserving the file and all nonzero data. Keep the PR draft until native acceptance.
