# M4a — the APT 2D matrix-concatenation pipeline: functions, addresses, and an exhaustive x86-vs-lift check

Read-only pass. No code was edited, nothing was built or run. Disassembly of the original bytes was
done offline with capstone against the user's own dump (`DEFJAM_DATA=C:\Users\Vlad\code\defjam`,
`extracted/default.xbe`), mapped VA→file-offset with the same section-table logic
`scripts/string-va.py` uses. Everything below is marked **CONFIRMED** (read directly, lifted C
compared instruction-by-instruction against capstone output of the real bytes) or **INFERRED** (a
conclusion drawn from confirmed facts, not itself directly observed).

**Bottom line up front:** I found the real 2D matrix-concatenation pipeline — in fact *two* parallel
implementations of it, selected by a runtime flag — and checked every float instruction in both,
plus the 2x3→4x4 packer, against the original x86 byte-for-byte, including x87 stack order and the
esp-relative addressing across interleaved `pop` instructions. **All of it is bit-exact correct.** I
did not find the lifter bug the symptom implies. This is a real, checked negative result, not an
absence of effort — see §6 for exactly what was verified and §7 for what is still open and how to
close it fastest (mostly runtime, not static).

---

## 1. The pipeline, top to bottom (CONFIRMED call graph)

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00165A00` (0x00165A00, 1404 bytes) is the per-object "draw yourself, then recurse into your own
children" function: it makes several indirect calls through the object's own vtable-ish slots
(`0x3B1E58`, `0x3B1E24`, `0x3B1E50`, `0x3B1E54`, …) — this is where the actual geometry submission
and the `sub_00119910` vertex-shader-constant upload for *this object's own quad* presumably happens
— and it calls `sub_0017A4A0` twice (once per some internal condition) to descend into children.
**I could not resolve those vtable slots** (no static vtable data in the lift, same wall
`docs/research/m3-movie-display.md` hit for the sibling `0x3B8084`/`0x3B8088` objects) — so I could
not find the exact instruction that takes the finished 24-byte matrix and writes it into the two
`SetVertexShaderConstant` register slots (c0/c1) the brief describes. **This is the one link in the
chain I did not close**; see §7.

---

## 2. The building blocks, address by address

| Address | Name | What it does | Verified? |
|---|---|---|---|
| `0x00179890` | matrix concat (4x4-embedded) | `out = Local * Parent`, only the 6 floats that matter for a 2D affine transform in a 4x4 D3D matrix (`M[0][0..1]`, `M[1][0..1]`, `M[3][0..1]`) | **CONFIRMED correct**, full instruction diff, §3 |
| `0x00179950` | build 4x4 from packed 2x3 | takes `{a,b,c,d,tx,ty}` at input offsets `0,4,8,0xC,0x10,0x14`, writes a 4x4 (`row0=(a,b,0,0)`, `row1=(c,d,0,0)`, `row2=(0,0,1,0)`, `row3=(tx,ty,0,1)`) | **CONFIRMED correct**, pure MOVs, §4 |
| `0x0017D4D0` | matrix concat (packed 2x3, no 4x4 expansion) | same math as `0x00179890` but operating directly on two packed 2x3 structs, writing a packed 2x3 result | **CONFIRMED correct**, full instruction diff, §5 |
| `0x0017A360` | compose+render child, path A | pushes/pops the GLOBAL matrix stack at `0x3B1E78`, calls `0x00179890` and an inline cxform concat, then `0x00165A00` | traced, not fully diffed (control flow only; the float-affecting parts are the calls into the two verified functions above plus an inline cxform block not covered by the brief's ask) |
| `0x0017A2F0` | compose+render child, path B | uses a per-renderer-object matrix field (`renderer+0x20`) and a per-renderer-object save stack (`renderer+0x238`, depth at `renderer+0x3BC`, via `0x0017D440`/`0x0017D480`), calls `0x0017D4D0` and `0x0017D370` (cxform), then `0x00165A00` | traced, not fully diffed |
| `0x0017A4A0` | walk a movie clip's children | reads `MEM8(0x3B1DC4)` bit 2 once, picks path A or B, builds a z-order list via `0x00179F10`, calls the chosen path per child through an indirect call | traced |
| `0x00119910` | `SetVertexShaderConstant` wrapper | `ecx+0x60` = register index, branches on count (1 → `0x0021B690`, 4 → `0x0021B740` MMX block-copy, else → `0x0021B8D0` generic) | traced in the earlier session that scoped this task; not re-verified here |

### The global 2D matrix stack (this is the "stage/view matrix" the brief asked about)

**CONFIRMED**, `sub_00148A40` (`recomp_0010.c:17323` area) is the one-time initializer:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

immediately followed by a tail-call into `sub_00148970`, which resets the (then-current, i.e.
bottom/root) slot to the identity 2x3-in-4x4 (`a=d=1`, everything else `0`, `row2col2=1`,
`row3col3=1`, plus its 0x20-byte cxform tail set to `mult=(1,1,1,1)`, `add=(0,0,0,0)`). **So the root
of the global stack — `MEM32(MEM32(0x3B1E74))` — is the stage/view matrix for path A, and it is
identity at init.** Whether something writes a non-identity value there later (e.g. a device-pixel or
letterbox scale, which would explain the *pure-scale, no-rotation* title-screen matrices the brief
measured: `c0=(0.000244,0,0,3)`) is a runtime question, not something this static pass can answer —
**INFERRED as a promising lead, not confirmed.** `sub_00148950`/`sub_00148960`/`sub_001407D0` are the
raw push/get-top/pop primitives on this same stack; **all three have zero direct callers** (indirect
only — the same "vtable wall" `m3-movie-display.md` already documented for this module), so I could
not trace who else pushes/pops it beside `sub_0017A360`.

### The per-renderer-object matrix (path B's equivalent)

**CONFIRMED**, no address for a "stage matrix" as such — path B keeps the running world matrix as a
field on the renderer/context object passed around as `ecx`/`esi` (`renderer+0x20`, 24 bytes,
same packed layout), and a *separate*, per-renderer save stack at `renderer+0x238` (indexed by a
depth counter at `renderer+0x3BC`, 0x18 bytes per slot via `sub_0017D440`/`sub_0017D480`). I did not
identify a global address for the renderer object itself in this pass (it is threaded through as a
parameter everywhere I looked, never loaded from a literal address) — **could not determine.**

---

## 3. `sub_00179890` — full instruction-by-instruction verification (CONFIRMED correct)

Original bytes, `0x00179890`–`0x0017994C` (188 bytes), disassembled directly:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

That is exactly `out = B*A` in row-vector convention (`out[i][j] = Σ_k B[i][k]*A[k][j]`), i.e.
`World = Local * Parent` given the call site passes `A=parent`, `B=local`, `dst=out` — the
mathematically correct 2D affine concatenation, including the `row3` (translation) terms picking up
`A.tx`/`A.ty` (the parent's own translation) additively, exactly as it must.

**Every one of the above lines matches the lifted C at `src/recomp/gen/recomp_0011.c:11052`–`11100`
verbatim**, including the two interleaved `pop edi`/`pop esi` in the middle of the second output
block — the lift re-derives `[esp+0x44]` *after* the `POP32(esp, edi)` it already executed, which is
the only thing that makes that instruction reference `B.a` instead of some stale offset; I checked
this specific spot first because it is exactly the kind of esp-bookkeeping mistake the brief was
worried about, and it is done correctly. **No lifter defect found in this function.**

---

## 4. `sub_00179950` — verification (CONFIRMED correct)

Pure integer `mov`s, no float ops, no branches — every one of the 21 `mov`s in the original
(`0x00179950`–`0x001799A4`) matches the lifted C 1:1, including the two reused-constant writes
(`0x3F800000` = `1.0f` written to both `+0x28` and `+0x3C`, the `row2col2` and `row3col3` identity
diagonal entries). Confirms the packed-2x3 field layout used throughout this report:
`a=+0,b=+4,c=+8,d=+0xC,tx=+0x10,ty=+0x14`.

---

## 5. `sub_0017D4D0` — full instruction-by-instruction verification (CONFIRMED correct)

This is the "path B" twin of §3 — same math, but it never expands to a 4x4; it reads and writes the
packed 24-byte `{a,b,c,d,tx,ty}` struct directly. Original bytes `0x0017D4D0`–`0x0017D5B6` (230
bytes) were disassembled and diffed the same way. The interesting part here is that the two `mov
eax,[esp+...]` reloads (`A` pointer → `B` pointer at `0x0017D4FB`, `B` pointer → `out` pointer at
`0x0017D535`) land in the *middle* of runs of `mov [esp+n],reg` stores, and the lift reproduces the
exact position of both reloads relative to the surrounding stores — i.e. it does not read `B.c`
through a stale `eax` that still points at `A`, and it does not write through `eax` before it has
been reloaded to the output pointer. I traced all six output floats (`out.a` through `out.ty`)
against the disassembly the same way as §3; all six match, and the formula is the same
`out = B*A` (`World = Local * Parent`) convention. **No lifter defect found in this function either.**

---

## 6. What was checked, method

For both concat functions (§3, §5) and the packer (§4): every `fld`/`fmul`/`fadd`/`faddp`/`fstp`
(or, for §4, every `mov`) in the real x86 was matched one-to-one against a lifted-C line, in order,
confirming (a) the source operand offset, (b) which x87 stack slot it targets, (c) that any
esp-changing instruction between two float ops (the `pop edi`/`pop esi` in §3) is reflected in the
*same relative position* in the lifted C so that later `[esp+n]` reads resolve to the address the
original instruction actually used, and (d) the final arithmetic reduces to the textbook 2D affine
matrix-concatenation formula. All three functions passed on every point. This rules out — with high
confidence — the specific bug classes named in the task brief (x87 stack-order errors, `fsubr`/
`fdivr` operand-order swaps, wrong operand size, SSE mishandling, flag-dependent branch errors) *for
these three functions specifically*. It does not rule out a bug anywhere else in the pipeline.

---

## 7. What is still open, and where to look next (INFERRED / not determined)

1. **Which path is actually live.** `MEM8(0x3B1DC4)` bit 2 picks path A vs path B once per
   `sub_0017A4A0` call (i.e. potentially per movie-clip, not globally fixed) — I could not determine
   its value or what sets it, and did not find a second static writer to point to. If the title
   screen and the post-title screens take *different* paths, that alone would not explain a shared
   *wrong* matrix (both paths verified correct), but it would matter for where to put a runtime
   watchpoint. **`RECOMP_WATCH_WRITE` on `0x3B1DC4`, or `RECOMP_PEEK`, is the fastest way to settle
   this.**
2. **The actual c0/c1 upload site.** `sub_00165A00`'s own draw calls are behind unresolved vtable
   slots (`0x3B1E58`, `0x3B1E24`, `0x3B1E50`, `0x3B1E54`, plus two `[reg+4]` icalls) — I could not
   find, statically, the instruction that reads the finished 24-byte matrix and writes the two
   4-float vertex-shader constants. Given both concat functions are proven correct, **the most likely
   remaining lifter-bug locations are (a) whatever reads `renderer+0x20` or the global stack top and
   packs it into the two vec4s for `sub_00119910`, which this pass did not locate, or (b) code this
   pass never reached at all** (e.g. the routine that turns `_x/_y/_xscale/_yscale/_rotation` into
   the child's own local `a,b,c,d,tx,ty` in the first place — genuinely unexamined here; that is
   exactly the kind of `sin`/`cos` x87 code most prone to a stack-order bug, and nothing in this
   report touches it).
3. **The stage/view matrix's actual runtime value.** §2 shows where it lives (`0x3B1E74`) and that it
   is *initialized* to identity, but whether it is later overwritten with something that explains the
   title screen's pure-scale numbers (and whether *that* write is correct on non-title screens) is a
   runtime question. `RECOMP_PEEK` on `0x3B1E74` (or the 0x60 bytes at its current top,
   `MEM32(0x3B1E78)`) across a title→menu transition would directly show whether the parent matrix
   itself is already wrong before any child ever concatenates against it — which, given §3/§5 are
   proven correct, is now the leading hypothesis for "why every sprite on non-title screens shares
   the same wrong rotation/skew/translation": **a single bad parent matrix, correctly propagated by
   provably-correct concat code, would look exactly like the reported symptom.**
4. **`sub_0017A2F0`'s glyph-refresh gate** (`type & 0x3F == 0xF`) and **`sub_0017D310`/`sub_0017D340`**
   (a third, apparently unrelated 32-byte per-renderer save/restore around the whole compose+render
   step) were traced but not deeply analyzed — they did not contain float arithmetic worth diffing
   against x86 for this brief's purposes, but a bug in *what* they save/restore (e.g. restoring the
   wrong slot, an off-by-one in the depth counter at `renderer+0x3BC`) could produce exactly the
   "everything shares one stale matrix" symptom without touching the concat math at all. Not ruled
   out.

---

## 8. Confirmed vs inferred, summary

**Confirmed (read directly, cross-checked against capstone disassembly of the original bytes):**
- `sub_00179890`, `sub_00179950`, `sub_0017D4D0`: bit-exact correct, no lifter defect.
- The packed-2x3 field layout (`a,b,c,d,tx,ty` at `+0,4,8,0xC,0x10,0x14`) and its 4x4 embedding
  (`row0=(a,b,0,0)`, `row1=(c,d,0,0)`, `row2=(0,0,1,0)`, `row3=(tx,ty,0,1)`).
- The global matrix-stack addresses (`0x3B1E74`/`0x3B1E78`/`0x3B1E7C`) and their identity init.
- The two-path dispatch in `sub_0017A4A0`, gated on `MEM8(0x3B1DC4)` bit 2.
- The call graph `sub_0017A4A0 → {sub_0017A360 | sub_0017A2F0} → {sub_00179890 | sub_0017D4D0} →
  sub_00165A00 → sub_0017A4A0` (recursive descent through a movie clip's children).

**Inferred (plausible, not observed at runtime):**
- The stage/view matrix at `0x3B1E74` is the most likely place a wrong parent matrix originates,
  given the concat code itself is proven correct and would faithfully propagate any bad parent to
  every child.
- Both compose paths are reachable only indirectly (icall through `ebp`/vtable), consistent with —
  but not proof of — either path being "the" live one on any given screen.

**Not determined (needs runtime data, listed with the fastest tool for each in §7):**
1. `MEM8(0x3B1DC4)`'s value and who sets it.
2. The literal instruction that packs a finished matrix into the two `SetVertexShaderConstant`
   register writes for an ordinary sprite (vtable wall inside `sub_00165A00`).
3. Whether the stage/view matrix (or the per-renderer `renderer+0x20` equivalent) actually holds a
   non-identity, non-trivial value on non-title screens, and if so what wrote it.
4. Where/how a display object's own `_x/_y/_xscale/_yscale/_rotation` become its packed local 2x3 —
   not located in this pass at all.
