# Why the push-buffer walker loses its place (2026-09-25/26)

Findings from a night of measurement on the menu script (`tests/golden/README.md`) and 70 s start-ups.
Addresses are Def Jam's. The walker is `tools/xboxrecomp/src/kernel/nv2a_pb_scan.c` (decode) and the
ack-thread loop in `xbox_memory_layout.c` (runs, stalls, fences). Complements
`docs/research/d3d-pushbuffer-wrap.md` (the sub-agent's reading of Direct3D's ring code).

## What Direct3D does (read from the lifted code, confirmed at run time)

| Item | Where | Notes |
|---|---|---|
| Device | `MEM32(0x234768)` | |
| Write pointer, "safe until", ring base, ring limit | `[dev+0]`, `[dev+4]`, `[dev+0x24]`, `[dev+0x28]` | ring `0x82A0E000`, 512 KB |
| Wrap count | `[dev+0x40]` | +1 at each wrap; the wrap writes a JUMP `(base & 0x0FFFFFFF) | 1` at the old write pointer |
| Fence word / latest issued | `*[dev+0x30]` / `[dev+0x2C]` | |
| Fence records | `[dev+0x64 + ((ref>>1)&63)*8]` = {ref, position} | last 64 only; **position is where the fence was allocated, before its release command**; a few references have no record at all (slot reads 0); a reference is counted before its record is written |
| Kick-off | `sub_0021EA70`, `sub_0021EB20` | PUT = `[dev] & 0x0FFFFFFF` (or `[dev+0x770]` in deferred-list mode, `[dev+8] & 4`, not seen used) |
| GPU busy | `sub_002162A0` | PFIFO `CACHE1_DMA_PUT` (`0x3240`) != `CACHE1_DMA_GET` (`0x3244`), else PGRAPH status. Only ~1 call in 90 s; the kick-off's wait-for-idle path is not taken. |
| Cached GPU position | `sub_0021E830` -> `[dev+0x5C]`, lap `[dev+0x60]` | from DMA_GET when inside the ring, else from PGRAPH `PATT_COLOR0`; lap = `[dev+0x40] - (write < GET)` |
| Block on fence | `sub_0021EC50` -> `sub_0021E8B0` | spins until `((fence << 2) ^ PATT_COLOR0) & 0x7C == 0`: **PATT_COLOR0 bits 6:2 must equal the fence's low five bits** (bits 1:0 carry the lap, bits 7+ a ring position) |
| Pusher error handler | `sub_00223810` | prints, and on a DMA-pusher error does `CACHE1_DMA_GET += 4` |

## Confirmed walker/executor bugs

1. **Fences ran ahead at start-up** (fixed, patch 0039/0040).
2. **Lap-blind fence completion.** The idle catch-up completed references whose recorded position was
   numerically behind PUT but on Direct3D's *next* lap (inserted after a wrap, before PUT crossed it):
   `[FENCE] caught up with PUT; completing 0x39F -> 0x3AD (its commands at 0x82A0E000 are behind PUT
   0x82A8822C)`. Direct3D then took the lap for consumed. Not fixed in the committed code.
3. **Packets cut off at PUT.** Direct3D kicks in the middle of long packets; the walker restarted
   every run afresh and took the next parameter for a header. Fixed (patch 0042).
4. **Any top bits accepted as a header**, so a pointer in data (`0x80244950`) decoded as one. Fixed (0042).
5. **Stale subroutine flag after a skip**: every later CALL refused as nested. Fixed (0042).
6. **Resume before the fixup.** The stall ended when the interrupt status was clear and FIFO access
   on; Direct3D's ISR clears the status before its deferred routine turns access off and patches the
   commands after the NOP. A vertex packet header read as count 16 was count 32 after the fixup.
   Fixed (0042: busy while the interrupt is delivered and its DPCs drained).
7. **Completing a fence without its PATT_COLOR0 pair** hangs `sub_0021E8B0`. Any code that sets the
   fence word must also set PATT bits 6:2 (see "Tried" below).

## Still happening

- **Direct3D writes its next lap a little past the executor** -- `0x158` to `0x1B84` bytes -- whenever
  the executor stalls at a software method, and even while it runs. Direct3D assumes the GPU has
  prefetched past a completed fence (the NV2A pusher reads ahead into its FIFO) and that a stall is
  microseconds (on a single CPU the interrupt preempts the game). Here the stall is milliseconds and the
  game thread keeps writing. The executor then reads the next lap from the middle of a packet --
  typically right after the Present's `FLIP_STALL` (`0x130`), which is normally followed by
  `SET_BEGIN_END(5)` (`000417FC 00000005`). Detector: `[PB] D3D lapped the executor` (in the WIP, not
  committed).
- 20+ "skipping to PUT" per menu run; each skip can execute garbage, raise bogus software methods and
  hang or crash D3D's fixup DPC (`sub_0021F1A0`).

## Tried, not kept (all in the scratchpad WIP of 2026-09-26, `wip-0042/`)

- **Reporting GET as the CALL's return address inside subroutines**: stalled during the movies.
- **Modelling CACHE1 DMA PUT/GET as PUT/executor**: the title stopped taking START (probably a wait for
  idle across long stalls). `RECOMP_PB_ALWAYS_IDLE=1` restored it.
- **Lap-aware fence completion from D3D's own state** (PUT's lap = `[dev+0x40] - (write < PUT)`, the
  executor's = PUT's lap `- (executor > PUT)`), with a **captured record queue** (D3D's table is
  overwritten before the executor gets there), a **prefetch margin** (complete a fence only once its
  position + 8 KB has been read), and a **prefetch copy** of up to 16 KB past the executor, frozen where
  Direct3D's next lap reached it and refreshed from memory elsewhere (to keep fixups). Start-up skips
  went to 0-3, but menu runs still showed 20+ skips, occasional stuck fences, and the busy model above
  broke START; not proven enough to commit.

## Suggested next step

Keep the fence completion model simple and correct (lap-aware, PATT-paired), and attack the stall
length instead: the real fix for "Direct3D writes past a stalled GPU" is that on the console the game
thread cannot run while the GPU's interrupt is being serviced. Options: raise the servicing thread's
priority further and pin it with the guest threads (D28) so the interrupt preempts the game thread, or
block guest threads at their next kernel call while `g_gpu_servicing` is set. Measure with the lap
detector.
