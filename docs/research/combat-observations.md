# Read-only combat observations

2026-10-05, testing worktree; verified USA dump from the repository manifest.

`RECOMP_TEST_OBSERVATIONS=1` enables four universal lifter entry hooks in
`src/recomp_manual.c`. The implementation is `src/hooks/test_observations.c`.
Re-lift after changing entry hooks. Normal play leaves them disabled. The probes
read guest state and write diagnostic JSON to stderr; they never change guest
memory, registers, flags or the stack, or call a guest function.

| Hook | Evidence |
|---|---|
| `001A4A30` | Counts entries into the routine that iterates the four fighter records. This is an **update-entry counter**, not certified simulation-frame timing. Its body can return early on state flags. |
| `001A5DD0` | Hit-resolution invocation: cdecl arguments 1/2 are attacking/defending records. A call alone does not prove damage or a player attack. |
| `001A50B0` | Captures the defender's health immediately before its update. |
| `001A6870` | Notification `0x3d` follows the health write inside `001A50B0`; reports the same record's before/after values. |

The four records start at `003B92E0`, stride `0x12e8`; only those exact pointers
are accepted, preventing diagnostic reads through arbitrary guest pointers.
The routine uses record `+0x28` as the slot index. Health is float `+0x350`,
maximum `+0x354`; the HUD notification consumes their ratio. `+0x358` is an
additional health limit used by the update. Its full gameplay meaning is not
claimed. Zero health does not establish KO: the match reason/state must be mapped.

Live evidence: `logs/run-20261005-204938.log.err`, retained in
`logs/scenarios/fight-terrordome-20261005-204936/`. The front end requested
One on One, fighter IDs **56/55**, venue **6**, then `Game.StartGame()`.
Two CPU-slot-1 hit resolutions were followed by slot-0 decreases:
**265.600006 → 249.577515**, then **258.600006 → 246.211014**. Recovery writes
were also observed. These prove the hook pair sees health changes; they do not
prove controlled-player attack causality, canonical fighter names or a KO.

This run crashed after roughly 16 seconds of presentation evidence at the
already-known `sub_001B54D0+0xFA2` corruption site. The runner returns failure
and does not suppress that fault. No 60-second fight capture was produced.

`[TEST-OBSERVATION]` records have `kind`, `update`, `host_ms`, slots, callers and
health values. `test_evidence.health_observations` links a decrease only to a
preceding hit for the same update/defender. `--observe-combat` requires at least
one linked decrease, but it remains a diagnostic gate. It **cannot satisfy**
`--require-combat`, whose `[TEST-EVENT]` contract requires scenario/frame and
movement/attack/damage/KO/results/menu evidence. Synthetic native tests verify
read-only behavior, invalid pointer rejection, disabled output and exact pairing.

Next research targets:

1. Read the caller `00087700` and the early-return flags in `001A4A30`; identify
   the actual simulation step and verify pause/slowdown behavior before naming
   any counter a simulation frame. Presentation/USB/host clocks are insufficient.
2. Map positions and fighter identity from the four records against real play.
   Do not assume `+0x30` is a fighter ID: nearby routines use it as a move/code.
3. Map the match-end reason, winner and results state. Front-end screens
   `battle/matchSm*`, `battle/reward*`, `battle/rematch` are useful boundaries;
   they alone do not prove a KO or player victory.
4. Associate the controlled slot's sampled frame inputs with movement/attack,
   then damage of its intended target. Preserve all actors/scenario identities.
5. Add a native PCM sample ledger for precise speech/hit alignment. Current host
   log/PCM offsets have polling uncertainty and capture pre-submit samples.

No guest bodies, game assets, saves, captures or PCM belong in this document or Git.
