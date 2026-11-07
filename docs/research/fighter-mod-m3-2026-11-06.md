# Fighter Mod Support: M3 lifecycle and save reliability

The owner authorized continuing M3 here on 2026-11-06. Work remains local on
`research/custom-fighter-mods`, following M1/M2 commit `fe78f12`; no public push
or PR. Use the approved native-profile/versioned-extension approach first,
with isolated profiles as the approved fallback if the native boundary cannot
be made safe. Original saves remain outside experimental writes.

**M3 implementation and focused Windows acceptance are complete locally.**
The accepted route retains native profiles plus a versioned extension; no
separate-career fallback is required by this evidence. All game tests used
disposable copies with complete save restoration. Launcher activation and
normal-profile adoption remain M4; platform/release regression and long-run
resource soak remain M6. No public push, PR or additional owner decision.

## Acceptance work

| Area | Status |
|---|---|
| Competing/stale save sessions | Fixed and focused tests pass; native caller now pins its materialized generation |
| Interrupted native writes and publication recovery | Five abrupt host publication boundaries and three native save-interruption points pass; clean Story restart/write verified |
| Pack disable/remove/update/re-enable | Authored-resource cycle, native Alpha removal, last-pack removal with Story save and updated-pack re-enable pass |
| Repeated matches and resource ownership | Corrected mixed-pack two-match run passes 10 combat checks, exact identities, release-before-reload and fresh cache/voice ownership |
| Disconnect/rejoin and ready/cancel | Actual SDL virtual-device detach/rejoin and two-human ready/cancel/reselection with the updated pack pass |
| Story and created-fighter profiles | Created-vs-authored and signed-in authored-player combat/results/save verified; same Story profile reloads and saves with zero packs. Bounded field audit supports the route; full opaque schema is not claimed |
| Native-profile extension integration | Shared session backend extracted and used by probe; focused tests pass. Production adoption/launcher workflow remains M4 and gated |
| Native profile deletion | Confirm and cancel pass; successful deletion persists through restart without re-import |

Testing is focused on changed behavior and these acceptance gaps. The owner's
request to avoid routine regression work remains in effect. No additional
architectural choice is currently required.

## Stale-session overwrite fixed

The old Monitor loaded the latest Store head when each completed batch arrived.
A session materialized from generation A could therefore overwrite profile
progress committed by another session to generation B: its compare-and-swap
used B even though its gameplay state came from A.

Monitor now requires the exact generation used to materialize the session,
including explicit `None` for a fresh namespace. Each batch must still descend
from that generation, and the expected head advances only after this monitor's
own successful commit. The Store's existing compare-and-swap also protects the
interval between verification and publication. A stale session fails with a
reload instruction and leaves the newer native bytes and extension intact.

The focused reproducer failed against the previous implementation with
`DID NOT RAISE ValueError` (`logs/fighter-m3-stale-session-before.txt`). After
the fix, profile-store/journal checks pass **35/35**
(`logs/fighter-m3-save-session-unit.txt`). Tests cover a competing commit before
and after monitor construction, another session's first save, and successive
verified batches from the same session. These are host transaction checks,
not native gameplay acceptance. An initial sandboxed attempt could not create
pytest temporary directories; the permitted retry produced the actual failure.

## Restart and publication recovery

A Monitor now claims an empty journal with an exclusively created, flushed
session marker. It refuses old intents, close receipts or an existing marker.
Recovery loads the last committed generation into a fresh session; it never
replays an abandoned working directory. A focused restart test preserves the
last completed profile write while leaving a later torn write untouched for
diagnosis.

Separate child processes now terminate with `os._exit` at each publication
boundary: native files, manifest, generation rename, before head, and after
head. This bypasses exception cleanup and leaves real abandoned staging
directories and locks. Fresh readers recover the complete old generation
before head publication and the complete new generation afterwards, including
both profile bytes and matching custom progression. A subsequent writer can
commit successfully. This tests abrupt process death, not physical power loss.
Store/journal checks pass **44/44** in `logs/fighter-m3-process-recovery-unit.txt`.

## Full-resource consecutive matches

`logs/run-20261106-153101.log.err` loaded both independent full-resource packs,
finished one match/results/save, returned through native Game.Quit, then loaded
and fought with a different pair. Actual selections were Alpha first/second
(logical 100/101, one-based Character cores 142/143), then Beta first/second
(logical 102/103, Character cores 144/145). Behavior tables use zero-based
cores 141/142 and 143/144 respectively. Voice resources changed from 600/601
to 602/603. Motion generation one was invalidated before generation two loaded;
both paired-finisher providers verified their active motions.

The original driver mistakenly expected mixed Alpha/Beta pairs, so its final
menu assertion **failed**. Do not record that command as passing. Independent
checks against the actual selections passed both immutable binding epochs and
**10/10 combat assertions** (`logs/fighter-m3-rebind-actual-evidence.json`).
This is a pack-pair transition, not the originally intended mixed-pair test.
The second match stopped after combat evidence, before its results screen.
The harness reported 236 two-second frame samples, min106/median120/max121,
zero crash/watchdog/unresolved-call signatures, two verified save generations,
and byte-identical complete save restoration (`logs/fighter-m3-rebind-native.txt`).
Guest heap was 5,243,952 bytes at both match setups; contiguous allocation
was 52,449,280 then 52,547,584 bytes. Two samples do not establish a leak slope.

The motion adapter now refuses to overwrite an unreleased source generation.
Focused C fixtures cover allocator address reuse after correct release,
unrelated-manager release, and rejection of overlapping registrations.
Motion, cinematic-cache, paired-provider and voice selection logs now expose
their ownership transitions for the next targeted native acceptance.
Affected native adapter tests pass **130/130** in
`logs/fighter-m3-resource-ownership-unit.txt`; these changes postdate the
native run above. The release build passes
(`logs/fighter-m3-resource-release-build.txt`). Its ignored CMake cache had
dependency paths into a removed checkout; those now use the already fetched
pinned SDL3/ImGui source in this checkout. No toolkit revision changed.

The corrected mixed-pack acceptance **passes** on that release build:
`logs/fighter-m3-ownership-native.txt`, native
`logs/run-20261106-154942.log.err`. Match one selects Alpha first/Beta first
(logical100/102), then match two selects Alpha second/Beta second (101/103).
Both immutable identity/materialization epochs and **10/10 combat assertions**
pass. There are 280 two-second frame reports, min105/median120/max121, zero
reported native faults, two verified save generations and byte-identical
complete save restoration. The second match ends after combat acceptance,
before results; the first includes results, save, native Quit and teardown.

Motion generation one releases source81829780 from manager00349760 before
generation two reuses that allocation. Cinematic descriptors82939104 and
requests8293E810 (12 native +40 added) are handed to that manager's native
destructor; generation two owns fresh descriptors82938E04/requests8293E510.
Finisher provider00349B98/storage810A0580 is released after native destruction,
then the second provider verifies. All four voice slots refresh for each setup:
600/602/absent/absent then601/603/absent/absent. Guest heap remains5,243,952
bytes at both setups; contiguous allocation rises98,304 bytes. This establishes
two-match ownership/reuse, not a long-run leak bound or platform soak.
The earlier stale-build preflight is retained as
`logs/fighter-m3-ownership-preflight-stale.txt`; it never launched a game.

## Whole-pack lifecycle and last-pack removal

The real Alpha/Beta full-resource packs passed compilation and isolated save
migration through both installed, Alpha removed, Alpha updated/re-enabled,
all removed, and original versions re-enabled. Missing model data in an update
was refused without changing the save head. Native profile bytes, historical
handles and saved custom marks stayed identical throughout. Re-enabling the
original definitions reproduced the original cache key. This is authored-data
and persistence acceptance, not native gameplay after a pack change:
`logs/fighter-m3-authored-lifecycle.json` and
`logs/fighter-m3-authored-lifecycle-fixed.txt`.

This uncovered a concrete failure when removing the last pack: the compiler
tried to construct a participant window from zero additions. It now emits an
explicit `retail-only` report and retail database without private banks/window,
while retaining the historical ledger with dormant custom identities. The
focused reproducer fails before the fix (`logs/fighter-m3-last-pack-before.txt`)
and passes afterwards with the 300-fighter/window and migration checks
(**3 passed**, `logs/fighter-m3-last-pack-unit.txt`). The research game probe
still requires an active custom fighter; launching the all-disabled product
configuration remains part of the profile/launcher integration gate.

## Audit follow-ups

- Resource bindings are process-lifetime data; native motion sources,
  cinematic caches and paired-provider metadata have narrower lifetimes.
  Repeated-match testing must establish teardown before registration, voice
  selection refresh, and correct ownership after changing selected fighters.
- The profile Store currently commits completed records as updates; native
  profile deletion needs an explicit witnessed removal path before normal
  profile lifecycle can be declared supported.

M3 is in progress. Launcher integration and release acceptance remain M4/M6.

## Controller detach and rejoin in combat

`logs/fighter-m3-hotplug-native.txt`, native
`logs/run-20261106-164430.log.err`, passes exact Alpha first/Beta first identity
checks and **5/5 combat assertions**, with129 two-second frame samples,
min103/median120/max120, zero native fault signatures, one verified generation
and byte-identical save restoration. The test removes SDL virtual joystick1 at
fight step900. At1080, host slot0 returns disconnected1167 and native held/pressed
input is zero. It attaches joystick2 at1200; at1320 it occupies player1 again,
host left-X is32767 and native held input is65544. Subsequent native movement
and input-linked attacks are observed. Both fighter record identities remain
fixed through every sampled fight step, and there is no ControllerSetup after
Game.StartGame. `logs/fighter-m3-hotplug-evidence.json` retains the bounded checks.

This is actual SDL virtual-device removal/addition. The emulated Xbox USB device
deliberately remains present and reports neutral input during host disconnection;
this is not guest USB topology removal or physical-device-driver acceptance.
The test-only game hook requires an isolated fighter window, exactly one known
virtual pad and no physical joystick. SDL's bundled headers document these
joystick operations as thread-safe, so no toolkit patch is needed. The harness
ends menu presses at Game.StartGame and supplies no combat input tail: otherwise
its raw-script fallback could hide disconnection. The replacement pad is driven
through SDL, without guest-memory or USB-report writes. Release build passes
(`logs/fighter-m3-hotplug-build.txt`); toolkit pin is unchanged.

## Native profile deletion boundary

The disposable VY3 deletion diagnostic reached the native confirmation dialog;
its default is No. Confirming Yes removed the entire copied profile directory
at 69.096 seconds, before harness restoration at 131.496 seconds:
`logs/run-20261106-161123.log.err` and
`logs/fighter-m3-delete-observed-files.json`. The harness restored the complete
save tree identically, with zero native fault signatures. Its unrelated
fighter-selector target was never reached, so the original command reports
FAIL; this is deletion evidence, not a passing selector run.

The in-memory D32E0 callback correlates with that deletion but does not itself
check filesystem success. Do not use row clearing alone as a removal receipt.
The native file-operation success boundary is being audited before hooking it.
Host support now accepts ordered FSD1 deletion witnesses only with the exact
unique committed profile identity and absence of its entire working folder.
Partial deletion, a missing workspace, unknown/ambiguous identities and stale
sessions cannot publish. The resulting generation excludes that profile and
its two companion files while retaining Options, the fighter identity ledger
and global custom unlocks. A restart does not re-import the removed profile.
FSC1 acknowledgements are written durably only after generation publication.
Host save/deletion/recovery tests pass **59/59**
(`logs/fighter-m3-deletion-unit.txt`); native receipt/barrier integration and
acceptance remain pending.

The implemented native boundary is XDeleteSaveGame at 1F89FD, reached from
19CA00. Its arguments are the ANSI drive and UTF-16 profile name (the latter
goes through the existing 1F8360 directory-name hash adapter); its stdcall
return pops two arguments and reports a DOS error, with zero indicating
success. Snapshot the name before delegation. A zero native result produces
FSD1; the host's exact-folder-absence check remains essential because a native
API success code alone is insufficient proof. The D32E0 row callback is not
used. Before new save staging/deletion, the runtime waits for the preceding
operation's FSC1 acknowledgement; after deletion it waits for its own. This
prevents a later operation from overwriting files awaiting verification.
The wait is bounded and fails closed without replacing the committed head.
Internal isolated-research fault points stop the native process after intent
publication or after the first Options/profile header write, bypassing cleanup.
Focused host/native-I/O checks pass **84/84**
(`logs/fighter-m3-save-lifecycle-unit.txt`); release build and re-lift pass
(`logs/fighter-m3-save-lifecycle-build.txt`, `logs/fighter-m3-save-lifecycle-relift.txt`).
Native receipt and interruption acceptance are in progress.

Confirmed native deletion now **passes** on that build:
`logs/fighter-m3-delete-confirm-acceptance.txt`, native
`logs/run-20261106-162744.log.err`. XDeleteSaveGame reports success, FSD1 is
published, the verifier observes the exact absent profile folder and commits,
then the native worker receives FSC1. One generation removes VY3 and its
companions. Restarting the Store does not re-import VY3; the read-only original
fixture stays byte-identical. The harness reports54 two-second samples,
min108/median120/max120, no native fault signatures and identical full save
restoration. `logs/fighter-m3-delete-confirm-evidence.json` records the session,
Store and committed generation. A further focused test passes recovery when
publication succeeds but writing FSC1 is interrupted
(`logs/fighter-m3-delete-lost-ack-unit.txt`, **1 passed**); recovery uses the new
head in a fresh session rather than reviving the deleted profile.

Cancellation also **passes**: `logs/fighter-m3-delete-cancel-acceptance.txt`,
native `logs/run-20261106-163023.log.err`. Choosing No leaves VY3 present, emits
no FSD1 and commits no generation. Restart retains the profile. The harness
reports54 two-second samples, min109/median120/max121, no native fault signatures,
identical save restoration and an unchanged original fixture. Machine-readable
evidence is `logs/fighter-m3-delete-cancel-evidence.json`.

## Native interrupted-write acceptance

Three deliberate `_Exit(86)` points now pass their independent recovery checks:

| Point | Native log | Evidence |
|---|---|---|
| Intent published, native writes not begun | `run-20261106-163310.log.err` | `logs/fighter-m3-interruption-intent-evidence.json` |
| First76-byte Options header successfully written | `run-20261106-163450.log.err` | `logs/fighter-m3-interruption-options-header-evidence.json` |
| First76-byte Story-profile header successfully written | `run-20261106-163631.log.err` | `logs/fighter-m3-interruption-profile-header-evidence.json` |

Each retains an uncommitted batch in its abandoned journal while the Store head,
native profile and extension remain the previous complete generation. The
original fixture is unchanged. These are expected failing native runs with a
verified injection marker, not ordinary successful gameplay or power-loss tests.
Their full harness reports are `logs/fighter-m3-interruption-*-native.txt`.
The fresh-session restart delegates the original Story/Options writes and
observes both complete write/close receipts before publishing one generation;
`run-20261106-163811.log.err` reaches `Game.StartMainMenu(3)`, reports64 two-second
samples (min107/median120/max120), zero native fault signatures, one verified
generation and identical save restoration. The native probe accepts the VY3
write. The outer driver's assertion incorrectly required a normal Story save
to leave profile bytes unchanged, so that original command **fails** and is
retained. Independent verification of the existing run proves the committed
VY3 and Options exactly equal their fresh native close receipts, FSC1 exists,
and all original fixture files equal the prior generation. Only profile payload
offset48 changes, from4 to10; its meaning is still opaque, so no field-schema
claim is made. `logs/fighter-m3-interruption-restart-evidence.json` records this
qualified restart acceptance. No repeat game run was needed.

## Native removed-pack reload

`logs/fighter-m3-removed-pack-native.txt`, native
`logs/run-20261106-161702.log.err`, passes the actual changed-pack run: Alpha is
absent, Beta first/second retain logical selections102/103 while their native
Character cores move from144/145 to142/143 and voice IDs from602/603 to600/601.
Both menu identities, **7/7 combat/result checks**, and two acknowledged Options
saves pass. The harness reports152 two-second frame samples, min106/median120/
max120, zero native fault signatures and byte-identical full save restoration.
Independent Store verification proves all historical bindings and prior marks
remain, including dormant Alpha first; Beta second gains its own progression.
Evidence: `logs/fighter-m3-removed-pack-evidence.json`. This run precedes the
new deletion/barrier hook; it accepts pack removal, not that later native code.

## Profile transactions with no active fighter packs

Journal/FUM initialization and native save/delete hooks now depend on the
configured profile transaction, independently of an active participant window.
The research driver accepts zero packs only in its explicit profile mode,
loads a valid empty name table and retains the complete historical bindings.
It emits no private-bank window and uses byte-identical original menus. The
isolated-root requirement and normal-profile activation gates remain in place.
Affected probe/journal tests pass **78/78**
(`logs/fighter-m3-retail-profile-unit.txt`); release build passes
(`logs/fighter-m3-retail-profile-build.txt`).

The created-profile check `logs/run-20261106-165037.log.err` signs in VY3, plays
the original created fighter99 against fully authored Beta second103, reaches
a decisive result and saves fresh VY3/Options records. The driver expected
Alpha second101, so its original identity assertion **fails** and is retained
in `logs/fighter-m3-created-profile-native.txt`. Independent checks of the
actual99/103 pair pass both immutable identity/materialization and **7/7 combat/
result checks**; committed files exactly match native close receipts. The
custom opponent uses Character core145/voice603, while the created fighter
retains its original core109 and native voice path. The profile payload changes
16 bytes in its leading362 bytes; field meanings remain opaque. Evidence is
`logs/fighter-m3-created-profile-evidence.json`. The harness reports105 two-second
samples, min108/median120/max121, no native faults, two verified generations and
identical save restoration. No repeat game run was needed for the input mismatch.

The same Store then passes a **zero-pack native Story save** with unlock-all
disabled: `logs/fighter-m3-all-disabled-native.txt`, native
`logs/run-20261106-165515.log.err`. Zero custom names and no participant window
are active; the runtime restores one dormant historical custom mark. VY3 loads,
exits Story normally, writes/closes both profile and Options, and returns to the
main menu. One new generation preserves the complete ledger, extension and six
profile files, including Beta second's dormant mark.64 two-second samples,
min107/median120/max120, no native faults and identical restoration.
`logs/fighter-m3-all-disabled-evidence.json` records the exact before/after heads.
Removing every fighter pack therefore no longer disables persistence or forces
a separate gameplay profile in this backend. Production launcher adoption is
still gated.

## Updated pack and two-player ready cancellation

`logs/fighter-m3-reenable-cancel-native.txt`, native
`logs/run-20261106-165833.log.err`, passes exact 102/101 identities and **6/6**
combat assertions, including movement and damaging hits from both humans.
The same Store used for Alpha removal now loads Alpha 1.0.1; its second fighter's
updated label is present in the compiled name table and visible in the reviewed
`0c81a17890d349919583ccf789f207d9/captures/versus-25s.png` combat capture under
`logs/fighter-window-runs`. Native menu events show
P1 selecting 101, `Fighters.KeepReady(0)` releasing readiness, P2 taking 101,
then P1 selecting 102 before the sole Game.StartGame. Both materialize their
correct immutable records. Historical bindings and all three prior custom
marks are unchanged. One acknowledged generation, 119 two-second frame samples
(min 102/median 120/max 121), no native faults and identical save restoration.
`logs/fighter-m3-reenable-evidence.json` records the checks. This run stops after
combat acceptance and does not claim a match result.

## Shared native-profile session backend and M4 contract

`setup/fighter_profile_session.py` now owns import-once, fresh workspace
materialization, matching extension restoration, pinned-generation verification
and clean-exit checks. The research probe calls this same backend. It rejects
overlapping source/Store/session roots and never reuses an abandoned journal.
A first-save test cannot reset an adopted Store. Focused session/probe/journal
tests pass **85/85** (`logs/fighter-m3-session-unit.txt`). The initial new test
fixture omitted native SaveMeta/image companions, so its save correctly remained
uncommitted; supplying those synthetic companions resolved the fixture failure.

This implements the approved native-profile-plus-versioned-extension route.
The test directory is isolation for acceptance, not a decision to require a
separate player identity or Story career for mods. M4 should adopt an existing
save into a Store once, preserve its source as a backup, and use that Store on
every subsequent managed launch, including zero active packs. Native writes go
to a new session workspace; only verified batches become the authoritative
generation. Do not copy an unverified working tree back over the source or
re-import the old source after a crash/deletion. Do not switch to the old source
when the final pack is disabled. Pack activation must finish validation before
session preparation. A stale session must reload, never silently overwrite.

M4 still owns the normal-profile adoption/recovery UI, launcher supervision,
whole-pack transactions and activation gates. The backend does not activate a
mod, relax the native research-root guard, or make normal-profile launches
production-ready. No fallback architecture or user decision is required by the
evidence so far.

The bounded native-profile audit identifies a verbatim 0x5904 payload copy from
`manager + profile_index*0x5950 + 0x1788` at 52B60/D23B0. The result coordinator
C3FF0 reaches C2F60 and the 15B80 profile updater, whose observed writes increment
stats at payload 9C/9E/A0/A2/A4 and AC+4*index. No transient selection/private-core
ID write is demonstrated in that updater. This is supporting evidence, not a
complete schema or proof about every indirect writer. Native reload acceptance
remains essential; opaque profile bytes are preserved rather than rewritten
using guessed field meanings.

## Signed-in authored player and subsequent retail-only Story reload

`logs/run-20261106-170332.log.err` signs in the same VY3 profile and selects
fully authored Beta second 103 as the human. CPU navigation selects retail
Crack 17 rather than the driver's expected Doc 55, so the original command in
`logs/fighter-m3-custom-profile-native.txt` **fails that identity assertion**.
Independent exact 103/17 immutable identity checks and **7/7** combat/result
checks pass; both VY3 and Options in the committed generation exactly match
their fresh native close receipts. Fifteen profile payload bytes change; the
rest remain unchanged. No repeat match was needed for the CPU expectation.
Evidence: `logs/fighter-m3-custom-profile-evidence.json`.

There are 126 two-second frame samples (min 100/median 120/max 121), no native
fault signatures, two acknowledged generations, results followed by native
Game.Quit, and byte-identical complete save restoration. The latest head is
`04c7c40a2ff7c717305057c4ce6d37c0e9cb8c84db4ad2933dc8a68fb45ea469`.
The subsequent zero-pack Story reload **passes** using this exact Store and the
newly extracted shared session backend: `logs/fighter-m3-custom-reload-native.txt`,
native `logs/run-20261106-170825.log.err`. VY3 enters the original Crib, exits
with save, writes and closes a complete VY3/Options batch, and reaches
Game.StartMainMenu(3). One acknowledged generation preserves all six files,
the complete ledger and Beta second's dormant mark. There are 64 two-second
frame samples (min 105/median 120/max 121), no native fault signatures and
byte-identical save restoration. Evidence is
`logs/fighter-m3-custom-reload-evidence.json`; new head
`0b666ebd9c85e798f06c4891d8b9bcb19b891fe9ddbe1fa0411dd8dfe12669e3`.

## Handoff after M3

- Local implementation commits: `a7edc85` stale-session/recovery protection,
  `dcf6477` dormant identity retention, `0d7d024` motion lifetime enforcement,
  `3f04b1f` native deletion and durable save acknowledgement, `1b0e216` real SDL
  detach/rejoin acceptance, `04d4ce9` zero-pack persistence, and `be4710c` shared
  session preparation. The Release binary contains the final native changes;
  later changes are the host session extraction, its tests and documentation.
- M4 can consume the shared session backend and the contract above. Wire the
  Fighters category, whole-pack installation/activation/update/rollback,
  restart and normal-profile adoption/recovery. Keep the current activation
  gates until that integration has its own acceptance. M4 has not been started.
- M5 remains authoring tools/documentation and ordinary-format Vendetta
  conversion. No compatibility-specific runtime was added in M3.
- M6 owns long-run resource/performance soak, physical controller/platform
  coverage, Windows/macOS/Steam Deck release checks and owner playtest. Two
  consecutive matches establish ownership/reuse, not an unlimited leak bound;
  SDL virtual detach/rejoin is not physical-driver coverage. Deliberate process
  termination tests do not establish power-loss durability on every filesystem.
- Retain qualified native script results above: incorrect opponent expectations
  were not relabeled as passing commands. Their actual match identities,
  combat/results and saved receipts were independently verified, avoiding
  redundant games. The owner-requested routine regression was not rerun.
