# Why a scripted fight does not replay identically (static read)

Scope: read-only look at the lifted C, the XBE data sections and the toolkit's rdtsc implementation. Nothing was run or
built. Addresses are guest addresses. "Verified" = read in the lifted code (or computed from it); "inferred" = a reading of
shapes. Call-graph claims come from a direct-call walk of `src/recomp/gen` plus the fighter handler table described in Q3;
indirect calls other than that table and in-function switch tables are not covered.

## Short answer

The CPU fighter's decisions are drawn from **four per-fighter random generators at `0x3BFC70 + slot*0x88`, which are
seeded from `rdtsc` at the start of every match**. The runtime's `rdtsc` is the host performance counter, so the seed differs
on every run. The match generator the harness logs and overrides (`0x3C1404`) is a different generator and was never drawn
in the first 79 steps. Confidence: high that this is a real source of divergence; medium-high that it is the one seen at
step 31 (not yet measured at run time).

## Q1. The generators

All of them use the multiplier `0x5D588B65` plus an additive term, and a 32-entry float table with a
Bays-Durham shuffle (each draw returns an old table entry and refills it). There are **three kinds of instance**, plus an
unrelated C runtime one. Confidence for this section: high (all read).

**A. The match generator** (global, single instance).
* State word `0x3C1404`, additive term `0x3C1400`, table of 32 floats `0x3C1408..0x3C1487` (scaled by 2^-32, constant at `0x2A8200`).
* Seed `sub_001BC690(seed, increment)`: stores the increment at `0x3C1400`, then runs 32 LCG steps writing one float per step; the
  state ends as the 32nd value. Only caller `sub_001A4D90` (match start), reached from `sub_000871F0`, which is called by the match
  setup functions `sub_000891A0` and `sub_0008B730`. Arguments are `CLogic+0x2D874` (seed) and `CLogic+0x2D878` (increment).
* Draw `sub_001BC6E0`: advances the state **twice** per draw (the first output picks table slot = low 5 bits, the second becomes
  the new state at `0x3C1404` and the new float for that slot), returns the old slot value in st(0). So a draw changes exactly two things: `0x3C1404`
  and one table entry `0x3C1408 + 4*idx`. There is no separate index or counter.
* Siblings: `sub_001BC730(p)` chance test (inferred), `sub_001BC770(n)` integer 0..n-1 (inferred), `sub_001BC7B0` weighted pick with an
  inline copy of the draw. `sub_001BC8E0` is not a draw.
* **Verified by computation:** running the seeding rule with seed 124866453 (`0x7714F95`) and increment 942483619 (`0x382D28A3`)
  gives final state `0x464CCEB5`, exactly the value sampled at every step up to 79. So this generator was never drawn from at
  match start nor in the first 79 steps. That resolves the earlier puzzle: nothing drew, rather than the word being the wrong one.
* Where the seed values come from: the constants are written by the `CLogic` constructor `sub_0008CB90` (`0x2D874 = 0x7714F95`,
  `0x2D878 = 0x382D28A3`). So **the first match after process start always has this seed**, which is why three runs agreed. The
  tail of `sub_0008BB00` (match setup) then rewrites them for the next match: `0x2D878 = rdtsc low 32 bits`, `0x2D874 = old 0x2D878 + 0x7714F95`.
  A second match in one process is therefore time-seeded. This corrects `simulation-tick.md` Q4, which implied every match was time-seeded.

**B. The object-form generator** (same algorithm, instance data in a larger object: table at +0x00..0x7F, state at +0x80,
additive term at +0x84). Seed `sub_000AA0D0(state, additive)` (thiscall), draw `sub_000AA2B0`, wrappers `sub_000AA300` (chance) and
`sub_000AA340(n)` (integer 0..n-1). Instances found:

| Instance | State / additive | Seeded in | From | Drawn by |
|---|---|---|---|---|
| **Per-fighter AI generators**, 4 x 0x88 bytes from `0x3BFC70` | `0x3BFCF0 + slot*0x88` / `+4` (slot 1: `0x3BFD78`/`0x3BFD7C`) | `sub_001AD220` (called by `sub_000C8820`) | **`rdtsc` low 32 bits**: state = (rdtsc>>16)+slot, additive = (rdtsc&0xFFFF)+slot | AI: `sub_001ADEB0` (weighted pick), `sub_001AE0C0`, `sub_001AF9E0` |
| Global utility object `0x39C0E0` | `0x39C160` / `0x39C164` | `sub_0008BB00` start | `CLogic+0x2D874/2D878` (constants on the first match) | `sub_000AC590` subtree in the step tail (`sub_000AACA0`, `sub_000ABB70`) and about 25 non-step callers (menus, UI, camera-like code) |
| `CLogic+0x2D87C` (`0x376FDC`) | `0x37705C` / `0x377060` | `sub_0008ABF0` (reached from `sub_0008BB00`) | **`rdtsc`**: state = rdtsc>>16, additive = rdtsc&0xFFFF | `sub_00088630`, `sub_00088760`, `sub_00088E80`, `sub_000898E0`, `sub_0008A300` (CLogic pre-fight states, not the fight step) |
| Object at `sub_00081240`'s `this+0xE18` | `+0xE98/+0xE9C` | `sub_00081240` | `this+0xE10/0xE14` | not traced (front-end / setup side) |

**C. C runtime `rand`/`srand`.** LCG `0x343FD`/`0x269EC3`, state in the per-thread data block at `ptd+0x14` (`sub_00200820` is `rand`; the setter at
`sub_00200800` has no direct callers). Direct callers of `rand` (`sub_00013AA0`, `sub_000146D0`, `sub_00065FD0`, `sub_000C33E0`, `sub_000DB2D0`,
`sub_000DB660`) are all outside the fight step in the direct-call walk. Seeding of `srand` not traced. Confidence medium.

## Q2. The AI (confidence: high for structure, medium for completeness)

* The array `0x3BFA0C + slot*0xB8` is **not a free-standing array**: it is word `+0x7C` of the AI "brain" struct at `0x3BF990 + slot*0xB8`
  (four brains end exactly where the per-fighter generators begin, `0x3BFC70`). Words `+0x7C..+0x90` (six words) are the output: direction/buttons first.
* Writers of the output words: `sub_001AE0C0` (the large behaviour switch, ~65 stores to +0x7C), `sub_001AF9E0`, `sub_001AD440`,
  `sub_001AD6E0`, `sub_001AD9C0`, `sub_001ADE20`, and `sub_001B0290` (which clears them and sets the brain's countdowns).
  `sub_001B0290(slot)` is the AI entry: called from `sub_001A4A30` in a loop while a per-record flag (bit 0 of the byte at record+0x936, with a
  CPU-controlled marker in the next byte) is set. It marks "new output ready" by writing byte `0x3BF328 + slot`.
* The hand-off: `sub_001AD380` (reached via `sub_000C89D0` from `sub_0008BE60`, **once per pass, before the state switch and before `sub_00087700`**)
  copies the six output words into the pad-table entry of each active slot when the ready byte is set, then clears the byte. It ORs in bits `0xC00`
  of the existing word. So a CPU pad entry is "whatever the previous AI decision left", with per-decision latency of one pass.
* Inputs the AI uses (verified from the 218 functions directly reachable from `sub_001B0290`): fighter record fields (ids, positions, states, distances
  through small math helpers), the brain's own countdown/script fields, difficulty (`CLogic+0x30040` -> table `0x2AE3A4`, via `sub_000C8820`), a few
  config globals (`0x3B9084`, `0x3C03E0..`, `0x3BF1B8/1C0/1D0`) and the per-step scale `0x3B8F2C` (read in `sub_001B01F0`, 1.0 or the slow-motion ramp).
* **Randomness the AI reads:** only the per-fighter generator of its own slot (through `sub_000AA340` in `sub_001ADEB0`, `sub_001AE0C0`,
  `sub_001AF9E0`). `sub_001ADEB0` sums the weights of a table and draws once to pick an entry, so one decision consumes one draw.
* **Time or clocks read by the AI:** none found. No `rdtsc`, no `xbox_` kernel call, no CRT `rand`, no match-generator draw, no `0x39C0E0` draw in the AI's
  reachable set. The only kernel imports reachable are CRT-side (critical sections, file/mutex calls under the debug-print routine `sub_00011520`).
  No reads of anything written by the audio, streaming or render threads were found (pad snapshots are not read by the AI).
* **The seed of the AI generators is time.** `sub_000891A0` and `sub_0008B730` (the two match-setup paths) each take `rdtsc` and pass it to `sub_000C8820`,
  which seeds the four brains via `sub_001AD220` right after `sub_000871F0` has started the match. Both calls were read; the only difference is which path runs.
* Toolkit side: `xbox_ReadTimeStampCounter` (`tools/xboxrecomp/src/kernel/kernel_hal.c`) is `QueryPerformanceCounter` since the first call, rescaled to 733.33 MHz.
  `src/recomp_manual.c` has no override. The harness's `RECOMP_TEST_RNG_SEED` only rewrites the argument of `sub_001BC690`.

## Q3. Who draws from the match generator (confidence: high for the list, medium for the "all inside the step" claim)

Direct callers of the draw and its wrappers (`sub_001BC6E0`, `7B0`, `730`, `770`): `sub_001A9440`, `sub_001A9C50`, `sub_001AB410`, `sub_001B5D80`, `sub_001C6CD0`,
`sub_001D87B0`, `sub_001D8BD0`, `sub_001BE0B0`, `sub_001DA5C0`, `sub_001DB8F0`, `sub_001A5C30`, `sub_001A6E40`, `sub_001A8F00`, `sub_001B95F0`, `sub_001C5420`,
`sub_001D2F60`, `sub_001D9E40`, `sub_001B3110`, `sub_001B5AF0`, `sub_001B9170`, `sub_001C2930`, `sub_001D0210`. Walking upwards, 151 functions reach a draw.

* Fight step proper: via `sub_001A4900` (`sub_001B5D80`, `sub_001A94B0`, `sub_001A7530` -> `sub_001A6E40`), via `sub_001A4A30` (`sub_001AB410` -> `sub_001AB2A0` -> `sub_001C6CD0`),
  via `sub_001A93B0` (`sub_001A9310` -> `sub_001A91C0` -> `sub_001A8F00`).
* Fighter state handlers: `sub_001B54D0` (called from `sub_001A3310`, in the `sub_001A4A30` loop) builds a table of 111 handler addresses (`0x1AAD40..0x1DC400`) on its
  stack and calls the one indexed by record+0x30. These handlers are not visible to `callers.py`; 98 of the 151 upward roots are handlers. They all run once per record per step.
* Not the step, but deterministic: match start only (`sub_001A4D90` -> `sub_001A9B60` and `sub_001B3110`). The measurement above shows they did not draw (or drew before seeding).
* **Nothing found that draws the match generator from rendering, camera, particles, crowd, audio or loading code.** Every route up ends in `sub_00087700`, the handler
  table, match start, or the CLogic setup functions. The match generator is therefore not a plausible cause of divergence *before the first real fight draw*, and
  afterwards it is only as deterministic as the fighters' state. It cannot explain step 31.
* The generators that are drawn from code with an unpredictable call count per step or per frame are the object-form ones: `0x39C0E0` (about 25 non-step callers: `sub_00036DF0`,
  `sub_0003E170`, `sub_00043690`, `sub_000436B0`, `sub_0007D2F0`, `sub_00083F30`, `sub_00084640`, `sub_000937E0`..`sub_00094260`, `sub_000A6940`, `sub_000A6B90`, `sub_000D8B90`, `sub_000D8C40`,
  `sub_000D90F0`) while `sub_000AC590` (called at the end of every `sub_00087700`) also draws from it. Whether that code runs per presented frame was not checked.
  Whether any fighter state depends on its output was not shown. `sub_000AC1F0` (in that subtree) can write the match time scale (`CLogic+4`) via `sub_00044C10`.

## Q4. Is the step given a variable delta? (confidence: high)

* No wall-clock scaling on the step path. `sub_00087700` does not read its own `dt` argument; it calls `sub_001A4900(CLogic+4)`, which stores that scale into `0x3B8F2C` and adds it to the accumulator `0x3B9064`.
  `CLogic+4` (`0x349764`) is written by `sub_00044C10` from: `sub_0007C2F0` (0 when paused, else 1.0), `sub_0008D5C0` (1.0), `sub_000AC1F0` (a float at its object+0xB0, effects/slow-motion), and match start (1.0).
* The `dt` that the main loop produces, `sub_0002C530`, measures real elapsed time (from the tick word at `0x3C9684` read by `sub_001EDB70`) into frame-object fields `+8` and `+0xC`, but **returns the constant at `0x28C798` and stores 1/60 (`0x3C888889`)**; it is not on the fight's step path.
* A scan of the 1111 functions reachable from `sub_00087700` plus the handler table found no `rdtsc`, no performance-counter, system-time or tick-count import, and no CRT `rand`. The only kernel imports in reach are
  critical sections, mutex/wait, file and memory calls inside the CRT/debug-print path.
* Caveat: `0x3B8F2C` can still vary if `sub_000AC1F0` picks slow-motion from `0x39C0E0` draws (unproven).

## Q5. Ranked causes

1. **Time-seeded per-fighter AI generators (`sub_000C8820` -> `sub_001AD220`).** Evidence: rdtsc low 32 bits is the only seed input (verified read); the generators are drawn by the AI decision
   picker (`sub_001ADEB0`), which feeds the pad words the harness saw differ (verified read); the toolkit `rdtsc` is host-time based (verified read); the match generator was proven untouched through step 79 by recomputing its seed state;
   no other time or random input exists in the AI's reachable set; the measured divergence is a CPU pad word at step 31. Counter-evidence: none found. Not yet seen at run time.
2. **Time-seeded `CLogic+0x2D87C` generator** (`sub_0008ABF0`, `sub_00088630`, `sub_00088760`, `sub_00088E80`, `sub_000898E0`, `sub_0008A300`). Drawn in pre-fight CLogic states, so it could change intros or spawn choices.
   It does not explain a pad difference at step 31 on its own unless a choice feeds the fighters. Unproven.
3. **Shared utility generator `0x39C0E0`** drawn by about 25 non-step callers and by `sub_000AC590` inside the step. Candidate for effects/camera-driven differences, including the time scale. Unproven; no fighter read of it found.
4. **Later matches in one process** take the match generator seed from rdtsc (tail of `sub_0008BB00`), so `RECOMP_TEST_RNG_SEED` is needed for them and for any fight long enough to reach the first match-generator draw. The match generator is deterministic after that only if 1 to 3 are fixed.
5. **Harness-side alignment.** The injected pad word is placed before `sub_001BAA00` reads it, but the pad table is also zeroed and refilled by `sub_0008BE60`/`sub_001AD380` once per pass, outside `sub_00087700`. If a pass occurs without a step (states other than 4/5/8) the AI copy runs again.
   This did not cause the measured step-31 difference (both runs ran the same passes) but matters for exact-step alignment. Low.

## Smallest measurements that settle it

* **Top candidate:** add an entry hook on `sub_001AD220` that logs `MEM32(esp+4)` (the rdtsc value), and at the first step log the eight words `0x3BFCF0/F4`, `0x3BFD78/7C`, `0x3BFE00/04`, `0x3BFE88/8C`.
  Prediction: they differ between runs. Then pin that argument (env var like `RECOMP_TEST_RNG_SEED`) or make `xbox_ReadTimeStampCounter` a function of a fixed counter, rerun twice, and the step-31 pad word and the positions should agree.
* **Sharper:** log `0x3BFD78` (slot 1 state) at every step; the first step at which it changes marks the first AI draw, and the first step where the pad word differs should equal or follow it.
* **Rule out 2 and 3:** log `0x37705C` and `0x39C160` every step (and `0x3C1404`, already logged). If either changes differently between runs before the first fighter difference, it needs a deeper look.

## What I could not settle

* Whether any fighter code reads output of the `0x39C0E0` or `0x2D87C` generators. Next read: trace the consumers of `sub_000ABB70`/`sub_000AB550` results and what `sub_000AC1F0` writes into the fighter records or `0x3B8F2C`.
* Whether the non-step callers of `sub_000AA340` run once per presented frame. Next read: caller chains of `sub_00036DF0`, `sub_0003E170`, `sub_00043690`, `sub_0007D2F0`, `sub_00083F30`.
* The exact seeding path of the CRT `rand` (`sub_00200800` is reached only indirectly).
* Meaning of the AI "wake" flag (bit 0 of record+0x936): who sets it was not traced.
* Indirect dispatch other than the fighter handler table (for example per-fighter vtable calls) was not walked; the "nothing in the step reads a clock" statement is limited to what the walk covers.
