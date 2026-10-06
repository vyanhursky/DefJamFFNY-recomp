# Gameplay test harness

How to run the scripted gameplay checks and read what they prove. The roadmap
behind this is [08-testing-roadmap.md](08-testing-roadmap.md); what is still
missing is listed at the end and in the
[handover](research/testing-harness-handover.md).

Everything here needs a local build made from your own dump. Hosted CI has no
game data and runs only the unit tests. Captures, audio and reports are the
game's artwork and stay under `logs/`, which git ignores.

## Three levels

| Command | Time | What it is for |
|---|---|---|
| `python scripts/regress.py --quick` | about 10 min | after every change: unit tests, three golden frames, one fight |
| `python scripts/regress.py` | about 50 min | before a commit that touches the runtime, renderer or generated code |
| `python scripts/scenario_suite.py run <route> ...` | one launch | one scenario with all its evidence and a browsable report |

Never run two of these at once: they share the save area, the window and the
frame-rate measurements.

The full regression is the quick one plus a four-fighter Free For All, the same
at the Terrordome for four minutes, the **combat check**, the Story intro, crib,
gym and a boot soak. `--only a,b` picks checks; `fight-terrordome` is selectable
that way only.

## The combat check

`python scripts/regress.py --only combat`, or directly:

```powershell
python scripts/scenario_suite.py run fight-result --fixture logs/fixtures/NAME --require-combat
```

It plays a One on One until the game asks for the match summary and asserts, from
the game's own state rather than from the picture:

| Assertion | Proves |
|---|---|
| `combat.setup` | the match started with two fighter records, one human-controlled |
| `combat.movement` | the player's fighter walked two units while a direction was held |
| `combat.attack` | a hit by the player's fighter resolved within a second of an action press |
| `combat.damage` | that hit's target lost health within a few simulation steps |
| `combat.result` | the game recorded exactly one decisive result with a winner and a loser, and its "decided" phase named the same winner |
| `combat.results_screen` | the front end requested the match summary after that |

A fight that renders but ignores the pad, or never causes damage, or never ends,
fails. With no telemetry in the log the check is `blocked`, which is a failure,
never a skip. It does not prove which move was performed or why the fight ended;
[combat telemetry](research/combat-telemetry.md) says exactly what was confirmed
against live fights.

The same run also asserts audio health, frame pacing and memory growth (below).

## Scenario reports

Each `scenario_suite.py run` writes `logs/scenarios/<route>-<stamp>/` with
`report.json`, `junit.xml`, `index.html`, the game log, captures, an audio preview
and any image differences. The report records the source and build identity, the
machine and GPU driver, the fixture's hashes, the settings, the input schedule and
which gates were selected. A gate that could not be evaluated is an error.

Routes: `fight`, `fight-result`, `ffa`, `fight-terrordome`, `ffa-terrordome`,
`story-tour` (crib and gym in one launch), `intro`, `crib`, `gym`, `boot`, `unlock`.

Options:

- `--require-combat` the combat assertions above (the result part only on
  `fight-result`, which plays to the end).
- `--observe-combat` record the telemetry without requiring it.
- `--no-audio` / `--audio` fight routes check audio by default.
- `--baselines <manifest>` compare captures with locally approved images.
- `--rng-seed N` replace the seed of the match's random number generator.
- `--settings file.json` render scale, gamma and vsync for the run.
- `--session-plan file.json` experimental: live input driven by screen events.

## Save fixtures

A scenario never runs on your save folder. It runs on a throw-away copy of a
*fixture*: a small folder holding profiles and options with a hash of every file.

```powershell
python scripts/scenario_suite.py fixture --source C:/LOCAL/prepared-save --output logs/fixtures/NAME --profile "who and how far"
```

The regression's combat check makes one automatically from `save/UserData` in the
data folder (a few hundred kilobytes; the gigabytes of cache are left out and the
source is only read). Menu navigation depends on the profiles: how many there are,
their progression and unread messages. A route calibrated for one profile list is
not guaranteed on another.

The other regression checks still use the whole save folder with the copy-aside
guard, which is why they are slower. Do not stop one mid-run: the guard restores
the saves when the run ends.

## Audio, pacing and memory

- **Audio.** The generated PCM must be long enough, not clipped and not silent,
  and the device queue must not run dry. Dropped buffers are allowed at one per
  five minutes, plus one when a result was recorded: both fights played to a
  knockout dropped exactly one buffer in the slow motion after it. PCM is captured
  before it reaches the device and is aligned to events only to within the log
  polling interval, so it cannot check that a particular sound played.
- **Frame pacing.** From the runtime's two-second reports during the fight: the
  median present interval within 1 ms of 16.67, and at most 2 percent of presents
  later than 1.5 times their window's median.
- **Memory.** The game's private bytes, sampled every five seconds, must not have
  grown more than 64 MB from the start of play to the end of the run. This catches
  a fast leak; one fight is too short for a slow one.

## Visual baselines

```powershell
python scripts/scenario_suite.py baseline-candidates --report logs/scenarios/RUN/report.json --output logs/baselines/NAME
```

copies a run's captures and a manifest with `approved: false`. Look at each image,
set `approved` only for the ones that are right, and pass the manifest with
`--baselines`. Approval is locked to the image's hash. Nothing is approved
automatically, and fights differ from run to run, so this suits still screens.

## Game-state telemetry

`RECOMP_TEST_OBSERVATIONS=1` (set by `--require-combat` and `--observe-combat`)
turns on read-only probes that write `[TEST-EVENT]` and `[TEST-STATE]` lines:
match start, fighter positions, health, buttons, hits, damage, the result. `step`
in those lines counts the game's simulation steps, 60 a second in a fight. Normal
play leaves the probes off. Adding or removing a probe point needs a re-lift.

## Not done

- Input is scheduled in host seconds, not simulation steps, so two runs of the same
  script play different fights.
- The random number generator can be seeded but repeatability has not been shown.
- No visual baseline is approved; tolerances are examples.
- Sounds are not tied to events (hit effects, the announcer).
- Only One on One has been played to a result. Four-fighter results, a human win,
  time-up, several matches in one launch, two pads, save and load, and cutscene
  skipping are not covered.
- The live-input session recipes in `tests/scenarios/` are uncalibrated examples.
- Long sessions and repeated matches are not measured.
