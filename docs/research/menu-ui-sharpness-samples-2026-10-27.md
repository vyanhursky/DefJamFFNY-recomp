# UI sharpness sample batch — 2026-10-27

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
