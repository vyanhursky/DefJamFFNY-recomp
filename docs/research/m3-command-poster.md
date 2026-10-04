# M3 — the front-end command poster at guest `0x002EB73C`

Read-only static pass over `src/recomp/gen/` (grep + manual read). No code built or run. This is a
continuation of `docs/research/m3-command-pointer.md` and `PROGRESS.md`'s 2026-09-21 19:35/20:05 entries,
which already established: exactly one literal-address write to `0x2EB73C` exists in the whole image
(`sub_0019AE50`, sets it to zero), a runtime write-watchpoint on `0x2EB73C` recorded zero hits over a full
run, and the `0x2EB59C + 0x1A0 = 0x2EB73C` theory was checked against all 15 `MEM32(reg + 0x1A0) =` writes
in the image with only one (unrelated, float-heavy) hit. I did not re-derive any of that; I took it as given
and pushed one level further on two specific sub-questions the brief asked me to test.

**Bottom line up front: I still could not find the code that posts a command.** I found one new, fairly
solid structural fact (a real "screen manager" singleton at `0x2EB738`, confirmed by construction-site
evidence, with `0x2EB738 + 4 == 0x2EB73C`), but I could not find any write through it either. Read the
"What I could not determine" section before trusting the base/offset material — it is the most important
part of this report.

---

## Q1 — testing the `0x2EB59C + 0x1A0` theory: what does `sub_0019ADA0` actually do with its argument?

**READ.** The call site, `sub_0019B0C0` (`recomp_0011.c:72518-72523`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This is a `thiscall` (`ecx = esi`) with **two** stack args pushed in this order: `eax` (`= MEM32(0x3B8088)`,
the second front-end manager pointer) pushed first, then the literal `0x2EB59C` pushed second (so it sits
nearer the return address — first C-order parameter). The function's own doc comment says "CC: cdecl, 1
params", which the earlier report flagged as unreconciled with two pushed args. I resolved that by tracing
the stack layout through the function body (`recomp_0011.c:71880-71891`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Working through the offsets (entry `esp0`: `[esp0+4]`=arg1=`0x2EB59C`, `[esp0+8]`=arg2=manager ptr; then
`esp -= 0xC` for locals, then three pushes = `esp0 - 0x18`; `esp+0x1C` from there lands back on
`esp0+4`), **`esi = 0x2EB59C` itself** (the raw constant, not something read *through* it). So the "1
params" doc comment is simply wrong/stale from the lifter's heuristic; the function genuinely takes two
stack args plus `ecx`.

`esi` (`= 0x2EB59C`) is then only ever **passed on, unchanged, as a plain integer argument** to three other
functions — never added to, never dereferenced by literal offset:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

I read `sub_0019C0B0`, `sub_0019C1F0`, `sub_0019D260`, `sub_0019D320` in full (`recomp_0011.c:74471`,
`74686`, `77423`, `77583`). All four are tagged `Category: game_input` in their doc comments and operate on
`ecx + 0x534` / `ecx + 0x53C` / `ecx + 0x548` — a completely different object shape (keycode/scancode
translation: `sub_0019C0B0` maps a 16-bit code through a big `cmp`/`je` ladder against constants like
`0x70`, `0xE`, `0x3ED`, `0x48F` into a small enum 0-7). None of the four ever forms an address by adding a
constant to `esi`/the `0x2EB59C` value; it is used purely as an opaque id/cookie argument.

**Conclusion for Q1 (the specific working theory in the brief): I now have stronger evidence against it than
before.** Not only did the exhaustive `+0x1A0` sweep (already done by a previous agent, per `PROGRESS.md`)
turn up nothing in the front-end file; the *only* place `0x2EB59C` is used at all routes into the keyboard/
input keycode-mapping subsystem, not the screen manager. `0x2EB59C` and `0x2EB73C` being `0x1A0` apart
looks like it is genuinely numeric coincidence — the two addresses belong to unrelated structures. **I could
not connect `0x2EB59C` to `0x2EB73C` by any addressing mode.**

---

## Q1 (continued) — a new, better-grounded candidate base: `0x2EB738`

The brief also asked me to look at `sub_0019AE50`, the clear routine, for what addressing form it uses to
reach `0x2EB73C`. **READ:**

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**This is the key negative result the brief asked me to check for: the clear routine uses a plain literal
address, not a base+offset form.** It gives no structure-layout hint at all — it just reads as `0x2EB73C`
being a flat global dword, not obviously a field of a larger struct reached relative to some other base.
That said, while grepping around `0x2EB73C` I found something the previous reports did not mention, so I
chased it:

**`0x2EB738` (4 bytes *before* `0x2EB73C`) is used, 5 times, only in `recomp_0015.c`, only as a literal
constant pushed as an argument — never dereferenced as `MEM32(0x2EB738)` anywhere in the whole image**
(checked with `grep -rn "MEM32(0x2EB738)"` across all of `src/recomp/gen/` — zero hits). All 5 uses are of
this shape:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

There are 5 near-identical wrapper functions (`sub_002106D0`, `sub_00210710`, `sub_00210720`,
`sub_00210730`, `sub_00210740`), each pushing the literal `0x2EB738` and a distinct fixed `this` address
(`0x3B8160`, `0x3B8290`, `0x3B8328`, `0x3B80A0`, `0x3B8200`), calling one of 5 different constructor
functions (`sub_0019B510`, `sub_0019B6C0`, `sub_0019B650`, `sub_0019B740`, `sub_0019B7B0` —
`recomp_0011.c:73078/73263/73215/73315/73363`). Each constructor takes `eax` = the pushed `0x2EB738` and a
literal type id (`1`, `6`, `4`, `8`, `7` respectively), and forwards both straight into the shared base
constructor:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**This is a real finding, not inference for the first part:** `0x2EB738` is a fixed address passed *by
value*, at construction time, into 5 distinct "screen"/state objects, and stored at each one's `+8` field
as their "owning manager" pointer. That is exactly the shape of a manager/registry singleton address, and
`0x2EB738 + 4 == 0x2EB73C` lines up with the very next field in that singleton being the pending-command
pointer the idle loop reads. This is a materially better-grounded candidate base than `0x2EB59C` was,
because unlike `0x2EB59C` it is demonstrably tied to the same "screen" object family that also owns the
front-end idle loop's dispatch (the 24 handler functions in Q2 below operate on exactly these `0x3B81xx`/
`0x3B82xx`/`0x3B80xx`/`0x3B83xx` object addresses).

**Where this theory falls short — I could not close the loop.** I found the only 3 places in the entire
image that read a `+8` field back out of one of these 5 objects (i.e. read the manager pointer out again):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

All three read sites do the exact same thing: load the manager pointer out of the screen object, and
immediately hand it off as one of several arguments to `sub_0019FBE0`, a function whose `this` is a
*different* fixed global (`0x2EB890`, not `0x2EB738`). I read `sub_0019FBE0` in full
(`recomp_0011.c:82915-82965`): it stores its incoming arguments into fields of *its own* `this` (`0x2EB890`)
at offsets `0x14`/`0x18`/`0x1C`/`0x74`/`0x88`/`0x8C`, then makes a virtual call through `this->+4`'s vtable.
It never writes `manager_ptr + 4` (i.e. never touches `0x2EB73C` even indirectly) in the code I can see
statically — the value it received is stored as opaque data on the `0x2EB890` object, and what (if anything)
happens to it after that goes through an unresolved indirect call, which is where static reading runs out.

I checked the analogous `+8` fields for the other 3 screen objects (`0x3B8328+8=0x3B8330`,
`0x3B80A0+8=0x3B80A8`, `0x3B8200+8=0x3B8208`) and found **zero** reads of any of them anywhere in the image
— those three objects apparently never read their own manager pointer back out at all (at least not through
this field, by literal address).

**Conclusion for Q1: not found, with more precision than before.** `0x2EB738` is now a fairly solid,
independently-confirmed candidate for the base of whatever structure `0x2EB73C` belongs to (much better
grounded than `0x2EB59C`, which turned out to be an unrelated coincidence). But every one of the 3 places
that reads the manager pointer back out of an object routes it into `sub_0019FBE0` against an unrelated
global (`0x2EB890`), not into a `+4` write on the manager itself, and I could not trace further than that
without resolving indirect calls I have no static way to resolve. **I did not find any write, direct or
computed, to `0x2EB73C` or to `(any traced register holding 0x2EB738) + 4`, anywhere in the lifted image.**

---

## Q2 — the jump table at `0x19ACB8` (command id → handler)

**READ in full**, `sub_0019AB60`, `recomp_0011.c:71432-71581`. The dispatch is `eax = MEM32(ptr+8) - 1`
(0-based), bounds-checked against `0x1E` (30), then a 31-entry table with 25 distinct targets (24 real
handlers + 1 shared "no-op / out of range" target, `loc_0019AC7A`, which several table slots also point at
directly). Every handler call is a single unconditional `RECOMP_ABI_CALL` immediately followed by
`goto loc_0019AC7A` (the shared cleanup/re-arm tail), so this table is exhaustively enumerable statically —
no indirection here.

| id (1-based) | jump target | handler | source line |
|---|---|---|---|
| 1 | `loc_0019ABC2` | `sub_001A0640` | 71458 |
| 2 | `loc_0019ABCC` | `sub_0019FC70` | 71463 |
| 3 | `loc_0019ABD6` | `sub_0019FD00` | 71468 |
| 4 | `loc_0019ABE0` | `sub_001A08E0` | 71473 |
| 5 | `loc_0019ABEA` | `sub_001A0EF0` | 71478 |
| 6 | `loc_0019ABF4` | `sub_001A1420` | 71483 |
| 7 | `loc_0019ABFE` | `sub_001A1BA0` | 71488 |
| 8 | `loc_0019AC05` | `sub_001A20A0` | 71493 |
| 9 | `loc_0019AC0C` | `sub_0019FFC0` | 71498 |
| 10 | `loc_0019AC13` | `sub_0019EBC0` | 71503 |
| 11 | `loc_0019AC1A` | `sub_0019EC60` | 71508 |
| 12 | `loc_0019AC21` | `sub_0019EDA0` | 71513 |
| 13 | `loc_0019AC28` | `sub_0019EE60` | 71518 |
| 14 | `loc_0019AC2F` | `sub_0019F4F0` | 71523 |
| 15 | `loc_0019AC36` | `sub_0019F5C0` | 71528 |
| 16 | `loc_0019AC3D` | `sub_0019F650` | 71533 |
| 17 | `loc_0019AC44` | `sub_0019F710` | 71538 |
| 18 | `loc_0019AC4B` | `sub_0019F890` | 71543 |
| 19 | `loc_0019AC52` | `sub_0019F110` | 71548 |
| 20 | `loc_0019AC59` | `sub_0019F000` | 71553 |
| 21 | `loc_0019AC60` | `sub_0019EEF0` | 71558 |
| 22 | `loc_0019AC67` | `sub_0019F790` | 71563 |
| 23 | `loc_0019AC6E` | `sub_0019F960` | 71568 |
| 24 | `loc_0019AC75` | `sub_0019F7F0` | 71573 |
| 25-31 | (unmapped) | fall through directly to `loc_0019AC7A` | — |

**"Which id loads a screen": I could not determine this.** The brief suggested grepping handler bodies for
`%s/%s.big` / `%s.swf` path construction or a call into the loader. String literals are not represented as
inline C strings anywhere in `src/recomp/gen/` (they live in the XBE's data section, not reproduced in the
lift), so `grep -n "\.big\|\.swf\|sprintf"` across the whole front-end file returns **zero hits** — that
search technique does not work against this lift. I also checked whether any of the 24 handlers call
`sub_00069F10` (the confirmed once-only SWF/font kickoff) directly — none do (its only call site is
`recomp_0003.c:34033`, inside a different function, `sub_0006BF90`, per `PROGRESS.md`'s own 14:52 entry).

I partially read `sub_001A0640` (id 1) and `sub_0019FD00` (id 3) looking for this. Neither obviously "loads
a screen": `sub_001A0640` is a small state machine over fields of screen-object `0x3B8160` that polls input
(calls `sub_0019C0B0`, the same keycode-mapper from Q1) and, on one path, builds and dispatches a
notification struct in the shared `0x2EBE90` scratch buffer to a *different* listener object
(`MEM32(0x3B8164)`'s vtable slot `+4`) — this writes `MEM32(0x2EBE94)=1` and `MEM32(0x2EBE98..0x2EBE9C)`,
**not** `0x2EB73C`. `sub_0019FD00` is its own small nested state machine (status field at `0x2EB80C`) that
at one point (`recomp_0011.c:83170-83196`) rewrites the *same* shared scratch buffer's id field to `3` (its
own id) before a virtual dispatch — consistent with the "handlers can requeue the next command by rewriting
the buffer's id field in place, without ever touching the `0x2EB73C` pointer" pattern the earlier report
already noted for other handlers (`sub_0019EBC0` etc. writing `MEM32(0x2EBE94)=9` and similar). I did not
have budget to read the other 22 handlers to completion; any of them could be the screen-load path and I
have no evidence pointing at one over another. **Flagging as not found, not guessing.**

---

## Q3 — who calls `sub_0019AE50` (the clear routine), and under what conditions?

**READ (a negative result).** `grep -rn "RECOMP_ABI_CALL(0x0019AE50u" src/recomp/gen/*.c` returns **zero**
matches anywhere in the codebase. The only reference to `sub_0019AE50` outside its own definition is its
entry in the function-pointer dispatch table:

```
src/recomp/gen/recomp_dispatch.c:11702:    { 0x0019AE50u, (recomp_func_t)sub_0019AE50 },
```

**Conclusion for Q3: `sub_0019AE50` has no direct call site anywhere in the lifted image. It is reachable
only through an indirect call (a vtable slot or function-pointer table) whose owning object I could not
identify statically** — the same limitation `CLAUDE.md` and `PROGRESS.md` describe for other indirect-only
functions in this codebase (direct calls compile to plain C calls and show up as `RECOMP_ABI_CALL`; indirect
calls go through `recomp_lookup()`/`RECOMP_ICALL_SAFE` and are invisible to a literal-address grep for the
callee). I cannot say whether it runs once, repeatedly, or never; that would need a runtime instrument
(`RECOMP_WATCH_EXEC=0x0019AE50`), which is out of scope for this read-only pass.

For context (already established by a previous **runtime** measurement, not re-derived here):
`PROGRESS.md`'s 2026-09-21 19:35 entry reports a write-watchpoint on `0x2EBE94` (part of the scratch buffer
`sub_0019AE50` also zero-fills, but a different address than `0x2EB73C` itself) caught exactly two writes,
both zero, from `sub_0019B0C0 + 0x6F3` and `sub_00210820 + 0x23E` — i.e. initialization-time clears, not a
command post. I did not independently verify that entry in this pass (it is a runtime result I cannot
reproduce without running the game), but it is consistent with `sub_0019AE50` itself also being reachable
only from initialization-adjacent code.

---

## Q4 — `sub_0019E8E0`, both branches, read in full

**READ**, `recomp_0011.c:80464-80500` (62 bytes, 20 instructions, `thiscall`, 1 stack param):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Branch A (command already pending, `0x2EB73C != 0`): does nothing but return `3`.** No side effects at
all — it is a pure "busy, try later" gate.

**Branch B (no command pending, `0x2EB73C == 0` — this is our stalled state): does NOT write `0x2EB73C`.**
It makes two virtual calls (slots `+0xC` then `+0x10`) on a *different* object (`this->+0x14`, not the front
-end manager at `0x3B8084`/`0x3B8088`), stores its own incoming byte argument into a field of the object at
`0x3B8078` (the same address the Q1 input-mapping functions use — recall `sub_0019ADA0`/`sub_0019C0B0`/
`sub_0019C1F0` all take `ecx = MEM32(0x3B8078)`, so `0x3B8078` looks like a font/UI-string-table object
shared across several subsystems), and returns `1`.

I could not resolve `this->+0x14`'s concrete type (it depends on which object calls `sub_0019E8E0` as
`this`, which I did not trace — no direct callers of `sub_0019E8E0` turned up in a quick check, meaning it
too is indirect-only, same caveat as Q3). **This reads exactly like a "request a command slot; if one is
free, kick off whatever `this->+0x14` is and remember a flag; if busy, decline" gate — very plausibly *part
of* the posting machinery — but the actual write to `0x2EB73C`, if it happens at all, would have to occur
inside one of the two unresolved virtual calls in branch B, which I cannot follow statically.** This is the
closest lead in this report to the real poster, and also the most explicitly unresolved one.

---

## What I read vs. what I inferred

**Read directly (highest confidence):**
- `sub_0019ADA0`'s full body and stack-offset arithmetic, resolving what its `0x2EB59C` argument actually is
  and where it goes (Q1).
- `sub_0019AE50`'s full body (literal-address write, no base+offset form) and its zero call sites (Q1/Q3).
- The `0x2EB738` construction chain: 5 wrapper functions in `recomp_0015.c` → 5 constructors → the shared
  base constructor `sub_0019B480`, and the exact field (`this+8`) it is stored at (Q1).
- All 3 sites in the whole image that read a screen-object's manager-pointer field back out, and what they
  do with it (`sub_0019FBE0`, itself read in full) (Q1).
- The complete 31-entry/25-target jump table and its 24 resolvable handler addresses (Q2).
- The zero call sites for `sub_0019AE50` (Q3).
- `sub_0019E8E0`'s full body, both branches (Q4).

**Inferred, flagged as such inline:**
- That `0x2EB738` is "the screen manager singleton" — strongly supported by the construction evidence, but
  I never observed a read of `MEM32(0x2EB738)` itself (only of objects' cached copies of it), so I cannot
  rule out that `0x2EB738` is itself a pointer field somewhere else rather than an embedded struct.
- That branch B of `sub_0019E8E0` is "part of the posting machinery" — plausible from its shape (gates on
  the exact same pointer, touches a plausibly-related object), not confirmed by tracing the two virtual
  calls it makes.

**What I could not determine (explicit list):**
1. **The actual poster of `0x2EB73C`.** Not found by literal address (confirmed again), not found via the
   `0x2EB59C+0x1A0` theory (actively ruled out — that address belongs to the keycode-mapping subsystem, not
   the screen manager), and not found via the better-grounded `0x2EB738+4` theory either (the only 3 places
   that read the manager pointer back out immediately hand it to an unrelated object and I lose the trail at
   an unresolved indirect call).
2. **Which command id (1-24) loads a screen.** The suggested string-grep technique does not work against
   this lift (no inline string literals); I could not identify the loader handler by any other static means
   in the time available. Only ids 1 and 3 were read past their headers, and neither obviously does it.
3. **The concrete type of `this->+0x14` in `sub_0019E8E0`, and what its two virtual-call targets (`+0xC`,
   `+0x10`) do.** This is where I would look first next — if branch B is the intended poster, the write has
   to be inside one of these two calls, and resolving them needs either a vtable-layout source I don't have
   in the lifted C, or a runtime instrument on the call targets.
4. **Who calls `sub_0019AE50` and `sub_0019E8E0`.** Both are indirect-only (no `RECOMP_ABI_CALL` site in the
   whole image); I could not identify their callers statically.
5. Whether `0x2EB738` is read anywhere via a register-relative form I didn't think to search for (I checked
   literal `MEM32(0x2EB738)` and the 3 known `+8`-field reads of the 5 screen objects; I did not do an
   exhaustive re-sweep of all `+0x1A0`-style offsets for this new base, given the `sub_0019ADA0` dead end
   already used most of the budget for that class of search).

## Suggested next step

Given the tool caveats already on record in `src/hooks/watchpoint.c` (a miss proves nothing for an
edge-triggered instrument if the code ran before the watcher armed, and one data watchpoint here already
missed a proven host-side write), the cleanest next static step is probably: find every indirect call site
in the image whose target register was loaded from `this + 0x14` where `this` could plausibly be a screen
object (to find `sub_0019E8E0`'s caller and pin down its concrete type), rather than another sweep for
`0x2EB73C` by address. A runtime `RECOMP_WATCH_EXEC` on `sub_0019E8E0` and on the vtable slots it calls
would settle Q4's open branch far faster than more static reading, given the front-end thread is confirmed
live and reachable (per `PROGRESS.md`'s 19:26 entry).
