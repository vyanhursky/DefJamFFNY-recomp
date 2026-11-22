# Photo Mode

Hold **R3 + D-pad Down for half a second** on one controller during a loaded fight. The fight freezes while the camera remains controllable. Press **B / Circle** to return. If you opened Photo Mode from the game's pause menu, you return to that pause menu.

## Controls

| Control | Action |
| --- | --- |
| Left stick | Fly forward/back and strafe |
| Right stick | Look around |
| LT / RT | Fly down / up |
| LB / RB | Narrow / widen the field of view |
| A / Cross | Save a PNG photo |
| X / Square | Hide/show the controls |
| Y / Triangle | Open/close camera settings |
| B / Circle | Close settings, or exit Photo Mode |
| D-pad in settings | Up/down selects a row; left/right changes it |
| A / Cross on Reset camera | Restore the entry position, orientation and lens |

Settings include field of view, roll, four travel speeds, look sensitivity, invert Y, game HUD visibility, rule of thirds and a centre guide. Flight is suspended while settings are open. The controller that entered Photo Mode owns these controls; held buttons must be released before gameplay resumes.

The HUD starts hidden. The game HUD toggle changes the preview; saved photos always exclude the game HUD, pause panel, photo controls, composition guides and host subtitles. The camera is held briefly while a clean frame is captured. PNG compression then runs on a background worker. A save message appears in the control panel.

## Photos

Photos are saved under **Pictures/DefJamRecompiled** with unique `.png` filenames. On systems without a Pictures folder, the fallback is the application's preferences directory under `photos`. `RECOMP_PHOTO_DIR` overrides the destination for testing or a custom library.

Capture uses the current internal render resolution and aspect ratio, including the game's gamma adjustment. It does not increase render resolution. Only one photo is processed at a time; a failed write reports an error and allows another attempt.

## Availability and limits

Photo Mode is intended for loaded fights, including entry from the game's pause menu. Fight entrances and victory scenes are attempted through the same fight screen. Ordinary menus, result screens and authored Story cinematic camera paths are excluded. Availability and native qualification are recorded in the [scene investigation](research/photo-mode-scene-paths.md).

The free camera has no wall collision. Moving outside the arena can reveal missing geometry or scenery designed to be seen from one direction. The first version contains features 1–8 from the [complete 18-feature plan](photo-mode-plan.md); later features remain proposals.

For diagnostics, `RECOMP_PHOTO_MODE=0` disables the feature and `RECOMP_PHOTO_TRACE=1` logs camera settings. Developers can run `scripts/photo-probe.py` against this checkout's guarded `logs/runtime-data` to exercise freeze, camera motion, pause restoration and PNG output without changing the player's save root.
