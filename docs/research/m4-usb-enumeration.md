# USB enumeration state machine in the lifted XAPI USB core (M4)

Investigation of `src/recomp/gen/recomp_0017.c` (covers guest 0x0027A000-0x00285... — the
whole 0x0027A000-0x00286000 window lives in this one file). Goal: explain why a gamepad on
the root port (experiment A) stalls after `SET_CONFIGURATION`, and why a hub on the root
port (experiment B) stalls right after `SET_ADDRESS`. Read-only investigation; nothing was
built or run.

All addresses below are guest addresses (`sub_XXXXXXXX` = lifted function at guest 0xXXXXXXXX).
Confidence is called out per finding — several field offsets are inferred from control flow
and constant values, not from symbols, since none exist for this binary.

## 1. The enumeration state machine and its driver (confirmed)

The per-device enumeration state machine is a global byte at **0x3CC928**, advanced by a
work item that the OHCI interrupt path queues on the **start-of-frame interrupt**.

Call chain, confirmed by direct-call evidence (`scripts/callers.py`) and by reading each
function:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_00281C20` (0x00281C20-0x00281C74):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

- **state 0 -> `sub_00281107`**: reads the cached `bMaxPacketSize0` from the device object
  and calls **`sub_00283761`** (one of the OHCI-register-writing functions named in the
  brief) with a completion address of `sub_00280FDA`. This is the SET_ADDRESS step — it is
  the first OHCI-level function on the path, consistent with SET_ADDRESS being the next
  thing the trace shows after the initial 8-byte GET_DESCRIPTOR(DEVICE).
- **state 3 -> `sub_00281AD5`**: this is the only place in the whole 0x0027A000-0x00286000
  window that branches on the device's class byte. See §2.

Only one SOF tick is needed to go from state 0 to state 3 in the observed traces (state 1
and state 2 are not exercised in either experiment — they appear to be alternate/retry
paths, e.g. `sub_0028191C`, state 2, independently builds a GET_DESCRIPTOR(DEVICE, wValue
0x0100, bmRequestType 0x80) request, which looks like a second, full 18-byte device
descriptor fetch used on a different branch; not exercised here).

## 2. The class-0-vs-everything-else branch (confirmed; this is the answer to Q1)

`sub_00281AD5` (0x00281AD5-0x00281C20), called as `sub_00281AD5(edx=0x3CC930 /*device
object*/, ecx=0x3CC8B4 /*scratch URB*/)`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So the *only* class-sensitive check anywhere in this address range is
`bDeviceClass == 0`. Any other value — 9 (hub) included, but the code does not special-case
9 beyond the tag byte — is diverted away from the "fetch Configuration descriptor" path
into `sub_002816C6`.

`sub_002816C6` (0x002816C6-0x002816FA) does **not** issue any further descriptor request:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

For the values actually reached in experiment B (hub, class 9), the "kind" tag is 1 and no
further request is queued in this file — which matches the observed behaviour exactly: one
SOF tick after SET_ADDRESS, the driver decides the device isn't a plain (class 0) function
device, tags it, calls this completion helper, and — in this environment — that's the end
of the road. Nothing here issues GET_DESCRIPTOR(CONFIGURATION), GET_DESCRIPTOR(hub, 0x2900)
or anything else for a class-9 device from this code.

**What the code expects instead of that OHCI-level dead end:** the `MEM32(esi+0x10)`
indirect handler slot is exactly the kind of thing a class-driver registration (an
`XInitDevices`-style table, or a hub-driver "AddDevice" callback) would populate. The value
tested at `sub_0027ECBA`'s return is data we did not chase further (it comes from a lookup
keyed off the "kind" byte written above); if the hub class driver's registration path
populates that slot only when it also observes a real hub descriptor / interrupt endpoint,
and our environment never lets that registration happen, this is where the chain would go
quiet with no visible trace beyond the one SOF tick. **Not fully confirmed** — I could not
find the code that populates `[esi+0x10]`; it may be a data-driven table (see the caveat in
§4).

The `bDeviceClass == 9` value is also used, separately and *not* on this path, later — see
§3's `sub_002834CA` — as the literal SET_CONFIGURATION `bRequest` byte value 9 (that's the
standard SET_CONFIGURATION request code, coincidence with the class number, not a class
check).

## 3. Why a class-0 device (experiment A) stalls after SET_CONFIGURATION (confirmed path, one gap)

For `bDeviceClass == 0`, `sub_00281AD5` falls into `loc_00281B37` and eventually the driver
fetches the Configuration descriptor and walks it. The only interface-class recognizer
found anywhere in 0x0027A000-0x00286000 is:

`sub_0027F6C3` (0x0027F6C3-0x0027F7A1):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`bInterfaceClass` 3 with protocol 1/2 is the **standard USB-HID boot-protocol keyboard/
mouse** case. There is no case for `bInterfaceClass == 0x58` (Microsoft's Xbox-controller
vendor class) anywhere in this file. An XID gamepad's interface descriptor (class 0x58,
subclass 0x42) falls straight into the `else` branch above — `loc_0027F776` — which is the
generic "not a device I recognise, give up on this interface" cleanup. That is why
experiment A's trace shows the vendor GET_DESCRIPTOR (bmRequestType 0xC1, bRequest 0x06,
wValue 0x4200) is **never sent**: nothing in this driver ever decides to send it, because the
code that would have to make that decision only knows about HID class 3.

I could not find where `sub_0027F6C3` itself is called from (`scripts/callers.py` reports
"reached only indirectly", and grepping this file for its address as data also finds
nothing) — so I cannot see what feeds it the current descriptor, nor rule out a second,
separate interface-class recognizer elsewhere that *does* know about 0x58/0x42 and that
simply isn't reachable in this trace for some other reason. See the caveat in §4.

**On "does it require a hub parent":** I found no code in this range that branches on
whether the device's parent is a hub versus the root hub. The repeatedly-checked global
`0x3CC8B1` looked at first like it might be a port/hub-position flag, but it is written `0`
and `1` and tested against `0` uniformly as a generic **abort/retry flag for the step in
progress** (every state handler checks it and, if set, calls the same `sub_00281468` abort
path) — it is not port- or topology-specific. So I found no evidence, one way or the other,
that a hub parent is structurally required by this address range; the real answer may live
in the hub/port-specific code the driver never reaches in either experiment (see §2's gap,
and the SET_CONFIGURATION -> GET_HUB_DESCRIPTOR chain below, which is the *hub's own*
continuation, not something a child gamepad would go through).

For contrast, the **hub-specific** continuation does exist and is concrete: `sub_002834CA`
(0x002834CA-0x002835F0) walks the cached Configuration descriptor for an interrupt endpoint,
then issues a real, standard `SET_CONFIGURATION` (`bmRequestType 0x00, bRequest 9, wValue =
MEM8(0x3CC99D)` i.e. the cached `bConfigurationValue`) whose completion routine is
`sub_0028344E`, which — on success — immediately issues `GET_DESCRIPTOR` for the **hub
descriptor** (`bmRequestType 0xA0, bRequest 6, wValue 0x2900`). This is unambiguous hub
enumeration continuation code. But it is *also* only reached "indirectly" with no static
caller found in this file, so I cannot show what triggers it or confirm it is what would run
after experiment B's SET_ADDRESS if the hub's own descriptor/interrupt-endpoint traffic were
present. Given experiment B never gets past SET_ADDRESS + one SOF tick, this function is
simply never reached in that trace either way — the divergence for the hub happens earlier,
at §2's `bDeviceClass == 0` check.

## 4. Caveat: several handlers are reached only through data, not code

`scripts/callers.py` and a plain grep for the literal address both come up empty for
`sub_0027F6C3` and `sub_002834CA` (and a few others: `sub_0027F1E7`'s own home address is
found as data at 0x3CC830, but who ultimately calls the function that writes 0x3CC830 in
the first place is not visible). Functions this happens to are called through pointers
whose value is never written by an instruction we can grep for — the most likely
explanation is a **static, read-only dispatch table** (interface-class -> handler,
"kind" -> handler) that was copied into guest memory as part of the image's initialized
data rather than constructed by code, so it never appears as a `MEM32(addr) = 0x27F6C3;`
line in the lifted C. This means: (a) I cannot rule out that such a table also contains an
entry for class 0x58/subclass 0x42 that simply isn't exercised on the code paths I could
trace by control flow alone, and (b) the exact selection mechanism feeding `sub_0027F6C3`
its current interface pointer, and feeding `sub_00281C20`'s work-item queue the specific
per-device context, could not be fully confirmed from lifted C alone. Anyone continuing
this should grep the raw XBE's `.rdata`/`.data` for `27 F6 C3 00` / `CA 34 28 00` style
32-bit little-endian literals to find the actual table.

## 5. Straight answers to the three questions

1. **What differs for class 9 vs class 0, and why does case B stop:** `sub_00281AD5`
   (state 3 of the SOF-driven state machine at `sub_00281C20`) reads a cached
   `bDeviceClass` byte (global `0x3CC938`, filled in from the earlier 8-byte
   GET_DESCRIPTOR(DEVICE) response) and requires it to be **exactly 0** to continue on to
   fetching the Configuration descriptor. Any other value, including 9, is tagged
   (hub=1, other=2) and handed to `sub_002816C6`, which completes/notifies with a fixed
   status and otherwise dispatches through an indirect handler slot at `[device+0x10]`
   that nothing in this address range is seen populating. No further descriptor request
   is issued on this path for a class-9 device. What the code is waiting for instead is,
   most plausibly, a class/hub-driver registration populating that handler slot — this
   could not be confirmed because the table that would do it (§4) is not visible in the
   lifted control flow.
2. **Why case A stops after SET_CONFIGURATION:** the one interface-class recognizer found
   in this address range, `sub_0027F6C3`, only knows about `bInterfaceClass == 3`
   (USB-HID) with protocol 1 (keyboard) or 2 (mouse); everything else — including class
   0x58/subclass 0x42 (XID) — falls into a generic cleanup path (`loc_0027F776`) that
   releases a reference and returns without issuing any further request. This is why the
   vendor GET_DESCRIPTOR (0xC1/0x06/0x4200) is never sent and no interrupt endpoint is
   ever registered: nothing in this driver decides an XID interface needs one. I found no
   requirement, in this address range, that the device have a hub parent — but I also
   could not locate the code that *would* recognise class 0x58 (if it exists, it is
   probably reached only through the data table in §4, or lives outside
   0x0027A000-0x00286000 entirely).
3. **Anything plainly about emulation rather than the device:** the entire state machine
   is gated on the OHCI **start-of-frame interrupt** — `sub_00281C20` only runs because
   `sub_0027D722` queues it as a one-shot work item from the SOF ISR path
   (`sub_0027D08C`). Both experiments show exactly one SOF tick driving the state machine
   from 0 to 3; nothing else in the trace depends on repeated SOF delivery in the range
   inspected here, so I did not find a spot where the driver is simply polling a register
   the emulation never updates, or waiting on a second interrupt that never arrives, in
   the specific control flow examined. The generic abort flag at `0x3CC8B1`, checked by
   every state handler, is the closest thing to a "something else must have gone right
   first" gate, but it is not obviously tied to any specific hardware register — it reads
   as ordinary error propagation between the small state-handler functions, not an
   emulation-specific wait.

## Functions referenced (guest addresses)

| Address | Role (confidence) |
|---|---|
| sub_0027D08C | OHCI ISR/DPC entry, reached only indirectly (high) |
| sub_0027D722 | Queues the enumeration work item on SOF (high) |
| sub_00281C20 | SOF-driven state-machine dispatcher, state byte at 0x3CC928 (high) |
| sub_00281107 | State 0: issues SET_ADDRESS via sub_00283761 (medium-high) |
| sub_0028275A | State 1 handler (not exercised in either trace; not analysed in depth) |
| sub_0028191C | State 2 handler; builds a GET_DESCRIPTOR(DEVICE, 0x100) request (medium) |
| sub_00281AD5 | State 3: branches on cached bDeviceClass == 0 vs other (high) |
| sub_002816C6 | Non-class-0 completion/notify helper, no further request issued (high) |
| sub_002828CB | Generic "submit/parse descriptor" helper used by the class-0 continuation (low detail) |
| sub_0027F6C3 | Interface-class recognizer: HID (class 3) protocol 1/2 only (high) |
| sub_0027F1E7 / sub_0027F271 | Completion routines that search a class-driver table and attach it (medium) |
| sub_002834CA | Hub continuation: parses config descriptor, issues SET_CONFIGURATION (high) |
| sub_0028344E | SET_CONFIGURATION completion for the hub path: issues GET_DESCRIPTOR(hub, 0x2900) (high) |
| sub_0027DE9D | Vendor request (bmRequestType 0xC1) builder gated by a device-object flag at [devobj+0xE]->+0x28; exact purpose and whether it is on the live path is **unresolved** |

Starting points from the brief (OHCI register writers) were used only as anchors for
`scripts/callers.py`; none of their own register-level content was re-examined here since
the question was about the enumeration logic that calls them, not the HC driver itself.

## 6. Resolution (2026-09-24, measured)

The "indirect handler slot" in §2 and the missing class-0x58 recogniser in §3 were the same thing: the
class-driver table in the XPP section, `0x27CDB4..0x27CDC4`, four pointers to driver records keyed
`{kind, class}` (`0x81` device-level, `0x82` interface-level):

| record | key | driver | entries (init, AddDevice, RemoveDevice) |
|---|---|---|---|
| `0x27CDE8` | `82 08` | mass storage (memory unit) | `0x27CF80`, `0x27E1B7`, `0x27E356` |
| `0x27CF20` | `82 58` | XID (gamepad) | `0x27D182`, `0x27FAE5`, `0x27F4C6` |
| `0x27CF38` | `82 03` | HID | `0x27D182`, `0x27FAE5`, `0x27F4C6` |
| `0x27CF68` | `81 09` | hub | `0x27D99A`, `0x2835F0`, `0x282FD9` |

`sub_0027ECBA` searches it; `sub_002816C6` calls the record's AddDevice through `[record+8]`. The hub's
AddDevice `0x2835F0` and the XID driver's `0x27FAE5`/`0x27F4C6` had never been lifted, so the call failed
(`[ICALL] Failed to resolve VA 0x002835F0`) and the device was dropped with no request after it. Seeding
the six unlifted entries (`config/seed_functions.json`) and re-lifting was the whole fix: the hub then
enumerates, powers its ports, resets port 1, and the pad behind it is addressed, configured and asked for
its XID descriptor and capabilities; the title polls its interrupt endpoint and sends rumble reports.
The table is found by `python` over the XBE: every dword in XPP/.rdata/.data that points into XPP code at
an address no lifted function starts at.
