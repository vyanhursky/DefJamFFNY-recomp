# Menu/UI reconstruction batch nine — 2026-10-29

Vlad requested: “Generate the next 100 for now. I will approve the 4 in about 2 hours”. This authorizes a new review batch; it does not approve the separate four stencil revisions or authorize publication. The accepted count remains 600 distinct source IDs, including the immutable published 390 and 210 queued for a future update.

## Review

[101 new menu/UI candidates](http://127.0.0.1:51752/review.html#overview): 36 dark and 65 light/gray sources across 17 families. These include shop/training labels, handwritten descriptions, plain music-list text, credits, prompts, statistics, and complete illustrated/promotional/demo menu artwork. The original source identity is verified; container names do not establish runtime use. Promotional BEATBOX is a different source/artwork from the pending stencil BEATBOX.

The [four pending stencil revisions](http://127.0.0.1:51751/review.html#overview) — STORY CHAMPS, BEATBOX, CRIB and stencil MAP — retain their exact prior raw and preview hashes. No approval is inferred from the anticipated review time.

Quick review has family/search/letter-colour filters and original/new comparisons. Detail includes original, published 1.3 or original fallback, selected draft, 1×/3×/6× scales, explicit outer-bounds fitting, raw proportions, original ghost and comparison backdrops. Saved older attempts are labelled **superseded**, excluded from the selected batch. Reference backgrounds are comparison aids; these are not new in-game captures.

## Generation and fidelity

105 distinct originals were assigned: 63 live-source candidates and 42 complete controls/menu-art candidates. Parent validated source RGBA and blue/pale composites, correcting classification mistakes including B versus a lock, L-only rotation prompts and unaccented source spelling SANTE / PRET !. One read-only classifier subagent helped inventory controls; all artwork calls and corrections were issued directly by the parent using the built-in image generator. There was no API/CLI fallback or artwork-generation subagent.

Actual counts: **121 issued calls, 120 saved PNGs, one failed output, 101 selected, 19 superseded-or-held PNGs**. Forty-two initial controls requests were prepared but never issued: their delimiter wording was corrected before generation, with old preparations retained and marked unissued. These are not failed calls or generated images. Six-field requests and eight-field successful-result receipts preserve literal prompts, actual input paths, generated defaults and byte-identical workspace copies.

Four assigned sources are held outside the review: Bless returned no image; copyright lettering remained warm/dark after one correction; cast-role gray remained too dark after one correction; PRET ! retained an unwanted dark contour and clipped halo in its final accent-removal edit. No fallback artwork, recolour or alpha repair replaces them. All attempts and the actual failure receipt remain saved.

The bounded corrections removed accidental prompt-delimiter footers from P4, cream4 and blackYES; cleaned an autosave alpha blotch; improved COST weight, the gold warning, EXTRAS terminals, additional-cast gray and NEW tone. WINNER/READY!/GAGNANT restore transparent inner fields instead of the first drafts' opaque black panels. Genuine source outlines, shadows, gray ink, yellow/yellow-green/gold colour and illustrated details are intentional references, not blanket fringe-removal targets.

These remain reference-based reconstructions, not recovered original fonts or identical source alpha. Glyph widths, counters, spacing, material detail and partial opacity differ. Several plain labels/credits have fuller stems. COST is brighter cream, additional-cast gray still slightly darker, and the gold warning remains more muted/darker; source-specific notes are visible in Detail and `review-notes.json`. The approved firmer music weight applies only to plain music-list text, not every stylized font.

## Validation and preservation

Parent inspected all 104 successful first-pass original/new pairs at native 1× and magnified up to 3× on blue/pale, then all 15 bounded correction pairs and the final PRET edit. Contact sheets and first-pass selections remain retained. Local macOS Vision flagged text mismatches for visual adjudication; its 208 initial inputs and 26 versioned correction inputs are pinned. OCR is an aid, not exact text/typography proof. The revised 4 and READY! punctuation were visually confirmed despite OCR misses. The unsuccessful PRET v4 correctly removed its invented accent but failed material/edge review, so remains held.

Independent checks verify all 105 source pins, all 120 generated-default/raw/request pins, exhaustive success/failure/unissued accounting, generated alpha and RGB above alpha16 retained on export, and the same contract for all 113 selected-source revision previews. No near-pure neon-green pixels remain in selected exports; intentional coloured ink is preserved. Selected borders have alpha at most16; held attempts keep their actual border statistics. Low-alpha RGB bleed uses the established tooling and restores every generated alpha byte; it does not fix generated-art geometry, outline or colour mistakes.

Browser checks: 101 detail entries, 202 overview canvases, 24 control cases, zero console warnings/errors or document overflow. Long comparisons scroll within their panels. All 600 accepted source IDs remain disjoint from the new batch; prior approved previews, all four pending stencil raw/previews and published 1.3 ZIP hashes remain unchanged. No game process, native run, install, catalogue update, publication or push occurred.

Source evidence: `config/menu-ui-reconstruction-wave-09-2026-10-29.json`. Private artwork/workspace: `logs/menu-ui-wave09-20261029/`. Additive recovery: `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave09-review-20261029`, pinned by `config/menu-ui-reconstruction-wave-09-checkpoint-2026-10-29.json`, chained to the prior stencil-revision checkpoint. Artwork, original textures, raw PNGs and captures remain outside Git.

Next: owner reviews the 101 candidates and separate four stencil revisions; record explicit approvals with exact selected hashes. Remaining inventory is 629 unassigned mappings, not 629 complete text assets, plus held sources/effect-role investigation. Atlas assembly, sampling/layering and serial native validation follow approval. Any future PR belongs to milestone **v0.12.2**.
