# Photo mode screen path findings

Bounded static read of `src/recomp/gen/recomp_0003.c` around `sub_00079B60`,
`sub_00079E40`, `sub_0007A7D0`, and `sub_0007A8F0`, plus their XBE method-pointer
table and selected render callbacks. No code was changed and no game was run.

## Screen fields and activation

- Both tick routines read `MEM32([screen+4] + 0x24)` and materialize
  `(value == 0)` as a boolean. The field is the underlying context's pause
  status: zero is unpaused; nonzero is paused. Root's live combat trace confirms
  module24=0 during active attacks. Photo mode should permit nonzero module24
  when the user deliberately enters from pause.
- `MEM32(screen + 0x24)` is the screen-local phase/status, not pause. Value 1
  enters a one-time setup path (`79B60` calls `79190`; `7A8F0` calls `79DE0`)
  and writes 2. Root observed zero through normal combat. Use `screen+0x24 == 0`
  as the observed live fight-screen qualification; do not reinterpret it as
  the pause gate.
- `[screen+0x2C]+0x24` is a third, separate attached-object field inspected by
  conditional update logic. It is not pause. It was zero in normal combat
  (`menu24=0` in Root's trace); no exact object/UI type is proven.
- Narrow entry gate: screen-local `+0x24 == 0`, loaded-fight CLogic state range
  (prototype currently uses 1..13, covering entrance/combat/victory), and host
  UI/menu/results closed. Do not require `[screen+4]+0x24 == 0`, since that
  excludes intended pause entry. State names and range boundaries are not
  proved by these functions alone. Root observed active combat at CLogic state
  5 with timer 12; auto-entry checks must include 5 (state 8 alone is invalid).

## Render pairing and original overlays

- `sub_00079E40` is a no-argument scene-render method at XBE raw pointer-table
  offset `0x28C3D4`; `sub_0007A8F0` is a one-argument tick at adjacent offset
  `0x28C3D0`. `sub_00079B60` is another tick at `0x28C3B0`. This table supports
  E40 being reachable as the render peer for A8F0's screen family, but does not
  establish that E40 is Story-only. Its body renders the fight scene and Root
  identifies it as the Battle renderer. A distinct Story-only render address
  was not established in this bounded read; keep that pairing unresolved.
- E40's conditional calls are not safe draw-suppression seams after inspecting
  their bodies:
  - `sub_000B5AD0(screen+0x2C)` processes a manager/global table (16 entries),
    calls `sub_000B2350`, `sub_000B3C30(0x39C1E0, ...)`, and conditionally
    `sub_000B54E0(screen+0x2C)`. This is state/subsystem work, not a demonstrated
    isolated paint callback.
  - `sub_000B70D0(screen+0x30)` checks byte `[object+1]`, then calls
    `sub_000B6B30(object)` and tail-calls `sub_000B6E50(object)`. These are long
    state/geometry processing routines, not a demonstrated isolated overlay
    paint path.
  - `sub_000CE200(screen+0x34)` is categorized `game_audio`; do not suppress it
    as HUD.
  - `sub_0006AFD0(screen+0x40)` checks byte `[object+4]`; when enabled it calls
    `sub_00068800([object+8])`, then increments `[object+0x90]`. This is a
    tick/counter path, not isolated drawing.
- No APT display name was visible in those bounded callback bodies. The E40
  18Dxx/1A2xx/1B5F0 sequence and world scene share the method, so skipping E40
  suppresses the whole scene. Mutating screen+0x24 also changes phase-dependent
  render cleanup/setup. This static pass identifies no safe original HUD,
  pause, or menu draw suppression call; leave E40 intact and trace APT/render
  dispatches separately if overlay removal is required.

## Limits

The field behavior above is from static branching plus Root's live combat
observation. Paused-entry probe is pending; it should confirm the nonzero
module24 value and ensure photo mode remains usable there. Overlay visual
ownership and a Story-specific render address are not proved here.

## Correct renderer for the `79B60` screen (follow-up)

The original XBE raw pointer table at offset `0x28C3B0` contains
`sub_00079B60`; the next pointer at `0x28C3B4` is `sub_000796A0`. This is the
matching update/render pair for the class dispatched through `79B60`, and is
the draw hook to use for the Story fight screen represented by this table.
The separate table around `0x28C3D0` contains `sub_0007A8F0` followed by
`sub_00079E40`, the Story/Battle-adjacent table previously inspected. Thus
`79E40` is not the renderer dispatched for the screen whose tick is `79B60`.

`sub_000796A0` is a no-argument `thiscall` returning int, Category
`game_vtable`, 495 bytes/135 instructions. Its body performs the full scene
render: calls `968A0`, `B8850`, the 18Dxx/1A2xx setup and draw sequence, global
render passes, and ends with `18DE0`, `97250`, and `18DF0`; it returns 1. The
body is structurally similar to `79E40`, but has screen-family-specific fields
and additional setup. Its `797CE` call passes `[screen+0x38]` to
`sub_0006AFD0`. It therefore explains why wrapping only `79E40` produced no
photo draw callback for the `79B60` screen.

`sub_00079190` is not the screen constructor and does not assign a vtable. It
updates the attached timing/UI resources: reads `screen+0x1C`'s `+0x3A0`, `+0x344`,
uses `[screen+0x1C]+0x3BC`, calls `sub_000647F0`, updates a float at `screen+0x48`,
and calls `sub_0006B000`/`sub_0006BF90`. This invocation occurs from the
`79B60` value-1 initialization branch. Runtime screen log gives `screen=810232F0`,
state 5; the table adjacency is the static address-level match.
