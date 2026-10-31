# UI reconstruction: 50 fighter wordmarks — 2026-10-28

**Subsequent owner approval (2026-10-28):** all fifty textures accepted with no issues.
Exact selected-preview pins are in `config/menu-ui-reconstruction-wave02-approval-2026-10-28.json`.
The owner requested a larger batch and explicitly authorized parallel imagegen
workers. Historical pending-review statements below describe the earlier checkpoint.
Artwork approval does not establish native validation or release approval.

The owner approved the previous 27 review textures, including Main Menu v6 and
dark Capone v3, and requested **at least 50 textures per review batch**. Approval
is pinned separately in `config/menu-ui-reconstruction-approvals-2026-10-28.json`;
the earlier generation records and raw artwork remain unchanged. Startup Continue
v3 stays accepted. This authorizes continued artwork production, not publication.

The new review is `http://127.0.0.1:51743/review.html#overview`. It contains
**50 distinct source mappings for 25 characters**, each with separate select-menu
and loading-screen artwork. These are new drafts awaiting owner review. The
previous 51742 review and all approved artwork remain intact. Published pack 1.2
and the signed mod register are not modified.

## Scope and fidelity

House, Bo, Nyne, Trick, Cruz, Skull, Trejo, Ice-T, Solo, Meca, Elephant Man,
Sean Paul, Chiang, Masa, WC, Fat Joe as Crack, Baxter, Dan-G, Crazy Legs,
Flava Flav, Busta Rhymes as Magic, Bubba Sparxxx, Lil Flip, David Banner and
Bless each receive two independently restored wordmarks. Exact source IDs,
aliases, original PNG hashes, visible bounds, literal prompts and selected
revisions are recorded in the source ledger. The baseline remains 1,348 mappings;
these fifty are within it, not fifty additional discoveries.

The select and loading versions use their own original authority. Bo's select
orange faces and dark loading faces/cream outlines, Sean Paul's staggered select
layout and one-line loading layout, and the other original distinctions are
preserved rather than produced by colour inversion. Source images are composited
on plain reference backdrops solely to make their visible alpha unambiguous.
The tool outputs genuine transparency. Existing emblems, kanji, underlines,
subtitle proportions, outlines and purposeful print wear are part of the logos;
no universal font or new Capone-style bevel is applied.

Six calibration outputs cover House's plaque, Nyne's blackletter and Skull's
shield. After inspecting those original/draft composites, production continues
through the other 44 sources. A targeted retry repairs Trejo's select emblem:
v1 dropped the central black disc inside the transparent ring; selected v2
restores it. There are **51 successful built-in imagegen calls**, with fifty
selected outputs and Trejo select v1 retained as a held attempt. Every generation
and reference remains immutable and individually pinned. No procedural artistic
sharpening, font substitution or alpha erosion is used.

## Export and colour checks

Review exports use the existing modding tool's RGB bleed, taking colour from
alpha>16 and restoring every original alpha byte. RGB above alpha16 stays exact.
Each selected preview has zero near-pure neon-green visible or hidden texels
under R/B<=8, G>=247. This is a defined check, not a claim that every possible
fringe defect is absent or that every green pixel must be removed.

Intentional teal in Bless, olive ink in Bubba Sparxxx and muted green/gold inset
accents in Solo are retained. Source Solo pixels include fully opaque dark green;
green dominance alone would wrongly classify these design colours as defects.
The source ledger keeps those counts separate from the near-pure matte criterion.
No global desaturation or visible-face recolouring is performed.

Selected raw height at matched width ranges **-8.82% to +25.44%**. Forty-eight
outputs are within 9%; the two Ice-T versions differ by +21.93% and +25.44%.
The review explicitly fits original outer bounds by default and exposes raw
proportions and an original ghost. A fitted word rectangle is not proof of
identical individual glyphs. Visual comparison, rather than the percentage alone,
controls selection. Original/source line layouts and separate symbols were
inspected in five matched comparison sheets.

## Review and remaining validation

Quick review shows all fifty original/new pairs together, with each character's
select and loading cards adjacent. Search, type filters and a new-only mode
support faster scanning. Detail provides Original / published 1.2 / draft,
next/previous navigation, 1x/3x/6x, raw/fitted bounds and the original ghost.
Loading art absent from 1.2 is labelled as an original fallback. Paper and portrait
backdrops use text-free crops and maintain their aspect ratio. Overview fits the
card; only detail's scale is a source-texel reference.

These are browser studies. No game is stopped or run for this wave, no atlas or
pack is installed, and no per-source native placement, blending, clipping or
2/3/4-fighter reuse is inferred. The resource inventory targets 2-fighter variants;
other aliases/layouts remain recorded separately until verified. Native validation
and a final assembled candidate remain required before release. The approved
scenery and previous masters are untouched.

The private workspace is `logs/menu-ui-wave02-20261028/`, served only on localhost
51743. Its scripts, references, all raw attempts, selected exports, comparison
sheets and browser evidence remain local. The source ledger contains hashes and
prompts, not image bytes:
[`config/menu-ui-reconstruction-wave-02-2026-10-28.json`](../../config/menu-ui-reconstruction-wave-02-2026-10-28.json).
Independent reopens verify all51 raw/input pins,50 export alpha/RGB invariants,
zero near-pure green export pixels, and the unchanged27 approved prior previews.
Browser verification covers50 details,100 grid canvases, type filters/search,
new-only mode, wraparound navigation, scales and raw/ghost controls; no console
errors or page overflow are observed.

A self-contained local recovery copy is saved at
`/Users/vlad/Code/defjam-data/scratch/menu-ui-wave02-review-20261028`, including
all50 original inputs, reference images, raw attempts and the static review.
The earlier immutable checkpoint retains the prior accepted masters. Feature-branch state lives here and in the handover;
`PROGRESS.md` is not edited. No push is requested. Future PRs use v0.12.2.
