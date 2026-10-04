# M3 node lifetime: why the Flash player's node-table head (`0x3B1D84` → `0x806C6A50`, offset `+0`) is null at every consumer call

Scope: read-only reverse engineering of `sub_00147430`, `sub_00146910`, `sub_00146C30`, `sub_00146C90`
(all in `src/recomp/gen/recomp_0010.c`), plus the lifter itself (`tools/xboxrecomp/tools/recomp/lifter.py`),
to explain the runtime observation that `MEM32(0x806C6A50)` (table `+0`) is always `0` when
`sub_001480B0` reads it, even though 7 create-branch inserts ran first and "ordering is not a race."

**Bottom line up front:** the node **is** supposed to survive. This is **not** a case of the consumer
reading the wrong field (question 4 does not apply). The node is destroyed immediately after every
single insert because of a mis-lifted `jne` in `sub_00147430` — a conditional branch whose flags come
from a `cmp` on one side of a control-flow join and from a `dec` on the other, which the lifter's own
basic-block boundary logic cannot resolve, so it emits a dummy `_flags` variable that is declared once,
**never assigned anywhere in the function**, and therefore always reads `0`. The `if (_flags ...)` guard
that should skip the destroy call every time (because the refcount is `1`, not `0`) never fires, so the
destroy call — and with it, the unlink of the just-inserted node from the table's `+0` list — runs
unconditionally, every time.

All addresses are guest (original Xbox) addresses.

---

## 1. `sub_00147430`'s reference discipline

`sub_00147430(ecx = table = 0x806C6A50, ...)` is a find-or-create. Full control flow, with every
increment/decrement of the created entry's refcount (entry field `+0`) quoted.

### 1.1 Lookup

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00147310` is the actual lookup (not one of the four functions this report was asked to open — not
read). If it returns non-null, execution falls through to the **found** branch (`loc_00147474`); if
`0`, it jumps to the **create** branch (`loc_0014748E`). The ground truth states all 7 observed calls
took the create branch, so §1.2 is the path that matters; §1.3 (found branch) is included for
completeness and flagged as a secondary, lower-confidence observation.

### 1.2 CREATE branch — allocates the entry (`sub_00147430`, quoted verbatim)

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So `sub_00146910` is called as `sub_00146910(ecx = table = 0x806C6A50, stack-arg = &local-holding-esi)`,
confirming the ground truth's "always `ecx = 0x806C6A50`" for this call. **The refcount on the
freshly-allocated entry is `1` at the moment `sub_00146910` runs** (bumped by REF A immediately before
the call).

### 1.3 After `sub_00146910` returns — two more refcount ops, then the buggy guard

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Reference-count accounting (READ, arithmetic verified from the quoted lines above):**

| op | line (loc) | delta | running total | who it represents |
|---|---|---|---|---|
| entry alloc | `loc_0014749D` | init `0` | 0 | raw memory |
| REF A | `loc_001474C6` | +1 | 1 | taken right before handing the entry to `sub_00146910` (list insertion) |
| REF B | `loc_001474E3` | +1 | 2 | taken right after `sub_00146910` returns, once `*edi = esi` (the return-to-caller value) is set |
| REF C | `loc_001474F6` | -1 | **1** | released unconditionally once REF B has been taken |

Net: **the entry's refcount ends the function at `1`**, not `0`. REF A/REF C bracket the call into
`sub_00146910` (matches the pattern of a temporary/scoped reference held only across that call, released
immediately after — the "scoped guard" idea from the ground-truth guess, except it's REF A/REF C on the
*entry*'s own refcount, not `sub_00146910`/`sub_00146C30`/`sub_00146C90` themselves — see §2). REF B is
the surviving reference, presumably owned by whoever `sub_00147430`'s caller is (the value written to
`*edi`).

Since the refcount is `1` (nonzero) at `loc_001474FF`, the correct behavior is to take the
`goto loc_00147514` (skip destroy) — i.e. **leave the entry, and its just-inserted list cell, alone.**
Instead, as shown in §3, the branch is always-false due to a lifter gap, so `sub_00146C90` (destroy) runs
every time regardless.

### 1.4 The FOUND branch (not exercised by the 7 observed calls — lower confidence, included for completeness)

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

I flag this as a possible **second** anomaly: the increment at `MEM32(esi) = ecx` is immediately
overwritten by `MEM32(esi) = eax` where `eax = ecx - 1`, i.e. the refcount write nets to unchanged. I
could not determine whether this is a genuine bug (mirroring §3's class) or intentional (e.g. the "found"
path is not supposed to add a durable reference, only a transient one that the same REF-C-style decrement
at `loc_001474FF` is meant to net against). **This branch never ran in the 7 measured calls, so it is not
part of the explanation for the observed symptom, and I did not chase it further.**

---

## 2. `sub_00146910`, `sub_00146C30`, `sub_00146C90` — what they actually are

**Verdict on the working guess: no, these are not a scoped guard or a temp-reference pair. They are the
real list push/remove/destroy operations.** The scoped-guard pattern that *does* exist in this code is
REF A / REF C on the entry's own refcount inside `sub_00147430` itself (§1.3), not these three functions.

### 2.1 `sub_00146910` — append a wrapper cell to the table's `+0` linked list

Full body (already quoted in the prompt; re-quoted here with the interpretation inline):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This is a plain **append-to-singly-linked-list**: it allocates an 8-byte "cell" object (`{ entry_ptr,
next }`), and either sets `table->+0` directly (first insert, list was empty) or walks to the current
tail (`next == 0`) and links the new cell there. **On the very first of the 7 observed calls, this is
literally the write of `table+0`** that the ground truth already knew about. On calls 2–7, it appends
instead of touching `+0` — meaning after all 7 successful inserts (if nothing removed them), `table+0`
would hold cell #1, chained via `+4` through cells #2…#7.

`sub_00146910` does **not** touch the entry's own refcount at all (no `MEM32(entry) = ...+1` anywhere in
this function) — it only copies the raw pointer into the cell. Ownership bookkeeping is entirely the
caller's job (§1.3's REF A/B/C).

### 2.2 `sub_00146C30` — remove a specific entry's cell from the table's `+0` list

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This is a **remove-by-value from a singly linked list**, unlinking whichever cell wraps the given entry
pointer (checking the head specially, then walking with one-behind lookahead for the interior/tail
case), and freeing the cell object (via the icall at `0x3B1DD4`) once unlinked. It operates directly on
`table->+0` — this is the same field the consumer reads. **It is a genuine list-removal primitive, not a
guard.**

### 2.3 `sub_00146C90` — destroy an entry (calls `sub_00146C30` as step 1)

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00146C90` is the entry **destructor**: unlink from the table list (`sub_00146C30`), tear down any
attached resource depending on `state` (`+8` == 3 or 4), release `+0x14`, and decrement the owning
"type" object's live-instance counter (undoing the `MEM16(ecx)++` from `sub_00147430`'s create branch),
destroying that too if it reaches zero. This is a real, correct-looking teardown routine **when called
at the right time** — i.e. when the entry's refcount has actually reached `0`. The bug (§3) is that
`sub_00147430` calls it when the refcount is `1`.

---

## 3. Root cause: a mis-lifted `jne` whose flags don't survive a basic-block boundary

### 3.1 The exact site

In `sub_00147430`, immediately after REF C (§1.3):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`_flags` is declared once, at the top of `sub_00147430`:

```c
int _flags = 0; /* fallback flag var */
```

I grepped the full body of `sub_00147430` (lines 3396–3555 of `recomp_0010.c`) for every occurrence of
`_flags`; the only two hits are that declaration and this one `if (_flags ...)` check. **`_flags` is
never assigned inside this function.** It is permanently `0`, so `if (_flags)` is permanently false, so
the `goto loc_00147514` (which would skip the destroy call) is **never taken**. Execution always falls
into `loc_00147501` and always calls `sub_00146C90(esi)` — regardless of what the `cmp eax, ebx` two
lines above it actually computed. Note the comparison it should have used is sitting right there:
`_fa = eax = 1` (the post-decrement refcount from REF C), `_fb = ebx = 0` — `CMP_NE(_fa, _fb)` would
correctly evaluate **true** and take the skip branch. The lift computed the right operands and then
discarded them.

### 3.2 Why: this is a documented, general lifter limitation, not a one-off typo

`tools/xboxrecomp/tools/recomp/lifter.py`, in the code path that lifts a conditional jump with no known
flag-setter (`_lift_jcc`, around line 2260), has this comment:

```
# Flag tracking resets at a block boundary, because which predecessor
# arrives is not known here. _cf survives it: it is a real variable
# holding the carry, so a jb/jae landing on a label still reads the
# right bit while the generic _flags fallback -- which nothing ever
# assigns -- is silently always false. The XCompress bit reader jumps
# into the middle of its refill exactly this way.
cond = "_flags"
```

and, near `COND_MAP`/`FLAG_SETTERS` (around line 347):

```
# A jb/jae reading CF after one of these is exact, which matters because the
# generic fallback is a _flags variable nothing ever assigns -- the condition
# came out always-false.
```

`loc_001474FF` is a label (a basic-block boundary) because it is a jump target: `sub_00147430`'s found
branch (`loc_00147474`) also ends with `goto loc_001474FF;` (line ~3449, see §1.4), reaching the same
address by a different path whose own last flag-setter is a bare `dec eax` rather than a `cmp eax, ebx`.
The lifter's block-by-block driver (`lift_basic_block`, `lifter.py:3301`) threads `last_flag_setter`
through blocks as a simple linear/sequential handoff and — per the comment above — resets/does not trust
that state across a block boundary in general, because it cannot prove which predecessor's flags are
live at a join point. So when it reaches the `jne` at `loc_001474FF` as the first instruction of its
block, `last_flag_setter` is not available to it, `_make_condition` is not invoked, and it falls through
to the generic single-instruction jcc lifter (`_lift_jcc`), which — lacking any tracked flag-setter —
emits the `_flags` fallback unconditionally.

This is the exact class of bug flagged in the prompt (mis-lifted flag-dependent instructions, in the
company of the already-fixed `rcl`/`rcr`): **a conditional jump separated from its flag-setting
instruction by a basic-block/label boundary loses its flag operands and is silently replaced by an
always-false condition.** Here the practical effect is that a cleanup/destroy call that should run only
when a refcount hits zero instead runs unconditionally on every call, which is precisely consistent with
the runtime observation: all 7 creates insert their cell (via `sub_00146910`, §2.1), and each one is
immediately, unconditionally unlinked again by the very next `sub_00146C90` → `sub_00146C30` call (§2.2,
§2.3) before `sub_00147430` returns — leaving `table->+0` at `0` (or, for calls 2–7, removing the
just-appended tail cell, which nets to the same empty list once every insert has been individually
un-inserted).

### 3.3 Scope check: is this isolated or systemic?

```
$ grep -rn "if (_flags" src/recomp/gen/ | wc -l
398
```

**I found 398 occurrences of this exact `if (_flags ...)` pattern across the generated sources.** I
confirmed only the one at `loc_001474FF` in `sub_00147430` is live and produces observably wrong behavior
(via the runtime measurements already in hand). **I did not audit the other 397** — some may be
genuinely unreachable/dead code, some may happen to land on paths where the always-false outcome is
coincidentally harmless, and some may be real, silent bugs of the same shape. I can't respons­ibly
characterize how many of the 398 are actual bugs without checking each one against a specific runtime
symptom, which I did not do. Flagging the count only as a signal that this is a **general lifter gap**
(basic-block-boundary flag loss), not something specific to this table.

---

## 4. Answering the prompt's question 4 directly

Not applicable. §1–§3 establish that the entry is designed to survive `sub_00147430` with refcount `1`,
and that it is destroyed only because of the `_flags` lift bug, not because `sub_001480B0` is reading the
wrong offset. `sub_001480B0`'s read of `MEM32(ebp)` at table `+0` (quoted in the prompt) matches exactly
the field `sub_00146910` writes on first insert and `sub_00146C30` clears on removal — it is reading the
correct, intended field. No alternate persistent-storage offset exists to point the consumer at.

---

## 5. What I read directly vs. inferred vs. could not determine

**Read directly (quoted above), from `src/recomp/gen/recomp_0010.c`:**
- Full body of `sub_00147430` (lines 3396–3555): lookup call, create branch, found branch, the REF
  A/B/C refcount sequence, and the exact `if (_flags ...)` guard at `loc_001474FF`.
- Full body of `sub_00146910` (lines 1402–1463): cell allocation, head-set-on-empty, tail-append walk.
- Full body of `sub_00146C30` (lines 1955–2043): head-unlink and search-and-unlink-by-value.
- Full body of `sub_00146C90` (lines 2051–2136): call into `sub_00146C30`, state-gated resource
  teardown, type-object refcount decrement and conditional destroy.
- Confirmed via grep that `_flags` is declared once and never assigned anywhere else in `sub_00147430`.
- `tools/xboxrecomp/tools/recomp/lifter.py`: `COND_MAP`/`FLAG_SETTERS` comments (~line 347),
  `_lift_jcc`'s block-boundary comment (~line 2277–2283), and `lift_basic_block`'s linear
  `flag_state` threading (~line 3301–3468), confirming the fallback is a known, general design gap, not
  a typo specific to this function.
- `grep -rn "if (_flags" src/recomp/gen/ | wc -l` → 398 total occurrences project-wide.

**Inferred (not directly confirmed against other evidence):**
- The identity/purpose of the icall targets at `0x3B1DD0` (allocator, inferred from "push size only, then
  call"), `0x3B1DD4`/`0x3B1DD8`/`0x3B1DF4` (releasers/deallocators, inferred from "push one pointer, then
  call, with no return value use"), and `0x3B1FD0`/`0x3B1DE4`/`0x3B1DF0` (function-pointer tables /
  further indirect dispatch). I did not trace where these globals are populated.
- That the "type" object at entry `+4` is the same kind of object across all 7 inserts (plausible from the
  create-branch code, not independently verified per-call).
- That REF A/REF C form a temporary/scoped hold specifically bracketing the `sub_00146910` call (this is
  the natural reading of the ordering, but I did not find an explicit comment or symbol name confirming
  intent — it is my interpretation of the arithmetic).

**Could not determine:**
- Whether the found-branch anomaly in §1.4 (`MEM32(esi) = eax` appearing to undo the increment two lines
  above) is a real bug of the same class, or intentional — it never ran in the 7 measured calls, so I have
  no runtime evidence either way and did not chase it further given the scope of this task.
- How many of the other 397 `if (_flags ...)` sites in `src/recomp/gen/` are live bugs versus harmless.
  I only confirmed the one relevant to this milestone.
- The exact original x86 mnemonic/operand sequence Ghidra/the disassembler saw at `loc_001474FF` (e.g.
  whether the original was `cmp eax,ebx` / `jne` as two separate instructions, or something the lifter's
  `try_match_cmp_jcc` fusion should have caught but didn't because of the block split) — I read the
  lifter's flag-tracking logic, not its disassembly-fusion matcher in enough depth to say precisely why
  fusion didn't apply here beyond "it's a block boundary," which is what the lifter's own comments say
  drives the fallback.
