# Photo Mode

Press **R3 + D-pad Down together** on one controller during a loaded fight. Photo Mode opens immediately, freezing the fight while the camera remains controllable. Press **B / Circle** to return. If you opened Photo Mode from the game's pause menu, you return to that pause menu.

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
| A / Cross on Reset picture | Restore the entry brightness, tint, vignette and scratches |

Settings include field of view, roll, four travel speeds, look sensitivity, invert Y, game HUD visibility, rule of thirds and a centre guide. Flight is suspended while settings are open. The controller that entered Photo Mode owns these controls; held buttons must be released before gameplay resumes.

Picture settings add brightness (50–200%), venue colour tint (0–100%), vignette on/off and strength (0–100%), and film scratches on/off. These adjustments affect the preview and saved PNGs. They start from your current settings and revert when you leave Photo Mode; your saved settings are never changed. Reset picture restores the entry look while keeping the camera where it is. Venue effects remain subject to what that venue actually draws.

The HUD starts hidden. The game HUD toggle changes the preview; saved photos always exclude the game HUD, pause panel, photo controls, composition guides and host subtitles. The camera is held briefly while a clean frame is captured. PNG compression then runs on a background worker. A save message appears in the control panel.

## Photos

Photos are saved under **Pictures/DefJamRecompiled** with unique `.png` filenames. On systems without a Pictures folder, the fallback is the application's preferences directory under `photos`. `RECOMP_PHOTO_DIR` overrides the destination for testing or a custom library.

On macOS this is normally `~/Pictures/DefJamRecompiled`; on Linux it uses the configured XDG Pictures folder (commonly `~/Pictures/DefJamRecompiled`). SDL resolves these paths and provides the writable preferences fallback through [SDL_GetUserFolder](https://wiki.libsdl.org/SDL3/SDL_GetUserFolder) and [SDL_GetPrefPath](https://wiki.libsdl.org/SDL3/SDL_GetPrefPath). The pinned SDL implementation maps macOS to `NSPicturesDirectory` and Linux to XDG `PICTURES`. These paths were verified from the API and platform source; native Mac/Linux capture remains a platform play-test check.

Capture uses the current internal render resolution and aspect ratio, including the game's gamma adjustment. It does not increase render resolution. Only one photo is processed at a time; a failed write reports an error and allows another attempt.

## Availability and limits

Photo Mode works in loaded fights, including entry from the game's pause menu, and fight entrances. Victory entry remains disabled pending qualification of a natural victory-scene route. Ordinary menus, result screens and authored Story cinematic camera paths are excluded. Availability and native qualification are recorded in the [scene investigation](research/photo-mode-scene-paths.md).

The free camera has no wall collision. Moving outside the arena can reveal missing geometry or scenery designed to be seen from one direction. The first version contains features 1–9 from the [complete 18-feature plan](photo-mode-plan.md); features 10–18 are on hold at the owner's request.

Entrance audio can continue during the freeze and finish before the animation resumes. A coordinated audio cursor pause requires more work across the audio engines, so this minor issue is [on hold](research/photo-mode-audio-audit.md). Crowd visibility also remains [on hold](research/photo-mode-crowd-audit.md): some spectators culled by the original camera remain missing, and refreshing their existing update would also advance animation. No global culling override is enabled.

For diagnostics, `RECOMP_PHOTO_MODE=0` disables the feature and `RECOMP_PHOTO_TRACE=1` logs camera settings. Developers can run `scripts/photo-probe.py` against this checkout's guarded `logs/runtime-data` to exercise freeze, camera motion, pause restoration and PNG output without changing the player's save root.

Standard builds include SDL for PNG saving. Custom Windows builds with `DEFJAM_SDL3=OFF` report that saving requires an SDL-enabled build.
