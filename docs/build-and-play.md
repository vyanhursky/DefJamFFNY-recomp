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
- PowerShell 5.1 or newer, a Direct3D 11 GPU and an XInput controller.
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

The launcher supplies graphics, vblank and USB settings. Use an XInput pad;
keyboard gameplay controls are not implemented. Closing the game returns control
to the terminal and prints the log path.

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
- Use `run.ps1`: a direct EXE launch lacks its working-directory and runtime setup.

Report your version/commit and reproduction steps. Review logs for personal
paths; do not upload game data, saves, generated source or memory dumps.
