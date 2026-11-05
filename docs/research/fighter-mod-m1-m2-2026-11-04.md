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
