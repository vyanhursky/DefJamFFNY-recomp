# Fighter Mod Support: M1/M2 implementation checkpoint

Local branch `research/custom-fighter-mods`, target v0.15.0. The owner authorized
M1 and M2, including computer testing. M1 is complete for local Windows
acceptance with the approved 2D selector/3D entrance-combat scope; macOS/Deck
smoke checks remain unperformed. M2 implementation is complete for local
handoff with the testing qualifications below. No push or public PR. Earlier entries below
are historical checkpoints; latest M1/M2 results appear at the end. M3 was
subsequently authorized on 2026-11-06; its current work is recorded in the
[M3 checkpoint](fighter-mod-m3-2026-11-06.md).

## Current acceptance summary

M1 has Windows evidence for independently registered appearances, native custom
portraits/grid artwork, entrances, combat and basic teardown. Two ordinary packs
coexist; the original resources remain available. Selection stays in native2D
menus as approved. Cross-platform smoke and broader lifetime stress remain open.

M2's ordinary data pipeline now supports independently bound moveset tracks,
voices, AI tendencies, intro/victory tracks, four-shot Blazin activations and
paired finishing animations. Human and CPU playback have positive evidence.
The corrected full four-participant run135539 passes all eight combat/result
checks with zero reported native faults and byte-identical save restoration.
The earlier stock regression passes5/5 (1769 unit tests passed). The final
controller-driven subject-finisher check has positive proof for both roles,
including a counterpart from the other pack. At the owner's handoff request,
the queued routine regression was canceled before starting and the focused
test was closed normally after that proof. Its save tree restored byte-identically;
it is not a completed full-match pass. The observation-only final-build event
has68 focused native checks and full-match145033 evidence; the earlier stock
pass predates that event. These qualifications accompany the local M1/M2 handoff.

This is local adapter acceptance, not launcher or production-profile readiness.
Authoring retains verified donor timing, root motion, events, hit behavior,
facial helpers and cameras. Unknown rigs/render programs and arbitrary new
gameplay logic are not admitted. Resource count ceilings are admission bounds,
not measured maximum-performance guarantees. Normal-profile/launcher gates stay
closed until their milestones; no public PR or publication has occurred.

For M3, the approved first choice remains native profiles plus a versioned
extension. Stress tests must establish atomic native/extension writes, recovery,
stable identity through pack changes, repeated-match cleanup and Story/created
fighter interactions. If that boundary cannot be made safe, the already-approved
isolated-profile fallback remains available. No new architecture choice is
required to interpret the M1/M2 result. The owner intends to continue M3;
this work has not started it.

### Handoff to M3

- Continue on `research/custom-fighter-mods`; keep all work local unless the
  owner changes the publication instruction. The toolkit pin is unchanged.
- Implement the already-approved native-profile extension path first, with
  the isolated-profile fallback if safe atomic writes/recovery cannot be proven.
- Keep launcher/normal-profile gates closed until lifecycle and integration
  acceptance. Do not treat count admission limits as performance guarantees.
- Known testing issues: some forced mid-combat shutdowns exceeded the harness's
  15-second wait; their saves subsequently restored. An intermittent startup
  callback to `0x81000344` predates this work and remains unexplained. Failed
  trials are retained below; neither issue was present in the accepted full runs.
- macOS/Deck smoke, repeated-match/resource stress, and release acceptance
  remain future milestones. No additional architectural decision is requested.

## Implemented and checked

- `fighter_motion_records.py` decodes and losslessly encodes packed WAZA and
  WPAR rows. Native offset, bit width, signed conversion, float32 scaling,
  sentinels and unused tail bits are explicit. The inspector exposes raw fields;
  gameplay meanings and animation/event joins remain unvalidated.
- Independent comparison against the local native decoder oracle matched every
  output byte for 2,181 move and 320 core records, with exact input round trips.
  Evidence: `logs/fighter-m2-typed-motion-oracle-comparison.json`. This extends
  the earlier field-only oracle comparison; it is not in-game behavior acceptance.
- `fighter_render.py` tracks command boundaries and the separate parameter
  cursor. Geometry now locates index data through op14 and optional draw headers
  through op2, instead of assuming offsets relative to the animation import.
  Omitted draw state is reported as inherited, not inferred to be safe.
- `fighter_skin.py` validates three-weight palettes, all dereferenced bone
  indices, and short vertex selectors against the two uploaded constant banks.
  It checks explicit exported VB headers and rejects relocations in numeric data.
  Shader execution and animation compatibility remain separate gates.
- Command parsing passed 3,560 retail and 2,031 community render resources.
  Skin checks passed 78 retail and 47 community models, 134,516 palette rows.
  Geometry passed 47 community and 77/78 retail models; retail402A's different
  stream layout is still unsupported. Evidence: `logs/fighter-m1-render-parser-corpus.json`,
  `logs/fighter-m1-skin-corpus.json`, `logs/fighter-m1-command-geometry-corpus.json`.
- `fighter_entity.py` emits bounded single-model entity registrations from typed
  declarations into a hash-verified baseline. It preserves the original bytes,
  including legacy processing instructions and the unused example after the
  root. Pack-supplied XML is not accepted. Names and native hash collisions fail.

Full unit gate before the entity composer: **1,252 passed, 27 skipped,
1 deselected**, `logs/fighter-m1-m2-unit-nov04.txt`. Subsequent Python entity,
native-adapter, probe and motion-record checks: **66 passed**. A sandboxed retry
failed only while creating Windows junction fixtures; the authorized run with
the required filesystem permissions passed. No C source, generated code or
toolkit pin changed in this checkpoint.

## Native diagnostic evidence

The private diagnostic uses model610 from the local community assets, validated
against the structural readers, original render-program hashes and original
import families. It adds files to a composed original V2IP archive and changes
one research fighter's Model property. It uses the existing language transport
only to deliver experimental composed files. This is **not** a Fighter package
format, a compatibility profile, or a general appearance adapter. Ordinary pack
definitions still reject unimplemented authored resources.

Four initial attempts crashed before the new main model was parsed:
`logs/run-20261104-205359.log.err` (old forced-start route),
`logs/run-20261104-205726.log.err` (native participant binding),
`logs/run-20261104-210203.log.err` (RefPack envelopes), and
`logs/run-20261104-210506.log.err` (entry trace).
The later tests read the correct compressed face payload but passed a non-ELF
cache pointer to `109F80`. Compression alone was not the cause. All save guards
reported byte-identical restoration.

The resource manager also requires a model definition in `assets/entity.xml`.
`97710` hashes the Model name and calls manager18 lookup `70730`; its descriptor
then supplies the cache key read by `97AA0 -> 6EE30 -> 26A00 -> 26760 -> 10B430`.
Missing definitions must be rejected before reaching this native path.

Adding a generated entity declaration in `logs/run-20261104-210943.log.err`
removed the loader crash and reached the actual model610 ELF (section-table
offset `0x5B928`, log line15332). The run rendered the venue/crowd but remained
in pre-fight phase0, with both actors initialized at their starting positions.
It was deliberately ended after observing the stall: 161 frame reports,
zero crashes/watchdogs/unresolved calls, saves restored identically. This is a
**failed combat test**, not an M1 pass. Captures are retained under
`logs/fighter-window-runs/fdb5e1df64634d0bad2824026544f431/captures`.
`logs/fighter-m1-model610-entity-live.json` records the read-only live state.

## Remaining work and next evidence

### Subsequent controlled appearance result

Adding a compact taunt mapping from `V2IP_610A` to the existing `CI_113A` /
`CE_113A` clips still stalled in phase 0 (`logs/run-20261104-211538.log.err`).
The run was deliberately stopped: 104 frame reports, no crash/watchdog/unresolved
calls, and byte-identical save restoration. Token-scanner inspection does not
indicate a newline requirement; a formatted-record control is being tested.

The next control replaced only the composed cache's original `113A` model,
texture and face payloads with the validated `610A` payloads, keeping `Model`
set to `V2IP_113A`. The original dump was untouched. This **is not an independent
resource registration** and would change retail Blaze's appearance in that
cache too. It is a diagnostic experiment, not the proposed shipping adapter.

That control (`logs/run-20261104-211926.log.err`) showed the new blond fighter
in native combat with attacks and damage in both directions, and reached a
decisive match result at step 13739 (CPU winner, clock 4:32). The custom fighter
identity remained present in `Game.GetMatchSummary`. It completed with 173
frame reports, zero crashes/watchdogs/unresolved calls, two verified save
generations and byte-identical save restoration. Captures are preserved under
`logs/fighter-window-runs/601d206f4a3a4726bf25ffbe1b319a01/captures`; the first
combat teaser is `logs/fighter-m1-teasers/model610-first-combat.png`.

This establishes that this geometry/skin can fight with the retail donor's
behavior. Independent resource naming/registration remains the blocker; it
does not establish a general appearance adapter, independent-pack coexistence,
or M1 completion.

### Independent registration and general compiler follow-up

The formatted loose-taunt control also failed (`run-20261104-212615`, 88 frame
reports, deliberate stop, saves restored). The cinematic trace
`run-20261104-212943` identified repeated `A3E80 -> A3830` lookup attempts for
the custom name. Live parser object `0x3770D4` referenced a 7,794-byte buffer,
matching the decompressed `assets/IntroExtro.xml` member inside `assets/nis.viv`.
Initializer `8ABF0` formats that member name. The earlier experiments modified
the wrong XML source. This trace was deliberately stopped, with 83 frame
reports, no native faults, and byte-identical restoration.

Correcting the archive target resolved the independent-name stall.
`logs/run-20261104-213244.log.err` completed with new `610A` files added alongside
all original entries: movement at step164, attacks/damage, decisive result at
step9402 (3:08, CPU winner), and verified native identities100/17. It had134
frame reports, zero crashes/watchdogs/unresolved calls, two verified save
generations and identical restoration. Captures:
`logs/fighter-window-runs/8075808e2ec94b9f852acd4e9c9f55ca/captures`.
This supersedes the independent-registration blocker above; the experiment
still used the private transport and is not the complete milestone.

The subsequent general implementation adds `fighter_appearance.py`,
`fighter_resource_files.py` and `fighter_cinematics.py`. Ordinary resource
definitions carry hashed package-relative data files; the compiler assigns
stable native names, checks original-resource pins and rig compatibility,
preserves retail data, and composes three files with entity/cinematic mappings.
It currently requires verified donor facial-animation data. Authored face
curves, complete render parameters and basic lifetime acceptance remain gated.
Single- and multi-pack definitions use the same compiler. Two-pack synthetic
tests verify independent names, exact preservation of original archive payloads
and SOD rows, deterministic ordering and mismatched-source rejection.

The research native loader accepts these generated files directly, verifies
their hashes, rejects incomplete triples and fails shared-file redirect
conflicts. SHA-256/file receipt code was factored from the existing language
implementation into `src/hooks/mod_sha256.h`; it is tested independently
against Python, including UTF-8 paths, padding boundaries and streaming input.
No generated C or toolkit pin changed. Release build passed
(`logs/fighter-appearance-build-nov04.txt`). Full units passed **1,304 tests,
27 skipped, 1 deselected**, 98.43s (`logs/fighter-m1-general-unit-nov04.txt`).
Subsequent aggregate source/decompression budget checks passed16 focused tests.
Native ordinary-manifest acceptance is being run separately; do not substitute
the earlier diagnostic result for that acceptance.

1. Finish ordinary-manifest native acceptance using the general appearance
   compiler, requiring movement, attacks, damage and a match result. The earlier
   diagnostic independently named model now passes, but used a private script.
2. Complete render relationship/parameter validation, menu presentation and
   basic ownership/cleanup. Exercise a second independent pack through the same
   native path, with original fighters preserved. Native namespaces and typed
   entity/cinematic/archive composition are now implemented for research.
3. Complete M2's semantic motion/event/animation/voice/AI/cinematic adapters.
   The original core descriptor table has 141 initialized 16-byte entries with
   adjacent live state; it cannot grow in place. The active core index is a
   dword in the inspected participant path. No descriptor is proven spare.
   Prefer explicit extended storage/resolution over borrowing an original row.
   Audit retained references and every consumer before implementing that route.
4. Prove independent pack coexistence with humans, CPUs and four participants,
   document measured capacities separately, and finish milestone tests before
   asking the owner to move to M3. Broad save/lifecycle stress remains M3.

The focused loader, renderer and motion audit reports alongside this file carry
supporting addresses. This checkpoint supersedes their earlier tentative
negative findings where the native diagnostic supplies newer evidence.

### Ordinary manifests, template compilation and FZUI follow-up

Ordinary appearance acceptance passed in `run-20261104-214840.log.err`:
native identities100/17, movement/attack/damage and result,169 frame reports,
minimum107/median120/maximum120, no native faults, two verified generations,
and byte-identical save restoration. Two independent packs then passed in
`run-20261104-215734.log.err`: identities100/101, new models610/611, human/CPU
combat through a decisive result at step15260 (5:02),193 frame reports,
minimum109/median120/maximum120, no faults, two generations and identical
restoration. Summary logs are `fighter-appearance-alpha-native.txt` and
`fighter-appearance-pair-native.txt`; captures are preserved in sessions
`3071e3ce348b4ef9b83bd42bdadc22fc` and `88bc3e84a21d429f8ab09bf0d1e1a6bc`.
These runs predate the template compiler below; do not substitute them for
acceptance of its rebuilt output.

`fighter_model_compile.py` now reconstructs geometry using a hash-verified
retail rendering template. It preserves the template's material/mesh/program
layout and all rendering controls, replacing checked vertex/index/palette
buffers, rig transforms and texture shape identities. It rebuilds relocations,
VB adjacency and count references, and gives internal model/RM/VB exports the
resource namespace. Unsupported layouts fail. This is the approved hybrid
adapter direction, not a community-specific runtime. The offline corpus passed
47/47 community main models with exact parsed mesh metadata preservation:
`logs/fighter-retail-template-corpus-nov04.json`. That corpus predates the final
namespace rewrite and is structural evidence, not visual acceptance.

The first compiled-output native diagnostic, `run-20261104-220659.log.err`,
completed with identities100/17,152 frame reports, zero faults, two generations
and identical restoration. **Visual acceptance failed:** the new body showed
a red/green material. Its internal exports retained the retail template's
name. Resource-owned internal names are implemented and being tested through
the general compiler; this is a candidate correction, not an established cause.
The failed visual captures remain under session
`4ce4a94c2d7f44e6827c8b3bc0e983a2`. M1 remains incomplete.

FZUI is now decoded/encoded as `parameter` records and exposed by the ordinary
motion inspector. Primary review corrected the audit's initial wire order and
conditional sentinel: fields+30..84 precede the four leading triples; +48 is
rewritten only when raw+44 is not7FF and raw+48 is7FF. The multiplier is the
float32 at292378. Independent native-oracle comparison passed **6,274 rows**:
retail2,088+873, community2,088+967, and258 random/edge records. Every decoded
byte and packed round trip matched; each consumes311bits and preserves its
one unused bit. Evidence: `logs/fighter-fzui-native-oracle-comparison.json`.
This establishes storage conversion, not behavior/event/animation semantics.

Full units after the first template compiler passed **1,312 tests,27 skipped,
1 deselected**,96.72s (`logs/fighter-template-full-unit-nov04.txt`). Subsequent
namespace checks passed10 focused tests. C source/executable is unchanged
since the earlier appearance-loader build. Stock/language native regression,
template visual correction, repeated resource loads and four-participant
appearance acceptance remain next gates before M1 can be completed.

### Corrected texture bindings and compiled-output acceptance

Neither namespace changes (`run-20261104-221702.log.err`) nor preserving the
template's symbol/relocation order (`run-20261104-222422.log.err`) corrected
the red/green material. Both are retained as failed visual diagnostics. The
missed relationship was the model root+BC counted shape-key table: the main
TAR imports named A610 but its first lookup key still named template B126.
Native112310/1130A0 consume this table;113270 determines each variable bitmap
tail size. The compiler now rewrites its keys consistently with the typed TAR
mapping, preserving the template's item counts, bitmap and control structure.
Tests include variable record lengths, short bitmaps and missing terminators.

Compiled ordinary-manifest acceptance then passed in
`logs/run-20261104-223019.log.err`: identities100/17, correct visible materials,
movement, input-linked attacks/damage and a decisive result at step6758,
clock2:12. There were114 frame reports (min107/median120/max120), no native
faults, two verified save generations and byte-identical restoration. All seven
combat assertions passed in `logs/fighter-template-shapekey-combat.json`.
Captures are preserved under
`logs/fighter-window-runs/0179b60f8eb64f6ebb14795852b9651f/captures`.
Updated offline compilation passed47/47 community models with identical parsed
mesh metadata; `logs/fighter-template-shapekey-corpus-nov04.json` records their
compiled hashes and shape keys. This is one compiled model's native acceptance,
not all47 models' visual acceptance.

Texture admission now fingerprints opaque header/attachment controls against
hash-verified original layouts. Authored dimensions, pixels, palette colors
and shape names remain separately bounded. Arbitrary material text or unknown
control words cannot pass merely by being ASCII. Composition rejects conflicting
same-name texture content, naming both owners and requiring a model/texture
rename. Identical shared texture content is allowed. This implements the agreed
D4 error path without silently choosing one pack's content.

The runtime probe now has explicit `--require-combat` and `--require-result`
gates. Each expected match is judged separately from bounded telemetry; an
unfinished fight cannot count as a completed result. Focused checks passed28
probe tests and23 appearance/texture/model compiler tests. Two-pack compiled
combat, four-pad coverage, basic resource cleanup and stock/language regression
are still in progress; M1 and M2 remain incomplete.

Two compiled ordinary packs subsequently passed in
`logs/run-20261104-223447.log.err`: identities100/101, models610/611, correct
materials, human/CPU movement/attack/damage and a decisive result at step18151,
clock6:02. There were214 frame reports (min109/median120/max121), zero native
faults, two verified generations and identical save restoration. All seven
combat assertions passed in `logs/fighter-template-pair-combat.json`. Captures:
`logs/fighter-window-runs/f49b3a29cfaf4de694399ddb4a296e5f/captures`.
The selector capture still uses inherited retail portraits; it is not custom
portrait acceptance and the selector does not display a live 3D model.

Full unit gate after the texture control/conflict checks and combat acceptance
helper: **1,318 passed,27 skipped,1 deselected**,99.64s, recorded in
`logs/fighter-appearance-final-unit-nov04.txt`. The subsequent recorder switch
only forwards the existing `RECOMP_RECORD=1` diagnostic for resource measurements.

### Four human participants, repeat match and motion-reference checks

Four human controllers passed ordinary-manifest acceptance in
`run-20261104-224929.log.err`: two packs with two logical fighters each,
identities100/101/102/103, correct compiled610/611 appearances and all six
combat assertions. There were121 frame reports (min99/median120/max120), no
native faults, one verified generation and identical save restoration. Captures
are in session `d84002b0d3c946afbda5898846414fe4`. The earlier224615 attempt
used incorrect six-column input on the three-column four-player grid; it was
stopped and is an input diagnostic, not an acceptance result.

The resource-observation build passed in
`logs/fighter-resource-observation-build-nov04.txt`. It records the toolkit's
existing live heap/contiguous counters at research match setup and Game.Quit.
These count allocator blocks, not individual assets or internal pool occupancy.
The toolkit pin and generated game code did not change.

`run-20261104-230040.log.err` then passed the two-match route with both compiled
packs: identities100/101 in each match, ten combat assertions, first match
result, return through menus, second combat, two verified generations and
identical save restoration. There were253 frame reports, median120, min37,
max120, zero native faults. This instrumented route includes loading/menu
transitions and concurrent offline checks; the low sample has not been
attributed, and this run is not a release performance qualification.
Captures: session `b784b2fc33d64f7a834829c9c4cd9882`.

Heap bytes remained5,243,952 at first setup, first quit and second setup.
Contiguous bytes were52,449,280,53,522,432,52,510,720 respectively: the increase
at the menu transition mostly receded on reload, leaving61,440 above the first
setup. The recorder's texture cache stayed within256 entries, peaked17.05MiB
and ended15.77MiB. This supports basic repeat-load acceptance but does not prove
all allocations are freed or establish a long-run leak bound. M3 stress remains
separate. Two preflight attempts were rejected before game launch for duplicate
screenshot labels and a malformed repeated input anchor; neither counts as a
native test. Source summaries and metrics are under `logs/fighter-template-repeat-native.txt`
and `logs/fighter-resource-metrics-20261104-230040.json`.

`fighter_motion_links.py` now checks established WWAZ/WAZA/FZUI namespaces,
including the row125 synthetic boundary and state65 parameter special case.
The inspector exposes this explicitly with `inspect-motion-index --check-links`.
Independent own-generated-native comparison of1A7F30 covered **3,498,000 cases**
across141 retail and177 community cores, all local IDs, four participant routes,
and eleven actor-state combinations. All2,081,165 in-range answers matched;
all1,416,835 rejected answers were outside the declared FZUI table. Zero
mismatches. Evidence: `logs/fighter-motion-links-oracle/comparison.json`.
This validates lookup behavior and rejection, not an extended native core table.

`AnimationIndex` validates relocation-backed name/record arrays, sorted unique
names, native `_t`/`_s` index lookups with explicit missing(-1) values, type15
child edges, budgets and cycles. All446 examined retail/community banks passed
(`logs/fighter-animation-index-corpus-nov04.json`). `CurveLayouts` adds bounded
structural inspection for13/20/21/25, finite serialized floats, time profiles,
output-size requirements and inert type25 wrapper seeds. It deliberately leaves
numerical decoding, external sample/output contexts, exclusive span ownership
and runtime admission false. It passed445/446 banks under this profile; retail
base00 contains a non-increasing time sequence and remains unsupported pending
consumer-specific review. Evidence: `logs/fighter-animation-curves-corpus-nov04.json`.
Focused animation/reference checks passed41 tests.

The corrected native bank join is core ordinal+1 to `wres%03d` MNL/ORD/ORL.
MNL tokens resolve named `_t`/`_s` **indices**, not pointers. The AnimationBank
initialization callback supplies its own native dispatch word to serialized
type25 inert wrapper prefixes. No mod-supplied dispatch address is accepted.
Detailed structural leads are in the animation-bank and curve18/19/20/21 audits;
native numerical and output-context validation remains required.

Native selection uses authored2D artwork; its current donor portraits cannot
serve as acceptance of the new appearance. The owner has been asked whether
M1 should use custom portraits with3D acceptance in entrances/combat, or add a
new live3D preview. Independent M2 work continues while that decision is pending.
See the portrait-registration audit for the separate grid/large/result paths.
Neither milestone is complete; no M3 work or publication is authorized here.

Full unit gate with the MSVC environment: **1,345 passed,27 skipped,1 deselected**,
95.65s (`logs/fighter-motion-links-msvc-unit-nov04.txt`). An earlier run without
that environment passed1,113 but skipped259; it is not the native-unit gate.
The subsequent standalone inspector/CLI checks passed19 tests after fixing the
new test module's independent import path. Stock golden/menu/fight regression
passed **4/4** (loading, startup/title, main-menu goldens and fight),
`logs/regress-20261104-232133.txt`. The fight reported median120/min107
over122 seconds. These are stock regression checks, not Fighter milestone exits.

### Portrait compiler, cleanup and language follow-up

The two appearance packs also passed a combined language/native-lifetime run,
`logs/run-20261104-232316.log.err`: seven combat assertions, native identities
100/101, result, two save generations and byte-identical restoration;139 frame
reports min106/median120/max120, no faults. The runtime verified the language
screens base before adopting composed fighter presentation. The early selector
capture is on SELECT USER ID and does not itself establish the later modified
SELECT FIGHTER string. Captures: `logs/fighter-window-runs/191a50119d8b44aba3edfe6649781e09/captures`.

Registration97710 instances349CC0/3549E0 received model keys811E723C/811E72CC.
Cleanup97BF0 later received the same instances with those exact keys at+8;
each immediately entered resource release709B0 (8105D900/81060B00), followed
by manager-node unlinks6EDC0. Final watch totals2/2/3/124 include one other
resource release. This establishes the model-instance cleanup path for both
custom models; it is not a proof of all asset deallocation or an M3 leak bound.
Native heap stayed5,243,952; contiguous allocation at match completion was
53,743,616 versus52,449,280 at setup (completion precedes teardown).

CurveLayouts now inspects types11/13/18/19/20/21/25. Focused structural suite
passed22 tests;445/446 corpus banks still pass. The sole retail base00 rejection
contains eight unsigned time descents65532->0, not duplicate keys. The native
consumer zero-extends these values; no signed reinterpretation or relaxation
was applied. Numerical decoding, output contexts and span ownership remain
separate, unfulfilled gates. See the type11/type25 audit.

The draft portrait resource `eagl-portrait-1` contains six hash-checked XSH files,
explicit original layout donor, and no UI code. Compilation copies only pixel
ranges into the verified original textures and preserves original APT/CONST/O.
Generated resources are namespaced, receipted, budgeted and compiled through
the ordinary registry; two independent packs and cache tampering are tested.
Retail portrait overrides remain rejected until they have an ownership adapter.
Grid artwork remains explicitly inherited and runtime readiness stays false.
Focused compiler/probe/native-definition tests passed50 including junction checks.

The first native authored-portrait run233424 displayed a red selector placeholder:
the compiler had added RefPack to an XSH leaf whose UI loader expects raw SHPX.
The outer movie remains compressed; the inner texture is now raw. A regression
test checks raw leaf bytes, and all six portrait tests pass. This failed visual
attempt is retained separately; a corrected native run is still required.

Full MSVC unit gate after portrait integration and scalar decoder: **1,370 passed,
27 skipped,1 deselected**,96.53s, `logs/fighter-portraits-scalars-msvc-unit-nov04.txt`.
The failed visual run233424 nevertheless completed combat/result with seven
assertions and byte-identical save restoration; visual failure is not hidden by
those successful telemetry checks.

### Owned grid follow-up, November5

Raw-SHPX run234319 displayed authored portraits and passed seven combat checks,
two save generations and byte-identical restoration (170 frame reports,
min109/median120/max121). The fixture accidentally paired Carla/Peewee artwork
with Briggs/Tank models; this is not correct-fighter visual acceptance. Corrected
`portraits-matched.json` fixtures use source selections40/41 for models610/611.

The static grid compiler now composes owned Shape/Image characters, original
result-drawable templates with separate runtime allocation symbols, and two
thumbnail frames per portrait into the native selector. Original frames and
geometry remain intact. Structural tests cover relocated image-name consumers,
symbols, frame collisions and pixels. Native acceptance is still failing:
run235407 displays the correct large Briggs portrait but padlocks in both new
grid cells. Combat/result passed seven assertions, two save generations,
identical restoration;175 frame reports min107/median120/max121. Changing the
new placement flags6 to7 did not fix the padlocks in run20261105-000057
(79 frame reports min108/median120/max120, no faults, identical restoration).
Do not treat either attempt as grid acceptance. A temporary runtime-owned
diagnostic is checking actual lock state, requested/current frame and frame
count; it lives under ignored logs, not the package format.

The new shared-motion-table capacity audit identifies append-only shared rows
as a candidate at the inspected registration boundary; primary WAZA edges
remain12-bit, and new cores need separate descriptor dispatch. This is static
evidence, not native behavior admission. M1/M2 remain incomplete.

Native grid diagnostics001045/001418/001818 show unlocked custom characters,
451 total frames and requested/current frames301/302. Correcting placement
defaults and a private retail-drawable/remove-object control did not fix the
image. The actual defect was shared frame item lists: native17DD70 rebases every
pointer-list element and Action code pointer in place, without an alias guard.
The compiler now owns separate lists, Action/code and PlaceObject records per
state. The grid audit records exact instructions and original-bank uniqueness.
Native acceptance of this fix is pending. The full MSVC gate passed **1,376
tests,27 skipped,1 deselected**,95.75s
(`logs/fighter-grid-scalars-msvc-unit-nov05.txt`).

The separate FC8A0 arithmetic oracle matched7,680 scalars across1,920 weighted
adjacent-key evaluations (240 synthetic cases); output sentinels remained intact.
`interpolated_pose` is restricted to type11: primary inspection of ED3F7/ED43E
confirms type13 uses a separate EA010 four-component blend. The new output-context
audit traces raw destinations and caller-owned buffers but does not establish
their allocation extent; native animation admission remains false.

`fighter_animation_scalars.py` decodes the full-channel type11/13 scalar poses,
including unsigned quantization, low nibble first, and format/lane-specific
float32 arithmetic order. Ten invented-fixture tests pass. An independent oracle
compiled the user's own FC3F0 body and compared240 synthetic cases,2,160 pose
evaluations and8,640 scalar outputs, with zero differing bytes across fresh,
forward-cache and reverse-replay paths. `logs/fighter-scalar-oracle/comparison.json`.
This scope excludes filtered subsets, interpolation, exceptional floating-point
states and output ownership; it does not enable native animation admission.
The scalar-codec audit documents why interpolation needs weighted deltas rather
than a generic blend of already-rounded endpoints.

### Native grid and motion registration follow-up, November 5

Unique frame records fixed the two-player grid in run002558. Captures at20/42/47s
show matching Briggs/Tank thumbnails, large portraits and correct hover redraw.
There were78 frame reports (min108/median120/max120), no faults, one save
generation and byte-identical restoration. Captures are preserved under
`logs/fighter-window-runs/4e0abee17f9f4ba6a16c2e4815bce446/captures`.

Four-player grid acceptance is still failing: new cells render flat colors,
although large portraits work. Run002908 also had an incorrect expected identity
order in its test invocation; its combat assertion failure is retained. The
corrected order is alpha/first, beta/first, alpha/second, beta/second, according
to the stable ledger. Run003438 passed six combat assertions for all four
custom identities103/104/105/106, with124 frame reports101/120/120, no faults,
one save generation and identical restoration. Preserving source SHPX raster
alignment did not fix the visual failure. Run004038 tested the accepted two-player
64px result artwork/template in all selector layouts: still flat four-player
cells, six combat assertions passed,123 reports107/120/120, no faults and
identical restoration. Neither is four-player grid acceptance. A native draw-state
diagnostic is the next discriminator; normalized ELF relocation checks found
no copied-geometry defect.

`MotionCoreTemplates` now composes owned WPAR/WWAZ pairs from hash-verified
original templates while preserving the six shared tables and all original
cores byte-for-byte. Nine focused tests cover independent packs, deterministic
allocation, budgets, donor validation and descriptor indices254..257. Receipts
distinguish zero-based descriptor indices from one-based Character core/bank
numbers. Core0/1 donors remain rejected because their special behavior needs
an adapter. A local141-to143 composition passed reinspection, but no native
descriptor or animation-bank dispatch has been wired; runtime readiness remains
false. Evidence: `logs/fighter-motion-core-composition-nov05.json`.

The output-context audit now identifies the initialized actor's22A90 allocation
path: two blend buffers each contain48*N bytes, with N from the attached
context. This resolves the allocation-size question for that path, not semantic
animation-to-rig binding or arbitrary external output pointers. M1/M2 remain
incomplete; M3 has not started.

The draw-state diagnostic004701 established the four-player failure: valid64px
textures, but sampled UVs spanning0..44 instead of normalized coordinates.
Source.data+310 points to the typed parameter `ScaleMatrix::1::TextureMatrix`.
The compiler renamed the texture references but omitted this matrix name;
native1813E0 therefore normalized it using another image's dimensions. The
compiler now renames that fourth reference to the owned image ID. A focused
fixture asserts the semantic matrix identity, beyond relocation correctness.
The common64px diagnostic policy was removed: each layout again uses its
matching original result template/artwork. Run005328's four-player24s capture
now shows matching Briggs/Tank thumbnails for all four participants; its draw
trace shows32px textures with UVs0..1. Final run/restoration summary is pending.

That trace also exposed an unchecked native512-model temporary table in1813E0
via17F080. The composer now rejects exceeding it and enforces image IDs equal
to their APT character indices (the native normalization callback's key).
This is a temporary safe admission bound, not the intended long-term roster
limit. A bounded audit recommends replacing the table with direct model
enumeration. That capacity adapter and acceptance above512 remain outstanding.
Focused grid/portrait/motion/scalar suite:31 passed.

Run005328 completed:92 frame reports109/120/120, no faults, one save generation
and identical restoration. Captures are preserved under
`logs/fighter-window-runs/60a072b1422c48dc996a9c276359d10d/captures`.

The UI capacity adapter is now implemented and rebuilt. It enumerates models,
validates/sorts their numeric identities and feeds dense512-pointer batches to
the unchanged native normalization body. This avoids unchecked numeric-ID
indexing while retaining original matrix arithmetic. Seven compiled invented-
guest tests cover0/1/511/512/513/1100 models, sparse IDs, once-only order,
scratch canaries, callback registers/arguments, inactive calls and budget failure.
Re-lift confirms the real17F080 wrapper is called by1813E0_gen. The compiler's
temporary512 guard is replaced by the independent four-digit namespace bound.

Native capacity acceptance010829 used402 grid templates and600 module models;
allocation was reversed so the visible portraits use IDs above1200. It showed
correct four-player thumbnails, verified identities103/104/105/106 and passed
six combat assertions, with124 frame reports min78/median120/max121, no faults,
one save generation and identical restoration. This tests model population and
sparse IDs; it is not a400-fighter roster or a release performance acceptance.
Captures: `logs/fighter-window-runs/3efb03d3efdf43d798beae2ab44991d4/captures`.
Full MSVC unit gate: **1393 passed,27 skipped,1 deselected**,101.26s
(`logs/fighter-ui-capacity-msvc-unit-nov05.txt`). Three-player visual acceptance
and stock native regressions on this rebuilt executable are next.

### 2026-11-05 three-player portraits and motion binding receipt

Run011515 completed three-player browsing of two independent two-fighter packs.
The20s/26s/32s captures show Briggs/Tank/Briggs with matching large portraits and
native grid thumbnails.114 frame reports min108/median120/max120; no faults,
one verified save generation and byte-identical restoration. Preserved captures:
`logs/fighter-window-runs/fff4592983004c4fadeed1ca4630a25d/captures`.
Stock regressions on the new UI executable are running serially.

The owned motion-core composer now emits a checked FMC1 relative-offset receipt.
It verifies the original-prefix hash, whole composed-stream hash, contiguous
new descriptor ordinals, one-based Character/bank bindings and exact inherited
WPAR/WWAZ bytes.18 focused tests pass, including descriptor254..257 and tampered
bindings/payloads. This remains a registration foundation, not native acceptance
or admission of authored moves/events. The native reader audit additionally
found a core-indexed float lookup in1B2C60; it must be handled before claiming
that adapting the four descriptor readers is sufficient. No retail row swapping
or actor identity substitution is planned. M1/M2 remain incomplete; no M3 work.

### 2026-11-05 owned native motion adapter — acceptance in progress

Stock regressions on the UI-capacity executable passed4/4 in7min
(`logs/regress-20261105-012943.txt`): boot25s, title123s, menu74s,
fight215s; fight median120/min107 presents per2s.

The motion adapter now validates FMC1 receipts and exact inherited core pairs,
registers full-width sidecar descriptors against the loaded source digest,
invalidates them before native source teardown, redirects the four descriptor
readers, maps inherited animation banks and handles1B2C60's independent static
scalar table. Original core IDs and native retail records are not swapped.
Eight real entry wrappers are regenerated; inspected direct calls reach them.
Research remains restricted to the isolated harness namespace.

MSVC invented-guest adapter tests:17pass, including16,000 frame scan cases,
distinct output/context participants, special/external moves, parameter override
sum wrap/argument-slot mutation, mixed scalar classes, source reload, expired
and malformed receipt rejection. Full unit gate:1418pass/27skip/1deselected,
with one recorder bundle-frame-count failure292vs300 while a release build was
running. Unchanged isolated recorder suite then passed6/6 in45.79s. No test
expectation was weakened. See `logs/fighter-motion-msvc-unit-nov05.txt` and
`logs/fighter-motion-recorder-recheck-nov05.txt`.

First native high-core run014255 is **FAILED acceptance**, not a pass: four
native menu identities103/104/105/106 verified, source generation1 and native
cores256..259 registered, all four mapped to inherited bank5. Presentation
stopped before combat setup; no crash/watchdog was emitted.66frame reports
99/120/120, one save generation and identical restoration. The live-stack
attempt was too late (process had ended); no stack diagnosis is claimed.
A longer traced reproduction is running to capture the blocked thread.
`logs/fighter-motion-four-high-native.txt`, `logs/run-20261105-014255.log.err`.
M1/M2 remain incomplete; no M3 or public publication.


### 2026-11-05 audio-table diagnosis and reader hardening

014823 reproduced the high-core hang; live host stack sampled1E7CD0's
stream scan beneath intro audio. No acceptance claimed.020004 data watch
then caught3E170 indexing fixed audio metadata with one-based core257:
voice3403B4 became2929016Dhex. Both diagnostic runs were explicitly
stopped and their save trees restored identically (one generation each).
Evidence: fighter-motion-high-native-stacks.txt and
fighter-motion-voice-write-native.txt underlogs/.

A new real3E170 wrapper delegates native setup with a private guest-stack
copy of its0x84-byte input, mapping only audio template keys. Actor cores
remain full-width. WAZA/FZUI/NAME dimensions, group populations, padding,
and string boundaries are now independently checked at native startup.
40focused MSVC tests pass, including pre-motion audio setup, mixed retail/
custom/empty slots, unchanged caller input, unknown-template rejection and
22malformed-table cases with recomputed matching digests. Native rebuilt
acceptance remains pending. No authored voice/behavior admission, M3 or push.


### 2026-11-05 full-width four-human combat acceptance

Run021106 PASS: independent packs' four selected identities103/104/105/106,
native cores256..259, inherited audio templates5/5/5/5, six combat assertions,
121frame reports min108/median120/max120, zero crash/watchdog/unresolved
calls, one save generation restored identically. Captures in
logs/fighter-window-runs/9d86677eadd148ae81540f5445a3c8cb/captures show the
four fighters in combat. Main harness: logs/fighter-motion-audio-high-native.txt.
This is acceptance of high-core inherited behavior, not genuinely authored
moves/voice/AI or fullM2. A one-human/three-CPU route is being checked next.

Type18 quaternion forward replay now matches isolated native helpers:
240cases/3360channelposes/13440scalars/0byte differences. 13focused Python
fixtures pass. Interpolation/cache/scatter and other numerical codecs remain
separate gates. See fighter-animation-quaternion-codec-2026-11-05.md.


Run021813 PASS onehuman/threeCPU with the same two independent packs and
native cores256..259: identities103/104/105/106, five combat assertions,
174frame reports min96/median120/max121, zero crash/watchdog/unresolved
calls, one save generation restored identically. Preserved captures:
logs/fighter-window-runs/48c744e7a4b5486d8e864972c9025be1/captures.
Main log: logs/fighter-motion-audio-cpu-native.txt.

Type18 native interpolation helper comparison expands coverage to53,760scalar
results with zero byte differences, weights0/.25/.5/1. Native source digest
and remaining cache/scatter gates are in the quaternion report. Stock quick
regression and clean full MSVC unit rerun are next; no C edits during them.


### 2026-11-05 inherited motion checkpoint accepted

Stock quick regression passed all five checks in eight minutes:
`logs/regress-20261105-023405.txt` and
`logs/fighter-motion-audio-quick-regression-nov05.txt`. Clean full unit run:
1455 passed, 27 skipped, 1 deselected (101.20 seconds). Boot, title and menu
goldens match. Stock fight: 122 seconds, median120/min114 presents per2s.
Together with the two high-core combat routes above, this accepts the current
inherited motion/audio adapter checkpoint. It does not complete M2: genuinely
authored behavior and independently registered voices remain outstanding.
No M3 work or public publication.


### 2026-11-05 owned PCM voice compiler and native comparison

Added bounded mono PCM16 stream writer/validator and verified-template bank
composition.71 focused tests pass, including malformed lengths/sample counts,
independent bank keys, event metadata preservation, explicit inherited samples
and offset-unit expansion beyond16MiB without truncation. Twelve real local
templates compose successfully (Character/Taunts/Enviro, donors4/5/22/500).
Original DAT tails can contain unindexed bytes beyond HDRterminal; the compiler
excludes/reports them rather than interpreting them as sample data.

Native parser/packet/PCM comparison:120 invented streams,311430 samples, zero
byte differences; partial reads, final zero-fill and exhaustion checked.
`logs/fighter-voice-oracle/comparison.json`,
`logs/fighter-voice-oracle-nov05.txt`,
`logs/fighter-voice-bank-template-validation-nov05.json`.
This is not in-game authored-voice acceptance. See the rewritten voice report
for the200-byte native loaded-flag limitation, independent WORD bank keys,
event metadata layout, and remaining family-selection/intro-extro mapping.
M1/M2 remain incomplete; no M3 or publication.


### 2026-11-05 independent voice registration and device playback

Added compiler-owned speech archive composition and FVA1 core-to-voice receipts;
real3DB00 dispatch avoids the200-byte native flag limit while preserving native
allocation/unload ownership and supplemental banks.14 MSVC adapter tests pass.
CPU030757 and four-human031755 pass five/six combat assertions respectively,
all four cores256..259 and voices600..603, no crash/watchdog/unresolved calls,
and identical save restoration (one generation each). Detailed frame counts,
logs and qualifications are in fighter-voice-registration-2026-11-05.md.

A second CPU032502 probe records all four owned entrance tones at exact expected
997/1499/2001/2503Hz in the device mix. Its software-decoder watches remain zero
because native129790 also has a hardwarePCM branch; this is independently
traced, not a failed decoder. Combat requests find all four IDs, but complete
category/sample/extro coverage is not claimed. Stock quick regression is running.

Authored animation work now has a typed quaternion track encoder and a verified
bank composer (16 focused tests). It preserves inherited parent timing and
paired records, requires exact rig identity and full quaternion coverage, and
bounds measured quantization error. Not yet natively accepted. The WWAZ word1
join to MNL ordinal is traced through1B4930/1A85A0/A0830. M1 preview clarification
remains pending: native portraits plus3D entrances/combat is recommended; a new
live3D selector preview is a different UI addition. M1/M2 remain incomplete.
No M3 work, push or public PR.


Voice runtime stock regression PASS5/5: logs/regress-20261105-034041.txt,
logs/fighter-authored-voice-quick-regression-nov05.txt. Working-tree full unit
run1566passed/27skipped/1deselected in101.03s; boot/title/menu goldens match;
stock fight120s, median120/min114presents per2s. No thresholds or goldens
changed. This accepts the first voice runtime checkpoint; M2 remains open.

### 2026-11-05 authored animation and AI integration in progress

Animation native oracle PASS20cases/220evaluations/77,880float slots, zero
byte differences. Native adapter12MSVC checks pass. CPU034831 loads four
owned banks1000..1003 with cores256..259, five combat assertions,173 frame
reports106/120/120, zero faults and one byte-identically restored save
generation. ED000 is positively executed; only two wrapper identities were
observed, so this does not prove all four authored clips ran. See the authored
animation report for exact logs and watch totals.

AI now has a data-only profile compiler (24 named tendency fields,23 editable,
canonical1..5 authoring range; inherited stage/trigger resources). FIA1 binds
full core IDs to bounded profile names at the native C9110 boundary. The native
parser retains ownership; post-load checks reject silent profile fallback and
log actual parsed tendency values.28 focused Python/MSVC checks pass. Re-lift
and release build pass (`logs/fighter-ai-relift-nov05.txt`,
`logs/fighter-ai-build-nov05.txt`); combined native AI/animation CPU run ongoing.

Moveset selection composer12tests pass. Edits preserve each target action's
MNL range while copying source behavior and matching MNL/event-family aliases;
all actual MNL parameter resolutions are rechecked. Current bounded profile
accepts same-bank one/two-motion families with matching control flags, excluding
special action windows. Original shared WAZA/FZUI bytes stay unchanged. Actual
core5 action6<-5 composes successfully; native receipt/admission is not yet
implemented. It is not evidence of authored hit logic or Blazin support.

M1 preview clarification remains pending; M2 moveset/event/cinematic coverage
and final regression remain incomplete. No M3, push or public PR.

### 2026-11-05 AI CPU/four-human acceptance and selected movesets

CPU040424 PASS5combat assertions,174frame reports99/120/120; four-human041104
PASS6assertions,199reports96/120/120. Both zero crash/watchdog/debug-layer/
truncated-batch/unresolved-call faults and one byte-identical save generation.
All16 native AI tendency rows per match show the intended per-core values.
See fighter-ai-registration-2026-11-05.md for paths and capacity qualifiers.
Read-only native memory sample also confirms four visual table entries and
full core IDs (`logs/fighter-animation-human-model-table-nov05.txt`). ED000
EBX contains a truncated model animation context, not an actor pointer;
serialized-record membership needs separate evidence.

FMC2 selected-core receipt and native validator implemented;56 combined MSVC
motion/selection tests pass (`logs/fighter-moveset-native-unit-nov05.txt`).
14 Python selection tests pass, including coupled bank-name aliases and
preserved neighboring parameter ownership. Incremental build passes
`logs/fighter-moveset-build-nov05.txt`; first combined native selected-moveset
CPU test is running. No completion claim until its assertions and actual
selected-action execution have been checked. Remaining cinematic/Blazin
binding work and final stock regression are still required.

### 2026-11-05 selected moveset combat and cinematic compiler checkpoint

Four-human043214 PASS6combat assertions,199frame reports96/120/121; zero
crash/watchdog/debug-layer/truncated-batch/unresolved-call faults and one
byte-identically restored save generation. Log: run-20261105-043214.log.err;
driver: fighter-authored-moveset-human-native.txt. Combat-phase diagnostics
prove action54 selections for cores256/257 and action56 for core258. No
claim that every selected action or all four edited cores executed follows.

The selected-moveset compiler/native validator now reject aliases from other
active actions into the edited MNL interval. Real action98 aliases action55;
editing55 would also change98. Tests include that non-owning alias.71 focused
Python/native checks passed before the additional native alias test, then17
selection-native checks passed. FMC2 preserves complete inherited parameter
families; arbitrary new hit/event behavior and Blazin remain unsupported.

The CPU042229 read-only combat-phase proof matched28 observed context/record
pairs to owned track descriptors across all four participant slots. Equal
duration tracks can have identical descriptors; the next proof additionally
checks the bank's record cell, parent/child edge and descriptor relocation.
That stronger live check is still being collected; do not treat the older
descriptor match as proof of a unique clip token.

A repeat044235 omitted its explicit browsing stage and remained at selection.
It was deliberately stopped:118frame reports106/120/120, zero fault categories,
one verified generation and identical save restoration. This is a failed test
fixture, not combat acceptance. Retest044717 restores the stage, exact command
saved in logs/fighter-authored-moveset-live-retest.ps1; still running here.

New fighter_cinematic_compile.py has6 focused tests and a real local CI_113A /
CE_113A composition probe. It generates independent FI00000/FV00000 bundles,
typed full-rig body quaternions, and retains trusted camera/face/hair/root-motion
and timing. Renaming only touches parsed symbols and indexed names. FIC1 ties
full core IDs to independent generated XML labels and hashes both archives.
Source v2ta SHA7385473c185e40525c2b821888b1e29da3a4d21e6fb69fcdc73725fb6d5da6c7;
probe logs/fighter-cinematic-compiler-probe/receipt.json. Native registration
and playback are not implemented yet. No completion, M3 or publication.

### 2026-11-05 cinematic native result checkpoint

The preceding pending items are superseded by the authored-animation and
cinematic reports. Strong combat proof044717 matched28/28 observed owned
record/descriptor pairs across all four participant slots, with no unmatched
pairs. All four edited cores positively executed selected moves in combat.

Cinematic FIC1 adapter and three scoped real wrappers are implemented and
built. Seven Python and21 MSVC checks pass. Human050022 passes6combat checks;
CPU051136 passes8combat/result checks,324frame reports101/120/120, zero native
fault categories, one byte-identical save generation. All four independent
intros were selected/body-bound; core259's winning FV00003 was also selected,
bound and matched by the named live pose sampler. Two cores sharing one
appearance selected different intro resources. Exact evidence and visual
qualifications: fighter-cinematic-registration-2026-11-05.md.

Stock quick regression for the complete animation/moveset/AI/cinematic batch
is running. M2 still needs Blazin registration and visual sequence acceptance;
general pack admission remains deliberately gated. M1 preview clarification
remains unresolved. M1/M2 are not complete and M3 has not started.

### 2026-11-05 integrated behavior regression

Stock quick regression PASS5/5 in9minutes:
logs/fighter-animation-ai-cinematic-quick-regression-nov05.txt and
logs/regress-20261105-053305.txt. Units1673passed/27skipped/1deselected;
all three goldens unchanged; stock fight120seconds,120median/114minimum
presents per2seconds. No thresholds changed. This covers the current native
animation, selected moveset, AI and cinematic wrappers together.

Subsequent Python hardening adds an incremental aggregate animation archive
budget and validates nested receipts/mixed core-key types before sorting or
indexing.44 focused animation/moveset checks pass. No further C changes.
Repeated diagnostic drivers and the named cinematic live sampler are now
source scripts under scripts/, retaining guarded saves and local-only assets.
These are reproducible development fixtures, not public package admission.

Ordinary resource-definition integration still needs a shared coordinator
behind fighter-registry.compile_inputs: allocate owned cores consistently,
couple FMC2 edits with their MNL aliases, bind voice/AI/cinematics using that
same core map, compose cinematics on the already-composed NIS archive, then
hash and emit the exact artifact set. Do not introduce a parallel installer
or silently enable shipping gates. This belongs to M2, while activation,
rollback and normal-profile workflows remain M4.

### 2026-11-05 Blazin classification and ordinary behavior composition

Native055646 passes8combat/result assertions,349frame reports101/120/120,
zero crash/watchdog/debug-layer/truncated-batch/unresolved-call categories,
one byte-identically restored save generation. Driver
logs/fighter-blazin-mask-cinematic-native.txt; log run-20261105-055646.log.err.
Cache logs/fighter-motion-probes/a0d7e3ae4d644d00a1e2f8b366fc10ca;
captures logs/fighter-window-runs/5a368fc51dd8430a8b29038da86973c9/captures.
The 1A8180 adapter preserves all four owned cores' WPAR choices2,2,2,2.
Mixed native fixtures also retain retail-created profile overrides, ignore
inactive slots and reject invalid choices before publishing the mask.
This proves inherited choice preservation, not authored Blazin playback.

Dedicated fighter-cinematic events produced all16 requested captures.
Reviewed entrance montage and winner frames show the synthetic arm/rig
exercise and the beta winning body. Selection events precede presentation:
the first intro captures still show the venue; later intro captures can show
the preceding participant. Do not label each screenshot by its load event.
The independent named live sampler confirms evaluated FI00000..FI00003 for
their four cores, and FV00003/core259 at phase3. The sampler report is in the
cache; visual capture timing still needs refinement for individual sequences.

The typed creator reader accepts bounded quaternion JSON, PCM16 WAV, action
choices, AI tendencies and simple cinematic templates;10focused tests pass.
SODB now accepts internally allocated character_cores before indexes/windows
and receipt generation;28SODB/reader checks pass. Partial cinematic authoring
can clone the other verified category unchanged;35cinematic/resolver checks
pass. BehaviorPlan and compile_inputs/write_preview/probe integration are
being implemented and are not yet accepted: all existing gates remain false.
An AI-only ordinary-manifest compiler probe is currently running.

Inherited AI needs an additional formatting correction. D6EE0(output,input)
constructs profiles before C9110 consumes them. Only when separate configured
identity V=input+200[slot] is zero does it use core K=input+40[slot] and format
char(K+1). A post-return adapter maps admitted owned K to its verified donor
for that fallback only; nonzero V (including chaXXXXX modes), unoccupied slots,
input bytes and guest registers remain untouched. Explicit FIA1 overrides
still win in C9110.64focused motion/cinematic native checks pass; relift/build
is running. Native inherited-profile acceptance remains pending.

Audit found separate open-ended setup+A8>=87 cinematic/presentation branches
in87AF0,87E20,89F20,8A300,8B440. Setup+A8 is one-based core, so owned cores do
enter these branches. Their original HERO/variant and sequence-state behavior
must be considered beyond the explicit FIC1 lookup. No second WPAR overwrite
was found. Broad temporary donor substitution is not adopted:8B440 has virtual
callbacks and the shared setup would expose substituted identity. See the
Blazin registration report for exact sites and remaining investigation.

M1/M2 remain incomplete. Remaining work includes authored Blazin registration,
ordinary-manifest integration/native acceptance, these setup assumptions and
the owner's native-portrait versus new3D-preview clarification. M3 has not begun.

### Owner preview decision — 2026-11-05

D-new: the owner chose custom2D portraits in the native fighter selector,
with3D models verified in entrances and combat. A new live3D selector preview
is not part of M1. This closes the earlier preview clarification; the milestone
table in docs/fighter-mod-support.md now uses the approved acceptance wording.
Existing entrance/combat geometry and portrait evidence applies to that scope.
Final integrated checks and M2 work are still pending; M3 has not started.

### 2026-11-05 ordinary behavior and inherited AI acceptance

The ordinary manifest coordinator now composes motion cores, authored animation
banks, voices, AI and intro/victory resources together. Each added fighter owns
a core; resources remain independently shareable. Typed JSON/WAV sources,
shared input/output budgets, exact artifact receipts and immutable cache
verification apply. General launcher activation remains gated. See
fighter-behavior-definitions-2026-11-05.md for creator contracts.

The earlier D6EE0 note was incomplete: the normal producer stores
V=K+1+1000*signed_variant, so ordinary inherited AI also needs the V=K+1 case.
The adapter now maps V=0 and V=K+1 to the verified donor, preserves other
variants and native formatting rules, and checks after C9110 that neither
inherited nor authored owned profiles silently fell back.67 focused native
tests pass; relift/build passed. Logs:
fighter-inherited-ai-identity-native-unit-nov05.txt,
fighter-inherited-ai-identity-relift-nov05.txt,
fighter-inherited-ai-identity-build-nov05.txt.

Native094636 uses two ordinary manifests with two authored and two inherited
AI profiles, four owned cores141..144. All four profiles were retained:
authored fma12cd81a9997efe476d4b8098/fma82c220697db1328958146c91 and
inherited char0005. PASS5 combat assertions and four menu identities;
210 frame reports102/120/121, zero five native fault categories, one
byte-identically restored save generation. No result assertion was requested.
Driver fighter-ordinary-ai-inheritance-retest-native.txt;
run-20261105-094636.log.err. Captures:
logs/fighter-window-runs/9fa5c84446114f29bbb8ef317fd627f1/captures.

Full authored behavior manifests have also compiled successfully using the
reproducible scripts/fighter-behavior-fixture.py creator-data fixture. Their
native combined acceptance is pending. Stock quick regression is running
for the current foundation. The new four-phase Blazin activation compiler
passes15 combined cinematic/compiler tests and a local original-data probe;
native registration and ordinary admission are not yet implemented. These
activation shots are distinct from the paired combat Blazin move resources.
M1/M2 are not formally complete; no M3 or public work has begun.

### 2026-11-05 stock regression and Blazin ownership counterexample

Stock regression PASS5/5,9minutes:1707passed/27skipped/1deselected, three
unchanged goldens,120seconds of stock combat with120median/110minimum
presents per2seconds. Logs fighter-ordinary-behavior-quick-regression-nov05.txt
and regress-20261105-100911.txt. This precedes the next activation adapter.

The four-phase FBZ1 adapter passed60 focused Python/native tests and built
successfully (fighter-blazin-native-unit-nov05.txt,
fighter-blazin-activation-build-nov05.txt). Ordinary full authored manifests
compile through the normal reader; archive receipts are chained and both
binding tables hash the same final v2ta resource. Native101354 is running
two packs/four owned fighters, independently authored animation/moveset,
voice, AI, intro/victory and activation resources. All four intro poses were
positively evaluated and all four authored AI profiles retained.

**Activation ownership failed live acceptance.** At preload, native87AF0
constructs all10 shared activation descriptors with slot0. The current
adapter consequently selects core141's B00000..B00003 once. The named live
sampler later catches slot2/core143 and slot3/core144 evaluating those same
resources, rather than their own. Four-phase playback works, but this is
not correct per-fighter routing. The earlier request-owner inference applied
to intro/victory, not this shared activation cache. Repair must distinguish
preload ownership from87E20's actual playback participant. No M2 acceptance
is claimed. Exact run:run-20261105-101354.log.err; driver
fighter-ordinary-full-blazin-native.txt; sampler
fighter-ordinary-full-blazin-live-proof.txt; cache
logs/fighter-native-preview/f965a3d343aca78204614be0143fe1457384a66bdc04fb7d93796e94d0cb9305.

Paired combat execution is separately located in1D3800: the selected subject's
F50/BB8 choice produces10709+2*choice at1D3B72, passed to1A85A0 at1D3BA0;
the linked counterpart receives the adjacent ordinal at1D3BAA. The new typed
BlazinPairs compiler appends independent subject/counterpart banks and MNL
entries while retaining original bytes and donor WAZA behavior.7invented
fixtures pass; the original-data probe produces four pairs at external
ordinals873,875,877,879,172total names,6026888bytes. Logs
fighter-blazin-pairs-unit-nov05.txt and fighter-blazin-pairs-probe.txt.
This compiler has no native registration or ordinary source admission yet.

### 2026-11-05 full ordinary run result and cache correction

Native101354 finished PASS8combat/result assertions,348frame reports108/120/121,
zero five native fault categories, four menu identities and one byte-identical
save restoration. All four authored intros and winner FV00003/core144 were
positively evaluated. Captures are under
logs/fighter-window-runs/4fb36698b55d4ebb878be0cea48d346e/captures.
This does not erase the observed activation ownership failure. The complete
sampler evidence is preserved as fighter-ordinary-full-blazin-live-proof-101354.json.

The cache fix reserves40 additional native descriptors/requests, ten per
participant, without changing the native logical load-loop count. It constructs
and loads each independently, remaps88DD0 using actual playback owner2D844,
and extends the cleanup count only for89310's native destructor loop. Shared
retail activation descriptors remain untouched.87AF0 labels only the private
groups.88FF0 is void-like; it cannot gate readiness by returningfalse. Instead
the state6/89B30 dispatcher waits until private groups are ready;8BE60 retries
it each tick without consuming the pending activation.37focused native tests
pass for allocation, delayed readiness, full-core selection, unchanged guest
registers, bounded writes and cleanup. Relift/build is running; native retest
is pending. The sampler now treats evaluated wrong-owner resources as failure.

With the preview decision closed, the two ordinary appearance packs' prior
human/CPU/four-controller acceptance, geometry/skin validation, entrance/combat
evidence and current stock regression meet M1's local Windows scope. M1 is
marked complete with explicit unperformed macOS/Deck smoke qualification.
M2 is not complete, and M3 remains unstarted.

### 2026-11-05 private activation cache native acceptance

Relift/build PASS: fighter-blazin-private-cache-relift-nov05.txt and
fighter-blazin-private-cache-build-nov05.txt; backup20261105-103250.
Native103546 PASS8combat/result assertions,349frame reports100/120/121,
zero five fault categories and one byte-identical save generation. All four
menu identities pass. Driver fighter-private-blazin-cache-native.txt;
captures logs/fighter-window-runs/bbf1bc1c27784638ae675fe71226aeea/captures.

The completed read-only sampler verifies17evaluated sequences with zero
ownership mismatches: four intros, four Blazin phases each for cores142/143/144,
and core144's winning FV00003. This directly resolves the preceding shared-cache
counterexample. Evidence fighter-private-blazin-cache-live-proof.json/.txt.
Human core141's activation was not observed; scripted right-stick gestures
alone did not establish it. Positive human activation remains a final check.
The native fixture now tests two different resources/owners and verifies the
original shared descriptors remain untouched.

Stock quick regression is running for this cache batch; unit phase already
PASS1735/27skipped/1deselected. Ordinary Blazin sources now also accept optional
paired finisher tracks under retained donor choices.24 focused composition/
reader/pair checks pass. The two full finisher manifests compile successfully
to cache8997f9352a25eac6f400bf8f30601ef8fba557e7b960a7648b7ce919e13eafe0
(fighter-behavior-finisher-compile-nov05.txt). **Do not launch that manifest
yet:** native FBP1/provider/selection adapters are not implemented. Normal
activation remains gated; M2 and M3 status is unchanged.

Stock quick regression for the private-cache batch PASS5/5 in9minutes:
fighter-private-blazin-cache-quick-regression-nov05.txt and
regress-20261105-105726.txt.1735passed/27skipped/1deselected; three unchanged
goldens;120seconds of stock combat,120median/105minimum presents per2seconds.
Source publication check720files/0failures; no toolkit change or game assets.
This is the local commit boundary before native paired-finisher work.

### 2026-11-05 native paired-finisher candidate

Saved the preceding accepted batch locally as da3b1ff. No publication.
The FBP1 adapter now owns an expanded byte mask/name pool, validates loaded
provider keys and skeletal record links, and remaps the two verified paired
calls using the subject's full core. Native teardown precedes metadata release.
An integer-overflow receipt case was corrected before testing.63 focused
native finisher/cinematic checks pass (fighter-finishers-native-unit-nov05.txt).
Relift/build pass (fighter-finishers-relift-nov05.txt and
fighter-finishers-build-nov05.txt), backup20261105-111032.

Native111321 is running two ordinary full-finisher packs/four fighters.
Cache553d53bb4cff3a98f77e88ccb66cd733ddf1579cb97de9b14a1be71a0a578fe3,
driver fighter-finishers-native.txt. The read-only sampler now attributes
subject/counterpart poses by indexed name, compiled quaternion descriptor,
actual actor ordinal and the subject's core. No native result is claimed yet.
The harness-only ready-meter control primes native momentum once per fighter;
positive controller-triggered activation still must be observed. M2 is pending;
M3 remains unstarted.

### 2026-11-05 paired playback passed; match result timeout retained

Native111321 completed its700-second window with349 frame reports101/120/121,
zero five native fault categories and byte-identical save restoration. All four
native menu identities and one isolated save generation verified. The completed
sampler (fighter-finishers-live-proof.json) has28 positively evaluated resources
and zero ownership mismatches: four intros, all16 activation phases including
human core141, and both roles of two independent cross-pack paired finishers
across several opponents. Capture folder062858b8a06c4bde9a678b58851f369f.

The run **failed** the decisive-result/eliminations/results-screen assertions:
two CPU fighters were still fighting at timeout. It is not counted as a full
acceptance pass. The initial combat input stopped most face-button actions
after112seconds. A second900-second run retains continuous face-button input
and earlier right-stick gestures, without artificially priming momentum.
Driver fighter-finishers-result-retest.txt; source/build unchanged. M2 completion
still awaits the result gate and final stock regression.

### 2026-11-05 separate finisher parameter domain corrected

The result timeout exposed a concrete missing adapter, not merely insufficient
combat time. Native1A85A0 sets actor+88/+8C to the new external animation ordinal,
then1A8641 indexes the separate873-row FZUI table at3B8634 with stride39. New
ordinals873+ therefore read beyond the original parameter table before1A38B0
decodes timing/reaction fields into actor+2BC. State34's paired-victim recovery
uses those fields. Correct visible poses alone did not establish valid gameplay.

Stopped native112733 deliberately after discovering this access. It had323
frame reports108/120/121 and zero five native fault categories; the harness
reports unexpected exit4294967295, as expected for the deliberate stop, and
still verifies byte-identical save restoration. It is **not** an acceptance pass.
Its sampler adds observed P0002 attacker/opponent ownership, but neither this
run nor111321 accepts paired-move behavior. Both are retained counterexamples.

The correction maps each admitted external ordinal to its complete inherited
39-byte FZUI row at the sole verified decoder call1A867E, keeping actor animation
IDs and diagnostic names independent. It validates table dimensions, the computed
source pointer, active token and both actor ordinal fields before substitution.
Shared animation bindings must also agree on inherited behavior. No global native
table is resized or temporarily rebound. Bounded source audit found no other
direct retrieval of this FZUI base/stride; other+8C uses feed the name adapter.
66 focused checks pass (fighter-finishers-parameters-unit-nov05.txt). Relift/build
is running. M2 remains incomplete until corrected native result acceptance.

### 2026-11-05 corrected parameter routing; results transition still pending

Final focused checks68pass. Relift/build passed with backup20261105-114239
(fighter-finishers-parameters-relift-nov05.txt and
fighter-finishers-parameters-build-nov05.txt). Native114454 positively routes
875/876,877/878 and879/880 through inherited FZUI rows713/714. A live state
sample after a paired move shows the former participants using ordinary
motions2042/2043 again. The sampler records27 evaluated resources with zero
ownership mismatches (fighter-finishers-parameters-live-proof.json).

The match reaches a decisive winner and match_over at native clock6:6, then
phase3. However it never requests victory FV00003 or the results screen by
the700-second cutoff. Driver fighter-finishers-parameters-native.txt fails
only combat.results_screen;348frame reports108/120/121, zero five fault
categories, byte-identical save restoration and one isolated save generation.
This remains a failed full acceptance run. Capture folder
2d2ccec3772b412e9e6f9815f0ea6b4f. Do not mark M2 complete.

Native120229 now traces the scheduler read-only at verified manager349760,
including2D820 state, pending match flags, owner/selection, setup flags and
the40 private readiness words. Its controller timing separates the right-stick
gesture from attack edges. No code or pack bytes changed for this run.
Driver fighter-postmatch-native.txt; sampler fighter-postmatch-live-proof.json.
M3 remains unstarted; final stock regression awaits this result boundary.

### 2026-11-05 post-match evidence and camera semantics

Native120229 confirms human core141's four activation phases on the corrected
FZUI build and reaches FV00003 plus all four Game.GetMatchSummary calls. The
read-only trace records manager states through13, all40 private request words
ready, and final match/snapshot flags14. However this run is **not a pass**:
the results screen produces eight unresolved calls to data address2BF410 and
two non-code call reports. First faults are122315/122334 in
run-20261105-120229.log.err. Save restoration is byte-identical,349frame reports
100/120/121. Capture folderad73cd6256584bf28957ffdc489e941b.

Bounded audit identifies the immediate faults as APT opcode dispatch: opcode50
releases a null stack value, then opcodeCC indexes beyond valid handlers to the
literal substr string. Do not seed2BF410 as code. The adjacent thumb-control
binding uses profile indices, not fighter IDs; its appearance beside the faults
does not establish causation. This UI failure remains under investigation.

A separate source-proven semantic issue was corrected:1A3ECF publishes the
motion name used by AC100's camera-script lookup. Newly owned Pnnnn_A/B labels
have no inherited script entry. A missing-script branch can leave a previous
zero time multiplier unrestored, which is consistent with114454's frozen ramp,
but that exact live state was not captured.1A8150 now supplies the donor semantic
name for this snapshot caller while preserving owned names for diagnostic
callers and owned animation bank selection.68 focused tests pass; rebuild is
running (fighter-finisher-camera-unit/relift/build-nov05.txt). Native proof and
the UI-results failure are still required before M2 acceptance.

### 2026-11-05 results action relocation defect isolated

Camera candidate133930 reaches victory and all four summary callbacks, with32
positively evaluated owned resources and zero ownership mismatches. The complete
700-second run still fails: eight unresolved calls and two non-code reports;
349 frame reports103/120/120, byte-identical save restoration and one isolated
save generation. Driver fighter-finisher-camera-native.txt, sampler
fighter-finisher-camera-live-proof.json, preserved captures
7da26a54b1e54fa39814da3dab4eb50d. This remains a failed acceptance run.

The first fault precedes Game.GetMatchSummary, excluding that callback's returned
statistics as its initiating cause. The fault stack contains action startA44FC;
the original XBE there begins50/51/68/CC, explaining the observed APT opcodes.
The composed four-player result movie shares one generated Action record between
frames0 and89. Native17DD70@17DE55 adds the movie base to that record's instruction
pointer on every frame occurrence, without a visited guard. Its156110/155AD0
bytecode relocation also adds the base to string operands. Thus both the record
and its bytecode must be independently owned, even when the actions are identical.
The observed low address is consistent with double addition wrapping a high guest
movie base; that exact live base was not sampled, so retain the qualification.

The compiler now emits a fresh Action and record per affected frame. Three new
relocation-contract tests reject the old compiler for2/3/4-player layouts and
pass the corrected compiler. Focused results/menu/grid suite25pass. A source
census found no other newly appended mutable aliases in those three compilers.
No native interpreter bypass or toolkit change is involved. A fresh full match
uses the same native binary and behavior resources with the corrected UI bytes
(fighter-finisher-results-owned-native.txt). M2 remains pending; M3 unstarted.

### 2026-11-05 corrected paired-finisher/results native acceptance

Native135539 PASS: two ordinary full-finisher packs, four participants (one
human/three CPUs), logical selections103/105/104/106. All eight combat/result
assertions pass, including movement, attacks, damage, eliminations, decisive
winner and native summary. The result occurs at step15389/native clock5:07,
winner slot3; FV00003 plays and all four summary callbacks execute. Full
700-second window:349 frame reports103/120/121, zero crashes/watchdogs/debug-layer
errors/truncated batches/unresolved calls and no non-code reports. Saves restore
byte-identically; one isolated save generation verified. Driver:
fighter-finisher-results-owned-native.txt.

Read-only proof fighter-finisher-results-owned-live-proof.json has32 evaluated
observations and zero ownership mismatches: four intros, all16 owned activation
phases (human141 and CPUs142/143/144), both roles of three independent paired
resources across opponents, and victory FV00003. It records70 distinct manager
snapshots through state13. Paired parameter routing retains FZUI713/714 while
animation ordinals875..880 remain owned. This is positive playback/behavior
evidence; it does not claim a human-triggered subject finisher was observed.

Preserved captures are under
logs/fighter-window-runs/4ab8c0e9fd064761a2ad7e874bb4f65d/captures.
The1.1s/2.1s summary captures were visually checked: all four custom portraits
and bounded labels are correct; scores populate normally. The earlier APT
faults do not recur with independently owned per-frame actions. Earlier failed
runs remain retained above. Final stock quick regression is running in
fighter-finishers-final-quick-regression-nov05.txt; M2 completion awaits its
verdict. Toolkit pin remains d569ca10811cef67ec4e9fa2173088c2f9fd0580.

Stock quick regression PASS5/5 in9minutes, regress-20261105-141654.txt:
1769passed/27skipped/1slow deselected, all three stock golden screens unchanged,
120seconds of stock fight with120median/113minimum presents per2seconds. No
toolkit change. Results relocation fix saved locally as f6d2364, no push.

One targeted follow-up closes the human subject-finisher observation gap. Native
grapple input uses A;1D1A90 requires active Blazin (+93E bit2) and a fresh right
stick edge (+43C bit20000) before1D2C30/1D0F80 select action31..34/38..41. The
earlier script began grapple attempts too late relative to activation. The new
script advances approach and A to25/26seconds with staggered repeated right-stick
gestures. No engine code, fixture resource or meter policy changes. Driver:
fighter-finisher-human-native.txt. M3 remains unstarted.

Targeted trial141757 is **not a pass**. It did not observe human activation or
a human subject finisher, and its harness p.kill()/wait hit the15-second process
exit timeout. The native log has199 frame reports103/120/121 and no observed
native fault signatures; the process subsequently exited. The finally-path
completed save restoration: an independent comparison against the retained
guard payload verified the whole disposable save tree byte-identical, with a
successful guard marker and no unresolved state marker. One isolated save
generation was verified. No original profile was exposed to this run.

The grapple attempts may have preempted the activation opportunity. A retry
tests that timing hypothesis with inputs at35/36seconds and timed combat captures; the attempted
finisher-log screenshot anchor was not an emitted native anchor event. Actual
playback ownership remains established by the read-only sampler, not by preload
name logs. Driver fighter-finisher-human-staggered-native.txt. No source or
resource changes since the accepted stock regression.

Staggered trial142809 also failed to observe human activation/subject playback
and hit the15-second process-reaping timeout. The process exited, and the
complete disposable save tree again independently matched its guard payload;
the success marker was present with no unresolved guard. These additional
input trials are not accepted gameplay runs, regardless of the earlier full
match pass. No cause for the slow process exit is established.

The next control adds observation-only fighter-blazin-playback:slot:phase events
at88DD0's verified private-cache selection boundary. They require
RECOMP_TEST_OBSERVATIONS=1, preserve the selected descriptor index, and distinguish
playback selection from asynchronous resource-preload notices. Native fixture
checks prove the event is absent without observation mode and records the right
participant/phase across all ten descriptor variants.68 focused checks pass;
incremental build passes (fighter-playback-anchor-unit/build-nov05.txt).

The event-driven run waits for the human's fourth activation shot before approach,
grapple and fresh right-stick gestures. It uses the same pack resources and meter
policy. The read-only sampler will finish before the native shutdown deadline to
remove that possible observer interaction; this is a control, not an established
explanation for the prior timeouts. Driver fighter-finisher-human-playback-native.txt.

Event-driven trial144030 positively evaluates all four human activation phases
and fires the final-shot input anchor. Captures6/12/18seconds after that event
show the human Blazin state active and grapple scoring. Human subject-finisher
playback remains unobserved. Its shutdown still exceeds the15-second harness
wait even though the replacement read-only sampler completed beforehand, so
the timeout is not explained by that observer alone. The process exited and
the complete disposable save tree independently matched its guard payload.
This run remains failed; the forced-shutdown delay is an open testing issue.

The harness's non-direction inputs hold for0.3seconds. The attempted A2.05 then
right-stick2.33 sequence overlapped by0.02seconds, repeated every second. A new
control uses A every3seconds and the stick0.78seconds later. Native1D2884 shows
the required0x100 flag is accepted grapple contact, not a direct strong-grapple
modifier; no unproven trigger requirement is introduced. The follow-up runs
the full700-second match/result window rather than stopping mid-fight, with
the same final native build and ordinary packs. Driver:
fighter-finisher-human-grapple-native.txt. Final-build stock regression remains
required after native acceptance; earlier141654 stock pass predates only the
observation-gated playback event.


The input audit corrected the earlier caller attribution: the intended subject
handler1D3800 uses1D0E80 at1D396D, not1D1A90 (whose callers are in1D41D0).
Blazin must be active when grapple startup copies +93E bit2 into +91A bit1.
Normal accepted contact supplies +91A0x100; after ten simulation updates,
subject state31/substate2 copies current held/rising inputs into +438/+43C.
A right-stick edge arriving before that state is not buffered. The selection
gates require +91A0x101, no0x1000 and no +9220x10 diversion; they do not
explicitly require a strong modifier, stunned target or left-stick direction.
A scratch controller-only probe will read those fields and send ordinary live
pad input when the native grapple window opens. It never writes game memory.
These timing tests remain local evidence collection, not package behavior.


Native145033 completes successfully: all8 combat/result assertions, menu keys
103/105/104/106, zero crash/watchdog/debug-layer/truncated/unresolved reports,
byte-identical complete save restoration and one isolated save generation.
348 frame reports span44minimum/120median/121maximum presents per2seconds;
the low sample is retained, not hidden behind the median. The read-only sampler
finishes before shutdown with33 observations, zero ownership mismatches and
zero unreadable samples, including all activation phases and winner FV00003.
Human subject-finisher playback remains unobserved. Captures are preserved in
logs/fighter-window-runs/ca0829b43a8342fda5fe749090bd1e84/captures. The process
exits normally under the harness; the earlier forced mid-match shutdown timeout
is still an unresolved testing issue rather than an established gameplay fault.


Controller trial150415 is invalid: ControllerSetup submitted selection60 for
P1 (stock core80), while the three CPU selections were correct. Both the actor
and participant table showed80; this was not transient donor borrowing. The
controller guard refused input, correctly. The trial was intentionally stopped
after the owned observer; full save restoration and one isolated generation
were verified. Its native log additionally contains one startup non-code call
to0x81000344 atline1163, before combat. No other crash/watchdog/unresolved
faults were reported;146 frame samples had5minimum/119median/120maximum.
It is not acceptance evidence. The retry delays initial P1 browsing to10seconds
with0.8-second spacing and confirms at32seconds; other selections are unchanged.
The scratch controller watches the stable participant identity and emits A only
while Blazin is active, then waits for the verified grapple state before rup.
No runtime or package changes accompany this control.


The150415 startup non-code callback is traced to27EC5D/27EC6C: it invokes
request+8 with request and request+C after the completion-queue path marks
request+22 bit8. The log lacks the actual request pointer; the printed ECX is
the callback value, not proof of the request address. The same81000344 target
and27EC6E return are documented in rc-v0.13.0-macos.md line69, so this predates
the finisher implementation. Its cause remains unresolved; historical presence
does not make that failed run clean. A useful future trace would capture the
request argument at27EC5D and the writer of its callback field.


Trial151235 reaches all four summaries and restores saves byte-identically,
with correct103/105/104/106 selections and zero native fault signatures. It is
still not an accepted combat run: human movement/attack/damage assertions fail.
The state observer sees human grapple-start state30, then a CPU-owned paired
attack on the human; no subject state31/substate2 is observed during Blazin.
The sampler ends before shutdown with31 observations, zero mismatches and zero
unreadable samples.352 frame reports have16minimum/120median/120maximum.
Capture root: logs/fighter-window-runs/ae009c1a034546d084a0bde3a569ed6a/captures.

The focused follow-up uses ordinary behavior-human-finisher.json variants: only
Alpha first references an authored Blazin sequence, while the other fighters
inherit retail Blazin. The unchanged harness meter control therefore readies
only core141 (confirmed single-row FBZ1 receipt), leaving CPUs to earn momentum
normally. Appearance, moveset, voice, AI, intro and victory definitions remain.
The controller takes one short approach step before grappling and waits for
actual native contact readiness before a fresh stick gesture. The all-authored
four-participant acceptance remains135539/145033; this complementary case
tests authored-human versus inherited-CPU behavior. No engine code or gameplay
rules change. Driver fighter-finisher-human-focus-native.txt; cache992e0a01.


Focused run152535 positively closes the human-subject playback gap. After an
ordinary approach and grapple, the read-only controller observes state31/2,
flags0x101 and neutral input, then sends rup200ms. Native execution enters
state33 with owned ordinal873. The independent sampler verifies evaluated
P0000_A on human core141 and P0000_B on the other pack's core144, both owned
by subject141, with matching indexed names and compiled descriptor hashes.
Controller output: fighter-human-focus-controller.txt; sampler stream:
fighter-finisher-human-focus-live-proof.txt. The controller then stops sending
input. This is scripted ordinary-controller evidence, not a manual playtest.
Only the running match/save checks, final stock quick regression, documentation
and local source commit remain; no additional exploratory tests or M3 work.


## Final local handoff — 2026-11-05

The owner explicitly requested skipping the queued routine regression and
handing over the finished features for continued M3 development. That queued
process was canceled before regress.py started; no final-regression log exists.
The read-only observer was stopped, then the owned game received normal window
close and exited0. The harness reports unexpected exit because the scheduled
720-second test was deliberately shortened; this is not a full-match pass.
Complete save restoration is byte-identical, with one isolated generation.
The focused native log has209 frame reports98minimum/120median/121maximum and
zero crash/watchdog/debug-layer/truncated/unresolved/non-code reports.
Its preserved stream contains10 evaluated observations and zero ownership
mismatches, including both human-owned paired roles.

Evidence: fighter-finisher-human-focus-native.txt,
run-20261105-152535.log.err, fighter-human-focus-controller.txt,
fighter-finisher-human-focus-live-proof.txt and the explicitly interrupted
stream summary fighter-finisher-human-focus-stream-summary.json. Captures:
logs/fighter-window-runs/1ebeac15874e4f72bb61b999a42126e6/captures.
The accepted full-match results remain135539 and145033; the stock quick pass
remains regress-20261105-141654.txt. No thresholds or golden images changed.
No additional exploratory tests, M3 implementation, push or PR were performed.
