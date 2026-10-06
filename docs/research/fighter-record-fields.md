# Fighter record fields for the test harness

Read-only reverse-engineering notes on the lifted code of Def Jam: Fight for NY. No lifted C or
disassembly is reproduced here; everything is described in words with guest addresses.
Method: read the per-update loop `sub_001A4A30` and its callees, the spawn path, and the
front-end `ControllerSetup` handler.

Conventions: `R(slot) = 0x3B92E0 + slot * 0x12E8`. Floats are IEEE single. The world is Y-up;
the ground plane is X/Z. Confidence: **V** = verified by reading the code that writes or uses
the field. **I** = inferred from usage patterns or constants. **U** = unknown or not resolved.

## Field table (offsets from the record start)

| Offset | Type | Meaning | Conf | Evidence (function) and slot-0 address |
|---|---|---|---|---|
| +0x00 | ptr | Primary opponent record. Also +0x04 and +0x08, other record pointers, null when unused. | I | Set in `sub_001B3110` from `slot ^ 1`, `slot ^ 3`, `(slot+1) % 3`. `sub_001C3B80` reads the target's +0x44 and adds a height offset of 18.0. |
| +0x28 | s32 | Slot index 0..3, or -1 when unused. | V | Written by `sub_001B3110` (second argument). `sub_001A4D90` writes -1 for unused slots. 0x3B9308 |
| +0x2C | s32 | **Character index** (zero-based). Indexes the per-character data table at 0x3B864C (stride 4). | V | `sub_001B3110` stores its third argument here. `sub_001B2090` reads it to fetch character data. 0x3B930C |
| +0x44 | f32 x | World position X. | V/I | `sub_001B3110` initialises the vec3 at +0x44 to (0, -100.0, 0). `sub_001BBB60` takes it, does atan2 on its X and Z, and returns a ring-sector index 0..3. `sub_001A76A0` adds the rotated animation offset to it. Not found: the writer that integrates movement. 0x3B9324 |
| +0x48 | f32 y | World height (up). | V/I | Same vec3. Copied to +0xC8 by `sub_001A76A0`. 0x3B9328 |
| +0x4C | f32 z | World position Z. | V/I | Same vec3. 0x3B932C |
| +0x50 | vec3 | Rotation in degrees (X, Y, Z). Passed to the model update `sub_00044660` together with +0xC4. | I | `sub_001B3110` zeroes it. `sub_001A8480`. |
| +0x54 | f32 | **Facing yaw, degrees** (middle component of the rotation vec3). | V/I | `sub_001A76A0` multiplies it by pi/180 and takes sin/cos on the XZ plane. Angle helpers `sub_001BACD0` (add and wrap to 360) and `sub_001BAC80` (shortest difference) use it. 0x3B9334 |
| +0x5C | vec3 | Scale, initialised to (1, 1, 1). | I | `sub_001B3110`. |
| +0x80 | s32 | Animation or model handle, -1 when none. | I | `sub_001B3110`, tested by `sub_001A7610`. |
| +0x9C / +0xA0 / +0xA4 / +0xA8 | f32 | Animation clock, remaining time, length, speed. | I | `sub_001A8480` advances +0x9C by `+0x334 * +0xA8 * dt`. |
| +0xC4 / +0xC8 / +0xCC | vec3 | Render position: +0x44 plus the yaw-rotated root-motion offset. | V | `sub_001A76A0`. Handed to `sub_00044660` for the model. |
| +0xD4 | f32 | Heading angle (yaw wrapped with an animation offset). | I | `sub_001A76A0`, copied to +0xA6C by `sub_001B9CE0`. |
| +0xDC.. | vec3[20] | World positions of 20 skeleton joints (joint ids in the table at 0x2EC0E0). +0x1CC.. holds last update's copy. | V | `sub_001A7610` copies each vec3 to +0xF0 higher, then refreshes it via `sub_000445A0(out, slot, jointId)`. |
| +0xE8 / +0xEC / +0xF0 | vec3 | Joint index 1 (joint id 3), a body-centre world point. Candidate for "where the fighter really is" during animations. | I | Second element of the +0xDC array. Copied to +0xA60.. by `sub_001B9CE0`. |
| +0xA60 / +0xA64 / +0xA68 | vec3 | Copy of +0xE8, used for auto-target distance. | V | `sub_001B9CE0` writes it. `sub_001B9D60` computes the XZ distance between this and another fighter's copy. 0x3B9D40 |
| +0x350 / +0x354 / +0x358 | f32 | Health, max health, second limit. | V (known) | `sub_001B3110` initialises. |
| +0x91E, +0x920, +0x924 | flags | Misc state flags. | known | |
| +0x937 | u8 | **Bit 0 = CPU/AI controlled.** Bit 1 = another mode flag (set when 0x3B907E bits 1 or 4 are set), bit 2 = team or partner flag. | V | `sub_001B3110` sets bit 0 when 0x3B9088[slot] is nonzero. `sub_001AD380` merges AI input only when bit 0 is set. 0x3B9C17 |
| +0x9E0 | u32 | **Buttons and direction bits held this update.** | V | `sub_001BAA00`. 0x3B9CC0 |
| +0x9E4 | u32 | Same word, previous update. | V | `sub_001BAA00`. |
| +0x9EC | u32 | Copy of +0x9E0 after button remapping. | V | `sub_001BAA00`. |
| +0x9F0 | u32 | **Newly pressed this update** (bits set now and clear last update). +0x9F4 is last update's value. | V | `sub_001BAA00`. 0x3B9CD0 |
| +0x9FC / +0xA00 | f32 | Left stick X, left stick Y (Y is negated from the pad value). | V | `sub_001BAA00`. 0x3B9CDC, 0x3B9CE0 |
| +0xA04 / +0xA08 | f32 | Right stick X, Y (Y negated). | V | `sub_001BAA00`. |
| +0xB34..+0xB4C | 7 x s32 | Per-character stat block copied from 0x3B9128 + slot*0x1C. | V | `sub_001B2090`. |

## 1. Position and facing

Position is the vec3 at +0x44 (X, Y up, Z), facing is the yaw in degrees at +0x54. Both are
verified as consumers (ring-sector query, model update, root-motion rotation), but I did not
find the function that adds velocity to +0x44, so "this is the logical root position" is
inferred. The animated body-centre point at +0xE8 differs from it while a move plays; the
harness should log both. No float is stored in meters that I could prove; the constants
(18.0 and 12.0 height offsets, 180 and 360 wraps) suggest game units.

## 2. Identity (the fighter ID of `ControllerSetup`)

- The handler is `sub_000558E0`. It converts the four script arguments to bytes, looks up the
  game-setup singleton at 0x2FB148, and writes a 5-byte entry per slot at `this + 0x1AA9 + idx*5`
  through `sub_0001E690` (bytes +0 and +2) and `sub_0001E700` (byte +1). `sub_0001E740` returns
  the table start, and the handler then copies 4 entries (20 bytes) to the global 0x2DDC08.
- Byte +1 of each entry compares against 0x63 (99) as an "unset" marker in `sub_0001E8xx`, and
  all fighter IDs you saw (8..92) are below it, so **I infer byte +1 holds the fighterId** and
  byte +0 the port or device. The stack-slot mapping of arguments to bytes was not resolved with
  certainty.
- The path from that table to the match runs through the match-setup block that `sub_000871F0`
  copies into globals (source pointer at `this + 0x2FF5C`). Verified: `0x3B90B8[slot]` receives
  `setup[+0xA8 + 4*slot] - 1`. `sub_001A4D90` then calls `sub_001B3110(record, slot, 0x3B90B8[slot])`,
  which stores that value at **record +0x2C**. So record +0x2C is the zero-based character index,
  and it is likely `fighterId - 1` of the front-end value (unconfirmed).
- Per-slot tables in the globals block (all dwords, stride 4, four slots): 0x3B9088 CPU flag,
  0x3B9098 pad index (always equal to the slot for active slots, -1 otherwise), 0x3B90A8 and
  0x3B9278 other per-slot values, 0x3B90B8 character index (-1 for unused). Per-slot stat block at
  0x3B9128, stride 0x1C.

## 3. Human versus CPU

- `setup[+0xB8 + 4*slot] != 0` becomes `0x3B9088[slot]` (`sub_000871F0`), then record +0x937
  bit 0 (`sub_001B3110`). The port argument is not stored in the fighter record.
- Human input: the pad poller `sub_0002D9E0` (clones `sub_00079280`, `sub_00079FA0` for other
  screens) fills an 8-entry pad table at 0x3B8F48, stride 0x20, entry = {buttons word, second
  word, left stick X, Y, right stick X, Y, 0, 0}. Device for slot j comes from the controller
  manager (component 0x19 of the singleton at 0x2FB148, `sub_000DCBA0(j)`); a null device is
  skipped. The pad index for a fighter equals its slot (0x3B9098), so slot 0 reads 0x3B8F48,
  slot 1 reads 0x3B8F68, and so on.
- CPU input: the match loop `sub_0008BE60` zeroes the pad entry of every CPU slot that has no
  device, then `sub_001AD380` (reached through `sub_000C89D0`) overwrites it from the AI output
  array at 0x3BFA0C + slot*0xB8 (buttons, then four stick floats) when the AI ready byte
  0x3BF328[slot] is set and record +0x937 bit 0 is set. So both human and CPU input reach the
  record through the same pad table and the same reader.

## 4. Input

`sub_001BAA00` (second call in the early loop of `sub_001A4A30`) is the reader. Behaviour:
1. Shifts +0x9E0 to +0x9E4 and +0x9F0 to +0x9F4.
2. Loads pad word 0 of entry `0x3B9098[slot]`, masked by a per-pad "held since disable" mask at
   0x3B8FC8 (a button stays blocked until released).
3. Loads the sticks (Y negated). If the left-stick magnitude exceeds 0.4 (constant at 0x2F058C),
   computes atan2(x, y) in degrees, `index = floor((180 - angle + 22.5) / 45) & 7`, and ORs the
   direction bits from the table at 0x2EF570: `[1, 9, 8, 10, 2, 6, 4, 5]`, then sets 0x10000. Right stick over the
   same threshold sets 0x20000.
4. `sub_001BA760` remaps six action bits through a per-slot binding table at 0x3B90C8 + slot*0x18
   (clears bits 0x10, 0x20, 0x40, 0x80, 0x1000, 0x2000 and sets the logical ones, logical bit
   values `[0x20, 0x80, 0x40, 0x10, 0x2000, 0x1000]` from 0x2F0644).
5. Stores +0x9EC and computes +0x9F0 = (previous held XOR now held) AND now held.

Bit layout (as seen by the state handlers): 0x0F direction nibble (1, 8, 2, 4 are the four
cardinals in that rotational order; if raw stick up is positive, then 1 = up, 8 = right,
2 = down, 4 = left, **I**), 0x10..0x80 and 0x1000, 0x2000 action buttons (mask 0x33F0 is used by
`sub_001B5090` and `sub_001BA9BA`), 0x100 and 0x200 untouched pass-through bits, 0x10000 left
stick active, 0x20000 right stick active. Which physical button each action bit is was not
resolved.

Update gating: byte 0x3B9054. `sub_001A4A30` returns without updating when any of bits 0x60 is set
and bit 7 is clear (paused or transition); `sub_001BAA00` also checks bit 7. Frame delta is the
float at 0x3B8F2C (initialised to 1.0 by `sub_001A4D90`).

## 5. Distance

No dedicated record-to-record distance helper was found. The auto-target scan `sub_001B9D60`
computes the X/Z distance inline between this fighter's +0xA60/+0xA68 and every other active
fighter's, so the harness should compute `hypot(dx, dz)` itself. Vector library in the 0x1BAxxx
range: `sub_001BAEC0` is a vec3 subtract (verified), `sub_001BAF50` normalises in place
(verified), `sub_001BAE90` and `sub_001BAEF0` look like add and scale (not read),
`sub_001BBA50` is a distance-like helper between two composite shapes (not understood).

## Run-time confirmation plan (slot 0 addresses; add 0x12E8 per slot)

| Field | How to confirm |
|---|---|
| +0x2C 0x3B930C | Start a match with a known `ControllerSetup` ID; read 0x3B90B8[slot]. Expect ID or ID-1. |
| +0x937 bit 0 | 0 for the human on slot 0, 1 for CPU slots. Cross-check 0x3B9088[slot]. |
| +0x44..+0x4C 0x3B9324 | Hold stick right for 30 frames; X (or Z, depending on camera) must change monotonically. Compare against +0xE8 at 0x3B93C8. |
| +0x54 0x3B9334 | Turn with the stick; value should wrap within +-180 and track the stick angle. |
| +0x9E0, +0x9F0 0x3B9CC0, 0x3B9CD0 | Inject a pad press; +0x9F0 is nonzero for exactly one update and +0x9E0 for as long as held. Record each action bit's identity this way. |
| +0x9FC, +0xA00 0x3B9CDC | Full stick up: check the sign of +0xA00 to pin the direction bits. |
| Pad table 0x3B8F48 | A harness can inject input by writing the pad entry before `sub_001BAA00` runs (after `sub_0002D9E0`). |

Unresolved: the movement integrator for +0x44; exact byte layout of the 5-byte entry; link from
the front-end table to `setup[+0xA8]`. Next reads: the state handlers reached through the +0x30
dispatch (search for writes to +0x44 with fadd in the 0x1C0000..0x1D0000 range), and the writer
of the match-setup block behind `this + 0x2FF5C` (grep for stores at offsets 0xA8 and 0xB8).
