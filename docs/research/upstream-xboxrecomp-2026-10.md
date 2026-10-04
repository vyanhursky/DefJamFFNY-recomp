# Upstream xboxrecomp since our pin, and what to do about our patches (2026-10-02)

Question (Vlad, 2026-10-02): before deciding whether to move our toolkit changes from patch files to a fork,
has `sp00nznet/xboxrecomp` moved since we pinned it, and would pull requests there be viable and worth it?

Method: `git fetch` of the upstream repository into the submodule (no working-tree change), `git log` and
`git diff` between our pin and `origin/main`, and the upstream pull-request list (`gh pr list`). Nothing in
our checkout was changed.

## Short answer

Upstream is very active and merges outside contributions quickly. It has independently fixed a good part of
what our patches fix, often in the same files and sometimes under the same names, so our patch stack is
drifting away from a moving target. **Recommendation: rebase onto upstream `main` before M6, as its own
piece of work, carrying our changes as commits on a fork branch rather than as patch files; then offer the
generic fixes upstream in small pull requests.** Details and the effort involved are below.

## How upstream has moved

- Our pin is `6f55eaa` (2026-09-15). Upstream `main` is `1409a7d` (2026-09-30): **255 commits**, 157 files
  changed, about 20,900 lines added and 900 removed.
- **159 pull requests**, about 140 merged. Most are from outside contributors (eight regular names besides
  the maintainer), merged within days, typically in batches (09-16, 09-20, 09-27, 09-30). Seven are open
  today, six of them from one contributor working on another title.
- The repository is MIT-licensed, 112 stars, 29 forks.
- `CONTRIBUTING.md` has a provenance section (PR #132, 09-27): contributions must be your own work or from
  an MIT-compatible source, no code ported from GPL projects (Cxbx-Reloaded, the GPL parts of xemu), and the
  same check applies to AI-assisted code. Our patches are written here, not ported, but a few comments cite
  xemu as the reference for hardware behaviour; that is reading, which the policy allows, and should be
  said in a PR.

The files our patches touch were changed upstream as well, heavily:

| File | Lines changed upstream since our pin |
|---|---|
| `src/kernel/nv2a_pb_exec.c` | 1,847 |
| `tools/recomp/translator.py` | 1,615 |
| `tools/recomp/lifter.py` | 1,006 |
| `src/kernel/xbox_memory_layout.c` | 911 |
| `src/usb/ohci.c` | 623 |
| `src/usb/usb_gamepad.c` | 471 |
| `src/kernel/kernel_bridge.c` | 438 |
| `src/kernel/kernel_hal.c` | 274 |
| `templates/runtime/recomp_types.h` | 208 |
| `src/apu/apu_core.c` | 148 |

Of the 52 toolkit files our 108 patches touch, 29 changed upstream.

## Where upstream already has our fix (or one like it)

Matched by title and topic. "Same" means the same bug; whether the code is equivalent needs checking at
rebase time.

| Our patch | Upstream PR | Note |
|---|---|---|
| 0107 seed tests read this machine's analysis | #79 (09-20) | same bug, same fix |
| 0108 FRNDINT ignores the rounding mode | #126 (09-27) | same bug |
| 0009 rep-compare flags, loop counts | #124, #110 (09-27) | REPE CMPS/SCAS CF and zero count; LOOP/LOOPE/LOOPNE |
| 0005 in/out, rotate through carry | #104 (09-27) | rcl/rcr |
| 0033 rol/ror at the operand width | #69 (09-20) | same |
| 0065 DPC queue lock | #155 (09-30) | same, plus KDPC.Inserted |
| 0007 OHCI physical addresses, frame clock | #142, #96 | |
| 0024, 0044 USB hub, gamepad, port | #85, #91, #96, #154 | upstream has up to four pads (`RECOMP_USB_PADS`) |
| 0016 APU physical addresses | #147 | |
| 0002, 0012, 0048, 0070 APU reset, doorbell, DSP memory, interrupts | #82, #84, #139, #141, #147 | |
| 0038, 0045-0047, 0063 pad scripts | #144 `RECOMP_PAD_SCRIPT` | upstream's own design; syntax may differ from ours |
| 0014, 0035, 0036 palettised textures | #145 | P8 through the stage palette |
| 0019, 0079, 0082 vertex programs, combiners, four stages | #152 (09-30) | "NV2A executor: vertex programs, register combiners, four texture stages, clipping" |
| 0023 blend and alpha test | #108 | |
| 0097 DRAW_ARRAYS | #81 | point sprites probably not |
| 0018, 0067 guest clocks | #119 | KeQuerySystemTime resolution |

So at least 15 topics, touching roughly 30 of our patches, are covered upstream in some form. Upstream also
has fixes we do not, in code this title runs: the NV2A primitive numbers one too low (#102, "a triangle strip
is drawn as a fan"), pushbuffer GET running ahead and a ring wrap dropping a segment (#97), x87 precision
control (#149), SSE compare predicates (#151), lahf and unordered compares (#150), guest-buffer bounds checks
(#89), switch tables whose displacement is not slot 0 (#140), plus large disassembler and recovery work
(#111-#116, #163, #164). Some of these may explain things we worked around rather than fixed.

## What is ours alone

Most of the rendering work after 0079 (stencil, surface clip, packed normals, constant-colour blending,
point sprites, long batches, texture filters, the fence hold), the kernel races found this week (0103 timer
re-arm, 0104 directory search), the lifter entry hooks (0095), and the diagnostics (batch dump, pixel probe,
palette dump). These are the natural pull requests.

## Options

1. **Stay on the pin with patch files** (today). Costs nothing now. Each week upstream moves, a later move
   costs more, and fixes upstream makes for code we also run (the strip/fan numbering, ring wrap) never
   reach us.
2. **Fork at our pin**, our patches as commits. Easier day to day than patch files, but the same drift.
3. **Rebase onto upstream `main`**, on a fork branch: apply our changes on top of upstream, drop what
   upstream covers, resolve the rest, then point the submodule at the fork. Future upstream updates become
   an ordinary `git rebase`, and pull requests come from the same fork. **Recommended.**

## What option 3 would take

- A fork (`vyanhursky/xboxrecomp`, can be private at first), a branch from upstream `main`.
- Our 108 patches re-applied in order with `git apply --3way`, each either applied, dropped as covered
  upstream (recorded which PR covers it), or ported. The three big files (`nv2a_pb_exec.c`, `translator.py`,
  `lifter.py`) will conflict heavily: upstream's executor grew vertex programs and combiners of its own, so
  ours and theirs have to be reconciled function by function, not patch by patch.
- A full re-lift (the lifter changes upstream alter generated code everywhere), then `scripts/regress.py`
  as the gate, plus Vlad's play-test of the Story route, since the goldens cover only three screens.
- Estimate: one to two long sessions, most of it in the executor. Risk: regressions in rendering that the
  goldens do not see; the harness routes and captures are the defence.
- Then, separately: pull requests for the generic fixes, a few at a time, each described with the title
  and symptom, in upstream's style. The upstream maintainer integrates batches and sometimes rewrites; that
  is fine.

## Hygiene for a public fork

The patches contain no game code or assets. Comments name this title, addresses in its XBE and its
behaviour, which upstream itself does for Halo. The provenance policy asks contributors to state AI
assistance concerns and sources; our PR descriptions should say the code was written with an AI assistant
and that xemu was read as a hardware reference, not copied.
