# Tutorial fight: how the first task (punch / kick) is marked done

Scope: Story-mode tutorial fight (entered through `Game.EnterTutorialMode`). First step on screen is
"PRESS X TO KICK / PRESS Y TO PUNCH". In the port the fighter punches and kicks, but the tutorial never
advances. This note records what the lifted code says about the task state machine and the completion test.

Method: static reading of `src/recomp/gen/recomp_00NN.c` plus data tables read from `default.xbe`.
Nothing was run. Addresses below are guest VAs (function names `sub_XXXXXXXX` are the guest VA).
Every item is tagged **[confirmed]** (read directly in the lifted C) or **[inferred]** (reasoned from
the code, not directly proven).

## 1. Short answer

* The tutorial task state machine is a small block of globals at **0x3B8598 .. 0x3B85B8**:
  * `0x3B8598` flags word, `0x3B859C` current step index (0..0xB, 0xC = tutorial finished),
    `0x3B85A0` fail/retry counter, `0x3B85A4` previous step, `0x3B85A8` copy of the step at failure,
    `0x3B85AC` intro-delay timer (float), `0x3B85B0` step time-out timer (float),
    `0x3B85B4` player-idle timer (float), `0x3B85B8` seconds-left value shown on the HUD (float). [confirmed]
* **Completion of a task is NOT a button bit, an analog value or a hit-landed event.** It is: "the fighter
  in slot 0 starts executing a particular move type". The move handlers call a tutorial hook,
  `sub_001A29E0(fighter)`, which compares `fighter+0x30` (the fighter's current move-type index) with a
  per-step constant and, if it matches, sets flag bit `0x10` in `0x3B8598`. [confirmed]
* Step 0 (the punch/kick prompt) completes when `fighter+0x30 == 0x45` **or** `== 0x49`. Step 1 (hard
  attack) completes on `0x46` or `0x49`. One strike is enough for step 0; the code does not require both a
  punch and a kick. [confirmed]
* Nothing on the advance path reads audio state (speech finished, stream state) or any HUD animation
  state. `EVTMAN_LASTTUTORIAL` is only an allocation tag string, unrelated. [confirmed]

## 2. Where the state lives and who drives it

| Item | Address | Notes |
|---|---|---|
| Tutorial flags | `0x3B8598` (dword) | see bit table in section 3 |
| Current step | `0x3B859C` (dword) | 0..0xB, then 0xC = finished |
| Fail counter / prev step / fail step | `0x3B85A0` / `0x3B85A4` / `0x3B85A8` | |
| Timers (floats) | `0x3B85AC` intro, `0x3B85B0` step time-out, `0x3B85B4` idle | advanced by `0x3B8F2C * 1.2` per update |
| Seconds-left (float) | `0x3B85B8` | `(899.4 - 0x3B85B0 + 60) / 60`, drawn by `sub_000B54E0` |
| Tutorial HUD object | global pointer `0x39D8E0` | HUD+0x12D0 = bitmask of strings shown, +0x12D4 / +0x12CC = RIGHT/WRONG/COME ON banner state and its 200-tick timer |
| Fighter array | `0x3B92E0`, stride `0x12E8`, 4 entries, end `0x3BDE80` | loop in `sub_001A4A30`; entry skipped when `fighter+0x28 == -1` |
| Per-player stat table | `0x3BE160`, 0x4C dwords per player | `sub_001A6870(fighter, statId)`, indexed by `fighter+0x28` |

Functions:

| Function | Role |
|---|---|
| `sub_001A2840` | Reset block to 0. Arms the tutorial only if `MEM32(0x3B9078) == 2 && MEM32(0x3B919C) == 1`; then flags = 3 (active + intro delay), step 0. Called from `sub_001A4D90` <- `sub_000871F0` (CLogic match start). [confirmed] |
| `sub_001A2BF0` | Per-frame state machine update: intro delay, step start, time-out, idle prod, **advance on completion flag**. Called from `sub_001A4900(dt)` (every frame) <- `sub_00087700` (CLogic frame update). [confirmed] |
| `sub_001A29E0(fighter)` | **Completion test**: sets flag 0x10 when the move type matches the step. [confirmed] |
| `sub_001A2B30(fighter, x)` | Failure test (sets flag 0x20 when the wrong move is used). Only active for steps 3..11. [confirmed] |
| `sub_001A29B0(fighter)` | Activity test: sets flag 0x40 when `fighter+0x9F0 & 0x220F0` (player is doing something); resets the idle timer. Called per fighter from `sub_001A4A30`. [confirmed] |
| `sub_001A28A0` | Per-step setup run at step start (camera/HUD values for steps 9, 0xA; returns early for 0xB). [confirmed] |
| `sub_000BD860` | Event poller (`sub_00011CD0` loop): diffs live blocks against a previous-frame snapshot (`sub_000BDF40` copies `0x3B8598..0x3B85B8` into it) and posts events with `sub_000BD720`. Posts `0xF0000034` (new step, arg = step, or 0xC when finished), `0xF0000035`, `0xF0000036` (arg 0x400 / 0x1000 / 0x2000 / 0x4000). [confirmed, snapshot pointer layout inferred] |
| `sub_000B76A0` | Tutorial HUD constructor, registers handlers `sub_000B70F0` (0xF0000034), `sub_000B7420` (0xF0000035), `sub_000B7440` (0xF0000036), `sub_000B6F90`/`sub_000B6FA0` (0xF0000011/13). Created from `sub_0002D1C0` ("TUTORIAL HUD") and `sub_0007A0C0`. [confirmed] |
| `sub_000B70F0` | HUD handler for new step: switch on step (0..17) and set bits in HUD+0x12D0. [confirmed] |
| `sub_000B6390` | HUD text builder; reads the string-key table at 0x2E24D8. [confirmed] |
| `sub_0008BE60` / `sub_00088C60` -> `sub_00033380` | CLogic tail turns flag bits 0x2000 / 0x4000 / 0x400 / 0x1000 into tutorial speech requests (ids 1, 2, 3, `0xA + step`). Fire and forget through an indirect call at `MEM32(0x3ADB7C)`; nothing comes back. [confirmed] |

### The string table at 0x2E24D8 (19 entries)

It is the list of HUD text keys (TUTOR_PUNCN, TUTOR_KCK, TUTOR_HRDATTK_XBOX, TUTOR_GRAB, ... TUTOR_COMEON).
It is indexed by **bit position** in HUD+0x12D0, not by step. Step 0 turns on bits 0 and 1, which is why the
first screen shows the punch and the kick prompt together. Mapping done in `sub_000B70F0`: [confirmed]

| Step | HUD+0x12D0 bits set | Strings |
|---|---|---|
| 0 | 0x1 and 0x2 | PUNCN, KCK |
| 1 | 0x4 | HRDATTK_XBOX |
| 2 | 0x8 | GRAB |
| 3 | 0x10 | PREFORMATTK |
| 4 | 0x20 | HRDGRPPLE_XBOX |
| 5 | 0x40, 0x80 or 0x100, chosen by `MEM32(game_mgr + 0x1AA4)` (0..4) | PREFORMATTK / PREFORMSUBMIT / LANDATTK |
| 6 | 0x200 | (index 9) |
| 7 | 0x400 | THRWOPP |
| 8 | 0x800 | BLCK_XBOX |
| 9 | 0x1000 (also posts 0xF1000004 / 0xF0000014) | BLAZE |
| 10 | 0x2000 | (index 13) |
| 11 | 0x4000 | DANGER |
| 12 (finished) | cleared | - |

Banner events (`sub_000B7440`, arg of 0xF0000036): 0x2000 -> RIGHT, 0x4000 -> WRONG, 0x400 -> COME ON,
0x1000 -> state 0, anything else -> state 5. [confirmed]

## 3. Flags word 0x3B8598

| Bit | Meaning | Set by | Used by |
|---|---|---|---|
| 0x1 | tutorial active | `sub_001A2840` (init) | every tutorial function bails out if clear |
| 0x2 | intro delay running | init (flags = 3) | `sub_001A2BF0`: while set, adds `dt*1.2` to `0x3B85AC`; when it exceeds 60.0 the bit is cleared and bit 0x4 set |
| 0x4 | start the step now | intro delay end, completion, failure | `sub_001A2BF0` calls `sub_001A28A0`, then sets flags = 0x809 (0x1809 for step 0 when fail counter <= 0) |
| 0x8 | step is live / waiting for the player | step start (0x809) | `sub_001A2BF0` only evaluates time-out / idle / completion while this is set |
| 0x10 | **task done** | `sub_001A29E0` | `sub_001A2BF0` consumes it (advance) |
| 0x20 | task failed / timed out | `sub_001A2B30`, step timer > 899.4 | `sub_001A2BF0`: bumps fail counter, sets 0x4004, rolls the step back for steps 3/5/7/10/11 |
| 0x40 | player active | `sub_001A29B0` | `sub_001A2BF0`: resets idle timer; when idle timer > 360.0 sets 0x400 ("come on") |
| 0x80 | tutorial finished | advance past step 11 | event 0xF0000034 with arg 0xC |
| 0x400 / 0x800 / 0x1000 / 0x2000 / 0x4000 | edge flags that the event poller turns into HUD events and speech: 0x800 = new step text, 0x2000 = success, 0x4000 = failure, 0x400 = idle prod, 0x1000 = first-time intro line | `sub_001A2BF0` | `sub_000BD860`, `sub_0008BE60` |

All [confirmed] from `sub_001A2BF0` (recomp_0012.c lines ~7359-7777) and `sub_001A29E0` /
`sub_001A2B30` / `sub_001A29B0`.

Timer units: `0x3B8F2C` is the `dt` argument of `sub_001A4900`, which comes from `MEM32(CLogic+4)`; `sub_000871F0`
initialises that to 1.0f. So the intro delay is about 50 frames (60 / 1.2), the step time-out about 750
frames (899.4 / 1.2, roughly 12.5 s at 60 Hz) and the idle prod about 300 frames. [confirmed constants,
unit interpretation inferred]

## 4. The completion test, exactly

`sub_001A29E0(fighter)` (recomp_0012.c line ~6751): [confirmed]

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Where the constants come from (all [confirmed]): the fighter dispatcher `sub_001B54D0` builds a local table of
move handlers and calls `table[MEM32(fighter+0x30)](fighter)`. Mapping handler -> index, derived from the
table offsets: `0x1C85D0` = 0x45, `0x1C8840` = 0x46, `0x1C8A00` = 0x47, `0x1C8C00` = 0x48, `0x1C8D80` = 0x49,
`0x1D3800` = 0x1F, `0x1D11F0` = 0x21, `0x1D41D0` = 0x2E, `0x1DB1B0` = 0x34, `0x1D9650` = 0x3F,
`0x1D8D00` = 0x4F, `0x1D87B0` = 0x55, `0x1D75C0` = 3. These are exactly the eleven callers of
`sub_001A29E0` (`1C85D0, 1C8840, 1C8D80, 1D11F0, 1D3800, 1D41D0, 1D75C0, 1D87B0, 1D8D00, 1D9650, 1DB1B0`).
So the hook is called from inside those move handlers; `fighter+0x30` is the move type, `fighter+0x34` the
phase inside the move.

How the hook is reached for step 0, handler `sub_001C85D0` (move 0x45), phase 1 (`fighter+0x34 == 1`),
recomp_0012.c lines ~115304-115430: [confirmed]

1. `sub_001C5090(fighter)`, then `sub_001C6440(fighter, 1, 0)` must return a non-zero attack candidate.
2. `sub_001C6CD0(fighter, candidate, 1, 0)` executes it (sets `fighter+0x41C |= 4`).
3. `MEM8(fighter+0x41C) & 4` must be set.
4. `MEM16(fighter+0x41C)` must have none of bits 0x60 set.
5. If bit 0x10 of `fighter+0x41C` is set the hook is skipped (that branch sets `fighter+0x421 |= 1` and just
   advances the phase). Otherwise: `fighter+0x420 |= 1`, two stat bumps via `sub_001A6870(fighter, 0xF)` and
   `sub_001A6870(fighter, 0x25 or 0x26)`, then `sub_001A29E0(fighter)`, then the phase advances.

The advance itself, `sub_001A2BF0` at the 0x10 test (lines ~7722-7770): when flag 0x10 is set and the
machine is in its live state (bit 0x1 set, bits 0x2 and 0x4 clear, bit 0x8 set, and the 0x20 time-out branch
not taken this frame), it stores `0x3B85A4 = step`, `step++`, `0x3B85A0 = 0`, and sets flags to 0x2005
(success + start next step + active) or, after step 11, 0x81 (finished). Next frame bit 0x4 starts the
following step (flags 0x809), the poller sees 0x800 and 0x2000 rising and posts the HUD events and speech
requests. [confirmed]

## 5. Is advancing gated on anything unrelated to the player?

* Speech / audio: no. Speech is requested by `sub_00033380` from the CLogic tail (`sub_0008BE60`,
  `sub_00088C60`) based on the flag bits, through a one-way indirect call. No audio state, callback or
  "finished" flag is read by `sub_001A2BF0`, `sub_001A29E0` or `sub_000BD860`. [confirmed]
* HUD animation: no. The HUD only receives events; its +0x12CC counter (0xC8) just times the
  RIGHT/WRONG banner. Nothing feeds back into `0x3B8598`. [confirmed]
* Script / event manager: `EVTMAN_LASTTUTORIAL` (0x2AB6EC) is only the tag string of a 0x24-byte allocation
  in `sub_000BE0F0`. The event manager (`sub_000BD610` register, `sub_000BD6A0` unregister, `sub_000BD720`
  post, `sub_000BE030` declare id) is just the transport between the poller and the HUD. [confirmed]
* Time based gates that are unrelated to the player, but only affect when a step becomes live (not
  whether it can complete): the intro delay (`0x3B85AC` > 60.0, bit 0x2 -> 0x4) and the step time-out
  (`0x3B85B0` > 899.4 sets 0x20 and restarts steps 0/1/2/4/6/8 or rolls back 3/5/7/10/11). If the step text is
  on screen (it is), the intro delay has already elapsed. [confirmed]

## 6. Full list of conditions on the path

Arming (once, at match start)

1. Match info mode: `sub_000871F0` copies the match-info block (`CLogic+0x2FF5C`) to globals
   `0x3B9078..`. A tutorial match arrives as mode 5 and is rewritten to `0x3B9078 = 2`, `0x3B919C = 1`
   (code at lines ~8488-8501). [confirmed code; that mode 5 means "tutorial" is inferred]
2. `sub_001A2840` arms only if `MEM32(0x3B9078) == 2 && MEM32(0x3B919C) == 1`. [confirmed]
   Evidence it is satisfied in the port: the step-0 text appears, and that needs flags 0x1 and a finished
   intro delay. [inferred]
3. Front end side: `Game.EnterTutorialMode` -> `sub_000475F0` registers `sub_000461A0`, which calls
   `sub_0001E2E0(mgr_0x18, 1)` = `MEM8(mgr+0x1AA8) = 1`. [confirmed]

Per frame

4. `sub_001A4900` -> `sub_001A2BF0` must run each frame with a sane `dt` (CLogic `+4`, 1.0f). [confirmed
   code; port behaviour inferred OK because step 0 started]
5. Flags must be in the live state (0x1 and 0x8 set, 0x2 and 0x4 clear) for a 0x10 to be consumed. [confirmed]

Completion hook (step 0)

6. `MEM8(0x3B8598) & 1`. [confirmed]
7. `MEM32(fighter+0x28) == 0`: the fighter must be the one with slot id 0. `fighter+0x28` is -1 for an empty
   fighter slot and otherwise the slot id; the same field indexes the per-player stat table. [confirmed
   usage; "slot id" meaning inferred]
8. `MEM32(0x3B859C) == 0` at that moment. [confirmed]
9. `MEM32(fighter+0x30) == 0x45` or `0x49`, i.e. the fighter must be inside handler `sub_001C85D0` (0x45) or
   `sub_001C8D80` (0x49) when the hook runs. [confirmed]
10. Inside handler 0x45, phase 1: attack candidate non-zero, `fighter+0x41C & 4`, no `0x60` bits,
    `fighter+0x41C & 0x10` clear. [confirmed]
11. Nothing about X vs Y, analog value, button bit, hit landed, or target hit. The input only matters
    indirectly through which move type the fighter engine selects. [confirmed]

Not gating

12. Audio finished, HUD animation finished, EVTMAN: not on the path. [confirmed]

## 7. Most likely blocking conditions in the port (ranked, all inferred)

The fighter visibly punches and kicks, so input -> fighter command already works. What is left:

1. **The human fighter is not slot id 0** (`fighter+0x28 != 0`), or the human's fighter is a different
   entry than the one the tutorial expects. Every tutorial hook (`29E0`, `2B30`, `29B0`) returns immediately
   for `fighter+0x28 != 0`, so no step could ever complete, and the idle-prod would also never be reset.
   Check fighter 0 at `0x3B92E0`: `+0x28` should be 0.
2. **The punch/kick runs under a move type other than 0x45 / 0x49** (for example 0x47 / 0x48, or a
   different handler because no valid target / candidate was found). Then `fighter+0x30` never equals
   0x45/0x49 at the hook. Check `fighter+0x30` (`0x3B9310` for fighter 0) while pressing X / Y.
3. **Phase-1 gating in handler 0x45**: `sub_001C6440` returning 0 or `fighter+0x41C` bits (4, 0x10, 0x60)
   in the wrong state, so `sub_001A29E0` is skipped even though the animation plays.
4. Flag word stuck so that 0x10 is never consumed (bit 0x2 or 0x4 never cleared, or bit 0x8 not set, or
   0x20 time-out firing before the player acts). Check `0x3B8598`.

How to confirm quickly at run time (read-only): sample `0x3B8598`, `0x3B859C`, `0x3B85A0`, `0x3B85AC`,
`0x3B85B0`, and fighter 0's `+0x28`, `+0x30`, `+0x34`, `+0x41C` with `scripts/peek-guest.py`. Expected on
a healthy run, step 0: flags `0x809` (or `0x1809`), step 0. Pressing a strike should briefly show bit 0x10,
then flags `0x2005`, step 1, then `0x809` with step 1. Interpretation of an unhealthy run:
* flags stay `0x809`, step 0, `fighter+0x30` never 0x45/0x49 -> cause 2 or 3.
* flags stay `0x809`, `fighter+0x28 != 0` -> cause 1.
* flags `0x829` / `0x4004`-style values appearing every ~12.5 s -> the step time-out is firing, so the hook
  never ran.
* flags show `0x819` and stay there -> the hook worked but `sub_001A2BF0` is not consuming it (cause 4).

## 8. Caveats

* The name "fighter" and the field meanings (`+0x28` slot id, `+0x30` move type, `+0x34` phase, `+0x41C` attack
  result flags, `+0x9F0` input flags) are inferred from usage, not from symbols.
* The mode-5 -> tutorial mapping and the exact layout of the event-poller snapshot (`sub_000BD860` /
  `sub_000BDF40`) were not traced to the end.
* The meaning of move types 0x45..0x49 (which is the light punch, light kick, etc.) was not resolved; only
  that 0x45 and 0x49 satisfy step 0 and 0x46 / 0x49 satisfy step 1.
* The "after you do both" behaviour on console is not what the code does for step 0: one move of type
  0x45 or 0x49 is enough.

## Outcome (main agent, 2026-10-01)

Measured live (0.02 s samples of `0x3B8598`, `0x3B859C` and both fighters' `+0x28/+0x30/+0x41C`): fighter 0
did enter move `0x45` on every X/Y press and the flags cycled `0x9 -> 0x402D` every 12.5 s, but bit `0x4` of
`+0x41C` never appeared, and `sub_001C85D0` only calls the hook `sub_001A29E0` when it is set. None of the
ranked guesses above was the cause. `sub_001C6CD0` sets that bit on a path chosen by

    and eax, 400h / push esi / mov [esp+8], eax / mov eax, [esp+29Ch] / push edi / je ...

and the lifter emitted the `je` as `if (eax == 0)`, reading the pointer the `mov` had just loaded. Fixed in
the lifter (patch 0090: the result is copied to `_fres` before the overwrite); after it the same trace shows
`+0x41C = 0x2000E`, flags `0x19 -> 0x2005`, step 1. See PROGRESS §6, 2026-10-01.
