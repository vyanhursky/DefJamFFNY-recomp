# Simulation tick of Def Jam: Fight for NY (static read of the lifted code)

Scope: a read-only look at the lifted C and the XBE image (for vtable and float constants). Nothing was run.
All addresses are guest addresses. "Verified" means read in the lifted code; "inferred" means a reading of shapes.
Confidence is high / medium / low per answer.

## Short answer for the harness

* The fight advances in **steps**. A step is one pass of `sub_0008BE60` (the match object "CLogic", object at `0x349760`)
  and, in the live-fight states, one call of `sub_00087700` -> `sub_001A4900` + `sub_001A4A30`.
* A step is **not** tied to a presented frame. The main loop runs **0 to 4 steps per outer iteration** (hard cap 4),
  one step per queued 60 Hz "frame record". Count entries to `sub_00087700` to count fight steps (see the caveats in Q3).
* The step is not seconds-based: the per-step scale is 1.0 (0 when paused), the real elapsed time is discarded.

## Q1. Call chain and where the fixed step lives (confidence: high for the chain, medium for the producer)

Chain, top to bottom (verified by `callers.py` and reading each caller):

1. `sub_00011500` (main) calls the main loop `sub_00011CD0` once (`sub_001F62E3` -> main).
2. `sub_00011CD0` is the loop. Before looping it calls `sub_000D7560(frameObj, 0x3C)`: it stores `frameObj` in `0x3A017C`
   and calls the object's vtable slot +0x10 with **60**. The object (global registry slot `0x27`, vtable `0x2B3AE0`) is the
   frame / input-record queue.
3. Each outer iteration: `sub_000D75E0(frameObj)` decides whether a step is owed. While it returns non-zero the loop runs
   one step: `sub_0002C530(0x33DB90)` (dt), `sub_000DD930`, **`sub_00077040(machine, dt)`**, then
   `sub_000BD860`/`sub_000BDF40`/`sub_0001A240` and re-asks `sub_000D75E0`.
   After the inner loop ends it runs the tail (`sub_000D02A0` -> `sub_000D0C20`, `sub_00077740`), which I read as render/present
   (inferred, not traced). So there is one render per outer iteration and 0..4 steps before it.
4. `sub_00077040` runs a 4-state machine on `machine+0x24` (load/start/stop) and then, under lock `0x2FB000`, calls the current
   screen's **vtable slot +0xC** with dt. The XBE vtables confirm slot +0xC = `sub_00079B60` (vtable ~`0x29D604`) and
   `sub_0007A8F0` (~`0x29D610`). `sub_00077A40` has the same shape but I found no vtable entry for it.
5. Each of those three screen updates calls `sub_0003D960(dt)` (global timers and a counter, Q3) and the match object update
   `sub_0008BE60` (`sub_00077A40` reaches it through `sub_0002DFF0`).
6. `sub_0008BE60(this = 0x349760, dt)` is a 16-way switch on `CLogic+0x2D820`.
   **`sub_00087700` is called only from here, in three switch arms**: state 4 (also runs `sub_00089650` first, then falls into
   state 5), state 5, and state 8. State 8 is the live fight (`sub_0008AB00` sets it); `sub_0008AB00` moves to state 9 on
   its end-of-fight tests (reads of `0x3BE0F4/F8`, not decoded). In states 4/5 a counter at `CLogic+0x2D86C` runs to 60 and then
   `sub_00088FF0` is called (the 60-step lead-in; meaning of that call not decoded). State 9 and the other states do not call
   `sub_00087700` directly.
7. `sub_00087700(CLogic, dt)` calls, in order: `sub_001A2F50`, `sub_001A4900(CLogic+4)`, **`sub_001A4A30`**, `sub_001A93B0`,
   `sub_001A8E00`, `sub_000B03D0`, `sub_001A2F60`, `sub_001A3D50(0x340D58)` (copies the match state into a snapshot buffer,
   probably a replay/recorder, inferred), `sub_000AC590`. Then it forces `CLogic+0x2D820` to 0xE/0x10 when `CLogic+0x2B9EC`
   has bit 0x400/0x800 (the "HI8 test 4 / 8" at its end).

Where the accumulator is: `sub_000D75E0` is the fixed-step gate.
* A ring of 10 records (0x260 bytes each, tail `+0x17C8`, head `+0x17C4`, **count `+0x17CC`**) lives in the frame object.
  Zero count means no step. Each call consumes one record (via `sub_000D7960`) and decrements the count.
* With `+0x1A54 == 0` it returns "run a step" for the first 4 calls of an iteration (counter `+0x1A5C` 1..4) and "stop" on the
  5th: **cap of 4 steps per outer iteration**. With `+0x1A54 != 0` it alternates run/stop, which looks like a half-rate mode,
  but the only write to `+0x1A54` in the lifted code is the constructor's zero, so nothing in the lifted code switches it on (unknown).
* Producer (verified shapes, inferred role): thread proc `sub_000D7700` waits on the event at `frameObj+0x1A60`, then calls
  `sub_000D7AE0`, which snapshots the four pad slots (0x94 bytes each plus a header) into the ring. The event is signalled by
  `sub_000D7EA0`, which re-arms a kernel timer through `sub_000D7DE0` (`sub_00216410`) and signals. `sub_000D7DA0(60)` sets the period;
  I read this as a 60 Hz timer. It is only reached indirectly. The earlier worklog (patch 0074) matches: when the timer ran
  too fast the fight ran exactly 4 steps per presented frame, i.e. this cap.
* If the ring is full (10) the oldest record is dropped. So a slow host loses steps rather than queuing forever.

Answer: the fighter update runs a **variable number (0..4) of times per presented frame**, once per consumed 60 Hz record.
The dt handed down is a constant 1/60 (`0x28C798`; `sub_0002C530` also computes the real elapsed time but returns the constant).
The fight itself ignores that dt: it uses `CLogic+4` (see Q3).

Confirm at run time: count entries of `sub_00087700` and of `sub_000D7960` per second and per presented frame; watch
`frameObj+0x17CC` (read the object address from `0x3A017C`) never exceeding 10 and `+0x1A5C` never exceeding 4.

## Q2. Bits of the dword at `0x3B9054` (confidence: medium for 0x04/0x08, low for 0x20/0x40/0x80)

It is a dword, not a byte (written with 32-bit ORs up to bit 0x20000). The match start `sub_001A4D90` zeroes the whole
block `0x3B8F28..0x3B9074` and sets the word to 1. **Every step `sub_001A4900` keeps only the bits in mask `0xFFFE017F`**,
i.e. it clears bit 0x80 and bits 0x200..0x10000 (per-step event bits) and keeps 0x01-0x40, 0x100 and 0x20000 and up.

| Bit | What the code shows | Evidence | Verdict |
|---|---|---|---|
| 0x01 | "match running" until the first update | set by init; `sub_001A4900` phase 0 clears it and sets 0x02 | medium |
| 0x02 | the start-up phase is over | set in `sub_001A4900` phase 0; gates the 0x08 transition below | medium |
| 0x04 | **end-of-fight slow motion is active** | set by `sub_001A6A80` (an event recorder: it appends 16-byte records at `0x3BE130`) when its flag argument has bit 0, together with a call to `sub_000442E0`. While 0x04 is set `sub_001A4900` accumulates raw dt in `0x3B9064` and writes the per-step scale `0x3B8F2C` = (0.1 + 0.6 * min(1, `0x3B9064`/60)) * dt (floats `0x2F0580/84/88`, `0x296DDC`). After `0x3B9064` reaches 300 (`0x28C2D4`) and bit 0x02 is set, 0x08 is set. `sub_001B3E00` is a one-line accessor returning this bit. Never cleared except by a new match. The name "slow motion" is my reading of the ramp; the code does not say it is a KO cinematic | medium |
| 0x08 | **match decided / over** | set by `sub_001A7140` (per-fighter KO tests on bit 8 of the flag words at fighter+0x932; counts losers per team; returns 1) and by three tiny setters (`sub_001A46F0`, `sub_001D1140`, `sub_001DA400`); `sub_001A4900` moves its phase counter on when it sees it | medium |
| 0x20, 0x40, 0x80 | **no setter found**. The word is only ever OR-ed with constants 0x04, 0x08, 0x200, 0x400, 0x800, 0x1000, 0x2000, 0x4000, 0x8000, 0x10000, 0x20000 | The early-out: `sub_001A4900` (tail) and `sub_001A4A30` (start) test `& 0x60`; if non-zero and the sign bit (0x80) is clear they **skip the match-phase logic / the main fighter pass**. 0x80 overrides that and is wiped every step. `sub_001BAA00` (per-fighter input copy) also tests the sign bit. Reads of `& 0x4` also sit in `sub_001A53E0`, `sub_001A5730`, `sub_001B50D0`, `sub_001B54D0` | low |
| 0x200-0x10000 | per-step event bits from `sub_001A6A80` and `sub_001D87B0` (0x200) | cleared each step by the mask | medium |

Pause: not in this word. The pause is the **scale at `CLogic+4` (`0x349764`)**: `sub_0007C2F0` (reads pad buttons) calls
`sub_00044C10` with 0 in one branch and 1.0 in another; `sub_0008D5C0` and `sub_000AC1F0` also set it. `sub_001A4900` copies it into
`0x3B8F2C` and the round clocks stop advancing at 0, but `sub_00087700` and `sub_001A4A30` still run (the step still happens).
Cutscene/intro: nothing in this word. The only lead-in I found is the 60-step counter in CLogic states 4/5 and the match phase
counter `0x3B8F30` (0 init, 1 running, 2 ending, 3 done), advanced by `sub_001A4900`. Match over: bit 0x08 plus that phase counter.
Confirm at run time: log `0x3B9054` once per step (watch `sub_001A4900` entry/exit) across a KO and a pause.

## Q3. Counters and time scale (confidence: high for addresses, medium for roles)

No counter that counts only fight steps exists. The nearest candidates:

| Address | What | Written by | Notes |
|---|---|---|---|
| `0x340538` (lo) / `0x34053C` (hi) | **64-bit counter, +1 per call of `sub_0003D960`** | `sub_0003D960` only (end of the function) | one call per screen update, so once per step in every screen, not only fights. Skipped when the byte `0x340540` is non-zero (set to 1 by an init-failure path in `sub_0003C6E0`; I read it as "module disabled"). Readers: `sub_00036FB0`, `sub_000379E0`, `sub_0003C400`. No reset found in the lifted code except possibly an init, so use deltas |
| `0x3B8F30` | match phase 0..3 | `sub_001A4900` | not per step |
| `0x3B8F44` | parity toggle (xor 1 per main pass of `sub_001A4A30`) | `sub_001A4A30` | gives step parity while the main pass runs |
| `CLogic+0x2D86C` | counts steps in states 4/5 up to 60 | `sub_0008BE60` | the lead-in length |
| `[0x805CD4B0+0x74C]` | counter in the world/effects object, +1 per `sub_000B9E80` | `sub_000B9E80` | from the worklog, object is on the heap |
| `0x3B903C` / `0x3B904C` | round clock floats | `sub_001A7530` | += `0x3B8F2C` * 1.2 per step, only in match phase 1 |

Time scale / delta:
* `0x3B8F2C` = per-step scale used by the fighter update. Written by `sub_001A4900` (and zero/1.0 at match init). It is the
  dt argument (`CLogic+4`, 1.0 normally, 0 paused) times the 0.1..0.7 ramp when bit 0x04 is set.
* `0x349764` = `CLogic+4`, written by `sub_00044C10`; set to 1.0f in `sub_000871F0` at match start.
* `0x3B8F28` is 1.0f at init (second scale, not traced).
* Seconds-based dt (1/60, `0x3C888889`) goes to screen updates and `0x33EA60` (game-time accumulator in `sub_0003D960`).

Confirm at run time: sample `0x340538` and count `sub_00087700` entries over the same 10 s; the ratio tells whether the counter
is per step or per screen update. Pause with the Start button and see `0x349764` go to 0.

## Q4. Random numbers (confidence: high that it is used in the step, medium on the seed)

Yes. A shuffled-table linear congruential generator:
* multiplier `0x5D588B65` (1566083941), additive term = a stored odd value, state at **`0x3C1404`**, additive term at **`0x3C1400`**,
  32-entry float table at `0x3C1408..0x3C1488` (scaled by 2^-32, `0x2A8200`).
* `sub_001BC690(seed, inc)` seeds: stores the additive term, fills the table. Called only by `sub_001A4D90` (match start),
  from `sub_000871F0`, which passes `CLogic+0x2D874` and `CLogic+0x2D878`.
* `sub_001BC6E0` draws one float (picks table slot from the state). Wrappers `sub_001BC730` / `sub_001BC770`. Called from the step:
  `sub_001A4900` -> `sub_001B5D80` and `sub_001A94B0`, `sub_001A4A30`, `sub_001A7530` and many fighter functions (`sub_001B5AF0`,
  `sub_001C*`, `sub_001D*`) per the caller walk. Two other uses of the same multiplier (`sub_000AA0D0`, `sub_000AA2B0`) are separate
  generators (not traced).
* Seed source: `sub_0008BB00` (match setup, state 0xF) sets `CLogic+0x2D878` to the **low 32 bits of `rdtsc`** and
  `CLogic+0x2D874` to the old value plus `0x7714F95`. So fights are **not deterministic** unless the recompiler's
  `xbox_ReadTimeStampCounter` is made deterministic. For reproducible tests, hook it (or set `0x2D874/0x2D878` before
  `sub_000871F0` runs). Not verified at run time.

## What I could not settle
* The producer rate (60 Hz) and the half-rate/30 Hz menu mode (`frameObj+0x1A54`): shapes only.
* The setters of bits 0x20/0x40/0x80 of `0x3B9054` (none found by constant; an aliased pointer into the block is possible).
* Which screen vtable (`sub_00079B60` vs `sub_0007A8F0`) is the in-fight screen; both reach `sub_0008BE60`.

## Suggested test hooks (cheapest first)
1. Count entries of `sub_00087700` (exact fight steps; excludes states other than 4/5/8).
2. Count `sub_000D7960` (queue consumption) and compare with a `sub_00011CD0` iteration count to get steps per iteration.
3. Watch `0x3B9054` and `0x349764` for KO/slow-mo/pause; read `0x3B8F30` for match phase; read `0x3B903C` for the round clock.
4. Make `rdtsc` deterministic before `sub_000871F0` if the test needs repeatable randomness.
