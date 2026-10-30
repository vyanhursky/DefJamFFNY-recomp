# Menu/UI reconstruction batch 13 — 2026-10-30

The owner approved all100batch-twelve drafts at51759 and requested the next batch.
Exact hashes are recorded in `config/menu-ui-wave12-approval-2026-10-30.json`.
There are **1005 distinct accepted mappings**:390published in1.3 and615queued.

[Review the next100texture mappings as50complete labels](http://127.0.0.1:51760/review.html#overview),
or [inspect all100individual pieces](http://127.0.0.1:51760/pieces.html#overview).
All100are new and await approval. **224unassigned+19held=243**still need restoration
or resolution. Including these100pending candidates,343are not accepted, out of1348
tracked mappings. Mappings include fragments and shared glyphs, not just whole words.
Wide scenery is counted separately.

## Joined-source restoration

D-new: Most remaining menu labels are split across texture materials. Restore each
complete label from proven source geometry, then derive its pieces from ONE generated
master. This batch is50complete labels covering100native texture IDs, with50imagegen
calls; it is not100whole words or100independent calls. Joined review makes typography
and joins easier to judge; the individual-piece view preserves source-level review.

The original mainMenu and cmtype ELF objects identify both XSH names per shape through
material relocations. The prior UV-audit object decoder reads compressed quad vertices,
model scales and UV matrices. Selected matrices are identity2D plus translation. Rounding
by less than0.04native pixels yields adjoining rectangles with coverage exactly1and no
missing/overlapping pixels. All100native originals were decoded anew from the archive,
matching source IDs and dimensions. Joined original references reproduce the exact RGBA
of those integer UV crops; the full native PNGs remain byte-identical. No tile-order or
missing wording was inferred from filename adjacency. Static source provenance still
does not prove runtime frame selection or final replacement registration.

The selection contains39mainMenu labels/78mappings and11cmtype labels/22mappings:
cream distressed headings, amber handwritten slogans, white condensed descriptions and
staggered match labels, including French variants. Preserve each source’s actual font,
stroke weight, spacing, row offset, stencil cuts, punctuation, muted palette and baked
shadow. Faithful6xLANCZOS gray/blue/pale original composites control generation. Parent
checked all50source/draft pairs on blue/pale, native1x and up to3x, in17contact sheets.
Two bounded read-only classifiers supplied evidence; several key/text claims were wrong
and rejected. Parent owns artwork generation/export/verification; no artwork subagents.

D-new: Candidate pieces are lossless integer slices of the literal generated master.
Their boundary follows original material geometry through explicit joined alpha128
outer-bounds fitting. Each pair concatenates back to the raw master’s exact RGBA.
These are derived crops, not independent tool outputs or finished native canvases.
Master and piece previews preserve alpha and RGB wherealpha>16exactly; only established
low-alphaRGBbleed is applied. There is no scripted letter, colour, alpha-mask or font
repair. Final source canvas/gutter/layer/sampling assembly remains due.

## Verification and limits

-50issued built-in calls,50literal raw masters,100selected native mappings. No failed,
  superseded or prepared-unissued calls. Literal requests/results/default paths and raw
  copies are preserved. No CLI/API fallback.
-100native source pins,50raw/request/default pins,50master+100crop export checks and
  50raw pixel-concatenation checks passed. Reconstructed50original joins exactly match
  their native sampled crops. Prior100approved raw/preview pins, accepted1005union and
  immutable published1.3archive verified; new IDs are disjoint from accepted IDs.
-100local Vision OCR inputs,98nonempty readings,9draft flags visually adjudicated.
  Distressed stencil glyphs, numeral1and staggered layouts confuse OCR; lettering was
  checked against originals rather than changed to satisfy recognition.
-Browser:50joined cards/100canvases;100piece cards/200canvases;450detail-scale cases
  and26controls passed, with no warnings/errors/overflow.1x/3x/6x, raw proportions,
  original ghost, family/letter filters, search, comparison modes and backdrops work.
-No pure-neon or green-dominant selected-master findings. One raw master has faint
  border alpha20/255, with no alpha128border ink; keep raw and validate native guards.
  Inner crop boundaries intentionally carry continuous ink from the shared master.

D-new: Word shapes, stencil gaps, weight/spacing, outlines, material, colour, partial
opacity and baked shadows remain approximate. Preview bounds fitting is explicit and
does not prove exact per-glyph alignment. Native UV provenance and coherent candidate
cuts still require full source-canvas/gutter/layer/filter/sampling checks in serial game
runs before shipping. No new game run, install, capture or publication occurred.
Published1.3/catalogue7remain immutable.

## Recovery and next steps

Ledger: `config/menu-ui-reconstruction-wave-13-2026-10-30.json`.
Private workspace: `logs/menu-ui-wave13-20261030/`, including native originals, geometry,
joined references, literal raw masters, derived pieces, prompts, previews and QA receipts.
Additive recovery: `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave13-review-20261030`,
chained to batch12; manifest pin in
`config/menu-ui-reconstruction-wave-13-checkpoint-2026-10-30.json`.
Artwork remains untracked; earlier reviews are unchanged. A full-copy space guard failed
(681MiBfree/475MiBworkspace), so recovery uses independent APFS copy-on-write clones
via cp-c, with all hashes verified. No hard links or existing-file deletion.

Next: owner reviews50complete labels/100native mappings, exact selected100piece hashes
and shared50master hashes on approval, exceptions and remaining224unassigned/19held,
then approved native assembly/serial checks. Future PR milestonev0.12.2. No PROGRESS.md
edit on this feature branch; no push.
