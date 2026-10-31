# UI reconstruction: next hundred variants — 2026-10-28

Subsequent owner approval: all 103 entries accepted; hashes pinned in
`config/menu-ui-reconstruction-wave04-approval-2026-10-28.json`. Historical review-pending statements below describe the completed checkpoint.

The owner accepted all 104 wave-three studies and requested the next batch.
Approval is pinned to their selected preview hashes in
`config/menu-ui-reconstruction-wave03-approval-2026-10-28.json`. Previous artwork,
generation records and recovery checkpoints remain immutable. The established
multi-agent authorization continues for isolated artwork lanes.

This batch covers 100 distinct three-fighter banner sources and three earlier
select-material corrections: Bo, Cruz and WC. Its 103 mappings comprise 53 select
and 50 loading variants; 100 use the three-fighter layout and three use the
two-fighter layout. These are source-specific reconstructions, not a shared master
recoloured or stretched into unverified aliases. The baseline remains 1,348 text
mappings within the known 2,337-source static menu/UI/background census.

Three workers own disjoint 35/35/33 assignments. They inspect actual original
RGBA plus blue and pale composites before built-in image generation. The source
controls wording, lettering, weight, spacing, line layout, symbols, outlines,
material, colour and wear. Alpha distinguishes opaque ink, translucent material
and true holes; RGB brightness alone cannot establish cutouts. Genuine source
green remains. Isolated sampling fringes must not become broad decorative paint.
No API/CLI generation fallback or procedural artistic editing is used.

Literal request records are saved before each call, followed immediately by
versioned raw PNGs and result records. Filenames derive from the same request
key/revision; prior records are never overwritten. Parent merging checks
request/result equality and hashes of the default and workspace PNGs. Adaptive
retries remain source-specific. Alpha <=16 matte residue uses the existing
mechanical export rather than repeated artistic regeneration. Every raw attempt
remains available.

The review is prepared at `http://127.0.0.1:51745/review.html#overview`. It retains
paired scanning, search, source-type/layout/material-correction filters,
1×/3×/6× detail, raw/fitted bounds and original ghost. Fitting outer bounds does
not establish identical individual glyphs or final native placement. Export uses
existing `hd_assets.bleed_rgb` with alpha >16 donors and restores raw alpha
exactly. RGB above alpha 16 remains unchanged. Near-pure neon-green checks use
R/B <=8 and G >=247; this criterion does not justify blanket desaturation.

No game is stopped or run, no atlas or pack is installed or published, and no
native coverage is inferred for these drafts. Published 1.2, catalogue revision 5,
scenery, game and toolkit remain unchanged. Final atlas assembly and native
blending, placement, clipping and sampling checks remain required before release.
No push is requested. Future PRs use milestone v0.12.2. Feature-branch state goes
in this report and the handover, not PROGRESS.md.

Private workspace: `logs/menu-ui-wave04-20261028/`. Completion results and recovery details follow below.

## Source-specific material and bounds decisions

WC select preserves solid charcoal faces and subdued partial-grey keylines. The
three-fighter source includes keyline samples `[99,97,90,156]` and
`[82,78,71,185]`, versus the opaque face `[35,32,33,255]`; a brighter opaque beige
edge is a revision candidate, not an intended new border. Bo's two-fighter
correction preserves genuinely opaque copper-orange faces (common source value
`[165,81,49,255]`). Neither case permits a universal hollow-face conversion.

Busta Rhymes loading three-fighter has an isolated horizontal smear reaching the
right texture edge. At x=180..255, each row is byte-identical: y=52 is
`[217,194,104,38]`, y=53 is `[198,170,156,130]`, and y=54 is
`[198,170,156,74]`; surrounding rows are clear. Alpha thresholds 140, 160, 190,
220 and 250 all give full-source bounds `[0,13,166,72]`, while threshold 128
includes the smear and extends to x=256. We treat that constant tail as an artifact
rather than a logo flourish; its decoding origin is not established. The full
source PNG, crop `[0,8,256,76]` and measured alpha-128 bounds remain unchanged.
Explicit logical review bounds `[0,5,166,64]` within that crop give aspect 166/59.
The generation omits the isolated tail, and the review discloses this bounds
exception. Genuine logo flourishes remain. No original pixels are modified.


## Completion and validation

All 103 source mappings have selected drafts: 100 new sources plus three earlier
material corrections, independently checked against the prior approval lists.
There are 111 successful saved built-in outputs,
103 selected and 8 held attempts. All actual PNGs are accounted for;
prepared requests without saved results are listed separately and never counted
as successful calls. The source ledger retains literal prompts, request/input/raw
hashes, selected revisions, worker findings and contextual-background hashes:
`config/menu-ui-reconstruction-wave-04-2026-10-28.json`.

Parent review covered all 103 matched original/draft rows on blue; workers also
reviewed pale backgrounds and the true RGBA sources. Source-specific retries
address amplified palette speckles and incorrect material/opacity. Jervis raw
halo investigation found clear surrounding alpha; hidden RGB and visible glow
must be distinguished. Numeric material flags remain diagnostics rather than
automatic art edits. Scarface and Method Man retain somewhat stronger gray wear
than their originals; the source comparison and this tone limitation remain
explicit for owner review. Cindy loading has a genuinely opaque warm face; its
brightness flag does not establish a transparency defect.

All 103 exports preserve raw alpha exactly and RGB above alpha 16 exactly. Every
export passes the bounded near-pure neon-green check in both visible and hidden
texels. Prior approved 104 + 50 + 27 preview files are independently hash-checked
and unchanged. Raw height error at matched width ranges from
-12.77% to +3.56%; explicit outer-bound fitting,
raw view and original ghost remain available. This is not proof of identical
individual glyphs or native placement.

Browser QA loads 103 detail cases and 206 overview canvases, exercises
32 control/filter cases, and reports zero console errors or page overflow.
The review has source-type counts 53 select / 50 loading, layout counts
3 two-fighter / 100 three-fighter, and a three-entry earlier-material filter.
Private receipts: `browser-qa.json`, `quality-receipt.json`,
`material-audit.json`, `independent-integrity.json` and the three worker QA files.
These are browser/artwork checks; no new native run is claimed.

The immutable local recovery copy is `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave04-review-20261028`. It contains the entire review,
all raw attempts and pre-call records, full original inputs, source records and
hash manifest. Its independently verified copy/hash pin is
`config/menu-ui-reconstruction-wave-04-checkpoint-2026-10-28.json`.
The prior wave-three checkpoint remains unchanged. No artwork enters Git.

Next: owner reviews this 103-entry page, resolve any exceptions, then continue
100+ source-specific batches from the remaining inventory. Use Busta's explicit
logical bounds in future atlas assembly, not its smear-inflated alpha-128 bounds.
Native integration must still check actual placement, blending, clipping and
sampling after atlas assembly. No publication or push was requested this turn.
