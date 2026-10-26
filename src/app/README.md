# The app

`defjam_app` is the first step of one app for setup, launcher and updates
([design](../../docs/research/unified-app-design-2026-10-26.md), step 2): the launcher's Home and
Settings in a program of its own, with no game code in it. Play starts the game that setup built
on this computer, with `--no-launcher`.

- **Same screen, same file.** It draws `src/hooks/pc_ui.cpp` built with `DEFJAM_APP`, which leaves
  out the overlay and the Debug page's controls for a running game (the recorder's mark, Story
  scenes, EA's developer menu). It registers the same catalogue
  (`src/hooks/pc_settings_catalog.c`) and edits the same `settings.ini` as the game.
- **Like the play wrapper.** It finds the install, holds `play.lock`, reads `installed.json`, sets
  `DEFJAM_DATA`, `DEFJAM_INSTALL_DIR` and the working directory, and keeps the session log beside
  the wrapper's (`~/Library/Logs/DefJamRecompiled`, or `~/.local/state/DefJamRecompiled/logs`).
  Play then `exec`s the game: the lock lives as long as the game, and the app is gone when the game
  ends.
- **When the window shows.** Same rule as the game's launcher (`pc_launcher_wanted`): skipped when
  "Skip launcher" is on, unless Shift is held or `--launcher` is given; always shown when mods need
  recovery. `--play` always skips it.

macOS and Linux (with SDL3) for now; setup does not build or install it yet.

```
cmake -S . -B build/app -G Ninja -DDEFJAM_BUILD_GAME=OFF
cmake --build build/app --target defjam_app
build/app/defjam_app --install "$HOME/Library/Application Support/DefJamRecompiled/app"
```

Without `--install` it uses `DEFJAM_INSTALL_DIR`, else the nearest folder above the program that
holds `installed.json`. The launcher's test hooks work here too (`RECOMP_LAUNCHER_SCRIPT`,
`RECOMP_WINDOW_SHOT`; see `src/hooks/pc_launcher_sdl.cpp`); `RECOMP_APP_NO_DIALOG=1` reports a
failure on stderr only.
