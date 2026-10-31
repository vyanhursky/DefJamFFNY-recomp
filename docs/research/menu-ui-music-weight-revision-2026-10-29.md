# Music-list UI weight revision — 2026-10-29

Vlad found the plain music-list lettering too skinny at 1×, specifically Exclusive, Hot New Shit and Method Man. He asked to increase weight and preserve the stylized fonts. This pass revises **45 plain music labels, titles and credits**, while keeping **five stylized or unrelated textures exactly unchanged**. It does not infer approval of the revised music text.

[Review at native 1×](http://127.0.0.1:51749/review.html#overview). Detail compares original / previous draft / new weight revision. Overview defaults to previous + new; original + new is also available. The 1× detail uses one CSS pixel per original texel at 100% browser zoom. Larger overview comparisons fit down only when the card requires it. Paper/brick are comparison backdrops, not verified native context claims.

## Weight and fidelity

The first three revisions gained useful small-size weight but rounded terminal cuts. One bounded correction restored the previous flat cuts while preserving stronger strokes. The remaining disjoint artwork lanes used the same approach, with separate corrections where weight edits turned smooth bowls into chamfers or changed round dots. Every original, previous draft and new raw remains preserved; no dilation, alternate font renderer or synthetic text image replaces imagegen.

The source still governs case, punctuation, spacing, open counters, palette and opacity. Numeric native-alpha coverage is a diagnostic, not a target that overrides the 1× visual comparison. The new typeface reconstruction remains approximate. **Volume 10 retains more angular bowls in its selected heavier draft**; its one targeted curve correction returned no image. That residual is disclosed on its detail page. Other source-specific differences are in `weight_revision_review_note` and the literal prompt ledger. New drafts await owner review, not acceptance as exact font matches.

CHOOSE MATCH TYPE, OPTIONS, handwritten P1, SELECT and SHOP DISTRICT retain their previous raw and preview pixels. All earlier accepted fighter banners, headings and other stylized art were outside the generation assignment. Freeway remains held from the previous batch and was not retried in this pass.

## Evidence and preservation

Three disjoint workers each revised 15 music sources using the built-in imagegen tool, one asset/revision per call. **61 actual calls: 57 successful saved PNG attempts and 4 failed calls; 45 selected new images and 12 saved alternates.** No prepared request is counted as a successful image. Failed ordinary artist/title calls and exact identical retries are retained separately; no CLI/API fallback or prompt-filter workaround was used.

Every request has the exact pre-call six fields; every successful receipt adds the actual built-in default PNG path and a byte-identical workspace copy. Reference and original hashes, source atlas size/crop/bounds and all previous drafts are pinned. Parent inspected all selected original/previous/new comparisons at 1× and magnified scale; worker blue/pale and full-resolution contour checks supplement those inspections.

Every selected export retains all generated alpha bytes and RGB above alpha16. The existing neighbour-colour bleed treats only low-coverage matte RGB. Near-pure neon-green checks pass, while intentional source colours remain. The five protected previews are pixel-identical and all old batch-seven raw/preview pins remain unchanged. Prior 450 accepted IDs and the published 1.3 archive retain their pins.

Browser verification covers all 50 detail entries, 100 paired overview canvases, 56 control/alternate cases, native1× and3×/6×, fitted/raw proportions, ghost overlay, filter/search/navigation and comparison backdrops. There are zero console errors or page overflow. These are artwork previews: no new pack installation, native capture, runtime sampling validation or publication is claimed.

Source-only ledger: `config/menu-ui-music-weight-revision-2026-10-29.json`. Private workspace: `logs/menu-ui-weight-revision-20261029/`. Additive recovery: `/Users/vlad/Code/defjam-data/scratch/menu-ui-weight-review-20261029`, pinned by `config/menu-ui-music-weight-checkpoint-2026-10-29.json`. Serve its root on localhost51749 to restore the review. Prior viewer51748 and recovery remain immutable. Published 1.3/catalogue7, game/toolkit/setup/saves and live tools8768 writer are unchanged. The accepted wave06 set of60 remains queued for the next release. Future source PRs use the owner's requested v0.12.2 milestone.
