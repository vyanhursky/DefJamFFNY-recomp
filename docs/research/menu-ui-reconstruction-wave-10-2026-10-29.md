# Menu/UI reconstruction batch ten — 2026-10-29

The owner approved the final nine batch-nine revisions and explicitly confirmed the other 82 original candidates. Together with the ten earlier revision approvals, all 101 reviewed batch-nine sources are now accepted. Exact pins are recorded in the two additive approval records; historical ledgers and the four held batch-nine sources remain unchanged.

There are **705 distinct accepted reconstruction mappings**: 390 in published 1.3 and 315 queued. The next **100 new mappings await review** at [the batch-ten viewer](http://127.0.0.1:51755/review.html#overview). Another **543 mappings still need restoration or resolution**: 525 unassigned and 18 held across all batches. These three groups sum to the tracked 1,348-mapping UI reconstruction inventory. Fragments, glyph atlases and thumbnails contribute mappings; this does not mean 543 whole text labels. Widescreen scenery is tracked separately.

## Review and method

The new selection covers venue handwriting and symbols, three countdown panels, result/user-ID stamps, a demo-select fighter banner and stat legend, fighting-style labels, vertical labels, tournament prompts and controller/training icons. There are 74 dark and 26 light artwork classifications. Source-container names do not establish actual runtime use.

Each original was checked directly. A bounded read-only classifier helped inspect remaining sources, but several suggestions had shifted keys or incomplete resources. Parent comparison corrected three demo-source pairings: METHOD MAN AS BLAZE, the six-row stat legend and KICKBOXING. Earlier wrong-text attempts remain superseded. The source spells CARRIBBEAN with two R and two B letters; the selected art retained it, and the incorrect navigation caption was fixed.

**D-new: use faithful smooth enlargements as edit references.** Nearest-neighbour inspection composites led seven small assets to reproduce enlarged raster steps despite prompt constraints. Their selected replacements use LANCZOS 6× source composites, with explicit preservation of intended curves, original font proportions and integrated artwork. Nearest-grid views remain useful for inspection, but should not be copied as future primary edit references.

Corrections also restored intentional black panels behind the gray countdown numerals, reduced added contours on plain cream labels, removed opaque blue/gray fields from stamps, and restrained overly bright spray/depth lining. The original 22×22 B-button core is reviewed separately from repeated edge samples; the complete 32×32 original remains preserved for later UV/gutter work.

These are reference-based reconstructions, not recovered original fonts or identical source alpha. Individual glyphs, spacing, weight, palette, material detail and partial opacity remain approximate. Selected controller shading is more resolved than the tiny source. Compare at 1× and 3×; original-bounds fitting is explicit preview placement, not proof of identical lettering. Saved superseded versions remain accessible in Detail.

## Accounting and validation

104 originals were assigned. Four are held outside the review: BARBERSHOP and TATTOO SHOP returned image-service output moderation blocks; AUCUNE IDENTITE and NO USER IDs were found to be earlier 4× baseline inputs, requiring original-source lookup. The first also has a cut frame edge. No output is invented for a blocked call, and neither baseline is presented as an original native-resolution comparison.

There were **143 issued built-in imagegen calls, 141 saved PNGs, two blocked outputs and zero prepared-unissued requests**. The selection has 100 sources; 41 saved outputs are superseded or held. All raw outputs, literal requests, actual reference paths and generated-default paths remain retained. No artwork subagents or API/CLI fallback were used.

Independent checks cover all 104 full inputs, all 141 default/raw/request records, the 100 selected exports and all 139 selected-source revision previews. Export retains generated alpha and RGB above alpha16 exactly; established low-alpha RGB bleed treats matte residue. No near-pure neon green remains in the selected visible or hidden pixels. Intentional controller green remains. One faint 21/255 border sample in NO USER ID SELECTED is retained; no selected border contains alpha128 ink. Final atlas gutters still need validation.

Parent inspected all 100 original/new pairs on blue and pale backgrounds at native size and magnified up to 3×. Final host Vision checks cover 156 original/draft inputs, with 128 nonempty recognition records and 35 normalized draft flags visually adjudicated. Single symbols, rotated text and brush lettering produce recognition misses. The sandbox's initial empty OCR result is retained as a diagnostic, not wording evidence.

Browser checks pass: 100 overview cards, 200 loaded overview canvases, all 300 source/scale detail combinations, 26 control/filter cases, no warnings/errors or document overflow. Context backdrops are comparison references, not new in-game captures.

The accepted-source union remains 705 and is disjoint from this new selection. Prior batch-nine original, nineteen-revision and nine-redo raw/preview pins remain unchanged, as does the published 1.3 archive. No game run, installation, publication or push occurred. Approved assembly still needs serial native layer, sampling, UV and gutter validation.

## Handoff

Source evidence: `config/menu-ui-reconstruction-wave-10-2026-10-29.json`. Private workspace and literal prompt set: `logs/menu-ui-wave10-20261029/`, especially `README.md`, `prompt-set.json`, current `batch.json`, `selection.json` and `review-data.json`. Historical preparation scripts record superseded classification; do not rerun them over the final selection. Every full input is copied under `source-originals/` and hash-pinned.

Additive recovery: `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave10-review-20261029`, pinned by `config/menu-ui-reconstruction-wave-10-checkpoint-2026-10-29.json` and chained to the final batch-nine approval checkpoint. Artwork and captures remain outside Git.

Next: owner review of these 100, exact selected-hash approval recording, then the remaining families and held original/effect-role investigations. Keep published 1.3 immutable. Any future PR belongs to milestone **v0.12.2**.
