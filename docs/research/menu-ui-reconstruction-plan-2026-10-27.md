# Remaining UI texture reconstruction plan — 2026-10-27

Status: owner-approved production plan. On 2026-10-28 the owner accepted the
[next 27 review textures](menu-ui-reconstruction-wave-01-2026-10-27.md), including
Main Menu v6 and flat dark Capone v3, and requested **at least 50 textures per
routine review batch**. The first twelve-family direction was approved earlier.
These supersede earlier Main Menu v5/Capone v2 style references below; historical
literal prompts remain unchanged. Startup Continue v3 stays accepted. Artwork
approval does not establish native coverage of every texture or authorize release.

Planning checkpoint, before further asset work: The owner gives
positive feedback on all three corrected-context samples (“They all look good
to me I think”) and requests the complete plan before proceeding. Treat Main Menu
v5, Continue v3 and Capone v2 as the accepted visual direction. This does not
establish native candidate quality or authorize publication of a new release.
No new artwork, game run, pack assembly or publication was performed during the original planning turn.

## Production authorization and green-fringe addition

The owner approved this plan on 2026-10-27 and authorized stopping the running
game when the isolated pilot was ready. Production has begun in a separate
private workspace. The owner also requested considering removal of the green
edge tinge from all remastered textures, citing
[issue #142](https://github.com/vyanhursky/DefJamFFNY-recomp/issues/142).
The issue reports green chroma backing and edge contamination; its suggestions
are investigation proposals, not proof that every green texel is unwanted.

Add a pack-wide green-edge census and inspect flagged textures. For reconstructed
lettering, explicitly exclude green matte contamination from the preservation
constraints, require neutral/source-appropriate antialias colours, and reject
coloured fringes. Use the established RGB bleed into alpha-zero texels at export,
checking that alpha and visible RGB remain exact. For retained artwork, visible
edge de-matting needs measured source-specific confirmation and comparison; do
not globally desaturate green, alter transparency or remove genuine green art.
Record source/output hashes and before/after metrics. Check pale, dark and real
game backgrounds plus downsampling. Keep runtime cleaning changes separate if
needed; this work first targets the pack data.

## Goal and scope

Produce visibly cleaner UI lettering at normal size on the owner's 27-inch
1440p display while preserving the game's spelling, lettering identity,
proportions, weight, spacing, colour, wear and placement. Smooth high-resolution
contours must survive the real renderer. Merely enlarging or sharpening the
old pixel staircase did not achieve that in 1.2.

The starting scope is the existing 1,140 text overrides, not a claim that every
UI element in the game is covered:

| Existing group | Texture mappings |
|---|---:|
| Menu labels, descriptions, tiled companions and textual controls | 574 |
| Fighter-name banners, including 2/3/4-fighter layouts | 214 |
| Loading venue/match wordmarks and companion tiles | 81 |
| Observed native headings/labels and one shared bitmap glyph page | 271 |
| Total | 1,140 |

The prior visual census inspected 2,129 static source IDs. The 1,140 mappings
are not a count of unique words or required generation calls. A production
inventory must distinguish duplicates, layout variants, tile fragments and
independent artwork. It includes English/French and historical/demo text already
in the pack. Mark unobserved resources as such rather than claiming native tests.

Retain the approved backgrounds, map and widescreen joins. Portraits, scenery,
background-baked decorative print and effects are outside this lettering pass.
Record symbol-only icons, controller prompts and frames in a separate audit if
they are visibly soft; do not silently redesign them with a text prompt.
Arbitrary player names, mutable numbers and uncaptured font-cache permutations
need a separate runtime-font investigation if exhaustive coverage is desired.

## Phase 1 — production manifest and family mapping

For every mapping, record source ID and aliases, original/published hashes,
exact visible text, language, texture and logical word bounds, baseline,
rotation, alpha/colour role, tile group, observed screen and state, placement,
review revision, and native-validation status. OCR assists searching; inspect
spelling and punctuation manually. Uncertain text or context is held, not guessed.

Separate serif headings, small sans-serif labels, distressed/stencil headings,
fighter-specific wordmarks, venue/match logos and glyph atlases. Give every fighter
its own original artwork authority. Do not convert handwriting such as Method
Man or N.O.R.E. into Capone's serif design. Do not deduplicate by recognized text
alone: weight, distress, aspect, layout and shader usage can differ.

Dark fighter-select lettering is reviewed on pale paper headers; light loading
lettering is reviewed over portraits. Confirm usage from game references/captures;
filename or PNG brightness alone cannot establish runtime tint/blending. Keep
2/3/4-fighter layouts and selected/unselected/disabled states separate until
compatibility is demonstrated. Share a master only where identity is verified.

## Phase 2 — integrate the three accepted samples before expansion

Keep raw generated PNGs immutable. The initial pilot's Main Menu v5 and Capone v2
were corrected after native feedback. The current accepted masters are Main Menu
v6, Continue v3 and flat dark Capone v3. Assemble them into their original full
texture/atlas coordinate systems in an isolated
candidate pack, rather than installing cropped words as replacement textures.
Match original visible bounds and baseline; retain gutters, transparent margins,
rotation, non-target content and UV relationships. The browser's optional bounds
fit is a preview convenience and is not proof of correct exported placement.

Use 4x replacement dimensions as the initial compatibility baseline, but inspect
effective detail at final display size. A large generated canvas does not ensure
adequate pixels across the actual word. If an output lacks real detail for its
final placement, regenerate at a useful size rather than relabel an enlargement
as added detail. Higher replacement scales are considered only for demonstrated
benefit after loader/memory checks; 8x everywhere is not the default.

Use the existing tool export/assembly path for placement, cropping, scaling and
preserving unaffected atlas pixels. Keep these mechanical transforms explicit
and reproducible; do not use additional artistic sharpening, thresholded alpha
or recolouring to rescue a bad generation. Artwork corrections go back through
built-in imagegen. Inspect generated alpha and use the loader's documented
channel/alpha contract, rather than guessing premultiplication or tint rules.

Run these three in the real game at 2560x1440 with recorded settings. Compare
published 1.2 and candidate at the same UI state and position. Check outline
clarity, alpha, colour/tint, width/height, animation, clipping and readability.
If filtering or mip selection still makes them soft, investigate the actual
sampler state using evidence before proposing renderer changes. More texture
pixels alone may not solve a sampling issue. The first expansion waits for this
native result; the game must demonstrate that the approach works.

## Phase 3 — representative family batch

Produce approximately 12–20 distinct masters across the remaining families:
short/long and multiline headings, small labels, distressed text, a long fighter
name, handwritten fighter art, both dark-select and light-loading cases,
venue/match marks and a tiled word. Include language-specific accents where
present. Each call has its own original edit target, exact text, measurements
and the applicable approved style reference.

Use built-in imagegen, one call per distinct asset or revision. The accepted
samples establish edge/material quality, not a universal typeface. Preserve
original alphabet forms, punctuation and distinctive strokes. Work on the whole
logical word when tiles compose one word, then assemble companion tiles from
that same approved master so there are no independently generated joins.

Review this diversity batch together. It establishes each family's direction
before producing hundreds of related items. Once a family is agreed, continue
routine production under that direction; bring material deviations and uncertain
source details back for judgment. This avoids requiring individual owner
approval for every ordinary technical pass while keeping style decisions visible.

## Prompt construction

Each call uses the following master, with literal values substituted for all
bracketed fields. Read the local edit target before the call. Image 1 is always
the source lettering authority; Image 2 is an optional same-family accepted
quality reference, never a replacement for Image 1's letter design. A context
image, if included, is explicitly a contrast reference and must not be baked in.
Set the actual tool transparent_background option to true for isolated lettering.
A template is a constraint request, not a guarantee of exact pixel geometry.

```text
Use case: precise-object-edit.
Asset type: transparent HD replacement for a Def Jam: Fight for NY UI texture.

Edit Image 1. Restore its original lettering with smooth, clean high-resolution
contours for display on a 2560x1440 monitor. Reconstruct the intended curves and
straight cuts; remove low-resolution stair steps without changing the design.

Text verbatim: "[EXACT TEXT, CASE, PUNCTUATION AND LINE BREAKS]".
Image 1 controls the typeface, individual glyph shapes, widths, height, baseline,
spacing, line arrangement, stroke weight, colour, wear and original edge treatment.
[Image 2 shows accepted contour/material quality for THIS FAMILY ONLY. Do not
copy its font, words, layout, bevel or ornament into Image 1.]

Measured layout: visible word width [W], height [H], aspect [W/H]; baseline [B];
letter or word horizontal ranges [MEASURED RANGES]; line spacing [IF APPLICABLE].
These are layout constraints, not text to print. Preserve the source's unusual
letter shapes, punctuation, open counters and deliberate asymmetry.

Material: [SOURCE-SPECIFIC FACE COLOUR, SHADOW, OUTLINE, DISTRESS AND WEAR].
Rendering context: [DARK ON PALE SELECT PAPER / LIGHT OVER LOADING PORTRAIT /
SPECIFIC MENU CONTEXT]. Use that fact only to preserve contrast. Render no backdrop.

Change only edge resolution and the clarity of existing material detail. Keep
face weight and original tonal balance. Retain intentional distress and fine wear
without treating stray pixel noise as a new pattern. No new chips or decorations.
No modern font substitution, heavier strokes, expanded bevels, broad bright rim,
new 3D extrusion, invented lettering or added words. No coloured fringe, white
halo, fog, loose flecks or filled counters.

Entire word or approved logical text group visible, flat front-facing raster,
genuine transparent alpha outside the lettering, even clear guard margin, no
clipping. Preserve continuous antialiased edges. No paper, portrait, brick,
checkerboard or shadow plate baked into the transparent background.
```

Family addenda are attached to that master, not sent without the original reference:

- **Serif headings:** retain each heading's slab/serif cuts, narrow letters,
  unusual U/M forms, original word gaps, ivory face and restrained charcoal edge.
  Main Menu v6 is the accepted clarity reference; retain flat lettering and thin
  stems/open counters, without adding a bevel.
- **Small labels:** preserve condensed slender strokes, thin I, open counters,
  modest rounded corners and restrained shadow. Continue v3 is the accepted clarity
  reference. Do not turn the label into bold varsity, athletic or stencil type.
- **Dark fighter-select wordmarks:** retain that fighter's own logo/skeleton and
  near-black/brown-charcoal broad faces against pale paper, retaining intentional
  source colours. Flat dark Capone v3 is a quality reference only for compatible
  material. Keep fine wear, without adding an outer rim or depth lining.
- **Light loading wordmarks:** retain that source's ivory/tan face and original
  dark edge for legibility against portraits. Do not darken it to the select
  version or create it by automatic inversion. Confirm any shared/tinted source.
- **Handwritten/distressed/stencil and venue/match marks:** follow the original
  irregular paths, interruptions, spacing and ornaments; smooth accidental pixel
  stairs while preserving intentional cuts and wear. No generic substitute font.
- **Glyph pages:** do not generate a complete rearranged alphabet sheet. Preserve
  the exact cell map, metrics and UVs; validate a few glyphs before any full page.
  A glyph atlas is a separate constrained subtask, not proof of general live-font
  coverage. If slot/shape fidelity cannot be achieved reliably, hold the existing
  page and report the limitation rather than ship a changed alphabet blindly.

Retry prompt, with just one observed defect substituted:

```text
Edit Image 1, the latest candidate. Image 2 is the original authority.
Correct only [SPECIFIC OBSERVED DEFECT]. Keep every other accepted property:
exact text, letter skeletons, widths, positions, spacing, face weight, colours,
wear and clean transparent alpha. Do not add a new font, bevel or ornament.
[PRECISE SOURCE MEASUREMENT OR COLOUR/EDGE REQUIREMENT].
```

Stop repeated prompt drift after a small number of unsuccessful targeted retries.
Hold that asset, retain the current published replacement and flag a constrained
contour/manual-restoration path for consideration. Do not substitute an easier
font or quietly weaken a quality requirement.

## Phase 4 — production waves and quality checks

After family review, work in waves of **at least 50 textures**, grouped by
family/screen, with a contact sheet and status ledger per wave (owner preference,
2026-10-28; supersedes the original 25–50 suggestion). Count distinct source
artwork, not retries as extra review items. This is a workload
size, not a promise that one call produces a whole sheet. Keep an approved master
and its observed variants linked, and mark every source mapping as reused,
newly reconstructed, retained for a stated reason, or held. Reconcile the full
1,140-mapping baseline plus any newly discovered in-scope assets. Do not declare
completion from a generation-call counter or only the frequently visited menus.

For every item inspect exact text, letter count/punctuation, original silhouette
and distinctive forms, measured outer bounds and baseline, per-letter spacing,
stroke weight, alpha/counters, unintended components, face colour, transparent
fringes and unintended detail. Numerical differences are triage aids, not an
automatic substitute for visual judgment. Do not promise a universal per-glyph
pixel lock from an imagegen prompt. Preserve source metrics during assembly and
reject visually wrong typography even if its outer rectangle fits.

Review Original / published 1.2 / candidate at matched game scale, with optional
source ghost, raw-versus-fitted view, 1x, 1440p reference 3x and detail 6x. Label
browser composites clearly. Use pale select paper for dark banners, several
portrait brightnesses for light loading names, and correct context for menus.
Contact sheets help coverage; they do not replace close inspection. A full-size
native capture is the final evidence for actual in-game sharpness.

Keep per-output original/published/reference hashes, full literal prompt and
input order, raw output hash/dimensions/alpha, parent revision, export transforms,
source mappings, review status and native route/capture. Never overwrite selected
raw art. Keep old review origins and storage intact; use a new reader/workspace
for production and immutable checkpoints outside Git.

## Phase 5 — native coverage and candidate package

Test high-traffic menus early, then fighter selection and loading in supported
2/3/4-fighter layouts, team/venue/match selection, settings, Story/shop screens
and other census families. Verify highlight/disabled/fade/tint states, long and
multiline text, transitions, tile joins, overlay layering and glyph-page slots.
Keep unvisited historical/demo resources labelled as visually reviewed only.
Check 1440p first, then 1080p/downsampling, 4:3 and widescreen extremes for clipping
and placement. Measure pack load time, memory impact and texture failures against
1.2. Native evidence starts on macOS; other platform results are reported only
when actually run. Use disposable isolated saves, restore/verify the complete
save root, run only one game instance, and compare the actual ZIP-extracted pack.

Export a new standalone version with unchanged approved scenery and layouts,
updated provenance and coverage ledger. Validate PNGs, dimensions, alpha, aliases,
manifest/paths, ZIP CRC, checksums, installer contract, and untouched background
hashes. Exercise managed install/update and rollback with the released 0.12.1
helper. No specific final archive size or generation budget is claimed before
the inventory and export are measured.

The intended result remains a textures-v1/wide-v1 content update usable on game
0.12.1 without reinstalling. This must be revalidated for the actual candidate.
If native testing demonstrates a necessary loader/font/sampler change, surface
that separately with its compatibility implications; do not bundle an unannounced
game requirement. Any future source PR uses milestone v0.12.2. Future publication
uses a newly versioned Cloudflare object and updated signed mod register after
approval of the concrete candidate. No existing stable archive is overwritten.

## Proposed checkpoints and required owner involvement

1. This plan, before further production.
2. Three-sample native integration result and the 12–20-master family review.
3. Exceptions/style deviations as they arise; otherwise routine waves continue.
4. Final native candidate/release review before shipment.

No more screenshots, credentials or files are needed from the owner to prepare
that first integration. The exact unique-master count, number of generation calls
and production time are unknown until the identity/tile/context manifest exists.
Builtin imagegen may require retries; offer measured progress by completed,
reviewed and native-verified mappings rather than a speculative deadline.

## Exact accepted sample prompts (historical, unchanged)

These are the literal prompts for the current accepted visual references; the
production master above adds a repeatable per-asset spec. Historical statuses
inside old generation records remain as history, with later feedback recorded
separately. Main Menu v5 and Capone v2 were edits of earlier generated artwork,
so their prompts must be interpreted with those pinned inputs rather than reused
against an unrelated source as standalone instructions.

### main-menu v5

Output SHA-256: `405f8375df10bec9e1de980da1cadec8bdd92311b19fde0e47cfe281cfec2841`

```text
Make ONE restrained typography adjustment to the supplied clean MAIN MENU wordmark. Preserve the exact letters, individual widths, positions, spacing and ivory face skeletons. Reduce only the thick dark bevel/outer rim to a thin simple clean charcoal edge, roughly half its current width, reducing its embossed effect. Keep the word flat and less tall: intended visible aspect880:111 (7.93:1). Do not repaint it with distress. Exact text "MAIN MENU". Colours are ONLY ivory, pale warm grey and charcoal grey. Every edge and all counters must have perfectly clean transparent alpha outside the letters. No red, yellow or green anywhere; no coloured fringe, bright outline, white specks, chips, halos, fog or loose pixels. Do not change typeface or move any letter. Smooth source-style serif contours, clean thin outline, subtle original shading; no 3D-heavy extrusion. Entire word visible on genuine transparent background with even guard margin.
```

### continue v3

Output SHA-256: `76314ebd19bc08d710db5681bfe73ba97327997f216e661fc93f426a3b5da9ae`

```text
Fidelity-critical HD tracing/restoration of the supplied CONTINUE game UI bitmap. Text verbatim "CONTINUE". The source controls typeface, ALL widths/heights/spacing/stroke weight. Reconstruct continuous clean outlines without redesigning its letter skeletons. This is thin/light-medium condensed sans-serif, small rounded/softly cut corners, with slender strokes and open counters, NOT bold athletic/varsity/stencil lettering. Keep original word visible bounds width246 height44, aspect5.5909:1. At identical word width, do NOT make letters taller than reference. Measured letter face x ranges relative to word left: C0..26 O32..58 N65..93 T100..126 I133..141 N149..177 U185..213 E222..245. Layout constraints only, do not print numbers. Thin I, source-shaped N diagonals, narrow U counter, original cap height and baseline; equal original spacing. White faces with the original very restrained dark edge/shadow. Do not add a heavier rounded outline or a new bevel. Correct pixel stairs into smooth contours, keep letter weight and exact original layout. Entire word as flat isolated horizontal UI strip, actual transparent alpha, even guard margin, no added text. The original rather than a modern font is the authority.
```

### capone v2

Output SHA-256: `3594b47ad9f3c1f1149378b8173a6b10e89b46f6c0273d7a3a716e3daa6b6a01`

```text
Edit Image1, the detailed CAPONE reconstruction. Image2 is the original game texture and controls the original dark values and letter layout. Text remains exactly "CAPONE". Keep the embellished worn texture detail and fine bevel workmanship from Image1; the owner likes that detail. Darken only the broad letter faces toward the near-black/dark brown-charcoal value of Image2, so the result reads like original dark ink/metal rather than the lighter grey-brown first reconstruction. Highlights should stay thin and restrained, not a broad bright border. Preserve the existing exact letter skeletons, smooth silhouette, counters, spacing and word proportions; do not regenerate a new font or embellishments. Keep fine wear visible inside the darker material; avoid globally crushing all detail to pure black. Entire flat wordmark isolated on actual transparent alpha background, no paper or scenery baked in, no new words. Source reference visible bounds612wide116high, aspect5.2759:1; preserve that ratio and original stroke weight.
```

