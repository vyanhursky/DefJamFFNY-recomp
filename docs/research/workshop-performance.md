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

## Bounded Blender left-finger pose authoring

The separate native-channel Blender bridge can retain an optional `left_hand`
in a `fighter-cinematic-caf-performance-2` source. This is distinct from the
Workshop's ordinary body-only source-animation preview described above.
The compiler advertises `caf-left-fingers-1`; Workshop refuses exporting a
project with this field through a runtime lacking that extension.

This profile is limited to reviewed `CE_113A` on the verified 94-bone CAF
contexts. `fighter-native-left-hand-1` contains exactly fifteen finite unit
quaternions and a bounded, increasing source-tick weight envelope with zero
endpoints. Destinations, rig pointers, controls and programs are never input.
The fixed destinations are the three joints of each anatomical left finger,
bones21..35, in the trusted palette's native channel order. The wrist20,
right hand, body/root, face, cameras and non-speech events remain donor-owned.
No mesh, skin weight or shared `share_hp.o` palette is replaced.

The native hand controller24610 resolves the same `_t`, `_s`, `_p` namespaces
as the face controller24430 and delegates to22010/22150. `_s` uses the numeric
slot+18 path, before `_p` uses the palette slot+30 path. A type13 record placed
under `_p` would not author a hand pose. The coordinator instead generates a
participant-owned `_s` with only the fifteen left-finger quaternion channels,
and keeps the original selector1/right palette leaf under `_p`. Original
selector0 must not also run afterward and overwrite the new pose. This is an
explicit closed transformation; general donor reconstruction still rejects
unapproved graph, destination, control and clock changes. Existing CAF rig,
capacity, resource hash, constructor, lifetime and binding proofs remain in force.

`fighter_caf_hand.py` samples the trusted left palette and authored envelope
at whole 30Hz source ticks and encodes native sixteen-bit type13 deltas.
The decoder must stay within0.0002 component error and0.001 norm-squared error.
This preserves decoded authored keys within that budget, but interpolation
between keys approximates the original type25 smoothstep. A measured donor
comparison at eighth ticks found a maximum0.8562-degree orientation difference
outside the gesture; do not call the reconstructed left track lossless. The
right palette leaf and other cinematic members are preserved exactly.

Blender previews that same quantized track, retains it on export and exposes
Begin/Full pose/Hold until/Return source ticks in the Left Hand Pose panel.
The preset finger shape is retained as validated native quaternions; this is
not a general free-rig or shape-key exporter. Frame1 corresponds to source tick0.
Body animation and cinematic framing are independent; a valid finger pose can
be off screen in a donor camera. Preview-only sound playback calibration and
50% playback do not change native export timing.

`RECOMP_CAF_HAND_TRACE=1` adds the fifteen left-finger quaternions, in the
fixed destination order, to the existing opt-in recorded cinematic pose sample.
It only reads the completed pose and rechecks clocks; it does not alter animation.
Native admission and visual acceptance must be recorded separately from a
successful Blender render, decoded curve comparison or package compilation.

A focused macOS/default-outfit CAF proof reached entrance, combat, authored
victory and results. The completed-pose diagnostic matched199 entrance and202
victory face/left-finger samples to the expected curves within1.2e-7 per component;
body and hand clocks agreed. Both imported voice streams were identified in the
captured mixed audio; copied and original saves stayed byte-exact. The run still
reported one skipped cold-start callback already observed before the hand change,
so this is not a clean full-regression result. Skip/rematch, other outfits and
platforms, and a separate retail-donor gameplay rerun remain unqualified. The
owner explicitly kept donor arm motion/cameras, which can crop the authored hand.
