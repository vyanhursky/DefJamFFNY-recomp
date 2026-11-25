# RecompLauncher

[RecompLauncher](https://recomplauncher.com) lists Def Jam Recompiled and can install and update it. The
repository's [`recomplauncher.json`](../recomplauncher.json) tells the launcher a little about the game. This page
says what it does, what it deliberately does not, and how it reaches players.

## What players get

On the game's page in RecompLauncher:

- **Experience: Modern or Original.** The same two presets as the app's first-run choice
  (`k_experience` in `src/hooks/pc_settings_catalog.c`). Modern is widescreen at 2x resolution with 16x
  anisotropic filtering; Original is 4:3 at 1x. Original also turns HD texture packs off, as the app does.
  Any other combination shows as it is.
- **Skip intro**, the same setting as `[debug] skip_intro` (the legal screen and the EA, THX and intro movies).
  It does not skip Story credits.
- A note that other settings and Mods are found in the game's launcher.
- What the game needs from the PC, and a check that the player's copy is the right game
  (`default.xbe`, on an XISO, a full Redump image or in an extracted folder). A copy that matches the USA
  Redump image (7,825,162,240 bytes, CRC32 `71d5b621`, recorded in `research/disc-layout.md`) is shown as verified.
  The check is optional and the launcher does not start Easy Setup from it. Your own dump check (setup and
  `config/dump-manifest.json`) is unchanged and is still the real gate: `default.xbe` is on every region's disc.

The launcher edits `settings.ini` only when the player changes one of those rows, only the keys named there, and
never `[launcher] skip`: the game's own launcher still shows on every start, where mods, songs and the other settings are.

## What it does not do yet

| Left out | Why |
|---|---|
| Easy Setup, a setup step, `start` | Setup changes wait for [#189](https://github.com/vyanhursky/DefJamFFNY-recomp/issues/189). |
| Cloud saves and save backups | The save folder holds large partition images; saves do not move between operating systems through the launcher yet. |
| The launcher's Mods tab | It installs only `.nrm`, `.rtz` and native libraries, not folder packs. Mods stay in the game's launcher and on Thunderstore. |
| ReShade looks | Marked not allowed: they would be added beside the launcher's copy of the program, not the installed game. |

## Where the file goes

RecompLauncher reads the file from a release (inside an AppImage or beside a Mac app in its zip), from its own
catalog entry, or from the repository of a Forgejo server. For the Windows program, an installer exe, the catalog is
the route: the file in this repository is the source, and the RecompLauncher maintainer attaches a copy to the
`defjamffny-recomp` entry. The AppImage and Mac zip do not carry it yet: they are checked file by file by
`scripts/check-setup-assets.py`, and a copy there is part of the packaging work that follows #189.

## Default folders only

The launcher cannot read `location.json`, so it looks for `settings.ini` in the default data folders:

| System | Folder |
|---|---|
| Windows, macOS | `%LOCALAPPDATA%\DefJamRecompiled\data`, `~/Library/Application Support/DefJamRecompiled/data` |
| Linux, Steam Deck | `~/Games/DefJamRecompiled/Data` |

A player who chose another data folder, or the portable layout, sees the rows waiting for the game's first start and
changes nothing. Their settings are always in the game's launcher.

## Keeping it in step

`tests/unit/test_recomplauncher_manifest.py` reads the game's settings table and the preset table and fails when a key,
value, default or slider range in `recomplauncher.json` no longer matches, or the Modern and Original rows differ from
what the app applies. Change the manifest in the same pull request as any of those settings.

Check a change in RecompLauncher itself: Settings, Developers, turn on Developer tools, "Add a build", and pick the
folder holding the installed program with a copy of `recomplauncher.json` beside it. The schema is
<https://recomplauncher.com/schema/recomplauncher.json>.
