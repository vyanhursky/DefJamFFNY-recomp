# UI sharpness sample batch — 2026-10-27

## Follow-up: typography fidelity and game backdrops

The owner likes the sharper samples at 1x and 6x, but requests closer original
letter sizes, spacing and weight for Main Menu/Continue. Capone's embellished
detail is liked; its lighter value needs comparison against game backgrounds.
That is directional feedback, not approval of a new release.

The separate follow-up page is `http://127.0.0.1:51741/round2/review.html#capone`.
The original review page and its four image outputs remain unchanged. New review
defaults: Main Menu v5, Continue v3 and Capone v2. Six additional built-in imagegen
calls retain exact prompts and all raw PNGs; ten outputs total are now pinned
in the sample config. Prompts specify the source cap-height/word-width ratio,
per-letter horizontal ranges, spacing and stroke-weight invariants. Capone keeps
the detailed v1 reference but requests darker broad faces and restrained highlights.

Measured raw height at matched word width is +2.35% for Main Menu v5, -2.83% for
Continue v3 and +6.07% for Capone v2, using alpha>=128 bounds. The previous Continue
v2 was about 19% taller than the source. These measurements address overall
proportions, not exact glyph correspondence. Prompts alone did not lock every
letter's shape, weight or spacing. Main Menu remains more bevelled than the source.
Main Menu v2/v3 produced white fringes and v4 coloured fringes; all three are held
as private history, not selected. V5 uses the cleaner first draft as its edit target.

The new review can match both outer bounds to the reference for presentation,
or show uncorrected generated proportions. This fit is canvas-only, not an
exported asset transformation or per-glyph geometry lock. An optional cyan source
ghost exposes alignment differences, and a draft selector compares the previous
version with the new one on an identical backdrop. All three cases, prior/latest,
3x/6x, ghost/bounds controls and game-paper/portrait/brick backdrops were inspected
in the browser; no broken reference image or page overflow was observed.

Backdrops are the real loading-paper master, a new native loading-screen portrait
excerpt, and an existing native Main Menu brick excerpt. The full native loading
frame is shown separately as context. These are clearly labelled texture studies;
they do not reproduce the candidate's actual game tint/combiners/animation.
No generated sample was installed or natively verified.

The background-only native run `logs/run-20261027-154735.log.err` uses the isolated
1.2 fixture and complete-save-root guard. It reaches Game.StartGame, records 42
two-second present intervals (minimum70/median120/maximum121), zero measured
crashes/watchdogs/unresolved calls/debug-layer/truncated-batch faults, and identical
save restoration. The ten reported optional omissions are inherited. Triage's
PARTIAL line-count warning is resolved by the bounded tail: TRANS frames advance
through5038 after the last sparse present report; the first unclassified return
is the known NtFsControlFile stub. No hang is inferred from that line count.

The native capture still shows Blaze/Fat Joe. `RECOMP_START_FIGHTERS=47,55` logs
47/55 at Game.StartGame, but this hook runs after loading-portrait selection;
it does not establish a native Capone banner comparison. This run is evidence
for the actual background context and save safety only. Private receipt:
`logs/menu-ui-sharpness-samples-20261027/round2/native-background-receipt.json`.

Await judgment on the darker Capone and remaining typography differences. Exact
original letter geometry, if required beyond these drafts, needs a constrained
font/contour construction rather than treating a prompt as a pixel lock. Atlas
assembly and a genuine native candidate comparison still precede any wider rollout.
No source push, catalogue change, public artwork upload or new PR was requested.

## Initial sample checkpoint

The owner found the published 1.2 UI textures pixelated on a 27-inch 1440p
display and requested a small sharper sample batch before extending the work.
The previous Stronger recipe narrows alpha ramps but retains the underlying
low-resolution contours. Stair steps are visible in the 1.2 texture files
themselves. This pilot reconstructs those contours at high resolution using
the built-in imagegen tool.

## Review batch

| Sample | Review revision | Focus |
|---|---|---|
| MAIN MENU | v1 | Clean serif contours and off-white bevelled faces |
| CAPONE, two-fighter banner | v1 | Dark slab-serif lettering, counters and surface wear |
| CONTINUE | v2 | Small condensed white text with rounded corners |

The first Continue reconstruction changed the font toward heavy varsity
lettering. It remains private revision history; v2 uses the original as its
authority again, asking for narrower, lighter, rounded lettering. All four
raw generations remain intact, with exact prompts/reference hashes. No fonts
or glyph artwork are downloaded or substituted.

`config/menu-ui-sharpness-samples-2026-10-27.json` pins the published full-texture
hashes, reference-crop hashes, all four generated output hashes/dimensions/alpha
counts and full prompts. Each generated PNG has genuine transparency. No
post-generation sharpening, alpha remapping or atlas resizing was applied.

Review: `http://127.0.0.1:51741/review.html`. The three original/current reference
crops, generated PNGs, prompts, receipts, HTML and browser proof are private in
`logs/menu-ui-sharpness-samples-20261027/`. The page renders each pair at the same
visible width, preserving each image's proportions. Its 1440p reference is
three CSS pixels per original texel at browser zoom 100%; detail view is 6x.
This is a texture comparison, not a new native capture or simulated game frame.

## Technical evidence and limits

The pinned toolkit's `texture_pack.c:prepare_png` creates the replacement mip
chain using the pack's opacity/channel policy. `texture_pack_bind` replaces the
texture while retaining the title's filtering/addressing/combiners. The Vulkan
sampler cache supports nearest and linear modes. No sampling, mip, runtime or
toolkit change was made here, and this inspection does not establish the actual
sampler state of a particular play-test frame.

The drafts visibly reduce stair steps at the reference scale, but can change
letter shapes, weight, spacing, colour and bevel intensity. Main Menu has a more
pronounced dark outline/bevel; Capone has clearer wear and bevels. Those changes
need the owner's judgment. These are not source-exact contour exports, and the
raw PNG sizes/placement are not runtime-ready replacement atlases.

Browser review verifies all three comparisons, reference/detail scale and
grey/light/dark backdrops. No game run is required to validate this presentation;
none was performed for these drafts. All published 1.2 art, catalogue records,
active packs and saves remain unchanged. Earlier review/workshop origins are
preserved; 51741 is a separate sample page.

## Hand-off

Local feature branch `codex/menu-ui-sharpness-samples` starts at 1.2 publication
commit `d7b45c3`. No push, new PR or publication is requested. Any later PR must
use milestone v0.12.2 per the owner. The feature branch does not edit PROGRESS.md.

Next: obtain the owner's judgment of edge clarity and typography, then refine
weight/spacing/colour as needed. After a direction is selected, assemble it into
the original full atlas bounds, check alpha/layout/tint, and test natively at
1440p before expanding the batch or exporting a release. Do not infer approval
of these drafts or universal live-font coverage.
