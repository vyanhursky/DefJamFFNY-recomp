# Workshop fighter UI artwork

This extends the standalone CAF/outfit work with editable presentation resources.
No game art or captures are part of this source change. Original profile saves,
legacy portrait resources and CAF recipe versions remain supported.

## Original-game audit

The verified dump uses selection 56 for Blaze (Method Man), with costumes 81/82;
Pockets uses selection 76. Selector movie names use selection + 1, while titlecard
names use the selection itself. Costume portraits differ and most titlecards are
shared. Loading portraits are independent close-ups, not selector thumbnails.

Each fighter needs eight roles in each 2/3/4-player layout: selector portrait,
result icon, selector titlecard, result titlecard, loading portrait, loading
titlecard, normal grid icon and selected grid icon. Original canvases vary:

| Blaze asset | 2 players | 3 players | 4 players |
|---|---|---|---|
| Selector | 212×377 | 164×374 | 109×309 |
| Result | 44×44 | 39×39 | 32×32 |
| Selector titlecard | 261×73 | 188×62 | 139×59 |
| Result titlecard | 238×59 | 178×58 | 139×48 |
| Loading | 290×334 | 222×337 | 379×314 |
| Loading titlecard | 202×99 | 167×85 | 180×69 |

Grid templates use a single original 64×64 DXT5 raster and retain existing normal
and selected native geometry. Retail reference export derives their placeholders
from the donor result portrait; authors can import separate grid states.

## Typed source contract

`eagl-portrait-png-1` has exactly `format`, retail `donor`, `hd_scale` (1, 2 or 4)
and `images`. Images map role names to relative PNG paths and SHA-256 digests.
The six master roles are `selector`, `loading`, `icon`, `titlecard`, `grid_normal`
and `grid_selected`. Exact layout roles use the existing 24 native part names;
an exact role overrides its master. Missing non-grid art uses the retail donor.

Each source PNG must be 32–2048 pixels per side, at most 4 MiB, with visible alpha.
Decoded unique images are capped at 64 megapixels; native and HD output together
are capped at 64 MiB per resource, within the existing complete-pack budget.
The compiler writes only original raster pixel spans, retaining movie actions,
geometry, layout and material control bytes. Exact donor canvases at 1×/2×/4×
preserve framing. Other shapes are contained in the largest fully covered region;
non-exact result images and grid images use a top-centered square crop.

`fighter-contract.py export-ui-reference --game … --donor retail/blaze
--portrait-out …` exports the 24 original PNGs and layout/hash receipt. Ordinary
`validate` compiles authored PNG resources, including all outfit references.
Workshop projects embed PNGs in version 4, with shared defaults and sparse outfit
overrides; the exported CAF recipe remains version 3.

## HD activation and launcher contract

HD tiles are sampled directly from the author PNG, preserving transparent tile
padding. The native compiled texture's XRTEX01 identifier keys the replacement.
Conflicting HD PNGs for the same native identifier are refused. A verified
content-addressed `textures-v1` cache is staged in the managed mods directory;
`RECOMP_FIGHTER_UI_TEXTURE_PACK` activates it last for this launch without changing
persisted texture selection. Unexpected files, changed hashes, redirected paths
and native texture-list overflow are refused. Pack disablement omits the layer.

Managed launch also admits `CAF_EXTRAS` and `CAF_EXTRAS_SHA256`. Their absence in
the old native allowlist caused the reported unsupported-runtime-setting error
for textured CAF packs. The producer/consumer regression test now exercises both
ordinary CAF extras and optional UI-layer projection through the actual producer.

## Validation

Windows release build uses the existing pinned toolkit; no toolkit changes.
Invented fixtures cover all role routing, original control/pixel holds, PNG/path/
hash/budget refusal, HD IDs, collisions, staging/tampering and native launch
admission. The native bridge aborts if settings persistence is called, and tests
missing/redirected caches, traversal, root override and list-budget refusal.

The real Windows Qt/WebChannel workflow passes 23 steps, including full retail
import, independent titlecard preview, exact PNG picker bytes, outfit inheritance,
local override/clear, Undo/Reset, save/reopen and actual native compiler export.
Full compilation qualifies all 24 roles for all three outfits; this is separate
from screenshots/gameplay. A normal managed-launch boot of that pack passes:
16 present samples, median 120/minimum 108 per two seconds, zero crashes,
watchdogs, unresolved calls or debug-layer errors, and identical save restoration.
The log confirms the HD UI layer, three CAF recipes and three extras admitted.

Private receipts: `ui-art-ui-proof1/receipt.json`, `ui-art-focused-tests.txt`,
`ui-art-managed-boot.txt`, and `run-20261109-201732.log.err`. Additional native
selector/loading/result acceptance is recorded in the PR handoff. Native Windows
evidence does not claim native macOS/Linux gameplay or AI-restored artwork.
