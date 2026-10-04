# M3 main-loop exit — sub_00011CD0, the flag at `esp+0x13`, and sub_00011060's second entry

Read-only static-analysis pass over `src/recomp/gen/recomp_0000.c` and the toolkit's own static
cross-reference database (`tools/xboxrecomp/tools/disasm/output/xrefs.json`). No code was edited, built,
or run in this session. Every claim below is either a direct quote of lifted C (marked READ) or an explicit
inference from that quote (marked INFER). Where I could not resolve something, I say so plainly rather than
guess.

`sub_00011CD0` original range: `0x00011CD0`–`0x00011E0D` (317 bytes, 98 instructions), lifted at
`src/recomp/gen/recomp_0000.c:4826-5029`. This is the *entire* function body — I read it start to finish.

---

## Q1 — Control flow of `sub_00011CD0`: the loop, and every way out

### Loop shape (READ)

The loop head is `loc_00011D40`; the sole back-edge is at the very bottom of the function:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0000.c:5007-5013`)

There is also a *secondary*, inner loop nested inside the body, purely local to one outer iteration:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0000.c:4951-4956`) — this re-enters `loc_00011D55` (inside the same outer iteration) as long as
`sub_000D75E0` keeps returning non-zero; it does not leave the outer loop, so it is not a separate exit.

### Every `goto` in the function (READ, exhaustive)

I grepped the full function body (lines 4826-5029) for every `goto` and every `RECOMP_ABI_CALL`/`return`.
There are exactly **nine** `goto`s and **one** `return`:

| line | from → to | condition |
|---|---|---|
| 4909 | `loc_00011D51` → `loc_00011DA7` | gate `sub_000D75E0` returned 0 (skip body) |
| 4932 | `loc_00011D7B` → `loc_00011DA2` | tick `sub_00077040` returned 0 |
| 4956 | `loc_00011D9C` → `loc_00011D55` | inner-loop continue (gate still non-zero) |
| 4959 | `loc_00011DA0` → `loc_00011DA7` | inner-loop fell out (gate went to 0) |
| 4987 | `loc_00011DC8` → `loc_00011DD9` | FPS-counter compare, unrelated to exit |
| 4998 | `loc_00011DD9` → `loc_00011DFF` | **the loop exit** — `MEM8(esp+0x13) != 0` |
| 5013 | `loc_00011DF6` → `loc_00011D40` | the back-edge (continue looping) |

`loc_00011DFF` is reached from exactly one place (line 4998) and falls straight through to the function's
single `return`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0000.c:5015-5022`)

**This confirms: `sub_00011CD0` has exactly one loop and exactly one way out of it** — the conditional
branch at `loc_00011DD9`/line 4998, gated on `MEM8(esp+0x13) != 0`. There is no other conditional branch to
`loc_00011DFF`, no second `return`, no `RECOMP_ICALL_SAFE` anywhere in this function (all ten calls in it
are direct `RECOMP_ABI_CALL`s to statically-known targets — read the table below), no exception/longjmp
construct, and the final "call" is a genuine x86 tail-jump modeled as `sub_000D7580(); return;` — i.e. it
*is* the return, not a call that might not return on its own.

### Resolving the contradiction you flagged

You already found the write:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0000.c:4927-4962`), guarded on `sub_00077040`'s return in `eax` being zero (line 4925: `RECOMP_ABI_CALL(0x00077040u, sub_00077040)` immediately precedes the test).

I read the whole function and found **no other write of 1** to that byte, and (see Q3 below) no aliasing
that could let some other callee write it. The only other write to it at all is the initializer, well
before the loop:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0000.c:4892`), executed once, before `loc_00011D40` is ever reached.

**Conclusion (INFER, but tightly constrained by what I read): you did not miss an exit — there isn't one.**
Given your runtime measurement that every call to `sub_00077040` returned non-zero, `loc_00011DA2` is
provably never reached, `MEM8(esp+0x13)` is provably still `0` at every check of `loc_00011DD9`, and
therefore `loc_00011DFF` — the function's only `return` — is never taken. As far as this function's own
logic goes, **the loop does not exit**. It should be spinning forever, which is consistent with your
separate measurement that `sub_00077740` (the unconditional tail-of-loop call) runs over 1000 times while
the gated tick runs only 9-41 times: the loop keeps iterating long after the gated block stops doing
anything, because the gate (`sub_000D75E0`, see Q2) is what's actually suppressing progress, not a loop
exit. If the title stops drawing while `sub_00011CD0` is still technically looping, the cause is upstream
of this function — most likely whatever makes `sub_000D75E0` start returning 0 on almost every iteration —
not a hidden exit from this loop. I could not investigate `sub_000D75E0`'s internals; that was out of scope
for this pass (see "Not determined" below).

---

## Q2 — The `sub_000D75E0` gate: confirmed, and exactly what it skips

Confirmed (READ). The gate is checked once per outer iteration, immediately after `sub_001ECE20`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0000.c:4895-4909`) — `TEST_Z` on `eax`'s low byte means: if `sub_000D75E0` returns 0, jump straight
to `loc_00011DA7`, skipping everything from `loc_00011D55` through `loc_00011DA0`. Confirmed exactly as you
described.

**Skipped when the gate returns 0** (`loc_00011D55`–`loc_00011DA0`, `recomp_0000.c:4911-4959`):
- `sub_0002C530` (loc_00011D55)
- `sub_000DD930` (loc_00011D5F)
- `sub_00077040` — **the tick** (loc_00011D71)
- conditionally, if the tick returned non-zero: `sub_000BD860`, `sub_000BDF40`, `sub_0001A240` (loc_00011D7F-D95)
- `sub_000D75E0` again (loc_00011D95) — this second call is the inner-loop's own re-check, so the gate
  effectively controls its own repetition too.

**Runs every outer iteration regardless of the gate** (i.e. reached whether or not `loc_00011D55` ran):
- `sub_001ECE20` (loc_00011D40) — before the gate is even checked
- `sub_000D75E0` itself (loc_00011D47) — the gate check is of course unconditional
- `sub_00012CF0` (loc_00011DA7)
- `sub_001E9550` (loc_00011DB3)
- `sub_0001A880` (loc_00011DBC), plus the inline FPS/frame-counter bookkeeping that follows it
  (`recomp_0000.c:4980-4992`, the `eax - edi` vs `MEM32(0x2FB030)` compare-and-maybe-store)
- the exit test itself (`loc_00011DD9`)
- if not exiting: `sub_000D02A0`, `sub_000D0C20`, and **`sub_00077740`** (loc_00011DE1-DED)

This matches your measurement exactly: `sub_00077740` (always-run) executes 1000+ times; `sub_00077040`
(gated tick) executes only 9/17/41 times — the gate is returning 0 on the vast majority of iterations.

---

## Q3 — Is `MEM8(esp+0x13)` ever aliased?

**No aliasing found within `sub_00011CD0` (READ, exhaustive check).** I extracted every line in the function
containing `esp +` or `esp -`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Every single occurrence is either a stack-pointer adjustment (`esp = esp ± N`) or a `MEM8`/`MEM32`/`MEMF`
dereference used for an immediate load or store. **None** of them is the LEA-style pattern that would
indicate address-of (i.e. a bare `reg = esp + N` computing a pointer value, then that register pushed or
moved into `ecx`/`edx` as a call argument). No call site in this function pushes a computed `esp`-relative
address as an argument — every `PUSH32(esp, ...)` in the function pushes either a constant, a return
address, or a value already loaded into a register from somewhere else (`esi`, `eax`, `edi`), never a
freshly-computed stack address.

**Caveat (explicitly not determined):** this only rules out aliasing done *by this function itself* — i.e.
`sub_00011CD0` never hands any callee a pointer into its own frame at offset `+0x13`. It does **not** rule
out a callee (`sub_000D7560`, `sub_000D75E0`, `sub_00077040`, `sub_0002C530`, `sub_000DD930`, `sub_000BD860`,
`sub_000BDF40`, `sub_0001A240`, `sub_00012CF0`, `sub_001E9550`, `sub_0001A880`, `sub_000D02A0`,
`sub_000D0C20`, `sub_00077740`) independently computing that exact same stack address on its own (without
being told it) and writing there anyway — that would require walking up the stack past its own return
address with no argument telling it to, which would be unusual and is not something I found evidence for,
but I did not read those 14 callees' bodies, so I cannot fully rule it out. Given the ordinary calling
convention in use everywhere else in this function (arguments passed via `ecx`/stack push, never raw frame
pointers), I consider this unlikely, but it is an inference, not something I read and confirmed.

---

## Q4 — `sub_00011060`'s early, indirect entry

**Grep results (READ):** across all of `src/recomp/gen/` (18 numbered files + `recomp_dispatch.c` +
`recomp_funcs.h`), the literal values `0x00011060` and `0x11060` appear in exactly three places:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

No occurrence of the value as a plain register/stack assignment (e.g. `eax = 0x00011060u` or
`PUSH32(esp, 0x00011060u)` as an argument) exists anywhere in the lifted C. Same result for `0x00011102`
(the interior entry point) — its only occurrences are the internal label inside `sub_00011060`'s own body,
the standalone `sub_00011102` function definition, and its own dispatch-table row; no external call site.

**Cross-checked against the toolkit's own static disassembly xref database**
(`tools/xboxrecomp/tools/disasm/output/xrefs.json`, 151,278 entries, generated by the toolkit's disassembler
over the full `.text` section — a broader analysis than grepping the lifted C, since it also tracks
data-reference xrefs):

```
{'from': '0x00011060', 'to': '0x002FB020', 'type': 'data_read'}   -- sub_00011060 reads a global; unrelated
{'from': '0x0001150A', 'to': '0x00011060', 'type': 'call'}        -- the one known direct call, from main
```

That's the complete list of xrefs touching `0x00011060` in either direction. No `data_write` xref exists
anywhere in the binary that stores `0x00011060` into memory as a value, and no second `call`/`cond_jump`
xref targets it. The same query for `0x00011102` likewise shows only internal xrefs (a conditional jump
from within `sub_00011060`'s own body, and a call *out* of `sub_00011102` to `0x000D0C90`) — nothing
external.

I also checked the host harness (`src/main.c`) and `src/hooks/` for any reference to `sub_00011060` or that
address outside the guest lifted code — there is none. `src/main.c`'s only guest entry point is
`xbe_entry_point` at the XBE's actual entry `0x001F6357` (`src/main.c:26,84,626`); it does not call
`sub_00011060` itself.

### Not determined

**I could not find how `sub_00011060`'s first, early entry is reached.** What I can say for certain:

- It is not a second literal call site anywhere in the ~63,000+ lines of lifted C (grep-exhaustive).
- It is not stored as a literal value anywhere in the lifted C or in the toolkit's independent static
  xref database — which means either the disassembler also failed to resolve it (consistent with it being
  a genuinely indirect/computed reference, e.g. a function pointer loaded from the XBE's initialized
  `.data`/`.rdata` segment — a CRT `atexit`/`_initterm`-style table or a C++ vtable slot populated at
  compile time as raw bytes, which would never appear as an *instruction* in the lifted C and so is
  invisible to any source-level grep), or it is reached from somewhere this pass didn't check.
- The two functions being adjacent in the dispatch table (`sub_00011060` and its interior entry
  `sub_00011102`, both ending at `0x000114F8`) and both being present as ICALL dispatch targets is
  consistent with — but does not prove — an indirect-call/callback mechanism (`RECOMP_ICALL_SAFE`) being
  the path for the early entry, since that dispatch table exists specifically to resolve indirect calls by
  runtime address value.
- I did not find any host-side (`src/main.c`, `src/hooks/`) call to this address either, so the early entry
  is not something the recompilation harness injects outside of the guest's own code.

Confirming this would require either reading the XBE's raw initialized-data segment for a stored pointer
equal to `0x00011060` (not available from `src/recomp/gen/` alone, and off-limits here since raw game bytes
aren't tracked in this repo), or runtime tracing (e.g. `scripts/icall-window.py`) to catch the actual ICALL
site resolving to it — both out of scope for this read-only pass. I am flagging this explicitly rather than
guessing at a specific mechanism.

---

## Summary of what was READ vs INFERRED vs NOT DETERMINED

**READ (direct quotes, verifiable in `src/recomp/gen/recomp_0000.c:4826-5029`):**
- The loop head (`loc_00011D40`), its single back-edge (`loc_00011DF6`→`loc_00011D40`), and its single exit
  branch (`loc_00011DD9`→`loc_00011DFF`, gated on `MEM8(esp+0x13) != 0`).
- The only write of `1` to that byte is at `loc_00011DA2`, gated on `sub_00077040` returning 0; the only
  other write is the one-time initializer to `0` at `loc_00011D3A`, before the loop.
- The `sub_000D75E0` gate at `loc_00011D47`/`loc_00011D51`, and the exact set of calls inside vs. outside
  the gated region.
- No LEA-style address-of of `esp+0x13` anywhere in this function.
- The grep/xref results for `0x00011060`/`0x00011102` across all lifted C and the toolkit's static xref DB.

**INFERRED:**
- Since every tick call returned non-zero (your runtime measurement), the loop's only exit is provably
  unreached, so the loop does not terminate on its own terms; the "stops drawing" symptom is more likely
  caused by the `sub_000D75E0` gate suppressing the tick/render-prep block than by this function returning.
- The early entry to `sub_00011060` is plausibly a function pointer stored in the XBE's static data segment
  (CRT init-table or vtable-style), reached via `RECOMP_ICALL_SAFE`, given the dispatch-table entries — but
  this is not confirmed.

**NOT DETERMINED:**
- Whether any of `sub_00011CD0`'s ~14 callees independently pokes `esp+0x13` in this frame without being
  passed a pointer to it (would require reading those callees' bodies).
- What actually makes `sub_000D75E0` start returning 0 on most iterations (not read in this pass; that
  function's body was out of scope for this question set).
- The concrete mechanism/call site that produces `sub_00011060`'s early, indirect entry. No second static
  reference to `0x00011060` exists anywhere I could grep (lifted C, dispatch table, xref DB, host harness).
  Resolving this needs either the XBE's raw data segment or runtime ICALL tracing, both out of scope here.
