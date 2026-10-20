# Issue 67 and four-fighter performance at The Pit, macOS

Result: sustained four-fighter slowdown and sustained 25/30 Hz animation were **not reproduced** in the measured Mac fights. Four guarded runs completed, and the extra window/input-path check also stayed near 60 fps. This does not close either report or establish that they share a cause. Issue: <https://github.com/vyanhursky/DefJamFFNY-recomp/issues/67>.

The owner reports slightly sluggish four-player Free For All compared with 1v1 at The Pit, using v0.10.5, render scale 2, VSync on, windowed widescreen. Issue 67's reporter describes choppy animation in every mode and venue, resembling 25 fps; their platform and log are not available in the issue. They said they attached a log by email, but no attachment appears in the GitHub issue body or comments retrieved on 2026-10-20. These reports have not been established as the same fault.

## Setup and method

- Apple M1 Pro, 6 performance and 2 efficiency CPU cores, 14 GPU cores, 16 GB; macOS 26.5.2. The host reports its built-in display at 120 Hz. Low Power Mode is off and `pmset -g therm` reports no recorded performance/thermal warning.
- `posix-release`, v0.10.5 game sources, toolkit `32aab4d`. The checkout starts at `0c6c665`; its runtime sources match the v0.10.5 tag before local instrumentation. Rebuilt through `scripts/pipeline.py build` after the build-state guard rejected the previous stale binary.
- Scale 2, `RECOMP_ASPECT=16:9`, `RECOMP_PRESENT_VSYNC=1`, no replacement texture pack. Baseline window 1280x960 points, swap chain 2560x1920 pixels; render target 1708x960. The last run also uses the local saved 1800x1034-point window (3600x2068 swap chain) and the normal host input path. The existing Vulkan shader cache is loaded; this is not a cold shader-cache comparison.
- The harness guards the complete save root `/Users/vlad/Code/defjam-data/save`; runs are serial. `RECOMP_START_VENUE=19` selects The Pit at StartGame. Loading/start diagnostics, telemetry and captures verify the venue and fighter counts. The first two fighters are Blaze and Doc; FFA adds Trick and Crazy Legs. One scripted human player, the remaining slots CPU. The exact owner roster is still requested.
- The baseline recorder keeps frame times and game state with `RECOMP_RECORD_FPS=0`. A single screenshot 25 seconds after StartGame checks the scene; its read-back is a measurement disturbance. RNG seed override 12345; ordinary wall-time harness attack/movement script. These are not pinned replay/step-input runs.
- The comparison window starts one second after fight step 300, and lasts 30 seconds. This avoids loading, walk-in and the later state-7 transition described below in all four runs. Longer captures were retained too. FPS means presented frames recorded by the port, rather than physical panel scan-out or a subjective input-latency measurement.

## Measurements

| Run | presented fps | fight steps/s | frame p99 | evidence |
|---|---:|---:|---:|---|
| 1v1 baseline | 59.999 | 59.999 | 18.387 ms | `logs/run-20261020-122629.log.err`, session `20261020-122633` |
| FFA baseline | 60.001 | 60.001 | 17.383 ms | `logs/run-20261020-122945.log.err`, session `20261020-122948` |
| 1v1, animation probe | 60.002 | 60.002 | 18.602 ms | `logs/run-20261020-123419.log.err`, session `20261020-123422` |
| FFA, larger window, host input, pose/video probes | 59.966 | 60.000 | 17.739 ms | `logs/run-20261020-123905.log.err`, session `20261020-123909` |

All four have zero crash, watchdog, unresolved-call, debug-layer and truncated-batch signatures. All four restore the save root byte-identically. Each comparison window has one frame longer than 25 ms (the screenshot is inside the window); no sustained throughput loss appears. The triage tool's line-count-based "frames stopped" warning at a harness kill is not a measured hang: frame rows continue to the timed termination. The baseline two-second reports have median 120 presents. Native five-second `sample` profiles are in `logs/issue67/*.sample.txt`, outside the comparison window. The profiles contain substantial waiting in the executor's flip pacing; `work_ms` includes pacing/waits and must not be interpreted as game-CPU execution time.

## Simulation versus animation

The fight-step counter counts entries to `sub_00087700`, not presentation or every game-screen update. The static read in [the timing note](issue67-animation-timing-read.md) follows the queue, actor clocks and joint/model wrappers. The inspected path has no hard 30 Hz animation gate. The game's actor clock is floating point and advances during the fighter pass, independently of presentation.

A temporary, explicitly enabled local diagnostic samples each actor's animation clock at `record+0x9C`, speed, state, and a hash of the twenty joint positions at `+0xDC..+0x1CB` once per presented frame. It also records the CLogic state and screen-update counter. This is a read of current simulation memory on the renderer thread, so an occasional zero/two-step pair is not by itself proof that a rendered picture was repeated. The diagnostic's own timing effect must also be considered. The source patch is retained only under `logs/issue67/animation-probe.patch`; it was reverse-applied after the measurements and the normal build rebuilt. No runtime/renderer change is retained.

In the 1v1 probe's 60-second window, slot 0's clock changes in 2,990 sampled transitions and its joint hash stays identical in only 13 of those; slot 1 has 2,987 clock changes and 9 identical hashes. No consecutive stale-pose run with a changing clock exceeds one sample. That does not support a sustained 25/30 Hz actor-pose update in this run. It does not measure final mesh pixels or the physical display.

The FFA probe gives the same result: 3,060/3,056/3,057/3,051 changing-clock samples across the four actors, with only 31/12/16/6 identical joint hashes while the clock changes. The longest such run is two samples for slot 0, one for the others. These are not regular every-other-frame holds.

The final FFA also records each presented picture through a temporary 60-pictures/s recorder override, retaining five seconds before each automatic mark and three after. The ordinary-motion bundle has 480 pictures: 478 adjacent pairs have consecutive presented-frame numbers, and **none is an exact duplicate**. One frame-number gap is 2, at the screenshot. This whole-picture comparison cannot prove every individual actor moves on every frame, since the camera/crowd also move; the separate joint probe supplies actor-level evidence. Consecutive contact-sheet frames also show the moving fighters progressing. The two bundle reports find no hitch or picture anomaly. Read-back cost is about 1.69 ms per captured picture, recorded separately; this capture run is a confirmation, not the undisturbed performance baseline. Its `session.json` records the actual 60-picture recorder configuration; the normal settings snapshot still says `record_fps=0`, since this was a local override outside the settings table.

## The four-second counter pause

FFA baseline: fight step 3763 stays unchanged from session time 177.284 to 181.484 seconds (4.200 seconds), while presentation continues at 60 fps. A similar 4.183-second interval occurs in the instrumented 1v1, at step 3155, 143.354..147.538 seconds. In that interval, CLogic state is 7; the screen counter advances 252 times while actor clocks/joints and the fight counter remain unchanged.

This is a game state which bypasses the ordinary fighter pass: `sub_0008BE60` dispatches state 7 to `sub_00089BC0`, which does not call `sub_00087700`. State 6's `sub_00089B30` enters 7. Thus averaging the fight counter across this transition produces an apparent 55.8/56.7 steps per second, even when ordinary fighting on either side runs at 60. The last FFA capture identifies the state: **the normal Blazin' activation taunt/camera sequence**, with Doc's close-up and taunt while the ordinary fight clock stops. Its pictures keep changing. It is not evidence of a stalled input timer or a frozen renderer.

Local bundles (analysed with `scripts/bug-bundle.py` before viewing):

- `logs/sessions/20261020-123909/bundles/001-animation-motion-124122/`: ordinary combat, median 16.64 ms, p99 17.77 ms, zero hitches; includes `consecutive-frames.png`.
- `logs/sessions/20261020-123909/bundles/002-logic-state-7-124151/`: Blazin' activation, median 16.63 ms, p99 18.14 ms, zero hitches.

## Local reproduction artifacts

`logs/issue67/run.py` runs the guarded comparisons through the existing harness. `measure.py` and `poses.py` calculate the timing and pose summaries. Each run's JSON there holds its complete environment, build identity, input schedule, log/session paths, summary and save-restoration result. Screenshots, profiler output, sessions, video bundles and the temporary diagnostic patch stay local and must not be committed or uploaded.

The remaining questions are the owner's exact four fighters and a bundle marked just after the sluggishness, plus the issue reporter's log, platform and display settings. The normal host-input run emulates a keyboard player; physical controller latency and physical panel scan-out are not measured. Neither Windows nor a different refresh rate was tested. No performance fix is justified by these measurements, and the two reported symptoms remain open pending a captured reproduction.
