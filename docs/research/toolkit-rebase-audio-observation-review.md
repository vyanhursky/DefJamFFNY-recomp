# Toolkit rebase audio observation review

2026-10-03. Read-only review of preserved `tools/xboxrecomp/src/apu/apu_core.c`
and `apu_xaudio2.c` versus `logs/rebase-work/migration/src/apu/`, plus only the
audio evidence in baseline `run-20261003-125958.log.err` and candidate
`run-20261003-173948.log.err`. No runtime edits, builds, game runs, generated C
reads or elevated tools were used. The procedure below is proposed additional
measurement; it was not performed by this audit.

## What the two logs prove

Both runs report:

| Evidence | Baseline | Candidate | Meaning |
|---|---|---|---|
| XAudio2 initialized | 48,000 Hz, stereo, signed 16-bit, three 1,024-frame buffers | Same | Creation/start calls succeeded at initialization. It does not establish sample submission or audible sound. |
| APU started by title | SECTL `0000000F`, FECTL `0000100F` | Same | Guest enabled its audio engine state. |
| Derived GP doorbell | `831F8810` | Same | Scratch-table/address path reached the expected command word. |
| Command acknowledged | `00000003` | Same | Stub DSP handshake completed. This is not evidence of full DSP effects processing. |
| First logged voice starts | `40`, `41`, `42`, `43`, `FA`, `F9` | Same | Voice start commands reached the model. These are budgeted messages, not a complete voice count. |
| Later APU interrupts | First five logged deliveries claimed by ISR | Same | Guest interrupt handling was reached. These are capped messages, not total interrupt counts or proof that all voices completed. |

The logs also open audio asset paths. That alone does not establish decoded
sample content, mixing, output gain, pacing or playback. Neither run contains
`[APU] output peak`, `[APU] status`, or XAudio2 shutdown submission totals. In
particular, **absence of drop/starvation lines does not mean zero drops or zero
starvation**. These runs establish similar initialization/handshake activity,
but do not establish audio parity or even non-zero output samples.

## Existing observation options

Candidate navigation:
[apu_core.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/apu/apu_core.c:342),
[apu_xaudio2.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/apu/apu_xaudio2.c:133).

| Option | Observation and limits |
|---|---|
| `RECOMP_APU_LEVEL=1` | Enables `[APU] output peak ... voices ... SECTL ... FECTL ... buffers dropped ... device ran dry ...`. Also enables periodic voice/routing diagnostics. Presence enables it; `=0` still enables it. |
| `RECOMP_APU_PCM=<absolute file>` | Writes the accumulated mix as raw 48 kHz, stereo, interleaved signed 16-bit little-endian PCM on Windows. Four bytes per stereo frame, 192,000 bytes per generated audio second. No WAV header. Uses `fopen(...,"wb")`, so choose a new path. Open/write failure is not reported: independently check that the file exists and grows. |
| `RECOMP_APU_TRACE=<n>` | Optional APU status/voice report every five wall-clock seconds: frame-loop count, active pipeline, cumulative notifications and ISTS/IEN/FECTL/SECTL. Default presence yields twelve reports; values greater than one select the report limit. `=0` enables the default too. This is not the peak/drop/starvation switch. A twelve-report limit can expire before a fight starts. |

The peak and counters are printed after **187 chunks of 256 frames**, from
integer `48000 / 256`, approximately 0.9973 seconds of generated samples.
They are not guaranteed to represent one wall-clock second when processing
falls behind. The peak is the maximum absolute sample across both channels
before host submission; a non-zero peak proves non-zero mixer output during
that sample interval. It does not identify which voice contributed it or prove
that speakers reproduced it.

`buffers dropped` counts `xa2_submit_samples` calls that found at least three
buffers already queued and returned without submitting. `device ran dry`
counts submissions that found zero queued buffers after at least one prior
successful submission. Both reset after each printed level report. They are
event counts, not lost sample duration. Initial empty-queue startup is excluded.
A failed XAudio2 `SubmitSourceBuffer` HRESULT returns zero without incrementing
these counters, so they are not an exhaustive output-error metric.

PCM is written **before** the XAudio2 submit attempt, whose return is ignored
by the monitor. Consequently, the capture can include audio blocks dropped by
the host queue; PCM without device counters cannot demonstrate uninterrupted
playback. The static PCM file has no explicit flush/close here, and the harness
terminates the process at the bound, so a buffered final tail can be lost.
Analyze complete four-byte frames and tolerate that bounded capture-tail issue.
These options are in the active-XAudio2 monitor branch; they do not provide the
same observations if the run falls back to waveOut.

## Source comparison

`apu_xaudio2.c` has no content differences between preserved baseline and
candidate. The 256-frame accumulation, 1,024-frame submissions, peak reporting,
counter reset and PCM capture logic in `mcpx_apu_monitor_frame` are unchanged.
The measurements are therefore comparable when enabled identically.

Candidate changes elsewhere in `apu_core.c` include atomic physical cache/IRQ
access, polling the DSP handshake independently of the active pipeline,
post-frame interrupt-line update and releasing/yielding/reacquiring the APU
lock each frame. Guest APU ISR execution still belongs to the kernel timer.
These source changes make output/pacing observations useful, but the two
ordinary logs do not quantify their effect. Synthetic mixer results and source
coverage cannot substitute for a live sample/counter comparison.

## Minimal bounded extra Release capture

After the current Debug regression and save restore finish, run one serial
Release fight using the existing harness stages, stopping **60 seconds after
`game.startgame(`**, with a 420-second total ceiling. This uses the same fight
clock as the established first fight capture, while halving the ordinary
route's 120-second fight observation. Disable screenshots for this audio run;
enable only LEVEL and PCM initially. No native-stack sampling, test tone,
mute/gain/routing override or runtime change is needed.

The following is a recipe for the main agent to execute in the established
Python environment from the repository root; this audit did not execute it:

```python
import sys, time
from pathlib import Path
sys.path.insert(0, 'scripts')
import harness as h

snapshot = Path('logs/rebase-work/baseline-path.txt').read_text(
    encoding='utf-8-sig').strip()
data = Path(snapshot) / 'runtime-data'
assert data.is_dir()
pcm = Path('logs/rebase-work/audio-candidate-release-fight-'
           + time.strftime('%Y%m%d-%H%M%S') + '.pcm').resolve()
r = h.ROUTES['fight']
run = h.run_game(
    'audio-rebase-fight', preset='win-x64-release', stages=r['stages'],
    tail=r.get('tail', ''), shots='', secs=420,
    until=r['until'], after=60,
    env={'DEFJAM_DATA': str(data), 'RECOMP_APU_LEVEL': '1',
         'RECOMP_APU_PCM': str(pcm)})
if not h.reached(run.summary, r['until']):
    run.missing_anchor = r['until']
print('PCM:', pcm)
sys.exit(1 if h.run_faults(run) else 0)
```

The child uses the already preserved **disposable** `runtime-data` root,
not `C:/Users/Vlad/code/defjam/save`. `run_game` protects and restores its entire
save/cache tree for every route, including fights, and reports restore equality.
The harness also checks its current build manifest and the normal fault policy.
Do not run this while another game/save guard is active. PCM and run logs remain
ignored local artifacts. The hard ceiling bounds PCM to approximately 81 MB
at real-time generation, rather than starting an open-ended recording.

Record the game-start anchor, fault/save-guard result, non-zero peak intervals,
zero-peak intervals, drop/starvation counts after startup, and capture size.
For complete PCM stereo frames calculate duration, per-channel peak/RMS,
zero-sample proportion and full-scale sample count. A recent tail segment can
provide a compact fight observation, but label the segment and avoid claiming
sample-accurate alignment with the game-start log. Expected intentional pauses
should not be treated as failures merely because an interval is silent.

The existing baseline log has no level/capture metrics. A candidate capture
can establish live output activity and observed device health; **numerical
baseline parity requires the same capture recipe on the preserved baseline
executable**, serially, with its compatible pipeline snapshot and the same
disposable saves. A raw PCM hash is unsuitable as a parity gate because game
timing and mixed voice phases vary between runs. Compare comparable fight
sections, levels, continuity and counters, not byte identity.

Listening parity remains separate: automated peaks/PCM/counters cannot establish
correct music, speech, pitch, effects, speaker balance or perceptual fidelity.
Vlad's listening/play-test is still needed before declaring audio parity.

## Parent measurement closure

The final extra Release fight observed its normal 120-second fight window with
LEVEL and PCM enabled. `run-20261003-202450.log.err` and
`logs/rebase-work/final-artifact-review.json` record 121 post-game-start level
reports, 120 with nonzero output, zero dropped buffers and zero dry-queue events.
Whole-run reports retain ten dry-queue events in the first six reporting intervals
before game start; no numerical baseline comparison is available. The 56,815,616-byte
stereo PCM has nonzero output in both channels and zero full-scale samples.
The complete measurements, save verification and owner listening gate are in
`toolkit-rebase-acceptance.md`. Captures/PCM were kept local and never committed.

## Owner listening closure, 2026-10-04

Vlad played the Release build and reports that audio is much better than before,
frames are smooth and he observed no graphical glitches. He accepts the experience
(D56); private PR #1 is merged. This closes the owner listening gate while the
measurement limits above remain: no numerical baseline or exhaustive fidelity
comparison was recorded.
