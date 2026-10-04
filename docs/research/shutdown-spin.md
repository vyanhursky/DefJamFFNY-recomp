# Shutdown spin — `sub_001F6657` / `sub_001ED3C0` polling loop on a thread handle

Read-only static-analysis pass over `src/recomp/gen/` and (for runtime behavior of the kernel calls
involved) `tools/xboxrecomp/src/kernel/kernel_bridge.c` and `kernel_ob.c`. No code was built or run in this
session; no edits were made. All guest addresses below were read directly out of the lifted C unless marked
INFERRED. The runtime-measured facts in the task prompt (call counts, the handle list, the live stack) are
treated as ground truth and not re-derived.

## Summary of the chain

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`0x285388`/`0x28538C`/`0x285384`/`0x285380`/`0x285390` are resolved, confidence-1.0 entries in
`tools/xboxrecomp/tools/disasm/output/labels.json`:

```
0x00285380  xbox_ObfDereferenceObject
0x00285384  xbox_KeSetBasePriorityThread
0x00285388  xbox_ObReferenceObjectByHandle
0x0028538C  xbox_PsThreadObjectType
0x00285390  xbox_KeQueryBasePriorityThread
```

This is READ, not inferred: `sub_001F6433`, `sub_001F6485` and `sub_001F6657` all push `MEM32(0x28538C)` —
i.e. **`xbox_PsThreadObjectType`** — as the object-type argument to `ObReferenceObjectByHandle`. The handles
being polled (`0x48000002` etc.) are being asked for **as thread objects**, not events. This is a direct,
labeled cross-reference, not a guess.

---

## Q1 — `sub_001F6657`: the loop, the field, the value it waits for

**`sub_001F6657` itself does not loop.** It is a single-shot "reference a thread handle, read one field,
dereference" helper, called from inside a loop in its caller (`sub_001ED3C0`, see below). Full body as read
from `src/recomp/gen/recomp_0013.c:31717-31792`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Answer to the priority question**: the field is a single **byte at object offset `+0x04`**
(`MEM8(ecx + 4)`, `ecx` = the object pointer `ObReferenceObjectByHandle` wrote back). The function needs that
byte to become **non-zero** to take the "signaled" branch. While it stays zero, `sub_001F6657` always writes
the constant **`0x103`** to its caller's out-parameter and returns TRUE (reference itself succeeded — this is
not a reference-failure spin). Only when `MEM8(object+4) != 0` does the code read something else (a DWORD at
`object+0x120`) and hand that back instead.

**This is directly confirmed against the runtime**, not inferred: `tools/xboxrecomp/src/kernel/kernel_bridge.c:3673-3716`
implements `ObReferenceObjectByHandle` as a **stand-in object pool**:

```c
#define XBOX_OBJ_STANDIN_SIZE  0x100
...
uint32_t va = xbox_HeapAlloc(XBOX_OBJ_STANDIN_SIZE, 16);
...
memset(XBOX_TO_NATIVE(va), 0, XBOX_OBJ_STANDIN_SIZE);
```

The stand-in is a 256-byte, all-zero block that is **never written again after allocation** — nothing in the
runtime ever sets any byte of it, including offset `+0x04`. So `MEM8(object+4)` is zero forever, `sub_001F6657`
returns `0x103` on every single call, and the polling loop above it (Q1 continued, below) never sees anything
else. This matches the task's own measurement exactly: making the object non-null didn't stop the spin,
because the loop was never gated on the pointer — it's gated on a byte inside an object that is real (non-null)
but permanently zeroed.

**The actual loop is in `sub_001ED3C0`** (`src/recomp/gen/recomp_0013.c:5868-5943`), the poll-with-timeout
that calls `sub_001F6657` repeatedly:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So the loop condition, put plainly: **keep calling `ObReferenceObjectByHandle`/`ObfDereferenceObject` on the
same handle, forever, as long as `sub_001F6657` keeps reporting status `0x103`** (i.e., as long as
`MEM8(object+4) == 0`), unless a caller-supplied timeout (`edi`, loaded from the function's own second
argument) has expired. `sub_000D1240` (Q4, below) calls this with that argument set to the literal `0` — and
`edi == 0` is exactly the branch that says "ignore the deadline, loop again" — so this particular call site
is an **unconditional, infinite** poll. There is no sleep or yield anywhere in this loop; every iteration is
two full kernel round-trips (reference + dereference), which is exactly the 872M/872M call signature in the
task's histogram.

I could not determine what `0x103` means as a symbolic NTSTATUS/constant from the lifted code alone (it is a
literal in the disassembly, not a named constant); I have not attempted to guess further than "it functions as
a not-yet-signaled/pending sentinel" because that is directly supported by the control flow, not because I
recognize the value.

---

## Q2 — `sub_001F6433` in full: what it does with the object, and the object layout it implies

Full body, `src/recomp/gen/recomp_0013.c:31125-31216`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_001F6433(handle, priority)` is a **`SetThreadPriority`-style wrapper**: reference the handle as a thread
object, clamp the requested priority at the `+15`/`-15` saturation boundary (`0xF -> 0x10`,
`0xFFFFFFF1 -> 0xFFFFFFF0`, otherwise pass through), call `KeSetBasePriorityThread(object, priority)`,
dereference, return TRUE/FALSE. **It does not read or write any field of the object itself** beyond passing
the pointer straight to `KeSetBasePriorityThread` and `ObfDereferenceObject` — no `object+0x04` or
`object+0x120` access here. The only thing this function tells us about the object layout is indirect: it is
the exact same reference/type/dereference skeleton as `sub_001F6657`, on the same `PsThreadObjectType`, so
whatever `sub_001F6657` reads at `+0x04`/`+0x120` is a field of the same kind of object this function sets the
priority of — i.e., **a thread object**, consistent with `xbox_PsThreadObjectType`.

`sub_001F6485` (immediately after, `src/recomp/gen/recomp_0013.c:31224-31309`) is the same skeleton again, but
calls `MEM32(0x285390)` = `xbox_KeQueryBasePriorityThread` instead — the query counterpart of
`sub_001F6433`'s set. Neither touches `object+0x04` or `object+0x120`.

---

## Q3 — Does the access pattern match `DISPATCHER_HEADER` (`Type`@0, `Size`@1, `SignalState` LONG@4, wait-list@8)?

**Partial match, and I'm not extending it past what I actually read.**

- `object+0x04` is read as a **single byte** (`MEM8(ecx+4)`, not a 32-bit `MEM32`) and tested for
  zero/non-zero. This is at the *offset* `DISPATCHER_HEADER.SignalState` would occupy, and "tested as
  zero/non-zero" is exactly how code consumes a dispatcher `SignalState` when it only cares about
  signaled-vs-not (as opposed to a semaphore's count). A compiler narrowing a 32-bit compare to an 8-bit one
  when it can prove the value fits in a byte is a completely ordinary optimization, so a byte test at this
  offset does not contradict a 32-bit `SignalState` field.
- I did **not** find any access in `sub_001F6657`, `sub_001ED3C0`, `sub_001F6433` or `sub_001F6485` to
  `object+0x00` (`Type`) or `object+0x01` (`Size`), so I cannot confirm or deny those two fields from this
  code. I also did not find any access to `object+0x08` (the wait-list head) — this whole call chain never
  queues onto a wait list; it polls a flag instead, so a wait-list field, if present, is simply not touched
  by this path.
- The other field this code reads, `object+0x120` (a `MEM32`, read only once `object+0x04` is non-zero), is
  far outside where `DISPATCHER_HEADER` itself would put anything (that struct is normally ~0x10-0x18 bytes).
  This is consistent with `object+0x120` being a field *elsewhere* in the larger `KTHREAD` (or equivalent)
  structure that embeds the dispatcher header at offset 0 — e.g. an exit-status/return-value slot filled in
  once the thread has terminated — but I did not find any code that writes that field, so I cannot say what
  it actually holds. This is INFERENCE, not a finding.
- Practical note, also INFERENCE: the runtime's stand-in block for this object is only `0x100` (256) bytes
  (`XBOX_OBJ_STANDIN_SIZE` in `kernel_bridge.c`), so offset `0x120` (288) lands **past the end of the
  allocated stand-in**, into whatever the allocator handed out next. This is currently inert only because
  `object+0x04` never goes non-zero, so that read is never reached at runtime — but it would need fixing
  alongside the `+0x04` field if `sub_001F6657` is ever made to see a "signaled" state.

**Verdict**: consistent with a `DISPATCHER_HEADER`-style `SignalState` at `+0x04`, but I could not verify
`Type`/`Size`/wait-list because this code path never touches them. I'm not asserting the full header layout
holds — only the one offset the code actually exercises.

---

## Q4 — `sub_0019AAF0` (destructor) / `sub_000D1240`: what is it waiting for, and is there a missing "signal"?

`sub_000D1240` (`src/recomp/gen/recomp_0006.c:11139-11161`), the function directly above `sub_001ED3C0` on
the live stack:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_001ED3C0`'s own entry (`src/recomp/gen/recomp_0013.c:5888-5894`) reads the handle from 4 bytes into the
struct its first argument points at (`edx = MEM32(ecx + 4)`, where `ecx = this[0x14]`), so the handle actually
referenced lives at **`this + 0x18`**. Combined with Q2/Q3 (the object being referenced is a `PsThreadObjectType`
object), this reads as: **`this + 0x18` holds a worker-thread handle, and `sub_000D1240` waits — with an
infinite timeout (`0` is the "ignore-deadline" branch in `sub_001ED3C0`, see Q1) — for that thread to
terminate**, then runs a cleanup step (`sub_001E9F90(MEM32(this+0x10))`) and clears a running-flag at
`this+0x24`. This shape (wait-for-thread, cleanup, clear-running-flag) is READ from the code; the label
"worker thread" for the handle is INFERENCE, built on: (a) the object type is `PsThreadObjectType`
(labeled, confidence 1.0), (b) the wait has no timeout, and (c) the surrounding shape matches a thread-join
pattern. I did not find, and did not have time to trace, the code that originally created this handle (a
`NtCreateThread`/`ExCreateThread`-style call) to directly confirm it is a worker thread this same subsystem
spawned, so treat that identification as strong-but-unconfirmed.

`sub_001E9F90` (`src/recomp/gen/recomp_0012.c:165288+`) looks like a fixed-size pool/free-list release
(indexes a table at `0x3C9158` off a small id derived from a byte near the freed object), not an explicit
`NtClose` on a handle — I could not confirm it closes the handle at all; it may just release the wrapper
object back to a pool while the underlying handle leaks or is closed elsewhere. This is INFERENCE and
incomplete; I would not build a fix on this detail without checking further.

`sub_0019AAF0` itself (`src/recomp/gen/recomp_0011.c:78704-78784`) does **not** call `sub_000D1240` via any
direct or lifted-visible call — it calls a sequence of vtable methods (`MEM32(x)+0xC`, `+0x1C`, `+0x10`,
`+0x14`, `+0x8`, `+0x8`, conditionally `+0x0`) on two global singleton pointers (`0x3B8088`, `0x3B8084`),
sets a shutdown flag `MEM8(0x3B808C) = 1`, and tail-calls `sub_0019E9D0`. None of these calls are visible as
direct calls to `sub_000D1240` in the lifted C — the task's own live-stack trace is the only evidence linking
`sub_0019AAF0` to `sub_000D1240`, presumably through one of these indirect vtable calls (invisible to grep,
per the project's own conventions on indirect calls). I could not independently confirm *which* vtable slot
resolves to `sub_000D1240` without a live vtable dump, so I'm reporting the destructor's own body as READ and
the link to `sub_000D1240` as given (task-supplied ground truth), not re-derived.

### Is there a missing "signal" call?

**No missing call in the game's own code** — this is the key finding, and it is grounded in the runtime
source, not guesswork. The handles (`0x48000002` etc.) are tokens tagged `0x48000000` and resolved by
`bridge_resolve_handle()` (`kernel_bridge.c:2827-2835`) to **real Win32 `HANDLE`s** in a table
(`s_handle_table`) — the same table `NtWaitForSingleObjectEx` uses (`kernel_bridge.c:1418-1436`,
`bridge_NtWaitForSingleObjectEx`). Those real handles genuinely do get signaled by the OS when the underlying
Win32 thread exits, and the task's own note that the title also calls `NtWaitForSingleObjectEx` on these same
handles is consistent with that path working correctly elsewhere.

But `bridge_ObReferenceObjectByHandle` (`kernel_bridge.c:3718-3754`) does **not** go through
`bridge_resolve_handle` / `s_handle_table` at all — it goes through a completely separate,
parallel table, `xbox_ObjectForHandle()` (`kernel_bridge.c:3695-3716`), keyed by the *same* raw token values
but mapping them to freshly `xbox_HeapAlloc`'d, permanently-zeroed 256-byte stand-in blocks that are never
written again. So `sub_001F6657`'s poll is asking a completely different, inert object whether the thread has
finished, while the real signal (the actual Win32 thread handle becoming signaled) happens on an entirely
separate object this code path never looks at. There is nothing in the game's code to "add" a signal call
to — the bug is that `ObReferenceObjectByHandle`'s stand-in object has no connection to the real handle state
that `NtWaitForSingleObjectEx` already tracks correctly.

The runtime's own comment at `kernel_bridge.c:3674-3688` independently describes this exact situation
("Returning STATUS_SUCCESS and a null object is the worst of both answers... this title does the second, in
a loop, and it spins on it") — written before this session, and consistent with everything read above.

---

## What I could not determine

- The symbolic meaning of the constant `0x103` beyond "not-yet-signaled sentinel" (it is a bare literal in
  the lifted C).
- The full layout of the object beyond offsets `0x00` (untouched by this path), `0x04` (byte, tested), and
  `0x120` (DWORD, read only on the signaled branch) — `Type`/`Size`/wait-list-head could not be confirmed or
  ruled out because this call chain never accesses them.
- What `object+0x120` is meant to hold (thread exit code is a plausible guess given it's only read once
  "signaled," but I found no write to it anywhere in this chain to confirm).
- Whether `sub_001E9F90` closes the underlying Win32-mapped handle, leaks it, or hands it to a pool that
  closes it later — I read enough to see it is pool/free-list-shaped but did not trace it fully.
- Which vtable slot in `sub_0019AAF0` actually dispatches to `sub_000D1240` — the lifted C only shows
  indirect calls through `MEM32(vtable + offset)`, and I did not have a live vtable dump to resolve it. The
  link is taken from the task's own live-stack evidence, not independently re-derived here.
- Whether the handle at `this+0x18` in `sub_000D1240`'s object is definitely the worker thread this same
  subsystem spawned (very likely, given `PsThreadObjectType` and the join-shaped code, but I did not trace
  back to the creating call site).

## What would actually stop the spin (for the fix, not implemented here — read-only task)

Not a code change I made, just the shape the evidence points at: `bridge_ObReferenceObjectByHandle`'s
stand-in objects would need to reflect real state for thread handles specifically — e.g., when the token
resolves to a thread handle already known to `s_handle_table`, set stand-in `+0x04` non-zero (and populate
`+0x120`, once its meaning is confirmed) once `WaitForSingleObject(realHandle, 0)` on the real handle reports
signaled, instead of handing back a block that is zeroed once and never touched again. That would make this
poll path agree with what `NtWaitForSingleObjectEx` already sees correctly on the same handles.
