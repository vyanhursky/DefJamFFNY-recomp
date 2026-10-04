# M2 — vblank ISR hang: why the D3D ISR declines, and what's actually stuck

Research date: 2026-09-17. Source: local disassembly (`tools/xboxrecomp/tools/disasm/output/`), toolkit
runtime C (`tools/xboxrecomp/src/kernel/`, `src/nv2a/`, `src/video/`), and `logs/iter4-vblank.log.err`.
Read-only pass, nothing modified.

## Recommended fix

**Root cause:** `kernel_vblank_tick()` in `tools/xboxrecomp/src/kernel/kernel_bridge.c:1975-2006` sets two
NV2A *status* registers before raising vector 3 — `PCRTC_INTR_0` (`0xFD600100`) and `PMC_INTR_0`
(`0xFD000100`) — but never touches `PMC_INTR_EN_0` (`0xFD000140`), the corresponding *enable* register.
The game's D3D ISR at `sub_00222FD0` (`0x00222FD0`) requires `[context_field_0 + 0x140]` (i.e.
`*(uint32_t*)(0xFD000140)`) to be **non-zero** as its second gate, or it returns `FALSE` immediately
(`0x00222FEE: test eax,eax; je 0x2230e0` → `xor al,al; ret 8`) — this is exactly the "ISR declined it"
log line. Nothing in the game's own init path (`sub_00223BD6`, `0x00223BD6`) ever writes a non-zero value
to `0xFD000140` either: it explicitly zeroes `PCRTC_INTR_EN_0` (`0xFD600140`) and `0xFD009140`, and leaves
PMC's enable register untouched. Because the NV2A aperture is backed as plain zeroed RAM
(`xbox_memory_layout.c:1532-1560`, "ponytail: plain memory, no register semantics"), that register can
only ever become non-zero if something explicitly writes it — and nothing currently does.

**Concrete fix, smallest surface:** in `kernel_vblank_tick()` (`kernel_bridge.c`, right before the
`BRIDGE_MEM32(... PCRTC_INTR_0) |= ...` lines around 1994), also OR the PCRTC-source bit into
`PMC_INTR_EN_0` before calling `kernel_raise_interrupt`:

```c
#define NV2A_PMC_INTR_EN_0     0x00000140u
...
BRIDGE_MEM32(XBOX_NV2A_REG_BASE + NV2A_PMC_INTR_EN_0) |= NV2A_PMC_INTR_PCRTC;  /* NEW */
BRIDGE_MEM32(XBOX_NV2A_REG_BASE + NV2A_PCRTC_INTR_0)  |= NV2A_PCRTC_INTR_VBLANK;
BRIDGE_MEM32(XBOX_NV2A_REG_BASE + NV2A_PMC_INTR_0)    |= NV2A_PMC_INTR_PCRTC;
```

This mirrors what a real NV2A driver does at device-creation time (program `PMC_INTR_EN_0` once to say
"I care about PCRTC interrupts") and what this specific title apparently expects the aperture to already
contain — the ISR's own tail (`0x002230C9: mov dword ptr [edi+0x140], 0`) *clears* `PMC_INTR_EN_0` after
each accepted interrupt, so on real/emulated hardware something has to re-arm it before the next vblank;
here nothing does, so `kernel_vblank_tick` re-arming it unconditionally on every tick is the least invasive
substitute. Setting it unconditionally rather than trying to find the game's own "arm" call
(`sub_00222F90`, see below — never reached by any statically-resolved caller) avoids depending on an
indirect call the disassembler can't confirm is ever taken.

**Secondary, independent bug worth a follow-up (not blocking this one):** the worker thread seen spinning
3.5M times on `KeWaitForMultipleObjects` (ordinal 158, log lines around `iter4-vblank.log.err:4090+`)
returns `0xC0000001` (`STATUS_UNSUCCESSFUL`) on every call instead of blocking. `bridge_resolve_handle()`
(`kernel_bridge.c:2524-2532`) passes untagged tokens through unchanged as raw `HANDLE` values; if this
title waits on raw guest dispatcher-object pointers (KEVENTs) rather than handle-table tokens, those
pointers become garbage Win32 handles, `WaitForMultipleObjectsEx` fails instantly (`WAIT_FAILED` →
`STATUS_UNSUCCESSFUL`), and the guest loop just retries — a busy-spin burning a full core rather than an
actual wait. Doesn't appear to block the main thread directly, but worth fixing once the vblank path is
verified, since it wastes CPU and could mask/alter timing once frames start advancing.

---

## 1. The runtime's synthetic vblank

`kernel_vblank_tick()`, `tools/xboxrecomp/src/kernel/kernel_bridge.c:1975-2006`, gated by `getenv("RECOMP_VBLANK")`:

```c
1991	    if (!xbox_GetConnectedInterrupt(NV2A_VECTOR))
1992	        return;
1993	
1994	    BRIDGE_MEM32(XBOX_NV2A_REG_BASE + NV2A_PCRTC_INTR_0) |= NV2A_PCRTC_INTR_VBLANK;
1995	    BRIDGE_MEM32(XBOX_NV2A_REG_BASE + NV2A_PMC_INTR_0)   |= NV2A_PMC_INTR_PCRTC;
1996	
1997	    {
1998	        static unsigned n;
1999	        int claimed = kernel_raise_interrupt(NV2A_VECTOR);
2000	        if (n++ < 3)
2001	            fprintf(stderr, "  [NV2A] vblank -> ISR %s\n",
2002	                    claimed < 0 ? "not callable" :
2003	                    claimed ? "claimed it" : "declined it");
```

Every ~16 ms it sets `PCRTC_INTR_0` bit 0 (vblank pending) and `PMC_INTR_0` bit 24 (PCRTC is the source),
then calls the connected vector-3 ISR (`kernel_raise_interrupt`, `kernel_bridge.c:1925-1947`). That helper
pushes a dummy return address, the `PKINTERRUPT` token, and the `ServiceContext`, calls the recompiled
routine, and returns `g_eax & 1` — i.e. it takes the guest `BOOLEAN` return value at face value: 1 ⇒
"claimed it", 0 ⇒ **"declined it"** (the exact string grepped from `kernel_bridge.c:2003`, also present
verbatim in `src/usb/ohci.c:557` for the unrelated OHCI vector). `kernel_vblank_tick` does nothing further
with a decline — no retry, no fallback path — it just logs and moves on to the next tick. Because the ISR
declines every time (see §2), `KeInsertQueueDpc` (`kernel_bridge.c:1876-1911`, the DPC ring the timer thread
drains via `kernel_drain_dpcs`, `kernel_bridge.c:2010-2018`) is never reached, so no DPC is ever queued for
this interrupt and `kernel_drain_dpcs` has nothing to run.

## 2. The game's D3D ISR — `sub_00222FD0`

`tools/xboxrecomp/tools/disasm/output/asm/D3D.asm:29646-29742`. Full disassembly quoted below (elided
where noted); `esi` = `ServiceContext` (`0x00236398`, the value `KeConnectInterrupt` was given for vector
3), `edi` = `[esi]` = the NV2A register-aperture base pointer the game itself stored there at init time.

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Two, and only two, gates return `FALSE` (decline): `[ServiceContext+0xa0] == 0`, or
**`[NV2A_base + 0x140] == 0`** — i.e. `PMC_INTR_EN_0`. Every other branch (whether `PMC_INTR_0` bit 24 is
set or not, whether the retrace-port read says active or not) funnels into the shared tail at `0x2230BE`,
which always queues a DPC and returns `TRUE`. So the runtime's own write to `PMC_INTR_0`/`PCRTC_INTR_0`
(§1) is not actually what gates accept/decline here — it's gate 2, `PMC_INTR_EN_0`, that the runtime never
touches.

`edi = [esi]` is confirmed to be the raw NV2A register base `0xFD000000` by the device-init routine
`sub_00223BD6` (`D3D.asm:30859-30874`), which is the function that populates the context struct in the
first place:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This confirms the register-offset mapping given in the task (PMC block at +0x000, PCRTC at +0x600000) and
that the game's own init explicitly zeroes the *other* two enable registers it cares about but never writes
`PMC_INTR_EN_0` here. A tiny two-instruction helper, `sub_00222F90` (`D3D.asm:29580-29589`), does exactly
`*(target + 0x140) = this->0xb4` — i.e. it looks like the "arm PMC_INTR_EN_0 from a cached enable mask"
routine — but `functions.json` shows `"called_by": []` for it (`functions.json:269337-269349`) and no
`call 0x222f90` appears anywhere in the corpus, so the disassembler could not find a static caller; it is
presumably only reached through an indirect/vtable call the tool didn't resolve. No DPC routine address or
vblank counter VA could be confirmed with certainty from static disassembly alone (see §3's caveat about
`0x00234770` below); `sub_00220344` (called from the ISR's signal path at `0x002230B9`) and whatever
`xbox_KeInsertQueueDpc`'s registered `DeferredRoutine` is are the two candidates worth breakpointing if a
future pass wants to name them precisely.

## 3. The "main thread hang" evidence is stale stack, not a live call frame

The watchdog dump in `logs/iter4-vblank.log.err` (around line 4146, `[WATCHDOG] no exit after 10s; guest
esp=0x00F7F874`) is a **raw scan of guest stack memory**, not a walked call stack — it prints whatever
32-bit values currently sit at successive stack addresses, including ones below the live frame that were
never overwritten by later pushes/pops. `0x00234770`, which appears four times in that dump
(`GS 00F7F87C/00F7F880/00F7F894/00F7F8A4`), is **not code** — `xrefs.json` shows every reference to it is
`"type": "data_read"`, and it is in fact a plain DWORD *variable*: the push-buffer/command-ring write
pointer used by `sub_00213E50` (`D3D.asm:620-643`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`GS 00F7F8A0 FD000000` in the same dump is the NV2A base pointer value (`edi` inside the ISR), and
`GS 00F7F884 0021EF70` is the `ret` address of `sub_0021EF60` (`D3D.asm:22054-22068`) — both consistent with
this being leftover data from an earlier command-submission/ISR pass through this same stack region, not
the thread's current instruction pointer. **No reliable "the main thread is blocked at VA X" answer can be
extracted from this log with static tools alone** — the regs at the watchdog point (`eax=2 ecx=3
edx=81202000 ebx=2 esi=D edi=A`) don't obviously decode to a wait primitive either. What the ring-buffer
code (`sub_00213E50` → `sub_0021EF00`/`sub_0021EF10` → `sub_0021EDC0`, `D3D.asm:21845-21993`) *does* show is
a fence-style allocator that, when the command ring fills, calls into a completion-tracking routine that
depends on GPU work having been consumed — i.e. it depends on the same DPC/interrupt chain that gate 2 in
§2 currently blocks. Getting the ISR to stop declining is the precondition for confirming whether this ring
allocator is in fact where the main thread now sits; a live debugger attach (or `RECOMP_NV2A_TRACE`) would
be needed to confirm the exact frame once §2's fix is in.

## 4. Worker thread spin — `KeWaitForMultipleObjects` never blocks

Routine `0x001F683A` (ctx `0x001F98A2`, stack top `0x01181FF0`) calls ordinal 158
(`KeWaitForMultipleObjects`) in a tight loop — `[KERNEL] ordinal 158 x3508820` in the same watchdog window,
each call returning `0xC0000001` (`STATUS_UNSUCCESSFUL`). Tracing the bridge:

- `bridge_KeWaitForMultipleObjects` (`kernel_bridge.c:3888-3913`) resolves each of the guest `Objects[]`
  entries through `bridge_resolve_handle(BRIDGE_MEM32(objects_va + i*4))` before calling the native
  `xbox_KeWaitForMultipleObjects` (`kernel_sync.c:266-287`), which is a thin wrapper over
  `WaitForMultipleObjectsEx`.
- `bridge_resolve_handle` (`kernel_bridge.c:2524-2532`):
  ```c
  static HANDLE bridge_resolve_handle(uint32_t token)
  {
      if ((token & 0xFF000000u) == BRIDGE_HANDLE_TAG) {
          uint32_t i = token & BRIDGE_HANDLE_MASK;
          return (i > 0 && i < BRIDGE_HANDLE_MAX) ? s_handle_table[i] : NULL;
      }
      /* Untagged: synthetic/dummy handle -- pass through unchanged. */
      return (HANDLE)(uintptr_t)token;
  }
  ```
  Only tokens tagged with `BRIDGE_HANDLE_TAG` go through the real handle table; anything untagged — which
  is exactly what a raw Xbox-kernel dispatcher-object pointer (e.g. a `PKEVENT` guest VA, which is how
  `KeWaitForMultipleObjects` is normally called on real Xbox — no handle table involved at all) looks like
  — is cast straight to a `HANDLE` and handed to Win32. That's a garbage handle value to
  `WaitForMultipleObjectsEx`, which fails immediately (`WAIT_FAILED`) rather than blocking.
- `xbox_wait_result_to_ntstatus` (`kernel_sync.c:183-195`) maps `WAIT_FAILED` (and every other
  unrecognized result) to `STATUS_UNSUCCESSFUL` = `0xC0000001` — the exact value seen in the log.

Net effect: this thread never actually waits; it fails instantly and the guest loop retries, so it spins at
full CPU rather than blocking on its intended events. This looks independent of the vblank/ISR issue (no
evidence it's what the main thread needs), but is worth a follow-up once M2's primary fix is verified, both
for CPU cost and because it means any real KEVENT this thread should be reacting to is silently never
observed.

## 5. Toolkit expectations / prior art (Burnout 3, env switches)

- `docs/technical/burnout3-reunification.md` is about a **kernel/threading "swap"** (reusing xboxrecomp's
  kernel under Burnout 3's own code) — it does not discuss vblank, PCRTC, or swap-as-in-buffer-flip at all;
  Burnout 3 in that document explicitly plans to "keep Burnout 3's nv2a local indefinitely" rather than use
  the toolkit's NV2A path, so there is no cross-title precedent here for how a title should get past first
  vblank. No other file under `docs/technical/` or `docs/pipeline/` mentions vblank, PCRTC, ISR, or
  `BlockUntilVerticalBlank` — the only design rationale that exists lives in the code comments already
  quoted in §1 (`kernel_bridge.c:1949-1966`), which name Half-Life 2's loader hang as the reason
  `RECOMP_VBLANK` was added, and explicitly note it's a **fixed 60 Hz synthetic tick**, not a real display
  timing source, and does not implement field/interlace handling.
- `xbox_memory_layout.c:1532-1560`'s own comment states the design intent plainly: the NV2A aperture is
  "backed as ordinary zeroed RAM... plain memory, no register semantics," good enough to get through
  init, and that "a spin loop waiting for a bit to *set* would hang rather than fault — if that shows up,
  the fix is to bridge the D3D8 entry point that owns the loop, not to start emulating NV2A." That is
  effectively what's happening here (a bit — `PMC_INTR_EN_0` — never gets set), though the fix proposed in
  this doc (arm the bit from the tick, §"Recommended fix") is smaller and more general than bridging a
  specific D3D8 entry point, and is consistent with the toolkit's own stated philosophy of staying plain
  memory rather than adding real NV2A register semantics.
- Related env switches found (`grep -rn getenv` across `src/kernel`, `src/video`):
  - `RECOMP_VBLANK` — enables the synthetic 60 Hz vblank tick (`kernel_bridge.c:1982`), the only lever that
    drives vector-3 interrupts at all.
  - `RECOMP_PB_SCAN` / `RECOMP_PB_EXEC` / `RECOMP_PB_EXEC_VERBOSE` — push-buffer survey/execution
    (`nv2a_pb_scan.c`, `nv2a_pb_exec.c`); explicitly diagnostic/read-mostly tooling ("nothing here executes
    them, so the framebuffer stays black however far the game gets," `nv2a_pb_scan.c:1-9`) for inventorying
    or optionally executing NV2A methods, unrelated to interrupt/vblank delivery.
  - `RECOMP_NV2A_TRACE` — traces NV2A aperture pokes (`xbox_memory_layout.c:1560-1562`), shares its poll
    with the pushbuffer survey.
  - `RECOMP_FB_WINDOW` / `RECOMP_FB_DUMP` — an independent debug window (`fb_present.c:180-214`) that
    polls whatever the game last set as the framebuffer VA/pitch via `xbox_FramebufferWindowSet` and blits
    it every 16 ms on its own thread; it is not gated on vblank/DPC completion and would not by itself
    unblock a title waiting on the vblank interrupt.
  - `src/nv2a/` (`nv2a_core.c`, `nv2a_mmio_hook.c`) is a **separate, more complete NV2A register emulation**
    ported from xemu, with its own `NV2AState`, a VEH-based MMIO hook, and real per-block interrupt-enable
    semantics — but `nv2a_hook_init()` is only ever called from within `nv2a_mmio_hook.c` itself
    (`grep -rn nv2a_hook_init` finds no caller elsewhere in `src/`), so **this subsystem is not wired into
    the running game** for Def Jam; the aperture the game actually touches is the plain-RAM one from
    `xbox_memory_layout.c`. If the plain-RAM approach in this doc's recommended fix proves too blunt later
    (e.g. once more titles need real register semantics), wiring this existing-but-unused emulation in is
    the documented escape hatch rather than hand-rolling more special cases in `kernel_bridge.c`.

## Evidence index

| Claim | File : line |
|---|---|
| "declined it" log site | `tools/xboxrecomp/src/kernel/kernel_bridge.c:2003` |
| `kernel_vblank_tick` register writes / ISR call | `tools/xboxrecomp/src/kernel/kernel_bridge.c:1975-2006` |
| `kernel_raise_interrupt` (BOOLEAN return handling) | `tools/xboxrecomp/src/kernel/kernel_bridge.c:1925-1947` |
| `KeInsertQueueDpc` / DPC queue drain | `tools/xboxrecomp/src/kernel/kernel_bridge.c:1876-1911`, `2010-2018` |
| D3D ISR `sub_00222FD0` disassembly | `tools/xboxrecomp/tools/disasm/output/asm/D3D.asm:29646-29742` |
| `sub_00222F90` (unreferenced PMC_INTR_EN_0 arm helper) | `tools/xboxrecomp/tools/disasm/output/asm/D3D.asm:29580-29589`; `functions.json:269337-269349` |
| Device-init writes `0xFD000000`/`0xFD600140`/`0xFD009140` | `tools/xboxrecomp/tools/disasm/output/asm/D3D.asm:30859-30874` (`sub_00223BD6`) |
| NV2A aperture = plain zeroed RAM (design comment) | `tools/xboxrecomp/src/kernel/xbox_memory_layout.c:1528-1562` |
| `0x00234770` is a data variable, not code (xrefs) | `tools/xboxrecomp/tools/disasm/output/xrefs.json:650840-650869` |
| Ring-buffer alloc / fence chain | `D3D.asm:620-643` (`sub_00213E50`), `21845-22068` (`sub_0021EDC0`/`sub_0021EF00`/`sub_0021EF10`/`sub_0021EF60`) |
| Watchdog raw stack dump | `logs/iter4-vblank.log.err:4146-4176` |
| Worker-thread spin evidence | `logs/iter4-vblank.log.err:4090-4126` |
| `bridge_KeWaitForMultipleObjects` | `tools/xboxrecomp/src/kernel/kernel_bridge.c:3888-3913` |
| `bridge_resolve_handle` (untagged pass-through) | `tools/xboxrecomp/src/kernel/kernel_bridge.c:2524-2532` |
| `xbox_wait_result_to_ntstatus` (`WAIT_FAILED` → `0xC0000001`) | `tools/xboxrecomp/src/kernel/kernel_sync.c:183-195` |
| Burnout 3 doc has no vblank/PCRTC content | `tools/xboxrecomp/docs/technical/burnout3-reunification.md` (grep, no hits) |
| `RECOMP_PB_SCAN`/`RECOMP_PB_EXEC` are read-mostly diagnostics | `tools/xboxrecomp/src/kernel/nv2a_pb_scan.c:1-46`, `nv2a_pb_exec.c:1271,1547,1664` |
| `RECOMP_FB_WINDOW` independent of vblank/DPC | `tools/xboxrecomp/src/video/fb_present.c:180-219` |
| Unused xemu-derived NV2A emulation, not wired in | `tools/xboxrecomp/src/nv2a/README.md`; `grep -rn nv2a_hook_init` (no external caller) |
