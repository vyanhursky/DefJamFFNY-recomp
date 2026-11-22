# Learn Moves row backgrounds (#181)

The grey/light row backgrounds agree with a historical Xbox reference. The
pre-#151 port baselines omitted them because the runtime rejected thin DXT
textures. Preserve the upload repair and review the affected local baselines.
This is a baseline correction, with no game or toolkit behavior change.

## Independent reference

Mark Ryan Sallee's IGN guide, mirrored as
[Def_Jam_Fight_for_NY_User_Manual.pdf](https://www.ogxbox.co.uk/media/com_eshop/attachments/Def_Jam_Fight_for_NY_User_Manual.pdf),
PDF page 35 (one-based), contains a Learn Moves screenshot immediately above
"FIGHT STRATEGIES". Despite the mirror's filename, this is a strategy guide,
not an EA instruction manual. The screenshot has Xbox A/B/X prompts and shows:

- a grey background behind the unselected LOCKED row;
- light backgrounds behind other unselected move rows;
- an orange background behind the selected move.

The inspected PDF SHA-256 is
`8dd645939389de35c79dd2d7d15c389c95b2faddcc6172445ecc94c715780513`.
This is visual reference evidence for the presence and meaning of the bars;
the small historical image cannot establish pixel-exact colours, alpha or
filtering. No new console hardware test is claimed. The PDF and its artwork
remain outside the source tree.

## Original failure retained

[Issue #181](https://github.com/vyanhursky/DefJamFFNY-recomp/issues/181) records
the Windows v1.0.0 candidate's exact-fixture comparison: crib passed, while
Learn Moves at 13 s and 23 s differed by 5.1%/6.1%, MAE 2.83/3.35. Those
failures remain failures against the older approved images.

The [original texture investigation](graphics-enhancements-windows-2026-11-01.md#validation-limits)
also retains its earlier comparison failures and the matched-profile retest.
Re-approving corrected images does not turn those aggregates into passes.

## macOS reproduction, 2026-11-21

Built source `f80a792` plus this documentation, toolkit `d108a64`,
`posix-release` (RelWithDebInfo), Apple Silicon. Fresh analysis, lift and build
passed; no source, toolkit or runtime settings were changed to hide the bars.
The guarded `story-tour` run used stock textures, 4:3, render scale 2, gamma on,
MSAA off, anisotropy 1 and the three-profile local Story fixture with manifest
SHA-256 `454458a4a737774483d36cd2e28244410d57f722658ae20c029e620beb46a74d`.
The selected profile shows 20/82 moves and 465 development points.

`logs/issue181/reference-story/report.json` passes all six selected assertions:
runtime faults, complete save restoration, crib and gym arrival, preview
request and unchanged fixture. Captures at 13 s and 23 s reproduce the grey
LOCKED/light other rows, with an orange selection. The 23 s capture contains
the playing preview. All three captures were inspected.

| Capture | SHA-256 |
|---|---|
| `story-tour-9s.bmp` | `dd91a2322ac4a475df0c60df8999ff29be1dd6c22630362d8f2cad4935846e9d` |
| `story-tour-13s.bmp` | `b6c419b7a0ff54711de49b09182739cb52c0ad0cc77fe88ea7f138b669a836c9` |
| `story-tour-23s.bmp` | `aa48d0774dcc7404212210d3cf2883d487d3cb114df56ab4eac726634ac6a527` |

The reviewed local manifest is
`logs/issue181/reviewed-baselines/manifest.json`. Strict comparisons retain
MAE 3 / changed fraction .02 / pixel threshold 16. The 23 s strict comparison
excludes only the 240x176 movie rectangle `[342,130,582,306]`; it never excludes
move rows. A separate movie-only comparison retains the previously calibrated
MAE 25 / changed fraction .5 policy (D362). Comparing the genuinely blank 13 s
preview with the playing 23 s reference fails that guard: MAE 119.64, changed
fraction 1.0 (`logs/issue181/reviewed-baselines/blank-preview-control.json`).

The independent native repeat retained at
`logs/scenarios/regress-visual-20261121-224041/report.json` passes the three gym
comparisons: 13 s MAE 0.2662 / changed fraction .003903; 23 s strict and movie
ROI both pixel-identical. Its aggregate remains **3/4**, because the initially
unmasked crib capture changed songs (MAE 4.5081 / changed fraction .043965).
Inspection of both captures and `diff-2.png` confines that difference to the
song banner. The reviewed manifest therefore excludes its observed rectangle
`[0,366,300,454]`, as the existing visual policy requires; no tolerance changes
were made. This does not mask any part of the gym screen.

The final native `regress.py --only visual --fixture
logs/issue181/story-fixture` run passes **4/4** image comparisons and all six
route/runtime/save assertions:
`logs/scenarios/regress-visual-20261121-224302/report.json` and
`logs/regress-20261121-224442.txt`. Gym differences match the independent repeat
above; the crib has zero changed pixels above threshold and MAE 0.000646 outside
the song banner. The previous 3/4 aggregate remains retained.

Unit tests: 2,763 passed, 78 skipped, one slow test deselected
(`logs/issue181/unit.txt`). A quick/full game regression was not required for
this documentation-only change; the targeted native visual runs establish the
reviewed scope. No Windows/Linux runtime or owner hardware acceptance is claimed.

Preserved setup failures are distinct from this successful reproduction:

- `logs/issue181/visual-before.txt`: blocked because this fresh worktree had no
  approved local manifest. The old Windows image mismatch was not rerun here;
  those baseline images are not available on this machine.
- `logs/issue181/reference-run/report.json` and
  `logs/run-20261121-223447.log.err`: the sandbox denied native graphics/fixed
  address memory initialization; no frames were presented. Save restoration
  and the fixture check passed.
- `logs/issue181/reference-native/report.json` and
  `logs/run-20261121-223549.log.err`: the older five-profile fixture selected a
  profile without Story progress, so the run was stopped before crib/gym.
  Save restoration and the fixture check passed. The subsequent successful
  run uses the calibrated three-profile fixture named above.

## Refreshing local acceptance

Follow [the harness review procedure](../09-testing-harness.md#learn-moves-row-backgrounds-181).
Keep captures, manifests and saves local. Use a separate candidate folder,
review each image, and verify it with a second launch before replacing any
active local baseline. The row area remains subject to the strict comparison;
the movie also retains a loose unmasked comparison to catch blank playback.

Windows and Linux/Steam Deck owners must review and refresh their own images
with the same fixture used for their original comparisons. This reference
review alone does not qualify their native runs.
