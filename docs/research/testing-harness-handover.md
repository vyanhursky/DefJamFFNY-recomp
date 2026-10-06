# Gameplay test harness: state and what is left

Updated 2026-10-05 by the Claude chat that took the work over from the Codex agent
(D67). The first stage was released as v0.2.2; v0.2.3 adds repeatable fights; v0.2.4 adds two pads,
four-fighter results, two matches in one launch and still-screen baselines. The testing roadmap
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

## Added in v0.2.4

- Route `ffa-result` and assertion `combat.eliminations`: a four-fighter match to
  its result, every fighter but the winner put out once.
- Route `versus` and assertion `combat.two_players`: two emulated pads
  (`RECOMP_USB_PADS=2`, `p2-` presses) join, pick fighters, walk and land hits. In
  the full regression.
- Route `two-matches`: a One on One, back through summary and menus, then a Free
  For All, each judged by its match ordinal. `anchor#N` in a pad script waits for
  the Nth call; an anchor must not contain a comma (the script splits on them).
- `--step-shots`: captures at a fight step (`RECOMP_TEST_SHOT_STEPS`).
- Reviewed still-screen baselines for `story-tour`, kept in the data folder under
  `test-baselines/`; `regress.py --only visual`.
- `[TEST-SEED]` logs every seeding of a generator of the game's common kind.
- `RECOMP_TEST_DRAWS=1`: `[TEST-DRAWS]`, the count of draws from every generator by
  calling site at setup and at steps 1, 300 and 900, with the game's screen-update
  count. It found the two crowds.

## Next, in order of value

1. **The audio chip model's trap handling** (toolkit, `src/apu/`): latch the first
   trapped method and voice, stop the frame's voice walk at a trap. This is the
   real fix for the sound-library crash; the guard only keeps the game alive.
   A to-do, not scheduled (backlog 1b, D70); audio needs Vlad's ear afterwards.
2. **A repeatable loading window** (`crowd-nondeterminism.md`). Two crowds start
   animating while the match loads: the background one (`sub_000DB870`, C runtime
   `rand`) and the 3D spectators (`sub_0007D2F0`, generator `0x375F68`). The window is
   906 screen updates in every run and every seed is identical, yet the background
   crowd's update ran 902 or 903 times and the spectators drew a different number
   of values. The spectators push fighters, so this is also the likely cause of
   pinned fights parting (step 871 in three pairs, 3,121 once before). Find what is
   host-timed inside the window (disc loads are the first suspect) and make it land
   on the same update in test mode; equal `[TEST-DRAWS]` counts at step 1 are the
   test. Clearing the crowd's update flag crashes; copying and restoring the
   background crowd alone changes nothing visible.
3. **Until then the `replay` golden can fail by chance.** If it starts to, shorten
   the window (`--stream-steps`) rather than loosening the comparison.
4. **Sounds tied to events.** Needs a sample counter from the audio output so a
   damage event can be matched to a rise in level. Toolkit change.
5. **More coverage.** A human win (needs a better scripted fighter than button
   cycling), time-up, grapples as such, save and load, cutscene skipping, long
   sessions, three and four pads. The result codes of a Free For All are not
   mapped: eliminations were seen as 32 then 9 in one match and 32 then 8 in
   another, with 33 or 9 on the decisive one.
6. **The three-game upstream-release matrix** in the roadmap's second half is
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
