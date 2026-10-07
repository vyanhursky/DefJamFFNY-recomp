# Build and play on Windows

This guide builds the game locally from your own Xbox dump. The source release
contains no game executable or assets. Windows x64 is the current platform;
Windows 11 is the tested environment.

## Prerequisites

- Git for Windows.
- Python 3.12 or newer as `python` on PATH. Local development used 3.13; CI uses 3.12.
- Visual Studio Build Tools with **Desktop development with C++**, an x64 MSVC
  toolset, a Windows SDK and the CMake/Ninja tools. VS 2019 built the tested game;
  hosted CI uses the Windows runner's toolchain.
- PowerShell 5.1 or newer, a Direct3D 11 GPU, and a gamepad or a keyboard. The first configure downloads
  SDL3 (see [Controllers, keyboard and mouse](10-input.md)), so it needs network access once.
- Your own **USA Xbox Def Jam: Fight for NY** dump.
- [extract-xiso](https://github.com/XboxDev/extract-xiso/releases) for ISO extraction;
  7-Zip is optional for an image inside an archive.

Supported `default.xbe` SHA-256:
`31cc0d11f7c656b1a6f337fdf7d9bbaac9df11c324a2fb881f7eb639d4be00c2`.
The [manifest](../config/dump-manifest.json) records the other checks.

## Clone and select data storage

```powershell
git clone --recursive https://github.com/vyanhursky/DefJamFFNY-recomp.git
cd DefJamFFNY-recomp
python -m pip install pyxbe capstone pytest
$env:DEFJAM_DATA = 'C:\Games\DJFFNY-data'
```

Use a folder outside the repository. Set `DEFJAM_DATA` in each new shell before
running the pipeline or game. Without it, historical scripts use the development
machine's default path; avoid that default on another machine.

If you cloned without `--recursive`, run `git submodule update --init --recursive`.
Do not update the toolkit to another branch or replay `patches/xboxrecomp`.

## Extract and verify

Place `extract-xiso.exe` at
`$env:DEFJAM_DATA\tools\extract-xiso\artifacts\extract-xiso.exe`, then run:

```powershell
.\scripts\extract-disc.ps1 -Image 'D:\MyDumps\DefJam.xiso.iso' -DataDir $env:DEFJAM_DATA
python .\scripts\verify-dump.py "$env:DEFJAM_DATA\extracted"
if ($LASTEXITCODE) { throw 'Dump verification failed' }
```

If already extracted, put the files under `$env:DEFJAM_DATA\extracted` and run
the verifier. Other regions/revisions and other console versions are unsupported.

Create the `game` junction once:

```powershell
$discFolder = Join-Path $env:DEFJAM_DATA 'extracted'
New-Item -ItemType Junction -Path .\game -Target $discFolder
```

If `game` exists, inspect its target first; do not remove a real data directory.

## Analyze, recompile and build

Run each step only after the previous step succeeds:

```powershell
.\scripts\analyze.ps1
.\scripts\recomp.ps1
.\scripts\build.ps1 -Preset win-x64-release
```

Build scripts load the Visual Studio toolchain automatically. The first complete
pipeline may take tens of minutes. The XBE working copy and generated C remain
ignored local files. Do not share them or the resulting executable.

Output: `build/win-x64-release/defjam_recomp.exe`. Release uses optimized
`RelWithDebInfo`, retaining symbols for diagnostics. Input fingerprints reject
stale analysis, generated code and builds; follow the [workflow guide](03-workflows.md)
after source or toolkit changes.

## Launch and saves

From the repository root, with the same `DEFJAM_DATA` selected:

```powershell
.\scripts\run.ps1 -Preset win-x64-release
```

Or start `build/win-x64-release/defjam_recomp.exe` directly (double-click it or
make a shortcut): it finds the `game` folder in the repository root, supplies the
runtime switches itself and writes its log to `logs/`. `run.ps1` additionally
checks that the build is current and prints the log path when the game closes.

Play with a gamepad (Xbox, DualSense, Switch Pro and most others), the keyboard and mouse, or both:
the keyboard is its own player. [Controllers, keyboard and mouse](10-input.md) has the default keys and
the `[input]`, `[gamepad]` and `[keyboard]` settings for remapping, deadzones and rumble.

## Display settings

Every setting, including these, is listed in [settings.ini and keybinds](settings-reference.md).

Press **Alt+Enter** or **F11** to switch between a window and borderless full
screen. The window can be resized freely; the picture keeps the console's 4:3
shape with black bars.

Settings live in `settings.ini` in your data folder (`DEFJAM_DATA`, beside
`extracted` and `save`). The game writes the file with comments on first start;
edit it while the game is closed.

| `[display]` key | Default | Meaning |
|---|---|---|
| `fullscreen` | `false` | Start in borderless full screen. The hotkeys update it. |
| `window_width`, `window_height` | `1280`, `960` | Window size. Resizing the window updates them. |
| `aspect` | `4:3` | `4:3` keeps the picture shape; `stretch` fills the window. |
| `render_scale` | `2` | Internal resolution, 1-4 times 640x480. Try `3` or `4` on a 1440p or 4K display. |
| `filter` | `smooth` | `smooth` or `sharp` scaling to the window. |
| `vsync` | `true` | Pace frames on the display for even motion. Used on 60, 120, 180 and 240 Hz displays; others use the game's own 60 fps timer. |
| `gamma` | `true` | The game's own brightness curve, as on the console. |

`render_scale` and `gamma` take effect at the next start. A `RECOMP_*`
environment variable, where one exists, overrides the file for that run.
`RECOMP_SETTINGS=<path>` selects another file and `RECOMP_SETTINGS=none` ignores
the file, which is what the automated tests do.

Profiles and caches live under `DEFJAM_DATA/save`. Manual play writes normally,
without rollback. Back up this whole directory before trying another build.
Legacy project profile folders are accepted only after an exact metadata/name
match, without renaming or merging. Automated harness runs separately restore
the complete save root after testing.

## Troubleshooting

- Read the terminal error and `logs/run-*.log.err` if a process started.
- Missing `game/default.xbe`: check the junction and extraction.
- Freshness error: rerun the named analysis/lift/build step.
- Missing compiler: check the C++ workload and bundled CMake/Ninja tools.
- "The game files were not found": the executable looks for `game/default.xbe` in the
  current folder, beside itself and up to four folders above; check the junction.
- Saves missing after a direct launch: the data folder is found from `DEFJAM_DATA`, or
  from the `game` junction when it points at a folder named `extracted`. The first
  lines of `logs/run-*.log.err` say which folder and settings file were used.

Report your version/commit and reproduction steps. Review logs for personal
paths; do not upload game data, saves, generated source or memory dumps.
