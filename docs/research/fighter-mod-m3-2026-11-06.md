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
| Pack disable/remove/update/re-enable | Existing prototype preserves dormant stable identities; authored-pack lifecycle acceptance pending |
| Repeated matches and resource ownership | M1 appearance-only repeat evidence exists; full M2 behavior/resource rebinding acceptance pending |
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

## Audit follow-ups

- Resource bindings are process-lifetime data; native motion sources,
  cinematic caches and paired-provider metadata have narrower lifetimes.
  Repeated-match testing must establish teardown before registration, voice
  selection refresh, and correct ownership after changing selected fighters.
- The profile Store currently commits completed records as updates; native
  profile deletion needs an explicit witnessed removal path before normal
  profile lifecycle can be declared supported.

M3 is in progress. Launcher integration and release acceptance remain M4/M6.
