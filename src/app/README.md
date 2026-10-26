# The app

`defjam_app` is one app for setup, launcher and updates, in progress
([design](../../docs/research/unified-app-design-2026-10-26.md), steps 2 and 3). It holds no game
code: it sets up the game from the player's own dump, shows the launcher's Home and Settings, and
Play starts the game that setup built on this computer, with `--no-launcher`.

- **Setup inside the app** (`app_setup.cpp`). With nothing installed it opens on the first run:
  the dump (an image or an extracted folder), the install and data folders, HD textures and
  shortcuts. Home's Update / Repair, and Advanced > Maintenance, open Maintenance: Repair and Clean
  Rebuild. Each runs `setup/engine.py` from the app's setup payload with that payload's Python, as
  the setup wizards do: the choices on its command line, its progress read from `--status-file`
  every frame and shown as a list of stages, Cancel through `--cancel-file`, and its exit code and
  last status line for how it ended. Closing the window during an operation asks it to cancel.
- **Same screen, same file.** It draws `src/hooks/pc_ui.cpp` built with `DEFJAM_APP`, which leaves
  out the overlay and the Debug page's controls for a running game (the recorder's mark, Story
  scenes, EA's developer menu). It registers the same catalogue
  (`src/hooks/pc_settings_catalog.c`) and edits the same `settings.ini` as the game.
- **Like the play wrapper.** It holds the install's `play.lock` (letting it go while setup works,
  since setup takes it), reads `installed.json`, sets `DEFJAM_DATA`, `DEFJAM_INSTALL_DIR` and the
  working directory, and keeps the session log beside the wrapper's
  (`~/Library/Logs/DefJamRecompiled`, or `~/.local/state/DefJamRecompiled/logs`; setup's own log is
  `setup-<time>.log` there). Play then `exec`s the game: the lock lives as long as the game, and the
  app is gone when the game ends.
- **When the window shows.** Same rule as the game's launcher (`pc_launcher_wanted`): skipped when
  "Skip launcher" is on, unless Shift is held or `--launcher` is given; always shown when mods need
  recovery or nothing is installed. `--play` always skips it.

macOS and Linux (with SDL3) for now; nothing packages or installs the app yet.

```
cmake -S . -B build/app -G Ninja -DDEFJAM_BUILD_GAME=OFF
cmake --build build/app --target defjam_app
build/app/defjam_app --payload <unpacked setup payload> [--install DIR] [--dump PATH] [--data DIR]
```

- **Install folder.** `--install DIR`, else `DEFJAM_INSTALL_DIR`, else the nearest folder above the
  program that holds `installed.json`, else the usual place (`~/Library/Application
  Support/DefJamRecompiled/app`, or `~/Games/DefJamRecompiled/App`).
- **Setup payload.** `--payload DIR`, else `DEFJAM_SETUP_PAYLOAD`, else `payload` in the bundle's
  `Resources` or beside the program.
- **First-run choices.** `--dump`, `--data` and `--no-shortcuts` fill them in. Setup refuses an
  Applications app that belongs to another install, so a second, test install needs
  `--no-shortcuts`.
- **Test hooks.** The launcher's work here too (`RECOMP_LAUNCHER_SCRIPT`, `RECOMP_WINDOW_SHOT`;
  see `src/hooks/pc_launcher_sdl.cpp`), with the setup screens' controls named `setup.*`.
  `RECOMP_APP_NO_DIALOG=1` reports a failure on stderr only.
