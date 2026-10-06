# Gameplay test harness: state and what is left

Updated 2026-10-05 by the Claude chat that took the work over from the Codex agent
(D67). The first stage was released as v0.2.2; v0.2.3 adds repeatable fights. The testing roadmap
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
- Repeatability is shown for thirty seconds of One on One at the Foundation only.
- Only One on One has reached the result path. The result code's meaning beyond
  "decisive" is not mapped.
- The session recipes and the visual-baseline workflow have never been used in a
  real run.

## Added in v0.2.3

- Step-timed input (`RECOMP_TEST_INPUT`, `--step-input`), pinned seeds for the match
  generator and the per-fighter AI generators (`--rng-seed`), and a recorded state
  stream a later run must reproduce (`--stream-out`, `--stream-expect`,
  `regress.py --only repeat`). Three replays reproduced thirty seconds exactly.
- A live negative control: an input file that never presses anything fails the
  movement, attack and damage assertions.
- A guard for the rare sound-library crash (`sub_0025FB7C` hand-written in
  `src/recomp_manual.c`); cause in `dsound-voice-list-crash.md`.
- Research: `fight-determinism.md`, `dsound-voice-list-crash.md`, and the v0.2.3
  section of `combat-telemetry.md`.

## Next, in order of value

1. **The audio chip model's trap handling** (toolkit, `src/apu/`): latch the first
   trapped method and voice, stop the frame's voice walk at a trap. This is the
   real fix for the sound-library crash; the guard only keeps the game alive.
   Audio is what Vlad praised after the rebase, so it needs his ear afterwards.
2. **Why a pinned fight can still part after about fifty seconds.** One pair did at
   step 3,121. Candidates not yet tested: audio capture being on, asynchronous
   loading, a generator not yet found. Sample every step around the divergence.
3. **Step-anchored captures**, then visual baselines for fights: with a repeatable
   fight a capture at a fixed step is comparable between runs. Still screens
   (crib, gym, menus) can be done now.
4. **Several matches in one launch.** After the summary the scripted presses reach
   the match-type menu again (`Game.Quit()` then `battle/cmtype`). Later matches
   take the match seed from the time-stamp counter, so pin it. Assert each match by
   its ordinal (`combat_checks(match=N)`).
5. **Sounds tied to events.** Needs a sample counter from the audio output so a
   damage event can be matched to a rise in level. Toolkit change.
6. **More coverage.** Four-fighter result, a human win (needs a better scripted
   fighter than button cycling), time-up, grapples, two pads, save and load,
   cutscene skipping, long sessions and repeated matches.
7. **The three-game upstream-release matrix** in the roadmap's second half is
   untouched and concerns other repositories.

## Working notes

- The worktree `C:\Users\Vlad\code\defjam-test-harness` was the branch's home; since the
  v0.2.2 merge the work is in the main checkout.
- Adding or removing a probe point (`sub_XXXXXXXX_enter`) needs `recomp.ps1` and a
  build; changing what a probe does needs only a build.
- A telemetry line must be written with one call: stderr is shared with every
  thread, and a line built from several writes had other output inside its JSON.
- Do not stop a regression mid-route: the copy-aside guard restores the save
  folder when the route ends. Scenario runs on a fixture do not have this problem.
- Research reports must not contain lifted code; describe and cite addresses.
