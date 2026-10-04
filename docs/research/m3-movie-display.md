# M3 — what has to happen for a loaded movie to become the one that is displayed

Read-only static pass over `src/recomp/gen/` (grep + manual read of the lifted C). No code was built or
run in this session. Ground truth is the MEASURED FACTS block in the task brief; nothing in it was
re-derived, only used as the frame for what the static call graph should be doing. Two earlier reports in
this project (`docs/research/m3-command-pointer.md`, `docs/research/m3-command-poster.md`) already did a
deep pass on the front-end command pointer at `0x2EB73C` and its idle loop `sub_0019AB60`, and concluded
that pointer is never written and is not the display trigger — the brief says the same
("do not spend time on it"). This report does not repeat that work; it picks up the *loading* pipeline
(`sub_001480B0`/`sub_00148210`, the `0x3B1Dxx` manager, and the `0x0018xxxx` Flash-movie module) instead.

**Bottom line up front:** the queue node that represents a loaded screen has an explicit `1 → 2 → 3 → 4`
state machine, and I found the exact code for every transition except the one that promotes `1 → wherever
state 3 gets set` — that transition happens in a completely different subsystem (an async-I/O poll on a
*separate* "movie slot" array), reached through a long, fully-quoted call chain, gated behind two file-I/O
status checks I could not evaluate statically. I also could not find the step that makes a linked/finalized
movie the *root*/`_level0` movie, or the step that walks its display list to emit geometry — those may not
exist as literal-address-reachable code at all (see the vtable-indirection wall in Q2/Q3). I *did* rule out
one whole path for Q4: `sub_001DF882` (the `.xsh`/SHPX parser) is reachable only through a resource-chunk
reader in a completely different, address-disjoint module, with no static call edge from anything in the
screen-loading pipeline I traced.

---

## Q1 — what `sub_001480B0` does after the registered loader returns, and what actually marks a node ready

**READ.** `sub_001480B0` (`recomp_0010.c:6510-6786`) is the queue consumer the brief names. `ecx` on entry
is the manager pointer (always `MEM32(0x3B1D84)` at every call site I found — see Q3). It walks 4 sub-lists
(`edi = 4`, `loc_00148D3` outer loop) and, for each node `esi`, reads a **state field at `esi+8`**:

**State 1 (queued) → 2, then the registered loader is called, synchronously, in-line:**

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Immediately after that call returns, the loop re-reads `esi+8`. If it is still `2`, nothing happens —
the node just falls through to the release/next-node path:**

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So **`sub_001480B0` itself never sets a node to state 3.** Calling the loader synchronously and getting
back to a node still at state 2 is a normal outcome, not an error — the loader (`sub_00069CC0`, see Q3) is
a *kickoff*, not a completion.

**State 3 (ready) → dependency check → 4, and the "become usable" callback:**

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00147530` (`recomp_0010.c:4332-4546`) is a dependency-readiness check: it loops over an array at
`MEM32(MEM32(esi+0x10)+0x2C)`, length `MEM32(MEM32(esi+0x10)+0x28)`, calling `sub_0014E170`/`sub_00147390`
per entry, and returns a boolean in `AL` (`SET_LO8(eax, MEM8(esp + 7));`, `recomp_0010.c:4540`, default `1`,
cleared to `0` on at least one failure path at `recomp_0010.c:4504`). **I did not fully resolve what each
array entry represents** (plausibly per-sub-resource dependency records — the `.apt`/`.const`/`.o`/`.xsh`
files, or child display objects), so I cannot say precisely what condition it is waiting for; I can say it
gates the 3→4 transition and is re-evaluated on every pass while state stays 3.

`sub_0015F950` (`recomp_0010.c:80860-81..`, thiscall, `Category: game_vtable`) runs relocation/fixup over
the node's data: a loop calling `sub_0015F8C0` per record, then a 6-case switch that patches offset tables,
including one case (`loc_0015F9C3`) that calls out through `MEM32(0x3B1E40)`. This reads as **linking the
loaded object's constant pool / symbol references**, not as "install as current/root movie" — see Q2.

**Who actually sets state to 3.** The only place in the whole image that writes `esi+8 = 3` on this queue's
node shape is `sub_00147660` (`recomp_0010.c:4554-4708`, 4 stack params):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00147660` has exactly **one caller in the entire lifted image**: `sub_00144B50`
(`recomp_0009.c:65819-65906`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`ecx = MEM32(0x3B1D84)` here is the identical global used everywhere else as the screens-queue manager, so
`sub_00147660`/`sub_00144B50` really are operating on the same node list `sub_001480B0` walks — this is the
bridge between "a file finished loading" and "the queue node is ready." `sub_00144B50` itself has **exactly
three call sites, all inside `sub_00181D20`** (see Q3) — it is not called from anywhere in the
`sub_001480B0`/`sub_00147430`/`sub_00069CC0` chain at all.

**Conclusion for Q1:** state 3 is set by a *different* subsystem than the one that requested the load
(`sub_00069CC0`/`sub_001480B0`). It is set from inside a per-frame async-I/O poller for a *separate* "movie
slot" array (Q2), gated behind two file-status checks I could not evaluate statically (Q3). If that poller
never sees the I/O it started report success, the node sits at state 2 forever and `sub_00147530`/
`sub_0015F950` never run for it.

---

## Q2 — the "current"/root movie pointer

**READ, partially.** I did not find a literal `_level0` variable or a single "root movie" pointer anywhere
in the lifted C (the brief itself notes AS variable names are not present as inline strings in this lift —
confirmed again here; `grep -rn "level0\|g_sLoadFile\|g_bLoadRequest"` across `src/recomp/gen/` returns
nothing). What I did find:

**A fixed-size movie-slot table, separate from the screens queue.** `MEM32(0x3B37A0)` is a pointer to an
array of `0x110`-byte (272-byte) records; `sub_001819C0` (`recomp_0011.c:14210-14449`) scans the first
`0x100` (256) slots for a free one (`state field == 2` at four different sub-offsets, `-544/-272/0/0x110`
relative to a stride cursor — i.e. it is checking several *candidate* slot layouts/generations, which I did
not fully resolve), then at the chosen slot:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

i.e. it copies a NUL-terminated name (the incoming argument) into the slot, appends the slot index to a
list at `MEM32(0x2EAB88)`, and zeroes `MEM32(edx+0x108)`/`MEM32(edx)` (`recomp_0011.c:14413-14414`) — these
are the same offsets the async poller in Q3 later treats as an I/O-handle field (`+0x108`) and a
state/status field (`+0`). This function is **only ever reached through `sub_00069CC0`'s icall to
`MEM32(0x345238)`** (see Q3/Q4 in `sub_00069CC0`'s own trace, and note `0x345238` is only ever populated
with `0x1819C0` by `sub_00069D30`, `recomp_0003.c:34146` region) — i.e. this is where a screen's `.apt` name
turns into a movie-slot allocation, not into a queue-node promotion.

**The manager objects at `0x3B8084`/`0x3B8088`.** I traced their construction (`sub_0019B0C0`,
`recomp_0011.c:87760-87849`, already partly documented in `m3-command-pointer.md` Q4 for a different
purpose):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Both objects are **produced by an unresolved indirect call** (factory pattern through some other object's
own vtable slot 0), so I could not identify their concrete C++ type or read their vtable contents (vtables
for heap-allocated objects are runtime data, not present in the lifted C at all). This is the same wall the
earlier command-pointer reports hit for these same two objects.

**A previously-unexamined lead:** inside `sub_0019AB60` itself (the idle loop the brief says is confirmed
alive, with `MEM8(0x3B808C)==0` and `MEM32(0x3B8090)==0` at runtime), there is an indirect call that is
**unconditional on every pass given those two measured-zero gates** — both the "command pending" branch and
the "no command" branch funnel into it:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Given the measured gates (`MEM32(0x2EB73C)==0`, both `MEM8(0x3B808C)` and `MEM32(0x3B8090)` read `0`), the
control flow reaches `loc_0019AB7D → (MEM32(0x2EB73C)==0) → loc_0019AC98` **directly**, skipping the
command-dispatch block entirely — so this `icall MEM32(MEM32(0x3B8084)+0x18)(5)` runs every single call to
`sub_0019AB60` in the observed idle state. **I could not determine what this vtable slot resolves to** (no
static vtable data), so I cannot say whether it is a movie-advance/tick call or (more likely, given
`0x3B8084` is registered via a `RegisterCallback(sub_0019AB60)` pattern in its own construction) some kind
of generic message-pump `Process(priority)` call belonging to the *input/command* subsystem the earlier
reports already traced — not necessarily the Flash movie system at all. I am flagging it rather than
asserting it either way.

**Conclusion for Q2: not found.** I can show where a screen's `.apt` name becomes a movie-slot allocation
(`sub_001819C0`) and where a loaded slot gets relocated/linked once its queue node reaches state 4
(`sub_0015F950`, Q1) — but I found no code, static string, or global that assigns a movie as "the root"/
`_level0`, and no assignment of a "current display" pointer distinct from the per-slot bookkeeping above.
This may be exactly the missing step, or it may exist behind one of the several unresolved vtable calls
noted here and in Q3 — I cannot tell which from static reading alone.

---

## Q3 — the per-frame ADVANCE and RENDER walk

**READ, with a solid chain to the loader/finalizer, and a hard wall at the actual render call.**

**The chain that reaches the queue consumer and the movie-slot poller runs regularly, and I can show every
link of it:**

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00068D90` has exactly two callers, both direct calls (`RECOMP_ABI_CALL`, so invisible to indirect-call
sampling): `sub_0006AF30` (12 call sites, all inside a large state machine in `recomp_0003.c`, addresses
`0x00077B10`-`0x0007BC42`) and `sub_00078EC0`/`sub_00078F9B`. **I could not determine whether `sub_0006AF30`
or its callers execute every frame** — direct calls compile to plain C calls and do not show up in the
brief's indirect-call-sampling list, so absence from that list proves nothing either way (this is the same
caveat `CLAUDE.md` documents for this codebase generally). Given `sub_00148210`/`sub_001480B0` are
independently confirmed by the brief to run 43 times each, *something* is reaching this chain regularly; I
just cannot point to which of `sub_0006AF30`'s ~12 call sites is the live one, or confirm the frequency is
"once per frame" versus some other cadence.

**`sub_00181D20` (`recomp_0011.c:14843-15... `, 815 bytes) is the async-I/O poller that finalizes a movie
slot, and it is called unconditionally by `sub_00068D90` (no branch precedes the call, `recomp_0003.c:31150`).**
It walks the current index `MEM32(0x2EAB4C)` into the slot table (`MEM32(0x3B37A0)`, Q2) and, on the "I/O
started, not yet checked" path, queries status twice:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Both the "more data" branch (after further BIGF/refpack-shaped calls) and the "done" branch converge on
calling `sub_00144B50` (two call sites, `recomp_0011.c:15027` and `:15172`). **This confirms the loading
pipeline is designed to converge, is driven by a call chain that is reached regularly (43 tag-pump runs, per
the brief), and is not obviously broken by any static branch I can see** — but whether `sub_001E6960`/
`sub_001E69D0` (the status queries) actually return `1` for the `intMain/legal1` screen's slot, and how many
times `sub_00144B50`/`sub_00147660` actually fire, is **not something I can determine by reading code**; it
depends on the runtime behavior of the async-I/O primitives, which I did not trace further (they are in a
different file range and are generic kernel-I/O wrappers, not movie-specific).

**The actual render/display-list walk: I could not find it.** The brief's own indirect-call sampling
already names the functions that run every frame for rendering: `sub_00118xxx` (vertex-stream emitter),
`sub_00121C80`/`sub_00121C90`, `sub_00125950`. I checked for direct callers of the first of these
(`sub_001189B0`, the family's apparent entry point):

```
grep -n "sub_001189B0);" src/recomp/gen/*.c   →  (no matches)
```

**Zero direct call sites anywhere in the image.** This is expected and consistent with the brief's own
framing ("from indirect-call sampling") — it means `sub_001189B0` is reached only through a vtable/
function-pointer slot, exactly like `0x3B8084+0x18` above, and I have no static way to find who populates
that slot or under what condition. I looked for, but could not find, a "walk display list, for each child
call Advance then Render" loop anywhere in the `0x0017xxxx`/`0x0018xxxx` Flash-module address range that
obviously calls into the `0x00118xxx`/`0x00121xxx`/`0x00125xxx` family — those two address ranges never
appear together in a `grep -n "0x00118\|0x00121\|0x00125"` restricted to `recomp_0010.c`/`recomp_0011.c`
(zero hits), which is at least consistent with the render path *not* being reached from the Flash-movie
module I traced for Q1/Q2, but I would need the reverse search (from the renderer's own module) to say
anything stronger, and I did not have budget to read that module (it is not `recomp_0010.c`/`recomp_0011.c`
and I did not locate it).

**Conclusion for Q3:** I can show, with full quotes, that the *loading-finalization* half of the pipeline
(`sub_00068D90 → sub_00181D20 → sub_00144B50 → sub_00147660`, and separately `→ sub_00146180 → ... →
sub_00148210 → sub_001480B0`) is wired together correctly and reached by a call chain that is live enough to
explain the brief's 43-run counts. I could **not** find the code that would take a state-4 (finalized)
node and turn it into vertices on screen — the vertex emitter has no discoverable static caller, and I could
not identify which vtable slot (on which object) would need to hold its address. **This is the most
significant unresolved question in this report**, and closing it needs either a runtime trace (e.g.
`RECOMP_WATCH_EXEC` on `sub_001189B0`, then a stack walk to find the actual caller) or locating and reading
the renderer/display-list module, which I did not identify.

---

## Q4 — `sub_001DF882` and the `.xsh` texture-bundle path

**READ.** `sub_001DF882` (`recomp_0012.c:145817-146045`) is one large function; the SHPX check is inside
it, not in a callee:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Its only caller, anywhere in the image:** `sub_001DF924` (`recomp_0012.c:146053-146065`), a thin wrapper
that just forwards its argument:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**`sub_001DF924`'s only caller, anywhere in the image:** `recomp_0006.c:39268`, inside `sub_000DBBA0`'s
neighborhood (`Category: game_io`, a generic chunked-resource reader — the surrounding code is a long
sequence of `sub_0002B960`/`sub_0002B970` "read next field" calls and a `sub_00200D22` allocation, not
anything Flash- or screen-shaped):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

That containing function's own callers (`sub_000DBDF0` at `recomp_0003.c:61497`, and `sub_000DBBA0` itself
at `recomp_0006.c:39517`/`:39623`) sit in address ranges (`0x00074xxx`, `0x000DBxxx`, `0x000DExxx`) that are
**disjoint from every function I traced for Q1-Q3** (`0x00068xxx`-`0x0006Bxxx`, `0x00144xxx`-`0x00149xxx`,
`0x00180xxx`-`0x001ABxxx`). `recomp_0003.c:61497` happens to be in the same *file* as the big menu state
machine that calls `sub_0006AF30` (Q3), but at a lower/different address block — **I could not determine
whether that specific container function is reachable from the `intMain/legal1` boot path or belongs to a
different, later screen** (e.g. a gameplay or character-select resource load); I did not trace it further.

**I also exhaustively listed every direct call `sub_00148210` (the tag pump) makes** (`recomp_0010.c:6794-
7444`, full body):

```
sub_001457F0, sub_00146C90, sub_00146D80, sub_00147090, sub_00147A30, sub_001480B0,
sub_0015FFE0, sub_00161160, sub_0017BAD0, sub_0017CA50, sub_0017D180, sub_0020259D
```

**Neither `sub_001DF882` nor `sub_001DF924` nor `sub_000DBBA0` appears in that list, nor did any of the 12
functions in it lead to those addresses in the greps I ran.** So: no static call edge connects the
confirmed-live screen-loading/tag-pump path to the `.xsh`/SHPX parser. This is consistent with — but does
not prove — the brief's runtime observation that `sub_001DF882` never executes.

**What I could not determine for Q4:** whether the front end registers a screen's textures through some
*other*, unidentified path (e.g. a case inside the tag pump's own 887-byte body that I did not fully
decode — I read its call list exhaustively but not every branch's semantics — or a vtable slot on one of
the `0x0017BAD0`/`0x0017CA50`/`0x0017D180` "game_vtable"-tagged callees, whose concrete behavior I did not
read). I found the `.xsh`-magic check and traced its only static call path to a dead end (a generic,
address-disjoint resource reader); I did **not** find a second, front-end-specific texture-registration
routine to point to instead.

---

## What I read directly vs. inferred vs. could not determine

**Read directly (highest confidence, all quoted above with file:line):**
- `sub_001480B0`'s full state-1/2/3 handling and the exact release/continue logic.
- `sub_00147660` is the only `esi+8=3` write in the codebase; its only caller is `sub_00144B50`; that
  function's only three call sites are inside `sub_00181D20`.
- `sub_00181D20`'s I/O-poll structure and its two convergent calls into `sub_00144B50`.
- The full call chain `sub_00068D90 → sub_00181D20` (unconditional) and `sub_00068D90 → sub_00146180 →
  sub_00146050 → sub_00148210 → sub_001480B0` (conditional but multiply-redundant).
- `sub_001819C0`'s movie-slot allocation and name-copy into `MEM32(0x3B37A0)`.
- `sub_0015F950`'s relocation/fixup loop (called only on the 3→4 transition).
- The construction of `MEM32(0x3B8084)`/`MEM32(0x3B8088)` and the unconditional `icall
  MEM32(MEM32(0x3B8084)+0x18)(5)` inside `sub_0019AB60` under the brief's measured gate values.
- `sub_001DF882`'s SHPX check and its complete, single-threaded call chain back through `sub_001DF924` to
  an address-disjoint generic resource reader.
- `sub_00148210`'s exhaustive direct-call list (12 callees, none of which are the `.xsh` parser or its
  wrapper).

**Inferred (flagged inline where used):**
- That `sub_00147530`'s per-entry array check is a "dependency readiness" gate (plausible from shape —
  looping over a count/array pair and returning a boolean — but I did not resolve what the entries mean).
- That `0x3B8084`'s `+0x18` vtable slot is *possibly* an input/command "process" call rather than a movie
  tick, based on the object's `RegisterCallback(sub_0019AB60)` construction pattern — not confirmed either
  way.
- That the `.xsh`/SHPX path being address-disjoint from the screen-loading pipeline means it is not used for
  screen textures — consistent with, but not proof of, the brief's "never runs" observation.

**Could not determine (explicit list):**
1. **Whether `sub_001E6960`/`sub_001E69D0` (the async-I/O status queries `sub_00181D20` polls) ever return
   the "done" value for the `intMain/legal1` screen's movie slot** — this is the load-bearing question for
   whether state 3 is ever reached for that specific screen, and it is a runtime fact, not a static one.
2. **What resolves at `MEM32(MEM32(0x3B8084)+0x18)`** (and at the many other unresolved vtable slots named
   above: `0x3B8088+0xC`/`+0x10`, the `sub_0019E8E0`-style `this+0x14` objects, etc.) — no vtable data is
   present in the lifted C for any heap-constructed C++ object; this needs a runtime memory read.
3. **Who calls `sub_001189B0`/the vertex emitter, and from what data (a display-list walk, or something
   else).** Zero direct call sites in the whole image; indirect-only, same wall as (2).
4. **Any explicit "become root"/`_level0`/"current movie" assignment.** Not found by any means available to
   this pass (no inline strings, no distinguishing literal-address write pattern I could isolate). It may
   not be a single pointer at all — the movie-slot array + name-list scheme in Q2 could implicitly make
   "the last successfully-finalized slot" current, but I found no code that reads the slot table that way.
5. **Whether `sub_0006AF30` (and thus the whole `sub_00068D90` chain) genuinely runs every frame, or only
   on specific menu states.** It has ~12 call sites inside one large front-end state machine; I did not
   trace which state(s) reach it or whether `intMain/legal1` is among them.
6. **What the `.xsh` texture bundle for a screen actually gets handed to, if not `sub_001DF882`.** I ruled
   the SHPX-parser path out (Q4) but did not find a positive alternative.
7. **The exact semantics of `sub_00147530`'s dependency array** (offsets `esi+0x10`, then `+0x28`/`+0x2C`
   off that) — read the loop shape, not what each entry represents.
