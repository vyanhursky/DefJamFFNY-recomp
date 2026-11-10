# Workshop performance contract

Owner scope, 2026-11-10: voice overrides, independent entrance/victory choices,
source animation playback and AI personality authoring target exportable projects
first. Existing Story-save editing remains unchanged. Broad gameplay regressions
are deferred by the owner until joint testing after further features.

## Portable inputs

`caf-fighter-6` delegates the existing outfit/face/retail-moveset readers and adds
an optional validated retail `voice_donor`. It explicitly admits typed voice, AI
and simple original intro/victory sources. Previous recipes keep their existing
scope. Multiple outfits share one performance identity.

`fighter-voice-retail-1` selects a verified original retail speech identity without
cloning its banks. Edited clips/categories use existing `fighter-voice-4` resources
with hash-bound PCM16 WAV descriptors. Original event ordinals are preserved.
`fighter-ai-2` permits empty edit dictionaries to retain a preset's original
tendency values; explicit edits retain the existing 1–5 field contract.
`fighter-cinematic-retail-1` selects an original CI/CE template, retaining its
body/root, secondary resources, timing and cameras through the existing compiler.
This does not admit arbitrary cinematic graphs or unknown animation formats.

## Participant identity

Owned motion cores remain zero-based 141–16383. The new binding formats use
`0x80000000 | logical_selection` for a stable CAF roster identity, admitting
selection 100 through 0x7ffffffe. Native readers map those keys into a separate
bounded internal table and resolve the active participant through its CAF recipe.
The Story adapter's pseudo-selection 99 cannot match these bindings.

| Format | Row | Meaning |
|---|---|---|
| FVA3 | 12 bytes | encoded identity, voice ID, three-category mask |
| FIA2 | 36 bytes | encoded identity, 32-byte profile name |
| FIC3 | 24 bytes | encoded identity, intro/victory labels, graph flags |

Old FVA1/2, FIA1 and FIC1/2 retain owned-core bounds. CAF FIC3 rows currently
require zero graph flags. Native XML tokens use `fmc16384` onward in sorted CAF
identity order; the compiler and reader agree on that index. Actual participant
motion cores remain separate from cinematic binding indexes. Clearing a match
clears CAF recipe ownership; unmatched retail participants use the original route.
No runtime supervisor setting or new environment variable was added.

## Offline authoring API

`scripts/fighter-contract.py` exposes workshop-catalog/check/audio/animation/export
under the existing authoring protocol. Requests are bounded and reject duplicate
JSON fields/non-finite numbers. The original game archives are pinned; authored
outputs stay outside the dump. Export emits typed resources and file descriptors;
the ordinary whole-pack compiler still performs final validation.

The catalog reports 214 admitted voice banks, 138 simple sequence tokens and 188
AI profiles. Retail labels use actual core IDs, not selection IDs or speech IDs:
Blaze core5→char0005, D-Mob core51→char0051, Pockets core64→char0064.

Audio audition converts original PCM/R2 into WAV offline. The R2 prediction/block
algorithm was independently implemented and checked against
[FFmpeg's primary decoder](https://github.com/FFmpeg/FFmpeg/blob/master/libavcodec/adpcm.c).
No FFmpeg source or binary is bundled. This integer audition is separate from
native float-history audio qualification. Edited voice banks use the first
original entrance/victory stream as their default unless replaced; preserving
every randomized original speech stream remains outside this first editor.

Animation playback uses the established body18/13 and root20 numerical readers,
physical skeleton rows and native op31/op9 palette/vertex selectors. The stored
skeleton permutation does not reorder channels. Each displayed CAF part receives
its own original bind rig and weights. Pinned CAF directories contain duplicate
texture names; the original-only model reader retains the existing CAF bounds,
refuses ambiguous requested models and does not relax the general BIG composer.
Preview uses 30 source ticks/second and omits native camera, face/hand palettes,
events and runtime blending. Unsupported clips are excluded by preflight.
Blaze's bank5 has 7 admitted clips and 110 exclusions, chiefly body19. Native
type19 recurrence/rest-quaternion evidence exists, but numerical parity across
axes and block boundaries is not yet established; that decoder remains gated.

## Focused evidence and limits

- Project/history/old-format tests and typed compiler tests pass.
- Initial source CI reached 2435 passes with one legacy AI error-message
  assertion failure: the earlier population guard changed the diagnostic for
  an invalid owned core. The corrected diagnostic preserves that contract;
  the focused AI tests pass. This failure was not a gameplay result.
- Native C fixtures compile with warnings as errors and verify old formats plus
  two CAFs sharing a retail core with distinct voice, AI and cinematic bindings.
- An actual three-outfit CAF with its existing atlases, UI images, finishers and
  sculpt compiles with independent performance, including an imported WAV.
- Disposable Windows Qt checks verify source animation on 14 CAF parts, changing
  joint poses, pause/scrub, visible editor tabs, independent staging and Save.
- Bind-pose reconstruction on used body joints matches stored inverse bind
  matrices within 4.18e-6. The CI_113A preview decodes 106 source ticks; supported
  original combat token N0410__B decodes 168 ticks.

These are compiler/editor/native-fixture results, not a completed in-game pilot
for CAF v6. Full game launch, native mixed-CAF/rematch/cinematic/audio behavior,
the full unsupported codec set and cross-platform gameplay remain pending joint
testing. No packaged release or merge is implied. Original assets, private art,
decoded models, projects, captures and built executables are not source payloads.
