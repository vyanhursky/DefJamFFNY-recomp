# Graphics enhancements: texture levels, anisotropic filtering, MSAA, downscaling, post effects

2026-10-28. Branch `feat/graphics-enhancements`, toolkit branch `defjam/graphics-enhancements`. Prototype of
the four recommendations from the recomp graphics survey (what Unleashed, Marathon, Zelda 64 and the other
recomps offer, and what fits this game):

1. quick, faithful wins: the game's own texture levels with anisotropic filtering, the venue post effects as
   options, and area-averaged downscaling;
2. MSAA (transparency anti-aliasing deferred, see below);
3. a 1x / 2x / 4x restoration pass over the effects;
4. a feasibility spike for frame rates above 60 (no code yet).

Every new setting defaults to the picture as it was, so regressions and golden frames are unchanged until a
player turns one on. Which ones should default on is a decision for after the Windows and Deck runs
(`D-new` in the PR).

## Settings

All in `[display]` ([reference](../settings-reference.md)), in the launcher's and overlay's Display page.

| Key | Values | Live? | Where |
|---|---|---|---|
| `texture_mips` | `false` / `true` | yes | toolkit `nv2a_pgraph_d3d11.c`, `nv2a_pb_exec.c` |
| `anisotropy` | `off`, `2x`, `4x`, `8x`, `16x` | yes | toolkit `d3d8_states.c` (D3D11), `d3d8_vk.c` (Vulkan) |
| `msaa` | `off`, `2x`, `4x`, `8x` | restart | toolkit `d3d8_present.c` + `d3d8_device.c` (D3D11), `d3d8_vk.c` |
| `filter` | `smooth`, `sharp`, new `smooth (high quality)` | yes | toolkit `d3d8_present.c` (D3D11), `d3d8_vk.c` |
| `color_tint` | 0-100 | yes | `src/patches/picture.c` |
| `scratches` | `true` / `false` | yes | `src/patches/picture.c`, `src/recomp_manual.c` |

Environment overrides for one run: `RECOMP_TEXTURE_MIPS`, `RECOMP_ANISOTROPY`, `RECOMP_MSAA`,
`RECOMP_PRESENT_FILTER` (choice names, e.g. `16x`, `smooth (high quality)`), `RECOMP_COLOR_TINT`,
`RECOMP_SCRATCHES`. `scripts/scenario_suite.py --settings` accepts `texture_mips`, `anisotropy` (1-16),
`msaa` (1-8), `color_tint` and `scratches`.

## Texture levels (mipmaps) and anisotropic filtering

Found while mapping the renderer: the translator uploaded **level 0 only** of every texture the title binds
(`pgraph_d3d11_set_texture_ready` created one-level textures, and `set_texture_filter` dropped the mip half of
SET_TEXTURE_FILTER: "Mip levels are not uploaded"). A swizzled or DXT texture carries its smaller levels right
after level 0 (SET_TEXTURE_FORMAT bits 16-19, the same chain `tex_face_stride` walks), and the console
filtered between them. So distant floors and crowds were sampled from full-size texels and shimmered, and an
anisotropic filter on its own would have had nothing to work with.

- `texture_mips`: `bind_texture_ready` passes the format's level count for swizzled and DXT 2D textures to the
  new `pgraph_d3d11_set_texture_ready_mips`; the cache key includes the level count, so turning it on or off
  takes effect as textures are next bound. Each level is uploaded through the D3D8 layer's own per-level
  `LockRect`/`UnlockRect`, which already unswizzles (D3D11) or converts (Vulkan) per level, as HD packs use it.
  The mip filter follows the title: MIN 3/4 nearest level, 5/6 blend two, anything else level 0 only.
  Linear textures (movies, render surfaces), palettised textures (converted to ARGB here) and cube maps keep
  level 0.
- `anisotropy`: a sampler for a texture the title minifies **linearly** gets anisotropic filtering of up to N
  samples; a nearest-filtered one (cut-outs keyed on a colour) is left exactly as asked. D3D11 builds its
  samplers per draw, so the change is immediate; Vulkan keys its sampler cache by the level too, and enables
  the `samplerAnisotropy` device feature when the GPU has it (every desktop GPU, MoltenVK, the Deck).
- Side fix: D3D11 samplers used `MaxLOD = FLT_MAX` even for MIPFILTER NONE, so an HD pack texture the title
  draws at level 0 could still mip on Windows while Vulkan sampled level 0. Both now sample level 0 for NONE.

## Area-averaged downscaling (`filter = smooth (high quality)`)

With a render scale above the window's size (4x in a 1080p window, 3x-4x on the Deck's 800 lines), bilinear
scaling reads four texels of a footprint that covers more, so the extra resolution aliases instead of
averaging out.

- Vulkan presents with `vkCmdBlitImage`. The new mode halves the picture with exact 2x2 averages (a linear blit
  at exactly 2:1 lands between four texels) until one more halving would go below the window, then does the
  last step, under 2:1, as before. Scratch images are made per picture size and retired when it changes.
- D3D11 presents with a pixel shader. The new mode takes N x N bilinear taps across each window pixel's
  footprint, N = the scale ratio rounded up (at most 4), so every texel under the pixel is weighed.
- The capture a harness takes is the title's target, before presentation, so this mode never changes golden
  frames; it has to be judged on screen (window screenshots, `RECOMP_WINDOW_SHOT`).

## MSAA

The Xbox game renders into an anti-aliased surface (pitch 5120 for a 640-wide target: 2x horizontally,
[widescreen-renderer](widescreen-renderer.md)); the port drew one sample per pixel, so its edges are harsher
than the console's at render scale 1-2.

- D3D11: the title's default target becomes a multisampled texture (`g_game_ms`) with a matching depth buffer;
  `d3d8_present_resolve` averages it into the single-sample game texture before the gamma pass, the blit, a
  readback (`d3d8_readback_begin`) and `GetBackBuffer`. Everything after the draws reads the resolved texture,
  as before. The sample count is the largest up to the setting that both R8G8B8A8 and D24S8 support.
- Vulkan: the render pass gets a multisampled colour attachment and depth buffer, and the existing
  single-sample target becomes the subpass's **resolve** attachment, so every pass end leaves it resolved for
  the gamma pass, presentation and readbacks. Pipelines take the sample count. The count is the largest up to
  the setting in the device's colour, depth and stencil limits.
- Restart only: the target, depth buffer, render pass and every pipeline depend on it.
- Not done: **transparency anti-aliasing** (alpha-to-coverage). The title's alpha test is a discard in the
  translated pixel shader, so coverage needs shader variants that turn the discard into a sharpened alpha
  when MSAA is on. Next step if MSAA is kept.

## Venue post effects: colour tint and film scratches

`RECOMP_POSTFX_TRACE=1` logs each new variance `sub_000D8C40` draws (`[POSTFX]`). In the default One on One
fight the variance is `glow 1 vignette 1 tint 1 scratches 1 flicker 0`, modulate `244 199 181`, fill `0 0 0`:
the warm, sepia grade of every fight is this tint. Transitions interpolate other variances (fill values up to
`210 255 180` with modulate near 255).

- `color_tint` (0-100): `sub_000D9AF0_enter` (the tint draw that also carries the vignette) moves the six
  colour arguments towards no tint in proportion: modulate towards 255, fill towards 0. 0 in a fight gives the
  untinted picture (blue denim reads blue).
- `scratches`: `sub_000D8AD0` is the film-scratch overlay's draw (thiscall, no arguments); a manual wrapper
  returns without drawing when off. The default fight's variance asks for scratches but its overlay byte
  (`this+0x98`) is clear, so the draw is never reached there; scenes that do draw them still need finding
  (Story flashbacks are the candidates). The option is wired and logs `[PICTURE] film scratches removed` the
  first time it skips one.
- Glow was not made an option: `GlowEnable` only copies an intensity to `this+0x54`, and the pass that uses it
  is somewhere else. Mapping it belongs to the restoration pass below, because the translator has no
  render-to-texture and a glow that renders off screen may already be drawing into the main target.

## Restoration pass (1x / 2x / 4x)

<!-- filled from the A/B runs -->

## Frame rates above 60: feasibility

The title runs one simulation step per flip, and the executor paces flips at 60 Hz (FLIP_STALL, the flip
hold, `xbox_Nv2aSetFlipHz`). Raising the flip rate speeds the whole game up, so a higher rate has to be made
from frames the game did not draw: interpolation.

What the other recomps do: Zelda 64 Recompiled (RT64) records each frame's display lists, matches draws
between consecutive frames (with per-object tags the game's patches add) and draws in-between frames with
interpolated matrices, at the cost of one frame of latency. Mega Man X6 Recomp interpolates presentation only.

What it would take here, at the translator, without engine knowledge:

1. **Record** every draw of a frame inside `nv2a_pgraph_d3d11.c` (state, textures, combiners, vertices or the
   vertex program's constants) instead of issuing it at once.
2. **Match** draws between frame N and N+1 by (vertex program hash, texture, vertex count, order within the
   frame). Skinned fighters keep their vertex counts; the HUD is identical; particles and the crowd will not
   always match and are drawn from the newer frame.
3. **Draw** frame N+0.5 by interpolating: screen-space vertices for executor-transformed batches; the
   matrices in the constants for GPU vertex-program batches. Then frame N+1 as recorded.
4. **Guard** cuts: when too few draws match or the camera jumps, show N+1 twice.

Costs: one frame of added latency (about 17 ms) in a fighting game, a recording layer under both backends,
and per-scene tuning. Rough size: two to four weeks for a first fight-only version. Cheaper things for
high-refresh displays first: black-frame insertion at 120 Hz (motion clarity like a CRT, no new frames), and
the #67 pacing work. Recommendation: do not start interpolation before MSAA and the texture work have shipped
and the latency cost has been discussed with players.
