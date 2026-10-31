# Four held UI corrections and full lossless experiment — 2026-10-30

Owner accepted the other held items and requested four corrections, followed by
lossless compression and a reusable Modding Tools procedure. Visual approval of
11 generated holds is pinned in `config/menu-ui-held-rest-approval-2026-10-30.json`;
five earlier tool-blocked mappings are accepted as baseline retention only.
**1,339 accepted restoration mappings: 390 published, 949 queued. Four new corrections
await review; five retained baselines have no new remaster.** Total tracked mappings: 1,348.

## Four corrections

Review: http://127.0.0.1:51764/review.html#overview . Source ledger:
`config/menu-ui-held-corrections-2026-10-30.json`. Private workspace:
`logs/menu-ui-held-fixes-20261030/`. Six literal built-in imagegen outputs; four
new review selections and two superseded attempts. All prompts, input/reference
hashes and original raw PNGs are saved. No automatic owner approval.

- GAGNANT v3 removes the added opaque backing/depth treatment. The comparison
  isolates the logical stamp and excludes the separate native white corner.
  The held 128×8 bottom material `37f74072` is only one piece of the complete 149×72
  artwork. Main/right context and detached 21×8 white context `8412529f` must be
  reconciled explicitly; previously approved neighbours are not silently replaced.
- NO USER IDs v5 restores transparent negative space and subdued burgundy ink.
- Dark/red venue symbols v2 reference only the original sampled 35×34 badge in
  native 64×64 canvases. The earlier generated cream plaques are removed. Stretched
  gutters were excluded from the art references. Source shapes 36/96 have fractional
  near-zero UV offsets; native UV/gutter reconstruction remains due.

Parent inspected the raw PNGs composited on blue and pale fields, then fitted
original/draft comparisons. The browser loaded four cards/eight overview canvases,
all four selected revisions at 1×/3×/6×, and raw-proportion/ghost controls without
errors. Screenshot and `browser-qa.json` are private. Letter/detail/spray fidelity
remains approximate pending owner review; this is not a native game capture.

## Compression measurements

Oxipng 10.2.1; conservative `-o4 --nx --interlace keep --threads 1 --timeout 60`,
four workers per dataset. No alpha optimization, palette/bit-depth transformations
or metadata stripping. The game receives the same PNG format and RGBA values.

| Dataset | PNGs | Before bytes | After bytes | Saved bytes |
|---|---:|---:|---:|---:|
| Published 1.3 PNGs | 1,704 | 682,774,940 | 573,469,182 | 109,305,758 (16.01%) |
| Approved queued review crops | 949 | 648,007,579 | 574,491,068 | 73,516,511 (11.35%) |

Both complete datasets passed every decoded RGBA8 byte, including RGB under zero
alpha, exact dimensions, all non-IDAT chunk payloads/order, unchanged input hashes
and output write verification. Zero verification failures or unsupported files.
Published PNG experiment took 713.4 s; queued crops 652.7 s
(the jobs ran concurrently). Per-file receipts remain private and are pinned in
`compression-summary.json`; source summary is in
`config/menu-ui-lossless-experiment-2026-10-30.json`.

The existing ZIP is 679,627,331 bytes. Recompressing every changed
PNG as raw DEFLATE level 1, while verifying each original stream length against
its released ZIP member, saves 108,045,093 payload bytes
(15.90% of the archive). With unchanged member/header
structure and non-PNG files, projected ZIP size is
571,582,238 bytes. This is a payload calculation,
not a rebuilt, re-signed or installable release. All 1,704 original PNG member hashes
also matched the published ZIP. Full native pack file bytes would drop from
683,803,577 to 574,497,819 with these PNG substitutions.

The four new RAW imagegen files were a separate negative control. Oxipng removed
`caBX` provenance chunks; all four candidates were rejected and exact originals
retained (5,271,642 bytes before/after). Raw masters and rejected
attempts remain immutable. No metadata was silently stripped to obtain savings.

## Reusable tooling and recommendation

`DefJam-Modding-Tools/src/defjam_tools/png_optimize.py` and alias
`defjam-tools optimize-png` implement fresh-directory copy-only optimization,
strict RGBA/chunk/hash verification, smaller-only selection and JSON receipts.
Directory or selected-file manifests are supported. Symlinks, unsafe relative paths,
case collisions, existing outputs and overlapping trees are rejected. APNG/16-bit
files retain original bytes with an explicit skipped status. Failed optimizer or
verification attempts retain originals and return nonzero. No review import,
server restart, workspace mutation or automatic installation occurs.

Procedure: `/Users/vlad/Code/DefJam-Modding-Tools/docs/lossless-png.md`.
16 focused tests include real Oxipng, hidden-RGB changes, metadata deletion, corrupt
CRC, output safety and receipt/source immutability. Full suite: 83 passes / 12 subtests;
initial sandbox localhost failures passed with host access. Wheel build includes
exact new module. Source-only hygiene check: 475 files/zero failures.

Apply this step to approved **final native exports**, before packaging and signing
new immutable release/catalogue artifacts. Keep originals/raws for rollback and
provenance. Measure the final archive again; do not add current native pack and
queued preview sizes as a future release estimate. PNG optimization reduces disk
and download bytes, not decoded GPU texture memory. No game update is required
solely for this same-format lossless recompression; final native atlas/alpha/UV/
gutter reconciliation and normal loader/native checks are still required for
integrating the new artwork. Published 1.3/catalogue 7 are unchanged.

References: [Oxipng](https://github.com/oxipng/oxipng),
[PNG specification](https://www.w3.org/TR/png-3/).
