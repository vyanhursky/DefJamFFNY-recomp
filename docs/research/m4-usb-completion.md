> **Correction, 2026-09-21 (added by the main agent, after measuring).**
> The brief this report was written from was wrong on one point: it said the endpoint descriptor's head
> pointer "is never updated by the model". It is — `ohci_run_control_list` writes it back. The
> software-timeout hypothesis below was built on that mis-statement and does not hold: nothing times out.
> What actually happens is that the driver reads the 8-byte device descriptor, rejects it, and abandons the
> endpoint. See `PROGRESS.md` work log, 2026-09-21. The reverse-engineering in this report is still useful
> as a map of the driver's functions; its conclusion is not.

# USB control-transfer completion: why the driver never reaches SET_ADDRESS

Research date: 2026-09-21. Read-only investigation of `src/recomp/gen/*.c` (lifted C) and
`tools/xboxrecomp/src/usb/ohci.c` (controller model). No code was built or run.

## The question

The title's USB driver enumerates a gamepad over the emulated OHCI controller. The first
control transfer (`GET_DESCRIPTOR`, type DEVICE, 8 bytes) completes cleanly on the wire —
SETUP/IN/OUT all move their full byte counts, condition code 0 — but the driver's completion
DPC, `sub_00284476`, ends up unlinking the endpoint, resetting the root-hub port, and re-issuing
the *same* 8-byte `GET_DESCRIPTOR` forever. `SET_ADDRESS` is never sent.

## What I found

### 1. What `sub_00284476` checks to judge a transfer's success

`sub_00284476` (Original: 0x00284476, `src/recomp/gen/recomp_0017.c`) is the OHCI interrupt
DPC. Per invocation it:

1. Calls `sub_00283E5C` (frame-clock drift compensation between the software frame counter at
   `HCD+0x418` and the HCCA frame number at `HCD+8+0x80`) — unrelated to transfer status.
2. Reads and clears an interrupt-status field at `HCD+0x438` into a local flag byte.
3. If bit 1 (0x02, "WritebackDoneHead") is set, reads `HCCA+0x84` (the HCCA done-head, masking
   off the low 4 bits — the low bit there is HC's own "more interrupts pending" flag) and, if
   nonzero, **reverses the singly-linked done queue** by walking each TD's word-2 (`NextTD`,
   offset `+8`) field, using next-pointers to temporarily hold the reversed chain. This matches
   the note that "the done queue is linked through word 2" — confirmed directly.
4. For each TD in chronological order, it tests byte `TD+2` bit 0 (a bit inside HC TD word 0,
   normally reserved on real hardware — the driver appears to reuse it as a private
   control-vs-isochronous discriminator) to choose between:
   - `sub_00284B12` — isochronous/periodic TD handling (bandwidth accounting), or
   - `sub_00284111` — general (control/bulk/interrupt) TD completion, which is the path our
     control-transfer TDs take.

**`sub_00284111` (Original: 0x00284111) is where success/failure is actually decided.** It
takes the TD pointer in `edx`/`esi` and:

- Tests `MEM8(TD + 3) & 0xF0`. **TD word 0 is 4 bytes at offset 0; byte 3 is bits 24-31 of that
  word, and its top nibble (mask `0xF0`) is bits 28-31 — exactly the Condition Code field.**
  This is the field named in the prompt, confirmed by direct read: byte offset **+3**, mask
  **0xF0**.
  - If nonzero (CC != 0) → jumps to the error path, `sub_0028401D`.
  - If zero (CC == 0, i.e. `NoError`) → falls into the success path: it computes actual bytes
    transferred (from `TD+4` "CBP"-style field and a per-TD "requested length" byte at `TD+0x1D`,
    using 12-bit wraparound arithmetic typical of an OHCI buffer-pointer/CBP delta), adds that
    into a running total at `owner_object + 0x14` (the endpoint/URB object reached via the
    software back-pointer at `TD + 0x18`), and calls `sub_00283F6F` to cancel the software
    timeout entry queued for this TD.
- A field at `TD + 0x1E`, compared against `1`, selects some extra bookkeeping (increments a
  global stats counter at `0x3CD0C2`) — this looks like a stage index (SETUP/DATA/STATUS) and
  is not part of the pass/fail decision.

`sub_0028401D` (the CC != 0 path) additionally special-cases CC `0xF` ("NotAccessed") by writing
a fixed status value `0xC000000F` into `owner_object + 4`, and otherwise synthesizes an NTSTATUS
from the CC nibble (`(CC << 28) | 0xC0000000`). It also updates the endpoint object's shadow
head-pointer field (see below) and, if a listed flag is set, calls `sub_00283F6F`.

**Summary of fields read, with offsets, all verified by direct reading of the lifted C:**

| Field | Offset | Meaning |
|---|---|---|
| TD word 0, byte 3, mask `0xF0` | `TD+3` | Condition Code (bits 31-28) — the pass/fail test |
| TD word 0, byte 2, bit 0 | `TD+2` | Driver-private control-vs-isochronous TD-type flag (reuses a reserved HW bit) |
| TD `NextTD` (word 2) | `TD+8` | Done-queue link, also endpoint TD-chain link |
| TD requested-length byte | `TD+0x1D` | Used with `TD+4` to compute actual bytes transferred |
| TD owner back-pointer | `TD+0x18` | Points to the endpoint/URB software object |
| TD stage/type byte | `TD+0x1E` | Selects extra bookkeeping, not pass/fail |
| Endpoint transferred-bytes accumulator | `owner+0x14` | Incremented on success |
| Endpoint status/NTSTATUS field | `owner+4` | Set on error |
| HCCA done head | `HCCA+0x84` | Read and cleared each DPC, masked `0xFFFFFFF0` |
| Interrupt-status snapshot | `HCD+0x438` | Read then cleared at DPC entry |

### 2. When it would judge a transfer a failure and retry

Directly from `sub_00284111`/`sub_0028401D`: **any nonzero value in TD word-0 bits 31-28 (the CC
nibble at byte offset `TD+3`, mask `0xF0`)** is treated as failure — there is no distinction
between "some non-fatal CC" and "fatal CC" at this layer; every nonzero CC takes the error branch
in `sub_0028401D`, which stores a derived NTSTATUS and (for `CC == 0xF`, NotAccessed) forces the
fixed code `0xC000000F`.

Separately, `sub_002841BD` (a periodic software-timeout scan over a list rooted at `HCD+0x42C`)
walks each endpoint's still-queued TD chain (via the endpoint's shadow head pointer, masked
`0xFFFFFFF0`, and each TD's `NextTD` at `+8`) looking for a TD matching a timed-out request. If
found, it **forcibly ORs `0xF0` into `TD+3`** (i.e., manufactures CC = 0xF, NotAccessed) and then
calls `sub_00284111` on it — meaning the driver can declare a transfer failed purely because its
own software timer expired while the TD was still linked on the endpoint, independent of what the
controller ever wrote into the TD.

I did **not** find, within `sub_00284476`'s call graph, the exact place that reads the accumulated
per-transfer status/byte-count and decides "issue SET_ADDRESS" vs. "reset the port and resend
GET_DESCRIPTOR" — that decision consumer appears to live in a higher-level
enumeration/class-driver routine outside this DPC's call tree (not reached from
`sub_00284476`, `sub_00284111`, `sub_0028401D`, `sub_00284B12`, `sub_002841BD`, `sub_00284315`,
or `sub_0028439C`). This is the main open item (see "Could not determine," below).

### 3. Where the port-reset-and-retry decision is made

**Not located.** I traced every function `sub_00284476` calls (directly and one level further:
`sub_00283E5C`, `sub_00284111`, `sub_0028401D`, `sub_00284B12`, `sub_002841BD`, `sub_00284315`,
`sub_0028439C`, and their callees `sub_00283F6F`, `sub_00283FEB`, `sub_002838B5`, `sub_0027EC5D`,
`sub_002842BF`, `sub_002847A9`). None of them write to the OHCI root-hub port-status register
(`HcRhPortStatus1`, MMIO offset `0x54` off the `0xFED00000` OHCI base per
`tools/xboxrecomp/src/kernel/xbox_memory_layout.c`); a search for writes at that offset across
`recomp_0017.c` also came up empty. The consumer of the completion status (the code issuing
`ClearPortEnable`/`SetPortReset` and re-queuing `GET_DESCRIPTOR`) is therefore in a different
translation unit or a different guest address range than the ones searched — most likely a
higher-level "device enumeration" state machine that reads the endpoint's status field
(`owner+4`, set by `sub_0028401D`) or its transferred-byte accumulator (`owner+0x14`, set by
`sub_00284111`) as its selector, since those are the two fields the traced code actually
populates as outputs. This is inference, not a verified call-graph finding — I did not locate the
state variable or its consumer.

### 4. Does anything the driver checks correspond to a field the model might not fill in?

Two of the four candidates are, per the prompt's already-established facts, filled in correctly
by the model (CC in word 0, and the done-queue link via word 2/`HcDoneHead`/HCCA+0x84), and I
independently confirmed by reading the code that the driver's pass/fail test is exactly the CC
nibble at `TD+3 & 0xF0`, and that its done-queue walk uses `TD+8` — so those two fields being
correct in the model does line up with what the driver reads there.

The interesting mismatch is the **endpoint descriptor's head pointer** (already noted as
established: "keeps its toggle-carry bit but is never updated by the model"). Reading the driver
confirms this field is *load-bearing*, not incidental:

- `sub_002841BD`, at `loc_0028421A`, reads an endpoint object's shadow head-pointer field
  (`ED_obj + 8`), masks off the low 4 bits (`& 0xFFFFFFF0u`) to get a TD pointer, and walks that
  TD's own `+8` (`NextTD`) chain specifically to find whether a given TD is *still linked* on the
  endpoint. It later writes back `ED_obj + 8` with the low 4 bits (Halt/ToggleCarry) preserved
  and the upper bits replaced — i.e., the driver expects to be able to advance this field itself
  in its abort/timeout path, the same operation real OHCI hardware performs on every normal TD
  retirement (spec section 5.2: HC writes `ED.HeadP = TD.NextTD`, preserving bits 0-1, whenever a
  TD is retired to the done queue).
- On real hardware, once a TD is fully processed and placed on the done queue, `ED.HeadP` is
  simultaneously advanced past it. The prompt states the model never does this (only preserves
  the toggle-carry bit). That means after our GET_DESCRIPTOR TD completes with CC=0, the endpoint
  object's head pointer **still points at the just-retired TD**, exactly the condition
  `sub_002841BD` treats as "this TD is still outstanding on the endpoint."

I could not, within the traced call graph, find the exact spot that turns "head pointer still
points at a TD I already completed" into "issue a port reset instead of SET_ADDRESS" — but
`sub_002841BD` demonstrates the driver actively uses a stale/un-advanced head pointer as a signal
that a transfer is *not actually done*, and will synthesize a CC=0xF failure and re-invoke the
same completion path (`sub_00284111`) on a TD that already completed successfully once, if it
still looks "linked" the next time the timeout scan runs. This is a plausible, but **not fully
verified**, mechanism for the observed symptom: the transfer succeeds on the wire, but because the
model leaves `ED.HeadP` pointing at the retired TD, the driver's periodic servicing re-examines
that same TD, treats it as unresolved/timed out, forces an error condition code onto it, and only
then does the higher-level (unlocated) enumeration logic decide to reset the port and resend the
request rather than advance to `SET_ADDRESS`.

## What I could not determine

- The exact function(s) that issue `ClearPortEnable` / `SetPortReset` to `HcRhPortStatus1`
  (MMIO `0xFED00054`) and that re-queue the `GET_DESCRIPTOR` SETUP packet — not found in
  `sub_00284476`'s call graph or by direct search of `recomp_0017.c` for writes to that offset.
  It is very likely in a different `recomp_00xx.c` file (a higher-level class/enumeration driver)
  that I did not exhaustively search.
- The specific state variable that selects "reset and retry" vs. "advance to SET_ADDRESS" and
  where it is set — not located. My best guess, unverified, is that it is downstream of the
  endpoint status field at `owner+4` (written by `sub_0028401D` on error) and/or the transferred-
  byte accumulator at `owner+0x14` (written by `sub_00284111` on success), since those are the
  only two outward-facing outputs the traced completion code produces.
- Whether the stale `ED.HeadP` is actually what trips the retry (my leading hypothesis) or
  whether the real trigger is something else entirely (e.g. a stage-count/toggle mismatch I
  didn't trace to its consumer). I verified the mechanism exists and is used by
  `sub_002841BD`, but did not verify that it is *this* mechanism that fires for the observed
  case.

## Recommended next step

Most concrete, testable fix: **have the OHCI model advance the endpoint descriptor's `HeadP`
field when it retires a TD**, the same way real hardware does — `ED.HeadP = TD.NextTD`, with the
low 2 bits (Halted, ToggleCarry) preserved from the current `ED.HeadP` rather than the TD. This
is a single documented OHCI behavior (spec 5.2.8) that the established facts already flag as
missing, and the driver code in `sub_002841BD` demonstrates the driver actively inspects
`ED.HeadP` to decide whether a TD is still "in flight." If this fix is applied, the next
concrete verification step is to set a breakpoint (or log) at `sub_0028401D`'s entry and at the
`0xF0`-force in `sub_002841BD` (`loc_00284250`) to confirm whether the observed GET_DESCRIPTOR TD
is currently being re-processed through the timeout/abort path — that would confirm or rule out
the hypothesis directly, before spending more time hunting for the actual port-reset call site.
