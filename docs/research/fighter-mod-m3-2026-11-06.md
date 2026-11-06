# Fighter Mod Support: M3 lifecycle and save reliability

The owner authorized continuing M3 here on 2026-11-06. Work remains local on
`research/custom-fighter-mods`, following M1/M2 commit `fe78f12`; no public push
or PR. Use the approved native-profile/versioned-extension approach first,
with isolated profiles as the approved fallback if the native boundary cannot
be made safe. Original saves remain outside experimental writes.

## Acceptance work

| Area | Status |
|---|---|
| Competing/stale save sessions | Fixed and focused tests pass; native caller now pins its materialized generation |
| Interrupted native writes and publication recovery | Fresh-session journal guard and five abrupt writer-death boundaries pass; native interruption acceptance pending |
| Pack disable/remove/update/re-enable | Real authored-resource compile/migration cycle passes; last-pack removal compiler bug fixed; native changed-pack reload pending |
| Repeated matches and resource ownership | Full M2 Alpha-pair to Beta-pair transition passes independent identity/combat checks; stronger ownership instrumentation added, native verification pending |
| Disconnect/rejoin and ready/cancel | Earlier selector evidence exists; match-lifetime acceptance pending |
| Story and created-fighter profiles | Native persistence field audit and integration acceptance pending |
| Native-profile extension integration | Research Store currently isolated; normal-profile transaction/recovery integration remains pending |

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
native run above and are not yet validated in-game. The release build passes
(`logs/fighter-m3-resource-release-build.txt`). Its ignored CMake cache had
dependency paths into a removed checkout; those now use the already fetched
pinned SDL3/ImGui source in this checkout. No toolkit revision changed.

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
