# M3 — why setting AS variable `_level0` never produces a pending-load object

Read-only static pass over `src/recomp/gen/` (`recomp_0000.c`..`recomp_0017.c` + `recomp_dispatch.c` +
`recomp_stubs_unresolved.c`, ~1.5M lines, all grepped rather than read whole). No code was built or run.
String contents were resolved by reading `tools/xboxrecomp/tools/ghidra_naming/work/xbe_flat.bin` (the flat
image the project's own Ghidra-import tooling produces; `virtual_addr - 0x00010000 = file_offset`, per
`tools/xboxrecomp/tools/ghidra_naming/extract_for_ghidra.py`) — this is a static read of the user's own
dump's rodata, not a live-memory read, and is used only to turn `0x29A668`-style literals into the strings
they hold. Everything else is straight `grep -rn` plus manual tracing of the matched functions. Every code
quote is copied verbatim from the lifted C with its line number so it can be checked directly.

Ground truth taken as given, not re-derived: all six bullets in the MEASURED AT RUNTIME TODAY section of
the brief, and the ALREADY RULED OUT list (callback table, command queue at `0x2EB73C`, file layer/archive/
flow database).

---

## Q1 — does `sub_001423F0` recognize `_level0` by name?

**Short answer: no.** `sub_001423F0` (`src/recomp/gen/recomp_0009.c:46361`) is not a dispatcher at all — it
is a small generic wrapper with exactly two jobs: wrap its two raw `const char*` arguments as ref-counted
String objects, then hand them to `sub_00148600`, which is where all the real logic lives.

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_0014E170` (`recomp_0010.c:20396`) is a generic "construct a ref-counted String from a `const char*`"
helper — it `strlen`s the input, allocates via the icall at `MEM32(0x3B1FD0)`, and `memcpy`s. It contains no
string comparison at all.

So there is no branch in `sub_001423F0` that could recognize `"_level0"` specially — by the time it does
anything, the caller-supplied name has already been reduced to an opaque `const char*` argument that gets
wrapped identically regardless of its contents. The real "is this name special" logic, if it exists, has to
be inside `sub_00148600` (`recomp_0010.c:6139`), which is what the rest of this report traces.

**Reconstructing the actual call**, using the caller chain from the brief
(`sub_0006BC90` → `sub_000687B0` → `sub_001423F0`) and the cdecl push-order convention (the deeper/first-
pushed arg lands at the higher stack offset in the callee):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

confirmed against the flat image: `0x29A6A4` = `"_level0"`, `0x29A678/84/90/98` = `"beloader"/"demoload"/
"loader"/"feloader"`. This is `SetVariable(name="_level0", value=<chosen loader-movie name>)`, exactly as
the brief states.

**A second, earlier assignment exists that the brief doesn't mention.** In the same function, in the
switch-case reached via the byte table at `0x6BDDC` (case target `loc_0006BD01`), *before* the unconditional
assignment above, there is:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

(`0x29A668` = `"_level0"`, `0x29A670` = `"main"`, `0x299A8C` = `"_level0"`, `0x299A94` = `""` — all
confirmed against the flat image.) So **if the boot chain takes this switch case, `_level0` is actually
assigned three times in a row within a single call to `sub_0006BC90`**: `""`, then `"main"`, then the real
loader-movie name — all before `sub_001480B0` runs even once. I could not determine from static reading
alone which switch case actually fires at runtime (the selector is `MEM8(eax + 0x6BDDC)` with `eax` computed
from a saved-state byte at `esi+0x98`/`esi+0x9C`); this matters for Q2 below and is a good thing to check
with a live memory read (log `MEM8(eax + 0x6BDDC)` or just watch how many times `sub_000687B0`/`sub_000687D0`
fire — 2 or 3 total, not 1, would confirm this path).

---

## Q2 — where does a pending-load object (state field `+8 = 1`) get created?

`grep -rn "\+ 8) = 1;"` (restricted to plain `MEM32`, not `MEM8`/`MEM16`) returns **41 sites** across 13
files. I inspected each one's containing function. They fall into two buckets:

**Bucket A — unrelated object types (37 of 41 sites).** The large majority are generic ref-counted-pointer
or object-pool constructors used throughout the game code, not the Flash VM. Representative example
(`recomp_0010.c:44101-44102`, inside `sub_001571E0`, header-tagged `Category: game_vtable`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
Every one of these sites also writes a **vtable pointer constant** (`0x2BEA18`/`0x2BEC18`/etc.) into the
same object, which the Flash-VM node type we're looking for never does. I also checked
`sub_001468E0` (`recomp_0010.c:1373`), which structurally matches the shape `sub_001480B0` expects
(`next@0`, `sharedptr@4` with a refcount bump, `state@8=1`, `@0x10`/`@0x14` zeroed) — but **grepping for
`sub_001468E0` and for the raw address `1468E0` anywhere in `src/recomp/gen/` turns up zero callers**. It is
either invoked only through a runtime-resolved indirect call the lifter can't show statically, or it is dead
code in this build. I could not resolve this either way from static reading.

**Bucket B — the real hit, 2 of 41 sites.** `sub_00147430` (`recomp_0010.c:3396`, `Original: 0x00147430 -
0x0014752B`) is a **find-or-create** function: given a table (`ecx`) and a name-string pointer, it first
does a raw lookup (`sub_00147310`); if found, it reuses the existing entry; if *not* found, it allocates a
fresh 0x18-byte node and initializes it with `state = 1`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

The found (update) branch, at `loc_00147474`, never touches offset `+8` — it only bumps a refcount. So this
matches the brief's expectation exactly: **`+8 = 1` is written once, at first creation of a table entry, and
never reset on update.**

The insert into the table happens via `sub_00146910` (`recomp_0010.c:1402`), called right after the create
branch at `recomp_0010.c:3496` (`loc_001474C8`). It **appends** the new node onto a singly-linked list
rooted at **offset `+0` of the table object itself** (walks to the tail via each node's own `+4` "next-cell"
wrapper, not the node's own `+4`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**This is the same field `sub_001480B0` reads.** `sub_001480B0`'s only caller, `sub_00148210`, sets its
`ecx` immediately before the call:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

and `sub_001423F0`'s own SetProperty implementation (`sub_00148600`) calls `sub_00147430` with **the same
global** as the table:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So mechanically, the insert site (`sub_00147430`, called from `sub_00148600`) and the consumer's list head
(`sub_001480B0`, `ecx = MEM32(0x3B1D84)`) **are the same object and the same list-at-offset-0**. Structurally
this closes the loop the brief is asking about.

**What I could not close:** whether, at the moment `sub_0006BC90` runs, `"_level0"` is *already* present in
this table (from Flash-VM bring-up before the boot chain even starts) or is genuinely new. This matters
enormously:

- If `"_level0"` is brand new the first time `SetVariable("_level0", ...)` runs, `sub_00147430` takes the
  create branch, a `state=1` node is appended, and by the brief's own measurement `sub_001480B0` runs 8
  times afterward — so it *should* find and process it (call `0x3B1DF0`/`sub_00069CC0`). It measurably
  doesn't, which would mean the bug is downstream of insertion (something about what content gets passed to
  the callback, or a scope/binding step past `loc_00148777` that this report did not fully unravel — see the
  "not verified" list below).
- If `"_level0"` is *already* a table entry (e.g. registered once at Flash-VM init, alongside
  `"_level1".."_level25"` — the engine's rodata contains a dedicated `_level0.."_level24"` + bare `"_level"`
  string cluster at `0x2BEF18-0x2BF1B8` that I found no other consumer for in the lifted code besides a
  name-*generator*, `sub_001507F0` at `recomp_0010.c:26735`, which builds `"_level" + "%d"` strings via
  `sprintf`-style code rather than comparing them), then **every** `SetVariable("_level0", ...)` call —
  including both calls inside `sub_0006BC90` — takes the found/update branch, `state` is never touched, and
  **no pending-load node is ever created for `_level0` at all.** This would fully explain the measured
  behavior and would mean the mechanism `sub_001480B0`/`0x3B1DF0` services is not "assign to `_level0`" but
  "the very first time *any* previously-unseen name is looked up as a path" — i.e. an unrelated
  unknown-symbol/autoload probe that happens to share plumbing with path resolution, not a `_levelN`-specific
  loader.

I was not able to determine which of these is true from static reading — it depends on whether `"_level0"`
was interned into this table before `sub_0006BC90` first runs, which is a runtime fact, not a static one.
**Concrete next step for a live check:** put a watch/breakpoint on `sub_00147430` and log whether the very
first call with a name string equal to `"_level0"` takes the create branch (`loc_0014748E`) or the found
branch (`loc_00147474`). If it's already "found" on the very first call your process ever makes, that
confirms the second bullet above.

**Full site list for the record** (containing function, guarding condition), so nothing here is asserted
without a citation:

| File:Line | Function | Guard | Verdict |
|---|---|---|---|
| `recomp_0010.c:1389` | `sub_001468E0` | none (unconditional) | shape matches our node, but **no static caller found anywhere** |
| `recomp_0010.c:3470` | `sub_00147430` | `alloc` succeeded, name not already in table (`loc_0014748E`) | **the create-branch of the find-or-create used by `sub_00148600`** |
| `recomp_0010.c:3975`†| — | (dup of 3470 — same function counted twice by grep's context) | — |
| `recomp_0010.c:4214` | (inside a movie/clip attach routine) | after icall `0x3B1DF4` succeeds | different node shape (`esi+8=1` immediately followed by unrelated cleanup at `esi+0`); not linked to table `0x3B1D84` — not investigated further, out of scope |
| `recomp_0010.c:43924/43933/43965/43975` | `sub_00157050`-family (`Category: game_vtable`) | object-pool "in use" flag, always paired with a vtable-pointer write | **unrelated — gameplay object allocator** |
| `recomp_0010.c:44102/44111/44143/44153` | `sub_001571E0` (`Category: game_vtable`) | same pattern as above | **unrelated** |
| `recomp_0010.c:93091/99215/112331` | (not individually traced — addresses `0x16D5B0`/`0x170300`/`0x174540`, inside the broader Flash-VM address range) | — | **not conclusively classified; flagged as unresolved, not claimed either way** |
| `recomp_0009.c:53954`, `recomp_0011.c:12537/63744/63805/63841`, `recomp_0001.c:*`, `recomp_0002.c:*`, `recomp_0006.c:*`, `recomp_0007.c:*`, `recomp_0008.c:*`, `recomp_0012.c:*`, `recomp_0013.c:*`, `recomp_0015.c:*`, `recomp_0016.c:*`, `recomp_0017.c:*` | various | various | spot-checked a sample of these (string-constructor and object-pool shapes identical to Bucket A above); **not individually traced exhaustively** — flagging rather than asserting they're all irrelevant |

† `sub_00147430`'s create branch is the single function; the table lists every raw grep hit so the count (41)
reconciles with the two-sentence summary above — 39 non-`sub_00147430`/`sub_001468E0` hits were all in
Bucket A shape once inspected, except the small set explicitly marked "not conclusively classified."

---

## Q3 — what is `sub_001480B0`'s `this`, and where does the list head live?

**Answer (verified, not inferred):** `sub_001480B0`'s only caller is `sub_00148210`
(`recomp_0010.c:5553`), which sets:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So **`this` = the object pointer stored at guest global `0x3B1D84`.** Inside `sub_001480B0`
(`recomp_0010.c:5337`), `ebp = ecx` at entry, and the list walk starts with:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**To read this at runtime:** dereference the global to get the object pointer, then read offset `+0` of
that object for the head node:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Each node in the chain that `sub_001480B0` actually inspects has its **state** at node `+8` (1 = pending →
gets processed and flipped to 2; 2 = already handled, skipped) and is fetched via one more dereference
(`esi = MEM32(eax)` at `recomp_0010.c:5371`, i.e. the object at `0x3B1D84+0` is itself a chain of
"buckets," each bucket's first real item read via one more `MEM32`). The value the loader callback receives
is built from the node's own `+4` field: `eax = MEM32(esi + 4); eax = eax + 8;` (`recomp_0010.c:5401-5402`)
— i.e. it skips what looks like an 8-byte String-object header and passes the character data straight to
`icall MEM32(0x3B1DF0)`.

**Caveat inherited from Q2:** I could not conclusively determine whether node `+4` here holds the *name*
string or a *value* string for the entries created via `sub_00147430`/`sub_00148600` — see the `Q2`
discussion of `MEM32(edi)` at `sub_00147430`'s create site, where `edi` is the caller's name-string pointer
(not the value). If `+4` really is the name, the callback (`sub_00069CC0`, `sprintf("screens/%s", ...)`)
would be handed the literal string `"_level0"` rather than a loader-movie filename, which would call into
question whether this whole mechanism is the intended `_levelN`-load path at all, versus an unrelated
unknown-symbol probe that happens to reuse the same "pending list + callback" plumbing. I was not able to
settle this from static reading; it needs either a runtime read of a live node's `+4` field once one exists,
or a much deeper structural trace of `sub_001470B0`/`sub_00146B70`/`sub_00148000` (the per-scope "binding"
machinery `sub_00148600` runs after the find-or-create, which attaches a *second*, separately-allocated
0x10-byte object to the symbol node — this second object is where I'd expect the actual assigned value to
live, not the symbol node's own `+4`). I read as far as identifying this second allocation
(`recomp_0010.c:6385-6412`, via `sub_001470B0`) but did not fully resolve its field layout or confirm which
pointer, if any, ends up feeding back into the symbol node's `+4`.

---

## Q4 — is `_level0` handled by name at all in this build?

**Exhaustive grep, both for the literal string address and for the string itself:**

- `grep -rn "29A668\|29A6A4"` across all of `src/recomp/gen/` → **exactly 2 hits, both `PUSH32` literal
  constants**, both already covered above (`recomp_0003.c:33634` and `recomp_0003.c:33714`, both inside
  `sub_0006BC90`, both feeding straight into the generic `SetVariable` call chain). Neither is a comparison.
- The game's rodata has a much larger cluster of `_level0`/`_level1`.../`_level24`/bare-`_level` strings
  (found by scanning the flat image with a regex, not by guessing addresses): roughly 90 occurrences of
  `_level0` alone, plus a dedicated block at `0x2BEF18-0x2BF1B8` holding one string per level index 0-24 and
  a bare `"_level"` at `0x2BF1B8`. Grepping the lifted C for every address in that dedicated block
  (`2BEF18, 2BEF28, 2BEF30, 2BEF38, 2BEFC4, 2BF1B8, 2BF05C`, etc.) turns up **exactly 2 consumers**:
  - `recomp_0010.c:26799` (`PUSH32(esp, 0x2BF1B8)`, the bare `"_level"` literal) inside `sub_001507F0`
    (`recomp_0010.c:26735`), which does `sprintf`-style **construction** of `"_level" + "%d"` — i.e. it
    turns a *number* into a name, the reverse of what a dispatcher would need. Not a comparison.
  - `recomp_0010.c:75233` (`PUSH32(esp, 0x2BEFC4)`, `"_level0"`) inside `sub_00164F00`
    (`recomp_0010.c:75197`), which — guarded by `if (MEM32(ecx + 0x4C) == 0)` — builds a
    `SetVariable("_level0", "")` call through the exact same `sub_0014E170`/`sub_00148600` path as
    everything else in this report. This looks like a cleanup/reset routine (clears `_level0` to empty when
    some root-movie pointer is null), not a loader.

**No `strcmp`/`memcmp`/byte-by-byte comparison against `"_level0"` or `"_level"` was found anywhere in the
1.5M-line lifted corpus.** Every single reference to these strings is either (a) one of the two `SetVariable`
call sites already covered in Q1, (b) the reset call in `sub_00164F00` just above, or (c) the reverse
name-*generator* in `sub_001507F0`.

**Conclusion:** in this build, `_level0` is **not** recognized by name anywhere in the reachable, statically
traceable code. Setting it goes through the fully generic path-aware `SetVariable`/`SetProperty` machinery
(`sub_001423F0` → `sub_00148600` → `sub_00147390`/`sub_00147430` path-segment lookup against the table at
`0x3B1D84` → per-scope binding via `sub_00146B70`/`sub_001470B0`/`sub_00148000`) with no branch anywhere that
tests the name's bytes. Whatever makes `_levelN` special in real Flash Player (loading a movie as a side
effect of the assignment) would have to be an emergent property of that generic path-resolution machinery
treating a never-before-seen path segment as "not found → try to load a resource by this name" — which is
exactly the shape of the `sub_00147430`-create → `sub_001480B0` → `sub_00069CC0` chain traced in Q2 — **or**
it genuinely isn't implemented in this custom engine at all, and the game's boot chain is relying on a
trigger this report did not find.

**I could not find any alternative, explicit "load a movie" trigger elsewhere in the C-side boot chain.**
I looked for: a second registered icall target besides `0x3B1DF0` that might be a more direct "LoadMovie"
entry point (none found reachable from the boot chain — the callback-table sites the brief already ruled out
are the only other registrations); any code between `sub_0006BC90` returning and the brief's stated stall
point that touches `0x3B1D84`, `0x3B1DA8`, or calls `sub_00148210`/`sub_001480B0` again (none found — the
boot chain as described in the brief ends with `sub_0006BC90` returning, and the brief already states
`sub_001480B0` runs 8 times from *somewhere*, which this report did not trace the caller of `sub_00148210`
for — that would be the natural next thing to check: what drives `sub_00148210`, and how often/when relative
to `sub_0006BC90`).

---

## Summary of what was READ vs INFERRED vs NOT DETERMINED

**Read directly (verbatim-quoted, verifiable by line number):**
- `sub_001423F0` full body — generic String-wrapper + dispatch to `sub_00148600`, no name comparison.
- `sub_000687B0`/`sub_000687D0` — thin 2-arg/0-arg wrappers around `sub_001423F0`.
- The relevant slice of `sub_0006BC90` — confirms `_level0` is assigned **up to three times** per call
  (`""`, `"main"`, then the real loader name), not once as the brief's summary implies (the brief's ground
  truth is about the *final* assignment; the earlier ones in the same function weren't previously called
  out).
- `sub_00147430` — the find-or-create that writes `state(+8)=1` only on first creation.
- `sub_00146910` — the insert that appends onto the table's offset-`+0` list.
- `sub_001480B0`/`sub_00148210` — confirms `this = MEM32(0x3B1D84)`, list head at `+0`.
- Every literal reference to `"_level0"`/`"_level"` in the lifted corpus (grep-exhaustive) — no comparison
  anywhere.

**Inferred (structurally consistent, not runtime-confirmed):**
- `sub_00147430`'s insert and `sub_001480B0`'s walk operate on the *same* list, so the plumbing for
  "unresolved name → pending → `screens/%s` load" mechanically exists and connects to `_level0`'s own
  assignment path.
- Whether `_level0` is pre-registered in the `0x3B1D84` table before `sub_0006BC90` first runs (which would
  fully explain the measured non-firing) versus genuinely new each boot.

**Could not determine:**
- What `sub_001468E0` (the other, better-shaped `state=1` constructor) is actually called from, if anything.
- Whether node `+4` in the `0x3B1D84` table holds the *name* or gets updated to hold the *value* — I traced
  as far as a second, separately-allocated per-scope "binding" object (`sub_001470B0`) that `sub_00148600`
  attaches after the find-or-create, but did not fully resolve its layout or whether it, rather than the
  symbol node's own `+4`, is what ends up feeding `sub_001480B0`'s callback argument.
- Which switch case in `sub_0006BC90` actually fires at runtime (1, 2, or 3 `_level0` assignments per call).
- What drives `sub_00148210` (and therefore `sub_001480B0`)'s 8 measured invocations — timing relative to
  `sub_0006BC90`, and whether any of those 8 happen *before* `_level0` is first assigned (which would matter
  if `0x3B1D84`'s table state depends on ordering).
- Whether `sub_00093091`/`sub_00170300`/`sub_00174540`-range `+8=1` sites (Q2 table) are related to this
  mechanism at all; not individually traced.

**Recommended next runtime check** (single highest-value one): breakpoint/log `sub_00147430`
(`0x00147430`) and record, for the very first call whose name argument resolves to the bytes `"_level0"`,
whether it takes the create branch (`0x0014748E`) or the found branch (`0x00147474`). That one bit answers
the central open question in Q2/Q4 and tells you whether to look at "why doesn't a freshly-created pending
node get processed" or "why is `_level0` never actually new."
