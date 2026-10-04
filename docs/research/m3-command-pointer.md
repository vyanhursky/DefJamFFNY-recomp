# M3 — the front-end command pointer at guest `0x002EB73C`

Read-only static pass over `src/recomp/gen/` (20 files, `recomp_0000.c`..`recomp_0017.c` +
`recomp_dispatch.c` + `recomp_stubs_unresolved.c`). No code was built or run in this session. All grep
passes below were run with `grep -rn` from the `src/recomp/gen/` directory root, so they cover every
generated file, not just the one most of the hits landed in. Every code quote is copied verbatim from the
lifted C; line numbers are given so each claim can be checked directly.

Ground truth taken as given, not re-derived: the five MEASURED FACTS in the task brief, and in particular
that a hardware write watchpoint on `0x002EB73C` recorded **zero writes of any kind, through any
addressing mode**, over a full run (see `src/hooks/watchpoint.c` header comment, which independently
documents the same problem this report investigates).

---

## Q1 — every write to `0x002EB73C`

`grep -rn "0x2EB73C\|0x002EB73C"` across all of `src/recomp/gen/` returns exactly **5 lines, all in
`recomp_0011.c`, all in three functions**. Only one of the five is a write:

| Line | Function | Access |
|---|---|---|
| 71401 | `sub_0019AB60` | read |
| 71419 | `sub_0019AB60` | read |
| **71987** | **`sub_0019AE50`** | **write** |
| 72785 | `sub_0019B330` | read |
| 80472 | `sub_0019E8E0` | read |

**READ (verified).** `sub_0019AE50` is the *only* function in the entire lifted image that assigns to
`0x2EB73C`, and the assigned value is always `0`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

There is **no condition guarding this write** — the function is unconditional top-to-bottom, no branches.
Before the write it zero-fills 35 dwords (`0x23`) starting at `0x2EBE90` (`rep stosd`, i.e. it clears
`0x2EBE90..0x2EBF1C`), then unconditionally sets `0x2EB73C = 0`. This is a **reset/clear** routine, not a
"post a command" routine — it is the thing that *un-sets* the pointer, not the thing that would set it. I
did not trace its callers (out of scope for "who sets it"), but functionally it cannot be the missing
setter: it only ever writes zero.

**Conclusion for Q1:** static analysis of the lifted C finds **no code path, anywhere in the generated
image, that ever assigns a non-null value to `0x2EB73C` through a literal address.** Combined with the
runtime watchpoint result you already have (zero writes of *any* kind, any addressing mode, for the whole
run — which rules out an indirect/register-relative write that a literal-address grep would miss), this
should be read as: **the instruction that would post the first command either does not exist in this
build, or lives on a code path that never executes.** I could not determine which. See Q3/Q4 for the
closest I could get to locating where that write *should* happen.

---

## Q2 — what reads `0x002EB73C`, and what is the structure

### Reader 1 (the main consumer): `sub_0019AB60` — the front-end idle loop itself

This is the loop the brief already identified as running on the worker thread. Quoting the relevant
section (lines 71374–71435, `recomp_0011.c`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So `0x2EB73C` gates whether the loop does anything at all this iteration
(`loc_0019AB7D`: `if (MEM32(0x2EB73C) == 0) goto loc_0019AC98;` — the idle path). This is exactly the stall
the brief describes.

When it *is* non-null, `ecx = MEM32(0x2EB73C)` is treated as a **pointer to a command struct**, and
`MEM32(ecx + 8)` is read as a **command-id integer** (`eax`), then `eax - 1` is used as an index into a
31-entry jump table at `0x19ACB8` that dispatches to one of 25 distinct handler functions (`sub_0019FC70`,
`sub_0019FD00`, `sub_001A08E0`, `sub_0019EBC0`, `sub_0019EC60`, `sub_0019EDA0`, `sub_0019EE60`,
`sub_0019EEF0`, `sub_0019F000`, `sub_0019F110`, `sub_0019F4F0`, `sub_0019F5C0`, `sub_0019F650`,
`sub_0019F710`, `sub_0019F790`, `sub_0019F7F0`, `sub_0019F890`, `sub_0019F960`, `sub_0019FFC0`,
`sub_001A0640`, `sub_001A0EF0`, `sub_001A1420`, `sub_001A1BA0`, `sub_001A20A0`), one per command id. So
**a "command" is a struct pointer whose dword at offset +8 is a command-id/opcode**, dispatched through a
switch, i.e. a classic "message struct" not a bare function pointer.

**Ownership note the brief should have:** the loop never re-nulls `0x2EB73C` after dispatch — it clears
the *buffer contents* (`0x2EBE90..0x2EBF1C`) each pass but not the pointer itself. So once set, the pointer
would stay set permanently unless something else clears it (that "something else" is `sub_0019AE50`, Q1).
That is consistent with a design where the pointer is set **once** at startup to the fixed address of a
static command-struct buffer, and thereafter only the buffer's *contents* (in particular the id field) are
rewritten to drive state transitions — see Q4.

### Reader 2: `sub_0019B330` — a boolean "is a command pending" predicate

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This function does nothing but `return (0x2EB73C != NULL) ? 1 : 0;`. I did not trace its callers (not
asked, and indirect-call fan-in makes it expensive); it reads like a small helper other code calls to ask
"is there a command in flight."

### Reader 3: `sub_0019E8E0` — a thiscall method that branches on the same pointer

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

I did not fully chase both branches (`loc_0019E915` vs. the vtable call at `esi+0x14`) — this is a `this`-
qualified method on some other object, and without knowing what calls it with what `this` I can't say what
subsystem it belongs to. Flagging as **not fully traced**, included here only because it is a reader.

**Conclusion for Q2:** the structure at `MEM32(0x2EB73C)` is a **pointer to a command/message struct**,
not a bare function pointer. Confirmed field: **offset `+8` is a 1-based command-id** consumed by a
25-way switch in the idle loop.

---

## Q3 — where does `sub_00069F10`'s kickoff queue its async request, and who consumes it?

**Short answer: I could not find it.** I read `sub_00069F10` in full and its five suggested callees; none
of them touch `0x2EB73C`, `0x2EBE90`, or anything in that page. I can report what they *are*, which rules
them out as the queue-insert point, but I did not find the actual insert.

`sub_00069F10` (`recomp_0003.c:28839`) is 162 instructions. Structurally it:
1. Early-returns if `MEM8(esi+0x41) != 0` (a "second load" tries the case brief already ruled as taken —
   the brief states it does NOT take this early return in the observed run).
2. Calls `sub_00068500`, `sub_00069E30`, `sub_000686B0(this=esi)` (font setup — brief confirms font archive
   opens here), `sub_00069D30`, `sub_00181230`, then builds a call to `sub_00182950` with two constant
   addresses `0x2EAB78` and `0x345118` pushed as arguments (each appears **exactly once** anywhere in the
   generated code — I could not determine their role beyond "output/scratch pointers passed by address" and
   did not trace into `sub_00182950` to resolve them; flagging as unresolved rather than guessing).
3. Calls `sub_00146200(this=esi, 0)`.
4. Conditionally calls `sub_000600A0` and unconditionally `sub_0005F930`, then conditionally
   `sub_00055FB0`.

I read all three of the last group in full. **None of them are queueing logic — they are field-zeroing
constructors:**

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00146200` (`recomp_0010.c:59`, 125 instructions) I also read in full. It is a **Flash/SWF font
allocator init**: it repeatedly calls through `MEM32(0x3B1DD0)` (a heap "Alloc" vtable slot, called 4 times
with sizes `0xC`, `4`, `0x18`, `0x1C`, `0x1294`), stores the results into globals in the `0x3B1Dxx` page
(`0x3B1DC0`, `0x3B1DA8`, `0x3B1DA0`, `0x3B1D88`, `0x3B1D84`), and finishes by setting `0x3B1DB0 = 1`. This
page (`0x3B1Dxx`) is a completely different memory region from the front-end command page (`0x2EBxxx`/
`0x3B80xx`). Nothing here references `0x2EB73C`, `0x2EBE90`, `0x3B8084`, or `0x3B8088`.

**What this means:** the SWF/font kickoff chain (`sub_00069F10` and the five suggested callees) appears,
as far as I traced it, to belong to an **entirely separate subsystem** from the front-end command struct —
it allocates font/Flash-runtime buffers, not front-end messages. If the async asset request really is
posted somewhere in this call tree, it must be inside one of the functions I did *not* fully trace to the
bottom: `sub_00068500`, `sub_00069E30`, `sub_00069D30`, `sub_00181230`, `sub_00182950` (the two I only
partially read), or inside an indirect-call target reached through `MEM32(0x3B1DD0)` or similar vtables
that can't be resolved statically. I did not have budget to chase all of those to completion and would
rather say so than guess.

**Conclusion for Q3: not determined.** I can rule out the five candidate functions the brief named as the
queue-insert point (they are constructors touching unrelated memory), but I did not find the actual insert
site or its consumer. This needs either more/deeper static tracing of the untraced callees above, or a
runtime watchpoint on a candidate address once one is identified.

---

## Q4 — the structure around `0x2EB59C..0x2EB73C`

**What I read directly:**

- `0x2EB59C` appears **exactly once** in the entire generated codebase, at `recomp_0011.c:72521`, inside
  `sub_0019B0C0` (the registration-chain function the brief already identified):

  *Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

  `0x2EB59C` is passed **by value as a raw address constant** into `sub_0019ADA0`. I read `sub_0019ADA0`
  in full (`recomp_0011.c:71874`, 53 instructions) and it does **not** dereference that argument anywhere
  I could find by literal address, nor does it write `0x2EB73C`. What it does with the incoming stack
  argument (if anything — the function's declared "1 params" doesn't match the two pushed args at the call
  site, and I could not resolve that mismatch) I could not determine. **This is the one place in the whole
  codebase that references the `0x2EB59x` end of the region, and I was not able to connect it to
  `0x2EB73C`.** Flagging as unresolved rather than asserting a link.

- The command buffer itself, `0x2EBE90`, is touched **134 times** across the codebase (`grep -c` on
  `0x2EBE9`/`0x2EBE[0-9A-F][0-9A-F]`). The clear routine (`sub_0019AE50`, Q1) zero-fills 35 dwords
  (0x8C bytes) starting there, i.e. `0x2EBE90 .. 0x2EBF1C` exclusive. Many of the switch-table handler
  functions from Q2 (`sub_0019EBC0`, `sub_0019EC60`, `sub_0019EDA0`, `sub_0019EEF0`, `sub_0019F000`,
  `sub_0019F110`, `sub_0019F4F0`, `sub_0019F5C0`, `sub_0019F650`, `sub_0019F710`, `sub_0019F7F0`, and
  others) rewrite fields inside this same buffer with a command-id in the `0x9..0x17` range at
  `0x2EBE94`, e.g.:

  *Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

  i.e. these are the **case handlers of the same idle-loop switch** (Q2) — each one, after doing its own
  work, can build the *next* command in place by rewriting the id field and payload fields of the shared
  buffer, without ever re-touching the pointer at `0x2EB73C`. This matches a "pointer set once, id field
  mutated repeatedly to drive a state machine" design.

**What I am INFERRING, not what I read:** the loop's own code (Q2) computes `MEM32(ecx + 8)` as the
command id, where `ecx = MEM32(0x2EB73C)`. The buffer's id field, written by all the case handlers above,
is at `0x2EBE94`. For those to be the same field, `0x2EB73C` would have to hold the value `0x2EBE8C`
(`0x2EBE94 - 8`), i.e. **4 bytes before the start of the memset'd buffer at `0x2EBE90`**. I could find zero
occurrences of the literal `0x2EBE8C` anywhere in the codebase (as either a read or a write), which is
*consistent* with this theory (the loop only ever reaches that offset by adding `+8` to a pointer value
it already holds in a register, so a literal-address grep for `0x2EBE8C` would never find it even if the
theory is right) but does **not confirm** it — I have no direct evidence for the exact numeric value that
belongs at `0x2EB73C`, only that it is a pointer whose `+8` field is the buffer's id field. **Do not treat
`0x2EBE8C` as confirmed** — treat it as the single most likely candidate value based on offset arithmetic,
nothing more.

**Field map (confirmed fields only, offsets relative to whatever `0x2EB73C` points at):**

| Offset (relative) | Absolute (if base = `0x2EBE8C`, unconfirmed) | Field | Evidence |
|---|---|---|---|
| `+8` | `0x2EBE94` | command id (1-based, switch key) | Q2 loop code + Q4 handler writes |
| `+0xC`? | `0x2EBE98` | payload word 1 | handler writes (e.g. `sub_0019EBC0`) |
| `+0x10`? | `0x2EBE9C` | payload word 2 | handler writes |

I did not map further fields (`0x2EBECC`, `0x2EBED0`, `0x2EBED4`, etc.) beyond noting they exist and are
written by the same handler functions — that would need per-handler tracing against the specific opcode
each represents, which is out of scope for this pass.

**Who owns the structure:** based on the registration chain (brief + `sub_0019B0C0` above), ownership sits
with whatever object lives at `MEM32(0x3B8084)` (registers the idle loop as a callback on it) and
`MEM32(0x3B8088)` (dispatched via vtable `+0xC` and `+0x10` throughout the idle loop and its callees) —
these read as a "front-end manager" and a second collaborating object (font/UI string table, given
`sub_0019ADA0`'s calls into `sub_0019D320`/`sub_0019C1F0`/`sub_0019C0B0` against `MEM32(0x3B8078)`). I did
not resolve either object's concrete type/vtable.

---

## What I could not determine (explicit list)

1. **Who is supposed to write `0x2EB73C` to a non-null value.** No such write exists anywhere in the
   generated C by literal address, and the runtime watchpoint independently confirms zero writes of any
   kind. I cannot say whether the write instruction was dropped by the lifter, belongs to a function that
   is genuinely never called, or was never present in the original binary's reachable front-end path (e.g.
   gated behind a feature/build flag).
2. **The queue/insert point for the async SWF/asset load kicked off by `sub_00069F10`.** Traced the
   function and its five suggested callees in full; none reference the `0x2EBxxx`/`0x3B80xx` command-struct
   region. The actual async post (if any) is somewhere I did not reach: `sub_00068500`, `sub_00069E30`,
   `sub_00069D30`, `sub_00181230`, `sub_00182950` (partially read only), or behind an unresolved indirect
   call.
3. **The exact base value that belongs in `0x2EB73C`.** Inferred as likely `0x2EBE8C` from offset
   arithmetic against the confirmed `+8` id field; not confirmed by any direct write or read of that
   literal address.
4. **What `sub_0019ADA0` does with its `0x2EB59C` argument.** Read the function in full; found no
   literal-address use of that value, and could not reconcile the "1 params" doc comment against two
   pushed arguments at the call site.
5. **`sub_0019E8E0`'s two branches** (Q2, reader 3) — read only the branch-on-`0x2EB73C` entry, not both
   arms to completion.
6. **The concrete types of the objects at `MEM32(0x3B8084)` and `MEM32(0x3B8088)`** — only their vtable
   call sites were observed, not their construction.
