# GPU reconciliation for the xboxrecomp rebase

2026-10-03. Static, bounded audit; no builds, tests, game runs, source edits, fetches, or Git mutations were performed by this audit. The main agent owns the migration and runtime measurements.

Comparison: cached upstream `1409a7d7801d3e931fb1074be6104209ddd9a33e` against the pre-rebase local toolkit working tree based on `6f55eaa29d369860c950f442649e23ca86a3c275`. "Ours" line references below identify that pre-rebase working tree, including untracked added modules; "upstream" references identify `git show 1409a7d:<path>`. They are snapshot references and will move during the migration.

## Recommended decision

Keep the upstream pushbuffer executor, CPU vertex-program interpreter, software rasterizer, and named combiner/texture state as the starting point. Port our D3D11 rendering and program compilation onto that state. Retain our resumable walker and release/fence implementation as a connected package. Do not replace the entire upstream executor or memory-layout file with ours, and do not compile both vertex interpreters unchanged.

This retains upstream's richer CPU fallback while preserving the working Def Jam D3D11 route. The initial integration can remain in these files; splitting the executor into a new renderer architecture is a separate, deferred task.

## Function-level map

| Area | Common / compatible | Material divergence and reconciliation |
|---|---|---|
| Vertex fetch | `fetch_attr` supports D3DCOLOR, float, normalized byte, normalized/as-is signed short and packed 11:11:10 in both trees (ours `src/kernel/nv2a_pb_exec.c:510`, upstream `:466`). `dma_resolve` is shared in purpose (ours `:90`, upstream `:97`). | Keep upstream implementations. Preserve our 32-bit guest indices, `ARRAY_ELEMENT32`, 32,768-index capacity and truncation diagnostics; upstream uses 16-bit indices and 4,096 capacity (`:227`, `:253`, `:3056`), which would truncate DRAW_ARRAYS's 24-bit start. Keep upstream's 65,536-dword inline capacity (`:229`), versus ours 4,096 (`:212`), while checking downstream capacities. |
| Batch assembly | BEGIN/END chooses immediate, inline, or indexed arrays in both trees (ours `:2667`, upstream `:3011`). Inline data synthesizes an attribute layout and enters the ordinary batch path (upstream `:2595`). | Keep upstream immediate attributes (`imm_attr[16][4]`, `:264`) and its richer immediate methods (`:2720`). Adapt D3D forwarding to fetch through the existing batch abstraction; preserve state save/restore. Do not transplant our reduced `imm_pos/imm_diffuse/imm_tex` state. |
| CPU rasterization | The executor is the draw boundary. | Upstream `raster_batch_program` (`:2179`) executes its interpreter and consumes position, both colors, fog and four texture results. Ours CPU-to-D3D ready path only carries position, diffuse and stage-0 UV (`:1984`). Keep upstream CPU rasterization as the software backend; the existing ready path remains a narrower D3D fallback until explicitly expanded. |
| Texture state | Common offset, format, dimensions, pitch, address modes and palette fields. | Upstream has `texs[4]`, filter, mip levels and cube flag (upstream `:237`, `:303`); ours has stage-0 `tex` plus raw registers for the others (ours `:269`, `:1715`). Add our CONTROL0 disabled flag and palette length to upstream stage state. Keep upstream fields instead of replacing its struct. |
| Combiners | Both consume the same register ranges and final constants. | Keep upstream `Nv2aCombiner` (`src/kernel/nv2a_combiner.h:22`) as canonical state. Bridge its named arrays directly to `d3d8_combiners_set_nv2a`. Ours `pgraph_d3d11_set_combiners` (`src/nv2a/nv2a_pgraph_d3d11.c:1144`) currently reinterprets three raw arrays; do not perpetuate a second state store. Preserve control, final0/1, final constants and stage_program. |
| D3D vertex shader / gamma | `src/d3d/d3d8_vsh.c` and `d3d8_gamma.c` have no net local change versus upstream. | Retain upstream files. `d3d8_vsh.c` decodes a different upload layout than the direct NV2A pushbuffer program; it is not a replacement for the NV2A interpreter/emitter. |
| Resource swizzles | Our `d3d8_shaders.c` changes are small additions to sampling semantics. | Port them with `d3d8_texel_swizzle` in resources/internal header. Modes 1/2/3 implement A8, luminance, luminance+alpha. Keep upstream's other resource and palette work. |
| Host device | Added external-VS draw entry, logical/physical render dimensions, scaled scissor, blend color, and debug messages are compatible additions. | Port individual additions, preserving upstream surroundings. Keep logical dimensions returned by `GetBackbufferWidth/Height`, actual D3D render size multiplied by `RECOMP_RENDER_SCALE` (ours device `:182`, `:264`), and scaled scissor (`:1437`). Present vsync remains opt-in (`:134`) alongside guest FLIP pacing. |
| CMake | Added `d3d8_extvs.c` is required for the GPU program path. | Keep upstream `nv2a_vsh_interp.c` and `nv2a_combiner.c` in kernel sources; merge emitter helpers there. Add `d3d8_extvs.c` only to the Windows D3D target. Do not copy our unrelated regression from `${EPOXY_LINK_LIBRARIES}` back to `${EPOXY_LIBRARIES}`. |

## Method and draw flow to preserve

1. The walker decodes packets, records the survey, and calls the executor once per method. Ours does not have an independent second rendering decoder (`nv2a_pb_scan.c:393`).
2. Our executor forwards methods to PGRAPH before rejecting nonzero subchannels (`nv2a_pb_exec.c:2566`). Preserve that ordering and our semaphore release (`:2611`), pattern-color write (`:2613`), point size (`:2616`), and parameter-NOP software-method/stall handling (`:2619`). Upstream rejects nonzero subchannels at `:2912`; copying that early return unmodified would drop these behaviors.
3. Upstream texture handling returns early at `:2908`. The D3D method forwarder and any required raw diagnostic recording must precede it. Keep upstream CPU alpha/fog/report methods (`:2970`) and canonical combiner setters (`:2949`, `:3186`).
4. Upstream transforms use execution mode, program load/start, constant load and the context-write enable (`:3161`). Viewport offset/scale mirror into constants 59/58 (`:3210`). Route these through a single program state before returning; do not leave our `nv2a_vsh_method` as a second parallel program consumer.
5. At END, forward the assembled batch through our D3D adapter, or run upstream software rasterization according to the backend setting. Ours calls `raster_batch()` before the D3D block (`:1793`), but its `soft_raster_on()` suppresses software framebuffer writes when `RECOMP_PB_D3D11` is present (`:696`). Carry this suppression into upstream's clear and raster paths so D3D mode does not unexpectedly write guessed surfaces into guest memory.
6. Our GPU route reads only inputs used by the program, fetches each distinct guest vertex, reindexes into local 16-bit GPU indices, and triangulates (`:1853`, `:1903`, `:1938`). Guest indices must remain 32-bit until this bounded reindex step.
7. Bind enabled textures, addresses/filters, surface clip and combiners, then draw either the compiled program or CPU-transformed ready vertices (`:2065`, `:2242`). CPU-only D3D fallback presently unbinds stages 1–3; preserve this known behavior during baseline migration and record its limitation.
8. FLIP_STALL updates read position/frame counter, paces, flushes and presents (`:2759`). Our executor directly calls the game-owned `d3d11_translator_frame_end` at `:2779`; the upstream new-game template contains no implementation. Make this a registered optional callback with a null/default path when preparing a generic toolkit contribution. Until then, confirm the Def Jam host link still supplies it.

The old PGRAPH guessed inline packet draw must stay suppressed by default (`nv2a_pgraph_d3d11.c:287`, `RECOMP_TRANS_INLINE_DRAW`). Enabling it alongside executor forwarding can duplicate draws and revive the magenta-mask behavior.

## Primitive numbering: fix only the divergent CPU constants

Hardware values are points=1, lines=2, line loop=3, line strip=4, triangles=5, strip=6, fan=7, quads=8, quad strip=9, polygon=10 (upstream executor `:1481`). Our old CPU rasterizer instead defines triangles=4 through quad strip=8 (ours `:1339`), and its fan/quad treatment is also less complete (`:1412`).

Our D3D topology mapper already uses correct hardware values (`nv2a_pgraph_d3d11.c:87`). Its ready quad conversions use 8/9 (`:1430`), and the GPU batch conversion uses 5–10 (`nv2a_pb_exec.c:1938`). Retain upstream CPU topology; do not apply a blanket +1 shift to D3D parameters or methods. Preserve point and polygon handling explicitly, and check triangle strip parity if culling is ever enabled (the current renderer disables culling).

## One vertex-program state, two execution backends

Upstream `nv2a_vsh_interp.h` exposes upload setters, instruction/constant fixture APIs, context-write control and CPU execution (upstream `:40`–`:59`). Its output contains position, d0, d1, fog and tex[4]. Ours `nv2a_vsh_cpu.h` exposes method decoding, current values, input-mask analysis, HLSL emission, hash and constant-version APIs; its `nv2a_vsh_run` symbol has an incompatible output type. Compiling both unchanged produces a symbol/API collision and leaves two divergent state stores.

Concrete port:

- Keep the upstream interpreter's program, constant, start/load cursors and context-write enable as canonical state (`nv2a_vsh_interp.c:37`). Keep its public fixture APIs.
- Port our decoded-instruction cache and input-mask/constant-write analysis, then HLSL emission (`nv2a_vsh_cpu.c:219`, `:280`, `:601`). Expose compatible hash, used-input, emitter, and constant-version accessors from the upstream module. Update PGRAPH includes/call sites to these APIs.
- Invalidate analysis/hash/decoded cache on every instruction setter, upload load/start change that affects traversal, and direct test instruction setter. Advance constant version on every component/vector setter, viewport mirror and permitted CPU program constant write. Our old CPU constant-write path did not advance the version (`:472`); do not copy that omission into the unified module.
- Keep upstream immediate `imm_attr` as the current vertex inputs rather than retaining `s_current` as another state source. Our missing-attribute fallback currently consults `nv2a_vsh_current` (`nv2a_pb_exec.c:1915`, `:1999`).
- GPU eligibility remains conservative: executable program mode, supported topology, no constant-writing program, no diagnostic CPU batch dump, and no blacklisted program (`:1882`). `RECOMP_VSH_GPU=0` must continue to select CPU execution before D3D drawing. `RECOMP_PB_D3D11` absent must retain upstream software execution.
- Preserve the HLSL output contract used by `d3d8_extvs.c` and the fixed-function pixel shaders: POSITION, COLOR0/1, TEXCOORD0–3, fog/view/point-size slots (`nv2a_vsh_cpu.c:601`; `d3d8_extvs.c:38`). Preserve screen-space-to-clip reconstruction, tex0 linear scaling, and program point-size output (`nv2a_vsh_cpu.c:722`).

The interpreters agree on the uploaded instruction field layout, ARL floor bias and paired ILU register rule, but they are not behaviorally identical. Upstream gates constant writes on context-write enable (`nv2a_vsh_interp.c:379`); ours writes unconditionally (`nv2a_vsh_cpu.c:472`). Out-of-range relative constants map to c0 upstream (`:205`) and clamp to c0/c191 ours (`:325`). Default unwritten position.w is 0 upstream (`:339`) and 1 ours (`:382`); upstream retains d1/fog/tex[4], while ours CPU output is reduced. LOG-zero and LIT exponent endpoints also differ (upstream `:286`, `:297`; ours `:436`, `:443`). Preserve upstream CPU semantics deliberately and validate the title's actual uploaded programs; do not claim interchangeability from matching bitfields alone.

Our PGRAPH program draw returns -1 on compilation/emission failure and blacklists the program (`nv2a_pgraph_d3d11.c:1551`), but the executor currently ignores the return (`nv2a_pb_exec.c:2244`); CPU fallback begins on a subsequent batch. Point geometry-shader failure similarly returns success while skipping (`d3d8_extvs.c:275`). These are existing limitations, not evidence that the failed batch renders. At the adapted draw boundary, explicitly define handled/refused status and validate first-use failure behavior before reporting robust fallback.

## Texture and renderer details that must survive

- CONTROL0 enable and palette entry count: ours `nv2a_pb_exec.c:2818`, `:2841`; upstream's `tex_update_valid` (`:352`) currently does not include the enable bit. Decode all four stages directly instead of our temporary stage-0 state shuffle (`:1715`).
- Pitch-derived row width for linear textures and matching UV scaling (`:307`, `:1976`); using IMAGE_RECT width alone changes padded atlas sampling.
- P8 unswizzle/palette expansion, mutable palette/texel signature and re-upload path (`:1464`, `:1547`, `:1640`). The converted-texture cache miss must re-expand, not bind an absent converted texture (`:1619`).
- Mutable nonconverted texture refresh (`nv2a_pgraph_d3d11.c:954`), LRU metadata (`:1033`), and eviction unbinding every stage before Release (`:996`). These are lifetime fixes, not optional diagnostics.
- Heap-backed ready conversion capacity (`:1379`) and external-VS dynamic ring buffers (`d3d8_device.c:1086`). Keep external GS cleanup (`:1167`) and buffer rebinding (`:1170`).
- Depth/stencil masks, alpha/blend/constant blend color, color-mask no-write handling, surface clip and texture address/filter state (`nv2a_pgraph_d3d11.c:1282`). Do not infer state solely from the upstream software raster fields while dropping the D3D method shadow.
- Preserve optional diagnostic knobs and dumps without changing their default enablement. Surface/render-target sampling remains a limited existing path; the opt-in skip/probe machinery is not new render-target emulation.

## Walker, MMIO and fence package

Our `nv2a_pb_scan.c` exports resumable `nv2a_pb_run`, stall, subroutine queries/leave, register-aware read, and recent ring-transfer lookup (`:187`, `:245`, `:261`, `:271`, `:508`). It bounds the contiguous window (`:337`), handles CALL/RETURN (`:361`), rejects bad headers more strictly (`:390`), remembers split payloads at PUT (`:410`) and only stalls at packet boundaries (`:418`). Upstream instead recursively scans CALL targets and has no resumable packet/stall interface (upstream `:166`, `:225`).

These exports are consumed by our memory-layout ack loop, release queue and backlog logic. Keep them together with:

- Hook-aware NV2A register read/write and ack ownership (`xbox_memory_layout.c:199`, `:1024`; public hook interface `.h:194`).
- Release reference validation, queue and configurable prefetch margin (`.c:619`, `:659`, `:702`).
- Fence register mirroring and lap-aware fence records (`:745`, `:762`, `:773`), plus late software-stall/idle follow logic (`:825`).
- Actual walker stop tracked in `s_run_pos`, and GET updated to consumed work rather than PUT (`:1048`, `:1194`, `:1210`). Continuing the same stream after software-method acknowledgement even when PUT has not moved is necessary (`:1052`).

Upstream's ack loop scans submit ranges and writes GET=PUT (upstream `xbox_memory_layout.c:925`, `:1010`), including a learned ring-wrap interval. That wrap handling does not subsume the resumable software-method and semaphore ordering above. Do not run both scanners over the same submission; it would execute methods twice. Port our run/ack/fence region onto the upstream file while retaining upstream allocation, mappings and non-GPU fixes outside it.

Two existing design limitations deserve explicit records: CALL state is one level, and the release-progress counter `g_pb_words` increments at header/control-word reads (`nv2a_pb_scan.c:343`), not for every payload word (`:398`). Preserve the measured behavior through the rebase; changing the prefetch model belongs in a separately measured follow-up. The XDK device offsets used for ring and fence records (for example `dev+24/+28/+40/+64`) also need parameterization or an adapter before claiming broad toolkit portability.

## Provenance and generic-host readiness

Our `nv2a_vsh_cpu.c:18` states that encoding/semantics follow xemu's `vsh.c` and the Cxbx-Reloaded field table. This establishes a review obligation, not proof of copied code or proof of clearance. Before a public upstream contribution, inspect its patch authorship and implementation history and document whether these were hardware references or transferred implementation/structure. Preserve original licence headers.

Upstream `CONTRIBUTING.md:200`–`:215` explicitly allows reading other implementations to understand behavior, rejects carrying GPL code/structure across, requests origin disclosure, and applies the same rule to AI-assisted work. `:195` retains LGPL status for the designated xemu-derived APU/register files. Do not infer the new interpreter/emitter's status from those separate exceptions or from upstream having similar source-reference comments.

Keep guarded title assets (`GAME_HAS_FONT_ATLAS`, `nv2a_pgraph_d3d11.c:26`) guarded. Remove/replace the Def Jam-only documentation dependency in the generic emitter file (`d3d8_extvs.c:13`) when submitting it upstream. The unconditional game-owned frame-end symbol above is the concrete template link hazard. Generic regression fixtures should build/link without Def Jam hooks or font globals.

## Serial migration gates for the main agent

1. Preserve the dirty toolkit and all untracked GPU modules/patches before changing its checkout. Use the exact upstream commit above for the first controlled comparison.
2. Establish one canonical program state and upstream CPU interpreter first. Add fixture checks for uploads with incrementing/nonincrementing packets, load/start changes, viewport constants, relative addressing and context writes. Check used-input/hash/version invalidation through direct setters as well as pushbuffer setters.
3. Integrate walker plus MMIO/ack/release package together. Require CALL/RETURN, PUT-split packet resume, ring-wrap, stalled method acknowledgement without PUT movement, semaphore ordering and GET/backlog progress checks before treating it as consolidated.
4. Add D3D forward/state adapter and ready drawing. Check primitive modes 1 and 5–10, 32-bit guest indices, large indexed draws, texture enable/palette length, 4-stage binding, linear padded atlases and texture eviction while bound on another stage.
5. Add compiled-program rendering and `d3d8_extvs`. Compare GPU enabled and `RECOMP_VSH_GPU=0` through intro/menu, select, fight, Story gym and point sprites. Check first compilation failure/blacklist handling, constant updates and point GS failure explicitly.
6. Verify standalone/generic toolkit build linkage and current Def Jam Debug/Release linkage. Keep gamma neutral/active behavior, logical render dimensions, clip/scissor and FLIP pacing consistent.
7. Run the established complete regression pipeline on the newly built executable, then the documented 20-boot/soak path and Vlad's manual visual gates. Existing 9/9 structural screenshots do not prove color, lighting, combiner or shader parity. Preserve saves with the main agent's approved save safeguards.

## Ten-line summary

1. Use upstream executor, software rasterizer and `nv2a_vsh_interp` as canonical state/CPU execution.
2. Port our D3D11 adapter and HLSL emitter onto that state; do not compile both interpreters unchanged.
3. Preserve 32-bit guest indices, ARRAY_ELEMENT32 and the 32,768-index capacity.
4. Keep upstream hardware primitive numbering; our D3D converters already use it.
5. Keep upstream's richer immediate attributes, software colors/fog and four textures.
6. Add texture enable/palette length and preserve mutable uploads, UV pitch scaling and safe eviction.
7. Retain walker, software stalls, register hooks, release queue and actual-GET advancement together.
8. Forward methods before texture/subchannel early returns and present once at FLIP_STALL.
9. Audit source provenance and the game-owned frame-end symbol before proposing generic upstream code.
10. Gate the migration on CPU/GPU comparisons, fence progress, full regression, soak and manual visual checks.
