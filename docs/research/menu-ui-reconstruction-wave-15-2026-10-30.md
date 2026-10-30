# Final Menu/UI reconstruction batch — 2026-10-30

Vlad approved all 100 mappings in batch fourteen (49 complete artworks). `config/menu-ui-wave14-approval-2026-10-30.json` pins the exact approved master and crop hashes. There are now **1,205 accepted mappings: 390 published in 1.3 and 815 queued**.

[Review the final batch](http://127.0.0.1:51762/review.html#overview) or [all 143 individual mappings](http://127.0.0.1:51762/pieces.html#overview). **123 new mappings in 83 complete artworks await owner review. Another 20 retain their published baselines: five historical image-service blocks and 15 technical holds.** All 1,348 tracked mappings are accounted for; those 20 remain unresolved restorations. Wide scenery is counted separately.

## Artwork and provenance

The batch includes venue and shop wordmarks, EN DUO/TEAM headings, red User ID warnings, English/French tournament labels, posters, paper panels, a portrait, and live UI text. The parent made 111 successful built-in imagegen calls for 98 complete artwork groups, preserving every literal request, result and raw output. Thirteen correction calls addressed transparent interiors, flat text without added contours, muted red and complete poster composition. There were no new tool failures. One prepared request, j080, was merged into j079 CORRUPT ID before issuance. No artwork subagents or API/CLI fallback were used.

The source audit covers every native XSH material, including 29 context-only pieces needed to view complete artwork. Originals were decoded from the user's own archive and hashed. All 98 original assemblies were independently reconstructed from source crops and placement. Single-material native references preserve their original RGBA; static assembled shapes use the recorded compositing operation. UV/quad rounding is below 0.1 native pixel where accepted. Some shapes have transparent gaps, fractional overlaps or repeated/irregular UVs. CORRUPT ID has approximately half a native pixel of overlap; its review reference normalizes the two parts to adjoining integer rectangles. These limitations remain recorded for native assembly.

All 111 master exports and 183 piece exports preserve alpha and RGB above alpha 16 exactly. Raw pieces are lossless integer regions of the same generated master; adding any separately saved transparent gap guard reconstructs each raw master exactly. Only established low-alpha RGB bleed is applied to previews. Context-only pieces remain unselected and are not automatically approved replacements for neighbouring artwork.

The parent inspected all 98 initial original/draft pairs on blue and pale fields at 1× and up to 3×, then inspected the corrections. The SUS caption was corrected to the visually verified SYNDICATE wording; literal issued prompts remain unchanged. Source glyph shape, spacing, weight, colour, opacity and preview registration remain approximate and subject to owner review.

## Holds and validation limits

The five earlier image-service moderation blocks were not retried or bypassed. Technical holds retain the published baseline when generation lost genuine opaque gray marks, shifted the shared font atlas, filled transparent venue symbols, changed the thin I, misread the GAGNANT gutter/context, or failed the NO USER IDs colour/alpha treatment. The review labels these as unchanged baselines. Rejected attempts and exact reasons remain in the private workspace and source ledger.

No selected near-pure neon-green or green-dominant texel findings remain. Nine selected raw masters touch an image edge: portrait and rectangular surfaces do so naturally, while several logos/fragments still need guard or source-clip reconciliation. This is not a clean native border result. Variable-sized review crops must not be copied directly into a release pack.

Browser checks loaded 103 artwork cards and 143 mapping cards, then checked all details at 1×/3×/6× (309 joined and 429 mapping checks). There were no loading, console or horizontal page overflow failures. Revision switching, original ghost, raw proportions, backdrops, search and the technical-hold filter were checked. These checks validate the viewer, not game rendering. No new native game run, installation or publication occurred.

## Recovery and next steps

The source ledger is `config/menu-ui-reconstruction-wave-15-2026-10-30.json`. The private workspace is `logs/menu-ui-wave15-20261030/`, including `prompt-set.json`, raw and derived assets, source geometry, `retained-records.json`, `technical-holds.json`, `attempt-review.html` and verification receipts. The additive private recovery checkpoint is chained to batch fourteen and uses independent APFS copy-on-write files, with every copied byte verified. No older artwork was deleted and no artwork is tracked in Git.

Next: owner review and exact-hash approval records, then approved native canvas assembly, reconciliation with approved context neighbours, and serial in-game gutter/layer/sampling checks. The held assets need further faithful restoration. Published **1.3/catalogue 7 remain unchanged**. No push or PR was requested this turn; any future PR belongs to **v0.12.2**.
