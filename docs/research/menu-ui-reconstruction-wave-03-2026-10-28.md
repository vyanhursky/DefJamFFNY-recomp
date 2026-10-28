# UI reconstruction: 100 new sources and four alpha corrections — 2026-10-28

**Subsequent owner approval (2026-10-28):** all104textures accepted: “These are all perfect - send the next batch over.” Exact selected-preview hashes are pinned in `config/menu-ui-reconstruction-wave03-approval-2026-10-28.json`. Pending-review statements below are historical; native validation and publication remain separate.

The owner accepted all fifty textures in the previous batch with no issues and
requested a larger batch, explicitly suggesting parallel imagegen workers.
`config/menu-ui-reconstruction-wave02-approval-2026-10-28.json` pins that approval
to the fifty selected preview hashes. Earlier pending-review records remain
historical. Artwork approval does not establish native validation or authorize
publication of a new pack.

## Scope and independent generation

This wave targets **100 new source mappings**: 84 remaining two-fighter
resources and sixteen three-fighter variants. A contrasting-backdrop audit adds
four technical alpha corrections to earlier approved select studies (Nyne, Skull,
Ice-T and Solo), giving **104 distinct source mappings in this review**. Earlier
approved files remain immutable; the four corrections are new sibling studies. The 1,348 text-mapping baseline is
unchanged. These are new restorations within that baseline, not new discoveries.
The wider static inventory contains 2,337 distinct IDs: the earlier 2,129 and the
208 separately identified loading-name sources are disjoint by source ID.
Runtime-generated text and arbitrary font-cache permutations are not exhaustively
counted by that static census.

Three isolated workers own disjoint 34/34/32-source assignments. Completed
workers then take four earlier alpha corrections and three final source-material
corrections in fourth/fifth isolated folders. The owner's
explicit request permits parallel artwork generation beyond the repository's
usual read-only delegation restriction. Workers do not modify shared source,
run the game, assemble packs or publish. The parent handles source selection,
merging, export, independent checks and the combined review. Native runs remain
serial. No API/CLI fallback or third-party generation service is used.

Each source has its own built-in imagegen call, original reference and literal
prompt. Separate select/loading and two/three-fighter sources retain their own
letterforms, palette, line arrangement and ornament; no recolour or filename-only
reuse is inferred. Provisional inventory names are not text authority. Workers
visually verify the originals before generation, correcting several inaccurate
navigation names and historical variants. Raw attempts stay immutable and each
retry has a new revision.

The approved prompt direction preserves individual glyph sizes, spacing, stroke
weight, open counters, source tonal balance and existing wear while reconstructing
smooth high-resolution contours. It prohibits invented outer light rims, bevels,
extrusion and extra decorations. Original outlines, emblems and intentional
colours remain part of the design. Neutral reference backings are visibility aids
and must be absent from the transparent outputs.

## Transparency and source-art exceptions

Contrasting-background inspection exposed a limitation of pale neutral references:
original transparent letter faces can look like cream ink. Rome select, Teck
select, Erick Sermon select and House's three-fighter select require explicit
negative-space preservation. Workers audit actual RGBA on contrasting backdrops
and correct filled faces through new built-in imagegen revisions. Numeric source
samples also distinguish actual alpha-zero interiors from subdued dark translucent
ink: Skull tooth ridges and Solo/Pockets fine lines must not be erased as holes.
Brightness counts alone do not establish opacity. Bo/Cruz select keylines and
fingerprint material receive dedicated final revisions. Original opaque
cream and coloured faces remain opaque; Fam-Lay select, for example, has genuine
opaque light material. This is not a blanket colour-to-alpha conversion.

Erick Sermon's loading source also contains isolated opaque dark red/purple/green
blocks along its top edge. A bright-red-only test missed these; bounded original
pixel inspection confirms dark red [82,0,0,255]. These edge/palette artifacts are
excluded explicitly from reconstruction rather than interpreted as logo ornaments.
Its actual face gradient, lighter letter weight and counters remain source
constraints. Raw attempts and specific exceptions remain recorded.

## Review and validation

The combined review is prepared at `http://127.0.0.1:51744/review.html#overview`.
It retains the paired grid, search, select/loading filters, game backdrops,
1x/3x/6x detail, raw/fitted bounds and original ghost. Layout variants are labelled
explicitly; the group filter also isolates the four earlier alpha fixes. Outer-bound fitting is a preview transform, not proof of identical
individual glyph geometry or final atlas placement.

Exports use the existing modding tool RGB bleed from alpha>16 donors, restoring
every original alpha byte. RGB above alpha16 remains exact. Near-pure neon-green
checks use R/B<=8 and G>=247; genuine source green/teal/olive is preserved rather
than globally desaturated. Output/source hashes and every full literal prompt
will be pinned in `config/menu-ui-reconstruction-wave-03-2026-10-28.json`.

This is an artwork review batch. No game instance is stopped or run, no native
placement/blending/clipping coverage is inferred, and no candidate pack is
installed. Approved prior previews and scenery, published 1.2, the signed mod
register, game code and toolkit remain unchanged. Atlas assembly and native
validation are required before a release. No push is requested; future PRs use
milestone v0.12.2. Feature-branch state belongs here and in the handover rather
than `PROGRESS.md`.

Private workspace: `logs/menu-ui-wave03-20261028/`. All 104 detail cases and 208 overview canvases load. Search, select/loading
filters (54/50), resource filters (88 two-fighter / 16 three-fighter / four prior
alpha fixes), wraparound, new-only mode, all backdrops, 1x/3x/6x and raw/ghost
controls pass with zero console errors or page overflow. There are130saved successful built-in generations:104selected and26held. Every
raw PNG is independently hash-equal to its built-in default output, every
original/reference pin is checked, and all104selected exports preserve raw alpha
and RGB above alpha16 with zero near-pure neon-green texels. Prior50and27approved
previews remain independently byte-identical. The parent inspected all104final
matched source/draft rows on a blue backdrop; workers also review pale/dark
material and source-specific numeric RGBA samples. Raw-height errors span
-13.18% to+31.27% at matched width; fitted bounds are explicit, and raw view
remains available. This does not establish exact per-glyph geometry, original
wear locations or identical local tone/opacity. Residual variation is recorded
in worker QA rather than hidden by source-exact claims.

A self-contained recovery copy is stored at
`/Users/vlad/Code/defjam-data/scratch/menu-ui-wave03-review-20261028`, with full
original inputs, raw attempts, reference images, preview exports, static review
and source records. The manifest hash/count is pinned in
`config/menu-ui-reconstruction-wave-03-checkpoint-2026-10-28.json`.


## Continuation boundaries

The four earlier corrections are sibling drafts, not silent replacements of the
owner-approved fifty. The rest of that checkpoint remains unchanged. Contrasting
backdrop and source-opacity auditing must continue through prior masters before
atlas assembly; low-resolution source edges, existing grey/coloured ink and
transparent wear must be distinguished explicitly. Prior Bo/Cruz/WC select
previews are specific material-review candidates. Their pale outlines should not
be treated as established source ink merely because a paper preview looked good.
No broad colour-to-alpha or desaturation operation is authorized by those flags.
