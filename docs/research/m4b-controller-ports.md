# M4b: how XAPI assigns controller port/slot, and whether our topology matches hardware

> **Correction (2026-09-26 04:20, measured).** The inferred mapping below (HC0 root port 1 = game port
> 0) is wrong. With the hub on HC0 root port 1 the title saw the pad as slot 2, player 3: its key events
> carried `slot + 2 = 4` (`sub_0005F9B0` -> `sub_00142640`; `Key.getController`, `sub_0016F480`, subtracts
> 2). XAPI numbers the root ports 3, 4, 1, 2 as game ports 1-4, as xemu wires them. Patch 0044 reports four
> root ports on HC0 and puts the hub on root port 3; the pad is then slot 0 and P1 joins (PROGRESS D39).

Read-only investigation. No code was built or run. All lifted-code addresses are guest addresses in
`src/recomp/gen/recomp_0017.c` (the XPP/XAPI `game_input` region, `0x0027A000`-`0x00286000`) unless a
different file is named. Confidence is marked per finding: **READ** (I read the exact code and it says
what's claimed), **INFERRED** (strongly implied by the code but not directly proven), **COULD NOT
DETERMINE** (needs a live memory read or more search than this pass covered).

This is a follow-up to `docs/research/usb-slot-status.md` and `docs/research/m4-usb-enumeration.md`, and to
`PROGRESS.md` §6 2026-09-26 03:20 / §7 "Then M4b". It reuses those docs' findings rather than re-deriving
them (in particular: the `sub_0027FC4D`/`sub_0027FC64`/`sub_0027FC7B` family are **generic parent/
first-child/next-sibling tree accessors** over the 32-byte device-object table at `MEM32(0x3CC990)`, not a
literal "port table" — that was my first hypothesis and `usb-slot-status.md` had already disproved it).

---

## Our emulator's topology (from `tools/xboxrecomp/src/usb/`)

**READ**, from `ohci.c` / `ohci.h` / `usb_hub.c`:

- Two OHCI controllers: `s_hc[0]` at `XBOX_OHCI0_BASE = 0xFED00000` (index 0), `s_hc[1]` at
  `XBOX_OHCI1_BASE = 0xFED08000` (index 1) (`ohci.h:28-29`). Each reports `OHCI_PORTS = 2` downstream root
  ports (`ohci.c:125`, `HcRhDescriptorA` init at `ohci.c:912`). `ohci_reset(&s_hc[0], ...)` runs before
  `ohci_reset(&s_hc[1], ...)` (`ohci.c:1110-1111`) — controller 0 is always registered/enumerated first.
- The controller-thread log line spells the topology out directly (`ohci.c:1141-1143`):
  ```c
  fprintf(stderr, "  OHCI: two controllers at 0x%08X and 0x%08X, "
                  "%d ports each, one device on HC0 port 1\n", ...);
  ```
  and the plug-in code (`ohci.c:1029-1034`) writes the connect bits to `HcRhPortStatus1` (register offset
  0, i.e. **root port 1** in the OHCI/this-codebase's 1-based port numbering) on `s_hc[0]`:
  ```c
  hc->reg[HcRhPortStatus1 / 4] |= PORT_CCS | PORT_CSC;
  ...
  fprintf(stderr, "  [OHCI0] operational after %u ms; device arriving on port 1\n", ...);
  ```
  So: **the hub sits on host controller 0 (`0xFED00000`), root port 1 (1-based).**
- The hub itself (`usb_hub.c`): `#define HUB_PORTS 3`, `#define PAD_PORT 1` (`usb_hub.c:13-14`), device
  descriptor `045E:0288` ("a Controller S's hub", `usb_hub.c:38`). Port-power/reset logic special-cases
  `PAD_PORT` only (`usb_hub.c:86-101`) — the gamepad is hard-wired to hub port 1 (1-based); the other two
  hub ports (2, 3) are left for memory units and are otherwise unimplemented.
- `usb_hub.h`'s header comment is explicit about why, and that it is meant to mirror real hardware:
  > "A Controller S is a three-port hub with the gamepad on its first port and the two memory-unit slots on
  > the others. The console's USB stack is built for that shape, and xemu models it the same way; a pad
  > plugged straight into a root port is something no console ever saw."

**Topology summary (READ): HC0 root port 1 -> hub (045E:0288) -> hub port 1 -> gamepad.** This is stated by
the project's own code comments to reproduce real Controller-S hardware (and xemu's model of it), not an
arbitrary emulator choice.

---

## Q1 — How XAPI assigns an Xbox port (0-3) and slot, from USB topology

### 1a. The four physical ports are enumerated, not computed, at `sub_0027CF80` (0x0027CF80-0x0027D08C)

**READ.** This is the first function in the whole `game_input` region and looks like `XInitDevices`'s/the
USB stack's own bus-enumeration bring-up. It builds a device name per index and asks the HAL/PnP layer for
it (indirect call through `MEM32(0x2853BC)`), for `esi` = 0 up to `ebx` (`ebx = min(deviceCount+1, 8)`,
`recomp_0017.c:54446-54471`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`MEM32(edx + 4) = esi` is the important line: **the 0-based loop counter is written straight into each
newly-created "root port" object's own field, with no arithmetic** — no `hcIndex*2 + rootPortIndex`
computation anywhere in this function. The number that ends up as the Xbox `dwPort` (0-3) is therefore
simply **the order in which the OS/HAL layer enumerates USB host-controller root-port objects to this
loop**, not something XAPI computes from a (host-controller, root-port) pair.

**INFERRED, high confidence:** since controller 0 is always reset/registered before controller 1
(`ohci.c:1110-1111`, confirmed above), and PnP/bus-relations enumeration order is deterministic and follows
registration order, the practical mapping in our emulator is:
- Xbox port 0 = HC0 root port 1
- Xbox port 1 = HC0 root port 2
- Xbox port 2 = HC1 root port 1
- Xbox port 3 = HC1 root port 2

I could not find a second, explicit confirmation of this order from a single instruction (it falls out of
enumeration order, which is a property of the emulator's/console's PnP layer, not of one line of XAPI
code) — flagging this half as **INFERRED**, not **READ**.

### 1b. Hub children inherit the port and get a 1-based hub-port "slot" tag, at `sub_002817D5` (0x002817D5-0x0028191C)

**READ.** This is the completion handler that matches a device against the class-driver table at
`0x3CC93C` (see `usb-slot-status.md` §Q2 point 4 for how that table walk works). When the matched record is
a multi-child (hub) type (`MEM8(0x3CC940) != 1`), it loops a 0-based counter `ebx` up to
`MEM8(0x3CC92B)` (a per-hub max-ports count, static XBE data), allocating one new device-object entry per
hub port via `sub_0027EC0D`, and stamping it (`recomp_0017.c:70326-70379`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Answer to Q1 (READ):** for a hub's children, the 1-based hub-port index (`ebx+1`, i.e. **1 for the hub's
first port, 2 for its second, ...**) is written into the low bits of the child device-object's own **+4**
field; every other identifying field the object needs later (**+5, +6, +8, +0xC, +0x18**) is copied
unchanged from the parent (the hub). So the child's "port identity" (whatever downstream code reads from
+5/+6/+8/+0xC/+0x18) is **inherited verbatim from its parent's root-port object**, while +4 records *only*
"which physical position on this hub" the child sits at. This is the on-disk implementation of the
classic Xbox `(dwPort, dwSlot)` split: the port is a property of the whole hub-and-its-children subtree; the
slot distinguishes children of the same hub.

### 1c. `XInputOpen`'s internal implementation resolves `(dwPort, dwSlot)` to a fixed record, then searches for a matching physical device by an inherited index

**READ / candidate identification.** `sub_0027DE3B` (0x0027DE3B-0x0027DE91, 4 params, called directly from
game code — see Q3) matches `XInputOpen(DeviceType, dwPort, dwSlot, pPollingParameters)`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

i.e. `dwSlot` selects between two fixed byte offsets (0 and 0x10) within a per-port record array — this
matches the real XDK's `XInputOpen` slot semantics (slot 0 = the device itself, slot 1 = the first memory
unit) directly, as a flat offset rather than a second array index.

`sub_0027F895` (0x0027F895-0x0027FAE5) is the body: it resolves the fixed per-`(dwPort,dwSlot)` record via
`sub_0027ED74(perTypeCtx, dwPort[+0x10])`, fails with `0x48F` if the record pointer comes back null (bad
port/slot), fails with `0x20` if the record's **+0x12** field is already non-null (**"already open"**, *not*
"device present" — see below), otherwise pops a 0xAB-byte handle object off a free list at
`MEM32(0x3CC810)`, and sets `handle.+0 = portSlotRecord`, `handle.+0xA3 = perTypeCtx`. **`XInputOpen`
itself never checks whether a physical device is actually attached** — it only checks the slot isn't
already opened, and (unconditionally, if the slot is free) hands back a handle. Presence is discovered
later, by `XInputGetState`.

`sub_0027ED74` (0x0027ED74-0x0027EDDE) is a **linear search** over the *separate* 22 (`0x16`)-byte "opened
device" table (base `MEM32(0x3CC80C)`, count `MEM16(0x3CC808)` = 4, 8 or 0xC depending on which device
types the game registered at init — set in `sub_0027CF80`'s neighbourhood, `recomp_0017.c:54958-54972`).
For each in-use entry it fetches `MEM32(MEM32(entry) + 0x14)` — via the one-line accessor
`sub_0027FE4F`: `eax = MEM32(ecx + 0x14);` (`recomp_0017.c:64288-64290`) — and compares it against the
`dwPort[+0x10]` key it was given, also requiring the entry's own `+0xE` "class context" to match:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**Answer to Q1 (READ, chained):** the number that finally ties a *physical, enumerated* device to the
`dwPort` (or `dwPort+0x10` for slot 1) a game asks `XInputOpen` for is a small integer living at **offset
+0x14 of the device's own lower-level USB device-handle object** (the thing `MEM32(deviceObject)` points
at, one level below the 32-byte enumeration-tree object discussed in 1a/1b). The same
`sub_0027FE4F`/`sub_0027ED74` pair is reused, unchanged, by the boot-keyboard/mouse attach-completion code
(`sub_0027F1E7`, `sub_0027F271`) for exactly the same purpose, confirming this is the one shared
"resolve a physical device to its assigned port/slot" mechanism for every USB-attached input device class.

**COULD NOT DETERMINE (needs live memory / more search budget):** the exact instruction(s) that *write*
this `+0x14` value on the lower-level device-handle object for a specific attach event. I found only a
single literal use of `0xFED00000` in the whole file (`recomp_0017.c:56312`, registering OHCI0's MMIO
window for the HAL) and no literal `0xFED08000` anywhere in it, and did not find an explicit
`hcIndex*2+rootPortIndex`-style computation reachable from a static call chain in the time available. Given
1a's finding that the four root-port objects are themselves just tagged with a bus-relations enumeration
index (no arithmetic), and 1b's finding that a hub's children copy that identity down from their parent
verbatim, the most consistent reading is that `+0x14` (or whatever the lower-level device handle uses to
back it) is *also* inherited down from the root-port object of 1a, rather than recomputed — but I could not
find the single instruction that copies it, and (per `usb-slot-status.md`'s own "could not determine"
list for the neighbouring `0x3CC990` table) this kind of value quite plausibly lives in static XBE data /
gets set by a function this subsystem reaches only through a data-driven table, which is a known-common
pattern in this exact code (see `docs/research/m4-usb-enumeration.md` §4's "Caveat: several handlers are
reached only through data, not code").

---

## Q2 — What port/slot does our topology's pad get, and does it match real hardware?

**INFERRED, from 1a and 1b together, high confidence for the shape, medium confidence for the exact
number:**

- Our hub is on **HC0 root port 1**. Per 1a's enumeration-order inference, HC0's ports are almost certainly
  enumerated before HC1's, and root port 1 before root port 2, so the hub's own root-port object is very
  likely tagged **Xbox `dwPort = 0`** (the first of the four).
- The gamepad sits on the hub's **port 1** (1-based, `PAD_PORT` in `usb_hub.c`). Per 1b's stamping code,
  that makes the gamepad's own device-object `+4` field equal **`0 + 1 = 1`** (the first hub child).
  `XInputOpen`'s `dwSlot` encoding (1c) only distinguishes slot 0 (offset +0) from slot 1 (offset +0x10),
  which lines up with "the gamepad itself is the hub-port-1 child" mapping to **`dwSlot = 0`** (the
  controller, as opposed to a memory unit) under the natural `dwSlot = hub_port_index - 1` reading implied
  by 1b's `ebx+1` stamp.

So: **our pad should present as Xbox `dwPort = 0`, `dwSlot = 0`** — i.e. what the console box labels
"controller port 1", with the pad recognised as the primary device (not a memory unit) at that port.

**Is that consistent with real hardware?** Yes, structurally, and this project's own code says so
explicitly: `usb_hub.h`'s comment (quoted above) states real Controller-S hardware *is* a 3-port hub inside
the controller shell, with **the gamepad on the hub's first port** and the two memory-unit expansion slots
on the other two — and that xemu, a well-established reference emulator, models it the same way. Our
`PAD_PORT = 1` (1-based, i.e. the hub's *first* port) matches that directly; there is no port-3-vs-port-1
mismatch to report. I did not find (and did not expect to find, since it is a hardware fact rather than
something in this codebase) independent confirmation of "port 1" vs some other hub port from a source
inside this repository beyond that comment — flagging that the real-hardware side of this claim rests on
this project's own prior research/comment, not on something I re-derived from first principles in this
pass.

**Net for Q2:** no mismatch found. If our pad is invisible to a screen that polls ports 0-3, the cause is
not "we put the pad on the wrong hub port" or "we put the hub on the wrong root port" — both match the
real Controller-S shape as this codebase itself documents it.

---

## Q3 — `XInputOpen`/`XGetDevices`/`XGetDeviceChanges` and their game-code callers

**READ**, candidates and call sites:

| Function | Address | Role | Called from (game code, outside XPP) |
|---|---|---|---|
| `sub_0027DDCE` | 0x0027DDCE-0x0027DE3B | `XGetDeviceChanges`-shaped (3 params; computes insertions/removals from an old/new connected-bitmap pair, matches real signature `(DeviceType, pInsertions, pRemovals)`) | `sub_00198160`, `sub_0019B060`, `sub_001A1420`, `sub_001A1BA0`, `sub_001EBBE0`, `sub_001EBE10` |
| `sub_0027DE3B` | 0x0027DE3B-0x0027DE91 | `XInputOpen`-shaped (4 params: DeviceType, dwPort, dwSlot, pPollingParameters — see Q1c) | `sub_001EBBE0`, `sub_001EBE10` |
| `sub_0027E075` | 0x0027E075-0x0027E0E8 | `XInputGetState` (per task's "Known"; confirmed by reading it — copies packet number + report bytes from the port/slot record reached via `handle.+0`) | `sub_001EBBE0` |

All three are called from `src/recomp/gen/recomp_0013.c` — well outside the `0x0027xxxx`-`0x0028xxxx` XPP
region, i.e. genuine game/engine code, not XAPI internals.

`sub_001EBBE0` (`recomp_0013.c:19748`) is the generic per-frame "poll every gamepad port" routine:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_001EBE10` (`recomp_0013.c:20103`) does the same shape of loop with an **explicit, literal bound of
4** (`ebx = 4;` at `recomp_0013.c:20146`) — i.e. this game-side polling code iterates **exactly ports
0-3**, matching the task's framing of "a screen that polls ports 0-3" precisely.

**Answer to Q3:** the game opens **all four ports, `dwPort = 0..3`, with `dwSlot = 0` fixed** (the
controller itself, not a memory unit) via this shared polling routine, driven by `XGetDeviceChanges`'s
insertion/removal bitmap. I found **nothing in this polling loop that would make an in-range port
invisible** — it tests every bit 0-3 of the bitmap unconditionally and opens/queries whichever ports report
an insertion. Combined with Q2 (our pad should enumerate at `dwPort = 0`) and the fact that the main menu
*does* see the pad (per `PROGRESS.md`), this loop — or one just like it — is almost certainly what feeds
the main menu successfully, which means **the four-player join screen's failure to react to START is not
a port-visibility problem in this shared XAPI-polling code.** The bug is more likely further downstream,
in front-end/game logic specific to the "Select user ID" screen (e.g. ActionScript-level gating on which
ports are allowed to "join", or an edge-detection/state check that differs from what the main menu does
with the same per-port state) — tracing that screen's own handler is outside what this XPP/XAPI-focused
pass covered and would need a separate investigation starting from the front-end script side
(`screens/feflow.xml`, the "Select user ID" screen's ActionScript) rather than from XAPI.

---

## Summary table

| Question | Answer | Confidence |
|---|---|---|
| How is `dwPort` (0-3) assigned? | Enumeration order of USB host-controller root-port PnP/bus-relation objects, stamped as a bare loop index (`sub_0027CF80`, `MEM32(edx+4)=esi`) — not computed from `(hcIndex, rootPort)` by any instruction found. | READ (the stamp) / INFERRED (that HC0-before-HC1 registration order determines the final numbers) |
| How is `dwSlot` (hub-port position) assigned? | 1-based hub-port loop index stamped into the child device-object's own `+4` field when a hub's children are created (`sub_002817D5`); `XInputOpen` maps `dwSlot` 0/1 to two fixed byte offsets (0, +0x10) in the per-port record array. | READ |
| What ties a physical device to a `dwPort`/`dwSlot` at `XInputOpen` time? | A linear search (`sub_0027ED74`) over the opened-device table, matching on a value at `+0x14` of the device's lower-level USB handle (read via `sub_0027FE4F`). | READ (the search) / COULD NOT DETERMINE (who originally writes `+0x14`) |
| Our topology's pad: what port/slot? | `dwPort = 0`, `dwSlot = 0` (first HC0 root port, first hub port). | INFERRED |
| Does that match real hardware? | Yes — our own `usb_hub.h` states real Controller-S hardware is a 3-port hub with the gamepad on the hub's first port, same as here and same as xemu. No port mismatch found. | Documented fact in this repo, not independently re-derived |
| Which ports does the game open? | All four, `dwPort=0..3`, `dwSlot=0`, via a shared per-frame polling routine (`sub_001EBBE0`/`sub_001EBE10`) that tests every bit of `XGetDeviceChanges`'s bitmap. | READ |
| Is there a port-visibility bug in this polling code? | No — it is generic and covers 0-3 unconditionally. The join screen's ignoring of START is therefore most likely a front-end/game-logic issue downstream of this polling, not an XAPI port-assignment defect. | INFERRED |
