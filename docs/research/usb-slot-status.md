# USB slot-status investigation: why the give-up condition latches

All addresses are guest addresses. All code quoted is read directly from `src/recomp/gen/recomp_0017.c`
(the entire USB/`game_input` subsystem lives in this one file, roughly lines 17500–30300). Line numbers
below are from that file as it exists right now; they will drift if the file is regenerated.

Everything under **READ** was read directly and I'm confident in it. Everything under **INFERRED** is my
reconstruction of intent from the mechanics — plausible, but not something I can prove from source alone.
**COULD NOT DETERMINE** lists what needs a live memory read to settle.

---

## Q1 — `sub_0027FC4D`: the slot-table lookup

**READ.** Full function (`src/recomp/gen/recomp_0017.c:19867`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

- **Input:** `ecx` = a pointer into the slot table itself (not an explicit stack argument — this is a
  register-convention leaf function; every caller sets `ecx` before calling).
- **Key:** `MEM8(ecx + 1)`, i.e. byte at offset **+1** of whatever `ecx` points to.
- **Sentinel:** if the key byte is exactly `0x80`, the function returns `eax = 0` (NULL — "no entry").
- **Formula otherwise:** `eax = MEM32(0x3CC990) + key * 32`. Stride confirmed as **32 (0x20) bytes**,
  matching the brief's guess.
- **Table base:** the pointer value is stored at fixed guest address **`0x3CC990`** (`MEM32(0x3CC990)`).
  I could not find any code in `gen/` that writes `0x3CC990` — see "Could not determine" below.

Two sibling functions exist right after it, identical except for the key offset:
- `sub_0027FC64` (`recomp_0017.c:19898`) — key = `MEM8(ecx + 2)`.
- `sub_0027FC7B` (`recomp_0017.c:19929`) — key = `MEM8(ecx + 3)`.
Both use the same base `MEM32(0x3CC990)` and the same `<<5` stride and the same `0x80` sentinel. So the
table's 32-byte entries carry (at least) three byte-sized **index links** to other entries in the same
table, at offsets +1, +2, +3.

**Answer to Q1:** table base = `MEM32(0x3CC990)` (a stored pointer, not a compile-time constant address),
stride = 32 bytes, key = `MEM8(device + 1)`, sentinel `0x80` = "no entry" → NULL. The status byte
`sub_00281468` tests is at **offset +0** of the returned entry — see Q3, this is read directly, not
inferred.

---

## Q3 — `sub_00281468` in full (answered before Q2, since Q2's answer depends on understanding this)

**READ.** Full function (`recomp_0017.c:24648`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Answer to Q3:** the function is a single branch on `MEM8(sub_0027FC4D(device))`, i.e. the status byte at
offset +0 of the slot entry reached via `MEM8(device+1)`:
- **`== 0`** → give-up path → calls `sub_002837AE` (`ClearPortEnable`, confirmed established fact) then
  `sub_00281435` (re-arm bookkeeping).
- **`!= 0`** → success path → calls **`sub_00282D57`** instead, passing the slot entry pointer itself as
  arg1, `MEM8(device+4) & 0x7F` as arg2, the device pointer as arg3, and a literal `1` as arg4.
  `sub_00282D57` (`recomp_0017.c:28772`) is a 231-byte function that does further table lookups
  (`sub_0027FCB6`, a fourth sibling of the `sub_0027FC4D` family, not traced in depth) and queues real
  USB transfers. I did not fully trace it — not needed to answer the question, but flagging that "the
  success path" is itself non-trivial if you want to instrument it.
- There's also a third branch (`loc_002814C1`), taken only when `MEM8(0x3CC8B1) != 0` at entry — this
  is a different global latch (previously confirmed by you as written once to 0, so this branch is not
  the one being taken during your repro).

This confirms: `sub_00281468`'s decision is **entirely** about one byte — offset +0 of whatever
`sub_0027FC4D(device)` returns. Given the established fact that `MEM8(device+1)` is the key, the real
question is what that byte is and who's supposed to set it.

---

## Q2 — Every write to the status byte (offset +0 of a slot-table entry)

This is where the investigation got hard, and where I want to be most careful about READ vs INFERRED.

### Method

Every pointer into the slot table that any code in `gen/` ever obtains comes from one of exactly three
functions — `sub_0027FC4D` (key at +1), `sub_0027FC64` (key at +2), `sub_0027FC7B` (key at +3) — because
`MEM32(0x3CC990)` (the table base) appears **nowhere else** in `gen/` (`grep -rn "0x3CC990"` returns
exactly 5 lines: the three lookup functions' bodies, plus two subtractions in one more helper, see below).
So I enumerated every call site of all three lookup functions (19 call sites total across
`recomp_0017.c`) and read the code immediately following each one, looking for a write to `MEM8(<returned
pointer>)` (offset +0).

### Result: no writer via the lookup-returned pointer, in the paths I checked

Across all 19 call sites, I found reads of `MEM8(eax)`/`MEM8(esi)`/`MEM8(edi)` (comparisons) and writes to
**other** offsets of the returned entry (+1, +2, +3, +4, +5, +6, +8, +0xC, +0x10, +0x18) — link-list
bookkeeping — but not a single direct write to offset +0 through a pointer obtained from
`sub_0027FC4D`/`64`/`7B`.

### The actual writers of offset +0 — found by tracking who writes `MEM8(esi) = <const>` in the USB region

Cataloguing every `MEM8(esi) = `, `MEM8(edi) = `, `MEM8(eax) = `, `MEM8(ecx) = ` in the game_input region
(`recomp_0017.c:23400`–`26000`) turns up a small, ordered set of state values, which reads as an
enumeration state machine:

| Line | Value | Function | Context |
|---|---|---|---|
| 17586 | `0x80` | `sub_0027EC0D` (the allocator) | freshly popped entry, "just allocated" |
| 23409 | `0xFF` | inside `sub_00280EA7` | (adjacent helper, see below) |
| 23481 | `0xFE` | `sub_00280EE8` | timer/delay entry just allocated |
| 23534 | `0xFD` | `sub_00280EE8` (first-time branch) | this entry becomes `MEM32(0x3CC930)` |
| 25265 | `4` | `sub_002817D5` | before the hub/simple-device branch |
| 25289 | `5` | `sub_002817D5` (hub-children loop) | newly allocated **child** entry |
| 25335 | `3` | `sub_002817D5` (non-hub / single path) | the **device's own** entry |
| 25630 | `1` or `2` | `sub_00281AD5` | **only when `bDeviceClass != 0`** — see below |

**Zero is never written anywhere.** In this entire region, offset +0 is set to `0x80/0xFF/0xFE/0xFD` (all
"in-progress" sentinels well above any small state number) or to small positive integers `1`–`5`, but
never explicitly to `0`. That is consistent with `0` being the **implicit BSS-zero default** — i.e. an
entry that was carved out of the table at image-load time and has simply never been touched by any of
these state-transition writes. `sub_00281468`'s give-up test (`MEM8(entry) == 0`) reads as "this device
was never assigned any real state."

### Tracing which entry `sub_00281468` actually tests, and why it can stay untouched

`sub_00281468` is called (from the confirmed 100 ms retry timer, `sub_00281107`) with `esi =
MEM32(0x3CC930)`. I traced where `MEM32(0x3CC930)` gets its value and, critically, where **its own +1
byte** (the key `sub_0027FC4D` reads) gets set — because that's what determines which entry's status byte
is actually being tested.

`sub_00280EE8` (`recomp_0017.c:23454`, the retry-timer-arm function, confirmed by you as part of the
100 ms retry chain):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

and the link helper it calls, `sub_0027FF76` (`recomp_0017.c:20633`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**READ, and important:** `sub_0027FF76(new_entry, parent)` writes **`new_entry`'s own +1** to
`index(parent)`, and writes **`parent`'s +2** (or a sibling's +3) to `index(new_entry)`. So:

- `sub_0027FC4D(X)` — reading `X`'s own +1 — returns **X's parent entry**, not a child.
- `sub_0027FC64(X)` — reading `X`'s own +2 — returns **X's first child**.
- `sub_0027FC7B(X)` — reading `X`'s own +3 — returns **X's next sibling**.

Applying that to `sub_00281468`: it's called with `esi = MEM32(0x3CC930)`, and
`MEM32(0x3CC930)` is exactly the `new_entry` that `sub_00280EE8` allocated and linked as a child of
whatever `edi` (its own `ecx` parameter) was, the first time it ran. `sub_0027FF76` set that
timer-entry's own **+1 = index(edi)** — so `sub_0027FC4D(MEM32(0x3CC930))` returns **`edi`**, the
original device/port object that first armed the retry timer. `sub_00281468` is therefore testing
**`edi`'s** own status byte (offset +0), not the timer entry's.

So the real question becomes: does `edi` (the actual attached-device slot entry for port 1) ever get its
own offset +0 written to something non-zero? I traced the enumeration chain that should do that:

1. **`sub_002816FA`** (`recomp_0017.c:25091`) — completion handler for the confirmed
   `GET_DESCRIPTOR(DEVICE, wLength=8)` transfer. Validates the 8 bytes at guest `0x3CC934`:
   *Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
   Checked against **your measured bytes** `12 01 10 01 00 00 00 20`
   (`0x3CC934`=bLength=0x12, `0x3CC935`=bDescriptorType=0x01, `0x3CC93B`=bMaxPacketSize0=0x20):
   **all three checks pass.** `0x20 <= 0x40` ✓, `bDescriptorType == 1` ✓, `bLength == 0x12` ✓. It takes
   the success path (`loc_00281758`), writes `MEM8(esi+6) = bMaxPacketSize0`, calls `sub_00281056` and
   `sub_00280FAC`, and queues the **next** transfer: `GET_DESCRIPTOR(DEVICE, wLength=18)` (the full
   device descriptor), with the next callback set to `sub_002814D5` → (on success) → eventually
   **`sub_00281AD5`**.

2. **`sub_00281AD5`** (`recomp_0017.c:25583`) — completion handler for the full 18-byte device
   descriptor. This is the one that decides device-vs-interface class:
   *Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
   **Your measured descriptor has `bDeviceClass = 0x00`** (byte offset 4 of `12 01 10 01 00 00 00 20`).
   That means the code **does not take this branch**. It takes `loc_00281B37` instead — the
   per-interface-class path — which does **not** write the status byte here. Instead it queues yet
   another transfer, `GET_DESCRIPTOR(CONFIGURATION, wLength=0x50)`, with callback `sub_00281A1C`.

3. **`sub_00281A1C`** (`recomp_0017.c:25484`) — completion handler for the configuration descriptor.
   Validates the received length against the requested length, then (on success) sets the *next*
   callback to **`sub_002817D5`** and queues one more request.

4. **`sub_002817D5`** (`recomp_0017.c:25197`) — walks a fixed table at guest address `0x3CC93C`:
   *Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
   If the table walk finds a matching record, the device (or its children) get their status byte set to
   `3` or `5` — a real success. If it **doesn't** find a match, it bails out with a cancel code and the
   status byte is left untouched — exactly the "never written, stays at BSS zero" state that
   `sub_00281468` reads as "give up."

**Answer to Q2:** I could not find a single writer of the status byte through the `sub_0027FC4D`-lookup
path directly, because that path returns a *parent* link, not a self-reference — the byte that matters is
written (or not) by the device's own enumeration-state-machine code, three levels deep in the descriptor
chain: `sub_002816FA` (8-byte GET_DESCRIPTOR, passes for your device) → `sub_00281AD5` (18-byte
GET_DESCRIPTOR; **branches away from the direct-write path because `bDeviceClass == 0`**) →
`sub_00281A1C` (config descriptor) → `sub_002817D5` (driver-class-table match at `0x3CC93C`; writes the
status byte **only if a matching table record is found**, otherwise silently bails with a cancel code and
never writes it).

This is a plausible full explanation of the bug, entirely consistent with every runtime fact you gave me
(three TDs complete cleanly, the 8-byte descriptor is well-formed and passes validation, the driver still
eventually gives up) — but I want to be explicit that the **last link in the chain is not proven**, only
strongly suggested. See below.

---

## Q4 — Code that reads the 8-byte descriptor buffer

Answered inline above as part of Q2's trace (`sub_002816FA`), since that's the function that reads it.
To restate directly: **`sub_002816FA`** (`recomp_0017.c:25091`) is the only code in `gen/` that reads
`MEM8(0x3CC934)`, `MEM8(0x3CC935)`, `MEM8(0x3CC93B)` (bLength, bDescriptorType, bMaxPacketSize0). It does
**not** read bcdUSB (`0x3CC936`/`0x3CC937`), and does not check bDeviceClass at this stage (that's the
next transfer, the 18-byte one, handled by `sub_00281AD5`, reading `0x3CC938`). Against your measured
bytes, all of `sub_002816FA`'s checks pass, confirming (from the code side, matching what you already
confirmed by reading memory) that the 8-byte descriptor is accepted. It does **not** write the slot
status byte itself — it only writes `MEM8(esi+6) = bMaxPacketSize0` and chains to the next request.

The place that copies descriptor fields into a device-ish structure and directly compares/uses
`bMaxPacketSize0` is `sub_002816FA` (copies it to `esi+6`) — I did not find a separate "copy the whole
descriptor into the slot entry" memcpy; each field seems to be picked off individually by whichever
completion handler needs it, and re-read from the shared buffer at `0x3CC900`-ish rather than being
duplicated. I did not find a generic "descriptor copied wholesale into slot" routine — see "could not
determine."

---

## What I could NOT determine

1. **`MEM32(0x3CC990)` (the slot table base pointer) is never written anywhere in `gen/`.** Same for
   `MEM8(0x3CC940)`, `MEM8(0x3CC92B)`, `MEM8(0x3CC941)`, and the contents of the table at `0x3CC93C`
   walked by `sub_002817D5`. These all read as **static data from the original XBE image** (`.data`/
   `.rdata`), populated at load time, not computed at runtime by any code the lifter emitted. I cannot
   read their actual values from source — this needs a live memory read (or a hex dump of the relevant
   `.data` section of the original XBE).
2. **Whether `sub_002817D5`'s table walk at `0x3CC93C` actually finds a match for your device is
   unconfirmed.** This is the crux of my hypothesis: if it finds a match, the status byte gets set (3 or
   5) and the driver proceeds normally; if not, it bails with `0x80000400` and the byte is left at zero
   forever, exactly matching the give-up symptom. I could not evaluate the match condition
   (`MEM8(eax + 1) != 4`, and what record `0x3CC93C` walking would land on) without knowing the actual
   table bytes.
3. **I did not fully trace `sub_00282D57`** (the success-path function `sub_00281468` calls instead of
   `sub_002837AE`) — I confirmed its call signature and that it does further table lookups via a fourth
   sibling function `sub_0027FCB6`, but didn't read its body in depth. Not needed to answer the given
   questions, flagging in case you want to instrument the success path too.
4. **I did not verify at runtime that `edi` in `sub_00280EE8`'s first invocation is indeed the same
   object that `sub_002816FA`/`sub_00281AD5`/`sub_002817D5` operate on as `esi`.** The chain of
   "`sub_0027FC4D(MEM32(0x3CC930))` returns `edi`, and `edi` is the device whose descriptor gets
   validated" is my reconstruction from the linking code and the shared call-site parameter naming
   convention (device pointers are consistently threaded through these functions as the object whose
   `+0`/`+1`/`+4`/`+5`/`+6`/`+0xC` fields get touched) — it is **not** something I directly observed two
   different functions dereferencing the identical address.
5. I did not check whether there's a *separate*, earlier per-port slot allocation (before
   `sub_00280EE8`'s first call) that might already carry a different, correct linkage — i.e. I traced one
   specific chain that is consistent with all your runtime facts, but there could be another code path
   feeding the same globals that I didn't stumble across in a ~1.5M-line codebase searched by grep.

## Suggested next runtime check

Given the above, the single most informative next measurement is probably:
- Read `MEM32(0x3CC930)` (root pointer), then `MEM8(MEM32(0x3CC930) + 1)` (the key/parent-link byte),
  then resolve `entry = MEM32(0x3CC990) + key*32` and watch `MEM8(entry)` (this is the actual object
  `sub_00281468` tests — likely `edi`, the device object, per the trace above).
- In parallel, watchpoint `MEM32(0x3CC98C)` (set by `sub_002817D5` only on a table match) to see whether
  the class-table walk ever succeeds for this device, and dump the record it lands on if so.
- If `MEM32(0x3CC98C)` never gets set and `sub_002817D5` always falls into `loc_002818FC`, that confirms
  hypothesis #2 above and the next step is reading the actual table bytes at `0x3CC93C` (needs a memory
  dump / the original XBE's `.data` section) to see what record the driver was expecting and whether the
  emulated Controller S's configuration/interface descriptor should have matched it.
