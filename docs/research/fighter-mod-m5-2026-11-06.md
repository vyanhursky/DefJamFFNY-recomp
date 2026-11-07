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
  bridge. Follow 97AA0/+430 -> 24BE0/CModel+2C0 instead. Exact normal-fighter
  provenance remains under investigation; neither trace closes that proof.
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
  allocate global WAZA rows. Implementation/native acceptance remain pending.
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

1. Finish the combat appearance-to-palette resource provenance check and extend
   native facial acceptance beyond the single component probe.
2. Implement the general per-slot finisher template/animation bindings and
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
