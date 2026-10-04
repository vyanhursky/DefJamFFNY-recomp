# M4e: vertex programs on the GPU (design)

Status: design, 2026-09-29. Owner decision: Vlad asked for this as its own milestone after the audio, crowd
and R3 fixes.

## Why

A fight presents 38-42 frames a second in the debug build (§6 2026-09-29 00:00), against the title's 60.
The GPU executor spends most of its time running the title's NV2A vertex programs on the CPU
(`src/kernel/nv2a_vsh_cpu.c`, one vertex at a time), even after 0073 (decode once, reuse vertices). A GPU
runs the same programs for thousands of vertices in parallel at no cost to the executor thread.

It also fixes two things the CPU path gets wrong by construction:

- **Perspective.** The CPU path hands the translator screen-space vertices with `rhw = 1`, so texture
  coordinates and colours interpolate affinely across a triangle. Large polygons near the camera (the floor,
  the fighters up close) swim. A vertex shader that outputs a real clip-space `w` gets perspective-correct
  interpolation for free.
- **Clipping.** Near-plane clipping is done on the CPU in screen space (`clip_batch_w`, 0057). On the GPU the
  hardware clips in clip space, exactly.

## Exit criteria

1. A fight presents 60 frames a second in the debug build (`[D3D] 2.0s: ... present` in a round), with the
   round clock at its design rate (1.2 ticks a step) and no new crash over three fights.
2. The M2, M3 and M4a goldens match; a fight capture differs from the CPU path's only where perspective
   correction is expected (checked by eye and by `scripts/frame-signature.py` bounds).
3. The CPU path stays available (`RECOMP_VSH_GPU=0`) and remains what the batch dump and `RECOMP_VSH_TRACE`
   use, so every diagnostic keeps working.

## What exists

- `src/kernel/nv2a_vsh_cpu.c`: the decoder that is right for this title (fields per xemu's `vsh.c`, dwords
  1..3), plus the semantics of every MAC and ILU op used, the constant/`a0` addressing, output register
  mapping (R12 = oPos, O[3] = oD0, O[9] = oT0), and the defaults xemu gives unwritten outputs.
- `src/d3d/d3d8_vsh.c`: an HLSL generator, compiler (`D3DCompile`) and cache keyed by a microcode hash,
  192 constants in a cbuffer at `b1`, bound by `d3d8_vsh_prepare_draw` inside the D3D8 layer's draw, so the
  pixel pipeline (texture stages, blend, depth, the combiner emulation) is applied as for any other draw.
  Its decoder uses a different field layout and does not read this title's microcode (noted in
  `nv2a_vsh_cpu.c`), and its input layouts are keyed by fixed-function vertex format.
- `src/kernel/nv2a_pb_exec.c` `draw_primitive`: fetches every attribute of every index (`fetch_attr`), runs
  the CPU program, normalises texture coordinates for linear textures, and calls
  `pgraph_d3d11_draw_ready` with screen-space vertices.

## Design

1. **One decoder.** Move the verified field decode out of `nv2a_vsh_cpu.c` into a shared header, and make
   `d3d8_vsh.c` parse with it. Keep `d3d8_vsh.c`'s HLSL emitter, rewritten per instruction from the CPU
   interpreter's semantics (it is the reference: every op there has been checked against this title).
2. **HLSL per program.** Inputs `float4 v[16]` (only those the program reads, from
   `nv2a_vsh_inputs_used`); constants `c[192]` with `a0` relative addressing; temporaries `R0..R11`; `R12` is
   oPos. Direct3D's epilogue (`RCC R1.x, R12.w; MAD oPos.xyz, R12, R1.x, c[59]`) leaves oPos in screen
   pixels with `w` = 1/w_clip. The shader reconstructs clip space from that: `w = 1 / oPos.w`,
   `ndc.xy = (oPos.xy / ScreenSize) * (2, -2) + (-1, 1)`, `z = oPos.z / zmax`,
   `SV_POSITION = float4(ndc * w, z * w, w)`. Clip-space `w <= 0` then clips in hardware.
3. **Outputs** match the D3D8 layer's `VS_OUT` (diffuse from oD0 saturated, tex0 from oT0 scaled by the
   linear-texture factor passed as a constant, tex1..3 from oT1..3 once multitexture is modelled, fog).
4. **Vertex data.** The executor builds one float4-per-attribute stream for the unique indices of a batch
   (the reuse map from 0073 already gives them) and a 16-bit index list, and hands both to a new translator
   entry, `pgraph_d3d11_draw_program(program words, start, constants, verts, n_verts, indices, n_idx, prim)`.
   The translator binds an input layout of the used `ATTRn` semantics, uploads the constants, and draws
   through the D3D8 layer (a new "external vertex shader" handle, so `d3d8_shaders_prepare_draw` binds the
   compiled shader instead of the fixed-function one and still sets up the pixel side).
5. **Constants** are uploaded when changed: the executor keeps a dirty range as `SET_TRANSFORM_CONSTANT`
   arrives (a fight rewrites a few dozen registers per draw: the bone matrices).
6. **Fallback** to the CPU path for any program the generator rejects (logged once per hash), for
   batch-dump frames, and with `RECOMP_VSH_GPU=0`.

## Steps, each a commit with a measurement

1. Shared decoder + HLSL emitter for the ops this title uses; a unit test that runs a captured program on
   the CPU interpreter and compares with the generated HLSL's semantics on a few vectors (the CPU path is the
   oracle).
2. Translator entry and D3D8 layer hook; draw the front end (2D, few programs) through it; goldens.
3. The fight: bones, lighting programs; perspective check; fps.
4. Clean-up: retire `clip_batch_w` for GPU-drawn batches; keep it for the CPU path.

## Risks

- Programs that write constants (`o_mask` with `orb` clear): rare; CPU path for those.
- Point sprites / oPts: not seen in this title yet.
- The D3D8 layer's pixel pipeline assumes its own VS output layout; any mismatch shows as black or garbage,
  so step 2 starts with the simplest screens.
