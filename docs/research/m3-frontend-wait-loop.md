> **Checked at runtime, 2026-09-21 (main agent). Mixed: one correction accepted, two claims not supported.**
>
> *Accepted.* The report is right that `sub_0021EC50+0x227A` is a **host** code offset, not a guest one, and
> that it lands in the D3D push-buffer wait spin that the work log already retired as normal per-frame flow
> control on 2026-09-20. That offset reached the brief as if it were a guest address; it was not, and the
> conclusion drawn from it was worthless. Good catch.
>
> *Not supported: the selector object.* A write watchpoint on `0x800250C0+0x24` (= `0x800250E4`) over a full
> run gives 7 hits, all of them zeroes plus one `0x0D0D0D0D` fill, from `sub_00029DE0+0x1772` and
> `sub_001ECF40+0x7D2` -- allocator and fill paths, next to the critical-section site at `0x001ECF0E`. It is
> never set to 2, and it does not behave like a live state-machine field. The address does not hold.
>
> *Not supported: input being ruled out.* The `PROGRESS.md` line the report cites is an inference from
> 2026-09-20 -- "the ISR claims the interrupt, so input enumeration is not what it is waiting on" -- and a
> passage a few lines later says the opposite is still open: no driver registers, so no descriptors are
> built, and XAPI device enumeration was deliberately left as M4 work. An ISR claiming an interrupt is not
> the title seeing a pad. Input is **not** ruled out as the front end's gate.
>
> *Also measured since.* "The worker-wake event is never signalled" does not survive counting: `NtSetEvent`
> is called 7,708 times in the steady state and `KeSetEvent` 1,825. Events are signalled constantly.


# M3 front-end wait loop — sub_0021EC50, the worker-thread wait, the sub_00118xxx cluster, and input

Read-only static-analysis pass over `src/recomp/gen/`. No code was built or run in this session; all
addresses, offsets and code quotes below come from reading the lifted C and cross-referencing it against
`PROGRESS.md`'s existing work log, which records findings from *earlier* sessions that used runtime tracing
(sample-threads, watchpoints, icall tracing) this pass did not repeat. Where I rely on those prior
runtime-verified entries instead of my own reading, I say so explicitly and cite the `PROGRESS.md` line.

**Headline finding, stated up front because it reframes the whole question**: this project's own work log
already investigated `sub_0021EC50` and concluded it is *not* the blocker. `PROGRESS.md` (2026-09-20 07:45)
reads: *"the front-end task idling on an empty queue is normal at this point ... which corrects yesterday's
reading of that loop as the blocker."* My independent static read agrees with the mechanics that entry
describes (see Q1). If today's hang is really the same condition, `sub_0021EC50` is a red herring — the
one hot thread the sampler sees is just the busiest place in an otherwise-idle frame, not a stuck wait.

---

## Q1 — What is `sub_0021EC50`, and what is the loop at +0x227A waiting on?

### It is not literally 8,826 bytes into this function — important caveat

`sub_0021EC50`'s *original Xbox x86* body is only **362 bytes / 122 instructions** (`0x0021EC50` –
`0x0021EDBA`, confirmed at `src/recomp/gen/recomp_0015.c:37530-37537`, and the next lifted function starts
at `0x0021EDC0`, so there is no larger function hiding here). An offset of `+0x227A` (8,826 decimal) cannot
be a byte offset into *that* 362-byte function. It has to be a **native offset into the compiled lifted C**
(the recompiled x86-64 machine code your sampler actually reads `RIP` from) — the lifter's `MEM32`/`PUSH32`/
`RECOMP_ICALL_SAFE` macros and the C compiler's own codegen inflate 122 original instructions into
considerably more native code, especially around the two `RECOMP_ICALL_SAFE` sites, which each expand into
a lookup through `recomp_lookup_manual()` → `recomp_lookup()` → `recomp_lookup_kernel()`.

This matters because it means "+0x227A" cannot be checked against the *source* line count directly — I
cannot promise you it lands on one specific `goto` versus its neighbor without the actual binary's debug
info, which I did not build. What I *can* say with confidence: **this function has exactly one polling loop
with a backward branch**, so whatever native code +0x227A lands in, it is extremely likely to be this loop,
because everything else in the function is straight-line code with only forward branches.

This identification is also independently corroborated by this project's own earlier runtime trace —
`PROGRESS.md:128-130` (2026-09-17, `scripts/sample-threads.py`) already caught the main thread spinning at
**`sub_0021EC50+0x2192..0x22A6`** — and `0x227A` falls inside that exact range (`0x2192 < 0x227A < 0x22A6`).
So this is the same spin that was already named and diagnosed in this repo, not a new one.

### The loop, read from the source

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`src/recomp/gen/recomp_0015.c:37711-37723`)

`esi` is loaded a few lines earlier from `MEM32(0x234768)` (`recomp_0015.c:37549`), i.e. a fixed guest
global that PROGRESS.md's own log names as `g_pDevice = [0x00234768]` (`PROGRESS.md:130`). This matches
the Xbox D3D "MakeSpace"/push-buffer-reserve pattern exactly: **`device+0x2C` is the Put pointer,
`device+0x30` is a pointer to the GPU's Get counter**, and the loop spins reading `*GetPtr` until the
consumed amount (`Put - *GetPtr`) covers the requested size, i.e. it waits for the GPU to catch up before
the CPU writes more command-buffer bytes.

`PROGRESS.md:130` (2026-09-17 20:25, already runtime-verified, not something I re-derived) names this
function outright: *"`sub_0021EC50` is D3D's MakeSpace: it spins on `(Put - *GetPtr)`... The runtime only
advances the USER DMA_GET register, so the fence never moves."* That entry's fix
(`xbox_Nv2aMirrorFence(0x00234768, 0x2C, 0x30)` in `src/main.c`, iteration 11) was intended to keep
`*GetPtr` moving so this loop resolves quickly every frame instead of spinning forever.

**Condition to proceed**: `(Put - *GetPtr) unsigned>= (requested size)` — i.e. the GPU/mirrored-fence value
at `MEM32(device+0x30)` has to advance to within `requested size` of `Put`. Since the game is still
rendering ~26 fps with real draw calls (per your measured facts), this loop is evidently still resolving
each frame — consistent with the 2026-09-20 07:45 correction that this is normal per-frame flow control,
not a stuck wait. **What I could not verify**: whether the mirrored fence is still being advanced correctly
in *today's* run, since that requires running the game, which I was told not to do. If it were not
advancing at all, draw calls would never complete either — and they are completing (2/frame), so by
elimination the fence is moving. This function is very unlikely to be today's actual blocker; I'd treat it
as confirmed background noise, not new evidence.

---

## Q2 — The worker-thread wait: where it's created, waited on, and what would signal it

I traced one complete, concrete instance of this pattern by following typed call chains (not by literal
address grep, because kernel calls in this image are **all indirect** — the XBE's import thunks are loaded
into fixed low guest addresses at load time and called through function pointers, so no `0xFE000000+`
literal ever appears in `src/recomp/gen/*.c`; see the file scan below). This is one instance among several
— see the caveat at the end of this section.

### The primitive library (`0x001EDDxx` family, `recomp_0013.c`)

Three tiny wrapper functions, back to back in the source, each taking a pointer to a small wrapper object
(`this`) whose `+4` field holds a raw Win32/Xbox handle:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Following `sub_001F6057` → `sub_001F5DDA` (`recomp_0013.c:27109`) shows it loops on the kernel indirect
call `MEM32(0x285354)` with args `(handle, 1 /*alertable*/, timeout_ptr, ...)`, a 3-arg wait — matching
`NtWaitForSingleObject`/`Ex`'s shape (ordinals 233/234 in `tools/xboxrecomp/src/kernel/kernel_bridge.c:8103-8104`,
which the loader would resolve to a synthetic VA in the `0xFE000000+` range you measured).

Following `sub_001F5BCB` (`recomp_0013.c:26635`) shows a 2-arg kernel indirect call at `MEM32(0x285330)`
— `(handle, NULL)` — which is exactly `NtSetEvent`'s signature (ordinal 225, 2 args = 8 bytes,
`kernel_bridge.c:8095`).

The handle itself is created by a third sibling, `sub_001EDD20` (`recomp_0013.c:6638`), which pushes four
zero args into `sub_001F5B0E` (`recomp_0013.c:26459`). That function's own indirect kernel call at
`MEM32(0x285324)` takes `(&handle_out, attributes, manual_reset_selector, initial_state)` — `NtCreateEvent`'s
shape (ordinal 189, 4 args, `kernel_bridge.c:8065`) — called with **`initial_state = 0`**: the event is
created **not signalled**.

### One concrete worker thread built on this primitive

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_000771E0` is the thread body (`recomp_0003.c:58677`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This matches, and gives line-level detail for, the finding already logged at `PROGRESS.md:460-464`
(2026-09-20 17:xx, from a live watchpoint/trace, which I did not re-run): *"a dedicated worker thread ...
`sub_00077230`, the machine's constructor, creates an event at `machine+0xC` and spawns `sub_000771E0`
with a 64 KB stack; that thread waits on the event ... and only then sets `+0x24 = 3`."* My static read adds
the exact primitives and addresses (`sub_001EDD20`/`70`/`40`, kernel slots `0x285324`/`0x285354`/`0x285330`).

### What has to happen to signal it

There is exactly one call site in this whole file that signals *this specific* event
(`sub_001EDD40` on `esi+0xC` where `esi` is the same "machine" object) — inside `sub_00077040`
(`recomp_0000.c:4591`, `recomp_0003.c:58397`), the function I identify in Q3 as the top-level state
machine's per-tick dispatcher:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This only runs when `MEM32(machine+0x24)` (the selector — see Q3) already equals `2` at the top of
`sub_00077040`. **I could not determine, within this pass, what sets that selector to `2` in the first
place** — the only other writer of `+0x24` I found in `sub_00077040` itself sets it to `0` (the
"no new state queued" / idle path, `recomp_0003.c:58468`) or `3` is set by the worker thread itself after
finishing a load (not by this function). Finding the actual trigger that requests dispatch would need
tracing every caller that can reach this object (`0x800250C0`+, per `PROGRESS.md`'s service-locator table)
and set its `+0x24` to `2` — a search I did not complete. **This is the open thread**, and it's the most
promising lead I found for "the asset load job is never dispatched": the wake-up mechanism exists, is wired
correctly end to end, and is *reachable*, but I cannot say from static reading alone whether anything is
currently asking for it.

### Caveat on "one handle, ~10 threads"

The object/thread pair above is one instance of what looks like a reusable "async job" pattern — I found
two more, unrelated, `MEM32(x+0x24) = 2` sites elsewhere in `recomp_0003.c` (`:65571`, `:67611`), but a
quick check of one of them (`:65571`) shows it belongs to a completely different object (a cache/table
init, unrelated fields), i.e. `+0x24` is just a common struct offset reused by many unrelated classes, not
proof of the same dispatcher class repeated. I did not find and confirm nine further instances of *this
exact* Create-event/Wait/Signal triple to account for "~10 worker threads on the same handle" — that would
need either a systematic scan for every `RECOMP_ABI_CALL(0x001EDD20u, ...)` call site (thread-safe primitive
constructors) or a runtime handle-table dump, which is outside what I can do read-only. Treat "the same
Win32 handle" in your measurement as good evidence several of these wrapper objects ended up sharing one
underlying OS handle (plausible if `ke_object_resolve()`/the kernel bridge's shadow-handle table maps
several distinct but identically-shaped guest dispatcher-header objects to one lazily-created native
object) — I can't confirm or deny that mechanism from source alone.

---

## Q3 — The `sub_00118xxx` cluster and the actual state-machine tick

### The `sub_00118xxx` cluster is not a state machine — it's the software vertex emitter

Every function in the list you gave (`sub_001189B0`, `sub_00118070`, `sub_00118320`, `sub_00117EA0`,
`sub_00118120`, `sub_001180B0`, `sub_001186C0`, `sub_00118950`, and their many neighbors in
`recomp_0008.c`, all tagged `Category: game_vtable`) share one recurring shape: read a shared vertex-stream
cursor, write vertex fields through it, advance it by 8 bytes, return.

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_001186C0` (`recomp_0008.c:17746`) is the matching "end" call: it clears a dirty flag at `0x3A61F8`
(`/* TODO: wbinvd */` — cache-flush marker) and tail-calls `sub_00106CE0`, the same function every other
member of the cluster calls to close out its work — consistent with a Begin/EmitVertex×N/End immediate-mode
API for 2D UI quads.

**Key addresses**: `0x3A5978` = vertex write cursor (incremented by 8 every call — every function in this
cluster ends by bumping it); `0x3A597C` = pointer to the active vertex-format/geometry descriptor;
`0x3A5758` = stride multiplier; `0x3A61F8` = a one-byte dirty/lock flag reset by the "end" calls;
`0x3A5980`/`0x3A5984`/`0x3A5988` = derived viewport/scissor-like values written once by `sub_00117EA0`.

I found **no switch statement and no state-selector comparison** anywhere in this cluster. This matches
"the same 2 draw calls per frame": this is the low-level vertex writer the front-end's fixed 2-quad UI
render path calls every frame, not evidence of anything stuck.

### The real state-machine tick is `sub_00077040`, and it *is* a 4-arm switch on one field

While tracing Q2's signal call site I found the actual switch/state-machine the task description was
looking for. It is called **directly** (not indirectly — which is why it never showed up in your icall
histogram; direct calls compile to plain C calls and are invisible to icall sampling, a caveat this
project's own `CLAUDE.md` already notes) once per iteration of `sub_00011CD0`, the function this project's
own `guest-stack.py` trace already named **"the run loop"** (`PROGRESS.md:280`, and confirmed directly here:
`recomp_0000.c:4496`, call site at `recomp_0000.c:4591`).

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`esi+0x24` is exactly the field `PROGRESS.md`'s own service-locator table (from an earlier runtime session,
`PROGRESS.md:774-778`) already calls **"selector"** on the object it names *"top-level state machine"* at
guest `0x800250C0` — which corroborates that `sub_00077040`'s `this` is that object.

Case values I could read:
- **`0`** (`loc_00077059`): asks the *current* state object `current->vtbl[5]()` (`+0x14` byte offset ÷ 4)
  "are you ready to advance?" — if false, does nothing this tick. If true, swaps in the queued "next" state
  (`esi+0x1C`) as current, destroys the old one, and calls the new state's `vtbl[2]()` (`+8`) "Enter" method.
  Leaves the selector at `0` afterward (does not itself request a dispatch).
- **`1`** (`loc_000770B8`): calls `sub_001ED1A0(0)` and returns — a no-op/pass-through tick.
- **`2`** (`loc_000770C3`, quoted in Q2): sets `esi+0x24 = 2` (idempotent re-affirmation), zeroes two globals
  at `0x346A50`/`0x346A54`, and **signals the worker thread's event**.
- **`3`** (`loc_000770EA`): a byte compare I did not fully trace (`MEM8(esi+0x21)` vs a flag) — not read
  in depth; ran out of budget for this pass.

**What I could not determine**: who first sets the selector to `2` to request a dispatch. If nothing does,
that is the actual mechanism of the freeze — everything downstream (event creation, wait, signal wiring)
checks out as intact and correctly wired, but the trigger for case 2 is unaccounted for in what I traced.
This is the strongest concrete lead this pass produced; I'd point the next session directly at "every write
of `MEM32(0x800250C0 + 0x24)`" with a runtime watchpoint, since that's cheap and would settle it immediately
(the tool for it, `RECOMP_WATCH_WRITE`, already exists per `PROGRESS.md`'s own tool table).

---

## Q4 — Is the front end gated on a controller?

**No — already ruled out, and not by inference.** `PROGRESS.md:766` lists this explicitly among things
*"ruled out along the way, each by measurement"*: *"input (`RECOMP_USB=1` presents a device and the routine
claims the interrupt)"*. The more detailed entry (`PROGRESS.md:679-680`, 2026-09-20 07:43) says the same
thing in more words: with `RECOMP_USB=1`, *"the OHCI model reports a device on port 1 and the title's own
interrupt service routine claims the interrupt, so input enumeration is not what it is waiting on either."*

This was tested with a device artificially present (bypassing the real enumeration failure you mentioned)
and the front end still did not advance — which is a direct experiment, not a guess, and it rules out the
"waiting on a gamepad" hypothesis regardless of whether real USB enumeration is fixed. I did not find any
`XInputGetState`/`XGetDeviceEnumerationStatus`-style polled bitmask being tested against zero anywhere in
the functions I read for Q1-Q3, but I also did not do a dedicated search of the whole 17,000-function corpus
for such a check — given the direct experiment above already answers the question, I judged that search not
worth the budget. If you want static confirmation too, the pattern to grep for would be a small function
returning `MEM8`/`MEM32` from a fixed global tested with `TEST_Z`/`TEST_NZ` right before a `Sleep`/retry —
I did not find one in the code paths this pass actually walked (the run loop, the state-machine tick, the
worker thread, the D3D wait).

---

## Summary of what is fact vs. inference in this report

**Read directly from the lifted C in this session** (highest confidence): the `sub_0021EC50` loop body and
its Put/Get comparison; the `sub_00118xxx` cluster's vertex-cursor shape; the full
Create/Wait/Signal primitive chain (`sub_001EDD20/40/70` → `sub_001F5B0E/5BCB/6057/5DDA` → kernel slots
`0x285324/0x285330/0x285354`); the worker-thread constructor and thread body
(`sub_00077230`/`sub_000771E0`); the state-machine tick and its 4-arm switch (`sub_00077040`) and its one
signal-firing case; that it is called directly (not indirectly) from the run loop (`sub_00011CD0`).

**Cited from this project's own prior, runtime-verified `PROGRESS.md` entries** (not re-derived by me, but
directly relevant and more authoritative than static reading alone): the `sub_0021EC50`-loop-is-not-the-
blocker correction (2026-09-20 07:45); the D3D MakeSpace identification and its fix (2026-09-17 20:22-20:25);
the worker-thread/event finding this report adds detail to (2026-09-20 17:xx); the service-locator table
naming `0x800250C0`'s `+0x24` field "selector" (used here to identify `sub_00077040`'s `this`); the
USB/gamepad ruling-out (2026-09-20 07:43); and the separate, already-traced finding that the Flash
notification plumbing is intact and the real gap is further upstream, at the archive read that never
happens (`docs/research/m3-flash-notification.md`).

**Inferred, not verified** (flagged inline above as well): that native offset `+0x227A` lands inside the
`loc_0021ED87` loop rather than somewhere else in the compiled function (very likely given it's the only
backward branch, and independently corroborated by the 2026-09-17 sample-threads range, but not something I
confirmed against the actual compiled binary, which I did not build); that `sub_00077040`'s `this` pointer
resolves at runtime to `0x800250C0` specifically (strongly implied by the field-name match with
`PROGRESS.md`'s table, not confirmed by reading the exact register provenance through `sub_00011CD0`'s
stack shuffling, which I did not fully resolve); and the "one handle, ~10 threads" reconciliation in Q2,
which is speculation about the kernel bridge's handle-shadowing, not something the source shows directly.

**Not determined**: what sets the top-level state machine's selector (`0x800250C0+0x24`) to `2` in order to
trigger the dispatch signal. This is the single most actionable next question and the natural continuation
of this report.
