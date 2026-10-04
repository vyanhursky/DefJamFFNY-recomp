# Def Jam: Fight for NY freezes at its first loading screen in xemu

Standalone notes for whoever picks this up. Nothing here depends on the rest of this repository, and the
work described is on xemu rather than on this port. Written 2026-09-19.

## The problem

Def Jam: Fight for NY (Xbox, USA, title ID `45410049`, catalogue EA-073) boots in xemu, shows the EA logo
and the game's own loading screen, and then freezes there. It never reaches the menu.

- xemu compatibility page rates it **Starts**: https://xemu.app/titles/45410049/
- The tracking issue is **xemu #1124**, open since June 2022 against xemu 0.7.55, with no fix, no workaround
  and no pull request: https://github.com/xemu-project/xemu/issues/1124
- The reporter's description is that the game "never make it past the first loading screen properly and need
  one of the unimplemented commands to be playable", and the error involves an unsupported **PTimer**
  operation.
- Cxbx-Reloaded does not get past the loading screen either, so both mature Xbox emulators are stopped by
  this title.

Reproduced here on xemu 0.8.136 with a legitimately dumped disc: the game reaches the loading screen and
stays there.

## What this project can add

This repository is a static recompilation of the same executable: the game's code is translated to C and run
natively, with the Xbox kernel and hardware replaced by a runtime rather than emulated. That makes it an
accidental experiment in which hardware behaviours the game actually depends on, because anything the
runtime does not implement shows up immediately as a hang.

**Finding 1: the game does use PTIMER, and reads the clock.** Searching the disassembled image for
literal `0xFD009xxx` addresses yields one, `0xFD009140` (`PTIMER_INTR_EN_0`), which the game writes **zero**
to inside its Direct3D device-creation path (at guest `0x00223BD6`, which zeroes `PCRTC_INTR_EN_0` at
`0xFD600140` alongside it). That was originally reported here as "the game touches the timer exactly once".

**It reads the block as well**, which a search for literals cannot see because the address is computed from a
base held in the device object. This port now traps the PTIMER page and models the counter
(`src/hooks/nv2a_regs.c`), and the log shows the game reading `PTIMER_TIME_1` and `PTIMER_TIME_0` as a
64-bit pair shortly after its assets are loaded. So the block is live, not merely disabled, which matters
for an issue whose reporter described "an unsupported PTimer operation".

**What it does not do is poll.** Three reads in a fifty-second run, all at the same moment. The game takes
the clock once and then does not look at it again, so in this environment a dead PTIMER is not what keeps
the title on the loading screen. It reads the clock, and it would read whatever the clock said.

**Finding 2: the game tolerated a completely non-functional timer.** For most of this port's life the
entire NV2A register aperture was plain zeroed memory: reads returned zero forever and nothing advanced. The
game passed the `INTR_EN` write without complaint, created its device, set a display mode, reached the same
loading screen, streamed its whole asset set and issued thousands of draw calls. It now renders that loading
screen natively. So the title does not need the timer to count, to raise interrupts, or to return anything
meaningful. It needs the access not to fail.

**Finding 3: one register really does have to work, and it is not in PTIMER.** `NV_PFB_WBC` at
`0xFD100410` is the frame-buffer block's write-back-cache flush. The game sets bit `0x10000` and then spins
on the same dword until the hardware clears it:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Against memory that bit never clears and the **main thread never leaves that loop**, while the rendering
thread keeps resubmitting the frame it already has. The symptom is a loading screen that stays up and keeps
animating — which is indistinguishable, from the outside, from a game that is still loading. If xemu's PFB
does not clear that bit, this is exactly what it would look like there too, and it is worth checking before
anything else. (xemu is a full hardware emulator and very likely handles it; recorded because it cost this
port a lot of time to find, and because the symptom is so misleading.)

**What that suggests.** If xemu is aborting or hanging on an unimplemented PTIMER register rather than on
timer semantics, a minimal implementation of that block may be enough. That is a much smaller change than
"implement the timer".

## Settled, 2026-09-20: it is the PTIMER alarm

This port now raises that interrupt, and the title's own service routine claims it and moves on - it opens
files it had never reached before. The sequence, traced off the register page rather than inferred:

```
write INTR_EN_0  (0x9140) = 0            turn the alarm interrupt off while configuring
write NUMERATOR  (0x9200) = 56966
write DENOMINATOR(0x9210) = 7629
write ALARM_0    (0x9420) = 0xFFFFFFFF   park the comparator
write TIME_0     (0x9400) = 0            reset the count
write TIME_1     (0x9410) = 0
read  TIME_1, TIME_0                     now
write ALARM_0    (0x9420) = now + 16,838,770
write INTR_EN_0  (0x9140) = 1            arm it
```

16,838,770 nanoseconds is 16.84 ms: one frame at 59.4 Hz. **The title's frame clock is this interrupt.**
Without it the simulation is never credited a frame, so the game renders its loading screen for ever while
updating nothing - which is exactly the symptom, here and on both emulators. Finding 2 below says the title
tolerates a dead timer; more precisely, it tolerates a dead *counter* and does not tolerate a dead *alarm*.

The comparison to implement is against `TIME_0` as the low 32 bits of a nanosecond count, with `TIME_1` the
rest. Some references describe `TIME_0` as the low 27 bits shifted up by five; that does not match this
title's arithmetic, and its own 16.84 ms deadline is what settles it.

One caution from implementing it here: the interrupt status registers matter as much as the alarm.
`PMC_INTR_0` is a read-only summary of which block is asserting, and `PTIMER_INTR_0` is write-1-to-clear. A
status bit left set reads as an interrupt still asserting and the next one is declined; a summary erased too
early makes the routine decline the first. This port still gets only one alarm per run for one of those
reasons, so treat the status registers as part of the feature rather than an afterthought.

## What is NOT established

Be careful with the above. Two real limits:

1. The search covered addresses appearing as **literals** in the instruction stream. An address computed at
   runtime as base plus offset does not appear, which is exactly what hid the PTIMER clock reads until the
   page was trapped. Treat any "the game never touches X" claim built from a literal search with suspicion;
   trapping the page and counting is the only version of that claim worth acting on.
2. This port's own loading screen has not yet advanced either, so nothing here proves what the title needs
   in order to reach the menu. What it proves is what the title does not need: it does not need the timer to
   count. xemu differs in many other ways, and its freeze may not be about this register at all any more.
3. The issue is four years old and was filed against xemu 0.7.55. Current xemu is 0.8.136. **The failure may
   have moved.**

## Recommended approach

**Verify before writing any code.** Run xemu from a console with logging, load the title, let it reach the
loading screen, and capture what it actually prints and where it stops. That single step decides whether
this is a small register fix or something else entirely, and it is ten minutes of work. Everything below is
conditional on it.

**Then fix it upstream, not per-game.** xemu is an accuracy-focused emulator and a title-specific hack would
rightly be unwelcome. If the timer block is genuinely unimplemented, implementing the missing registers is a
general correctness improvement that happens to unblock this game, which is what issue #1124 asks for. Post
the findings on that issue regardless, because nobody there currently has this level of detail.

Suggested order:

1. Reproduce with xemu's own logging and record the exact message and stop location.
2. Locate the PTIMER handling in xemu's NV2A implementation and establish what is missing: a whole block, a
   single register, or an assertion that fires on an otherwise harmless access.
3. Implement the minimum that makes the access well-defined, matching the NV2A documentation that xemu's
   other blocks are written against.
4. Test against this title **and** a handful of known-good titles, since the block is shared.
5. Open a pull request referencing issue #1124, and describe the evidence rather than just the symptom.

## Two other handshakes this title needs

Both of these blocked our port and were hard to find. xemu emulates the hardware properly, so it most likely
handles both already, and they are recorded here only so that whoever works on this recognises them if they
surface.

- **AC'97 bus-master channel reset.** The game writes `2` to a bus-master control register (bit 1, RR,
  "reset registers") and then polls the same byte in a two-instruction loop that never re-reads it. Real
  hardware clears the bit when the reset completes. The loop is `test cl, cl / jne $-2` at guest
  `0x00267B73`, with the register read six instructions earlier, so the bit must read back clear
  essentially immediately.
- **Audio DSP command doorbell.** DirectSound hands the DSP a command block in guest memory, writes a
  command word, and spins until the DSP writes zero back. Requires actual DSP56300 execution, or at minimum
  something that acknowledges the command.

## Practical notes

- You need your own legally dumped disc and your own Xbox BIOS, MCPX boot ROM and EEPROM. None of those are
  in this repository and none can be provided.
- The title is a single `default.xbe`, roughly 3.3 MB, built against XDK 5849, with separate `D3D`, `D3DX`,
  `DSOUND`, `XGRPH` and `XPP` sections, so all the Xbox libraries are statically linked into it.
- Getting this working in xemu would also help this port: xemu is currently our only reference for what the
  game should look like, and because it cannot pass the loading screen we have no source of truth for the
  title screen at all.
