# Menu/UI reconstruction batch fourteen — 2026-10-30

Vlad approved all 100 native mappings in batch thirteen, spanning 50 joined labels. The exact selected raw, preview and shared-master hashes are pinned in `config/menu-ui-wave13-approval-2026-10-30.json`. His approval follows the delivered review on port 51760; the ambient browser address still pointed to the older, already approved batch twelve.

**1,105 mappings are accepted:** 390 published in modpack 1.3 and 715 queued. The [new review](http://127.0.0.1:51761/review.html#overview) contains **100 new mappings across 49 complete artworks**, with an [individual-piece view](http://127.0.0.1:51761/pieces.html#overview). After this batch, 124 unassigned plus 19 held mappings leave **143 to restore or resolve**. Including these 100 pending candidates, 243 await acceptance. The inventory contains 1,348 native mappings, which include fragments and are not all whole words; widescreen scenery is counted separately.

## Source reconstruction and generation

The selection comprises four single-material match emblems, 42 labels made from two materials, and three descriptions made from four materials. There are 96 mappings from `battle/cmtype` and four from `intMain/prestart`: match headings, handwritten slogans, English/French descriptions, and both startup prompts.

The original object ELF material relocations, model scales, compressed quad vertices and UV matrices identify each source rectangle and its adjoining placement. All 100 native originals were decoded anew from the user's own archive and their source IDs verified. All 49 original RGBA assemblies are exact, with coverage one and no overlap or gap. Multi-material coordinates round by less than 0.04 native pixels. The four centered single-material quads use half-pixel origins; their local origin is normalized without resampling the source image. Static metadata does not establish the runtime's filtering or sampling behavior.

The parent issued **56 built-in imagegen calls**, retaining 56 literal raw outputs: 49 selected masters and 7 superseded attempts, with no failed or unissued requests. No artwork subagents or CLI/API fallback were used. WINDOW MATCH v2 restores the original opaque white shattered-glass corners omitted by v1. MATCH DEMOLITION, LA CAGE and CHACUN POUR SOI received edge-colour corrections after the pixel check detected sparse green extraction specks. Exact prompts and all raw revisions remain in the private workspace. CHACUN POUR SOI v2 thinned its black border; final v3 uses blue/pale composites of v1 to preserve that border and shadow while cleaning colour. LA CAGE final v4 uses neutral warm ink.

Every selected native candidate is an integer crop of the same complete master as its adjoining pieces. Reassembling the one, two or four rectangles reproduces the full raw master RGBA exactly. All 56 master exports and 113 piece exports preserve alpha and RGB where alpha exceeds 16; only established low-alpha RGB bleed is applied. These variable-size candidate crops are not finished native canvases and must not be copied directly into the pack.

## Review and verification

The parent inspected all 49 original/draft pairs on blue and pale backgrounds, at native 1× and magnification up to 3×, in 17 comparison sheets. Changed masters were inspected again. Original stencil cuts, mixed letter heights, subdued amber/cream/red, genuine white/black emblem regions and soft shadows remain the constraints. Individual glyph paths, weight, spacing, small emblem detail, material, opacity and preview registration remain approximate and require owner review.

Selected masters have no near-pure neon-green or green-dominant visible samples under the documented check, and no outer-border samples above alpha 16. Internal crop edges can cross real ink; native gutters still require validation.

Local Vision OCR checked 98 inputs, with 97 nonempty readings and 2 draft mismatches adjudicated visually. OCR checks wording and does not validate typography. The viewer transcription for the French reward description was corrected to the original “DANS LE SCENAR”; the generated artwork already matched it. The issued request’s earlier plural transcription remains immutable history. Browser checks covered 49 complete-artwork cards/98 canvases, 100 piece cards/200 canvases, 147 artwork and 300 piece detail/scale cases, plus changed-master rechecks. Backdrops, filters, search, raw proportions, original ghost and revision switching were checked. No loading errors, console warnings/errors or page overflow remained.

## Saved state and next steps

The source ledger is `config/menu-ui-reconstruction-wave-14-2026-10-30.json`. Artwork, prompts, request/result history, raw outputs, derived crops, comparisons and QA receipts remain private in `logs/menu-ui-wave14-20261030/`. The additive recovery checkpoint is separately pinned and chained to batch thirteen. Independent APFS copy-on-write files preserve the workspace without hard links or deletion of older artwork. The owner's disk cleanup freed space during generation.

There was no new native game run, installation, publication, catalogue change, push or PR. Published modpack 1.3 and catalogue revision 7 remain unchanged. Future PRs use milestone **v0.12.2**.

Next: review these 100 candidates and pin exact approvals; restore the remaining 124 and resolve the 19 held mappings; assemble approved artwork into full native canvases with correct gutters/layers, then run serial native placement, clipping, blending and sampling checks before publication.
