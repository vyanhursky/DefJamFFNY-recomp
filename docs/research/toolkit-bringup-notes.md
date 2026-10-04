# Toolkit Bring-Up Notes — Def Jam: Fight for NY (XDK 5849)

Research pass over the local `xboxrecomp` toolkit checkout
(`tools/xboxrecomp`) to explain the current bring-up state: ICALL failures
into XGRPH/XPP/DSOUND, and the crash at Xbox VA `0xFFFFFE00`. Every claim
below is sourced from a specific doc/file in the checkout; quotes are
verbatim unless marked "paraphrased."

## Recommended next commands

Re-lift the XDK library sections that `--text-only` skipped, then redo every
downstream step that reads `functions.json` (func_id, abi_analysis, recomp
all re-derive from it — nothing here can be skipped):

```bash
# 1. Re-disassemble, adding the sections --text-only excluded. Section names
#    come straight from your XBE's section table (D3D, D3DX, DSOUND, XPP,
#    XGRPH, DOLBY per the problem statement) -- confirm exact names with
#    tools.xbe_parser's section dump if unsure.
py -3 -m tools.disasm game_files/default.xbe --text-only \
    --extra-sections D3D,D3DX,DSOUND,XPP,XGRPH,DOLBY -v

# 2. Re-classify (now covers the newly-lifted library functions too)
py -3 -m tools.func_id game_files/default.xbe -v

# 3. Re-recover ABI/calling conventions for the new functions
py -3 -m tools.abi_analysis game_files/default.xbe -v

# 4. Regenerate C -- the dispatch table now contains the 7 VAs that were
#    failing (0x00201954, 0x0027E5AC, 0x0025E58B, 0x0025E596, 0x00262020,
#    0x0026202B, 0x002091E3), plus everything else in those sections
py -3 -m tools.recomp game_files/default.xbe --all --split 1000 \
    --gen-dir ../mygame/src/recomp/gen

# 5. Rebuild and re-run; capture stdout+stderr to a log
build\Release\your_game_recomp.exe > run.log 2>&1

# 6. For any ICALL failure that *survives* step 1-4 (a true runtime-only
#    target, e.g. a vtable call or thread entry point nothing references
#    statically), feed the log back into the seed file and re-lift:
py -3 -m tools.seed_from_log run.log game_files/default.xbe \
    --functions tools/disasm/output/functions.json \
    --seeds config/seed_functions.json
py -3 -m tools.disasm game_files/default.xbe --text-only \
    --extra-sections D3D,D3DX,DSOUND,XPP,XGRPH,DOLBY \
    --seed-functions config/seed_functions.json
# ... then repeat steps 2-4
```

For the `0xFFFFFE00` crash: it is not one of the toolkit's documented
special addresses (see Q2 below) — chase it as an uninitialized-pointer /
vtable-garbage bug per `docs/technical/lessons-learned.md`, using
`RECOMP_PEEK_CHAIN`/`RECOMP_TRACE_ARGS` (see Q4) to find what wrote
`0x8003F980`-shaped garbage into `edx`.

---

## Q1: How should the XDK library sections (D3D, D3DX, DSOUND, XPP, XGRPH, DOLBY) be handled?

**Answer: lift them (disassemble + recompile), the same as `.text`. They
are not HLE'd wholesale — only the top-level D3D8 Device/Buffer COM
interface is intercepted; everything statically linked underneath it
still needs to go through the normal pipeline.**

### The mechanism

`tools/xboxrecomp/tools/disasm/loader.py`, `get_code_sections()`
(lines 132-147), is explicit that library sections are meant to be
disassembled, not skipped, even though their names look like data:

> "The executable flag alone is not a usable signal: Xbox linkers mark
> nearly every section executable, including `.data`. ... So data sections
> are excluded by name regardless of their flags. ... Only the conventional
> PE data sections are listed. XDK library sections are NOT excluded even
> when their name suggests data (DSOUND_RD, D3D_RD, XON_RD): the linker
> maps class those as CODE, and they are exactly the sections we want
> disassembled."

`DATA_SECTION_NAMES` (same file, lines 21-23) is `{".data", ".data1",
".rdata", ".idata", ".edata", ".reloc", ".tls"}` — D3D/D3DX/DSOUND/XPP/
XGRPH/DOLBY are not in that set, so they are picked up automatically by a
plain `tools.disasm` run **as long as `--text-only` is not passed**. Your
run used `--text-only`, which restricts to `.text` unconditionally
(`tools/xboxrecomp/tools/disasm/disasm.py`, `_get_target_sections()`,
lines 286-293) — that is exactly why those VAs were never lifted.

### The documented flag syntax

`README.md` (Quick Start, disassemble step):

> "`--text-only` does what it says: only `.text`. A title with code in its
> XDK library sections (D3D, DSOUND, XPP...) needs them named explicitly,
> e.g. `--extra-sections XIPS,DOLBY`. Drop `--text-only` to take every code
> section."

`docs/DECOMP.md` (same table):

> `--extra-sections XIPS,DOLBY` | treat non-executable sections as code

`docs/pipeline/02-disassembly.md`:

> "The `--text-only` flag restricts disassembly to the .text section (game
> code). Without it, the tool also processes the named library sections
> (XMV, DSOUND, etc.), which adds time but increases coverage for games
> that call library code via indirect jumps."

`--extra-sections` is for sections the XBE marks **non-executable** but
that actually hold code (`tools/disasm/__main__.py` help text: "additional
section names to treat as code (for sections marked non-executable in the
XBE but containing code)"). If D3D/D3DX/DSOUND/XPP/XGRPH/DOLBY are already
flagged executable in this XBE, simply dropping `--text-only` picks them
up via `get_code_sections()`; if any are flagged non-executable, they need
explicit `--extra-sections` naming. Passing `--extra-sections` is safe
either way (it's additive and skips names already present), so the
recommended-next-commands section above uses it unconditionally.

### Steps that must be re-run

`func_id`, `abi_analysis`, and `recomp` all read `functions.json` from
`tools/disasm/output/` by default (confirmed directly in
`tools/func_id/__main__.py`, `tools/abi_analysis/__main__.py`, and
`tools/recomp/__main__.py`, which all default `functions` to
`tools/disasm/output/functions.json`). Re-running `tools.disasm` with the
extra sections regenerates that file with the new functions in it, so
**func_id, abi_analysis, and recomp must all be re-run afterward** —
`docs/GETTING_STARTED.md` Step 4.5 is explicit that skipping ABI recovery
silently falls back every function to `cdecl` / 0 params, so it cannot be
skipped for the newly-added functions either.

### What Burnout 3 did

`docs/technical/burnout3-reunification.md` and
`docs/technical/gap-analysis.md` describe the actual architecture: the
runtime's `xbox_d3d8` library (see `README.md`'s Runtime Libraries table)
only intercepts the **D3D8 Device/Buffer COM vtable** — fake COM objects
whose vtable entries point at the D3D11 translation layer
(`docs/pipeline/05-runtime.md`, "COM Vtable Emulation"). `gap-analysis.md`
confirms this explicitly for push-buffer parsing:

> Push buffer parsing (PFIFO DMA pusher) | Full | Stub | N/A | Low
> (D3D8 API intercept instead)

That is HLE **at the Device-interface boundary only**. Everything the XDK
statically links beneath that boundary — the D3D8LTCG "mega-function"
(`docs/technical/d3d8ltcg-device-context.md`, 0x34C2E0-0x360A54, ~83 KB,
described as containing many mid-entry points that each become a separate
recompiled function), D3DX, DSOUND's internal mixer helpers, XPP
peripheral-port code, XGRPH — is statically-linked game-adjacent code that
gets lifted like any other function and runs as recompiled C, exactly like
`.text`. `docs/technical/ms-fusion-recompiler.md` contrasts this
explicitly with Microsoft's own Xbox-360 recompiler, which recompiles
*all* of this verbatim too and only HLEs at the `xboxkrnl` import boundary:

> "All of these are recompiled verbatim. None are replaced. Microsoft's
> HLE line sits at the `xboxkrnl` import boundary and nowhere else;
> graphics is emulated at the *hardware register* level, three layers
> deep."

So: **lift, don't skip.** The only genuinely-HLE'd surface is the D3D8
Device/Buffer COM interface itself (and the Xbox kernel ordinals). D3D,
D3DX, DSOUND, XPP, XGRPH, DOLBY as *sections* need to go through disasm →
func_id → abi_analysis → recomp the same as `.text`.

---

## Q2: How does the runtime treat 0xFD000000 (NV2A), 0xFE800000 (MCPX), 0xFF000000 (flash), and 0xFFFFFE00?

Source: `src/kernel/xbox_memory_layout.c` (comments) and
`docs/technical/memory-layout.md`.

| Range | Purpose | Size | Doc/source |
|---|---|---|---|
| `0xFD000000` | NV2A GPU register aperture | 16 MB (`XBOX_NV2A_SIZE`) | `memory-layout.md` table + `xbox_memory_layout.c:79-81` |
| `0xFE000000`-`0xFE000600` | Kernel thunk synthetic VAs (not real hardware) | ~600 B | `memory-layout.md` table; `docs/technical/kernel-replacement.md` |
| `0xFE800000` | MCPX southbridge register span (APU through NIC) | 8 MB (`XBOX_MCPX_SIZE`) | `xbox_memory_layout.c:83-86`: "MCPX southbridge register span: APU 0xFE800000 through NIC 0xFEF00000." |
| `0xFF000000` | Flash ROM (mirrored through top of address space) | 1 MB (`XBOX_FLASH_SIZE`) | `xbox_memory_layout.c:88-104` |

All three apertures (NV2A, MCPX, flash) are backed as **plain committed
RAM, not caught by a fault handler** — the source comment on the flash
region explains why, and it applies to all three:

> "Plain memory, like the other two apertures, and mapped for the same
> stated reason: a read of zero is survivable, a fault is not."

This is a change from the older `docs/pipeline/05-runtime.md` /
`docs/technical/memory-layout.md` description of a Vectored Exception
Handler that lazily commits a 4 KB page on first fault in the
`0xFD000000-0xFF000000` range — the current source pre-maps all three
apertures directly rather than faulting-and-committing. The flash gap was
found and fixed for exactly this class of bug — `README.md`, Xbox
Dashboard changelog entry:

> "`0xFF000000` was not mapped. The MCPX span stops one page short of the
> flash ROM, so an access that is ordinary on hardware was a hard fault.
> Backed as plain memory like the NV2A and MCPX apertures."

**`0xFFFFFE00` is not inside any of these mapped apertures.** Flash is
`0xFF000000`-`0xFF0FFFFF` (1 MB); MCPX is `0xFE800000`-`0xFEFFFFFF`
(8 MB); NV2A is `0xFD000000`-`0xFDFFFFFF` (16 MB). `0xFFFFFE00` sits
~15 MB past the end of the mapped flash region, right at the very top of
the 32-bit address space. **No doc or source comment names `0xFFFFFE00`
as a known hardware mirror, a KUSER_SHARED-style page, or any other
special address** — grepping the full checkout (docs and source) for
`0xFFFFFE`, `FFFFFE00`, `KUSER_SHARED`, and "negative index" turns up
nothing. It is not a documented address.

The closest documented parallel is `docs/technical/indirect-calls.md`'s
"Why the alignment filter is on by default" section, which describes a
crash from a read through `0xFFFFFFF3` (also near the top of the address
space) and diagnoses it as "garbage that happens to land inside `.text`,
most likely uninitialised vtable reads." Given `edx=0xFFFFFE00`,
`eax=0x8003F980` in your crash (neither value matches a documented
sentinel like the SEH end-of-chain `0xFFFFFFFF` used elsewhere in
`kernel_bridge.c` and `memory-layout.md`), the most consistent explanation
per the toolkit's own pattern (see `lessons-learned.md`, "Indirect Calls
with Corrupted Vtables" and the Q1 finding that XGRPH/XPP/DSOUND were
never lifted) is an **uninitialized-object / bad-pointer read**, not a
recognized hardware region — likely a knock-on effect of the missing
library functions from Q1 (a constructor or init routine in one of the
unlifted sections never ran, leaving a pointer/struct field as heap
garbage). Re-lifting per Q1 and re-testing before spending time on this
specific address is the efficient order of operations.

---

## Q3: What are the documented next steps once an ICALL fails to resolve?

Two independent, complementary paths are documented plus one closely
related mechanism, in this order of applicability to your log:

### 1. `tools/seed_from_log` (exact match for your `[ICALL] Failed to resolve VA` lines)

`tools/xboxrecomp/tools/seed_from_log/__main__.py` module docstring
(there is no separate `docs/*.md` page for it — the docstring is the
documentation):

> "Feed function addresses a *run* discovered back into the seed file, so
> the next codegen pass knows about them."

Its `LOG_PATTERNS` regex list matches your exact log format —
`re.compile(r"Failed to resolve VA (0x[0-9A-Fa-f]+)")` is tagged
"Indirect-call target observed at runtime" — plus thread-start-routine and
generic kernel-bridge-dispatch patterns. Usage (from the docstring):

```bash
py -3 -m tools.seed_from_log run.log game/title.xbe \
    --functions build/disasm/functions.json \
    --seeds     config/seed_functions.json
```

It gates every candidate address through two checks before seeding it
(script lines 129-134): it must fall in an executable, non-data-named
section, **and** `tools.disasm`'s own probe must read it as a valid
function body — the docstring warns that seeding a non-function address
"splits real functions and breaks the build far more thoroughly than the
missing target did," citing a real regression on Wreckless. Importantly,
this tool only helps if the target VA is already inside a section the
loader considers executable — for VAs in sections excluded by
`--text-only`, you must fix the section coverage first (Q1) or the address
will fail the "in an executable section" gate.

After seeding: `py -3 -m tools.disasm ... --seed-functions
config/seed_functions.json` (repeatable per file), then re-run
func_id/abi_analysis/recomp as in Q1.

**Note**: your 7 failing VAs are described as inside XGRPH/XPP/DSOUND,
i.e. sections that were never disassembled at all under `--text-only`.
`seed_from_log` is the tool for VAs `tools.disasm`'s static heuristics
missed *within already-covered sections* (indirect targets, thread
entries) — it is not a substitute for the `--extra-sections` fix in Q1,
which is the actual root cause here.

### 2. `RECOMP_ICALL_FEEDBACK` + `tools.recomp.icall_feedback` (for targets that remain invisible after full section coverage)

`docs/technical/indirect-calls.md`, "Target Feedback: Measure Instead of
Guess":

> "Build with `RECOMP_ICALL_FEEDBACK` defined and every indirect branch
> records its target into a flat byte array indexed by guest VA — one
> subtract, one compare, one OR on the hot path, and nothing at all in a
> default build. Dump it from `atexit` and from your crash handler..."

```c
#include "recomp_icall_feedback.h"
recomp_icall_feedback_dump("icall.txt");
```

```bash
python -m tools.recomp.icall_feedback --db game/2276/icall_targets.json \
    --functions build/disasm/functions.json merge icall.txt
python -m tools.recomp.icall_feedback --db game/2276/icall_targets.json \
    seeds --out game/2276/icall_seeds.json --align 16
python -m tools.disasm ... --seed-functions game/2276/icall_seeds.json
# re-run the recompiler; repeat
```

Key documented caveat: **seed `icall_seeds.json`, not the raw
`icall_targets.json` database** — the doc reports that seeding the raw
measured set once made a title crash *earlier* (segfault on
`0xFFFFFFF3`) because unaligned garbage targets got seeded as functions;
the `--align 16` filter (real MSVC function starts are 16-byte aligned)
is on by default in the seed step for exactly this reason.

### 3. There is no `RECOMP_ICALL_TRACE` environment variable

Grepping the full checkout (source and docs) finds no `RECOMP_ICALL_TRACE`
or `ENABLE_ICALL_TRACE` symbol anywhere. The actual mechanisms are:
the always-on 16-entry ring buffer `g_icall_trace` (compiled in, no env
var needed — `docs/pipeline/06-debugging.md`, `docs/technical/indirect-calls.md`),
the compile-time `RECOMP_ICALL_FEEDBACK` `#define` above (not an env
var), and `recomp_icall_fail_log()`'s `_ReturnAddress()`-based failure
logging, matched against the linker `.map` file
(`docs/technical/lessons-learned.md`, "The map file is your best friend").

### `recomp_lookup_manual`

Documented in `docs/pipeline/05-runtime.md` and
`docs/technical/indirect-calls.md` as Tier 1 of the 3-tier `RECOMP_ICALL`
dispatch (manual overrides checked before the auto-generated dispatch
table and the kernel bridge) — the mechanism for hand-written
replacements, not for resolving genuinely-missing lifted functions. It is
the right tool once you've identified *why* a function is broken (not
*that* it's missing), per `docs/pipeline/06-debugging.md`'s "Manual
Overrides" section.

---

## Q4: Diagnostic environment variables / compile definitions

None of these are documented in `docs/*.md` as a consolidated list — they
were found by grepping `getenv(...)` calls across `src/`. `README.md`'s
v0.7.0 changelog entry documents a subset with descriptions (quoted where
applicable); the rest are inferred from call sites with file:line
citations since no prose doc covers them.

### Documented in README.md (v0.7.0 "Non-Local" changelog)

| Variable | Meaning |
|---|---|
| `RECOMP_WATCHDOG_SECS` | "dumps the guest call stack when a title stops making progress, which is otherwise indistinguishable from working." **Caveat** (v0.10.0 changelog): inert unless the host explicitly calls `xbox_WatchdogStart()` — the `templates/new-game` template does not call it by default, so check your `main.c`. |
| `RECOMP_TRACE_ARGS` | stack arguments dumped at each traced call entry |
| `RECOMP_TRACE_DEREF` | one level of pointer dereference at each traced entry, on top of `RECOMP_TRACE_ARGS` |
| `RECOMP_PEEK` / `RECOMP_PEEK_CHAIN` | read guest dwords, or walk a pointer chain, without a run per level |
| `RECOMP_WATCH_VA` | hardware watchpoint on a guest address |
| `RECOMP_PB_SCAN` / `RECOMP_PB_EXEC` | survey a title's NV2A pushbuffer / execute its surface and clear methods |
| `RECOMP_FB_WINDOW` | opens a window on the guest framebuffer |
| `RECOMP_TRAP_NULL` | (v0.7.0 body text) makes a null-guest-pointer dereference fault immediately at the FS-base-relocated TIB, instead of surfacing later as a NaN |

### Found via `getenv()` grep (not covered by any prose doc — file:line for verification)

| Variable | File:line | Apparent purpose (from surrounding code/comments) |
|---|---|---|
| `RECOMP_WORKERS=inline` | `src/kernel/kernel_bridge.c:547,7140` | run worker threads inline instead of spawning — "answer whether a bug needs two threads" per README's v0.8.0 diagnostics list |
| `RECOMP_KERNEL_LOG_BUDGET` | `kernel_bridge.c:328` | caps kernel-call log volume |
| `RECOMP_VBLANK` | `kernel_bridge.c:1982` | enables vblank-related behavior |
| `RECOMP_FMV_HOST` | `kernel_bridge.c:2700` | host-side FMV handling toggle |
| `RECOMP_KERNEL_WATCH` / `RECOMP_KERNEL_WATCH_ALL` | `kernel_bridge.c:8659,8760` | watch specific/all kernel calls |
| `RECOMP_CMDLINE` | `kernel_bridge.c:181` | override guest command line |
| `RECOMP_CS_MODE` | `src/kernel/kernel_rtl.c:252` | critical-section emulation mode |
| `RECOMP_CS_TRACE_CRT` | `kernel_rtl.c:404` | per-lock acquire/release tracing by address (matches README's v0.8.0 diagnostics description) |
| `RECOMP_CS_WATCH` | `kernel_rtl.c:425` | watch on one lock with a guest backtrace |
| `XBOX_LOG_LEVEL` | `src/kernel/kernel_thunks.c:409` | general kernel log verbosity |
| `RECOMP_FB_DUMP` | `src/kernel/nv2a_pb_exec.c:429`, `src/video/fb_present.c:186` | dump framebuffer contents (prefix path) |
| `RECOMP_RASTER_TEST` | `nv2a_pb_exec.c:573` | rasterizer test mode |
| `RECOMP_TEX_DUMP` | `nv2a_pb_exec.c:816` | dump textures (prefix path) |
| `RECOMP_PB_EXEC_VERBOSE` | `nv2a_pb_exec.c:1271,1547,1664` | verbose pushbuffer executor logging |
| `RECOMP_FIND_NAN` / `RECOMP_FIND_QUAD` | `nv2a_pb_exec.c:1892,1898` | NV2A debugging aids |
| `RECOMP_TEX_STATE` | `nv2a_pb_exec.c:1946` | dump texture state |
| `RECOMP_PB_UNHANDLED_ALL` | `nv2a_pb_exec.c:1963` | show all unhandled pushbuffer methods (vs. first 10) |
| `RECOMP_NV2A_TRACE` | `src/kernel/xbox_memory_layout.c:1560` | NV2A MMIO tracing — **this is your D3D/NV2A tracing env var** |
| `RECOMP_AC97_READY` | `xbox_memory_layout.c:1636` | AC97 audio codec readiness toggle |
| `RECOMP_USB` / `RECOMP_USB_TRACE` | `src/usb/ohci.c:725,729` | enable USB/OHCI emulation and its tracing |
| `RECOMP_FB_VA` | `src/video/fb_present.c:37` | pin the guest framebuffer VA |
| `RECOMP_FMV_DUMP` | `src/video/video_pump.c:140,143` | dump FMV frames at specific frame numbers |
| `RECOMP_APU_DSP_ACK` | `src/apu/apu_dsp.c:61` | APU DSP acknowledgement behavior |
| `RECOMP_APU_TRACE` | `src/apu/apu_mmio_hook.c:266` | APU MMIO tracing |
| `RECOMP_TRACE_BUDGET` / `RECOMP_TRACE_PROFILE` | `src/kernel/recomp_trace.c:33,103,114` | cap trace volume / profile mode |

**No "log to file" variable found** — all diagnostics above go to
`stderr`/`fprintf(stderr, ...)` per the pattern shown throughout
`docs/technical/lessons-learned.md` and `docs/pipeline/06-debugging.md`;
redirect with `2>stderr.txt` as `docs/GETTING_STARTED.md` Step 7 already
does (`build\Release\my_game.exe 2>stderr.txt`).

**Compile-time (not env vars):** `RECOMP_ICALL_FEEDBACK` (Q3, indirect
call target recording) and `RECOMP_GENERATED_CODE` (the preprocessor
define that enables the `eax`/`ecx`/... register-alias macros in
generated files — `docs/pipeline/04-lifting.md`).

---

## Q5: VS 2022 vs VS 2019

**No doc states VS 2019 is sufficient or tested; three separate docs
state VS 2022 as the requirement, with no version floor narrower than
"2022" given anywhere:**

- `README.md` Prerequisites: "**Visual Studio 2022** (MSVC compiler)"
- `README.md` runtime dependencies: "MSVC (Visual Studio 2022) or
  MinGW-w64"
- `docs/GETTING_STARTED.md` "What You Need": "A C compiler: **Visual
  Studio 2022** (MSVC, C/C++ desktop workload) on Windows"
- `CONTRIBUTING.md`: "**Visual Studio 2022** with the C/C++ workload
  (MSVC compiler required)" and "**C11** standard, targeting MSVC (Visual
  Studio 2022)."

No doc explains *why* 2022 specifically (no MSVC-2022-only intrinsic,
`/std:` flag, or SDK feature is called out anywhere in the checkout), and
none of them mention VS 2019 by name at all — positively or negatively.
MSVC 14.29 is the VS2019 16.11 toolset (VS2022's toolsets are 14.3x), so
your successful build with 14.29 is not contradicted by any documented
claim, but it is also not a configuration the docs vouch for — the stated
requirement everywhere is VS 2022, and CI/tested behavior for VS 2019 is
undocumented.
