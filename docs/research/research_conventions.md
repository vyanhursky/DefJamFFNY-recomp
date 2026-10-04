# Original-Xbox disc→XBE tooling and recomp-project conventions

Research date: 2026-09-17. Target environment: Windows 11, VS 2019 Build Tools, Python 3.13, git, 7-Zip, winget, choco present; no cmake/ninja/clang yet. Target platforms: Windows + Steam Deck (Linux).

---

## Part A — Disc image → analyzable XBE

### 1. extract-xiso (XboxDev/extract-xiso)

Repo: https://github.com/XboxDev/extract-xiso
Releases (prebuilt binaries incl. Windows): https://github.com/XboxDev/extract-xiso/releases

**Windows install**: no winget/choco package. Download the newest `build-*` release asset for Windows from the Releases page (e.g. `build-202609111233`), or build from source with CMake (needs `cmake`, a C compiler, `make`/Ninja — see Part C toolchain install below). There's also a third-party GUI wrapper, `TheRealNextria/XisoGUI` (https://github.com/TheRealNextria/XisoGUI), if a GUI is preferred.

**CLI flags** (from `extract-xiso.c` usage text):
```
-c <dir> [name]   Create xiso from file(s) starting in <dir>
-l                List files in xiso(s)
-r                Rewrite xiso(s) as optimized xiso(s)
-x                Extract xiso(s) (default mode)
-d <directory>    In extract mode, expand xiso in <directory>
-s                Skip $SystemUpdate folder
-D                Delete original after rewrite
-m                Disable automatic .xbe media-patching
-q / -Q           Quiet / silent
```

**Plain `.xiso.iso` (game-partition-only image)**: just run
```
extract-xiso -x mygame.xiso.iso
```
This is the common/simple case — no offset handling needed.

**Full Redump `.iso` (video partition + game partition)**: this is the part with real nuance.
- extract-xiso **does** detect XGD1/XGD2/XGD3 layouts internally — its source (`extract-xiso.c`) contains explicit offset constants used when locating the XDVDFS header if it isn't at the start of the file:
  - `GLOBAL_LSEEK_OFFSET = 0x0FD90000`
  - `XGD3_LSEEK_OFFSET = 0x02080000`
  - `XGD1_LSEEK_OFFSET = 0x18300000`
  It probes for the `XISO_HEADER_DATA` magic at these offsets, so **`extract-xiso -x` or `-r` run directly against a full Redump image generally works without manual splitting**, because it auto-locates the game-partition XDVDFS filesystem header past the video partition/padding.
- Community discussion (https://github.com/XboxDev/extract-xiso/issues/58) confirms two workable approaches for Redump images: run `extract-xiso -r redump_game.iso` directly (rewrites to a trimmed/optimized xiso), or manually `dd skip=387 bs=1M` to cut the file at the game-partition offset before extracting — the manual `dd` route was reported to produce a larger file than `-r`, because `extract-xiso -r` **rebuilds the XDVDFS filesystem losslessly-but-repacked** (recreates the ISO9660/XDVDFS tree, dropping the video partition and inter-partition padding) rather than simply byte-copying from an offset.
- Caveat: extract-xiso's rewrite is **lossy relative to the original XDVDFS structure** — it reconstructs the filesystem tree rather than preserving byte-identical layout. If bit-exact preservation of the original XDVDFS (e.g. for hashing against Redump checksums) matters, use **Deterous/XboxKit** instead (https://github.com/Deterous/XboxKit): it does lossless, bidirectional conversion between Redump ISO and XISO by splitting out the video partition, filler/padding data, XGD1 seed data, and (for XGD3) system-update files into sidecar files, keeping the XDVDFS filesystem byte-identical. Also see **rizaumami/redump2x** (https://github.com/rizaumami/redump2x) and **NearlyTRex/XIsoConvert** (https://github.com/NearlyTRex/XIsoConvert) as alternative converters, and the community wiki page https://consolemods.org/wiki/Xbox:ISO_Extraction_%26_Repacking for a walkthrough (this page returned 403 to automated fetch — read it manually in a browser).

**Recommendation for this project**: use `extract-xiso -x` (or `-r` then `-x`) directly on whatever image the user provides (plain xiso or Redump). If later you need byte-exact XDVDFS preservation for hash-matching against Redump's published checksums, add XboxKit as an alternative path — don't build that complexity in up front.

### 2. XBE analysis tools

| Tool | What it gives you | Notes |
|---|---|---|
| **XboxDev/xbedump** — https://github.com/XboxDev/xbedump | Dumps XBE header fields; can also (re)sign XBEs (SHA-1 section hashes + RSA-2048 header signature, replicating what the Xbox kernel checks). Based on Michael Steil's original XBE Dumper. | C source, builds w/ OpenSSL + `make`. No prebuilt Windows binary found — build from source or use pyxbe instead for read-only analysis. |
| **mborgerson/pyxbe** — https://github.com/mborgerson/pyxbe, PyPI: https://pypi.org/project/pyxbe/, docs: https://pyxbe.readthedocs.io/en/latest/ | Pure-Python 3 library to read/write `.xbe`: kernel image header, sections, certificate (title ID, region, allowed media), library-version table (XAPI/D3D8/DSOUND/XNET/etc. with their version numbers), TLS directory. Easiest, no-compile option on Windows/Python 3.13. | `pip install pyxbe` |
| **XboxDev/ghidra-xbe** — https://github.com/XboxDev/ghidra-xbe | Ghidra extension adding an `XboxExecutableLoader`. On import gives: entry point (XOR-decoded per retail/debug key), kernel import thunk table (resolved xboxkrnl.exe ordinal → function name), sections, TLS, certificate/title ID, and library-version list. Does **symbol recovery via pattern matching against XbSymbolDatabase** (see #3) so statically-linked XAPI/D3D8/etc. functions get named automatically where signatures match. Optional GPL Xbox C headers improve type info. | Install: download `ghidra_X.X.X_PUBLIC_..._ghidra-xbe.zip` from Releases, drop into `<Ghidra>/Extensions/Ghidra`, enable via File → Install Extensions → XboxExecutableLoader. |
| **IDA**: `emoose/idaxex` — https://github.com/emoose/idaxex | Native loader plugin for IDA 9.x supporting both XBE (original Xbox) and XEX (360). Superset of IDA's stock XBE loader; supports writing patched bytes back via "Apply patches to input". | Prebuilt IDA 9 builds on the Releases page. (This is the modern replacement for older/dead XBE-only IDA loaders.) |
| **Cxbx-Reloaded** built-in XBE dump | Cxbx-Reloaded (the OG-Xbox emulator/community HLE project) parses XBE headers as part of loading and cross-references imports against its own OOVPA database at runtime — useful as a second opinion / ground truth for what a "correct" HLE match looks like, but it's not a standalone dumper CLI; you'd run the emulator itself. Repo: https://github.com/Cxbx-Reloaded/Cxbx-Reloaded | No separate install; comes with the emulator build. |

**Practical recommendation**: for scripted/automated analysis on Windows/Python 3.13, use `pip install pyxbe` as the primary tool (entry point, sections, TLS, cert/title ID, library versions, no native build needed). Use `ghidra-xbe` when you need disassembly + automatic symbol naming for statically-linked library code.

### 3. Identifying the XDK version and why it matters for HLE

- Original-Xbox games statically link Microsoft's XDK libraries (XAPILIB, D3D8, DirectSound, XNet, etc.) directly into the XBE — there's no DLL-style dynamic linking to a system D3D8.dll like on PC. The **library-version table in the XBE header** (readable via pyxbe/xbedump/ghidra-xbe) lists each linked library's name + a 4-digit build number; comparing these numbers against known XDK release tables tells you which XDK (and therefore which exact library source/binary revision) a title was built with.
- This matters because HLE (high-level emulation) reimplementation projects like **Cxbx-Reloaded** don't emulate the CPU running the statically-linked library code — instead they **pattern-match** (via OOVPA: "Optimized (Offset,Value)-Pair Array", a byte-signature scheme invented by the original Cxbx author "Caustik") known compiled library functions inside the XBE's `.text`, replace them with native trampolines into the emulator's own reimplementation, and leave the game's own code alone. Because Microsoft relinked slightly different compiled code into each XDK release (compiler/LTCG changes, bugfixes), OOVPA signatures are versioned per XDK/library-build — matching the wrong version's signature set will misidentify or fail to find functions.
- Cxbx-Reloaded's signature DB now lives in a separate repo, **Cxbx-Reloaded/XbSymbolDatabase** (https://github.com/Cxbx-Reloaded/XbSymbolDatabase, wiki: https://github.com/Cxbx-Reloaded/XbSymbolDatabase/wiki/Overview-of-the-project-&-Glossary-of-terms) so third-party tools (including ghidra-xbe) can consume it without embedding Cxbx-Reloaded itself. It's organized per XDK library build number.
- For a from-scratch static-recompilation approach (rather than HLE trampolining), the practical takeaway is: dump the library-version table first, use it to pick/generate the matching OOVPA/XbSymbolDatabase signature set, and expect statically-linked XAPI/D3D8 code to require the same signature-matching step Cxbx-Reloaded already solved — reuse XbSymbolDatabase rather than re-deriving signatures per game.

### 4. Legal-hygiene conventions (asset-free repos)

Observed directly in hedge-dev/UnleashedRecomp (the most mature current recomp project):
- The repo and its `UnleashedRecompLib` submodule ship **no game data**. Build docs (https://github.com/hedge-dev/UnleashedRecomp/blob/main/docs/BUILDING.md) instruct the developer to manually place `default.xex`, `default.xexp`, and `shader.ar` — files the user must dump themselves from their own legally-owned disc/console — into `./UnleashedRecompLib/private/` before building. The word "private" as the directory name is itself the convention signal: user-supplied copyrighted game data lives under a `private/` (or similarly named, gitignored) directory, never committed.
- The general `.gitignore` in UnleashedRecomp is a standard VS/.NET ignore file; the actual asset-exclusion is enforced structurally (the `private/` directory + build-time hash check) rather than by a special gitignore rule — i.e., don't rely on gitignore alone, gate at the file-picker/installer level too.
- At **install time** (not build time), UnleashedRecomp's own installer **validates the user's game files by hash and rejects modified/incorrect content** before proceeding — this is the "hash verification of the user's XBE via SHA-256 in a config" pattern the task asked about. Zelda64Recomp does the same for ROMs: it "will only accept one specific ROM: the US version of the N64 release of Majora's Mask" and performs hash-based validation (auto-converting non-`.z64` formats first), explicitly stating "this repository and its releases do not contain game assets."
- CI runs without the game: build workflows (see Part B) build the recompiler/runtime/tooling only; they do not fetch or embed any copyrighted asset. Anything that needs the actual game (full end-to-end "does it run" testing) is left to the human developer running locally with their own legally-dumped copy, not CI.
- **Recommended pattern to copy**: (a) a clearly-named, gitignored `private/` (or `dump/`) directory for user-supplied XBE/ISO content; (b) a small config file (TOML/JSON) listing expected file names + SHA-256 hashes for known-good title versions; (c) an install/setup script that computes SHA-256 of what the user supplies and refuses to proceed (or warns) on mismatch; (d) CI never touches this directory and only builds tooling/runtime code.

---

## Part B — Reference project conventions

### 5. hedge-dev/UnleashedRecomp and hedge-dev/XenonRecomp

- **UnleashedRecomp**: https://github.com/hedge-dev/UnleashedRecomp — unofficial PC port of Sonic Unleashed (Xbox 360) via static recompilation.
- **XenonRecomp**: https://github.com/hedge-dev/XenonRecomp — the generic Xbox 360 (PowerPC) → C++ static recompiler used to produce UnleashedRecomp's game code; paired with **XenosRecomp** for Xenos GPU shaders → HLSL. XenonRecomp explicitly states it was "heavily inspired by N64: Recompiled."

**Build system**: CMake (3.20+) + **Clang required** — "compilers other than Clang have not been tested and are not recommended" (clang-cl via VS's CMake integration works on Windows). Submodules must be cloned recursively. UnleashedRecomp build requirements:
- Windows: Visual Studio 2022 + "C++ Clang Compiler for Windows" + "C++ CMake tools for Windows" workloads (VS auto-generates CMake config on open).
- Linux: cmake, ninja, clang, pkg-config, autoconf, automake, libtool, curl, libgtk-3-dev.
- macOS: Xcode 16.3+/CLT, cmake, ninja, pkg-config.
- Uses **vcpkg** as a thirdparty submodule (`thirdparty/vcpkg`), wired in via `CMAKE_TOOLCHAIN_FILE` pointing at `vcpkg.cmake`, with **CMake presets** (`linux-debug`, `linux-release`, `linux-relwithdebinfo`, similarly for macos) driving `VCPKG_TARGET_TRIPLET`/`VCPKG_CHAINLOAD_TOOLCHAIN_FILE`. Build docs: https://github.com/hedge-dev/UnleashedRecomp/blob/main/docs/BUILDING.md
- Linux build commands: `cmake . --preset linux-release` then `cmake --build ./out/build/linux-release --target UnleashedRecomp`.

**XenonRecomp workflow (config format)**: two-stage TOML-driven pipeline.
1. `XenonAnalyse <in.xex> <out_switch_tables.toml>` — detects jump/switch tables, emits TOML.
2. `XenonRecomp <config.toml> <ppc_context.h>` — recompiles per a config TOML with sections like:
```toml
[main]
file_path = "../private/default.xex"
patch_file_path = "../private/default.xexp"
out_directory_path = "../ppc"
switch_table_file_path = "SWA_switch_tables.toml"
```
plus per-optimization toggles (`skip_lr`, `ctr_as_local`, `cr_as_local`, …), manual function-boundary overrides, register-save-function addresses, and `[[midasm_hook]]` entries that splice named C++ hook calls into the recompiled output at a given address/register-set — this is the extensibility point used for things like custom rendering hooks.

**CI**: UnleashedRecomp's `.github/workflows/` contains `validate.yml`, `validate-internal.yml`, `validate-external.yml`. `validate-internal.yml` triggers on push-to-main and PRs from the same repo, and simply calls the reusable `validate.yml` workflow with `secrets: inherit` (the external variant presumably runs a safer subset for fork PRs, withholding secrets). These are build/compile validation workflows — no game files are fetched; CI proves the code builds, not that the game runs. (Actions history: https://github.com/hedge-dev/UnleashedRecomp/actions)

**Frame rate / game loop**: default 30 FPS Xbox 360 game is unlocked to 60 FPS by default with support for higher/unlocked targets; because "the game does not perform some tasks in an asynchronous way," stutter remains at high framerates (120+) and is called out as an open issue needing further work — i.e., the delta-time/frame-pacing hook is not a fully solved decoupled-simulation model, it's a partial unlock layered onto code that still assumes fixed-step behavior in places.

**File I/O / mod hooking**: integrates with **Hedge Mod Manager**, using the same mod-loading convention as Sonic Generations PC mods (asset-replacement mods only at present); some codes/patches are directly embedded and toggled through the mod manager; full code modding (patching recompiled logic) is called out as "currently not possible" / planned, unlike Zelda64Recomp's more mature RecompModTemplate system (see below).

**Install / hash validation**: installer requires the user to supply Xbox 360 disc/console dumps (containers or raw extracted files) and **rejects modified content** via validation; only US/EU Sonic Unleashed (not JP) is supported due to structural differences.

**Steam Deck**: ships a native Linux build plus a **Flatpak** (`io.github.hedge_dev.unleashedrecomp`), data installs to `~/.var/app/io.github.hedge_dev.unleashedrecomp/data`; documented as installable directly on Deck and addable as a non-Steam game from Desktop Mode; recommend using external storage (microSD/network share) given Deck storage constraints.

### 6. Mr-Wiseguy/N64Recomp (now org N64Recomp/N64Recomp) + Zelda64Recomp

- **N64Recomp**: https://github.com/N64Recomp/N64Recomp — statically recompiles N64 binaries (from an ELF, typically produced by a decompilation project) into C, compiled for any target. CMake 3.20+/C++20. Directory layout includes `src/` (core recompiler), `include/`, `lib/`, `RSPRecomp/` (RSP microcode recompiler), and separate tool binaries `RecompModTool/`, `LiveRecomp/`, `OfflineModRecomp/`.
- **TOML config format**: specifies input/output file paths, per-function stubbing, skip-recompilation lists, and single-instruction patches; metadata is sourced from the ELF (symbols/relocations from the decompilation project). Same family of config idea as XenonRecomp's TOML (both post-date/borrow from each other; XenonRecomp explicitly cites N64Recomp as its inspiration).
- **Mod/patch system — RecompModTemplate**: e.g. `Zelda64Recomp/MMRecompModTemplate` (https://github.com/Zelda64Recomp/MMRecompModTemplate) is the canonical example — provides a build system, headers, and a `mod.toml`. `RecompModTool mod.toml <build_dir>` compiles a mod into a `.nrm` file. The TOML lets a mod author declare patched functions (functions from the original game that this mod overrides), stubbed functions, and instruction-level patches; the tool cross-checks patch targets against symbol names from the (possibly community-renamed) decompilation, so a common failure mode is "function marked as a patch target doesn't exist" when upstream decomp renames a symbol. Multiple other games clone this same template (BKRecompModTemplate for Banjo-Kazooie, BMHeroRecompModTemplate for Bomberman Hero, etc.) — strong evidence this is the reusable convention to copy for a new project's mod story.
- **Runtime libs**: `N64Recomp/N64ModernRuntime` (https://github.com/N64Recomp/N64ModernRuntime) provides two libraries — **ultramodern** (reimplementation of libultra's OS/threading/audio/controller-IO core, with platform I/O supplied via callbacks from the embedding project) and **librecomp** (glue between N64Recomp-generated code and ultramodern). Rendering is not baked in — ultramodern expects the embedder to register a renderer, and the recommended one is **RT64** (a modern N64-era-aware renderer, also reused by Zelda64Recomp).
- **Zelda64Recomp** (Majora's Mask, and formerly under Mr-Wiseguy, now org `Zelda64Recomp`): https://github.com/Zelda64Recomp/Zelda64Recomp. Layout: `src/`, `include/`, `lib/`, `assets/`, `icons/`, `patches/`, `mods/`, `shaders/`, `shadercache/`, `rsp/`, `docs/`, `flatpak/` (Linux packaging directory), `CMakeLists.txt`, `CMakeSettings.json` (VS CMake integration), plus `.toml` files describing the ROM/overlays. CI runs a GitHub Actions matrix across Windows/Linux/macOS. ROM handling: hash-validates the ROM is specifically the US N64 Majora's Mask release, auto-converts non-`.z64` container formats, and ships **no game assets** in the repo or releases. Mods use RecompModTemplate; distribution is via **Thunderstore** (thunderstore.io/c/zelda-64-recompiled/). Ships a standalone Linux binary and a Flatpak; Steam Deck support is via "Add to Steam" (non-Steam game) plus Steam Input's Gyro-as-Mouse for gyro aim. Dependencies include RT64 (rendering) and RmlUi (UI).

### 7. Steam Deck packaging

- Both mature projects (UnleashedRecomp, Zelda64Recomp) ship: (1) a native Linux build, and (2) a **Flatpak** specifically for easy Deck/Desktop-Mode install and update management, rather than an AppImage. Flatpak is the dominant convention in this project family — likely because it gives sandboxed, self-updating distribution that plays nicely with Deck's read-only SteamOS filesystem, versus an AppImage (portable but no update channel) or asking users to run a Windows build under Proton (unnecessary once you have a native Linux/Vulkan build, and would forgo the perf win — UnleashedRecomp's docs even note Linux is sometimes *faster* than Windows for this workload due to better thread-sync handling).
- Rendering/windowing stack: UnleashedRecomp uses **plume** (https://github.com/renderbag/plume), a graphics HAL over D3D12 (Windows) and Vulkan (Linux/Deck), with Metal planned — i.e., not SDL2/SDL3+Vulkan directly, but a custom abstraction layer serving the same purpose. Zelda64Recomp pairs with RT64 for rendering. Neither project surfaced explicit SDL_GameControllerDB usage in this research pass — Deck/Steam Input controller mapping for Zelda64Recomp is instead handled by configuring Steam Input profiles (e.g. Gyro-as-Mouse) rather than the app shipping its own controller DB; verify directly in-repo if SDL_GameControllerDB matters for your project, this wasn't confirmed either way.
- Known Deck friction point: a filed issue, "Flatpak system operation ConfigureRemote not allowed for user on steam deck" (https://github.com/hedge-dev/UnleashedRecomp/issues/1414) — Flatpak's need to add a remote can hit SteamOS's locked-down permission model; worth planning for (e.g. document a manual `flatpak remote-add` fallback, or ship via Flathub proper once eligible so users don't need to add a third-party remote at all).
- Practical recommendation for a new project: build a native Linux binary via CMake+Clang using Vulkan (skip a custom HAL initially — plain SDL2/SDL3+Vulkan is fine for a solo project and is well-trodden), package it as a Flatpak for Deck/Desktop-mode distribution, and keep a plain unpackaged Linux build available too as a fallback/dev path since Flatpak sandboxing can complicate file-picker access to the user's dumped game files (both reference projects flag exactly this: recommend booting Desktop Mode first to run the installer/file-picker before switching to Game Mode).

### 8. Testing conventions

What these projects actually test in CI, based on this research:
- **Build-only / compile validation** is the dominant CI pattern. UnleashedRecomp's `validate*.yml` workflows exist specifically to prove the code compiles (internal vs. external/fork-PR variants, presumably to avoid leaking secrets to untrusted fork builds) — no game files are present in CI, so nothing beyond compilation and (implicitly) any unit tests that don't need game data can run there.
- **Instruction-level unit tests on the recompiler itself**: XenonRecomp has a dedicated **XenonTests** project that feeds Xenia's PowerPC test binaries through the recompiler and checks the generated output against expected results — i.e., the recompiler's correctness (not the game's) is unit-tested against a known-good instruction corpus. This is the most directly reusable pattern: test your instruction-translation layer against a synthetic/reference binary, independent of any copyrighted game asset.
- **No evidence found** (in this pass) of golden-image/screenshot regression testing or a headless "boots to title screen" smoke test in CI for either project family — unsurprising, since that would require the actual copyrighted game asset to be present in CI, which both projects deliberately avoid (see Part A §4). Any "does it actually run/boot" verification is left to manual/local testing by contributors who own the game, not automated CI.
- **Runtime library unit tests**: not confirmed directly in this pass for N64ModernRuntime/ultramodern; worth checking their `.github/workflows` directly if you want a concrete example, but the general pattern across this whole project family is clearly "unit-test the translation/runtime layer with synthetic or third-party-open test binaries; leave asset-dependent end-to-end testing to humans."

**Recommended practical test pyramid for a solo hobbyist** (synthesizing the above, not lifted from a single source):
1. **Unit tests on the recompiler/translator core** (no game asset needed): feed hand-written or third-party-open PowerPC/x86 test binaries (Xenia and other emulator projects publish PPC instruction test corpora) through your instruction-translation layer and assert on the generated C/C++ output or its execution result. This is cheap, fast, runs in CI on every PR, and is exactly what XenonTests does.
2. **Unit tests on the runtime/HLE shim layer** (no game asset needed): test your reimplementations of kernel calls / library functions (the equivalent of ultramodern/librecomp) against expected behavior using synthetic inputs, independent of any real game.
3. **Build-matrix CI** across Windows + Linux (Steam Deck target) on every push/PR — compile-only, mirroring `validate.yml`'s pattern — catches portability breaks early without touching copyrighted assets.
4. **Manual, local "does it boot" smoke test** run by you (the only person with a legal dump) before tagging a release — not automated, not in CI, exactly the boundary these projects draw. If you want to eventually automate this without distributing the asset, a **self-hosted runner you control, with your own legally-owned dump on that machine only**, running headless-boot + a frame-hash check, would be the way to do it without committing/distributing the asset — none of the researched projects appear to do this yet, so treat it as a stretch goal rather than a convention to copy.
5. Skip golden-image/screenshot diffing and full-game automated playthrough testing for now — none of the reference projects do it, it's high-maintenance, and it doesn't fit a solo-hobbyist budget; revisit only if the project grows contributors.

---

## Part C — Toolchain install commands for the stated Windows 11 environment

Current gaps per the task: no cmake, no ninja, no clang. Below are exact commands using the tools already available (winget/choco).

```powershell
# CMake
winget install --id Kitware.CMake -e

# Ninja
winget install --id Ninja-build.Ninja -e
# (or: choco install ninja -y)

# LLVM/Clang (needed as the primary compiler for XenonRecomp-style projects; clang-cl integrates with VS 2019 Build Tools' MSVC headers/libs)
winget install --id LLVM.LLVM -e
# (or: choco install llvm -y)

# Python XBE tooling
pip install pyxbe

# extract-xiso: no package manager entry found — download the Windows binary from
# https://github.com/XboxDev/extract-xiso/releases (latest build-* asset), or build from
# source once cmake/ninja/a C compiler are installed above.

# Ghidra (for ghidra-xbe) — not covered by winget/choco reliably; download from
# https://ghidra-sre.org/ and then install the ghidra-xbe extension zip from
# https://github.com/XboxDev/ghidra-xbe/releases

# vcpkg (used by UnleashedRecomp/XenonRecomp-style CMake builds) — typically vendored as a
# git submodule in thirdparty/vcpkg rather than a standalone winget install; if you want a
# standalone copy: git clone https://github.com/microsoft/vcpkg && .\vcpkg\bootstrap-vcpkg.bat
```

VS 2019 Build Tools already provides MSVC; clang-cl (from the LLVM install above) can be used as the CMake compiler for a Clang-only project like XenonRecomp while still linking against the VS 2019 Build Tools' Windows SDK/CRT. Confirm the reference projects' minimum Clang version (18+ was cited for XenonRecomp) against whatever `winget install LLVM.LLVM` resolves to, and pin/upgrade if older.

---

## Sources

- https://github.com/XboxDev/extract-xiso
- https://github.com/XboxDev/extract-xiso/releases
- https://github.com/XboxDev/extract-xiso/blob/master/extract-xiso.c
- https://github.com/XboxDev/extract-xiso/issues/58
- https://github.com/TheRealNextria/XisoGUI
- https://github.com/Deterous/XboxKit
- https://github.com/rizaumami/redump2x
- https://github.com/NearlyTRex/XIsoConvert
- https://consolemods.org/wiki/Xbox:ISO_Extraction_&_Repacking
- https://github.com/mborgerson/pyxbe , https://pypi.org/project/pyxbe/ , https://pyxbe.readthedocs.io/en/latest/
- https://github.com/XboxDev/xbedump
- https://github.com/XboxDev/ghidra-xbe , https://github.com/XboxDev/ghidra-xbe/blob/master/README.md
- https://github.com/emoose/idaxex
- https://github.com/Cxbx-Reloaded/Cxbx-Reloaded
- https://github.com/Cxbx-Reloaded/XbSymbolDatabase , wiki: https://github.com/Cxbx-Reloaded/XbSymbolDatabase/wiki/Overview-of-the-project-&-Glossary-of-terms
- https://github.com/hedge-dev/UnleashedRecomp , /blob/main/README.md , /blob/main/docs/BUILDING.md , /tree/main/.github/workflows , /blob/main/.gitignore , /issues/1414 , /actions
- https://github.com/hedge-dev/XenonRecomp , /blob/main/README.md
- https://github.com/renderbag/plume
- https://github.com/N64Recomp/N64Recomp (formerly Mr-Wiseguy/N64Recomp)
- https://github.com/N64Recomp/N64ModernRuntime
- https://github.com/Zelda64Recomp/Zelda64Recomp
- https://github.com/Zelda64Recomp/MMRecompModTemplate
- https://ghidra-sre.org/
- https://github.com/microsoft/vcpkg

## Notes on gaps / unverified claims

- The exact contents of `validate.yml` (the reusable workflow both `validate-internal.yml`/`validate-external.yml` call) were not directly fetched — only inferred from the calling workflows' names and trigger conditions. Worth a direct look if you need the exact OS matrix/build-step list.
- SDL_GameControllerDB usage was not confirmed or denied for either project in this pass — flagged as unverified above rather than guessed.
- `consolemods.org`'s Xbox ISO extraction/repacking wiki page returned HTTP 403 to automated fetch; recommend a manual browser visit for the step-by-step walkthrough it likely contains.
- Zelda64Recomp's own `.github/workflows/build.yml` matrix contents (exact OS list/job names) weren't directly fetched — only the general "Windows/Linux/macOS CI matrix" claim, sourced from search summaries, was confirmed.
