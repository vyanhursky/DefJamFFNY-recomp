# Fighter Mod Support: active runtime implementation

Work in progress on 2026-11-02, local `research/custom-fighter-mods`, following
`3df4086`. Owner requests implementation/testing of **all documented next steps**,
with an update in a few hours. Continue through the runtime/save/launcher/asset
work; do not treat this intermediate note as completion. Keep work local, no push
or public PR, and no reference implementation code copying.

The requested three-hour update was delivered at 09:54 America/Vancouver in this
thread; its one-time heartbeat was deleted after delivery. Work began about
06:54 and continues. No additional reminder/automation remains.

## Current code and tests

11:39 checkpoint: implementing the logical roster/native binding window and
coherent isolated save generations. This supersedes the immediate continuation
at the bottom of this note. Latest committed source is `01b41a6`; the following
window/save work is being tested locally before its source checkpoint.

- Native list capacity is **not a single 255 limit**. The signed-byte selection
  path narrows inside `558E0` before `1E700`; the shared roster has a different
  fixed boundary, and Options has 80 cells. The chosen R&D direction is a large
  logical native-menu roster plus **four participant banks**. Installed fighters
  retain historical logical keys; each match binds at most four native rows.
  This is within the approved hybrid/virtualization direction, not a proposed
  four-installed-fighter limit. Lifetime/rebind and full ownership remain gates.
- `--logical-menu` appends original CCharacter objects to the shared native
  aCharacters array without adding Character rows. The corrected 300-fighter
  browse run `run-20261102-103633.log.err` / summary
  `logs/fighter-logical-300-native-browse-corrected.txt` highlighted **Capacity
  261 / logical 361**, with name, donor portrait, stats and consistent thumbnails.
  78 frame reports, min 110 / median 120 / max 121, no native faults, saves
  identical. Header still reads SELECT USER ID; stock comparison is pending.
  It is browsing evidence, not >255 gameplay acceptance. The earlier 10:23 run
  had incorrect thumbnail states and is retained only as a diagnostic.
- Generated visual methods now retain the original constant pool verbatim,
  replace only visual getID operands with literal getThumbID calls, and relocate
  branch targets. The created-fighter identity comparison remains untouched.
  Positive integers above 127 use a wide immediate. The 10:45 direct regression
  stopped on a **new guard bug**, not a native crash: its guard read a narrowed
  argument with unrelated upper bits. Validation moved to the original four
  strings in `558E0`, before native narrowing. The replacement call frame owns
  its vector/text and never edits an original movie string.
- `setup/fighter_window.py` and `src/hooks/fighter_window.[ch]` define FWR1,
  runtime-owned typed templates/banks with checked row offsets, identities and
  bounds. The SODB writer can retain unindexed templates/string IDs. A 300-row
  synthetic pack produces **four additional indexed rows**, with original rows
  unchanged. The public FMB1 ledger has no private bank identities. Private
  handles occupy reserved internal ranks and cannot become public progress.
  Four-slot bindings, 254/255/256/257, duplicate ownership and match freeze have
  C codec tests. This is not yet native capacity acceptance.
- The first window run at 10:56 reached the automatic user-ID save and stopped
  on the intended save gate (`logs/fighter-window-native-two.txt`). It is not a
  gameplay pass. Persistence is therefore connected before further acceptance.
- `fighter_profile_store.py` implements authorized **D3B isolated generations**:
  immutable native files, historical ledger and hash-bound custom extension,
  with one durable head publication. Fault injection at files/manifest/generation/
  head proves recovery reads a complete old or new generation. A stale writer,
  crossed extension, torn file or redirected state cannot replace committed data.
- Native D2300 temporarily projects **retail-only Options** into the original
  queue, then restores its live data after the native copy. D23B0 captures profile
  save intent; D2780 seals an FSB1 intent journal. **Sealing is not success**.
  `fighter_save_journal.py` requires every staged native file's full payload,
  identity and MC02 signatures to match before committing exactly that batch
  over the previous generation. It excludes unstaged partial working files.
  FUM1 restores historical custom marks, including dormant content. All writes
  are under ignored isolated research data; original fixture files are read only.
  Native file verification and helper/runtime failure reporting still need
  acceptance before a production launch capability can be enabled.
- Focused window/profile/journal/probe gate: **44 passed**,
  `logs/fighter-journal-final-focused.txt`. Earlier full gate after logical UI
  changes: 952 passes plus four junction setup failures under the sandbox; those
  **four passed** with junction access (`logs/fighter-logical-junction-unit.txt`).
  Fresh full gate: **994 passed, 27 skipped, 1 deselected**, 91.03 seconds,
  `logs/fighter-window-full-unit.txt`. One later evidence assertion test passes
  in the eight-test probe gate; the full gate predates that additional test.

Native window/save follow-up:

- `run-20261102-111208.log.err` committed the first independently verified
  native Options generation. It then stopped because the prototype assumed
  costume 0 only. Native ready submissions use costume **1** for the first set;
  the generated one-costume contract now accepts selection 0 / ready 1. No
  crashes/watchdogs; this stopped run is not gameplay acceptance.
- `run-20261102-111532.log.err` / summary
  `logs/fighter-window-journal-native-two-retest.txt` passed: native menu P1
  **Alpha Two 101 / stable 0700004C / donor core 5** bound to engine 100; CPU
  **Beta One 102 / stable 0700004D / core 23** bound to engine 101. Match setup
  receives 100/101, and the reviewed 90-second capture shows those custom names,
  expected bodies and combat. One verified save generation, 78 frame reports,
  min 110 / median 120 / max 120, no faults, disposable saves restored identically.
  The stronger evidence parser also checked the recorded stable/core bindings.
- **First native >255 path passed:** 300 enabled custom fighters plus the
  original roster, `run-20261102-111846.log.err`, summary
  `logs/fighter-window-native-wide.txt`. Native menu submits **361** for
  Capacity 261; its historical handle **07000150** binds to engine 100/core 5.
  Retail Blaze remains **56/core 5**. Match setup is 100/56, HUD is Capacity 261 /
  Blaze, and native hit/damage events advance. Reviewed 85-second combat capture.
  One verified save generation, 78 frame reports, min 101 / median 120 / max 120,
  no crashes/watchdogs/unresolved calls, saves identical. This proves a real
  native selection beyond 255 without widening the original byte consumers;
  it does not prove every boundary, independent controllers or bank rebinding.
  Four-participant boundary and progress-save/reload tests remain next.

Header isolation: stock `run-20261102-112219.log.err` shows CHOOSE FIGHTER and
both native button hints (79 frame reports, median120, no faults). Moving copied
constant pools to function registration did **not** fix the stale SELECT USER ID
header (`run-20261102-112854.log.err`). Even an empty appended action has the
stale title (`run-20261102-113339.log.err`); it is therefore not established as
an error in the copied thumbnail methods. An original-screens control under the
same runtime/profile state is running next. The controlled helper is ignored
`logs/fighter-menu-isolation.py`, never a package or production feature.
Do not fix the title by substituting a guessed string. Native frame-0 assignment
already names `~CHTCR_CHSEFGHTR`; find which layer prevents its update. Captures
in the standard harness directory are transient; the research driver now retains
each completed run's PNGs under a unique ignored session folder.

Immediate continuation: finish the native two-pack window/save test, then prove
actual >255 selection/combat and P1/P2/four-participant ownership. Resolve the
header against a stock selector. Find a verified teardown boundary before
releasing frozen banks; movie entry alone is insufficient. Audit the remaining
profile fields and interrupted native batches, complete save/update/missing-pack
acceptance, then authored resource adapters, language/texture composition,
launcher Fighters transactions and ordinary Vendetta conversion. All shipping
gates remain false. No public push/PR, no PROGRESS.md edits.

### Earlier accepted checkpoints

Accepted state (09:05): two independent packs, three donor-backed custom
fighters, native mixed four-participant combat, and P1/CPU custom selection
through the original selector. FML1 names and FMB1 stable identity bindings are
connected. Full unit gate: **923 passed, 28 skipped, 1 deselected**, 90.55 s
(`logs/fighter-bindings-full-unit.txt`). Stock golden/Story regressions are in
progress. The earlier failures below are historical diagnostics; they are fixed
by the inline-map correction described later. No shipping capability is enabled.

09:25 update: native donor thumbnails and custom name headers are now visible
in the original two-player selector (`logs/fighter-menu-alpha-two-092139.png`).
ControllerSetup still receives custom IDs **101/102**, and StartGame receives
the same values: this verifies that presentation remapping did not alias input
identity for this case. `run-20261102-092139.log.err` / summary
`logs/fighter-native-presented-menu.txt`: 79 frame reports, median 120, min 102,
no crashes/watchdogs/unresolved calls, all disposable saves restored. The capture
at 90 seconds shows the normal weapon-help pause after attacks/damage, not a
runtime stall. The native created-player comparison inside selectChar was then
preserved explicitly (one byte operand redirected through a spare local pool
slot); the corrected compiler needs its follow-up native run.

09:34 follow-up: the compiler preserving the created-fighter comparison passed
the same native selection test: `run-20261102-093035.log.err`, summary
`logs/fighter-native-menu-semantic-retest.txt`. P1 101 / CPU 102 reached StartGame,
79 frame reports, min 102 / median 120 / max 120, no crashes/watchdogs/unresolved
calls; saves restored identically. Focused menu/probe/harness gate: **65 passed,
1 skipped**, `logs/fighter-menu-final-focused.txt`. The four-participant native
menu variant is the next acceptance run; earlier four-participant combat used
explicit StartGame test controls.

Stock regression with wrappers inactive: loading/title/main menu/fight/Story
intro **5 passes** (`logs/fighter-bindings-stock-regression.txt`). Crib/gym
failed because the copied mixed profile list selected a non-Story entry; no
crashes, continuous frames, final UI remained user-ID flow. Logs
`run-20261102-091145.log.err` / `run-20261102-091607.log.err` were triaged and
read. Retest in progress on `logs/fighter-story-regression`: only a valid VY3
profile imported from the retained hashed fixture, canonical folder generated by
the existing save-import tool. Source profile/fixtures unchanged. Do not count
these two checks passed until the curated retest actually reaches its anchors.
Curated retest completed: **crib and gym both passed**, 56/99 seconds,
`logs/fighter-story-curated-regression.txt` and `logs/regress-20261102-092810.txt`.
Together with the original five passes this covers all seven targeted stock
rows; the initial two fixture failures remain recorded above.

Full unit gate including the shared APT parser/menu compiler: **929 passed,
27 skipped, 1 deselected**, 88.33 s (`logs/fighter-runtime-final-unit.txt`).
Subsequent native-menu evidence assertions: six focused tests pass; the new
unlock projection has nine focused tests (`logs/fighter-unlocks-unit.txt`).
Neither unit gate is a complete save-lifecycle or wide-selection acceptance.

- `setup/fighter_bindings.py` allocates append-only historical selection tokens
  and Character handles. Retail bindings retain original ranks; removed custom
  definitions become dormant. Adding an earlier-sorting pack, a display rename,
  update, removal or re-enable does not reassign prior identities. The ledger is
  runtime-owned state, never an author-specified engine-ID field. Its schema is
  not by itself an authenticated profile transaction or complete save migration.
- New FMB1 Python/C codec (`src/hooks/fighter_bindings.[ch]`) has bounded rows,
  explicit availability and checked permutations for native/name/selection
  lookups. Manual `BE870`/`BE760` wrappers translate the Character handle domain
  while preserving native tuples and the absent sentinel. Before translation,
  every active binding is checked against the loaded native row's name hash,
  selection key and core ID. Other SOD tables keep their native path.
- Native stable-handle acceptance: `run-20261102-085715.log.err`, summary
  `logs/fighter-stable-handles-fight.txt`. All 78 active bindings verified;
  custom Alpha One/Beta One combat, 101 frame reports, min 110 / median 120 /
  max 121, no crashes/watchdogs/unresolved calls; disposable saves identical.
  This is not complete coverage of all opaque stored handles outside the two
  audited SODB APIs. Missing native rows resolve absent, never a different row.
- `setup/fighter_archive.py` composes bounded BIG directories while preserving
  original payloads/footer. Portrait aliases rename all four inner filenames
  without editing movie/model/texture bytes. Source screens archive is pinned
  to SHA-256 `389066e1e20a35de850fdd8fbf38edbae3050dabd6b9a49e9b48bf27bbac0b57`.
  Three fighters' nine portrait variants add 619,339 bytes. Cache SHA-256
  `e284d0491af3d5746c06ecd750a042f9e82379a9f8a9c22d05b7cddd970c6412`.
- Native menu selection acceptance before stable-handle wrappers:
  `run-20261102-084849.log.err`, summary `logs/fighter-native-menu-select.txt`.
  ControllerSetup receives **P1 101 / CPU 102** and StartGame receives the same
  keys without a StartGame fighter override. Native HUD displays Alpha Two /
  Beta One. 79 frame reports, median 120, no crashes/watchdogs/unresolved calls,
  saves restored. A normal first-play weapon-help dialog pauses the match at
  the reviewed 90-second capture. Body portraits load; custom thumbnail frames
  and name headers are blank and remain implementation work.
- `apt-dump.py` now walks nested function bodies without letting their End
  truncate the parent timeline. EA_PushLong is an unaligned four-byte LE word,
  corroborated by own chooseF2 colour bytes and the format writer in
  [AptConverter](https://github.com/feliwir/AptConverter/blob/master/ActionHelper.cpp).
  No converter implementation code was copied. This reveals CThumbGrid redraw
  and highlight methods: they call getID and add fixed thumbnail state offsets.
  Portrait identity must remain distinct from thumbnail frame identity.

- New `setup/fighter_loc.py`: bounded LOCH/LOCT/LOCL parser/composer, opaque
  headers retained, original translations/indices preserved, explicit conflicts.
  16 synthetic tests pass. A local cmusen experiment adds one entry: 3,068 to
  3,069 strings, all existing text unchanged, output SHA-256
  `c1da36db85e15a3b5d66849d010d7356a4830fb5261e5e4a80ab8c3748ce337d`.
  Native file-parser acceptance and LOCT opaque header interpretation remain
  unproved. Visible English labels do not determine the original opaque keys.
- New FML1 protocol: `setup/fighter_names.py`, native codec
  `src/hooks/fighter_names.[ch]`. Bounded sorted lookup keys, contiguous UTF-16
  payload, duplicate/range/encoding/budget checks. Cross-language synthetic tests
  compile the real C decoder and exercise malformed and Unicode inputs.
- `setup/fighter_native.py` now hashes the generated name file into the report;
  preview cache writes/checks `fighter-names.bin`. This changes the report/cache
  identity while the earlier constructed SOD bytes remain the same.
- New `src/patches/fighter_runtime.[ch]` and manual wrapper `45180` preserve
  original localization lookup priority, then serve validated custom-name data
  from a single game-owned UTF-16 allocation. Off without
  `RECOMP_FIGHTER_NAMES`. This is local R&D name registration, **not roster
  activation**. Optional `RECOMP_TRACE_FIGHTER_NAMES` logs lookup metadata.
- An explicit `RECOMP_FIGHTER_NAMES_PROBE` test runs on the first
  successful native lookup, call the native lookup again for every registered
  test name and compare exact UTF-16. No profiles or roster modifications.
- Native exact-name probe passed for all three names in
  `logs/run-20261102-073227.log.err`; stock menu rendered normally, 0 crashes.
- Full unit suite with MSVC available: **845 passed, 27 skipped, 1 deselected**,
  90 seconds (`logs/fighter-runtime-unit-results.txt`). Later probe/partition/asset
  additions require a new full run; focused names/probe/model tests pass.
- New `scripts/fighter-runtime-probe.py` recompiles semantic inputs from the
  verified original SOD, then invokes the guarded harness with a dedicated
  `logs/fighter-runtime-probe` data root. It rejects a running game and signed-byte
  overflow, clears inherited debug settings, and never activates installed packs.
  `RECOMP_FIGHTER_RESEARCH_SOD` works only in that disposable namespace with
  settings disabled and custom names loaded. This is an internal vertical slice;
  it does not advertise a shipping capability or a final roster limit.
- Native file-loader accepted the 78-record/two-pack SOD: boot
  `run-20261102-074003.log.err`; default retail fight
  `run-20261102-074054.log.err` reached combat, median 120 presents/2 s,
  0 crashes. Custom-vs-custom StartGame controls (100/102) reproducibly crash
  during model loading, `run-20261102-074636.log.err` and
  `run-20261102-075727.log.err`. Identical retail donors (54/7) pass:
  `run-20261102-075325.log.err`. All saves restored identically.
- New wrappers retain original menu filtering/context ordering, then partition
  completed lists with retail entries first. Initial native test found zero
  custom tokens because these lists contain **packed handles**, not symbol
  hashes. `BE870` encodes table rank in the high byte and record rank in the
  low 24 bits; `BE760` resolves them. Corrected code uses that native resolver
  and separately passes name hashes to the tested stable-partition helper.
  Corrected native acceptance is in progress, not yet established here.
- New `setup/fighter_elf.py` validates data-only ELF32/MIPS model envelopes,
  section/symbol/relocation bounds and explicit import ownership; no CPU code,
  absolute-address symbols or arbitrary relocation methods. New bounded RefPack
  decoder in `setup/fighter_assets.py` enforces output limits before expansion.
  Synthetic malformed/executable/relocation tests pass. Local envelope audit:
  **156 retail objects and all 93 Vendetta objects accepted**; the original
  objects reference 619 distinct imports. New texture factory/shape imports
  remain unresolved under the exact retail allowlist. EAGL geometry, skeleton,
  texture/material semantics and native authored-resource acceptance remain gates.
  Evidence: `logs/fighter-model-envelope-audit.json`. This is not pack conversion.

## Native build lane

Research checkout has its own `game` junction to the owner's original extracted
dump. Original dump and retained release checkout are unchanged. Copied ignored
analysis/generated output was initially hash-verified with pipeline-state; fresh
lifts now include the `45180` manual wrapper.

CMake configured with cached SDL/ImGui source paths from the retained release
lane and FETCHCONTENT_FULLY_DISCONNECTED. Sandboxed MSVC configure initially
failed C1902 (PDB manager); configuring/building with process permissions resolved
it. Use `scripts/build.ps1 -Preset win-x64-release`, not ad-hoc stale binaries.

Build 1 succeeded (`logs/fighter-native-build.txt`). Stock boot route with trace:
`logs/run-20261102-071956.log.err`, capture `logs/shots/boot/boot-25s.png`.
Native main-menu screenshot reviewed: normal UI rendered. 15 frame reports,
median 120 presents per two seconds, **0 crashes/watchdogs/unresolved calls**;
disposable save restoration identical. Triage is UNEXPLAINED due 11 inherited
diagnostic/file-stub classes, including NtFsControlFile stub and optional missing
assets; primary read the first context/tail. Do not call this an all-green full
regression or a custom-fighter acceptance run.

Disposable root: `logs/fighter-runtime-data`, initially copied from retained
release test save (not the owner's active profile), then guarded by harness.
Never run games in parallel or let harness kill another lane's instance.

Build 2 (`fighter-runtime-lift-probe.txt`, `fighter-native-build-probe.txt`) and
ordering build (`fighter-order-lift.txt`, `fighter-order-build.txt`) succeeded.
Latest build (`fighter-handle-lift.txt`, `fighter-handle-build.txt`) includes the
corrected handle resolver and narrow materialized-model/input diagnostics. The
current diagnostic run is recorded in `logs/fighter-model-diagnostic.txt`.

## Newly established native UI facts

Read-only trace of GameMode vtable `293160`: slot `+40` is `47BC0`, next `+44`
is `480E0`. Temporary 32-byte rows in `47BC0` hold the `+4` UTF-8 sort key;
after sorting the function emits values from `+0/+18/+1C` into global `3A07B0`,
without copying the text into that output. `480E0` consumes that value list, not
the temporary rows. This supports fixing the **sorting representation** while
preserving full visible labels. It is not a whole-program proof of every alias.
Direct ASCII paths and missing-string fallback must also be covered; merely
bounding conversion `45320` for caller `47DF3` is insufficient without that audit.
Global `3A07B0` output capacity also needs inventory; dynamic temporary storage
does not prove a dynamically sized final roster.

## Save-format lead (primary observation)

Copied native profile files A/ABC/VY1/VY2/VY3 are 22,928 bytes (`0x5990`). The
first four little-endian words in VY1 are:

`4d433032, 5990, 40, 5904` (raw magic `20CM`).

The size fits `0x4C header + 0x40 identity block + 0x5904 profile block` exactly;
the profile name starts at `0x8C`. Existing `scripts/save-import.py` already
documents and tests the three HMAC-SHA1 regions and the port's signature key.
Reuse it rather than re-investigating the signature container. This does not
establish payload identity fields or safe migrations.

Native generated source contains the actual magic initialization and checks
(`src/recomp/gen/recomp_0011.c` around 126075 / 129742 / 129943 in this lift).
`52B60`/`D23B0`/`D05A0` staging provides a raw fixed-size profile copy; it is not
per-field serialization. Slot 18 has a separate row-base pointer at `+4`, so
the apparent numerical overlap between its frontend bytes and profile offsets
does **not** prove those bytes are serialized. Complete persistence interpretation
remains open. `52E60` and `52ED0` are empty UI callbacks in this image; stop
treating them as payload readers.
Previous async/UI queues and metadata/image readers did not establish the save
wire boundary; stop treating them as evidence of serialization.

## Immediate continuation

### Save container and selection-width findings (09:40)

The Character unlock container has a real **80-entry** fixed inline backing.
`200E0` constructs the manager-index-0x18 block; `16160` calls `144B0` with
`this=block+4`. The binder sets capacity `block+20=80`, external-count pointer
`block+28 -> block+1268`, and backing `block+2C -> block+12E4`. `16440` initializes
the preceding sentinel to FFFFFFFF and 80 dwords. `16810` inserts sorted keys,
masking metadata bit 23 for comparisons, with no capacity check or growth.
`14460` resets counts; it does not free pointers.

These unlocks **are persisted in Options**, even though they are outside the
per-user profile rows. `D2300` copies `block+50`, length 1490, into the Options
settings buffer; `D1DC0 ->14540` copies it back and synchronizes the live count.
Within that payload: count at **1218**, sentinel **1290**, 80 keys in
**[1294,13D4)** (hex offsets). Absolute framing in the complete Options file is
still unproved. Do not overwrite unrelated settings bytes or append keys to this
fixed payload. Growing only the live array would lose progress on save/load.

`setup/fighter_unlocks.py` now decodes that set by stable historical keys and
projects only retail marks into the fixed payload. A versioned extension retains
custom/dormant marks and the opaque metadata bit. Hashes bind it to the exact
settings bytes and ledger generation; updating a ledger requires an explicit
old-generation restore then new-generation projection. Unrelated native bytes
are preserved. Tests cover 300 customs, removal/re-enable, deterministic ordering,
malformed counts/sentinels/keys, wrong metadata and crossed save generations.
This pure codec performs no writes and is **not yet connected to native expanded
storage or a coherent save transaction**.

Primary check against the retained, unmodified Options fixture confirms the
complete file is **5404 bytes**, with the existing MC02 8C-byte header/identity
prefix and a **1490-byte payload**. The Character count is 22, sentinel FFFFFFFF,
and all 22 entries have the expected Character-table high byte 07. This verifies
the payload offsets against an actual saved file as well as the native copy path.
`logs/fighter-options-real-projection.json` records a full in-memory round trip
of those 22 marks plus **300 customs**: the native payload remains byte-identical,
322 marks restore, and the recomputed MC02 signatures verify. The source file
was read only. This is a real-file codec test, not native save/load acceptance.

The runtime now validates the fixed Options payload before `14540` loads it and
before `D2300` stages a save; every unlock must have a stable historical binding.
`144B0` verifies the owner/container layout, and the `16810` wrapper rejects an
81st insertion before the original unchecked write. These guards remain confined
to the research roster. They do not implement expanded live storage/persistence.
The actual C wire decoder agrees with Python at counts 0/1/79/80/81 and for
malformed lengths/sentinel/duplicates/order: **19 focused Python/C tests pass**,
`logs/fighter-unlock-native-unit.txt`. Re-lift/build passed
`logs/fighter-options-guards-lift.txt` / `logs/fighter-options-guards-build.txt`.

Four-player calibration: chooseF4 has **three columns**, versus chooseF2's six.
The first script stopped on retail WC and never reached combat; it is not an
acceptance pass. The corrected script selected custom **101/100** and retail
**17/58** through the original four-player menu, all identical at StartGame.
`run-20261102-094131.log.err` rendered Alpha Two/Alpha One/Crack/Crow in combat,
123 frame reports, min 109 / median 120 / max 120, no native faults and saves
restored. Its explicit assertion named the wrong retail pair (Blaze/Bo), so the
driver correctly failed it. Repeat with the intended exact four stable keys
and the Options guards is running; do not relabel the failed assertion a pass.

Repeat **passed**: `run-20261102-095123.log.err`, summary
`logs/fighter-options-native-menu-four.txt`, exact asserted identities
**101/100/17/58**, 124 frame reports, min 107 / median 120 / max 120, no native
faults and save root restored identically. This uses one human controller to
choose P1 and three CPU participants, not four independent human controllers.
With a copied real Options fixture, boot `run-20261102-095712.log.err` also
**passed**: native `144B0` owner binding, `14540` loaded all **22 stable unlocks**,
and `16810` ran (89 watched entries across set kinds). Fifteen frame reports,
median 120, no faults, saves identical. Summary: `logs/fighter-options-native-load.txt`.

An ordinary 10-fighter semantic research pack reaches the native unlock limit:
`run-20261102-100426.log.err`, summary `logs/fighter-native-unlock-capacity-stop.txt`.
The last watched Character insertion had count **0x50 (80)**, and the guard
stopped before the unchecked write. Exit 1 / harness FAIL is the **expected
negative test**, not playable-roster acceptance. No native crash or watchdog;
entire fixture restored. Triage's first unclassified return at line 412 was
read and belongs to the inherited NtFsControlFile stub; tail lines 4946–4948
show the intended bounds rejection. This is now a reproduced native bottleneck,
not merely a guessed save capacity.

### Shared roster storage boundary

Primary source check corroborates a further constraint: GameMode's temporary
count*32 workspace is dynamic, but its final `3A07B0 + index*4` list is static.
The literal base appears in **26 native functions**, not just the two wrapped
menu producers. In `4E9A0`, `3A09B0` is separately assigned the scalar input
argument while the list uses computed `3A07B0 + index*4` writes. Thus **index
128 would overwrite a known distinct scalar at 3A09B0**. This establishes an
upper bound before that state, not proof that every preceding slot is usable.
`3A09B4` is also scalar state; `3A0BB0` is a separate object. Relocating only
the list producer/consumer pair would miss the other literal readers/writers.

The next D1 prototype therefore separates the full logical roster from a bounded
native binding window. Test whether runtime-owned native movie data can append
logical CCharacter entries, preserving each player's grid/cursor, then bind the
chosen definitions at audited setup boundaries. Keep stable identity and saved
progress outside transient byte slots. This is a general adapter experiment,
not a fixed 28-fighter product limit or a promise that >255 selection is solved.

Correction to earlier speculative row interpretation: `D23B0` copies
`block+16FC`, length **40**, into the identity staging buffer. Its second stack
argument supplies the separate **5904** user-profile payload; `52B60` passes
`row+C`. There is no established profile payload at `row+16FC`.

Selection widening also has a bounded inventory: setter `1E700` and getter
`1E820` use manager owner + **1AAA + participant*5**, separate from the block
pointer. The six getter callsites (46D50, 46FD8, 55B85, 55C7A, 3E24A, 65641)
truncate or sign-extend the return. Setter callers: 559E0, 55C05, C147B, C14C8.
`1EB00`/`1EC50` initialize/reset four rows. Direct readers in `1E850`, `20270`
and interior `20525` test created sentinel 99. Replacing only the getter/setter
does not widen the callers; low-byte aliases of 98/99 must never become customs.
`55A20` also copies a second set of byte-sized participant rows, so a widened
side table needs explicit copy semantics. These are implementation inputs, not
a claim of playable keys above 127.

### Inline index correction and native combat acceptance

The model crash was caused by an incomplete SODB writer, rather than an asset
incompatibility. The Character table's primary member map is inline at header
`+16`. Generic pointer-following lookup accepted the old output, but packed-handle
functions `BE870` and `BE760` derive the map from that inline address. Relocating
the map produced `FFFFFFFF` handles for additions. The writer now preserves the
inline maps and rewrites their subindex pointers. A malformed relocated-map
fixture is rejected. The CPU oracle now executes six native routines, including
both packed-handle routines and a complete row round trip.

Evidence: `logs/fighter-inline-oracle.json`, generated C SHA-256
`35bb1296…`, SOD SHA-256
`ab7733b608c3d69ed62821f07b9523332a0e6000e25cbc38878f5526194da3e7`.
The earlier pointer-only oracle was insufficient; its >255 result is not a
packed-handle or gameplay proof. Full unit gate after this correction and the
asset validators: **875 passed, 27 skipped, 1 deselected**, 88.83 s
(`logs/fighter-inline-unit-results.txt`).

Two independent packs supply three donor-backed fighters. Corrected native runs:

- `run-20261102-081556.log.err`: Alpha One versus Beta One, custom selection
  keys 100/102, native HUD names, normal models, attacks and damage. 99 frame
  reports, min 106 / median 120 / max 121 presents per two seconds; no crashes,
  watchdogs or unresolved calls. Native GameMode list: 77 entries, three custom
  entries appended. Summary: `logs/fighter-inline-custom-fight.txt`.
- `run-20261102-082207.log.err`: Alpha One, Beta One, Alpha Two and retail Blaze
  together, including a custom and retail fighter sharing the Blaze donor core.
  Reviewed the 65-second capture: all four HUD names and normal combat rendered.
  126 frame reports, min 109 / median 120 / max 120, no crashes/watchdogs or
  unresolved calls. Summary: `logs/fighter-inline-ffa.txt`. Triage's terminal
  line-count warning reflects the scheduled harness termination while GPU and
  health events were still advancing; the harness did not detect a hang.

Both runs restored the entire disposable save root identically. Both use explicit
StartGame test controls; later two-player browsing acceptance is recorded above.
The earlier 08:05/08:10 runs failed on the old inline-map bug and are not passes.
The `20270` diagnostic observed a venue object (`V2BG02A`); it is a general data
materializer, not established evidence of a fighter-specific Character→core path.

Native APT inspection establishes that `FE_ID` is both ControllerSetup identity
and portrait identity. Portrait paths use `p_cf_<FE_ID+1>_<2|3|4>p.swf` beneath
`portrait/p_CF/`. Keep identity separate from donor artwork: derive portrait
archive aliases rather than changing FE_ID. The native movie already has a
scrolling CThumbGrid; the three small buttons under a portrait select variants,
not roster pages. Thumbnail registration still needs its own proof.

1. Complete four-player native menu/input ownership and created-fighter acceptance.
   Donor portraits, scoped thumbnails, custom headers and two-player selection
   now work; preserve all identity comparisons when adapting other native views.
2. Trace MC02 constructor/writer/reader and keyed profile containers. Establish
   D3A complete companion interception, or implement authorized D3B isolation
   with stable missing-content state. No unsafe roster activation before this.
3. Implement safe sorting and original-order/custom partition in both native list
   paths; inventory final global arrays, selection-byte consumers, previews and
   four-player ownership. Select expansion/virtualization from full evidence.
4. Compose localization with language changes, wire typed resource adapters and
   asset validators (remove donor-only preview restrictions through normal
   adapters), then test one custom fighter and independent packs natively.
5. Integrate whole-pack launcher Fighters transactions and restart behavior;
   lifecycle/capacity/menu/resource/Story/platform acceptance and ordinary-format
   Vendetta conversion remain required. Finish documentation/handoff as code
   changes, source-only commits, no PROGRESS.md edits on this feature branch.
