# DirectSound voice-list crash at 0xFFFFFFBE (sub_002626B5)

Read-only analysis; nothing was run or changed. No game code is reproduced: guest addresses,
offsets and constants only. "V" = verified by reading code or the XBE image; "I" = inferred.

## Summary

- The crash is not a null list node. `esi = 0` at the fault means `sub_002626B5` was called
  with `this == NULL`: a DirectSound voice-client pointer fetched from a per-hardware-voice
  table was NULL (V, from register algebra, section 2).
- The call chain is entirely inside the APU interrupt service routine (ISR), not the deferred
  routine (DPC). It is the "front-end trap" branch (ISTS bit 4), not the bit-6 branch (V).
- DirectSound's ISR assumes that a trapped hardware voice always has an owning client. The
  APU model breaks the assumptions that make that true on a console (section 4). Which one
  fired in the crash run cannot be settled by reading; ranked candidates are in section 4.
- Smallest change: a guarded skip of a NULL client in the lifted lookup (safety net), plus a
  model change so a front-end trap latches its method and voice once (the real fix).

## 1. What `sub_002626B5` reads and does

Calling convention: `this` in ecx (a DirectSound voice client), one stack argument
(0 = called from the release path `sub_00262891`, 1 = called from the ISR path).

Guest layout of the client, as used by this function (offsets from `this`):

| Offset | Meaning (inferred from use) |
|---|---|
| +0x08 | pointer to the owning voice manager ("parent") |
| +0x0C | array of 16-bit hardware voice ids, count in the byte at +0x64 |
| +0x4C / +0x50 | software list node: flink, blink |
| +0x65 | list type, 0 = 2D, 1 = 3D, 2 = MP, 0xFF = not on a list |

Parent layout: +0x84 is a "table busy" counter; +0x88..+0x487 is a 256-entry table mapping
hardware voice id to client pointer; +0x488 + type*8 are the software list heads (circular).

APU registers read (V; the table at guest 0x27C3A8 is 12 bytes per list type and was read
straight from the XBE image; it holds register offsets, same order as the model's
`voice_list_regs`):

| Type | Top (TVL) | Current (CVL) | Next (NVL) |
|---|---|---|---|
| 2D | 0x2054 | 0x2058 | 0x205C |
| 3D | 0x2060 | 0x2064 | 0x2068 |
| MP | 0x206C | 0x2070 | 0x2074 |

The function reads TVL, CVL and NVL for the client's type (all `0xFE800000 + offset`), and
also reads and read-modify-writes the 0x80-byte hardware voice records in guest RAM
(`MEM32(0x27CCB0)` is the base, which is the model's VPVADDR). Voice record +0x7C is
`NV_PAVS_VOICE_TAR_PITCH_LINK`: low 16 bits are the next-voice handle.

In plain words it removes a client from the hardware voice list:
1. Find the predecessor client (blink, unless it is the list head) and the successor client
   (flink, same test). Take the predecessor's last voice id and the successor's first.
2. Splice the hardware chain: if there is no predecessor, write TVL with the successor's
   first voice (or 0xFFFF); otherwise rewrite the low 16 bits of the link field of the
   predecessor's last voice.
3. Fix the sound engine's walk cursor: if CVL or NVL currently names one of the removed
   voices, rewrite that register. This is a guest write into registers the frame thread
   also writes.
4. Rewrite the link field of each removed voice (low 16 bits become the voice's own id;
   purpose not determined), unlink the software node (`sub_00256A3A`), mark the client as
   off-list (+0x65 = 0xFF), and finish with a bookkeeping call.
The "next" pointers therefore come from two places: DirectSound's own software list (client
nodes), and voice-record link fields in guest RAM, which both DirectSound and the model write.

## 2. Exactly what was null

Crash registers: `esi` is the saved copy of `this`; `esi = 0`. Everything else follows from
reading low guest memory as zeros (V as algebra, I that the zero page is all zero; three
independent reads agree):
- list type = byte at 0x65 = 0, so `edx = 0x2054` (TVL2D). Matches the crash edx.
- parent = dword at 0x08 = 0, so `ecx = 0 + 0*8 + 0x488 = 0x488`. Matches the crash ecx.
- blink = dword at 0x50 = 0, so `edi = 0 - 76`; byte at 0x18 = 0 (eax = 0); the fault read is
  `0xFFFFFFB4 + 0*2 + 0xA = 0xFFFFFFBE`. Matches.
- `ebx = 0x71` is the ISTS value the ISR had just read: GINT | FETINT | FENINT | FEVINT.

Where the NULL came from: the ISR branch for ISTS bit 4 (`sub_00260322`) calls
`sub_00260205`, which reads FECTL (0x1100) and, only if the trap reason field (0xF00) equals
"requested", reads FEDECMETH (0x1300) and FEDECPARAM (0x1304). `sub_00260184` accepts only
method 0x8000 (`SE2FE_IDLE_VOICE`) and passes the parameter to `sub_0025FB7C` as a hardware
voice id. That function accepts ids below 0x100, requires the parent's +0x84 counter to be 0,
skips voices whose CFG_FMT bit 23 (PERSIST) is set, then loads
`client = parent_table[voice]`. It dereferences the client before calling `sub_002626B5`
(reads the client's voice count and last voice id), and only calls on if the voice id equals
that last id and the client's list node is linked.

With `this == 0`, those reads come from low memory. For the call to happen the id must equal
the 16-bit value at guest 0x0A. If the zero page is zero, the trapped voice id was **0**
(I, moderate: depends on the zero-page assumption). A voice with no table entry that sits on
a list, is not PERSIST and is inactive.

Invariant DirectSound relies on (I, from code structure): a non-persistent inactive voice
that the engine reports always belongs to a client whose table entry is set, unless the
client is mid-update, in which case +0x84 is non-zero and the ISR returns early. The
release routine (`sub_0025F97F`, under a raised IRQL guard) increments +0x84, clears the
client's voice ids and table entries, then decrements it. On the console the ISR can
preempt that routine at any instruction and sees consistent state either way, and it
always runs promptly after the trap.

## 3. How the model produces these values

All in `tools/xboxrecomp/src/apu/` (V):

| Value | Producer | Thread | Lock |
|---|---|---|---|
| TVL2D/3D/MP | guest MMIO write (VEH hook), or `fe_method` VOICE_ON | guest thread that wrote | none; `qatomic_set` on the word |
| CVL/NVL | `mcpx_apu_vp_frame` rewrites them every iteration; guest also writes them (cursor fix-up) | APU frame thread and guest thread | frame thread holds `d->lock`; guest write does not |
| Voice link fields | `fe_method` VOICE_ON (guest thread); `sub_002626B5` (guest) | guest/ISR thread | none; ldl/stl read-modify-write |
| FEDECMETH/FEDECPARAM | `fe_method` writes them on every method | APU thread (idle voices) and any guest thread issuing a PIO write | none |
| FECTL trap bits | `fe_method` SE2FE_IDLE_VOICE case, only if FETFORCE1 bit 15 set (the title sets 0x8000 at init) | APU thread | `d->lock` held by the frame loop |
| ISTS FETINT | `update_irq` ORs it in whenever FECTL has any of mask 0xE0 | APU thread, guest thread on ISTS write | atomics only |
| ISTS FEV/FEN + notifier bytes | `set_notify_status` | APU thread (voice off) and guest thread (VOICE_OFF PIO) | none |
| IRQ line | `s_irq_line`, set in `update_irq` | APU thread / guest | atomic; consumed by timer thread |

PIO writes at +0x20000 are decoded synchronously on the writing guest thread
(`mcpx_apu_vp_write` calls `fe_method` directly); only VOICE_LOCK takes `d->lock`.

The walk (`mcpx_apu_vp_frame`): for each list it sets CVL = TVL, then loops: v = CVL; NVL =
link(v); if v is not ACTIVE (PAR_STATE bit 21) it calls `fe_method(SE2FE_IDLE_VOICE, v)`,
else processes the voice; CVL = NVL. Notes:
- Every inactive voice on every list issues a trap call, in the same frame, and the loop
  does not stop when the first one has set FECTL to trapped. Each call overwrites
  FEDECPARAM, so the ISR sees the last idle voice of the frame, not the first.
- `fe_method` overwrites FEDECMETH/FEDECPARAM for every method, including guest PIO
  writes that arrive while FECTL is already trapped. Hardware halts method decode while
  trapped; here nothing does.
- ISR delivery: `kernel_timer_thread` (vector 5 loop, `kernel_bridge.c` ~2987) calls
  `kernel_raise_interrupt(5)` while `xbox_ApuIrqPending()`. It runs once per ~1 ms wake,
  at TIME_CRITICAL priority, pinned to the one guest core.

## 4. Is there a window?

Verified facts about exclusion (`kernel_hal.c`, `kernel_bridge.c`):
- Guest threads, including the timer thread that runs ISRs and DPCs, share one host CPU
  (`xbox_PinToGuestCore`). The timer thread is TIME_CRITICAL, so a title thread is stopped
  mid-instruction while the ISR runs. That matches console semantics, and the inline check
  of `+0x84` in the ISR is therefore not a time-of-check/time-of-use race on its own.
- The APU frame thread is not pinned ("Host-side threads (the GPU executor, the APU, audio
  output) are left free" in the source comment). It runs truly in parallel with title code
  and with the ISR.
- DPCs exclude title threads at DISPATCH via `g_dispatch_cs`. ISRs are deliberately not
  excluded ("they run above DISPATCH_LEVEL on the console too"). The vector-5 loop does not
  consult `xbox_IrqlBlocksInterrupts()`. This crash is in the ISR, not a DPC, so the DPC
  lock is irrelevant to it.
- DirectSound's own critical regions only raise to DISPATCH (`KfRaiseIrql`, import 160, level
  2, via `sub_00256A8C`; lower is import 161). They never mask the APU interrupt; they rely
  on the +0x84 counter instead (V).

So there is no title-thread-versus-ISR data race to find; the differences from hardware are
between the model's frame thread and the guest, and in latency:

1. **Trap latency (I, most likely).** On the console, a trap raises the APU interrupt in
   microseconds and the ISR preempts the title. Here the title keeps running until the next
   1 ms timer wake and its scheduling slot. In that gap a title thread can release the
   client (clearing its table entry) while the trapped voice id is already latched.
   The ISR then looks up a voice with no client. Hardware cannot get a latched id older than
   the release it races with. Fits "1 run in 3, minutes in", since voice churn in a
   four-fighter match is the trigger.
2. **Latch overwritten (I, plausible).** FEDECPARAM holds the last idle voice of the frame
   and is also clobbered by guest PIO writes during the trap window (section 3). Combined
   with the cursor fix-up writes into CVL/NVL that race the frame thread's own CVL/NVL
   stores, the engine can report a voice that was just retired: its table entry is already
   clear. Voice id 0 fits a stale or default latch value, but this is a guess.
3. **Cursor lost update (I, weaker).** The frame thread overwrites CVL/NVL after the guest's
   fix-up, so it can walk onto a voice the guest just removed. Because removed voices are
   rewritten to point at themselves, such a walk would loop up to 256 times, issuing an idle
   trap per pass for the same retired voice. The model's loop guard then prints
   "Voice list contains invalid entry!" if `DPRINTF` is enabled.

Not shown by reading: whether voice 0 ever sits on a list in this game, and which of the
three actually occurred. Confidence that the trigger is "idle-trap voice with no table
entry": high (~90%). That it is stale/clobbered latch or latency versus a genuinely
unowned voice: unsettled.

## 5. Smallest change

Two layers, in this order of preference:

1. **Safety net, game side (guarded override of `sub_0025FB7C`).** After loading the client
   from the table, if it is NULL, return as the function's other skip paths do (`ret 4`).
   The ISR tail (`sub_00266E32` twice) still runs and is the same tail taken when the
   busy counter is non-zero or the id is out of range, so skipping is architecturally
   legal (V that the skip paths exist; I that the tail resumes the front end). Cost: one
   comparison. Risk: hides a voice that stays on a list forever and traps every frame (an
   interrupt per frame, harmless but noisy). Log the voice id when it fires.
2. **Root-cause fix, APU model (`apu_vp.c`).** Behave like a halted front end:
   - in `fe_method`, do not overwrite FEDECMETH/FEDECPARAM or accept SE2FE_IDLE_VOICE
     again while FECTL is already trapped; keep the first (method, voice) latched;
   - break out of `mcpx_apu_vp_frame` after the first trap, so the cursor registers keep
     the value the guest will inspect;
   - optional: queue guest PIO methods that arrive while trapped instead of decoding them
     immediately (what hardware does).
   This also removes the 256-iteration self-loop walk.

Not recommended: serialising the ISR against title threads in the kernel IRQL layer. The
existing pinning already gives console semantics; adding a lock would not change this
failure and risks the stalls the comments describe (the APU thread starving PIO writers).

## 6. Evidence that would settle it

- In `fe_method`'s SE2FE_IDLE_VOICE case and in the ISR path, log (method, param, FECTL,
  voice-record PAR_STATE) once per trap, and log which thread and tick. A NULL-client hit
  with param 0 means a default/stale latch; a non-zero param whose client was released
  within the last few ms means latency.
- At a crash, dump guest 0x00..0x100 (zero-page assumption), the parent table around the
  trapped id, and the three list heads (`scripts/peek-guest.py`).
- A counter of guest PIO writes accepted while FECTL is trapped, and of idle-trap calls per
  frame beyond the first.
- Release-path trace: timestamp of `sub_0025F97F` for the same voice id against the trap
  timestamp.

## Open items

- Which hardware voice id was trapped (0 is inferred, not observed).
- Whether the title legitimately keeps an unowned voice on a list (an anchor voice).
- Whether `sub_00266E32` is what resumes the front end, and what happens to FECTL if the
  skip path is taken: unchecked.
