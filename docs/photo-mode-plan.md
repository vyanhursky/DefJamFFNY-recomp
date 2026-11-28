# Def Jam Photo Mode Plan

Photo Mode freezes a loaded fight while the player composes and saves a photograph with a controller. The first version targets features 1–9 for milestone v1.3.0. Entrances and victory scenes are also candidates for activation, provided their animation and camera can freeze and resume correctly. Story cutscenes and ordinary menus remain excluded.

The implemented controls and capture behavior are in the [Photo Mode guide](photo-mode.md). Native evidence and remaining coverage are in the [scene qualification](research/photo-mode-scene-paths.md). The catalogue below keeps the original feature IDs for later selection.

First-version qualification: entrances, active Battle fights and paused Battle fights passed native probes. Victory entry remains disabled: the stock Battle route skipped the scene, and forcing the engine's extro branch reached uninitialized objects. A natural victory-scene route is needed before enabling that context. Story fights and wider platform/controller coverage remain release play-test work.

## Entry and return behavior

Press R3 + D-pad Down together on one controller. Activation is immediate and fires once; release the chord before reuse. The initiating controller owns the camera. Other controllers cannot complete the chord or operate gameplay while Photo Mode is active.

| Context | Behavior |
| --- | --- |
| Active Battle or Story fight | Freeze the scene; return to combat on exit. |
| Paused fight | Open Photo Mode over the frozen world; return to the existing pause menu on exit. |
| Fight entrance or victory animation | Attempt support after confirming scene ownership, frozen animation, free camera rendering, and exact resumption. |
| Cinematic attack within a fight | Attempt support using the same freeze and restoration checks. |
| Story cutscene, hub, shop, loading, character preview, result menu, other menu | Reject activation. |

Leaving Photo Mode restores its entry camera, FOV, roll, picture adjustments, HUD state, input ownership, and previous pause state. Picture edits are temporary and never write saved settings. Clear consumed button edges and require release before gameplay input resumes. Scene teardown cancels Photo Mode without writing saved camera data into a new scene. A disconnected controller must not unpause the game accidentally.

## Feature catalogue

The numbers remain stable so later decisions can reference them. On 2026-11-22 the owner approved feature 9 after play-testing features 1–8, requested immediate activation, and placed features 10–18 on hold. Entrance audio synchronization and full crowd visibility are also on hold after bounded audits found no straightforward qualified fix; see the [audio](research/photo-mode-audio-audit.md) and [crowd](research/photo-mode-crowd-audit.md) investigations.

| ID | Feature | Scope and implementation considerations |
| --- | --- | --- |
| 1 | Full scene freeze and controller free camera | Freeze combat, AI, timer, hazards, crowd, animation and effects while continuing camera updates and world rendering. Prove active and paused entry first. |
| 2 | Clean PNG capture | Save the finished game image at current internal resolution and aspect ratio, with unique names and success/error feedback. Exclude HUD, pause menu, photo controls, guides and notifications. |
| 3 | Adjustable camera speed | Precision and fast travel settings, look sensitivity and invert-Y. Use host elapsed time independent of frozen game time. |
| 4 | FOV and zoom | Adjust the lens independently of gameplay camera tracking. Respect the game's horizontal-at-4:3 FOV convention and widescreen projection. |
| 5 | Camera roll | Tilt the view with bounded controls and a level reset. |
| 6 | Reset camera | Restore the exact entry pose, FOV and roll without leaving Photo Mode. |
| 7 | HUD and control panel toggles | Hide the game HUD by default; independently hide the help panel. Restore original visibility on exit. |
| 8 | Composition guides | Rule-of-thirds grid and centre guide; never included in captured photos. |
| 9 | Existing picture adjustments | Temporary brightness, venue tint, vignette and film-scratch controls, using existing hooks and restoring entry values. |
| 10 | Fighter-centred orbit camera | Select a fighter and orbit their stable world position; retain free flight as an alternative. |
| 11 | Camera smoothing | Optional acceleration and damping; allow immediate movement for precise composition. |
| 12 | Camera bounds and collision | Start with optional distance/height limits; reliable wall collision requires further engine investigation. Free flight may expose unbuilt scenery. |
| 13 | Colour grading and filters | Saturation, contrast, temperature and presets through additional rendering work. |
| 14 | Depth of field | Manual focus and aperture after validating depth-buffer access, transparency and edges. |
| 15 | Higher-resolution still rendering | Render a new still above gameplay resolution; validate resource recreation, memory use and restoration. Image enlargement alone is insufficient. |
| 16 | Advance one simulation frame | Advance all required simulation and animation systems consistently, then freeze again without unintended gameplay input. |
| 17 | Selective subject and effect visibility | Targeted hiding of individual fighters, crowd or effects; preserve desired scenery and lighting. |
| 18 | Borders, aspect masks and presets | Saved camera/look settings and optional exported framing; distinguish crop from decorative borders. |

## Controller layout

| Control | Action |
| --- | --- |
| R3 + D-pad Down together | Enter Photo Mode immediately. |
| Left stick | Move forward/back and strafe. |
| Right stick | Look. |
| LT / RT | Move down / up. |
| LB / RB | Narrow / widen FOV. |
| A / Cross | Take a photograph. |
| X / Square | Hide/show the control panel. |
| Y / Triangle | Open/close camera settings. |
| B / Circle | Exit to the entry fight or pause state. |
| D-pad in settings | Select/change camera, HUD, guides and picture settings. |

The first version shows Xbox and PlayStation face-button labels together. Opening the camera settings suspends flight controls that conflict with menu navigation. Photo Mode, PC settings and song shortcuts have explicit priority and must not combine inputs across pads. B / Circle closes settings before exiting Photo Mode.

## Prototype and implementation stages

1. **Freeze and rendering proof.** Observe scene state and rendered frames in a live fight and a paused fight. Stop the fight screen's simulation work while continuing its draw path. Move the world camera before culling and verify visible geometry changes. Measure fighter poses, timer, hazards, crowd and effects; a stopped timer alone is insufficient.
2. **Eligibility and restoration.** Identify the active screen and cinematic ownership. Remember the prior pause state. Reject unrelated screens and stale scene pointers. Attempt fight entrances, victory scenes and special attacks with explicit evidence for each.
3. **Camera and input.** Initialize from the displayed view, update with a monotonic clock, support free flight, FOV, roll, reset and speed settings. Queue host requests to the guest thread; do not mutate guest state on the presenter thread. Consume photo inputs before gameplay.
4. **Capture and interface.** Add a bounded PNG request, portable save location and save feedback. Capture with correct colour/gamma and aspect, excluding original and host UI. Add HUD/panel toggles and composition guides.
5. **Qualification.** Test repeated entry and exit, multiplayer, disconnect and focus loss, paused return, Story fights, rejected scenes, entrances/victory and special moves. Check indoor venues, crowds, fire and Subway hazards, native/wide resolution and output failures. Run focused native regression gates and preserve platform limitations explicitly.

## Architecture and evidence

The game already identifies the fight step (`sub_00087700`), match state update (`sub_0008BE60`), fight screen ticks (`sub_00079B60`, `sub_0007A8F0`) and camera dispatch (`sub_000AC590`). The original debug camera (`sub_000AAE00`) is a coordinate/layout reference. Paused fights skip the normal match update, so a camera hook only inside that update cannot satisfy paused entry. Existing host input can read raw pads while neutralizing guest input; input ownership must compose with PC settings. Existing render-target BMP captures and PNG encoding provide groundwork for player-facing captures.

The corrected camera convention is described in [Cameras and venues](widescreen/05-cameras-and-venues.md). Earlier research labels some FOV calculations as vertical; the later errata supersede that premise.

Reference implementations:

- [BLACK Photo Mode](https://github.com/portingpete/Black-2006-Recomp/blob/main/docs/photo-mode.md): paused free camera, FOV, roll, speed, range, PNG capture and scripted-camera rejection. Its RenderWare-specific offsets are not Def Jam offsets.
- [BLACK integration](https://github.com/portingpete/Black-2006-Recomp/blob/main/src/recomp_manual.c) and [camera/controller implementation](https://github.com/portingpete/xboxrecomp/blob/e4b621706a3b5e58c084838d1f27547548cf27a8/src/video/pc_photo.c).
- [JSRF camera and freeze implementation](https://github.com/JuMatt/JetSetRadioFuture-Unleashed/blob/main/port/recomp_manual.c): selectively stop world updates while preserving camera publishing and drawing.
- [God Hand Rearmed](https://github.com/God-Hand-Rearmed/God-Hand-Rearmed): the reviewed README lists free-camera Photo Mode as coming soon; use its camera code as context rather than evidence of a complete Photo Mode.

## Acceptance for the first version

- Features 1–9 operate with a controller; the same frozen scene is rendered from multiple camera poses. Picture settings revert exactly on reset/exit without changing saved preferences.
- Active and already-paused fight entry work; exit preserves the prior pause state.
- Story fights are allowed; Story cutscenes and ordinary menus are rejected.
- Entrances, victories and special attacks are enabled only where freeze/render/resume evidence passes; record any remaining excluded paths.
- Frozen scene checks cover animation and relevant effects in addition to fighter position and timer.
- Saved PNGs have correct dimensions, aspect and colour, contain no photo UI, and report failed saves without leaving the scene frozen unintentionally.
- Normal gameplay remains unchanged while Photo Mode is inactive. No game data, captures or generated guest code are committed.
