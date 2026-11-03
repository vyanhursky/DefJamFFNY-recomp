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

Checkpoint after immutable-record acceptance: implementing the logical roster/native binding window and
coherent isolated save generations. This supersedes the immediate continuation
at the bottom of this note. Receipt checkpoint `d059bfd` is followed by the
ownership/profile work described below. Native Options and Story profile
write/close receipts and two independent controllers with cancellation have
passed. Four independent humans and repeated native matches now pass with
immutable custom records. Authored assets and launcher integration remain incomplete.

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
  identical. The imported-fixture header issue is isolated below.
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
same runtime/profile state also reproduced the title (`run-20261102-113727.log.err`).
Crucially, **stock with the same Options fixture and all fighter hooks inactive**
reproduced it too (`run-20261102-114059.log.err`), with 78 frame reports, median
120 and no faults. A fresh isolated fighter profile now shows the correct
**CHOOSE FIGHTER / A SELECT / B BACK** header, visually checked at 10 seconds in
the current result run. The issue is not established as a Fighter Mod regression;
retain the controls instead of patching copied methods to hide it.
The controlled helper is ignored
`logs/fighter-menu-isolation.py`, never a package or production feature.
Do not fix the title by substituting a guessed string. Native frame-0 assignment
already names `~CHTCR_CHSEFGHTR`. Captures
in the standard harness directory are transient; the research driver now retains
each completed run's PNGs under a unique ignored session folder.

Immediate continuation: finish the native two-pack window/save test, then prove
actual >255 selection/combat and P1/P2/four-participant ownership. Resolve the
header against a stock selector (fresh profiles now pass). Find a verified teardown boundary before
releasing frozen banks; movie entry alone is insufficient. Audit the remaining
profile fields and interrupted native batches, complete save/update/missing-pack
acceptance, then authored resource adapters, language/texture composition,
launcher Fighters transactions and ordinary Vendetta conversion. All shipping
gates remain false. No public push/PR, no PROGRESS.md edits.

### Full native result/save cycle and current follow-up

- `run-20261102-114526.log.err` / `logs/fighter-window-fresh-result-native.txt`:
  fresh namespace from native defaults, two custom fighters (101/102), actual
  result, then one verified Options generation. The immutable extension contains
  `research-alpha/second` and `research-beta/first`, both with metadata 0. Native
  Options contains 75 retail marks and no custom/private bank keys. 202 frame
  reports, min107/median120/max120, no faults. Captures are preserved under
  `logs/fighter-window-runs/7eca0476ebd048dd9e8b1394916d7503/captures`.
- Custom binding now requests native Options saving through **1E310(GameData,1)**,
  after verifying its manager/settings owner. Native purchase code uses this
  same dirty setter; D2300 is conditional. FUM1 restoration does not dirty state.
  `run-20261102-115439.log.err` / `logs/fighter-no-unlock-save-native.txt` passed
  the native selector, combat, result/rewards/save and return to Battle **with
  RECOMP_UNLOCK_ALL=0**. Live Options had 12 retail plus two selected custom marks;
  native persisted Options has only the 12 retail marks. One verified isolated
  generation retains both custom stable keys. 144 frame reports, min109/median120/
  max120, no faults; complete disposable saves restored identically. Captures:
  `logs/fighter-window-runs/c3edd9d2d40c4f46a6c5fdae217001e0/captures`.
- `--fresh-profiles` bootstraps the first complete native Options batch without
  importing a fixture. Integration fixtures exercise native compiler -> dormant
  pack -> re-enabled/content-updated pack -> appended identity migration -> next
  save batch, retaining metadata and unrelated opaque native profile bytes.
- The research save helper publishes a heartbeat/status. The harness stops only
  its own child if the helper fails, disappears or becomes stale; exceptional
  exits reap that child before restoring files. A failed verifier preserves the
  previous immutable head. At this checkpoint it did **not** establish a native
  successful-write acknowledgement: identical old bytes could satisfy the checks.
  The later FSA1 implementation and native Options proof below close that gap
  for the observed synchronous write/close path; other lifecycle cases remain gates.
- Native results read the transient byte through `1E820`, then emit field `fid`
  in `65540` at formatter callsite **65653**. A narrow **5F810** wrapper now emits
  the frozen logical identity for that field using an owned call frame. All
  other fields/calls remain native. Results use **t_MS_/l_MS_ exact IDs**, whereas
  selector **p_cf_ uses ID+1**. The portrait compiler now includes those result
  families, and runtime-owned `fighter_results.py` fills the original result name
  text field with literal custom labels. It relocates complete original actions
  by four-byte multiples, preserving original constant/parameter/literal pointers,
  nested function bodies and relative branches; label actions follow every native
  text-field placement (F4 replaces the field on a later frame). Re-lift/build:
  `logs/fighter-results-lift.txt`, `logs/fighter-results-build.txt`, both pass.
  Native visual acceptance of these result changes is still pending.
- Four-participant IDs254/255/256/257 run **120813 is not acceptance**: its
  5,785-byte pad script exceeded the native4,095-byte budget and was ignored.
  Stopped only the verified owned PID47700, then harness restored the save root
  identically. `build_pad_script` now uses the existing native repeat syntax when
  needed and rejects any remaining byte/256-token overflow before launch. The
  compact rerun **121422** selected254 and255 correctly, then stopped at256 on
  the prototype's fourth-argument guard. Primary APT inspection corrects the
  earlier costume interpretation: **ControllerSetup's fourth argument is nConID
  (0..3)**, not a costume. F4 passes nConID both first and fourth; clothing is
  read separately. The guard now preserves that native four-controller range.
  This stopped run is not four-participant gameplay acceptance.
- Four-participant boundary rerun **passed**: `run-20261102-122144.log.err`,
  `logs/fighter-boundary-four-controller-native.txt`. Native menus submitted
  logical **254/255/256/257**, stable **070000E5/E6/E7/E8**, bound respectively
  to engine **100/101/102/103**, all donor core5. Reviewed combat capture shows
  all four Capacity154/155/156/157 HUD labels and bodies. 240 frame reports,
  min105/median120/max120, no native faults; saves restored identically and one
  verified generation. PNGs retained in
  `logs/fighter-window-runs/ab4c5ddd62244dc19033a9e5d9e56e85/captures`.
  This is one human selecting three CPUs, not four independent human pads.
  Narrow F4 selector labels clip on the left; text-field fitting remains work.
- Result acceptance `run-20261102-123353.log.err` stopped safely before combat:
  Windows denied opening supervisor.json during an atomic replacement. No
  crash/watchdog, 46 frame reports/median120, complete save-root restoration.
  The harness now retries PermissionError and may reuse a previously validated
  heartbeat only until its original 15-second deadline; malformed/failed/stale
  state still stops. Focused supervisor/journal suite **77 passed,1 skipped**,
  `logs/fighter-supervisor-race-unit.txt`. Native result rerun is pending.
- Focused result/menu/archive/probe/journal suite: **51 passed**,
  `logs/fighter-results-final-unit.txt`. Later harness/supervisor/journal gate:
  **76 passed, 1 skipped**, `logs/fighter-supervisor-unit.txt`.
  Fresh full gate: **1,002 passed, 27 skipped, 1 deselected**,95.05s,
  `logs/fighter-results-full-unit.txt`; the later C-only controller-range
  correction passed the native four-participant boundary test above.

### Native save receipts and result-label correction (12:56)

- `run-20261102-123704.log.err` / `logs/fighter-logical-results-native-retest.txt`
  passed the saved-profile two-pack selection/combat/results/save path:153 frame
  reports,min107/median120/max120,no faults,saves identical,two verified generations.
  Native result fids map engine100/101 to logical101/102 with exact stable handles.
  Captures retained in `logs/fighter-window-runs/fa9d4418bdd34ba0b2fa3873b18edc7b/captures`.
  Portraits render, but the reviewed three-second result still has donor logos.
  This is **not custom result-label acceptance**.
- The first result adapter incorrectly treated `iFighterID` as a timeline local.
  It is local to original **fillStats(playerId)**. The corrected adapter preserves
  all original bytecode/pointers, saves that function and wraps its synchronous
  call, then uses the exact logical ID it publishes to `_level0._root.nLastPlayerID`.
  A runtime-owned action fills the original name field, hides the one-based
  logoLoader target and reapplies the label after F4's later field replacement.
  Synthetic tests now model this function scope; native visual proof is pending.
- Injected verifier failure **passed**: `run-20261102-124404.log.err`,
  `logs/fighter-supervisor-negative-native.txt`. Expected harness FAIL/helper
  error, eight frame reports,median120,no native faults,save root identical and
  committed head unchanged. The one-off injection helper remains ignored under logs.
- Added a real native IO witness: **1F8D61** wraps WriteFile's return and full
  output byte count, **1F694D** observes successful CloseHandle, and **1F8EBB**
  invalidates an in-progress attempt on unexpected seek. `fighter_save_io.[ch]`
  recognizes bounded MC02 streams, rejects short/failed/asynchronous writes,
  overflow, incomplete/failed closes and handle reuse without a fresh header.
  A complete closed stream must match exactly one staged identity/payload before
  an **FSA1** receipt, tied to its session/batch/record, is durably published.
  The Python verifier now requires that receipt plus an identical independently
  signature-verified on-disk file and metadata. Matching old bytes alone cannot
  publish. Generation files/head still receive their own durable publication.
- Do not reuse the earlier save audit's type14/event16 as acknowledgement:
  primary review found it is device/path selection. MC02 construction is in
  **1987A0**, not1989B0. Its write states enter198D40→backend+3C→19E380→19C7D0;
  chunk success alone is insufficient. Likewise8BE60/2D9E0 are input bookkeeping,
  not established voice/model release. No teardown was proven by those leads.
- Focused receipt C/Python/result suite **49 passed**, `logs/fighter-save-io-unit.txt`.
  Full unit gate **1,034 passed,27 skipped,1 deselected**,106.30s,
  `logs/fighter-save-receipts-full-unit.txt`. Re-lift/build passed
  `logs/fighter-save-io-lift.txt` / `logs/fighter-save-io-build.txt`.
  Fresh no-unlock native acceptance **passed**: `run-20261102-125328.log.err`,
  `logs/fighter-closed-results-native.txt`,143 frame reports,min109/median120/
  max121,no native faults,saves identical,one verified generation. Options wrote
  **76+64+5264 bytes**, then successful CloseHandle produced the5404-byte receipt
  for batch1/record0. The generation retains12retail marks and two custom stable
  marks, with no private bank IDs in native Options. Captures retained at
  `logs/fighter-window-runs/1d22271381204915b238e36fee7cba77/captures`.
  Custom result labels are visible, but donor logos subsequently overlay them;
  this is still not clean visual acceptance. The compiler now aliases custom
  l_MS logos to original **empty2** (APT/const only), while retaining donor t_MS
  portraits. This avoids relying on visibility set before asynchronous movie load.
  Focused archive/probe/result tests **29 passed**, `logs/fighter-blank-logo-unit.txt`.
  Native pack lifecycle checks subsequently passed, as below.

Native lifecycle against the receipt-backed saved generation **passed**:
`logs/fighter-lifecycle-native-summary.txt`. Each boot has15 frame reports,
min110/median120/max120,no faults,zero save batches and identical save restoration.
Removing Alpha (`run-20261102-130056.log.err`) and updating/re-enabling Alpha2.0
(`130132`) both retain generation **fe8d51f2ec8aaab4a5a2483521c5c0ec5fe2f470772c4610bb66b0dde742139c**.
Adding independent Gamma (`130207`) migrates to
**9f10bf2142ca9713c017d16bd8f0539869b285207f4c5ad51ed20da22bd605d3**.
Assertions compare every old ledger binding, both custom progress marks and all
native file bytes. New content gets a fresh identity; dormant Alpha history never
becomes Beta or Gamma. Separate summaries are `fighter-lifecycle-removed-native.txt`,
`fighter-lifecycle-updated-reenabled-native.txt`, `fighter-lifecycle-added-pack-native.txt`.

Pre-match reset/retail submissions now clear window ownership through a checked
codec operation. A frozen match cannot be cleared by a menu reset; verified
teardown is still required. This does **not** implement Back-from-ready release,
which does not issue a native ControllerSetup reset. Focused current gate:
**92 passed**, `logs/fighter-pre-match-clear-unit.txt`. The native IO output-count
pointer is now read only inside the active research path. The build first
correctly refused stale manual-wrapper metadata; re-lift
`logs/fighter-save-io-inactive-lift.txt` and rebuild
`logs/fighter-save-io-inactive-build-retest.txt` passed.

`--import-profiles` reads verified fixtures once into an empty isolated store;
it refuses fresh-default mode or replacement of an existing store. It permits
native Story/real-profile acceptance without changing the original fixtures.
A six-file composite fixture copies verified Options and the previously tested
VY3 profile (payload **0x5904 /22788 bytes**) read-only into ignored research data.
`run-20261102-130905.log.err` / `logs/fighter-real-profile-results-native.txt`
passed custom selection, combat, results and two complete Options save/close
receipts:159 frame reports,min109/median120/max120,no native faults,saves restored.
The first generation retains12retail/zero custom marks; the second retains12retail/
two custom marks. The imported VY3 file is present, but this Battle path did not
write it; native0x5904-profile save remains unproved. Captures are retained in
`logs/fighter-window-runs/713ba6dbc00b43fd9af5b0e790cb7c1d/captures`.
Reviewed both the two- and three-second results: Alpha Two/Beta One, correct donor
portraits, and no donor logos. Both names are fully visible. An initial reading
mistook the portrait's edge for text overlap; no placement fix was necessary for
these labels. Long-name fitting and narrow F4 names remain separate gates.

Latest stock regression **4/4 passed**,7min:
`logs/fighter-save-io-stock-regression.txt` / `logs/regress-20261102-132838.txt`.
Boot/title/main-menu goldens match;122s of combat,min102/median120 presents per
two seconds. This covers the inactive native write/close/seek wrappers before
the next ready-ownership hook is added.

Back does not issue ControllerSetup. The new runtime-owned native-menu adapter
wraps the original `keyBackHandler(nConID)` and observes its completed shared
CCharacter `iTakenBy` state, including recursive cancellations. It sends only a
bounded ready-owner mask through a fixed `Fighters.KeepReady(mask)` command.
The native dispatcher wrapper preserves the original bridge's allocation and
result-copy ownership; unknown calls remain original. The checked window codec
rejects malformed masks, owners with no binding and any frozen-match release
before mutating state. Focused C/menu/result gate **26 passed**,
`logs/fighter-ready-native-unit.txt`; re-lift/build/native acceptance underway.

Original Crib APT establishes the normal profile-save route: horizontal choices
Map0,Message1,Wardrobe2,Options3,Trophies4,Exit5, then first popup option Yes0.
`confirmExitCallback` enters the
loader's QuerySave/Save flow for `story/crib.swf`; completion calls
`Game.StartMainMenu(3)`. Initial selection inherits `_root.iCribLastIndex`, so
calibrate it rather than guessing a fixed right-press count. With this single-VY3
fixture, the first row is Create User ID; one Down selects the existing VY3.
An earlier audit confused constant-pool slots with assigned indices. Primary
review of `logs/fighter-crib-original-apt.txt:1121` verifies the assignments above.

### Native ownership and real-profile acceptance (13:59)

- The first Story calibration `run-20261102-133319.log.err` never reached Crib;
  an appended override of an earlier anchor closed later original input stages.
  `harness.merge_stages` now replaces matching anchors in their original position,
  retaining later route input. It also reports a missing route target after the
  earlier game summary. `133820` correctly failed the Crib target: its capture
  showed the Create User keyboard, rather than an existing-profile selection.
- After selecting VY3, `run-20261102-134205.log.err` reproduced a research guard
  bug: original `ControllerSetup( -1,0,99,0 )` has leading whitespace, which the
  strict integer parser rejected. No native fault; saves restored. The bounded
  shared C parser now accepts original ASCII whitespace and optional signs,
  rejects trailing non-whitespace and signed overflow, and has native C boundary
  fixtures. Focused gate **96 passed,1 skipped**,
  `logs/fighter-native-argument-unit.txt`; incremental build
  `logs/fighter-native-argument-build.txt` passed. Corrected VY3 Story entry
  `134407` passed:26 reports,min109/median120/max120,no faults,saves identical.
- `--expect-save options|profile` now requires this run's **committed** batch of
  the requested payload size plus valid native close receipts. Existing files,
  imported profiles, a different save kind or an uncommitted receipt cannot pass.
  `run-20261102-134542.log.err` deliberately remains a failed acceptance attempt:
  four Right presses from Map0 selected Trophies4; no profile save occurred.
  The explicit expectation failed instead of treating a clean run as a save pass.
- Real profile write/close acceptance **passed**:
  `run-20261102-135252.log.err`, `logs/fighter-story-profile-save-retest-native.txt`.
  Calibrated route: user selection Down4/A9; Crib messages No Down4/A6, Left12
  from Map0 to Exit5, A18, Up21 to Yes, A24. The original QuerySave/Save callback
  writes VY3 **76+64+22788 bytes**, then closes its22928-byte MC02 successfully.
  It also writes Options **76+64+5264**, then closes5404bytes. Both form batch1
  and one coherent generation before `Game.StartMainMenu(3)`.
  54 reports,min107/median120/max120,no native faults,saves restored identically.
  Reviewed Exit/Yes and returned-main-menu captures, retained in
  `logs/fighter-window-runs/748219d9847744c8a23d2e5adae1bb07/captures`.
  Generation **a7a641e9a9478b461048ccf946a0d5abbd3675678a7ea7933a8d4cdf6f373b6e**
  retains all six files and both custom marks; `fighter-profile-save-preservation.json`
  compares the untouched original fixture. VY3's payload stayed byte-identical in
  this no-progress-change run; the fresh native receipts prove a write actually
  occurred. This does not prove new Story progression or custom battle-stat saves.
- Two independent native-controller cancellation/reselection **passed**:
  `run-20261102-134828.log.err`, `logs/fighter-two-pad-cancel-native.txt`.
  P1 first submits logical101, then Back produces `Fighters.KeepReady(0)` and
  releases its pre-match binding. P2 independently submits that same logical101
  with native controller1; P1 chooses logical102/controller0. StartGame matches
  expected **102/101**, stable **0700004D/0700004C**, engines100/101, cores23/5.
  Reviewed ready/cancel/ready and combat captures in
  `logs/fighter-window-runs/a41222fb77304f5cb38043eac8d416e1/captures`.
  120 reports,min106/median120/max120,no native faults,one verified generation,
  saves restored identically. This establishes two independent humans; four
  independent pads and disconnect/rejoin remain required. The imported-fixture
  SELECT USER ID header is the previously reproduced stock behavior, not fixed here.
- Current full unit gate **1,039 passed,27 skipped,1 deselected**,113.02s,
  `logs/fighter-ownership-profile-full-unit.txt`. An earlier unprivileged full run
  failed four junction-creation safety fixtures on Windows access denial; all four
  passed with required filesystem permissions, and the fresh full gate above
  passed. Re-lift/build for the ownership dispatcher passed
  `fighter-ready-ownership-lift.txt` / `fighter-ready-ownership-build.txt`.
  Stock golden/combat regression **4/4 passed** on checkpoint `136eb7d`,
  `logs/fighter-ownership-profile-stock-regression.txt` /
  `logs/regress-20261102-140324.txt`: loading/title/main-menu goldens and122seconds
  combat, min113/median120 presents per2seconds. This predates the immutable
  record prototype described next.

Current binding experiment: keep the indexed Character bank rows immutable and
resolve every installed custom **stable handle** to its own immutable unindexed
template, rather than copying it into a reusable row. Native BE760 success is a
12-byte record/database/type tuple; preserve the native registered database/type
and substitute only the validated record pointer. StartGame's bank-token query
still yields a full stable handle. Primary stack-flow review shows20270's
per-participant BE760 output feeds its BEE90 property receiver; its secondary
0x5950-stride profile branch is gated by Story's created-player state or Battle
sentinel99, rather than custom byte tokens100..103. This is now implemented
behind isolated research controls. Original indexed banks are never overwritten;
every installed custom stable handle resolves to its canonical process-lifetime
template, independently of current participant ownership. BE760 retains the native
database/type tuple and only substitutes the validated record pointer. After the
original20270 returns, a guard compares each custom participant's actual core
field with its intended core. Original bank records are snapshotted and checked.
The subsequent guard also snapshots/checks every104-byte custom template across
binding/setup/Quit boundaries, rather than assuming that absence of a crash proves
immutability. Existing model cleanup
findings do not prove full teardown:9D340 resets an inner owner before replacement,
while the proven four-owner destructor is process-exit-only. Never call a UI
transition a model/XSH release acknowledgement.

- CPU oracle now executes **nine native routines**, adding16AE0/BEC70/BEE90 to
  the six packed-handle/lookup routines. It checks19 actual Character properties,
  their descriptor/schema/pointer/database/value relationships, and unchanged
  source records. Original75-row SOD passes19 checks
  (`logs/fighter-immutable-stock-oracle-final.json`); the300-custom/four-indexed-bank
  cache passes38 (retail plus immutable template logical256, offset278764),
  `logs/fighter-immutable-256-oracle.json`. Generated0/5 source hashes are in each
  report. Earlier oracle attempts wrongly treated the schema's Character type
  entry as a queryable Name property; they are scaffold failures, retained as such.
- Four independent human controllers **passed** immutable native selection and
  combat: `run-20261102-141259.log.err`,
  `logs/fighter-immutable-four-human-native.txt`. Three packs supply AlphaOne100,
  AlphaTwo101, BetaOne102, GammaOne103. Exact native controller/participant0..3,
  stable0700004B..4E, transient100..103 and materialized cores **4/5/23/56** all
  agree. Reviewed selector and60second combat captures under
  `logs/fighter-window-runs/a186108cefeb4049b5b8b0236d429266/captures`.
  130reports,min96/median120/max121,no crashes/watchdogs/unresolved calls,
  one verified generation,saves restored identically. Narrow selector names still
  clip; combat HUD labels render correctly. This run did not release/rebind banks.
- Internal `--immutable-reuse` enables selection ownership release **after original
  Game.Quit returns**. It retains all immutable records and does not claim models,
  XSH or voice resources have been released. Default research behavior remains
  frozen. Native repeated-match acceptance passed as recorded below.
  The driver now asserts each match's fresh ControllerSetup, stable binding,
  actual post-materialization core and prior Quit release separately; records
  from another match cannot satisfy it. The harness supports replacing later
  match stages in place without closing the first match's input. Focused gate
  **90passed,1skipped**, `logs/fighter-immutable-reuse-focused.txt`.
  Immutable re-lift/build and incremental record-guard build passed in
  `fighter-immutable-records-lift.txt`, `fighter-immutable-records-build.txt`,
  `fighter-immutable-records-guard-build.txt`.
- Two consecutive native matches **passed**, `run-20261102-142833.log.err`,
  `logs/fighter-immutable-two-matches-native-corrected.txt`. First101/102,
  stable4C/4D,cores5/23; original result/reward/save/Quit; second100/101,
  stable4B/4C,cores4/5. Both reuse engine100/101 while canonical records remain
  unchanged. The complete first match and120seconds of second combat ran,
  with277reports,min84/median120/max120,no native faults,two acknowledged Options
  save generations and byte-identical save-root restoration. Native core guards
  and independent per-match identity assertions passed. Both60/61second combat
  captures were reviewed under
  `logs/fighter-window-runs/66d9f7e52c65425ebb1807b999d06020/captures`.
  Earlier142358 is a failed harness calibration: a comma before#2 in an anchor
  caused later input to fire early. Stopped only verified ownedPID62980; restoration
  passed. Repeated-anchor compilers now reject that lossy syntax. The corrected
  route uses comma-free call prefixes. This acceptance does not establish a
  resource memory soak or all rematch/disconnect/Story cases.
- Strict `fighter_xsh.py` validates single-level paletted/BGRA/DXT1/3/5 SHPX
  textures, pixel/palette/attachment ranges, swizzle dimensions, directory/material
  names and overlap/expansion budgets. Typed shape renaming edits only verified
  directory and material references and revalidates the result; it never replaces
  arbitrary matching bytes. Unsupported mips/attachments fail closed. All46
  Vendetta XSH files passed, `logs/fighter-vendetta-xsh-validation.json`; this is
  file-format acceptance only, not model/material/runtime compatibility.
  CLI `fighter-registry.py inspect-textures` reports metadata and pending gates.
- Full gate **1,050passed,27skipped,1deselected**,97.30s,
  `logs/fighter-immutable-xsh-full-unit.txt`. The subsequent F4 text-layout
  prototype has28 focused passes (`logs/fighter-label-fit-first-unit.txt`) and
  still requires native visual acceptance. Stock immutable-build regression is
  **4/4passed** in `logs/fighter-immutable-stock-regression.txt` /
  `logs/regress-20261102-195432.txt`: loading/title/main-menu goldens and122seconds
  combat,min114/median120 presents per2seconds. The F4 layout probe is running;
  The earlier transform experiment failed visual acceptance; the accepted
  replacement is recorded below.

F4 name fitting follow-up:

- Transform prototype `run-20261102-195545.log.err` completed four-player combat
  and identity assertions but **failed visual acceptance**: generic TextField
  `_x/_xscale/_yscale` fallback changes its surrounding display object. Its35/39/43s
  captures show compressed panels. Removed the transform implementation; retain
  `logs/fighter-menu-transform-rejected.py` as ignored diagnostic source only.
  The generic property map2EA4A0 and setter167270→17EBD0→164B80 prove dispatch,
  not ownership of a TextField-local transform. Never infer the latter again.
- Replacement owns four additional native Text definitions, reusing the original
  font and immutable field templates. Its fixed75x64 bounds/font12 sit beside
  portraits; generated custom labels wrap, and original fields render unchanged
  for retail/created entries. It clears only the extra label when browsing away.
  No generic display transforms/visibility toggles are used in the F4 path.
- First overlay `run-20261102-200631.log.err` crashed in native155AD0 constant-pool
  fixup before selection, with save restoration intact. The appended PlaceObject
  lacked its always-present final clip-actions-pointer word. Native original
  placements are **64bytes**, including that zero word even without flag128.
  The compiler now clones complete verified64-byte placements and changes only
  depth, Character index, matrix and name pointer. It rejects unreviewed nonzero
  clip actions. Tests retain the complete slot and original Text records.
- Corrected overlay `run-20261102-201143.log.err` **passed** with exact
  custom100/101/102/103 and cores4/5/23/56. Reviewed35/39/43s captures show full
  panels and readable AlphaOne/AlphaTwo/BetaOne/GammaOne labels; P1's intervening
  locked native entry clears its custom label and restores the original presentation.
  131reports,min104/median120/max121,no native faults,one verified generation,
  saves restored identically. Captures retained under
  `logs/fighter-window-runs/2f2595aba5a043d3b31850e4bdfed1db/captures`.
  Focused overlay/created-assertion gate **21passed**,
  `logs/fighter-created-assertion-unit.txt`. Fresh full gate **1,052passed,
  27skipped,1deselected**,93.26s, `logs/fighter-immutable-overlay-final-unit.txt`.

### Real Battle ID and created-fighter progression

- `run-20261102-202336.log.err` /
  `logs/fighter-created-profile-signin-native.txt` **passed** native VY3 sign-in
  (`SetBMCurrentUserIndex(0,0)`), selection of the profile-owned created fighter
  **99** against **Alpha Two101 / stable0700004C / core5**, combat, results,
  rewards, saving and return to Battle. The internal `@created` assertion checks
  sentinel99; it does not introduce a pack identity or override StartGame.
  Two independently acknowledged generations committed, including one coherent
  VY3+Options batch. VY3's native writes were76+64+22788 bytes, total22928;
  Options was76+64+5264, total5404. 87reports,min108/median120/max120,
  no native faults; the complete original save root restored identically.
  Captures: `logs/fighter-window-runs/51b73c34930d4a8780eb08f936163dde/captures`.
- New head `9517a56bfeb12d9211bef698209743bc112af5a566f05c9c9aa9a8a2f0cc7ad6`.
  Independent verification of the previous and new immutable generation finds
  **16 changed bytes in the5904-byte VY3 payload**; all other payload bytes are
  unchanged. Native container hashes/signatures verify. Report:
  `logs/fighter-created-profile-progress-diff.json`. The changed words are
  recorded without assigning unproved gameplay meanings to their offsets.
  This establishes new native profile data, rather than merely re-saving an
  identical imported profile. Fresh reload after a custom-P1 match remains a gate.
- Battle's ControllerBind prompt defaults to **No**. Up then A chooses Yes;
  four Down presses and A select the sole actual VY3 profile from this fixture.
  A signed-in selector starts at the created fighter, unlike the guest selector.
  CPU selection must explicitly move to an eligible retail/custom fighter.
  `run-20261102-203325.log.err` correctly submitted Capacity261/logical365 for
  P1 but the script then confirmed the CPU's initial created-fighter entry and
  never submitted P2. Stopped only the verified probe PID65596; 263reports,
  min100/median120/max120, no native faults, one acknowledged Options generation,
  full save restoration. This is a script-calibration failure, not combat/save
  acceptance. The next run explicitly moved Right before CPU confirmation.
- `run-20261102-204235.log.err` completed native selection, combat, a decisive
  result, VY3+Options saving and return to Battle. The driver **failed its CPU
  expectation**: the Right press selected **Doc/Redman55**, rather than Blaze56.
  Do not label that original assertion a pass. A separate exact-identity check
  verifies **Capacity261/logical365/stable07000154/core5** as P1 and retail/doc55
  as CPU, including immutable native core materialization. Both acknowledged
  batches match their immutable committed payloads. VY3 changes16 payload bytes;
  all remaining payload bytes stay unchanged. Supplementary report:
  `logs/fighter-wide-real-profile-supplementary.json`; head
  `425fc94e83f04f28079e57200d3de603d72edfc57521dea2e7a72cf4f2b1844c`.
  216reports,min100/median120/max120,no native faults, full save restoration.
  Captures: `logs/fighter-window-runs/ac0bae6d30a04a4093c69557598ad840/captures`.
- Fresh-process reload `run-20261102-205044.log.err` disabled all300 capacity
  definitions and restored three historical custom marks. Native sign-in still
  selects VY3's original created fighter99; the reviewed4s selector capture shows
  its original body, clothing, name and stats. The CPU script selected GammaOne103
  rather than expected AlphaTwo101, so **the original driver assertion failed**.
  Native match setup99/101 uses the second participant's transient bank101 for
  GammaOne, not the public AlphaTwo identity. Combat, decisive result, two
  acknowledged generations and return to Battle completed.168reports,
  min102/median120/max120,no native faults, full save restoration. Current head
  `d75c7c17e20839530bf125796546ea3c973c359cea0c9b9672cd1f921dfb9b00`.
  Captures: `logs/fighter-window-runs/2300a295298d4affa04dbd23d752205a/captures`.
  Independent exact-identity/materialization checks verify99/103; both committed
  batches' native files are byte-identical to their successful-close receipts.
  The restored extension retains AlphaTwo, BetaOne, dormant Capacity261 and new
  GammaOne marks, and Capacity261 retains logical365. VY3 changes16 payload
  bytes; other payload bytes remain unchanged. Report:
  `logs/fighter-created-after-wide-reload-supplementary.json`. A clean driver run
  with corrected CPU expectations remains desirable.

- Clean corrected custom-P1 run **passed**: `run-20261102-205927.log.err` /
  `logs/fighter-wide-real-profile-exact-native.txt` independently asserts
  **365/55**, original native menu submissions, stable07000154/core5 immutable
  materialization, combat, result, two acknowledged generations including a VY3
  profile batch, and return to Battle.169reports,min100/median120/max120,
  no native faults, full save restoration. New head
  `18498428d2f114b444f8a4532d3f49d4ed066bc7c4e567fcb1410bd61a3be86a`.
  Captures: `logs/fighter-window-runs/8ceb4e6d202a481595a33c894003bae4/captures`.
  This closes the original CPU-expectation issue for the wide custom-P1 case.

### Language/fighter semantic screen composition

- `setup/fighter_composition.py` applies the existing DJDELTA1 format to a
  hash-pinned original file, with bounded nested archive edits, strict source
  and output hashes, operation/depth/size budgets and explicit target conflicts.
  Replacement order matches the native language builder byte for byte. A
  content-addressed provenance receipt records original/base/delta hashes.
- The internal probe's `--language-pack PATH` rebuilds the language screens
  base first, then generates fighter-owned menus/portraits from those bytes.
  Native `pc_language_adopt_composed_file` independently hashes the language
  loader's actual cache file and the final semantic output before adopting
  one final redirect. Missing/wrong/corrupted files cannot silently override
  another owner. The new path supports UTF-8 final filenames on Windows.
  Language files outside the shared screens archive retain their native loader;
  a language edit to assets/djv2.sod gets an explicit unsupported-composition
  error. This remains a research entry point, with shipping capabilities false.
- Focused composition/language/probe fixtures **68passed**,4.13s,
  `logs/fighter-language-probe-unit-final.txt`; build passes in
  `logs/fighter-language-composition-build.txt`. Coverage includes native cache
  parity, preservation of another served file, Unicode output paths, crossed
  hashes, missing output and a modified cached base. The first9 fixture failures
  used a new data root without pointing the native loader at the fixture's mods;
  corrected fixtures supply that root explicitly. No production bounds relaxed.
- Native acceptance **passed**: `run-20261102-211325.log.err` /
  `logs/fighter-language-created-reload-native.txt`. The diagnostic language
  pack changes the audited cmusen.loc entry199 from CHOOSE FIGHTER to SELECT
  FIGHTER and four annotation bytes in the original chooseF2.xsh; all other
  texture bytes remain identical. This exercises two native language files and
  an actual shared screens edit. The strict fighter-model SHPX subset does not
  accept every original menu shape identifier; this fixture edits only a bounded
  annotation in hash-verified original menu art and grants no new fighter asset
  format capability. `logs/fighter-language-composition-pack.json` records it.
  Native log confirms verified base adoption, real VY3 sign-in, created99 and
  GammaOne103/core56 bound to bank101. Reviewed4s/22s captures show SELECT FIGHTER,
  the preserved created fighter and GammaOne. Native menu assertions99/103,
  combat, decisive result, two acknowledged generations including VY3+Options,
  and return to Battle all pass.105reports,min101/median120/max121,no native
  faults, full original-save restoration. Captures:
  `logs/fighter-window-runs/5e09985618c44faaabe726b67d1b7ab4/captures`.
  Head `d532548f8efa56bef315c089cb978c4d7ad252215bdc5fe7716b3180ac78dcc9`.
  Independent readback verifies the native language base hash, final composed
  archive hash, exact preservation of the edited XSH, added fighter actions and
  translated cmusen.loc199 in the other served file. Report:
  `logs/fighter-language-composition-native-verification.json`. This also closes
  the fresh created-fighter reload after a wide custom-P1 save with the capacity
  pack absent, using corrected CPU expectations. Fresh full unit gate:
  **1,094passed,27skipped,1deselected**,93.08s,
  `logs/fighter-language-composition-full-unit.txt`. Stock/language regression
  **6/6passed** in10minutes: loading/title/menu goldens,120seconds of stock combat
  (min113/median120 presents per2seconds), native French and English SC05
  subtitles. `logs/fighter-language-composition-stock-regression.txt` /
  `logs/regress-20261102-213118.txt`. Native regressions did not change thresholds
  or golden frames. Visually reviewed French5s and English subtitle12s/20s
  captures: menu translation and rendered dialogue are intact.
- Final review fixed redirected research output paths before cache/store/session
  writes, including existing cache children. Common language manifest validation
  now rejects intermediate linked delta directories and returns the one checked
  parser snapshot to composition. Real Windows junction fixtures verify these
  refusals without creating files in their external targets. Focused gate:
  **128passed**,6.63s,`logs/fighter-path-focused-unit.txt`. These are checks of
  the current path structure, not handle-based protection against concurrent
  hostile filesystem renames.
- Final combined unit gate after the composition/path and typed-rig work:
  **1,127passed,27skipped,1deselected**,94.82s,
  `logs/fighter-composition-rig-final-unit.txt`. The Windows native build and
  six stock/language regression checks above remain the current C gate.

### Authored model findings and remaining uncertainty

- Primary inspection of community `V2IP_610A.o` finds94 exported `__Bone`
  identities with unique raw index DWORDs0..93 and no relocation at those words.
  Its complete bone-name/index map exactly matches retail Blaze `V2IP_113A.o`.
  Reports: `logs/fighter-community-bone-index.json` and
  `logs/fighter-retail-blaze-bone-index.json`. This is an animation-reuse lead,
  not proof of skin weights, poses, parents or material compatibility.
- The model inspector now retains the validated relocation graph and offers
  bounded inline-word/export lookup and explicit local-pointer traversal.
  Imported pointers, unrelocated words and one-past dereferences fail closed.
  Inspection exposes the bone map separately, rejects duplicate/gapped indices,
  and still reports `runtime_ready:false`. Game-free parser/graph fixtures:
  **27passed**. Rechecking610A against113A with the same implementation confirms
  identical94-entry maps and inline Skeleton headers; report
  `logs/fighter-model-graph-blaze-610.json`. Full reinspection also passes all
  **156retail+93community** model/face files, with observed bone populations0/94;
  `logs/fighter-model-graph-all-assets.json`. Fresh full unit gate:
  **1,064passed,27skipped,1deselected**,94.38s,
  `logs/fighter-model-graph-full-unit.txt`. No native C changed in this checkpoint;
  the immutable-build stock4/4 regression above still applies.
- `__Skeleton:::root` is inline data, not a pointer. Community data offset40C50
  and retail356C0 begin03AC3F23,0,94,0; the +8 count agrees with the94 bones.
  Correction: the community **Model resource is inline at43BB8**. Its first
  member points to43950, the named-descriptor array, rather than another Model.
  The ELF symbol's declared size4 does not describe the whole inline object.
  Primary checks confirm its named-descriptor count17, material count5 at+9C
  and group-table pointer43584 at+CC. Retail Blaze's corresponding counts are
  22/10. `logs/fighter-rig-inline-primary-check.json` records these checks.
- Corrected source leads:21500/215E0 query **PosePaletteBank**,21710 queries
  **AnimationBank**, and10AC20's count is an ELF section count. They do not prove
  a mesh decoder. CB3B0 queries the Model class; CB9A0 queries Skeleton and uses
  accessor+8 for runtime allocations. Its0x80 runtime record stride does not
  establish an on-disk skeleton stride. CB010 parses dotted/underscored tokens
  and formats V2CA_%s; it does not decode bone parents. A downstream12-byte
  association entry points to64 bytes copied into runtime+20, but its pose
  convention and link to the model file remain unknown. Do not describe these
  generic class accessors as XML readers without evidence.
- The owner's published [Modding Tools format research](https://github.com/vyanhursky/DefJam-Modding-Tools/blob/main/docs/research/trejo-pose-material-layout.md)
  supplied a primary format lead, independently checked against610A/113A. No
  reference-project implementation code was copied. New `setup/fighter_rig.py`
  validates the inline skeleton header and112-byte records: ordered parents,
  finite transforms, normalized quaternions, exact bone count, no pointer
  relocations in scalar records and a bijective opaque permutation. It preserves
  authored matrices instead of assuming they are all inverse local transforms.
  Geometry/skin mapping and animation compatibility remain explicit false gates.
  Game-free rig/envelope fixtures: **45passed** (18new rig cases).
- Full reinspection passes **156retail+93community** model/face envelopes,
  including **78retail+47community skeletons**. All125 share one topology hash,
  `a9488faa8e02c640e882ecc74a1aaf0329e4b9da0aee3ae148ceefbbe930ec47`;
  `logs/fighter-rig-all-assets.json`. The610A/113A whole skeleton bytes differ:
  matching parents/permutation, but28 translation records and22 stored matrices
  differ beyond their tiny scale/quaternion rounding differences. Therefore
  matching topology alone is insufficient for approved animation reuse.
  `logs/fighter-community-retail-rig-field-diff.json` retains that comparison.
  An intermediate complete gate passed **1,112tests**,27skipped,1deselected,
  93.20s,`logs/fighter-rig-language-final-unit.txt`; the later redirected-path
  fixtures are covered by the separate focused gate above.

### Geometry inspection checkpoint (2026-11-03 UTC)

- Local commits `940bb40` (language composition) and `1f51901` (typed skeletons)
  retain the accepted source work. Nothing has been pushed or opened as a PR.
- `setup/fighter_geometry.py` and `inspect-geometry` add strict checks of the
  observed material/render associations and data ranges. The group table is a
  zero word followed by **inline variable count/pointer lists**, not a fixed
  count/pointer-to-array table. Every wrapper must be RM+38, point back to that
  exported RM, and occur exactly once across the material groups. Stream headers
  must agree with their inline data pointers, counts/strides are bounded, scalar
  streams cannot hide relocations, positions/UVs are finite, and supported uint16
  strip indices stay inside the position stream. Short streams permit the
  observed two-byte tail padding. Sparkle streams and untextured helpers retain
  their distinct reviewed parent types.
- This is **data-structure inspection**, not validation of GPU render commands,
  native parameter bindings or skin weights. The separate CLI remains explicitly
  `runtime_ready:false`; plain `inspect-model` retains its envelope/skeleton
  scope. Optional `--textures` checks shape references against the supplied
  validated XSH, refusing missing dependencies instead of treating arbitrary
  shape names as globally available. Shared sparkle/environment libraries still
  require a verified baseline dependency adapter.
- Current corpus result: **65/78retail and1/47community main models** pass these
  structure checks. Twelve retail and46community models stop on unsupported
  index-header/parameter layouts; one retail model has an unsupported stream
  layout. These are not declared corrupt assets. In610A RM33, the binding after
  EAGLAnimationBuffer does not follow the header/count/data arrangement used by
  the currently checked subset. The reader deliberately rejects it; the next
  decoder must establish the native parameter schema before accepting it.
  `logs/fighter-geometry-all-assets.json` retains per-file diagnostics, including
  the accepted original Blaze113A and Trejo112A reports.
- **74focused tests passed**,0.29s,`logs/fighter-geometry-cross-unit.txt`, including
  20new game-free geometry cases: variable group lists, surface/helper/point
  layouts, texture dependencies, scalar-pointer injection, bad counts, nonfinite
  values, aliased wrappers and index bounds. Full gate **1,147passed,27skipped,
  1deselected**,94.20s,`logs/fighter-geometry-full-unit.txt`. No native C changed
  after the build and six stock/language regression checks above.
- Automatic approval review refused a proposed local download of the owner's
  complete Modding Tools decoder source, citing the no-copy instruction. The
  download did not run. Continued using published format documentation and
  independent bounded local-asset inspection; no source copied from Comoria.

### Re-enable/update and native texture coexistence (2026-11-03 UTC)

- Re-enabled the300-definition capacity pack after its missing-pack test, as an
  ordinary1.0.1 manifest update. Stable `research-capacity/unit-261` keeps logical
  **365**,handle**07000154**,core5, while its name becomes **Capacity261v2**
  (with spaces in the actual label) and authored Health becomes**88**.
- First run `run-20261102-220552.log.err` selected the neighboring364 due to
  navigation calibration. The exact expected-identity assertion correctly
  failed. It still completed a match and two acknowledged generations,168reports,
  min108/median120,no faults,full save-root restoration; it is not acceptance of
  the intended update. Summary:`logs/fighter-reenable-update-native.txt`.
- Corrected navigation (five final Rights) `run-20261102-221201.log.err` /
  `logs/fighter-reenable-update-retest-native.txt` passes native identity**365/55**,
  immutable core materialization,combat,results,two acknowledged generations
  including VY3,return to Battle and full save-root restoration.192reports,
  min108/median120/max120,no native faults. All historical bindings are unchanged;
  independent native SODB readback confirms Health88 and the new name.
  `logs/fighter-reenable-update-verification.json`; head
  `b36cf378b8c810755677fd0fe0cf91e1298f59b949774ec04cef3cc7009c4fb0`.
  **Visual acceptance failed:** the high stat overfills its bar and the longer
  header clips. Preserve this finding; identity/save success does not close it.
- The probe now supports existing `--texture-pack PATH` layers, using their
  native order and a shared root with the language pack. It validates images,
  the language pack's optional image layer and the complete1023-byte native
  list budget. A common pack-file path checker rejects linked intermediate
  directories for both deltas and textures. Focused gate75passed,3.90s,
  `logs/fighter-texture-probe-unit.txt`.
- Combined native acceptance **passed**, `run-20261102-221912.log.err` /
  `logs/fighter-language-texture-coexist-native.txt`: diagnostic language screens
  and LOC199,three ordinary donor-backed fighter packs,real createdVY3 and the
  existing Faithful HD **2048x2048 RGBA** Bo atlas. The original A012 source ID
  was independently recomputed as
  `219a7ab28c2db0e729c73fe94292ebce24df12352687a099334ea3055f9726b0`.
  Native upload/load of that exact atlas is recorded at20465–20466;12mips,
  44,739,240 accounted bytes. All300capacity definitions were absent again;
  their historical identities and the saved261 mark remain intact/dormant.
- This combined run asserts**99/103**,core56 for GammaOne,then combat,result,
  VY3+Options write/close,two verified generations and return to Battle.118reports,
  min101/median120/max120,no faults,full save-root restoration. Reviewed combat
  capture20s; donor Bo appearance has its existing HD texture, not new community
  geometry. Captures:`logs/fighter-window-runs/c0b00ce3e4e84c479f04e6a1c5f2464c/captures`.
  Independent report:`logs/fighter-language-texture-coexist-verification.json`;
  head`ee23ebc28409502423e1b39ef4185dbeb070029b17d2fad848074f784db5de61`.
  This run predates the next name/stat presentation fix.

Remaining implementation gates, in order:

1. Finish F4 fitting acceptance, long names, three/four-player result variants,
   disconnect/rejoin and rematch cases. Real created-fighter selection and
   progression now pass as recorded above. Existing
   native two-pad cancellation, four independent pads and two-match reuse have
   passed; preserve their exact evidence instead of redoing their investigation.
2. Complete native missing-pack/update/re-enable and interrupted-write cases,
   building on the real Battle ID/custom-P1/created-fighter reload evidence. Native5904-byte
   write/close and isolated generations already pass; unchanged VY3 payloads do
   not prove new progression. Internal `@created` is an assertion of sentinel99,
   never a package identity or a StartGame override.
3. Repeat immutable >255/four-bank boundaries and memory/resource soaks. Canonical
   immutable records avoid row overwrite; they do not establish every asset's
   lifetime. Native bank windows remain four simultaneous participants, not four
   installed fighters.
4. Complete authored resource validation/registration (geometry/skeleton/materials,
   motions/events, voice/AI/cinematics) and shared language/texture composition.
   ELF envelopes,125skeletons and46XSH texture files pass only their documented
   format gates; matching topology is not verified skin/animation compatibility.
5. Whole-pack launcher Fighters transactions/restart/profile-helper integration,
   ordinary Vendetta conversion, authoring tools/docs, platform/Story/soak gates
   and owner play-test. No shipping capability, public push or PR is authorized.

Resource/lifetime audit corrections: 109F80 is the DynamicLoader ELF parser, not
cleanup. 102130 resolves four-character SHAPENAME via SHAPE in a supplied module
context, not a demonstrated process-wide shape table. The XSH owner/load path and
collision/lifetime rules remain unproved. Game.Quit is registered to462C0; its
686A0 manager-C call only clears a UI flag. Neither that flag nor C20B0/E660 UI
transitions establish fighter-resource teardown. Save async backend vtable2C0728
slot18 maps, in the own XBE, to19E180; lower19C7D0 checks one WriteFile's return and
full byte count but is not yet linked to MC02 writes. Continue from concrete
writers/owners rather than treating queue submission or movie entry as teardown.

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
