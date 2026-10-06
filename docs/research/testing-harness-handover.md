# Gameplay test harness: state and what is left

Updated 2026-10-05 by the Claude chat that took the work over from the Codex agent
(D67). The first stage is merged and released as v0.2.2. The testing roadmap
(`docs/08-testing-roadmap.md`) is **not** complete; its checklist carries the
status of every item. How to run what exists is in `docs/09-testing-harness.md`.

## What exists

- `scripts/scenario_suite.py`: one launch, many assertions, a JSON/JUnit/HTML
  report under `logs/scenarios/`. Runs on a throw-away copy of a hashed save
  fixture, never on the save folder.
- `scripts/test_evidence.py`: the assertions. Combat from game state
  (`combat_checks`), audio health, frame pacing, memory growth, image comparison
  against locally approved baselines, fixture and environment identity, reports.
- `src/hooks/test_telemetry.c`, `test_observations.c`: read-only probes behind
  `RECOMP_TEST_OBSERVATIONS=1`, attached with lifter entry hooks in
  `src/recomp_manual.c`. They emit `[TEST-EVENT]` and `[TEST-STATE]`.
- `scripts/harness.py`: routes `fight-result` (plays to the match summary) and
  `story-tour` (crib and gym in one launch), memory sampling, run identity.
- `scripts/regress.py`: twelve checks in the full run, including the four-fighter
  Terrordome match and `combat`; `--quick` is unchanged.
- `scripts/session_driver.py` and `tests/scenarios/*.experimental.json`: live
  input driven by screen events. Unit-tested, never calibrated in a real run.
- Research: `simulation-tick.md`, `match-end-state.md`, `fighter-record-fields.md`
  (code reads by sub-agents, to be treated as leads) and `combat-telemetry.md`
  (what live fights confirmed and corrected).

## Verified

- Unit tests: 157 pass with MSVC on PATH; without a compiler the native ones skip.
- Live, Release, on fixture `logs/fixtures/vy2-hour-v1`: `fight` with audio gates
  and probes; `story-tour`; `ffa-terrordome` for four minutes with probes;
  `fight-result` with `--require-combat`, all seven combat assertions passing on a
  fight played to a knockout.
- The full regression on Release: see the work log entry for v0.2.2 in
  `PROGRESS.md` for the run and its numbers.

## Not verified, and known limits

- Debug has not been run with the probes.
- The frame-pacing and memory assertions have run in one fight each; their limits
  are first guesses from healthy runs.
- `--rng-seed` is implemented and unit-tested; no live run has used it.
- Only One on One has reached the result path. The result code's meaning beyond
  "decisive" is not mapped.
- The session recipes and the visual-baseline workflow have never been used in a
  real run.

## Next, in order of value

1. **Repeatable fights.** Scripted input is timed in host seconds
   (`xbox_ScriptSeconds` in the toolkit's `kernel_path.c`, used by
   `usb_gamepad.c`), so the same script plays a different fight each time. Give
   the pad script a clock the host can supply and drive it from the fight step
   (`step` in the telemetry, 60 a second). That is a toolkit change on
   `defjam/m6`. Then check whether two runs with the same seed and the same
   step-timed input produce the same event stream; the seed was already identical
   across three runs.
2. **A live negative control.** Run `fight-result` with the player's input removed
   and confirm `combat.movement` and `combat.attack` fail. Unit tests cover this
   with altered event streams only.
3. **Several matches in one launch.** After the summary the scripted presses
   reach the match-type menu again (`Game.Quit()` then `battle/cmtype`). Use the
   session driver to play One on One, return, then a Free For All, and assert
   each match by its `match` ordinal (`combat_checks(match=N)`).
4. **Visual baselines for still screens.** Crib, gym, menus: generate candidates,
   review, approve, and measure run-to-run differences to set tolerances. Fights
   need step-anchored captures first.
5. **Sounds tied to events.** Needs a sample counter from the audio output so a
   damage event can be matched to a rise in level. Toolkit change.
6. **More coverage.** Four-fighter result, a human win, time-up, grapples, two
   pads, save and load, cutscene skipping, long sessions and repeated matches.
7. **The three-game upstream-release matrix** in the roadmap's second half is
   untouched and concerns other repositories.

## Working notes

- The worktree `C:\Users\Vlad\code\defjam-test-harness` was the branch's home; after
  the merge the work continues in the main checkout.
- Adding or removing a probe point (`sub_XXXXXXXX_enter`) needs `recomp.ps1` and a
  build; changing what a probe does needs only a build.
- A telemetry line must be written with one call: stderr is shared with every
  thread, and a line built from several writes had other output inside its JSON.
- Do not stop a regression mid-route: the copy-aside guard restores the save
  folder when the route ends. Scenario runs on a fixture do not have this problem.
- Research reports must not contain lifted code; describe and cite addresses.
