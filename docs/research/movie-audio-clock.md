# Movie audio clock: what drives the stream counters at 0x3A9984[h]+0x48/+0x4C

Scope: read-only study of the lifted C (`src/recomp/gen/recomp_0003/0006/0008/0009/0013/0014/0016/0017.c`) plus a short look at the
toolkit APU model (`tools/xboxrecomp/src/apu/`). Nothing was run. Addresses are guest addresses; "confirmed" means read in the
lifted code, "inferred" means reasoned from names, shapes or the toolkit.

## 0. Two corrections to the working hypothesis (read these first)

1. **`sub_001260E0(h)` is not a play position. It is the audio backlog.** `S+0x48` is "samples submitted by the title and not yet
   popped", `S+0x4C` is "samples popped but not yet copied to the hardware ring buffer". Submitting raises the sum; copying into the
   DirectSound ring lowers it. So `out[2]` of `sub_00120110` is "ms of audio still waiting", falling to a reader-based estimate
   when that is 0. (confirmed, section 2)
2. **`sub_0013B9A0` never reads `out[0]` or `out[2]`.** It reads only `out[1]` (a source id) and feeds it to `sub_00121FD0`. The
   movie clock it returns is a *wall-clock tick counter* (`[0x3C9684]`, a 120 Hz software timer) with an optional drift correction
   toward the audio play position of the head source node. If the audio does not move, it returns the tick-based clock unchanged.
   (confirmed, section 5)

Consequence: a frozen audio play cursor alone would not freeze the movie clock. What freezes the movie is the tick counter
`[0x3C9684]` not advancing, or the video-side frame test never passing (section 5/7). The audio stall is still a real, separate
dependency (it stalls the packet feeder and the stream counters, section 4).

## 1. Object model (confirmed)

| Object | Where | Notes |
|---|---|---|
| Sound channel object `C` | `[0x3A92A0 + id*4]`, count = byte `[0x3A9386]`; `sub_0011EC00(id)` returns it | `C+0x00` source reader ctx, `C+0x08` stream handle `h`, `C+0x10` byte kind (1 or 2, tested in `sub_0011F4A0`), `C+0x14` current sample rate (Hz, 16-bit use), `C+0x18` next source's rate, `C+0x11C` list A, `C+0x128` list B, `C+0x134` node being parsed |
| list header | 3 dwords: head, tail, count | `sub_001263D0` init, `sub_001263E0` push back, `sub_00126410` push front, `sub_00126440` pop front, `sub_00126470` remove; each updates `count` at `+8` |
| so `C+0x124` | = count field of list A (`C+0x11C`) | **it is a node count, not a state machine.** Nonzero while at least one source node is queued |
| source node | element of list A / B | `+0x00` next, `+0x04` prev, `+0x0C` id (matched by `sub_001264B0`), `+0x10` divisor used by `sub_00120110`'s fallback, `+0x14` samples played, `+0x18` total samples, `+0x1C` samples remaining |
| Stream object `S` | `[0x3A9984 + h*4]`, created by `sub_00125B20` (called from `sub_0011F6E0`) | see table below |
| hardware voice entry | `[0x3A9518]` array, stride `0x8C` | owned by the voice allocator (`sub_00124990/124B50/124CE0/125050/125170`) |
| voice-group object | on the lists at `0x3A95EC..0x3A9604` | `+0x08` DirectSound buffer, `+0x0C` voice-entry index, `+0x14` ring bytes, `+0x18` last write offset, `+0x1C` pending packet ptr, `+0x20` **stream handle `h`** (>= 0 means "stream voice"), `+0x24/0x28` packet bytes / bytes consumed |

Stream object `S` fields (all confirmed from `sub_00125B20/125BD0/125FA0/126150/1262B0`):

| Off | Meaning |
|---|---|
| `+0x00` | voice-group id, `-1` when stopped (set by `sub_00126370`), negative error from start |
| `+0x04` | packets submitted (incremented in `sub_00125FA0`); slot snapshot |
| `+0x08` | packets popped; `+0x0C` packets fully retired (all channels popped) |
| `+0x10 + 4*ch` | per-channel popped counters |
| `+0x28 + 2*ch`, `+0x34 + 2*ch` | per-channel read index / pending packet count |
| `+0x40` ring slot count, `+0x44` head (pop) index, `+0x46` tail (submit) index, `+0x42` byte: master channel index |
| **`+0x48`** | **samples submitted, not yet popped** |
| **`+0x4C`** | **samples popped, not yet copied to the hardware ring** |
| `+0x50..0x5C` | `+0x50` caller arg, `+0x54` callback A (`0x11EC80`, "packet retired"), `+0x58` callback B (`0x11ECB0`, "n samples consumed"), `+0x5C` user = `C` |
| `+0x62` | byte channel count; `+0x7C + 0x20*i` packet slots (`+4` size|flag31, `+0xC+4*ch` data pointers) |

## 2. Q1: who writes `S+0x48` and `S+0x4C`

All writers of the two fields are in four functions (confirmed by scanning every store to `+0x48/+0x4C` in 0x110000-0x140000 and reading
the ones that go through `[0x3A9984+h*4]`):

| Function | Store | Effect |
|---|---|---|
| `sub_00125BD0` (stream start, prologue 0x125BD0-0x125C3C) | `+0x48 = 0`, `+0x4C = 0`, also `+0x04/+0x08/+0x0C/+0x44/+0x46 = 0` | resets the stream. Anything submitted before a start is dropped |
| `sub_00125FA0(h, pkt)` (submit), block at 0x126052 | `+0x48 += pkt[+4] & 0x7FFFFFFF`; `+0x04++`; tail `+0x46 = (tail+1) mod +0x40` | adds the packet's sample count |
| `sub_00126150(h, ch, &size, &flag)` (pop), block at 0x126250 | when the **last** channel pops the packet: `+0x0C++`, `+0x48 -= size`, `+0x4C += size` | moves samples from "submitted" to "popped" |
| `sub_001262B0(h, ch, n)` (copied n samples), block at 0x1262C6 | only if `ch == S+0x42`: `+0x4C -= n` | removes samples that reached the hardware ring; also queues event `{type 0, h, n}` at `0x3A9680/0x3A9684` if `S+0x58 != 0` |

(`sub_00125BD0` also writes a 16-bit `+0x4C` at 0x125D74, but there `esi` has been reloaded as a **voice entry** from `[0x3A9518]`, not `S`.)

Call chains:

* **Pop and copy (decrease side).** Audio service thread entry `sub_001242D0` (started by `sub_001243A0` via `sub_001F68D2`, loop flag
  byte `[0x3A95DD]`, 10 ms tick, sleep through `sub_001F6083`):
  `sub_001242D0 -> sub_0011FAF0 (call at 0x1242F1) -> sub_00124F30 (call at 0x11FB04) -> sub_001293F0 (per voice-group object with +0x20 >= 0)
  -> sub_00126150 (pop) and sub_001262B0 (copy done)`.
  `sub_001262B0`/`sub_00126150` are also called by three indirectly-reached codec pull routines `sub_0012D5D0`, `sub_0012DBF0`, `sub_0012E290`
  (software-mix path, driven by `sub_001241A0 -> sub_001291D0 -> sub_00128F30/12BFE0`, only when byte `[0x3A9A36]` is set; inferred that the movie
  uses the hardware-voice path, not this one).
* **Submit (increase side).** `sub_0011F4A0` (the per-tick stream feeder) `-> sub_0011F300 -> sub_00125FA0`. `sub_0011F440` is the indirect
  per-chunk dispatcher that reaches the same `sub_0011F300`. `sub_0011F4A0` is registered into the callback table `0x3A94D8` by `sub_0011BB30`
  (call at 0x11F96F inside `sub_0011F6E0`, executed when the first sound object is created). The table is run by `sub_0011BBB0`, which
  `sub_00127550` calls; `sub_00127570` registers `sub_00127550` with `sub_001ECCC0(0x127550, 0, 1)` in the game's tick scheduler (table
  `0x3C9500`, 16-byte entries). **That scheduler is run by `sub_001ECE20` (called from the main thread's wait/yield helpers) and an entry fires
  when tick counter `[0x3C9688] >= its due time`.** So the feeder runs on the *main thread*, paced by the tick counter (inferred: that
  `sub_001ECE20` is only reached from the main thread; callers listed by `scripts/callers.py` are all game-logic functions).
* **Event dispatch (consumes `S+0x58`).** `sub_001242D0 -> sub_00126300` (call at 0x124344) calls `S+0x58`/`S+0x54` per queued event;
  `S+0x58 = sub_0011ECB0` advances the head source node (`node+0x14 += n`, `node+0x1C -= n`, retires nodes whose played >= total with
  `sub_00126470` + `sub_001263E0` to list B, which is what lowers `C+0x124`).
* **Create.** `sub_0011F6E0` (sound create) `-> sub_00125B20(0x11EC80, 0x11ECB0, C, ..)` fills `S+0x40/0x50..0x5C` and `[0x3A9984+h*4]`.
  `sub_00125BD0` is reached through `sub_0011E9C0`, itself called by `sub_0011ED80` (header parse) and `sub_0011F4A0` (start of next source).

## 3. Q2: where the numbers come from

* `+0x48` comes from **a count of what the title submitted** (packet sizes), not from hardware.
* `+0x4C -= n` happens only after the engine has **copied n samples into the DirectSound ring** in `sub_001293F0`. The amount copied per pass is
  bounded by how far the hardware **play cursor** has advanced since the last write offset (`voice-group+0x18`). Reads in `sub_001293F0`:
  `sub_00259423(buf = voice-group+0x08, &play, 0)` (call at 0x129423), result quantised to 36-byte units (`*0x38E38E39 >> 35`), then
  `free = play - last_write` (modulo ring size `voice-group+0x14`). If the cursor has not moved, `free == 0` and nothing is popped or copied.
* So the **stream counters are driven by a poll of a DirectSound buffer position every 10 ms**, not by completion callbacks or interrupts.
  The title does not use an APU interrupt for streaming. (It uses `sub_00259407` = `GetStatus` in `sub_00124F30` to detect one-shot voices that finished.)
* DirectSound wrappers (statically linked XDK `dsound`, confirmed by shape): `sub_00259423` = `IDirectSoundBuffer::GetCurrentPosition`
  (this-pointer adjusted by -0x1C) `-> sub_00257F0E -> sub_0026415B` (CMcpxBuffer::GetCurrentPosition) `-> sub_0026302E` (hardware read).
  `sub_00259323` = `Play`, `sub_0025BB3D` = `SetBufferData`, `sub_00259443` = `SetCurrentPosition`, `sub_00259383` = `Stop`,
  `sub_0025C620` = `CreateSoundBuffer`, `sub_00259407` = `GetStatus`.
* The hardware read, `sub_0026302E(this)` (confirmed):
  1. returns 0 at once if `(this+0x12 & 1) == 0`;
  2. voice index `v = MEM16(this + MEM8(this+0x64)*2 + 0xA)`; voice array base `[0x27CCB0]`, stride `0x80`; if `voice[+0x54] & 0x100000` it
     returns 0 (that bit is `NV_PAVS_VOICE_PAR_STATE_NEW_VOICE` in the toolkit's `apu_regs.h`: the voice has never been processed);
  3. spins on MMIO `0xFE820010` (`NV1BA0_PIO_FREE`) until its value `& ~3 >= 0xC`;
  4. writes `0xFE8202F8 = MEM16(this+0xC)` (`SET_CURRENT_VOICE`), `0xFE8202FC = 1` (`VOICE_LOCK`);
  5. reads `voice[+0x58] & 0xFFFFFF` (`NV_PAVS_VOICE_PAR_OFFSET_CBO`, the current buffer offset, written by the APU voice processor);
  6. writes `0xFE8202FC = 0` (unlock) and returns the offset; `sub_002605CD` converts samples to bytes (format `0x69` = Xbox ADPCM uses `>>6` times bytes per block).
  `sub_0026415B` then reports `play = offset` and `write = play + max(32 samples, voice field) mod buffer`.
  **So the play position is read from the voice structure in guest RAM that the (emulated) MCPX voice processor updates.** No timer is involved.
* In the toolkit model that RAM word only changes while the APU frame thread runs the voice (`apu_vp.c`, voice process: `NEW_VOICE` cleared,
  `if (paused) return`, CBO advanced) and `apu_active` holds in `apu_core.c` (`XCNTMODE != OFF` and front end not `TRAPPED`/`HALTED`). The
  model itself notes an earlier case where a front-end trap left every later frame silent. (inferred link to the guest side; not measured.)

## 4. Q3: what must happen for the counters to move

Start-up sequence (confirmed from code order):

1. `sub_0011F6E0` creates `C` and `S` (counters 0, list A empty, `C+0x124 == 0`).
2. `sub_0011F4A0` (main-thread, per tick) reads blocks from the source reader `sub_001E7D80(C+0)`; signature `0x6C484353` ("SCHl") goes to
   `sub_0011ED80` which builds a node (list A count becomes 1+), signature `0x6C444353` ("SCDl") goes to `sub_0011F300 -> sub_00125FA0` (`S+0x48 += size`).
   Kind 1 feeds as many packets as `sub_001260A0(h)` free slots; kind 2 first requires `sub_001260E0(h) <= 0` (no backlog) to start the next source,
   else it skips the whole channel for that tick.
3. Start of a source: `sub_0011F4A0` stops the old voices (`sub_00126370`) and calls `sub_0011E9C0 -> sub_00125BD0`, which zeroes the counters,
   allocates voices (`sub_00129DC0`) and calls `sub_00129790`. **`sub_00129790` itself does `SetBufferData`, `SetCurrentPosition(0)` and `Play(0,0,1)`
   (looping) on each voice buffer (call at 0x129A8F, arg 1).** There is no separate Play/Pause(false); no minimum buffered size is checked.
4. The service thread (10 ms) then needs the hardware cursor to advance (section 3). Only then does `sub_001293F0` pop (`+0x48 -> +0x4C`),
   copy, and call `sub_001262B0` (`+0x4C -= n`), after which `sub_00126300 -> sub_0011ECB0` advances the node played counters.

`+0x124` "state machine": it is just the list count; `+1` per queued source node (`sub_001263E0` on list A), `-1` when `sub_0011ECB0`/`sub_0011EC20`
retire a node. `sub_00120110` reports nothing (all three out fields 0) while it is 0, and `out[2]` is also 0 if `MEM16(C+0x14) == 0`.

Dependencies on the hardware cursor: if the DirectSound play cursor never leaves 0, nothing is ever popped or copied, `S+0x48` only grows,
`sub_001260E0` stays > 0, kind-2 channels never start their next source, and the head node's `+0x14` never advances.

## 5. Q4: the movie loop

`sub_0007B700` (per-frame update of the movie screen, vtable method) -> `sub_000CC330(V)` -> `sub_0013BA80(M = V[0])` -> `sub_0013B9A0(M)`.
The "spin" is the main game loop repeating this; there is no inner loop in `sub_0013B9A0`. Per call (confirmed):

1. `sub_0013AE30(X = M+0x5C)`: `now = [0x3C9684]` (`sub_001EDB70`); `X[8:12] += (now - X[0]) * X[0x10] >> 12` (64-bit, `X[0x10]` = 0x1000 = 1.0); `X[0] = now`.
2. `ebp = X[8] * 1000 / [0x3C9680]` (`sub_001EDC30`, tick rate; set to 120 by `sub_001ED6D0(0x78)` from `sub_0001A890`).
   `clock = ebp - M[0x4C]`. If `M[0x54] == 0` return `clock`. (`M[0x54] = (sound handle >= 0)`, set in `sub_0013B7A0`.)
3. Else lock (`sub_0011FCE0`), `sub_00120110(handle = [M[0]+0xC], out)`, `sub_00121FD0(out[1], tmp)`, unlock (`sub_0011FD00`).
   `out[0]` and `out[2]` are **not read**. `sub_00121FD0` maps `out[1]` to the source node and returns `tmp[1] = node+0x14 * 1000 / rate`, i.e. the **played
   position (ms) of the head source node**, which `sub_0011ECB0` advances from the copy events (section 2).
4. `audio = tmp[1] - sub_0020B920()` (`sub_0020B920` is a stub that returns 0 both ways, confirmed). If `audio <= M[0x50]` return `clock` (no new audio
   information). Otherwise `drift = M[0x58] * 7/8 - clock + audio`; `M[0x50] = audio; M[0x58] = drift`. If `|drift| <= 0x108` (264 ms) return `clock`.
   Else `M[0x4C] -= drift/8`, `M[0x58] = 0`, return `ebp - M[0x4C]`.

So audio only nudges the tick-based clock, and only after the audio position has moved forward and drifted more than 264 ms.

Advance test, `sub_0013BA80` (confirmed): `F = rate * (clock_ms + M[0x40])` with `rate` from the decoder object's vtable (`sub_0013CE30`, returns the
constant at `[0x28947C]` when `M[0x64] == 0`, which is the 0.0 used elsewhere in this engine, inferred); stores `F` at `M[0x48]`; returns `F >= M[0x44] + 1.0`
(`M[0x44]` = last frame index, constant at `[0x289478]` = 1.0, inferred). `sub_000CC330`: when true copies `F` into `V[0x38]`; if `V[0x38] != V[0x3C]`
it decodes/presents the next frame (`sub_0013B240(time = V[0x38])`), sets `V[0x40]`, `V[0x3C] = V[0x38]`, returns 1.
**A video frame becomes due when `F >= lastFrame + 1`, nothing else.** Exit/finish of the movie is not decided here (inferred: when `sub_0013B240` yields
no frame, or when `V+0x18 == 0`, `sub_0007B700` takes its cleanup path).

## 6. Q5: condition list

| # | Condition | Status |
|---|---|---|
| 1 | `sub_00120110` returns all-zero out unless `C+0x124` (list A count) != 0 | confirmed |
| 2 | `out[2]` = `1000 * (S+0x48 + S+0x4C) / MEM16(C+0x14)`; if that is 0 and node `+0x10 != 0`, `min(sub_001E7E30(C+0), 4000000) * 1000 / node+0x10` | confirmed |
| 3 | `S+0x48/+0x4C` start at 0 on every stream start (`sub_00125BD0`) and submissions made before it are dropped | confirmed |
| 4 | `S+0x48` grows only through `sub_0011F4A0 -> 0x11F300 -> 0x125FA0` | confirmed |
| 5 | pop and copy happen only in `sub_001293F0` (service thread, 10 ms) for voice-groups with `+0x20 >= 0` (or the software-mix pull routines) | confirmed |
| 6 | copy amount = play cursor advance since last write offset, in 36-byte units; zero advance means zero copy | confirmed |
| 7 | play cursor = `CBO` at `voice[+0x58]`, voice array `[0x27CCB0]` stride 0x80, MMIO `0xFE820010/0xFE8202F8/0xFE8202FC` | confirmed |
| 8 | cursor read returns 0 if `this+0x12` bit 0 clear or voice `+0x54` bit 20 (NEW_VOICE) set | confirmed |
| 9 | `Play(looping)` is issued from `sub_00129790` at stream start | confirmed |
| 10 | `sub_001262B0` reduces `S+0x4C` only for `ch == S+0x42` | confirmed |
| 11 | position events are queued at `0x3A9680/84` and delivered by `sub_00126300` on the service thread (and at stream teardown) | confirmed |
| 12 | the movie clock is the 120 Hz tick counter `[0x3C9684]`; audio only corrects it | confirmed |
| 13 | `sub_0013B9A0` ignores `out[0]`/`out[2]` | confirmed |
| 14 | frame due when `F >= M[0x44] + 1` | confirmed |
| 15 | the tick counter is advanced by the thread running `sub_001ED5A0` (loop: `tick++`, run callbacks `0x3C9660..0x3C9680`, wait on object `0x3C9614` via `sub_001EDD70 = sub_001F6057(.., -1)`), signalled by a re-arming timer thread (`sub_001ED620 -> sub_001F9A8A`, a `timeSetEvent`-like emulation, 5 arguments, one thread proc at `0x1F98A2`) | inferred from shapes |
| 16 | `0x3C9688` (scheduler time) is incremented in `sub_001ED5A0` as well; the audio feeder is a scheduler entry, so it also needs the tick thread alive | inferred |
| 17 | the movie's audio uses the hardware-voice path (`sub_001293F0`), kind 1 | inferred |
| 18 | which kind (1 or 2) the movie's `C+0x10` has | not determined |
| 19 | the toolkit APU model advances `CBO` only when `apu_active` and the voice is not paused | inferred (read of toolkit, not run) |

## 7. What this means for the 1-in-14 hang, and what to measure next

Facts that follow from the code, in order of how directly they match "GPU idle, main thread spinning in `sub_0013B9A0`, audio service thread asleep":

* The main loop spinning is expected whenever `F < lastFrame + 1`: nothing blocks and nothing waits, so it runs flat out and takes the engine lock each time
  (`M[0x54] != 0` path). That alone does not say audio is stuck.
* For `F` to stay put, `clock_ms` must stay put, i.e. `[0x3C9684]` is not advancing (or `[0x3C9680]`, `M[0x40]`, the decoder rate or `M[0x44]` are wrong). A frozen
  audio cursor cannot do this by itself because audio only corrects the clock after it moves (section 5, point 4).
* A frozen audio cursor does stall the feeder side: `S+0x48/+0x4C` never decrease, kind-2 channels never advance, node `+0x14` never moves. If the intro audio
  never starts, expect video to continue on the tick clock; so a total freeze suggests the tick path rather than the audio path. Both can be true in one run.

Cheap checks that would separate the cases (all read-only for the game, using existing tools):

1. `RECOMP_PEEK` of `0x3C9684` and `0x3C9688` two seconds apart at the hang: tick counters moving or not. Also `0x3C9680` (expect 120), `0x3C9624`, `0x3C9620`.
2. `scripts/sample-threads.py` / `scripts/native-stacks.py`: is there a thread blocked in `sub_001F6057` on the `0x3C9614` object (tick thread, entry via `sub_001ED080`),
   and a timer thread (proc `0x1F98A2`)? The audio service thread (`sub_001242D0`) was already seen alive.
3. `RECOMP_WATCH_EXEC=0x1293F0,0x126150,0x1262B0,0x125FA0` totals (not the first lines): does the service thread pop/copy at all, and does the feeder submit?
4. Peek `S` for the movie's stream: `[0x3A9984 + h*4]` then `+0x48`, `+0x4C`, `+0x44`, `+0x46`, `+0x00` (-1 means stopped); and the channel object `C` (`[0x3A92A0+id*4]`)
   `+0x124`, `+0x08`, `+0x10`; head node `+0x14/+0x18/+0x1C`.
5. For the hardware cursor: guest word `voice[+0x58]` at `[0x27CCB0] + idx*0x80` for the movie voice (idx from `[buffer+0x64]`/`+0x0A`), and `RECOMP_APU_TRACE` lines
   (`active`, `FECTL`, `SECTL`) to see whether the APU frame thread is running the voice.
6. Peek the movie object `M`: `+0x54`, `+0x40`, `+0x44`, `+0x48`, `+0x4C`, `+0x50`, `+0x58`, `+0x64` and `[M+0x5C]+8`.

## 8. Function index

| Address | Role |
|---|---|
| `sub_001242D0` | audio service thread, 10 ms loop |
| `sub_0011FAF0` | per-tick update: `sub_00124F30`, per-type hooks `[0x3A94C0+i*4]` |
| `sub_00124F30` | walks voice-group lists `0x3A95EC..0x3A9604` |
| `sub_001293F0` | stream voice service: GetCurrentPosition, pop (`126150`), copy, `1262B0` |
| `sub_00126150` / `sub_001262B0` | pop packet / copy-done report (`S+0x48/0x4C`) |
| `sub_00125FA0` / `sub_00125BD0` / `sub_00125B20` / `sub_00126370` | submit / start / create / stop stream |
| `sub_00126300` / `sub_0011ECB0` / `sub_0011EC80` | event dispatch / samples-consumed callback / packet-retired callback |
| `sub_0011F4A0` / `sub_0011F300` / `sub_0011F440` / `sub_0011ED80` | stream feeder / submit packet / chunk dispatcher / header parse |
| `sub_0011F6E0` / `sub_0011E9C0` | create sound / start source |
| `sub_00120110` / `sub_00121FD0` / `sub_001260E0` / `sub_001260A0` | query out[3] / source timing / backlog / free slots |
| `sub_00259423` -> `257F0E` -> `26415B` -> `26302E` | `GetCurrentPosition` down to the MCPX read |
| `sub_0013B9A0` / `sub_0013BA80` / `sub_000CC330` / `sub_0007B700` | clock / frame due / per-frame advance / screen update |
| `sub_0013AE30`, `sub_001EDC30`, `sub_001EDB70`, `sub_001ED6D0`, `sub_001ED5A0`, `sub_001ED620`, `sub_001ECE20`, `sub_001ECCC0` | movie timer accumulate, tick rate, tick counter, tick init (120 Hz), tick thread, timer re-arm, callback scheduler, scheduler register |
