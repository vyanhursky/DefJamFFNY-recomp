# M2 — render path: NV2A pushbuffer executor vs D3D8 intercept, and why the main thread parks

Research date: 2026-09-17. Source: local toolkit checkout (`tools/xboxrecomp/docs/`, `src/d3d`,
`src/nv2a`, `src/kernel`), `tools/xboxrecomp/tools/func_id/output/{identified_functions,summary}.json`,
and `logs/iter8-fbwindow.log.err`. Read-only pass, nothing modified.

## Recommendation

**Target the D3D8 intercept path (`src/d3d`), not the NV2A pushbuffer software executor
(`src/kernel/nv2a_pb_exec.c`), for M2.** Def Jam: Fight for NY is XDK 5849 — the *same* XDK build as
Burnout 3, the toolkit's one proven target — and its D3D section starts at the identical virtual address
Burnout 3's does (`0x0034C2E0`, confirmed from `tools/func_id/config.py`'s `SECTIONS` table against
`docs/technical/d3d8ltcg-device-context.md`'s worked example). Both games statically link the D3D8LTCG
library and both are Criterion-engine/RenderWare titles; `docs/technical/candidate-games.md:125` calls
RenderWare titles "a natural second target" because "the kernel layer, memory layout, and D3D8
abstraction from Burnout 3 are directly reusable." That is a direct, address-verified match, not a
guess.

The currently-enabled `RECOMP_PB_EXEC=1` path is explicitly a bring-up diagnostic, not a renderer: its
own header comment (`src/kernel/nv2a_pb_exec.c:10-17`) says it "rasterises geometry, but only the part
that can be drawn honestly: batches whose attribute 0 is already in screen space, flat-shaded" and that
"Texturing, depth and vertex programs are still a renderer, not a command decoder." `docs/technical/gap-
analysis.md:19` marks full PFIFO pushbuffer parsing `N/A — Low (D3D8 API intercept instead)`. It is the
right tool for confirming a title is producing *any* pixels (which it just did — Def Jam booted, built a
pushbuffer, and vblank/ISR/DPC all work), not for shipping 3D or FMV.

**Do not spend more time on the pushbuffer executor's own black-screen symptom** (`draws 0`, all ten
top unhandled methods are ordinary pre-draw state setup — `NO_OPERATION`, `WAIT_FOR_IDLE`, clip
min/max, viewport offset, z/stencil clear value, dither enable — none of them exotic). The park is not a
rendering gap, it's a **synchronization gap**: the toolkit has generic mechanisms for exactly this
situation (`xbox_Nv2aMirrorFence`, `xbox_Nv2aMirrorCounter`, the `NV2A_ACK`/`NV2A_IDLE` tables, all in
`src/kernel/xbox_memory_layout.c`), and **none of them have been registered for Def Jam yet** — the
iter8 log contains no `"NV2A fence mirror"`, `"NV2A counter mirror"`, or `"Frame counter"` startup lines,
even though `NV2A] DMA_PUT = DMA_GET` already agree (the PFIFO-level ack table is already covering the
push-buffer-full case). The watchdog stack shows the guest looping over the same ~8 kernel-thunk targets
(`FE000004/…/FE0001FC` repeating, `logs/iter8-fbwindow.log.err:1116`) with `FD000000` sitting on the
guest stack — the signature of a title re-polling an NV2A register or a GPU-owned counter that this
runtime never advances, the same class of bug `xbox_memory_layout.c:312-336` was written to fix for the
Xbox Dashboard's swap-throttle pair.

**First 5 concrete steps** (details in §4):
1. Diff Def Jam's D3D section against `docs/technical/d3d8ltcg-device-context.md`'s Burnout-3-derived
   offset map (push-buffer ring at +0x00.. +0x4C, `pb_gpu_read_ptr` at +0x30) to confirm the layout is
   identical or find the deltas.
2. Run `tools/symbols/map_names.py port` with Burnout 3's MAP as donor to auto-name Def Jam's D3D/D3DX/
   XGRPH functions and locate the mid-entry stub addresses (the `sub_0034xxxx` table in gap-analysis.md
   is Burnout-3-specific addresses; Def Jam's will differ even though the section VA matches).
3. Apply the same class of `recomp_lookup_manual` overrides gap-analysis.md documents for Burnout 3's
   mid-entry stubs (return current PB position; `esp` cleanup per call site).
4. Apply the device-context GPU-read-pointer self-reference fix (`MEM32(dev+0x30) = dev+0x2C`) so the
   D3D8LTCG spin-wait exits immediately, and register a fence/counter mirror via
   `xbox_Nv2aMirrorFence`/`xbox_Nv2aMirrorCounter` for whatever swap-throttle pair Def Jam's loop turns
   out to poll (this is very likely what the current park actually is).
5. Once the D3D8LTCG code is unblocked, its draws flow through `src/d3d/*` (the D3D11-backed compat
   layer, already DONE for FVF transform, texture stage states, combiners, vertex shader microcode,
   lighting, fog — see gap-analysis.md's D3D8 Translation Layer table) instead of through the pushbuffer
   executor, which is expected to produce the EA logo/FMV quad correctly where the diagnostic path
   cannot (no texturing, no vertex programs).

---

## 1. Two rendering strategies, and which is production

**(a) NV2A pushbuffer software executor** — `src/kernel/nv2a_pb_exec.c` (1,988 lines), enabled by
`RECOMP_PB_EXEC`. Walks the same command stream `nv2a_pb_scan.c` surveys and executes the subset that
"decides what is on screen": surface/clear state and flat-shaded, already-screen-space geometry only
(`nv2a_pb_exec.c:1-26`). Its own doc comment says texturing/depth/vertex-programs are "still a renderer,
not a command decoder; the upgrade path is the D3D11 translator in `src/nv2a/nv2a_pgraph_d3d11.c`"
(line 17) — but that translator (`nv2a_pgraph_d3d11.c` + `nv2a_pb_replay.c`) turns out to be Burnout-3
menu-specific: its own header says it replays **captured push buffer snapshots from xemu** for eight
named Burnout 3 menu states (`main_menu`, `world_tour`, `single_event`, …, `nv2a_pb_replay.c:8-16`) and
is gated behind `#ifdef GAME_HAS_FONT_ATLAS` referencing a reference-title font atlas
(`nv2a_pgraph_d3d11.c:26-41`). It is not a general NV2A-to-D3D11 renderer; it is Burnout 3's own
hand-authored menu frontend, reusing the file layout. Treat it as inapplicable to Def Jam.

`docs/technical/gap-analysis.md:19` states directly: `Push buffer parsing (PFIFO DMA pusher) | Full |
Stub | N/A | Low (D3D8 API intercept instead)` — the toolkit authors' own prioritization already says
full pushbuffer decode is *not* the path, ranked Low.

**(b) D3D8 API intercept** — `src/d3d/*` (`d3d8_device.c`, `d3d8_resources.c`, `d3d8_shaders.c`,
`d3d8_states.c`, `d3d8_combiners.c`, `d3d8_vsh.c`, `d3d8_swizzle.h`, `d3d8_fvf.h`, `d3d8_gl.c`,
`d3d8_gamma.c`), documented in `docs/technical/d3d-translation.md` and
`docs/technical/d3d8ltcg-device-context.md`. Intercepts D3D8 calls (COM vtable dispatch for a normal
build, or fixed guest VAs for an LTCG build) and re-implements them against `ID3D11Device`/
`ID3D11DeviceContext`. `docs/technical/d3d-translation.md:1-28` is explicit about the architecture:
"The recompiled game code calls D3D8 methods through COM vtable pointers, and our translation layer
intercepts these calls and routes them to D3D11."

**What Burnout 3 / the Dashboard actually do:** `docs/technical/candidate-games.md:17-28` — Burnout 3 is
"The first game successfully targeted by this toolkit," "boots, loads game data, runs gameplay loop with
a custom rendering frontend," and is statically linked against D3D8LTCG among 11 XDK libs. It is the
**proven production path**, and it goes through the D3D8/D3D11 bridge (`src/d3d`), not through NV2A
pushbuffer decode — the NV2A pushbuffer executor exists in the toolkit for titles/bring-up phases where
the D3D8LTCG device-context work hasn't been done yet (exactly Def Jam's current state). The Xbox
Dashboard is used elsewhere in the toolkit (`nv2a_pb_exec.c:1085-1092`, `xbox_memory_layout.c:47-53`) as
the reference case that *exposed bugs in* the diagnostic executor (screen-space classification, the
"don't clear over the title's own image" guard) — it is a test case for path (a)'s honesty, not evidence
path (a) is how a shipped title renders.

**`d3d8ltcg-device-context.md` on D3D8LTCG builds:** applies to "Xbox games using Criterion's
RenderWare engine (and potentially other Xbox D3D8 games)... using a statically-linked D3D8LTCG library
that maintains a ~16KB device context structure" (line 5), explicitly scoped to "Xbox games using XDK
D3D8LTCG (Burnout 3, possibly other Criterion/RenderWare titles)" (line 7) — Def Jam: Fight for NY is
exactly that: Criterion RenderWare, XDK 5849. The doc gives:
- **Device context is static**, not heap-allocated, living inside the D3D section itself; example
  address `0x0035D6A0` in a D3D section starting at `0x0034C2E0` (`d3d-translation.md:520-524`) —
  **this is Def Jam's own D3D section start address**, per `tools/func_id/config.py`'s `SECTIONS` table
  (`("D3D", 0x0034C2E0, 83828, 0x0033F000)`), and the doc's mega-function end address `0x00360A54`
  matches Def Jam's next section, XGRPH, starting at `0x00360A60` (config.py). The doc was almost
  certainly written from data that is Def Jam's own binary layout, or a byte-identical Burnout-3 build.
- **Identification/replacement is neither OOVPA nor a runtime function-signature scan.** No `OOVPA`
  string appears anywhere in the toolkit (`grep -rn OOVPA` over the checkout returns nothing). Instead:
  a fixed **VA table via `recomp_lookup_manual`** (see §2) for the mid-entry stub functions inside the
  single 83 KB D3D8LTCG mega-function, plus a captured **device-context memory snapshot** taken from
  xemu at a known guest address and loaded at boot with pointer fixups (`d3d-translation.md:583-601`,
  `d3d8ltcg-device-context.md:174-188`). Static, one-time VA discovery — not per-call pattern matching.

## 2. What a game project must provide for the D3D8 intercept path

**Entry points a normal (non-LTCG) D3D8 vtable build redirects**, from `src/d3d/README.md` and
`docs/technical/d3d-translation.md`: `Direct3D_CreateDevice`/`xbox_Direct3DCreate8`, `CreateDevice`,
`BeginScene`/`EndScene`/`Clear`, `Present` (wrapped by `d3d8_PresentFrame()`, which also pumps the Win32
message loop — `d3d-translation.md:493-510`), `SetTransform`/`GetTransform`, `DrawPrimitive`/
`DrawIndexedPrimitive`/`DrawPrimitiveUP`/`DrawIndexedPrimitiveUP`, `CreateTexture`/`CreateCubeTexture`/
`CreateVolumeTexture`/`CreateImageSurface`, `CreateVertexBuffer`/`CreateIndexBuffer`, `Lock`/`Unlock`
(staging-buffer pattern, `d3d-translation.md:100-125`), `SetTexture`/`GetTexture`,
`SetStreamSource`/`SetIndices`, `SetRenderState`/`SetTextureStageState`, `SetVertexShader`/
`SetPixelShader`, `SetViewport`, `SetRenderTarget`/`CreateRenderTarget`/`CreateDepthStencilSurface`, and
the Xbox extensions `BeginPush`/`EndPush` (direct pushbuffer access) and `Swap` (`src/d3d/README.md:
214-265`). This is a static const vtable (`g_device_vtbl` in `d3d-translation.md:57-69`) — a single
global device instance, matching "Xbox has a single D3D device."

**For a D3D8LTCG build (Def Jam's case), the mechanism is different**: there is no vtable call site to
intercept because the library is inlined into the game binary as one giant function with many "mid-entry
points" depending on dirty flags (`d3d-translation.md:548-560`). Redirection happens per guest VA through
the **same generic mechanism the whole toolkit uses for any manual override**:
```c
// recomp_manual.c (game project, not the toolkit)
recomp_func_t recomp_lookup_manual(uint32_t xbox_va) {
    switch (xbox_va) {
        case 0x0034D410: return manual_full_entry;      // full flush entry
        case 0x0034D530: return manual_standard_entry;   // standard entry -> capture PB output
        case 0x0034F5B0: return manual_stub_partial;      // stub: return current PB pos, esp+=4
        case 0x003558A0: return manual_stub_minimal;      // stub: return current PB pos, esp+=4
        default: return NULL;
    }
}
```
documented in `docs/pipeline/05-runtime.md:330-352` and `docs/technical/indirect-calls.md`. The correct
`esp` cleanup per stub must be derived by counting `PUSH32` sites before each call
(`d3d8ltcg-device-context.md:107-148`); getting this wrong corrupts the Xbox stack, since an empty
`void sub(void){}` stub does not pop the return address/params the caller pushed.

**Device-context struct layout** (`d3d8ltcg-device-context.md`, offsets from the static device base,
`MEM32(0x35FB48)` in the Burnout-3-address example — Def Jam's global pointer will need re-deriving but
the section/context layout is expected to match closely): push-buffer ring management at +0x00..+0x4C
(`pb_put`, `pb_limit`, `pb_ring_start/end`, `pb_write_seq` at +0x2C, **`pb_gpu_read_ptr` at +0x30 is
critical** — it is a pointer, and on hardware the GPU advances what it points to; render state at +0x784
(render target), +0x794 (depth/stencil), +0x7A8 (back buffer), +0x954/+0x958 (viewport w/h); double-
buffered render target pointers at +0x1974/+0x1978 (must be non-NULL — camera orchestrator skips
rendering if NULL, line 58-63); pre-render callback at +0x19FC; frame counter at +0x2478.

**How the runtime creates the D3D11 window/device**: `docs/pipeline/05-runtime.md`'s Startup Sequence
(§ Startup Sequence, steps 1-8) — after memory layout and kernel init, "Create the window and D3D11
device" happens before the decoded entry point is called; the D3D8-to-D3D11 bridge's `CreateDevice`
wraps `IDXGISwapChain`/`ID3D11Device` creation (`d3d-translation.md`'s Present/Window Management
section, lines 493-510, shows the message-pump + `IDXGISwapChain_Present` pattern used per frame).

**Helper tool for automatic VA discovery**: `tools/symbols/map_names.py port` mode
(`tools/symbols/map_names.py:189-239`, driven from `tools/symbols/lib_port.py`/`rw_port.py`). It is
**byte-signature matching, not OOVPA**: `port_names()` takes a *donor* binary with known symbols (a MAP
file — e.g. one that names Burnout 3's functions) and a fixed-length opening-byte signature per donor
function within the XDK library sections (`D3D,D3DX,DSOUND,WMADEC,XGRPH,XPP,...`,
`DEFAULT_XDK_SECTIONS`), searches the target XBE's same-named sections for a **unique** match, and keeps
only matches that land on a function-start address the target's own `tools/func_id`/`tools/disasm`
detector already found (`map_names.py:137-179`). `lib_port.py` does the analogous thing straight from a
COFF `.lib` archive (e.g. XDK's `rwcore.lib`/`d3d8.lib`) by pulling each function's own compiled opening
bytes out of the archive's object members — no MAP needed at all. The tool explicitly notes XDK-version
mismatch between donor and target is tolerated ("library code is largely stable across versions,"
`map_names.py:229-235`) — directly applicable given Def Jam and Burnout 3 share XDK 5849 exactly. This
is the concrete next step to locate Def Jam's D3D8LTCG mid-entry addresses (equivalent to Burnout 3's
`0x0034D410`/`0x0034D530`/`0x0034F5B0`/`0x003558A0` table) without hand reverse-engineering them.

## 3. What "main thread parks after the first pushbuffer batch" usually means

This toolkit has a documented, recurring failure family: **Xbox D3D/kernel code talks to hardware via
set-a-bit/wait-for-hardware-to-clear-it handshakes, or via counters only a real GPU would advance; run
against plain zeroed RAM, the wait spins forever.** `xbox_memory_layout.c` implements the fix for each
known instance as a table the caller must register — none of which had been wired up for Def Jam as of
`logs/iter8-fbwindow.log.err`:

- **`NV2A_ACK`** (`xbox_memory_layout.c:170-188`) — "busy-bit acknowledgement": specific aperture offsets
  where a set-and-wait-for-hardware-to-clear bit is force-cleared by a background thread (e.g. Halo's PFB
  flush kick at aperture 0x100410, bit 0x10000) and interrupt-status registers held permanently at 0
  (nothing here raises real GPU interrupts, so that's the honest value).
- **`NV2A_IDLE`** (lines 190-205) — bits that must read SET because they mean "queue empty" and nothing
  is ever queued (PFIFO_RUNOUT_STATUS, CACHE1_STATUS low-water marks).
- **PFIFO channel DMA_PUT/DMA_GET** (lines 207-231, `NV2A_USER_DMA_PUT/GET` at aperture offset
  0x800040/0x800044) — copying PUT to GET is the acknowledgement that the pushbuffer was "consumed."
  **This one is already working for Def Jam** — the log shows `DMA_PUT == DMA_GET` at every sample from
  `0x012044F0` onward (`logs/iter8-fbwindow.log.err:971-1109`), so this is not what's parking the thread.
- **Fence mirrors, `xbox_Nv2aMirrorFence`/`fence_mirrors_tick()`** (lines 260-513) — "GPU completion
  fences the title waits on in guest memory rather than in the aperture." A title writes a target value
  and polls a guest-memory location the GPU is supposed to write back; the mirror copies PUT to that
  location once the device pointer is registered. `NV097_SET_SEMAPHORE_OFFSET` /
  `NV097_BACK_END_WRITE_SEMAPHORE_RELEASE` (`nv2a_regs.h:1268-1269`) are the hardware-level version of
  this same handshake.
- **Counter mirrors, `xbox_Nv2aMirrorCounter`/`counter_mirrors_tick()`** (lines 312-357) — the
  "submitted vs. completed" pair D3D's swap throttle uses; documented worked example is the Xbox
  Dashboard's exact spin at guest `0x000AF121` (`[esi+0x2518]` completed vs. `[esi+0x2B60]` submitted,
  spinning on a 400-iteration delay loop once 2 frames are outstanding — measured at "99.8 million of the
  dashboard's calls"). `NV097_SET_REFERENCE` is the hardware register family this pattern maps to; the
  fix is the same shape as the fence mirror, just for a plain counter pair instead of a pointer-chased
  fence.
- **Frame counters, `xbox_Nv2aFrameCounter`/`frame_counters_tick()`** (lines 384-485) — a swap counter a
  title spins on waiting for it to advance by N frames; ticked at 60 Hz until real presents start, then
  driven off actual flips instead (explicitly *not* run off the synthetic clock once flips are real,
  because that desynced Half-Life 2's FMV pacing, per the comment at lines 420-430).

**What the executor does NOT emulate, that a title would poll forever on**: `nv2a_pb_exec.c` only
"decides what is on screen" for the subset of methods listed at lines 136-186 — it never touches PFIFO/
PGRAPH status registers, never advances a GPU-owned completion fence in guest memory, and never
advances a submitted/completed counter pair. Any D3D8LTCG code that finishes building a batch and then
polls one of those for the *next* batch's buffer space (exactly the `d3d8ltcg-device-context.md:79-99`
"GPU Read Pointer Problem" spin-wait: `do { gpu_read = MEM32(MEM32(device+0x30)); } while (requested >
available);`) spins forever unless `MEM32(device+0x30)` has been pointed at `device+0x2C` per that doc's
fix, or a fence/counter mirror has been registered for whatever guest address the title actually polls.

**Diagnosis for Def Jam specifically**: no `"NV2A fence mirror"`, `"NV2A counter mirror"`, or `"Frame
counter"` line appears anywhere in `logs/iter8-fbwindow.log.err` (only `"RAM mirror: 28/28 views
mapped"`, a different, unrelated mirror system for address-space aliasing) — meaning **none of these
registration calls have been made for this game yet**, even though `xbox_Nv2aMirrorFence`/
`xbox_Nv2aMirrorCounter` exist and are ready to use. Combined with the watchdog snapshot showing the
guest looping over a tight, repeating set of kernel-thunk targets (`FE000004 FE000008 001ED620 FE000004
FE0001F8 FE0001F4 FE00003C FE000008 FE0000F0 FE000004 FE000008 FE0001FC …`, `logs/iter8-
fbwindow.log.err:1116`, 25,222 ICALLs by the time the 25s watchdog fires) with `0xFD000000` (the NV2A
aperture base) sitting on the guest stack (`logs/iter8-fbwindow.log.err:1122`), this reads as exactly
the documented pattern: the title finished one pushbuffer batch, then entered a spin-wait on an NV2A
register or a GPU-owned counter this runtime has not yet been told to acknowledge for this title.

## 4. Concrete M2 plan: 721 D3D-section functions, 575-797 game_render

Current `tools/func_id` output (re-measured directly from `identified_functions.json`/`summary.json` in
this pass — the question's cited "316 game_render" figure appears stale, current totals are higher):
`total_functions: 20387`, `by_category.game_render: 797` overall, and specifically **721 functions in
the `D3D` section** (`("D3D", 0x0034C2E0, 83828, ...)` per `sections` breakdown), of which **575 are
already classified `game_render`** and 719 remain `unknown` within D3D-ish sections (D3D+D3DX+XGRPH
combined: 1,297 functions). This matches the task's "721 D3D-section functions lifted" figure exactly.

**NV2A executor path vs. D3D8 intercept path — work estimate:**

| | NV2A pushbuffer executor (a) | D3D8 intercept (b) |
|---|---|---|
| What exists already | Flat/untextured 2D rasterizer, diagnostic-only, already running (`RECOMP_PB_EXEC=1`) | Full D3D11 backend: FVF transform, 4-stage TSS, combiners, NV2A vertex-shader microcode, 8-light T&L, fog, mip chains, cube/volume textures — all `DONE` per gap-analysis.md |
| What's missing for Def Jam | Texturing, vertex programs, depth — explicitly out of scope by design (would mean building a second, parallel renderer) | D3D8LTCG entry-point VA table + device-context init for *this* binary (Burnout 3's addresses don't transfer, only the *offset layout* likely does) |
| Ceiling | Never reaches parity with (b); "not a command decoder" by the code's own comment | Full-featured; proven on Burnout 3 |
| Estimated effort to M2 (EA logo) | Large and open-ended (would need to hand-roll texturing/vertex-program support inside the diagnostic executor, duplicating (b)) | Moderate: symbol porting + stub table + device-context wiring, using a documented, address-matching template |

**Recommendation: D3D8 intercept path (b).** The address match to Burnout 3's D3D section, the shared
XDK 5849, and the shared RenderWare/Criterion engine make this a template-following exercise rather than
new design work, and it reaches a real renderer (needed well past M2) instead of a diagnostic dead end.

**First 5 concrete steps:**
1. **Confirm the device-context offset map holds for Def Jam.** Cross-reference `d3d8ltcg-device-
   context.md`'s offset table against Def Jam's D3D section disassembly (`tools/xboxrecomp/tools/disasm/
   output/`) at the same relative offsets (+0x00 PB put, +0x30 GPU read ptr, +0x784/+0x794/+0x7A8
   surfaces, +0x1974/+0x1978 double-buffered RT). Because the section VA is identical to the doc's
   example, this is a direct diff, not a fresh RE pass.
2. **Run `tools/symbols/map_names.py port`** with a Burnout 3 MAP/analysis pair as donor (`--donor-map`,
   `--donor-xbe`, `--donor-analysis`) against Def Jam's target XBE/analysis/functions
   (`tools/func_id/output/identified_functions.json` already has the target function starts), sections
   `D3D,D3DX,XGRPH`, to name Def Jam's mid-entry stub addresses (the equivalents of Burnout 3's
   `0x0034D410/0x0034D530/0x0034F5B0/0x003558A0`).
3. **Write the `recomp_lookup_manual` stub table** in the Def Jam project's `src/recomp_manual.c` for
   every mid-entry point found in step 2, following the `esp` cleanup derivation method in
   `d3d8ltcg-device-context.md:133-148` (count `PUSH32`s before each call site).
4. **Apply the GPU-read-pointer self-reference fix and register a fence/counter mirror.** Set
   `MEM32(dev+0x30) = dev+0x2C` at device-context init, and call `xbox_Nv2aMirrorFence`/
   `xbox_Nv2aMirrorCounter` for whichever swap-throttle pair the watchdog stack trace (§3) turns out to
   be polling once symbol names make that identifiable — this is the most likely actual fix for the
   current park.
5. **Boot with `RECOMP_PB_EXEC` off** (or leave it as a fallback comparison) once the D3D8LTCG entry
   points route through `src/d3d`, and verify the EA logo/FMV quad renders via the D3D11 backend instead
   of the flat rasterizer — cross-check against `nv2a_pb_exec_report()`'s texture-usage stats
   (`RECOMP_TEX_STATE`, `TEXUSE` lines) to confirm real texture reads are happening once the intercept is
   live.

## 5. FMV: `src/video` and Def Jam's EA "MADk" format

The toolkit's shared FMV player (`src/video/video_player.c`/`video_pump.c`/`video_player.h`) is Media
Foundation-based and explicitly **container-agnostic in the wrong direction**: "For a title whose video
is a container Windows can already decode, the decoder does not have to be emulated for the video to be
watchable" (`video_player.h:4-7`). It owns its own window, D3D8 device, and Media Foundation session on a
dedicated thread (`video_pump.c:1-11`), so playback doesn't block the guest.

**How it's hooked in — not a codec-specific VA override.** The hook point is generic and file-extension
based, at the kernel file-open boundary, not at any XMV/Bink/decoder function: `kernel_bridge.c`'s
`bridge_NtCreateFile` (ordinal 190) — after the real file open succeeds — checks, only when
`RECOMP_FMV_HOST` is set, whether the just-opened host path ends in `.wmv`, and if so and nothing is
already playing, calls `xbox_VideoPlayFile(host)` (`kernel_bridge.c:2687-2719`). The comment is explicit
about the mechanism: "The trigger is the title opening the file, so this plays when the game decides to
play it... it plays the file the game chose." There is no separate hook for `XMV`/Bink decode functions
in the toolkit; `xbox_VideoPlayFile` is not called anywhere else in the checkout.

**Def Jam uses EA "MADk" videos (e.g. `movies\eagames.mad`), not XMV or Bink — implications:**
- The extension check is hardcoded to `.wmv` only (`_stricmp(host + n - 4, ".wmv")`,
  `kernel_bridge.c:2716`). A `.mad` file will never trigger this path as written — the check needs
  extending (or the resolved host path needs to be an already-transcoded `.wmv` sitting alongside the
  original, matched by convention) before this mechanism does anything for Def Jam at all.
- More importantly, **Windows Media Foundation has no native EA MADk decoder.** XMV works with this
  scheme "for free" because XMV wraps WMV video/WMA audio, which MF decodes natively — that's exactly
  the case the player's own doc comment describes. EA's MADk container/codec (used across several
  Criterion/EA titles of this era) is proprietary and unsupported by any stock Windows codec, so the
  same trick (point Media Foundation at the original asset) will not work for Def Jam's intro movie
  regardless of the extension-check fix.
- Practical options, in order of effort: (1) skip/stub the intro movie read entirely for M2 (many titles
  proceed to the main menu on a failed/skipped movie open — check what Def Jam's own code does on an
  `NtCreateFile` failure for the movie, which may already be a viable path given `[FILE]` failures are
  logged as informative, not fatal, per `kernel_bridge.c:2721-2734`); (2) have the *user* transcode their
  own legally-dumped `.mad` to `.wmv`/`.mp4` locally (never shipped, never committed — consistent with
  `CLAUDE.md` §3's hygiene rules) and extend the extension match to redirect to that sidecar file; (3)
  write an actual MADk demuxer/decoder, which is real reverse-engineering work and should not block M2
  (boot to EA logo) — better attempted after the D3D8 intercept path is otherwise rendering, so any
  intro-movie work isn't blocking gameplay-critical rendering.

---

## Sources (all local, read-only)

- `tools/xboxrecomp/docs/technical/d3d-translation.md`
- `tools/xboxrecomp/docs/technical/d3d8ltcg-device-context.md`
- `tools/xboxrecomp/docs/technical/gap-analysis.md`
- `tools/xboxrecomp/docs/technical/candidate-games.md`
- `tools/xboxrecomp/docs/pipeline/05-runtime.md`
- `tools/xboxrecomp/docs/technical/indirect-calls.md`
- `tools/xboxrecomp/src/kernel/nv2a_pb_exec.c`
- `tools/xboxrecomp/src/kernel/xbox_memory_layout.c`
- `tools/xboxrecomp/src/kernel/kernel_bridge.c`
- `tools/xboxrecomp/src/nv2a/README.md`, `nv2a_regs.h`, `nv2a_pgraph_d3d11.c`, `nv2a_pb_replay.c`
- `tools/xboxrecomp/src/d3d/README.md`
- `tools/xboxrecomp/src/video/video_player.h`, `video_pump.c`
- `tools/xboxrecomp/tools/func_id/config.py`, `tools/xboxrecomp/tools/func_id/output/{identified_functions,summary}.json`
- `tools/xboxrecomp/tools/symbols/map_names.py`, `lib_port.py`
- `logs/iter8-fbwindow.log.err`
