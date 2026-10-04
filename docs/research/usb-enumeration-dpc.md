# USB enumeration DPC: does `sub_002239A0` examine the device descriptor?

Research date: 2026-09-21. Read-only investigation of `src/recomp/gen/recomp_0015.c` and
`src/recomp/gen/recomp_0017.c` (lifted C). No code was built or run. This report answers the
three questions in the brief and is a direct follow-up to the existing
`docs/research/m4-usb-completion.md` (same subsystem, different entry point); I cross-reference
it below rather than repeating its findings.

## Headline finding: `sub_002239A0` does not look like USB code

I read `sub_002239A0` in full (`src/recomp/gen/recomp_0015.c:49038`) and its four direct callees
(`sub_00223760`, `sub_002232E0`, `sub_002231D0`, `sub_00223810`, all in the same file, address
range `0x223xxx`). None of them touch a USB descriptor, a SETUP packet, an OHCI register, or
anything resembling a device object. Concretely:

- `sub_002239A0` takes one pointer parameter (`ebx`, "the device object"), dereferences it once to
  get `edi`, then reads a bitmask at `edi+0x100` and does a chain of `test`s against `0x1000`,
  `0xFFFFEFFF` (i.e. "not 0x1000"), `0x100000`, `0x1000000`, `0x100`, `0x10000` — calling one of
  `sub_00223760` / `sub_002232E0` / `sub_002231D0` / `sub_00223810` per set bit, then looping
  (`goto loc_002239B0`) until nothing is left set. This is a generic "drain the dirty-flags word"
  pump, not a protocol handler.
- `sub_00223760` reads/writes fields at `esi+0x400100`, `esi+0x400104`, `esi+0x400700`,
  `esi+0x400704`, `esi+0x400708`, `esi+0x400720` — the `0x400xxx` range is the NV2A
  (GeForce-derived) graphics core's MMIO block on the original Xbox. This function is GPU
  register plumbing.
- `sub_002231D0` reads I/O port `0x80C0` (`xbox_IoRead8`) and touches fields at
  offsets `0x1B4`/`0x1C0`/`0x1C4`/`0x1D0`/`0x1D4`/`0x1D8`/`0x190`/`0x194` on the same object,
  ending in two indirect calls (`MEM32(0x28527C)` and a computed target). No descriptor bytes.
- `sub_002232E0` and `sub_00223810` manage a small array-based free-list (`esi+0x820..0x84C`,
  indices via `edi*8`) — looks like a generic interval/allocator structure, again nothing
  USB-shaped.

**I could not find any comparison against 8, 0x20 (32), 0x40 (64), or a power-of-two test
anywhere in this function or its call graph.** Grepping `recomp_0015.c` around these functions
for `MEM8(x + 7)` (byte 7 of an 8-byte buffer, i.e. `bMaxPacketSize0`) turns up nothing in this
address range either.

**This is worth flagging plainly, not quietly working around:** the measured fact "the DPC
deferred routine is guest address `0x002239A0`" and the decompiled behaviour of `0x002239A0` do
not match each other. I have no way to resolve this discrepancy from static reading alone — I can
only report it. Two possibilities, in order of how easy they are to check:
1. The runtime trace caught a **different**, coincidentally-scheduled DPC (e.g. a GPU vblank/flip
   DPC that legitimately fires on its own schedule) rather than the one the OHCI ISR actually
   queued, if the log/breakpoint was reading the `KDPC.DeferredRoutine` field at the wrong time or
   from the wrong object.
2. `0x002239A0` really is queued by the ISR (e.g. as a secondary "kick the GPU/whatever" DPC the
   same ISR always queues alongside the real completion DPC), and the *actual* USB completion
   routine is a separate DPC queued in the same interrupt that wasn't captured.

Either way, the function that actually matches the OHCI behaviour described in the prompt
(WritebackDoneHead handling, done-queue walk via TD word 2) is **not** `0x002239A0` — it is
`sub_00284476`, which `docs/research/m4-usb-completion.md` already identified and I independently
re-confirmed by reading it again (see next section). I'd suggest re-checking the runtime capture
against `0x00284476` specifically.

## What actually is the OHCI completion path (confirming/extending the prior report)

`sub_00284476` (`recomp_0017.c:32655`, original `0x00284476`) reads and clears an
interrupt-status byte at `HCD+0x438`, and when bit `0x02` (WritebackDoneHead) is set, walks the
done queue (TD word 2, offset `+8`) exactly as `m4-usb-completion.md` describes. For each retired
TD it picks `sub_00284111` (control/bulk/interrupt) or `sub_00284B12` (isochronous) based on
`TD+2` bit 0.

I read `sub_00284111` (`recomp_0017.c:32026`) in full, which the prior report didn't quote
completely:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This is purely byte-accounting: it never reads or compares the *contents* of the transferred
data, only the transferred *length*. All three TDs in the described transfer (SETUP/IN/OUT,
CC=0 each) go through this exact path, feeding `owner->bytesTransferred` (`owner+0x14`) — the
device-descriptor bytes themselves are never inspected here.

`TD+0x14` (the value saved to `ebp-8` before the accumulation, and passed as `edx` into
`sub_00283FEB`) is used identically in the CC-error path, `sub_0028401D` (`recomp_0017.c:31851`),
which passes `edx = edi = MEM32(<TD>+0x14)` to the same `sub_00283FEB`. So `TD+0x14` is a pointer
to some per-request/per-device state object that both the success and the failure path converge
on before returning.

## Answering the three questions

### 1. Does the DPC (or its callees) examine the returned descriptor bytes, specifically byte 7 (`bMaxPacketSize0`)?

**Not found**, in either code path I traced:

- `sub_002239A0`'s call graph (the address given as ground truth) — confirmed unrelated to USB,
  see above.
- `sub_00284476`'s call graph (the code that actually matches the described OHCI behaviour) —
  `sub_00284111`/`sub_0028401D` only account transferred *length*, never inspect *content*. The
  three "checker" functions `sub_00284476` also calls (`sub_002841BD`, `sub_0028439C`,
  `sub_00284315`) are all generic completed-request-queue drainers rooted at `HCD+0x42C`,
  `HCD+0x430`, `HCD+0x434` respectively (three separate pipe/queue-type lists); none of them read
  descriptor payload bytes either — they manipulate queue-linkage fields (`+0x24`/`+0x14`), a
  "busy" bit (`x+0x10` bit `0x40`), and (in `sub_0028439C`) what looks like an isochronous
  bandwidth-bitmap update, not descriptor content.

The one place I found *any* code reading byte offset 7 of an 8-byte-ish buffer and feeding it
into a subsequent request is `sub_002831B5`/`sub_00283220` (`recomp_0017.c:29528`/`29592`,
`Category: game_input`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

and, in `sub_00283220`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**I could not confirm this is the check the prompt is asking about**, and I lean against it: the
`bmRequestType`/`bRequest`-shaped bytes here are `0x28/0x41`, `0x30/0x40/0xA0`, `0x30/0x40/0xA3` —
none of which is `0x80/0x06` (`GET_DESCRIPTOR`, device-to-host/standard/device) or `0x00/0x05`
(`SET_ADDRESS`). These look like the Xbox controller's proprietary vendor-class request codes
(used for the post-enumeration "get capabilities"/state exchange), not the standard descriptor
read the prompt is about. I'm flagging it as the nearest lead I found, not as an answer — it
needs a caller-chain trace back from a confirmed enumeration entry point to be trusted, which I
did not do (see "Could not determine").

**No comparison against 8, 0x20, 32, or 64 was found anywhere in the code I read.**

### 2. The enumeration state variable and where SET_ADDRESS would be issued

**Partially found; not conclusive.** `sub_00283FEB` (`recomp_0017.c:31791`) is a 4-way dispatcher
keyed on a single byte, reached as `edx` from both the success and failure completion paths
above (i.e. `MEM8(edx + 0x11)`, where `edx` = the pointer stashed at `TD+0x14`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00285078`, `sub_0028502B`, and `sub_00284FD8` are structurally identical: each pops the next
entry off a per-pipe queue head (`[device+0x41C]`, `[device+0x424]`, and a queue passed in `ecx`
respectively), and re-submits it by calling `sub_00284CDA` (the TD builder named in the prompt).
So state values 0/2/3 each "kick the next queued transfer for a specific pipe"; state 1 (and
anything above 3) is a no-op.

**This is a plausible fragment of an enumeration state machine, but I would not call it "the"
state variable with confidence** — it only has 4 branches, three of which do the same generic
thing (pump a queue), which is thin for a full enumeration sequencer (reset → SET_ADDRESS →
GET_DESCRIPTOR(full) → GET_CONFIGURATION → SET_CONFIGURATION typically needs more states than
that). It may instead be a narrower "pipe scheduling policy" flag, e.g. bulk/isoc pipe endpoint
management, and not the same variable as. Please note the ground-truth fact from
`m4-usb-completion.md`'s correction that a state-based rejection *has* been measured — this
`[device+0x11]` byte deserves a runtime check (log it) but I could not verify it is the same
object being referenced there.

**I could not locate SET_ADDRESS construction.** I grepped `src/recomp/gen/*.c` for the immediate
`0x0500` (the little-endian 16-bit word `bmRequestType=0x00, bRequest=0x05`) and for `MEM8(x) = 5`
assignments; both patterns hit hundreds of unrelated locations across the 1.5M-line lifted
codebase (this is a full game binary, not just the USB driver), and without a confirmed call-graph
anchor from a "device now has an address, proceed to configure" entry point I could not narrow
this down further inside the time available. This matches the prior report's identical
conclusion ("not located... most likely in a different translation unit"). **Not determined.**

### 3. What makes `sub_002239A0`/its callees abandon the device instead of retrying

Reframed against `sub_00284476` (the function that actually matches the OHCI behaviour, since
`0x002239A0` itself has no plausible abandon logic — see the headline finding): the clearest
"abandon-shaped" trigger I found is this, at the tail of `sub_00284476`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So: whenever bit `0x40` of the interrupt-status byte read from `HCD+0x438` at the top of the DPC
is set, `sub_00284476` unconditionally calls `sub_002837F6` — the exact function the prompt
identifies as "port-reset-related" — and stamps `0x40` as a status/reason code onto the current
request object (`ebx+0xC`). This is the single clearest "do something port-related, unretried"
trigger in the code I read: **the comparison is a bitmask test of bit `0x40` in the per-DPC
interrupt-status snapshot, not a retry counter or a descriptor-content check.**

However, I read `sub_002837F6` in full (`recomp_0017.c:30415`) and it does **not** itself write
`HcControlHeadED` or unlink an ED in visible code. It walks a small table indexed off
`[object+0x460]` (a count) and `[object+0x54+i*4]` (the array), testing two bits (`0x10` and
`0x1`) on each entry's flags byte, and — when set — makes **indirect calls** through
`MEM32(0x285440)`, `MEM32(0x285454)`, and a per-entry function pointer at `[esi+0x478]`/`[esi+0x474]`
(a small COM/vtable-style interface, filled in elsewhere and not visible statically). `sub_00283761`
(the *first* port reset, named in the prompt) calls through the same `MEM32(0x285454)` slot.

**I believe these `0x2852xx`–`0x2854xx` cells are Xbox kernel import-table (IAT) thunks** — fixed
data cells the loader fills with the address of an `xboxkrnl.exe` export, the standard way every
Xbox driver invokes kernel/HAL services — rather than anything USB-specific. That would also
explain why the (unrelated, GPU-flavoured) `sub_002231D0` calls through the neighbouring cell
`MEM32(0x28527C)`: it's simply a different kernel export, not evidence of a real
GPU/USB relationship. This is **inference, not verified** — I did not cross-reference these
addresses against a known `xboxkrnl.exe` ordinal table.

**Bottom line for Q3: the actual `HcControlHeadED` write, and whatever comparison decides
"abandon, don't retry," happens inside one of these indirect-call targets, which the static
lifter cannot show.** This is the same category of gap the project's own `CLAUDE.md` describes
("indirect calls... invisible" to static lifting) and the same one `m4-usb-completion.md` hit
when it couldn't find the `HcRhPortStatus1` write anywhere in `recomp_0017.c`. My addition here is
narrowing the search from "somewhere in this file" to "behind these three specific
call sites" (`MEM32(0x285440)`, `MEM32(0x285454)`, and the per-object vtable at
`[object+0x474]/[object+0x478]`), which `scripts/icall-window.py` (already in the toolkit, per
`CLAUDE.md` §4) should be able to resolve at runtime.

## What I could not determine (explicit)

- Whether `0x002239A0` is genuinely the DPC the OHCI ISR queues, or whether the runtime capture
  caught a different, coincidental DPC. I can only report the mismatch between the measured
  address and its decompiled (GPU-flavoured) behaviour.
- Any code that reads USB descriptor *content* bytes (specifically offset 7,
  `bMaxPacketSize0`) and compares it to 8, 0x20 (32), 0x40 (64), or does a power-of-two test.
  Not found anywhere I looked.
- The concrete SET_ADDRESS construction site (`bRequest = 5` / `wIndex/wValue` word `0x0500`).
  Grep sweeps for both patterns were too noisy against the full 1.5M-line lifted game to isolate
  without a verified call-graph anchor.
- Whether `MEM8([TD+0x14]+0x11)` (the 4-valued dispatch key in `sub_00283FEB`) is actually "the"
  enumeration-stage variable, or a narrower per-pipe scheduling flag. I only verified it is
  consumed identically from both the CC=0 and CC≠0 completion paths.
- What runs behind `MEM32(0x285440)`, `MEM32(0x285454)`, `MEM32(0x28527C)`, `MEM32(0x28549C)`,
  and the per-object vtable calls at `[object+0x474]/[object+0x478]` — these are exactly where I
  would expect the `HcControlHeadED` write and the abandon-vs-retry decision to live, but they are
  indirect calls the static lifter cannot resolve.

## Suggested concrete next step

Given `sub_00284476` (not `0x002239A0`) is the function whose static behaviour actually matches
every measured fact in the brief (WritebackDoneHead bit test, done-queue walk via TD word 2,
port-reset call gated on a status bit), I'd re-run the runtime capture with a breakpoint/log at
`0x00284476`'s entry instead of (or in addition to) `0x002239A0`, and log `MEM8(HCD+0x438)`
(pre-clear) on entry to see whether bit `0x40` is the one that's set for this failing transfer.
Separately, `scripts/icall-window.py` at the moment `sub_002837F6` runs should reveal the real
guest addresses behind `MEM32(0x285440)` and `MEM32(0x285454)`, which is very likely where the
actual `HcControlHeadED` unlink write happens.
