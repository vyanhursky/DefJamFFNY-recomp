# M5: creator workflow and faithful conversion

Target v0.15.0, local only. **M5 remains in progress.** The owner explicitly
chose to include general adapter R&D before closing the milestone. No public
PR/push, no donor-substitution conversion and no opaque native archive admission.

## Creator implementation and validation

Modding Tools owns offline `fighter catalog/new/validate/package/extract`.
Runtime `scripts/fighter-contract.py` exposes `fighter-authoring-api-1`, shares
inventory/native compilation/menu composition, and uses only temporary caches.
The packager includes exactly the validated bytes, checks hashes again, emits
stable ZIP metadata, verifies CRCs and exclusively creates the requested output.
Starter and extraction outputs also refuse overwrite. Full source documents are
not installed automatically; normal launcher validation remains authoritative.

Runtime inventory now matches ZIP admission's file population/extension and
case-collision rules. An installed-wheel single-fighter check exposed an older
SODB builder bug: pack IDs sorting after `runtime-bank` collided with indexed
bank selection IDs100–103. Logical templates and indexed banks now check
uniqueness in their own domains, both excluding retail identities. Stable IDs
and ledger schema are unchanged. Tests cover both sort orders and reject
same-domain duplicates.

Evidence (private logs, no game data in source):

- `logs/fighter-m5-contract-unit.txt`:16 focused Python tests passed, including
  native template composition, name-order bug, mutation rejection and manager
  transactions. Native C probe cases excluded from this focused authoring run.
- Tools twelve synthetic creator cases passed: deterministic ZIP contents,
  post-validation mutation, failure receipts, exclusive output and exact-member
  extraction safety.
- Tools wheel built and installed into `logs/m5-wheel-env`; installed console
  entry point ran from outside the checkout, created `single-starter/solo`,
  compiled its native resources/menu and packaged it.
- Tools `logs/m5-starter.zip`: two-fighter starter, SHA-256
  `1968380637cccae7ac406fd91558ffbb34d33f1a09919b88d39777ae503bc16f`.
- Tools `logs/m5-single.zip`: one-fighter starter, SHA-256
  `8a007eaee11b2bb619942fe1d586a51e94e4e02808de0e1d6aa267f67e7fbd55`.
- Actual manager imported both, enabled all three fighters together, then
  disabled both in `logs/fighter-m5-authoring-install`; no save folder created.
  `logs/fighter-m5-authoring-install.json` records host acceptance.
- `logs/fighter-m5-authored-contract.json`: full native/menu compilation accepted
  both existing M4 authored appearance/behavior packs, four fighters combined.
  This was not another native game run. Prior M1–M4 evidence remains separate.

Beginner guide: `DefJam-Modding-Tools/docs/fighter-modding-guide.md`, every
numbered section starts with plain-language context before technical details.
It covers all components, tools, constraints, stable keys, conflict resolution,
packaging and testing, with game-free single/multiple fighter examples. Updated
[runtime reference](../fighter-mod-authoring.md) replaces stale prototype claims.

## Direct Vendetta audit

Input SHA-256 `42645b4ad0d4b9bb502dec3db88095b7a21f061a20ad9091387b3272137f415f`.
Read-only extracted source under the private `defjam-fighter-data` workspace.
No reference-project code was copied. Own format readers inspect actual data.

- SOD has121 characters vs75 retail:46 additions, not44 advertised. Existing
  75 character records and native bindings are unchanged in this comparison.
  This says nothing about other shared tables without separate comparison.
- All 46 appearances now compile through the ordinary adapter, including their
  distinct facial palette values. `logs/fighter-m5-vendetta-audit.json` reports
  46/46 accepted and zero retail SOD edits. No complete pack is emitted by this
  audit. A subsequent combined 46-fighter appearance pack passes the shared
  native/menu contract (`fighter-m5-appearance-roster-contract.json`, cache
  `66dd6e09972bea2d66f643962d268e54376d45dc7c731183b203965c57a2e181`).
  This pack explicitly inherits retail behavior: it is not the full conversion.
- `setup/fighter_face.py` bounds sample frames, channel destinations against the
  matched body rig, local relocations, finite values, unit quaternions and
  nonoverlapping spans. It rebuilds typed values in a verified retail envelope;
  source control words, padding, extra bytes and relocations are not copied.
  All 46 typed rebuilds preserve source active values. Fifteen synthetic tests
  cover bounds, malformed data and rebuilding (`fighter-m5-face-unit.txt`).
- Source faces have capacities 13/15. A census of 553 retail banks found 35,018
  face-context type25 records, with maximum sample indices 12/14. Source and
  donor combat face joins each cover 10,406 records without rejection. These
  are context-specific bounds, not the type25 time-key count. Native FDB40
  supplies no sample/destination bounds checks. Logs:
  `fighter-m5-retail-face-contexts.json`, `fighter-m5-face-joins.json`.
- Corrected trace: VA 28AD7C is `%s_p`, not `%s_f`. The 59D50 -> 24430 ->
  22010 -> 22150 chain is the cinematic face-palette registration. The
  17A40 path separately evaluates `%s_f` with the per-object bank at +9E00;
  `%s_h` uses the shared bank at global 33AB30. 980B0 loads the per-object
  PosePaletteBank from manager11. The traced A288 selection uses v2cp_1
  (created-fighter components), so it does not prove the normal appearance
  bridge. The normal face owner loads `%s_F.o` at 97710; 97AA0 resolves its
  handle and 215E0 registers `PosePaletteBank` at face-owner+430. Its destructor
  97BF0 releases that wrapper through21670. The normal-fighter bridge is now
  established:9DC51 explicitly calls97BD0 with owner=visual+20, so owner+430
  is exactly visual+450.9DF40 stores that wrapper in paired context+20;
  9FB30/245B0 dereference it and22010/22150 pass the root to type25 evaluation.
  CModel+2C0/+2C4/+2C8 are transform floats, not a face-bank pointer; the
  previously proposed24BE0 bridge was incorrect. The created-fighter alternate
  visual+A6B0 remains outside this normal-appearance proof.
  22C20 returns the pose pointer stored at context+0xC, not that field's address.
- `main_all.dat` has 177 core pairs vs 141. All 46 mappings resolve to retail
  donors. All 130 action rows per mapped core match: 5,980/5,980. A subsequent
  direct byte comparison establishes **all three unpacked ORD/ORL/MNL parts
  of all 46 combat banks exactly equal their mapped donor**, not just token or
  curve-type counts. Those ordinary combat animations can inherit faithfully.
- WPAR fields 88–91 are the four finisher choices. They select secondary WAZA
  rows 142+choice and paired motions. All 47 added choices 82–128 have WAZA
  and FZUI behavior identical to specific verified retail finisher templates.
  Their 94 subject/counterpart animation banks contain genuinely different
  skeletal and root-motion curves. Importing shared tables is unnecessary.
- General design: keep each selected WPAR slot's value equal to its retail
  behavior template (0–81), but bind independently owned animation by core and
  action-derived slot. This distinguishes two different pairs using the same
  template. FBP2 needs slot/template/owned ordinal; a new motion proof must
  permit exactly the four declared WPAR changes. Existing FMC2's byte equality
  cannot admit those edits. Do not merely raise the legacy choice limit or
  allocate global WAZA rows. The FMC3/FBP2 implementation is now present;
  focused compiled-C checks pass and native acceptance is in progress below.
- General ELF canonicalization preserves every section payload and relocation
  meaning while fixing exporter-dependent physical section order. Empty curve
  arrays may retain bounded local pointers. All 1,012 supplied cinematic and
  activation member files now pass envelope/index/curve-layout inspection
  (`fighter-m5-cinematic-audit.json`); this is not numerical/native acceptance.
- New type20/type21 vector decoders preserve float32 arithmetic, block resets,
  time lookup, interpolation and static channels. Actual unfiltered native
  evaluator oracles each pass 405 invented cases and 10,935 sampled times with
  zero byte differences. See [codec evidence](fighter-animation-vector-codec-2026-11-06.md).
  Existing type18 numerical decoder already has an independent oracle. These
  readers do not yet authorize arbitrary cinematic or paired-motion graphs.
- AI profiles match their mapped donors. The six supported portrait slots have
  coherent retail layouts; ancillary portrait art still needs accounting.
  The four-phase activation and camera/helper bindings need general adaptation.
- Voices use EA revision3/codec10 (ADPCM R2). The new typed adapter preserves
  their coded blocks instead of silently transcoding to PCM. Out-of-order HDR
  offsets are valid logical-entry layouts. Omitted Enviro614/626 and Taunts626
  still need explicit accounting. Voice626 Character metadata matches verified
  templates504/505/506/509; the earlier unresolved523 note was incorrect.

## Native facial component probe

Private pack `logs/fighter-m5-face-probe` uses original Briggs model, textures
and face, with explicitly inherited Bonecrusher behavior. It is a component
probe, **not the converted Vendetta fighter**. The shared contract compiles it.
Native log `logs/run-20261106-194958.log.err`: 240 seconds, 120 presentation
samples (min108, median/max 120 presents per two seconds), zero crash/watchdog/
debug-layer/unresolved-call signatures; complete test save restored identically.
Native selection and immutable identity checks pass for Briggs/Crack, and five
movement/attack/damage assertions pass. Captures show the custom geometry in
combat; they do not establish every facial expression or every cinematic.

Qualification: the command expected Doc but the scripted selector chose Crack;
independent verification used the observed Crack identity. The results-route
harness exits 1 because no match summary was reached within the bounded run.
This is partial component acceptance, not a full-match/results pass. Evidence:
`logs/fighter-m5-face-native-evidence.json`; capture directory
`logs/fighter-window-runs/152acb6daa5c4ad7a4a49069f6fee28b/captures`.

## Additional focused evidence

- `fighter-m5-compiler-unit.txt`: 137 focused format/compiler Python cases pass;
  the separate window run covers five additional Python cases. No broad stock
  regression. Eleven menu/compiler cases pass after the style-order fix.
- Combined validation exposed retail Bubba's primary style mask9/mask9. Native
  48270 jumps on its **first** matching bit to48294;4829E appends other enabled
  styles ascending. It does not append every primary bit before the fallback.
  `RetailCatalog.menu_record` now accepts multiple primary bits and picks the
  lowest intersection. Tests include mask25/primary24 -> [3,0,4], which detects
  the incorrect all-primary-bits interpretation.
- Creator source is committed locally as Tools9958362; shared runtime contract
  and SOD identity-domain fix as runtime138d915. No push/public PR.
- Tools audio preflight resolves 2,865 referenced entries in217 files.28 banks
  contain unreferenced physical gaps; logical HDR order is preserved and gaps
  are explicitly reported.2,539 streams have a partial final28-sample block.
  A normal FFmpeg invocation truncates that tail. Offline export rounds the
  decoder request to the full encoded block, then retains exactly the declared
  sample count. All 2,865 clips decode successfully, no resampling/downmixing,
  at the native24kHz default in
  `DefJam-Modding-Tools/logs/m5-audio-export-native-rate.json`. The earlier
  `m5-audio-export.json` used the decoder's incorrect48kHz default and is superseded.
- Native130C10 explicitly decodes a full28-sample tail then exposes only the
  remaining count. An isolated native-body oracle confirms31,944 samples and
  no output-guard violations for the first Character600 clip. Its float-based
  predictor differs from FFmpeg's integer PCM decoder (max44.925, RMS21.085 in
  signed16 sample units). PCM export is therefore a documented transcode, not
  bit-identical native decoding. Preserving the original bounded R2 payload is
  implemented by the bounded `fighter-voice-2` adapter. Its separate numerical
  and native acceptance evidence is recorded below.
  Oracle: `logs/fighter-r2-oracle/comparison.json`, body SHA256
  `b0bc2a322713fc53972214a6e9a0ab2350c024687d7e4da113c71e8a6342db3e`.

## Typed compressed voice adapter

`fighter-voice-2` retains the voice1 resource fields and adds an explicit
`format` to every audio descriptor: `wav-pcm16` or `ea-adpcm-r2`. Legacy voice1
packs remain unchanged. R2 is a narrow mono revision3/codec10 profile: bounded
packet/sample counts, four predictor indices or literal blocks, complete final
blocks, zero alignment padding, and known sectioned header properties only.
The compiler writes a fresh header and retains the coded blocks. No legacy HDR
metadata or executable payload enters through this adapter.

Native omitted-rate default is 24000, not FFmpeg's 48000. Header property 8C=36
selects the native software decoder; omitting it can select the hardware path.
Property 06=101 also stays explicit. An isolated original/canonical header oracle
compared all 237 parsed metadata bytes with zero differences. All 2,865 streams
retain 138,547,695 declared samples and 85,685 packets without changing coded
blocks (`logs/fighter-m5-r2-canonical-audit.json`). Focused PCM/R2/bank/package
checks plus scalar/timed-animation tests: 145 passed
(`logs/fighter-m5-adapters-final-unit.txt`). The final all-source check also
passes signed-count and header-section validation without changing coded blocks
(`logs/fighter-m5-r2-final-corpus.json`).

Synthetic R2 playback is positively identified in captured device audio:
`run-20261106-204610.log.err`, 170 seconds, 84 presentation reports, min 104 and
median/max 120 presents per two seconds, zero crash/watchdog/debug-layer/
unresolved-call signatures, restored-identical save, expected menu 100/17 and
five combat assertions. Custom voice 600, family 40962 resolved bank row 42. The
2-second literal-block chirp correlates 0.67086 at 130.6928 seconds with its known
waveform (`fighter-m5-r2-enabled-correlation.json`). This proves one native R2
playback route, not every event or a completed voice conversion.

Earlier one-fighter PCM and R2 runs were stable but did not identify their test
sound. Do not report those as playback passes. The successful run used a private
copy of earlier M4 Options; payload bytes 17/18 differ, but the native audit does
not establish that they mute speech. No user Options were changed. Loose-file
intro600 open failures are part of archive fallback and do not establish a
loader defect.

Voice metadata matching currently finds 84 exact banks among 129. The other 45
differ from a retail template only in the first family WORD: Character 0/1,
Taunts 16625/16626, Enviro 40962/40963. Native 135CB0 looks up the exact family/voice
pair; retrying another family comes from event alternatives at 138EDA, not an
automatic numeric fallback. A converter must preserve or explicitly account for
that distinction. It must not infer event family from the IP filename.

The original predictive clip probes (`run-20261106-205021.log.err` and
`run-20261106-205746.log.err`) passed menu/combat/save checks but had no observed
custom voice request and did not identify the clip confidently in their audio.
These are **inconclusive playback checks**, not evidence of a codec failure or
a predictive-clip acceptance pass. The isolated native predictive-decoder oracle
and synthetic literal-block device playback remain distinct evidence.

### Explicit category templates and original-line probe

`fighter-voice-3` supplies exactly three category banks, each with a verified
`template_voice`, bounded `family`, and typed sample overrides. Intro/extro remain
mandatory. Character allows0/1, Taunts16625/16626, Enviro40962/40963; a category
cannot borrow another category's metadata. The moveset event namespace still
must match. Voice1/2 keep their existing single-template contract. Missing
whole categories remain unsupported rather than silently filled with donor audio.

`logs/fighter-m5-voice3-bank-audit.json` checks all129 source banks/2,777 clips,
including the45 first-key differences. Rebuilt normalized event metadata matches
every source bank exactly. Original coded blocks are retained through the R2
adapter. This excludes the separate88 entrance/victory streams and does not
resolve missing source banks.

Native `run-20261106-213135.log.err`: full original voice600 category content
bound to a diagnostic Blaze-derived fighter;220seconds,109 frame reports
101/120/120, no crash/watchdog/unresolved-call/debug-layer failures, identical
save restoration, one verified profile generation, menu100/17 and five combat
assertions. Family1/voice600 positively resolves bank row1. Device audio matches
Character clip030 (also present as Enviro003) at160.356875seconds, normalized
correlation0.408 in an8kHz comparison (`fighter-m5-voice3-original-correlation.json`).
The next distinct candidate is0.167. This supports playback of one original line
amid mixed game sound; it is not all-events or whole-pack acceptance. The digest's
late-frame heuristic is explained by dense audio tracing between the final
two-second frame report and the deliberate220second cutoff, not an observed hang.

## Per-slot finisher adapter

`fighter-blazin-2` retains four activation shots and replaces choice-keyed pairs
with1–4 explicit slots0–3. Each selects a verified retail behavior0–81 and owns
subject/counterpart quaternion tracks. Omitted slots inherit. Version1 stays
supported; mixed generations expand its choice bindings to their selected slots.

FMC3 extends the existing independent action proof with four optional choice
words. The compiler and C validator reconstruct only WPAR fields88–91:
native offsetsD4/D8/DC/E0, packed payload bytes56–59 (bits448–479). Every other
WPAR/header bit and unselected action remains donor-equal. An early arithmetic
error in a read-only audit was caught by the native fixture before gameplay;
the corrected byte offsets are checked at both declared and neighboring bits.
FBP2 binds core/slot/template/owned ordinal. Runtime registration checks the
specific decoded actor slot; execution checks its action-derived slot again.
Slots sharing a template can therefore select distinct pairs without adding
global WAZA/FZUI rows. Parameter/camera identity remains the selected template.

Focused Python/native-C suite:164 passed in9.64seconds,
`logs/fighter-m5-slots-voice3-unit.txt`. C tests cover malformed proofs,
unrelated changes with recomputed hashes, same-template distinct slots, alternate
action31/38 families, unchanged slots, mutated runtime choice and lifetime.
The first four-fighter run (`run-20261106-214617.log.err`) **failed** during
match startup, after registering16 pairs/196 total provider slots and verifying
34 active motions. Invalid pointers surfaced in viewport update1A710 and
allocator29DE0; no cause is yet established.81 frame reports109/120/121,
byte-identical save restoration and one profile generation. The native table
allocations audited so far scale with count; do not invent a fixed32-motion
limit from this failure. The fixture's32 owned role banks total12,516,736bytes.
A short direct-start attempt did not reach match startup and provides no
comparison. Native acceptance remains open; source motion/root/helper graph
conversion is separately unfinished.

Subsequent tracing narrows the startup fault to texture loading. In
`run-20261106-220023.log.err`, a hardware write watch on the actual viewport
field8109D6B4 catches native swizzler2115D3 overwriting its valid81014200
pointer withFF602E15. The preceding watch on8124D264 watched a different object
and was inconclusive. In `run-20261106-220452.log.err`, an entry watch proves
the swizzler receives source00000010, destination81080190, width/height256.
The direct caller return2123BD is verified; deeper stack-scan entries are not
treated as live callers. The source is invalid, but its origin and destination
ownership still need tracing before assigning an allocation failure or a
swizzler defect. Both runs restore saves identically and fail before combat.
A shared-resource comparison is rejected before launch because the four
appearances have different verified rigs; that is correct admission behavior,
not gameplay evidence. A two-owned-slot-per-fighter comparison
(`run-20261106-221049.log.err`) reaches the match with8 paired bindings,
180 provider slots and18 active motions, no crash/watchdog,109 frame reports
101/120/121, all four menu identities and byte-identical save restoration.
It misses player attack/damage assertions at the220second cutoff; this is a
diagnostic comparison, not native finisher acceptance. It strengthens the
resource-footprint hypothesis without proving memory exhaustion.

`run-20261106-221501.log.err` traces the earlier failure. A valid texture
descriptor839A1EF0 reaches the conversion path; the allocation result retained
in EBX is zero at the next descriptor lookup (return1DF309). Static data flow
traces EBX directly to callback2F756C's return at1DF289. The game then copies
the header through zero, calls the swizzle path with a null source descriptor,
and obtains pixel pointer00000010. The destination's header is also empty.
Initializer1A920 registers297E0 for that allocator callback; it delegates
through295B0/1E9E70 to the native free-list allocator1E9AB0. This establishes
allocation failure upstream of the swizzler, not a texture swizzle arithmetic
defect. The cause of allocation rejection still needs pool evidence.
Boot allocates43,044KiB for the title arena at81000000; kernel live-byte
counters alone cannot report free space or fragmentation inside that arena.

The next guarded run (`run-20261106-222244.log.err`) captures the rejected
request as263,378bytes (`0x404D2`), alignment128, offset16 at return1DF289.
Read-only pool sampling records105 changed snapshots with no failed reads.
The last pre-crash pool0 snapshot has271,488 total free bytes spread across10
blocks, but the largest is218,784bytes. This is concrete native arena pressure
and fragmentation evidence, rather than a fixed motion-count limit. The
initial sampler attached before guest mapping was ready and failed; the
corrected standalone sampler attached after initialization and produced
`logs/fighter-m5-slots-pool-samples.json`. Both are accounted for; no game
memory was changed. The run restores saves identically.

A CPU animation memory adapter is now implemented and built, with native
acceptance underway. It registers a bounded32MiB guest-heap region under native
pool key63, preserving native allocation headers and the normal free path.
Only exact admitted active `motion/blazin.viv|Pdddd_A/B.ord` reads route there;
textures, other archives and ordinary allocations keep their existing paths.
The native small-block manager's free fallback reaches1E9F90, which reads the
allocation header's pool key. A per-call high-bit selector bypasses29500's
small-block allocation/default-pool OR without changing global allocation mode.
The backing remains available across matches; after native provider destruction,
the adapter requires the pool's original single coalesced free block.

The focused CPU-pool and finisher native C fixtures pass52 cases, including
registration, flag routing, register/stack preservation, allocation boundaries,
key collision, rejected flags, retained allocations and reuse. Regeneration and
the release build pass. These stand-in allocator tests are not native gameplay
acceptance. The original16-pair/34-active-motion fixture is now testing native
allocation, combat/result and return-to-menu release; keep its gates open until
the observed run completes.

The first native adapter run (`run-20261106-223951.log.err`) stops explicitly
at the loaded-bank ownership check before combat: no CPU pool was registered,
and the owned banks still use their original allocation. It has zero native
crash/watchdog signatures,81 presentation reports108/120/121, exit1 and
byte-identical save restoration. This is a failed routing/admission check,
not a CPU-pool acceptance pass. Bounded callback/path diagnostics are now
tracing the rejection; do not remove the ownership assertion to conceal it.
The diagnostic repeat (`run-20261106-224446.log.err`) exposed that the admitted
callsite list covered compressed reads but omitted the uncompressed1E4100→1E3FF0
callback at return1E4057. Generated owned banks take that path. The corrected list
covers1E3F20/1E4057/1E4453/1E473D/1E477A with verified(filename,bytes,flags) arguments;
it excludes1E43E8's different argument shape. Temporary path logging was removed.
All52 focused cases pass again, including every admitted callsite and rejected
nonmatching callers. The release rebuild passes; full acceptance repeats as
`run-20261106-224908.log.err`.

That corrected700-second run passes all8 combat/result assertions and the four
menu identities103/105/104/106, with349 presentation reports105/120/121, zero
crash/watchdog/debug-layer/unresolved-call signatures and byte-identical save
restoration. Native pool63 registers at01486180 with33,553,888 free bytes; all34
active motions verify inside the expected ownership domains. The read-only sampler
records39 evaluated custom resources, including12 paired role resources across
six subject/slot combinations, with zero ownership mismatches. Slots0/2/3 execute;
slot1 remains a targeted coverage gap.960 skipped/unreadable samples include
unbound/transitional pointers and must not be reported as zero failed reads.
Receipt:`logs/fighter-m5-slots-cpu-fixed-live-proof.json`.

A separate15-second free-list sample has8 changed consistent snapshots and no
failed reads. Minimum pool0 free space is7,927,520 bytes, largest block7,876,464;
pool63 has21,061,344 bytes free in one block. This directly contrasts with the
prior263,378-byte texture request failing against a218,784-byte largest block.
Receipt:`logs/fighter-m5-slots-cpu-headroom.json`. The32MiB CPU backing is a bounded
research budget, not an unlimited asset-size or cross-platform capacity promise.

The result screen was visually confirmed, but the added B input does not select
its A/Continue action. The run therefore does not establish destructor release.
A focused full-load/pause/exit follow-up is testing native cleanup; don't report
cleanup or repeated-match reuse accepted until its full-free-block check runs.

The first cleanup-only run (`run-20261106-230339.log.err`,350seconds) reaches
pause/quit confirmation, but its deadline expires before the final confirmation.
It does not prove native release; its optional attack/damage assertions are also
unmet at that early cutoff. It preserves saves identically. The observed native
sequence is Start, Down four times, A, Left, A. A300-second repeat scripts that
sequence at75/80/81/82/83/85/87/89seconds after Game.StartGame.

The scripted repeat (`run-20261106-231010.log.err`) verifies34 active motions,
then records native provider destruction and complete CPU-pool release:
32 allocations,33,553,888 bytes free, original single-block/sentinel invariants
restored. It returns to `battle/cmtype.swf`. This is actual native release evidence;
within-process second-match reuse remains covered by focused C fixtures, not by
this particular native run. It completes with150 presentation reports99/120/120,
zero crash/watchdog/debug-layer/unresolved-call signatures, verified four-fighter
menu identities and byte-identical save restoration. No game memory was poked
to force cleanup.

### Full paired-motion graph boundary

All94 source role banks contain five named type15 graphs: `_s` has a type18
child, `_t` type20, `_d` type13, and `_f`/`_h` each have two type25 children.
The hand helpers require palette samples0–20 in both selectors; face maxima
are11/14. A body-only or body/root-only replacement omits real source behavior.

Comparing the47 independently matched retail behaviors shows identical parent
type/control words and the same bounded one-entry scale attribute across all470
parents. Child populations also match, but duration differs in93/94 skeletal
parents and92/94 of each other role. A typed builder can retain the verified
control/attribute profile, while explicitly rebuilding source duration, child
times, destinations, coefficients and samples. It must not keep donor duration
or transcode everything to uniformly sampled type11 and call that lossless.

The `_d` helper output allocation is now proven. A0EA1/A11E0/9FA60/218C0/220A0
bind the second wrapper in the separate helper context. Its context+20 stores
time, not an output pointer. Ordinary caller9FAE0 reserves48bytes on its stack;
9FAF6 calls222A0(time, output, force=0), which temporarily installs time and
calls22150(output,0). At2223E, the wrapper receives that output and null selection.
9FB08 passes output+16 (floats4–7) to44E90 and stores its scalar result atB+58.
The actual allocation therefore contains12floats, independent of body bone count
or face/hand palettes. All94 source helper records use type13, four scalars,
destination4; a conservative typed profile can require exactly that mapping.

Paired `_t` also has a traced output allocation:9FCA5/A1190 resolve its record;
9FCDA/243B0/218C0/220A0 bind it as the first wrapper at CModel+1E0, with `_s`
second.23F56/22BF0 initialize the pose at CModel+140;22C20 returns its buffer,
and23F6C/22150 evaluate both wrappers there with null selection.26760/22A90
allocate48 times Skeleton.N bytes;22BA0 releases it. All94 source root curves
have one type20 dynamic channel, no constants, destination8 and no explicit
time array. They write floats8–10 of item0, so the numeric bound is N>=1.
This establishes the direct unfiltered paired root path, not every vector context.

A fresh source census finds all94 body type18 curves have40 dynamic channels,
no constants, block shift0 and explicit times; all94 root type20 curves use
one channel, no constants and block shift0. Parent control words are not zero:
body/root16163, helper5120, face49729 and hand50460. All470 attribute maps contain
one key1/size1 entry with low byte60 and retained upper padding bytes. A typed
builder must validate these against the verified template profile, then rebuild
source durations and numeric curves. Do not silently zero unknown header words.

Normal paired face/hand palette provenance is now established. The face root
comes from the owned appearance wrapper at visual+450, through paired context+20
and9FB30/245B0 into pose context+210+14. The shared hand wrapper33AB30 loads
`assets/misc.viv|share_hp.o` through1265E/21500;8B440 stores it atvisual+ABB8,
9DF40 copies it to paired context+24, and9FB30/24790 binds its root atpose+240+14.
22150 supplies those roots to the type25 evaluation route. Face teardown21670
and shared-hand teardown216A0 retain resource ownership; motion records borrow.

All46 rebuilt face receipts declare13/15 frames; source maxima11/14 fit both
selectors. The verified shared hand bank has32/32 frames, each with15 quaternion
channels and no vectors; maxima20/20 fit. Its largest destination676 requires
at least57 twelve-float output items. Admission must join exact palette identity,
selector/sample bounds and the matched output rig, not merely count curve keys.
These are static ownership and bounded-data proofs; existing fresh-cache numeric
oracles do not settle parent timing, retained-cache/filtered evaluation or native
execution of rebuilt full graphs. These remain concrete admission gates, not
permission to accept arbitrary serialized animation banks.

### Parent timing and explicit voice absence

Type15 parent dispatch caches child wrappers and a scale value separately from
serialized child curves. E5CD0 reports the parent u16 duration divided by its
cached scale when scaling is enabled; EDF90 and the other dispatch routes multiply
incoming time by that scale. EE190 additionally divides its child-returned time.
EE2D0/EE320 obtain the low byte of attribute key1. FD920 binary-searches sorted
8-byte attribute rows, so validated count/range/order and a nonzero scale are
required; a zero scale can collapse playback and divide by zero. Rebuilding must
preserve source parent duration and scale, not derive them from child key count.
Use fresh parent wrappers for changed graph shapes. EDEC0 re-attachment destroys
the existing cache using the new record's child count; a different count could
walk beyond or incompletely release the previous cache. Same-count re-attachment
can test cache invalidation, but arbitrary live graph replacement is excluded.
`scripts/fighter-parent-oracle.py` now extracts12 original generated parent
routines into an ignored stand-alone executable.48 invented cases pass with
scales1/2/60/255, durations0/93/65535, one/two children, scaling enabled/disabled,
reverse child dispatch, inverse time query, cache reuse and same-count reattachment.
Only manager allocation/factory/free and leaf evaluation are stand-ins; the
parent behavior executes the original generated bodies. Native body SHA-256:
`593f2ef9bd8d2965e62e16d5cd7090cd18a30cb7cd595b448aa71e1e124f1ef2`.
Receipt:`logs/fighter-parent-oracle/comparison.json`. Full leaf graphs, palette
joins and native converted-pack playback remain separate gates.

For missing voice categories, absence and an empty bank are different native
states. Exact pair lookup135CB0 leaves the initialized output handle at-1 and
returnsFFFF on a miss;137780/138070 return false before playback. A zero-entry
bank can register and become a successful lookup instead, with different selection
behavior. The proposed general adapter is an explicit absent state plus a versioned
per-owned-voice category presence mask, skipping registration for absent categories.
It is not implemented yet. Event alternatives at138EDA and family-only lookup
modes still need audit/native checks: absent exact-pair data is not a promise that
no other intentionally referenced event can play. Missing required keys must
remain errors; absent categories must never be silently populated from a donor.

## Timed finisher rotation reader

Added the general type13 reader and repeatable native-body oracle. Its normalized
sign-selecting interpolation and exact-key behavior match 20,160 evaluations,
2,078,720 bytes with zero differences across both x87 precision profiles.
The 94 source curves pass 188 key decodes and 1,128 additional samples. This does
not install a full paired-motion graph. See [type13 evidence](fighter-animation-type13-2026-11-06.md).

## Remaining work and decision

D-new (owner): extend M5 with general adapter R&D rather than close creator tools
and defer conversion. Preserve exact intended behavior wherever supported; report
unsupported data instead of silently substituting donor components.

1. Enforce the now-traced normal appearance/hand palette joins in full-graph
   conversion and extend native facial acceptance beyond the single component probe.
2. Complete native acceptance of the per-slot finisher bindings, then implement
   typed full-motion/cinematic rebuilding, preserving timing/root/helper data.
3. Inventory remaining voice, portrait, AI, cinematic and shared-table changes;
   convert all46 using typed resources and explicit dependencies, with a report
   accounting for every source change and any intentional nonfighter leftovers.
4. Validate/package using the ordinary creator/launcher path and playtest the
   converted pack with an independent pack in native menus/entrances/combat.
5. Update creator examples/guide with supported conversion/export commands,
   preserve evidence/limitations and then assess the M5 exit criteria.

Focused native component runs are recorded above; whole-pack acceptance remains open. No broad stock regression
was repeated, following the owner's waiver.
M6 cross-platform/release acceptance is still separate.
