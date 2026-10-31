# Menu/UI reconstruction batch 12 — 2026-10-29

The owner approved all 100 batch-eleven drafts at 51758 and requested another batch.
Exact selected raw/preview hashes are recorded in
`config/menu-ui-wave11-approval-2026-10-29.json`.
There are now **905 distinct accepted mappings**: 390 published in 1.3 and 515 queued.

[Review the next 100 drafts](http://127.0.0.1:51759/review.html#overview).
These 100 await approval. **324 unassigned + 19 held = 343** remain to restore or resolve;
including these pending drafts, 443 have not been accepted. The inventory contains 1348
mappings, including fragments, shared glyphs and variants, rather than 1348 whole words.
Wide scenery is counted separately.

## Source and artwork decisions

D-new: The parent owns generation/export/verification and issues parallel built-in calls,
one source/revision per call. Two bounded read-only classifiers supplied source evidence;
several proposed key/text/completeness claims were wrong and rejected. Actual mapped
native originals control the work. All 100 pairs were inspected on blue and pale at
native 1x and magnified up to 3x across 30 comparison sheets.

The batch covers controller prompts, match headings/stars, fighting-style stencil variants,
locked loading stamps, menu placards, paper elements and small labels. Each source keeps
its exact ID, full native PNG, dimensions and SHA. Inputs are faithful original 6x LANCZOS
gray/blue/pale composites. Preserve source-specific stencil gaps, weight, spacing, subdued
palette and alpha, actual line/stub geometry and cropped star fragments. Tiny rotated THE
is part of THE SOURCE branding; B.A. is not R.B.A. Two clipped BATTLE/OPTIONS pieces were
replaced before generation by complete C/venue-description placeholders from their own
sources. Prepared historical prompts remain separate from issued requests.

D-new: Six native 128x128 mainMenuButtons originals were recovered locally from the game
archive using the existing decoder and checked against source IDs. Earlier 512x512 files
were published baselines, not originals. Five recovered sources are selected; STORY remains
unselected because its fine print needs more investigation. The selected placards include
stretched lower atlas gutters. Review fits their artwork faces with logical bounds
`[0,0,native alpha128 right,90]`; full 128x128 originals remain byte-identical. This is face
artwork approval, not a complete native texture replacement. Full-canvas UV/gutter assembly
and in-game checks must precede installation.

D-new: Original placeholder fighter tiles are opaque white squares with small lettering.
Refined requests restore white margins instead of expanding the text to fill the tile.
Question-mark v2 invented a button; v3 removed the white. Both are superseded. Selected v4
requests opaque output to match its fully opaque source. Other corrections restore B.A.,
wide L-button proportions, clean cream PRESS TO CONTINUE lettering, seven source-specific
star edges/fragments and notebook/KO baked shadows. MATCH ENFER v2 gained an opaque band;
v3 restores transparent negative spaces. No scripted lettering/color/alpha repairs.

## Evidence and limits

- 124 issued built-in calls and 124 saved raw PNGs: 100 selected, 24 superseded, no failures.
  28 historical prepared prompt versions were never issued. Every actual request/result,
  default generated path and raw copy is pinned. No CLI/API fallback or artwork subagents.
- 100 selected native source pins, all 124 request/default/raw pins and all 124 revision
  exports verified. Generated alpha and RGB where alpha>16 are exact. Only existing
  low-alpha RGB bleed is applied. Selected exports contain no near-pure neon-green pixels;
  parent also inspected actual composites for green/pink contamination.
- 124 local Vision OCR readings, all nonempty, with 21 draft flags visually adjudicated.
  Stylized glyphs, rotated THE, stars and distressed stamps confuse OCR; it is a wording
  cross-check, not font/geometry proof.
- 100 browser cards/200 canvases, 300 detail-scale cases and 38 controls passed. No browser
  warnings/errors or page overflow. Filters, search, backdrops, saved revisions, original
  ghost and raw proportions work.
- Previous 100 approved raw/preview pins, the 905 accepted-source union and immutable
  published 1.3 archive verified; new selection is disjoint from accepted IDs.

D-new: Ten selected raw borders reach alpha>=128: nine actual source-specific rules/star
cuts plus one intentionally opaque white tile. Preserve raw and inspect native gutters.
Individual letter shapes, stencil cuts, material, color, partial opacity and baked shadows
remain approximate. Matched outer bounds are explicit preview fitting, not atlas placement.
No new game run, install, capture or publication occurred. Published 1.3/catalogue7 remain
unchanged. Approved assembly still needs serial native UV/gutter/layer/sampling checks.

## Recovery and next steps

Source ledger: `config/menu-ui-reconstruction-wave-12-2026-10-29.json`.
Private workspace: `logs/menu-ui-wave12-20261029/`, including literal prompts, native originals,
all raw revisions, previews, contacts, OCR, browser proof and integrity receipts.
Additive recovery: `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave12-review-20261029`,
chained to batch eleven; manifest pin in
`config/menu-ui-reconstruction-wave-12-checkpoint-2026-10-29.json`.
Artwork remains untracked. Prior reviews are unchanged.

Next: owner reviews 100; record exact selected-hash approvals, handle exceptions, then
continue unassigned/held families and approved native assembly. Future PR milestone is
v0.12.2. This feature branch does not edit PROGRESS.md; no push.
