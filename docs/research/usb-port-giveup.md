# USB port give-up: why the driver ClearPortEnable's port 1 after a clean GET_DESCRIPTOR

Investigation of `src/recomp/gen/recomp_0017.c` (lifted C, gitignored, present on disk).
All addresses below are **guest (original Xbox) virtual addresses** — the `sub_XXXXXXXX` naming
convention. Line numbers refer to `src/recomp/gen/recomp_0017.c` as it exists on disk today.

Read-only investigation. No code was edited, built, or run.

## 0. TL;DR of the mechanism (see Section 6 for the parts I could not close out)

`sub_002837AE` (the function that issues the `ClearPortEnable` write) is itself an
**unconditional, branchless 11-instruction leaf**. It has exactly one direct caller,
`sub_00281468`, and that caller is the actual decision point. `sub_00281468` — and at least
five other entry points in this same state machine — all open with the identical guard:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So the real question becomes "what sets/clears the byte at guest address `0x3CC8B1`, and what
does the slot-state check test". I traced both (Sections 1–3). I could **not** find a bounded
numeric retry counter anywhere in this call graph that would explain "exactly six attempts, then
stop forever" — see Section 6 for what I ruled out and what remains open.

---

## 1. `sub_002837AE` — the give-up write, read in full

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`src/recomp/gen/recomp_0017.c:30346-30367`)

**There is no branch in this function.** It unconditionally writes the 32-bit value `1` to
`*(arg0) + arg1*4 + 0x50`. Whatever decides to call it has already decided to give up; the
function itself carries no condition of its own.

I confirmed the register semantics against the sibling function `sub_00283761`, which the
brief already told me issues `SetPortReset` (measured fact) and which writes to the exact same
address formula:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`src/recomp/gen/recomp_0017.c:30300-30321`)

Both functions write into `hwbase + port_index*4 + 0x50`, where `hwbase = *(object+0xC+0x18)`
(see Section 2). `sub_00283761` writes `0x10` (OHCI `SetPortReset`, bit 4), `sub_002837AE`
writes `1` (OHCI `ClearPortEnable`/`CurrentConnectStatus`, bit 0). This is consistent with the
`HcRhPortStatus`-style write-to-clear/write-to-set register semantics your runtime trace already
identified. I read this directly; the *bit-meaning-matches-OHCI* interpretation is inference, but
a well-supported one given `sub_00283761` is already proven (by your runtime measurement) to be
the `SetPortReset` call site and shares the identical addressing formula.

**Conclusion for Q1:** the write itself is unconditional. The "condition that leads to
`ClearPortEnable`" lives entirely in the caller, `sub_00281468` — see Section 3.

---

## 2. Callers of `sub_002837AE`

Only **one** static call site exists in the whole lifted codebase, at line 24680 inside
`sub_00281468`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`src/recomp/gen/recomp_0017.c:24648-24689`)

**So `sub_00281468`'s own gate to reach `ClearPortEnable` is:**
*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
where `slot_table` is a 32-byte-stride table at guest address `0x3CC990`, looked up by
`sub_0027FC4D`:
*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`src/recomp/gen/recomp_0017.c:19867-19890`)

If no slot is assigned (or the assigned slot's status byte is still 0), `sub_00281468` gives up.

**`sub_00281468` itself is reached from at least 5 direct call sites** (found by grepping the
whole `recomp_0017.c` for `RECOMP_ABI_CALL(0x00281468u`):

| Call site (line) | Enclosing function | Context |
|---|---|---|
| `recomp_0017.c:23610` | `sub_00280FDA` | (not read in depth) |
| `recomp_0017.c:23932` | `sub_00281107` | 100ms retry-timer expiry handler (Section 4) |
| `recomp_0017.c:24919` | `sub_0028153A` | transfer-completion state dispatcher (state==5, first-success branch) |
| `recomp_0017.c:25414` | `sub_0028191C` | completion handler, same `MEM8(0x3CC8B1)!=0` guard |
| `recomp_0017.c:25612` | `sub_00281AD5` | completion handler, same `MEM8(0x3CC8B1)!=0` guard |

In addition, `sub_00281468`'s guest address `0x281468` is stored as a **raw function-pointer
value** into a shared "deferred work item" object at two places:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

That work item (fields at `0x3CC8B4..0x3CC8C4`: type byte `0x1C`, subtype `0x43`, function
pointer at `+8`, context at `+0x10`) is handed to `sub_002828CB`, which — based on the pattern
used throughout this file — queues it for a **later indirect call** rather than calling it
inline. I did not chase `sub_002828CB` down to the actual `RECOMP_ICALL`/kernel-APC dispatch
that fires the stored pointer (out of budget — see Section 6), but this is almost certainly why
a previous constant-sweep of `sub_00284476`'s direct call graph found nothing: **`sub_00281468`
is reached through a stored function pointer resolved by an indirect call somewhere inside
`sub_002828CB`'s machinery, not through a direct call edge from the ISR's DPC.** This matches
the brief's own hint that the rejection test is "more likely in the XID/XAPI device layer".

**Conclusion for Q2:** `sub_00281468` takes 2 cdecl args — `(status_or_zero, device_object)`
— and is both directly called (5 sites above) and indirectly dispatched via a function pointer
stashed at guest address `0x3CC8BC` by `sub_002814D5` and `sub_0028153A`.

---

## 3. The common guard: `MEM8(0x3CC8B1)`

Every completion/retry entry point I read in this subsystem opens with the same test before
deciding whether to continue enumeration or give up:

- `sub_00281468` — `recomp_0017.c:24656-24660`
- `sub_00281107` (timer-expiry handler) — `recomp_0017.c:23925-23927`
- `sub_0028191C` — `recomp_0017.c:25406-25409`
- `sub_00281AD5` — `recomp_0017.c:25600-25605`
- `sub_00281236` (retry re-arm) — `recomp_0017.c:24207-24209`
- `sub_002814D5` (top-level completion callback, effectively `if (status<0) target=give_up; else if (flag) target=give_up; else target=continue`) — `recomp_0017.c:24738-24749`

`0x3CC8B1` is **cleared to 0** (armed / not-given-up) in exactly one place I found, inside
`sub_00280EE8` when a fresh retry timer is set up:
*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0017.c:23533-23550`)

It is **set to 1** in exactly one place I found, inside `sub_002812E5` (a "cancel the pending/
active retry request" routine), guarded by:
*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0017.c:24358-24370`, reached only when `MEM8(0x3CC8B0) != 0`, i.e. a retry is
currently outstanding)

**Conclusion:** `0x3CC8B1` behaves as a **sticky one-shot "abort" latch**, not a counter. It is
armed (cleared) each time a fresh retry request is queued in `sub_00280EE8`, and it is set when
`sub_002812E5` is asked to cancel the request that is currently outstanding (`0x3CC930` still
points at it). Every completion/timeout handler checks it first and routes to `sub_00281468`
(hence `ClearPortEnable`) if it is set.

---

## 4. The retry loop itself is time-based, not (as far as I could find) count-based

`sub_00280EE8` / `sub_00281107` / `sub_00281236` implement a **100 ms one-shot kernel timer**
retry loop, not a counter loop:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0017.c:23499-23509`)

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
(`recomp_0017.c:23571-23580`, and again in `sub_0028191C` with `MEM32(...) = 0xFFF0BDC0u`,
which as a signed 100ns relative deadline is exactly **-100ms**, i.e. "fire again in 100ms")

`sub_00281107` is the timer-expiry callback: if the give-up latch is clear, it re-checks the
slot table and, if still invalid, re-issues `SetPortReset` via `sub_00283761` (matching your
runtime observation that `SetPortReset` gets reissued from `sub_00283761`) or, if the slot is
now valid, proceeds down the success path via `sub_00282D57`.

I could not find any integer field that increments on each of these 100ms cycles and is
compared against a limit of 5 or 6. See Section 6.

---

## 5. Q4 — where the 8-byte descriptor is judged (partial answer, low confidence)

I was not able to close this out with the same confidence as Sections 1–4. What I did find:

- `sub_0028153A` (`recomp_0017.c:24776-25025`, "Original: 0x0028153A-0x002816C6") is a
  1-argument (`status`) state dispatcher keyed on a state byte `MEM8(esi)` where `esi` is the
  device object. It is called from **11 different sites** across the file (`recomp_0017.c` lines
  16025, 18611, 18631, 18724, 18744, 19353, 19471, 19491, 25076, 28756, 29909), which tells me it
  is a generic "advance the state machine after a transfer completes" entry point used by many
  different transfer types in this driver, not something specific to the GET_DESCRIPTOR(DEVICE)
  transfer alone. I did not trace all 11 callers to determine which one(s) are reached from the
  control-transfer completion path your runtime trace identified (`sub_00284CDA`'s TDs → ISR →
  `sub_00284476` → ... ).
- `sub_002814D5` (`recomp_0017.c:24722-24767`) is the higher-level completion callback: it reads
  `MEM32(arg0 + 4)` as a signed status and, together with the `0x3CC8B1` latch, decides whether
  the queued follow-up action is "continue" (`0x28102B`) or "give up" (`sub_00281468`,
  `0x281468`). This is a strong **candidate** for "the consumer that judges the transfer", but I
  could not confirm that `arg0+4` (the status field) is itself derived from inspecting descriptor
  *bytes* (e.g. `bMaxPacketSize0` at offset 7) as opposed to purely the TD condition-code chain
  that the brief already says is proven-good (all CC=0). If the give-up is driven purely by
  `MEM32(arg0+4) < 0` and that field is only ever a USBD-style completion status (not a
  descriptor-content judgement), then **the descriptor content itself may not be judged at all**
  on this path — the give-up would instead come from the slot-table check in Section 1-2 (i.e.
  from `sub_0027FC4D`'s lookup returning a still-zero status byte, meaning "no class driver has
  claimed/validated this slot yet" rather than "the descriptor bytes were rejected").
- `sub_00282D57` (`recomp_0017.c:28772-28877`) is called on the *success* path (both from
  `sub_00281468`'s `loc_002814AA` and from `sub_00281107`'s success branch) and builds a request
  block at `0x3CC9C8..0x3CC9F8` with `MEM8(0x3CC9F0) = 0x23`. `0x23` as a USB `bmRequestType`
  would mean Host-to-Device / Class / Interface, which does **not** match plain `SET_ADDRESS`
  (`bmRequestType 0x00, bRequest 5`) or `GET_DESCRIPTOR` (`0x80, 6`). I could not confirm this
  is an XID-specific request or identify its `bRequest` byte with confidence — I did not trace
  which field in the block corresponds to `bRequest`. **I did not find any function in this
  call graph that reads `MEM8(buf+7)` of the returned descriptor, nor one that visibly branches
  on `bRequest == 5`.** This part of Q4 is unresolved.

I want to flag explicitly: I am **not confident** in the descriptor-buffer address itself. I did
not find the buffer the IN-transfer's 8 bytes land in — I did not trace `sub_00284CDA` (the TD
builder) to find which guest address it points the IN TD's buffer pointer at, and did not find
downstream code dereferencing that address as a `USB_DEVICE_DESCRIPTOR` struct (e.g. reading
`bMaxPacketSize0` at +7 or `bcdUSB` at +2/+3). This is the weakest part of the report — treat it
as "not found", not as "determined absent".

---

## 6. What I could not determine — please read before acting on this report

1. **The "exactly six attempts, then abandon the port forever" behavior is not explained by
   anything I found.** I read every direct caller and the two indirect-dispatch call sites of
   `sub_00281468`, plus its full gating chain (`0x3CC8B1` latch, the 32-byte slot table, the
   100ms retry timer in `sub_00280EE8`/`sub_00281107`/`sub_00281236`). None of that code
   contains an incrementing counter compared against 5, 6, or 3. I grepped the entire
   `game_input`-tagged region of `recomp_0017.c` for 8-bit/32-bit comparisons against the
   literals 5 and 6 and manually checked every hit in the neighborhood of this state machine;
   all of them turned out to be **enum state values** (e.g. `MEM8(esi) == 5` is a state-machine
   state number, not a retry count) or unrelated code elsewhere in the file. It is possible the
   real counter lives in a structure field I never identified (i.e. some `MEM32(esi + N)++`
   pattern I didn't recognize as a counter because I didn't know which structure offset to look
   at), or possibly the "six times" is not a counter at all but an emergent property of a
   **higher-level timeout** (e.g. a total-connect-deadline elsewhere that isn't part of this file,
   which would abort after a fixed wall-clock time regardless of how many 100ms retry cycles that
   works out to). I did not locate that layer if it exists.
2. **`sub_002828CB`** (the "queue this work item" call used throughout this state machine) was
   not read. It almost certainly contains the actual indirect dispatch that fires the function
   pointer stored at `0x3CC8BC` (i.e. the mechanism that actually invokes `sub_00281468` when it
   was only stashed as a pointer, not called directly). Reading it would likely also reveal
   whether it or its caller maintains any attempt counter.
3. **Q4's buffer address is unresolved** (see Section 5) — I did not trace `sub_00284CDA` (the
   TD builder your brief already identified) to find the guest address of the IN-transfer data
   buffer, and therefore could not identify what dereferences that buffer's contents afterward.
4. I did not fully trace `sub_0028153A`'s 11 call sites to determine which ones are reachable
   from the specific GET_DESCRIPTOR(DEVICE) transfer vs. other transfer types this same generic
   dispatcher handles.
5. Everything under "OHCI register bit meaning" (that offset `+0x50 + port*4` is
   `HcRhPortStatus`-equivalent, that `1` = `ClearPortEnable`, that `0x10` = `SetPortReset`) is
   **inference from matching bit patterns to the OHCI spec**, not something I read a comment or
   symbol name confirming. It is well-supported (matches your independently-measured
   `SetPortReset`/`ClearPortEnable` register writes exactly, and the two functions share the
   identical addressing formula), but it is inference, not a directly-read fact.

## Direct reads vs. inference, summarized

**Directly read (quoted above with line numbers):**
- Full body of `sub_002837AE` — unconditional, no branch.
- Its single caller `sub_00281468`, full gating logic.
- The 5 direct call sites of `sub_00281468` and the 2 sites that stash its address as a raw
  function pointer.
- `sub_0027FC4D`'s slot-table lookup.
- Where `0x3CC8B1` is set (`sub_002812E5`) and cleared (`sub_00280EE8`).
- The 100ms timer arm/re-arm code in `sub_00280EE8`/`sub_0028191C`/`sub_00280FAC`.
- `sub_00283761`'s `SetPortReset` write, used as a structural cross-check for `sub_002837AE`'s
  register-write interpretation.

**Inferred (flagged inline above):**
- OHCI bit meanings for the `+0x50+port*4` register array.
- That `sub_002814D5`/`sub_0028153A` are "the" descriptor judges (plausible, not confirmed).
- That `sub_00282D57`'s request block is XID-specific rather than standard `SET_ADDRESS`.

**Not determined at all:**
- The retry-count mechanism bounding enumeration to six attempts.
- The exact guest address the 8-byte device descriptor is copied to, and its consumer.
- The internals of `sub_002828CB` (the deferred work-item dispatcher).
