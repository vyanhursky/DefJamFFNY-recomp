# xboxrecomp Research Report

Compiled 2026-09-17. All facts below are sourced from live GitHub API queries (`gh api`) and WebFetch/WebSearch against the cited URLs on that date. Anything I could not confirm is explicitly marked **NOT FOUND / UNVERIFIED**.

---

## 1. Does `sp00nznet/xboxrecomp` exist?

**Yes — confirmed live.** https://github.com/sp00nznet/xboxrecomp

Verified directly via `gh api repos/sp00nznet/xboxrecomp`:
- Full name: `sp00nznet/xboxrecomp`
- Description: "Turn any Xbox game binary into a native Windows executable. No emulation. No interpreter. Just raw, recompiled C."
- Created: 2026-03-06, last push: 2026-09-16 (i.e., updated yesterday relative to today's date)
- Stars: **74**, Watchers: 74, Forks: **19**, Open issues: 10
- License: **MIT** (repo also ships a `LICENSES/` directory and `NOTICE` file — README states LGPL-2.1+ components are pulled in from xemu)
- Primary language: C, with a large Python component (see language breakdown below)
- Latest release tag: **v0.10.0 "Negative Control"** (published 2026-09-16); previous tags v0.9.0 "Quietly Wrong" (2026-09-12) and v0.6.0
- Has Issues, Projects, Wiki (`has_wiki: true`) enabled; no GitHub Pages/Discussions
- Owner `sp00nznet` (GitHub user id 4937302) is a single prolific individual maintainer — see section 2/3 caveats below

**Important caveat on maturity/provenance:** this is a very young, small, single-maintainer-led project (created March 2026, ~6 months old), not a large community effort. Commit messages in the repo's own history explicitly carry `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` trailers, indicating the codebase is built with heavy AI-agent assistance. Contributor list (`gh api repos/sp00nznet/xboxrecomp/contributors`): sp00nznet (321 contributions), `rhoggs-bot-test-account` (19), `GTTeancum` (17), `DarthSidious666` (14), `NoRain211` (13), `dplewis` (7), `andeecollard` (3). This is a small, informal contributor pool, not an established emulation-scene team.

Also worth flagging: the owner `sp00nznet` maintains a very large number of similarly-styled "X-recomp" repos across wildly different platforms and eras — e.g. `360tools` (Xbox 360), `androidrecomp` (Android ARM64), `apple2recomp` (Apple II), `catz-recomp`, `civ` (Civilization 1991), `crazytaxi`/`chuchu` (Dreamcast SH-4), `blockdude-ti-recomp` (TI-83), `lynxrecomp` titles, `burnout3` (69 stars, the flagship game port), `xboxdashboard` (12 stars), `hl2-recomp` (2 stars, "Possibility of porting Half-Life 2" per issue #12) — all published within the same ~6-month window in 2026. This pattern (one person, dozens of "recomp" toolkits for unrelated architectures, all AI-co-authored, all low-star) is a strong signal this is a solo rapid-prototyping/"vibe-coded" body of work rather than an established scene project. Treat claims of completeness/robustness with proportionate skepticism.

**Forks found:** `NoRain211/xboxrecomp`, `DanielJVoxSmart/xboxrecomp`, `phobos665/xboxrecomp`, `dplewis/xboxrecomp`, `DarthSidious666/xboxrecomp`, `GTTeancum/xboxrecomp`, `MattSG/xboxrecomp`, `andeecollard/xboxrecomp` — all are plain GitHub forks of the same repo (consistent with `forks_count: 19`), not independent projects.

**No other independently-named original-Xbox static-recompilation project was found.** Searches for "XboxRecomp", "xbox-recomp", "OGXboxRecomp", "xbe2c" turned up only `sp00nznet/xboxrecomp` and its forks/companion repos. No unrelated project by those names exists as far as I could verify. **NOT FOUND / UNVERIFIED**: any static-recomp-for-original-Xbox effort independent of sp00nznet.

Sources:
- https://github.com/sp00nznet/xboxrecomp
- https://github.com/sp00nznet/xboxrecomp/releases
- https://github.com/sp00nznet/xboxrecomp/graphs/contributors
- https://github.com/sp00nznet/burnout3
- https://github.com/sp00nznet/xboxdashboard
- https://github.com/sp00nznet/hl2-recomp
- https://github.com/sp00nznet/360tools
- https://deepwiki.com/sp00nznet/xboxrecomp

---

## 2. Workflow / technical details (best/only candidate: `sp00nznet/xboxrecomp`)

**Pipeline (from README, "The Pipeline" section):**
1. Extract `default.xbe` from the Xbox disc image (user-supplied tool, e.g. `xdvdfs`/`extract-xiso`)
2. `tools/xbe_parser` — parse XBE headers/sections/kernel imports → JSON (`--json game_files/default_analysis.json`)
3. `tools/disasm` — x86 disassembly, function detection, control-flow graphs (`--text-only` or `--extra-sections`)
4. `tools/func_id` — classify functions as CRT / RenderWare / D3D / game code
5. `tools/abi_analysis` — recover calling convention/parameter counts (required — skipping it silently falls back to cdecl/0-params/guessed return type for every function)
6. Optional: `tools/ghidra_naming` (or `tools/ida_naming`) — symbol name recovery via Ghidra/IDA FLIRT/FidDb, applied via `merge_names.py --apply`
7. Copy `templates/new-game/` to a new project directory — the actual game `.exe` is built **outside** this repo, in the user's own project, which links against the xboxrecomp libraries
8. `tools/recomp` — lift x86 to C (`--all --split 1000 --gen-dir ../mygame/src/recomp/gen`), emitting `recomp_NNNN.c`, `recomp_dispatch.c`, `recomp_funcs.h`
9. Build with CMake + MSVC from the game project; run the resulting native `.exe`

**Config format:** JSON, not TOML — `default_analysis.json`, `functions.json`, `xrefs.json`, `strings.json`, `abi_functions.json`, `symbols.json`. (The planning document's assumption of a TOML config format is **not confirmed** — I found no TOML anywhere in the described pipeline; NOT FOUND / UNVERIFIED for TOML specifically.)

**Runtime libraries (link-time, no emulator at runtime):**
| Library | Source | Function |
|---|---|---|
| `xbox_kernel` | custom | xboxkrnl → Win32 shim: 170/371 kernel ordinals routed (169 w/ dedicated bridges as of v0.9.0, "every ordinal routed" claimed for v0.9.0 release notes — memory, file I/O, threading, sync, crypto, HAL, EEPROM, SMBus) |
| `xbox_d3d8` | custom | D3D8 → D3D11: fixed-function multitexture pipeline, NV2A register-combiner pixel shaders, NV2A microcode → HLSL vertex shaders, hardware T&L (8 lights), vertex fog, texture unswizzling |
| `xbox_dsound` | custom | DirectSound → software mixer |
| `xbox_apu` | from **xemu** (LGPL-2.1+) | MCPX APU audio (256-voice, ADPCM/PCM, HRTF) |
| `xbox_nv2a` | from **xemu** (LGPL-2.1+) + custom | NV2A GPU register handling / push-buffer parsing / PGRAPH → D3D11 |
| `xbox_input` | custom | Xbox controller → XInput |
| `xbox_video` | custom | FMV playback via Media Foundation onto a D3D8 texture |

So: **yes**, it does shim `xboxkrnl` exports and provide D3D8 and XInput HLE, as the planning doc assumed, plus DirectSound HLE (not a separate "DSound" acronym but functionally the same). Graphics backend on Windows is **D3D11**; on Linux, README states an OpenGL backend (`tools/linux/install_deps.sh`); macOS needs `brew install sdl2 libepoxy` (also implies an OpenGL-family backend).

**Host platforms:** Windows 11/10 (primary, D3D11), Linux (OpenGL backend), macOS (OpenGL backend via SDL2/libepoxy) — per README Prerequisites and per Darwin-specific fixes noted in the v0.10.0 changelog (`IsDebuggerPresent`, `SecureZeroMemory`, `GlobalMemoryStatusEx`, waitable timers, etc., contributed by `dplewis`).

**Toolchain requirements:**
- Python 3.10+ with `capstone` disassembly library (`pip install capstone`)
- CMake 3.20+
- Visual Studio 2022 (MSVC) on Windows; the repo's own CI/conformance suite additionally uses a `linux/386` Docker container with GCC for cross-checking x86 semantics
- Windows SDK (D3D11, DXGI, XInput)
- Optional Ghidra or IDA for symbol recovery
- No Rust anywhere in the toolchain (language breakdown per `gh api .../languages`: C 2,103,418 bytes, Python 1,165,482, CMake 20,916, Shell 12,058, Java 2,533, Dockerfile 246 — no Rust)

**Known limitations (from README + release notes):**
- Not all kernel ordinals are implemented (v0.9.0 claims full ordinal routing, but many are "documented stubs," not full implementations)
- The lifter/disassembler has had numerous correctness bugs fixed as recently as v0.10.0 (Sept 16, 2026): wrong ABI on `NtQueryDirectoryFile`, `KfRaiseIrql`/`KfLowerIrql` (`__fastcall` mishandled), `SAR` sign-extension bugs, `INC`/`DEC` clobbering flags it shouldn't, `jbe`/`ja` branch-folding bugs, `FIST`/`FISTP` rounding-mode bugs, `FXAM` not implemented, uninitialized `ebp` locals — i.e., the x86→C lifter is actively being debugged for basic instruction-semantics correctness as of this writing, which is a meaningful maturity signal.
- ICALLs (indirect calls via vtables/function pointers) are called out in the README as "the hardest 10%" of getting a title running.
- First boot of any recompiled game "will crash" — the workflow is explicitly iterative/manual (stub functions, fix ICALLs, add runtime support, debug, repeat).
- Xbox Live / networked features are explicitly called out as adding difficulty; offline-only games are preferred targets.
- Self-modifying/dynamically-generated code is explicitly listed as something to avoid when picking a target game.

**Games recompiled / in progress** (per `docs/technical/candidate-games.md` and the sp00nznet repo list):
- **Burnout 3: Takedown (2004)** — the reference/proven title. Status per docs: "boots, loads game data, runs gameplay loop with a custom rendering frontend" — i.e. **not a finished, shippable port**, still in active development. Separate repo: https://github.com/sp00nznet/burnout3 (69 stars).
- **Xbox Dashboard build 3944** — https://github.com/sp00nznet/xboxdashboard (12 stars), described as "the first-ever native PC port of the original Xbox Dashboard."
- **Half-Life 2 (Xbox, 2005)** — https://github.com/sp00nznet/hl2-recomp (2 stars), very new (created 2026-09-01).
- Candidate lists (not yet started, just documented as targets) include GTA III/Vice City/San Andreas, Burnout 1/2, Tony Hawk's Pro Skater titles, Halo: CE, Jet Set Radio Future, Fable, KOTOR, Ninja Gaiden, Halo 2, DOA3/XBV, Conker: Live & Reloaded — these are **aspirational tiered candidates**, not completed ports.

Sources:
- https://github.com/sp00nznet/xboxrecomp (README, `docs/technical/candidate-games.md`, `docs/GETTING_STARTED.md`)
- https://github.com/sp00nznet/xboxrecomp/releases/tag/v0.10.0
- https://github.com/sp00nznet/xboxrecomp/releases/tag/v0.9.0
- https://github.com/sp00nznet/burnout3
- https://github.com/sp00nznet/xboxdashboard
- https://github.com/sp00nznet/hl2-recomp

---

## 3. Context: comparison with Cxbx-Reloaded / xemu, and is static recomp of OG Xbox a real 2025-2026 trend?

**Cxbx-Reloaded** — https://github.com/Cxbx-Reloaded/Cxbx-Reloaded
- Stars: 60 (this number is surprisingly low for a long-running project and worth double-checking against the live page if precision matters — GitHub API confirmed 60 stars, 6 forks, GPL-2.0, last push 2026-04-19, language C++)
- Approach: **HLE** — runs the original Xbox x86 XBE code natively on the host x86/x64 CPU, intercepting/shimming Xbox kernel calls and Direct3D 8 calls at the API boundary (conceptually similar in spirit to xboxrecomp's kernel/D3D8 shim layer, but Cxbx-Reloaded executes the guest's *original compiled binary directly* rather than lifting it to new C source).

**xemu** — https://github.com/xemu-project/xemu
- Stars: **4,109**, forks: 509, license NOASSERTION (mixed, GPL-family with LGPL components), last push 2026-09-14 (yesterday), very active.
- Approach: **LLE** (low-level emulation) — emulates the Xbox's actual hardware (MCPX bootrom, NV2A GPU, SMBus/EEPROM, etc.) via a QEMU/HW-emulation base, running the unmodified XBE/kernel exactly as the console would. This is the most accurate/most-compatible original-Xbox emulator and is under active, well-resourced development.
- A WebSearch snippet also surfaced a claim ("xemu supports 80% of games considered playable") from a general web result — treat as approximate community/website claim, **not independently verified in this report**.

**xboxrecomp vs. these two:** because the original Xbox is x86 (Pentium III-class, Coppermine-based, IA-32), a recompiled `.exe` and an HLE-shimmed original XBE are running semantically similar strategies (native execution of x86 + kernel/API shims) — the key difference is that xboxrecomp *transforms the binary into new C source* ahead of time (a compile-time, one-shot translation you can then hand-edit/mod), whereas Cxbx-Reloaded *loads and directly executes the original compiled x86 code* at runtime with call interception. Static recomp's main selling points per xboxrecomp's own README are moddability of the generated C, portability to non-x86 hosts, and "preservation," not raw performance — since the source XBE is already x86, the native-speed argument that justifies MIPS/PowerPC recomp (N64, Xbox 360) applies far less on original Xbox, where an HLE approach like Cxbx-Reloaded already runs the original code natively without any translation step.

**Is static recompilation of original-Xbox games a real, active 2025-2026 trend?**
Based on my search coverage: **NOT FOUND / UNVERIFIED as an independent, community-wide trend.** I found no Reddit r/emulation threads, X/Twitter posts, YouTube coverage, or blog posts discussing original-Xbox static recompilation as a genre/movement — all search results resolved back to `sp00nznet`'s own repos (xboxrecomp, burnout3, xboxdashboard, hl2-recomp) and their GitHub PR/issue trail. This looks like a single motivated individual (plus a handful of contributors: GTTeancum, DarthSidious666, NoRain211, dplewis, andeecollard) applying the recomp *technique* — popularized by N64Recomp/XenonRecomp for MIPS/PowerPC targets — to original Xbox, rather than a broader scene trend the way, e.g., Xbox 360 recomp (UnleashedRecomp) or N64 recomp (Zelda64Recomp) clearly are (both of which have thousands of stars, hundreds of forks, and substantial press/community coverage — see section 4).

The practical, well-established, actively-developed routes for playing/porting original Xbox games on modern PCs remain:
- **xemu** (LLE, 4.1k stars, very active) — highest compatibility, hardware-accurate emulation
- **Cxbx-Reloaded** (HLE, native x86 execution + kernel/D3D8 shims) — an older, slower-moving project but still the canonical "runs the original XBE directly" HLE option
- Traditional reverse-engineering **decompilation** projects (game-specific, e.g. in the style of the many decompilation projects for other consoles) — I did not find a prominent original-Xbox-specific decompilation project comparable to, say, the N64 decomp scene, in this search pass. **NOT FOUND / UNVERIFIED.**

Sources:
- https://github.com/Cxbx-Reloaded/Cxbx-Reloaded
- https://github.com/xemu-project/xemu
- https://en.wikipedia.org/wiki/Xemu_(emulator)

---

## 4. Comparison with mature recomp toolchains

| Project | URL | Platform | License | Stars/Forks (live, 2026-09-17) | Asset handling |
|---|---|---|---|---|---|
| **XenonRecomp** | https://github.com/hedge-dev/XenonRecomp | Xbox 360 (PowerPC) → native x86-64 | MIT | 6,478 stars / 424 forks | Tool only — takes a user-supplied Xbox 360 XEX/game dump as input; no game assets or code in the repo itself |
| **UnleashedRecomp** | https://github.com/hedge-dev/UnleashedRecomp | Xbox 360 (Sonic Unleashed) → native PC (Win/Linux/Steam Deck) | GPL-3.0 | 5,064 stars / 419 forks | Built on XenonRecomp; requires the user to supply their own legally-owned copy of the Xbox 360 game files/assets at build or first-run time — no copyrighted Sega/Sonic Team assets ship in the repo |
| **N64Recomp** | https://github.com/N64Recomp/N64Recomp | N64 (MIPS) → native executables | MIT | 8,133 stars / 448 forks | Generic tool; operates on a user-supplied N64 ROM, no ROMs bundled |
| **Zelda64Recomp** | https://github.com/Zelda64Recomp/Zelda64Recomp | N64 Majora's Mask (and OoT) → native PC (Win/Linux/Mac) | GPL-3.0 | 7,267 stars / 333 forks | Requires the user to provide their own legally-dumped Majora's Mask/OoT ROM at build/first-run; no Nintendo ROM or asset data included in the repo |

All four of these are, by star count, fork count, and license/legal-hygiene pattern (generic MIT tool + separate GPL "recomp" project that requires the user's own game dump, never bundling copyrighted assets), an order of magnitude more mature/adopted than `sp00nznet/xboxrecomp` (74 stars/19 forks) and its companion `burnout3`/`xboxdashboard`/`hl2-recomp` repos. `sp00nznet/xboxrecomp` follows the same legal pattern in its FAQ ("You must own a legitimate copy of any game you recompile. No copyrighted game code or assets are included in this repository") but has nowhere near the community size, contributor count, or track record of a finished, playable port that XenonRecomp/UnleashedRecomp and N64Recomp/Zelda64Recomp have.

Sources:
- https://github.com/hedge-dev/XenonRecomp
- https://github.com/hedge-dev/UnleashedRecomp
- https://github.com/N64Recomp/N64Recomp
- https://github.com/Zelda64Recomp/Zelda64Recomp

---

## 5. Documentation / wiki / Discord for xboxrecomp

- **README.md** (root of https://github.com/sp00nznet/xboxrecomp) — the primary doc; covers What Is This, Why Not Just Use an Emulator, The Pipeline, Runtime Libraries table, Integration Pattern, Architecture diagram, Quick Start, What To Expect, Repository Structure. Setup steps (condensed, from README "Step-by-Step," names kept exact):
  1. `git clone https://github.com/sp00nznet/xboxrecomp.git && cd xboxrecomp`
  2. Extract `default.xbe` from your Xbox disc image into a `game_files/` directory using a third-party tool (`xdvdfs`, `extract-xiso`, or similar) — not bundled
  3. `py -3 -m tools.xbe_parser game_files/default.xbe --json game_files/default_analysis.json`
  4. `py -3 -m tools.disasm game_files/default.xbe --text-only` (outputs to `tools/disasm/output/`: `functions.json`, `xrefs.json`, `strings.json`)
  5. `py -3 -m tools.func_id game_files/default.xbe -v` (outputs to `tools/func_id/output/`)
  6. `py -3 -m tools.abi_analysis game_files/default.xbe -v` (outputs `tools/abi_analysis/output/abi_functions.json`) — README stresses this step is not optional
  6b. Optional: `XBE=game_files/default.xbe tools/ghidra_naming/run_ghidra.sh` then `py -3 tools/ghidra_naming/merge_names.py --apply`
  7. `cp -r templates/new-game ../mygame` (or `xcopy /E /I templates\new-game ..\mygame` on Windows), then edit `../mygame/CMakeLists.txt` (project name, `XBOXRECOMP_DIR` path) and `../mygame/src/main.c` (entry point / XBE path)
  8. `py -3 -m tools.recomp game_files/default.xbe --all --split 1000 --gen-dir ../mygame/src/recomp/gen` — generates `recomp_0000.c` … `recomp_dispatch.c`, `recomp_funcs.h`, `recomp_types.h`
  9. `cd ../mygame && cmake -S . -B build && cmake --build build --config Release`, then run `build\Release\your_game_recomp.exe`
- **docs/GETTING_STARTED.md** — the longer version of the above, explains rationale behind each flag; also documents the Linux/macOS platform matrix and notes the D3D11 backend is "six files against one for OpenGL"
- **docs/technical/candidate-games.md** — game-selection guidance, tiered difficulty list (see section 2)
- **docs/technical/ms-fusion-recompiler.md** — referenced in README as covering Microsoft's own internal Xbox→360 back-compat recompiler ("Ficl/Fission") that the project studied; contents not separately fetched in this pass
- **CONTRIBUTING.md**, **CONTRIBUTORS.md**, **NOTICE**, **LICENSE**, **LICENSES/** (for the xemu-derived LGPL components) all exist at repo root
- **Wiki**: GitHub reports `has_wiki: true` for the repo, but I did not separately crawl wiki page contents in this pass. **NOT FOUND / UNVERIFIED** (existence of the wiki tab is confirmed; its actual content is not).
- **Discord**: README links `https://discord.gg/CRpzGWZFcu` — "the community hub for sp00nznet's recomp projects, where ps3recomp development happens in the open." I did not join/verify the Discord's member count or activity level (out of scope / requires an account). **NOT FOUND / UNVERIFIED** beyond confirming the invite link is published in the README.
- **DeepWiki mirror**: https://deepwiki.com/sp00nznet/xboxrecomp exists (third-party auto-generated wiki, not official).

Sources:
- https://github.com/sp00nznet/xboxrecomp (README.md, CONTRIBUTING.md, CONTRIBUTORS.md, docs/ tree)
- https://deepwiki.com/sp00nznet/xboxrecomp

---

## Summary of NOT FOUND / UNVERIFIED items
- TOML as the analysis/config format — the actual pipeline uses JSON, not TOML.
- Any Reddit/X/YouTube/blog coverage discussing original-Xbox static recomp as a trend, independent of sp00nznet's own repos.
- Any original-Xbox decompilation project comparable to N64/Xbox 360 decomp scenes.
- Actual content of the xboxrecomp GitHub wiki tab and Discord server activity/size.
- The "xemu supports 80% of games" figure (surfaced once in a general web snippet, not independently confirmed here).
