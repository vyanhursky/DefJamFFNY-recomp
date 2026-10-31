# Menu/UI reconstruction batch seven — 2026-10-28

The preceding 60 four-fighter banners are now explicitly approved, with exact raw/preview pins in `config/menu-ui-reconstruction-wave06-approval-2026-10-28.json`. They were approved after 1.3.0 archive freeze and remain queued for the next pack update. HD Widescreen Menus 1.3.0 is published separately in signed catalogue revision 7; see [publication evidence](menu-ui-v1.3-publication-2026-10-28.md).

## New review

[Review 50 new textures](http://127.0.0.1:51748/review.html#overview): standalone headings/controls, music titles and artist names, plus one handwritten P1 indicator. There are **41 dark and 9 light** previews. Three disjoint artwork workers finished with 11/23/17 assigned sources after six untouched sources transferred and one replacement was added. All source IDs are distinct from the prior 450 accepted mappings.

**51 originals inspected; 50 have selected preview images; one source is held without an image.** There were **80 actual builtin calls**: 72 successful immutable PNG attempts and 8 failed issued calls. The 50 selected PNGs leave 22 saved alternate attempts. There are zero unissued prepared requests. Freeway failed twice at builtin output moderation; no image was returned and it remains incomplete. P1 is a separate genuine source, not a substitute for Freeway's design or identity. No API/CLI generation fallback was used.

Each source retains original/reference SHA-256, full atlas size, crop and original alpha bounds. Literal six-field requests were saved before calls; eight-field result receipts retain the actual builtin default path and a byte-identical workspace copy. All raw outputs and actual failures remain local and immutable. Every selected export preserves generated alpha and RGB above alpha16 exactly; low-coverage RGB bleed removes matte residue. All 50 exports pass bounded near-pure green checks, including hidden RGB. This does not authorize deleting intentional colours or treating source grey as transparent.

## Fidelity and limits

This is a new plain condensed text family, not an extension of the distressed fighter-banner style. The parent inspected all 50 source/draft pairs on both blue and pale backgrounds. Bounded revisions clean raster microsteps, reduce broad/heavy substitutions and remove unsupported shaded edges. Several reconstructions still have rounder lowercase shapes, wider stems, different terminals or altered cream opacity/warmth. They are **review drafts, not exact typeface matches**. Saved revisions can be switched in Detail; the default is the parent's selected comparison candidate, not approval.

Dense black CHOOSE MATCH TYPE and OPTIONS sources retain their actual black mass and small counters. SHOP DISTRICT retains cool grey/partial ink. Light What's Happenin' keeps v1 because v2 added an unsupported dark lower edge. STOP v2 removes v1's bevel but remains heavier than the source. Pistolgrip-Pump v2 is finer, with uncertain g/r terminal shapes. Lighter What's Happenin' / See About Ya revisions are about +28.28% / +26.39% taller at matched raw width; explicit outer-bound fitting is available and is not proof of identical individual letters. Source-specific notes remain in the ledger and viewer.

Names derived from OCR were visually checked against actual originals, including Tical 0: The Prequel, LL Cool J and the long one-line credits. The precise runtime context of many live-text source IDs remains unverified. Paper and brick are comparison backdrops, not claims of native placement. Original black/grey/cream ink and true alpha govern the reconstruction.

## Browser and preservation

All **50 detail comparisons**, **100 paired overview canvases**, **22 alternate revision previews**, and **51 control cases** pass, with zero console errors or page overflow. Controls cover 1×/3×/6×, fitted/raw bounds, original ghost, dark/light/context/grey backdrops, filters, search, new-only mode and wraparound navigation. Browser evidence and screenshot remain private.

All 444 prior formal approval entries (437 unique IDs) retain their preview hashes. Adding the earlier accepted 13 mappings gives 450 distinct prior IDs; no new source overlaps them. The exact published 1.3 ZIP hash is unchanged. Game, toolkit, setup, saves, published packs/catalogue and the tools repository/live8768 writer were not changed for this batch. No artwork was installed, newly captured in-game or published.

Source ledger: `config/menu-ui-reconstruction-wave-07-2026-10-28.json`. Private workspace: `logs/menu-ui-wave07-20261028/`. Recovery: `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave07-review-20261028`, pinned by `config/menu-ui-reconstruction-wave-07-checkpoint-2026-10-28.json`. Review the plain-font direction before expanding or assembling it into a pack; preserve both selected and alternate attempts. Freeway remains in the incomplete queue. Future source PRs retain the owner's requested v0.12.2 milestone.
