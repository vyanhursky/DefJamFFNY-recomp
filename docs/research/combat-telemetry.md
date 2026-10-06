# Combat telemetry: what the probes read and what was confirmed

2026-10-05, test worktree, verified USA dump, Release build. The probes are in
`src/hooks/test_telemetry.c` (with `test_observations.c`) and are off unless
`RECOMP_TEST_OBSERVATIONS=1`. The addresses came from three code reads
(`simulation-tick.md`, `match-end-state.md`, `fighter-record-fields.md`); this note
says which of those claims a live fight confirmed, corrected or left open. No guest
code, assets, saves or captures belong here.

## Hooks

Lifter entry hooks in `src/recomp_manual.c` (re-lift after adding or removing one):

| Function | Used for |
|---|---|
| `sub_00087700` | one simulation step of a live fight; the `step` counter |
| `sub_001A4D90` | match set-up: restarts `step`, bumps the `match` ordinal |
| `sub_001BC690` | seeding of the match's random number generator |
| `sub_001A6A80` | the result recorder: winners list, losers list, 16-bit code |
| `sub_001A5DD0` | hit resolution (attacker record, defender record) |
| `sub_001A50B0`, `sub_001A6870` | a defender's health before and after an update |
| `sub_001A4A30` | per-update loop entry (the older `update` counter) |

## Confirmed in live fights

Runs: `logs/scenarios/fight-result-20261005-22*` (three One on One fights at the
Foundation, two played to a knockout) and `fight-20261005-214201`.

- **Step rate.** 17,320 steps in 288.6 s of host time, and 10,498 in 175 s: 60.0
  steps a second. The game's own round clock read 5:46 at step 17,320, 1.2 clock
  seconds per real second, which matches the long-standing "1.2 ticks a step" note.
- **Phase** `0x3B8F30`: 0 at the first step, 1 while fighting, 2 then 3 after the
  result. This is what `match_over` uses.
- **Flag word** `0x3B9054`: `0x1` at the first step, `0x2` during the fight, `0x6`
  after the result. Bit `0x04` is the end-of-fight slow motion: the time scale at
  `0x3B8F2C` dropped to 0.14 and ramped back to 0.5 while it was set.
- **Fighter records.** Spawn positions (-25, 0, 0) and (25, 0, 0) facing 90 and
  -90 degrees; `+0x44`/`+0x4C` then change smoothly as the fighters walk.
  `+0x937` bit 0 was 0 for the scripted player in slot 0 and 1 for the CPU.
  `+0x350` fell from the maximum at `+0x354` to 0 for the loser.
- **Buttons.** With the script holding d-pad right and cycling X, Y, A, B, the
  held word at `+0x9E0` showed bit `0x8` with each of `0x10`, `0x20`, `0x40`,
  `0x80`: `0x8` is right and the four action bits are the four face buttons.
  Which bit is which button was not pinned down.
- **Attack to damage.** Every one of 84 hits by the player resolved within 30
  steps of an action press, and the first was followed one step later by a health
  decrease of its target.
- **Result.** `sub_001A6A80` fired once per fight with code 33 (`0x21`: the
  decisive bit plus `0x20`), winners `[1]`, losers `[0]`, the loser at zero
  health. `0x3B8F40` then held the same winner slot.
- **Results screen.** The front end calls `Game.GetMatchSummary(0)` after the
  result; `battle/matchSm` never appears as a `GetScreenInfo` call, so that is
  the anchor to use.

## Corrected

- Bit `0x08` of `0x3B9054` is **not** set by a One on One knockout. The code read
  called it "match decided" with medium confidence; it stayed clear.
- Record `+0x2C` is **not** the fighter ID minus one. The front end requested IDs
  56 and 55 and the records held 4 and 9. It is reported as `character` and not
  compared with the requested IDs.
- Distance from the spawn point is not movement: the first `movement` events
  reported 14 to 29 units in one step, because the game repositions the fighters
  when the walk-in ends. Movement is now path length accumulated in steps of at
  most one unit while a direction is held and the phase is 1.

## Open

- What result code `0x20` means (knockout, as opposed to another way of losing)
  is inferred from the loser's zero health, not read from the code. Time-up,
  ring-out, draws and team results have not been observed.
- The random number generator's seed was 124866453 with increment 942483619 in
  all three runs, so the time-stamp value it is taken from is the same every
  start in this runtime. The fights still differed (knockout at step 17,320 and
  at 10,498), so something else varies: scripted input is timed in host seconds,
  not steps. `RECOMP_TEST_RNG_SEED` can replace the seed; that it changes play has
  not been shown.
- One audio buffer is dropped in the slow motion just after the result, in both
  fights that reached one. Not investigated.
- Four-fighter matches, a human winner, and a second match in one process have
  not been run through the result path.
- A hit by a human fighter is tied to the most recent action press by step count
  only. Which move it was, and that the damage came from that hit rather than
  another in the same step, are not established.
