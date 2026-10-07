# Launcher and overlay

Two ways to change settings without editing `settings.ini`. Both show the same screen, both save as you
change things, and both are usable with a mouse, the keyboard or a gamepad.

## The launcher

A window that appears **every time you start the game**, before the game itself loads. It has the settings
and two buttons: **Play** starts the game, **Quit** closes it. Changes that are read only at start-up (render
scale, who plays, how many controllers, the pad backend) take effect for this very launch, because the game
has not started yet.

- **Skip it:** tick *Skip the launcher at start* at the bottom of the launcher, or in the overlay's
  General page (`[launcher] skip` in `settings.ini`).
- **Bring it back when skipped:** hold **Shift** while the game starts, or start `defjam_recomp.exe` with
  `--launcher`. `--no-launcher` skips it for one launch.
- Test and scripted runs (the regression harness, `RECOMP_SETTINGS=none`) never show it.

## The overlay

Press **F1** in the game (or the pad's guide button, or hold both stick clicks for half a second) to open it
over the picture; the same keys close it, and so do Esc and the pad's B button. While it is open the game is
polled at rest, as if every pad and the keyboard were untouched, but it **keeps running**: it does not pause.
Close it before the next hit.

Full screen, window size, picture shape, filter and vsync apply as you change them. Render scale and the
brightness curve are marked *(restart)* and take effect the next time the game starts; a banner at the bottom
lists the changes that are waiting for a restart. Keys: `[ui] overlay_key` and `overlay_pad` in
`settings.ini`, or the General page.

## The pages

| Page | What it has |
|---|---|
| Display | Full screen, window size, picture shape, scaling filter, vsync, render scale, the brightness curve |
| Controllers | Which controller is in which player, with a live view of each pad's sticks and buttons as the game will see them (after dead zones and mapping) and a rumble test; who plays (keyboard player, controller count, backend); dead zones and thresholds; rumble; the pointer |
| Pad buttons | Which physical button acts as each Xbox control. Choose from a list, or press **Detect** and then the button on your pad |
| Keyboard & mouse | The keys and mouse inputs for each Xbox control. Press **Add**, then a key, a side or middle mouse button or a wheel notch (Esc cancels); the left and right mouse buttons have buttons of their own while you are adding. **Clear** and **Default** per control |
| General | Skip the launcher, the overlay's key and pad buttons, text size, a button that shows `settings.ini` in Explorer, reset every setting to default, and the version |

## Using a gamepad in the menus

The d-pad or left stick moves, **A** (the bottom face button) activates, **B** goes back or closes, the shoulder
buttons switch pages, and the triggers change a slider faster. This works with any pad the game reads, with
the first pad to press a button, and independently of the game's own button mapping.

## Where it comes from

The screen is [Dear ImGui](https://github.com/ocornut/imgui) (MIT; release 1.92.9b, fetched at build time at
a pinned hash, licence in `thirdparty/imgui-LICENSE.txt`). The overlay is drawn in the presentation step after
the game's picture has been scaled into the window, so it is in window pixels and never in a test capture.
Source: `src/hooks/pc_ui.cpp` (the screen and the overlay), `src/hooks/pc_launcher.cpp` (the launcher window),
`src/hooks/pc_ui_settings.c` (the settings and the rule for when the launcher shows).
