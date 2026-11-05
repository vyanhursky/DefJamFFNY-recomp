# Fighter Mod Support: M1/M2 implementation checkpoint

Local branch `research/custom-fighter-mods`, target v0.15.0. The owner authorized
M1 and M2, including computer testing. Neither milestone is complete; review
the results and unresolved decisions before M3. No push or public PR.

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
