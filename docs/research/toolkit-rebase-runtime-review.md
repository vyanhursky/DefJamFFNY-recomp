# Toolkit rebase: kernel, saves, USB and audio carry-forward review

2026-10-03. Read-only source review; no build, test or guest run performed for this report.

## Scope and evidence

Compared the selected patch files against immutable upstream trees: old pin
`6f55eaa29d369860c950f442649e23ca86a3c275` and new target
`1409a7d7801d3e931fb1074be6104209ddd9a33e`. The conclusions concern semantic coverage,
not whether an old diff happens to apply. The root agent owns migration and measured acceptance.

Reviewed all 35 requested patches:

- Kernel/memory/clocks: 0001, 0011, 0018, 0032, 0059, 0065, 0067, 0069, 0074, 0077, 0103.
- Files/saves: 0006, 0025, 0030, 0104.
- USB/input: 0007, 0024, 0029, 0038, 0041, 0044, 0045, 0046, 0047, 0063, 0064, 0093.
- Audio: 0002, 0012, 0016, 0048, 0068, 0070, 0076, 0102.

Read the upstream changes in `src/kernel/{kernel_bridge.c,kernel_hal.c,kernel_memory.c,
kernel_path.c,kernel_file.c,kernel.h,xbox_memory_layout.c,xbox_memory_layout.h}`,
`src/usb/{ohci.c,usb_gamepad.c,usb_gamepad.h,CMakeLists.txt}` and
`src/apu/{apu_core.c,apu_shim.h,apu_dsp.c,apu_vp.c,apu_xaudio2.c,apu_state.h}`.
Checked downstream anchor callers in `src/recomp_manual.c`,
`src/hooks/d3d11_translator.c`, and the script contract in `scripts/harness.py`,
`scripts/regress.py`, `scripts/pad-chain.py`, and `tests/golden/README.md`.

Classification below:

- **Keep**: behavior absent upstream; carry the final behavior, adapting context as necessary.
- **Drop/fold**: exact behavior covered upstream or the historical intermediate patch is superseded.
- **Split/rework**: overlapping implementation or changed API; retain the specified pieces of both.

## Findings that determine the merge

1. Upstream's DPC queue lock and `KDPC.Inserted` handling are stronger than 0065. Keep
   upstream insert/remove/drain; do not replace it with the old SRW-lock-only implementation.
   This does not cover 0032's exclusion between a guest at DISPATCH_LEVEL and a running DPC.
2. Upstream publishes actual IRQL in guest `fs:[0x24]`, counts raised threads and brackets
   host-run ISRs/DPCs. Preserve those changes while carrying 0032's dispatch exclusion.
   A global interrupt hold-off is a different operation from a DPC mutual-exclusion lock.
3. Physical-address arithmetic is upstream, but our recorded inverse translation is not.
   The upstream image-range/high-water heuristic does not replace the kernel's actual
   answers for low guest buffers outside the loaded image. Preserve the map and its
   generation cache, and record from the unified public `xbox_MmGetPhysicalAddress` path.
4. `RECOMP_PAD_SCRIPT` is an incompatible shared name. Upstream expects
   `<milliseconds>:<button>[+button][:hold]`, with time starting at the first report;
   our routes expect `button:from:to[:period:hold]` in seconds and `@anchor` tokens.
   Preserve our existing contract and anchor APIs. Keeping upstream's parser alone will
   break the regression pipeline without a compile error.
5. Upstream's USB devices are direct-root pads and its public pad functions now take a
   pad index. Our validated Controller S topology contains a hub on HC0 root port 3,
   with the pad on child port 1; game-port ordering is roots 3, 4, 1, 2. Keep that
   topology and mapping while adapting signatures. Two-pad support remains a backlog
   criterion; do not infer that upstream's four-pad code validates our topology.
6. Upstream APU interrupts execute guest ISR code on the APU frame thread. Our interrupts
   execute on the pinned kernel timer thread. Use exactly one delivery route and retain
   single-guest-core semantics. Keep upstream's per-frame APU lock release and its DSP
   doorbell poll while the frontend is trapped/halted.
7. Upstream's mixdown sums all even bins left and all odd bins right. Our measured audio
   path downmixes the six speaker bins, including center/LFE/rears, with headroom. These
   are different audible outputs, not equivalent fixes. Preserve Def Jam's accepted
   behavior; any general mixdown policy can be addressed after the rebase baseline.
8. Guest boot clocks, core affinity, accurate console memory statistics, PTIMER origin
   correction, the timer rearm race, lazy dispatcher-object shadows, saves routing and
   directory search cleanup are still needed.

## Patch-by-patch recipes

### Kernel, memory and clocks

| Patch | Decision | Recipe and dependencies |
|---|---|---|
| 0001 kernel interrupts, waits and PTIMER | **Split/rework** | Keep lazy `ke_object_resolve` for inline events/semaphores; object resolution in KeSetEvent and both waits; thread-object stand-ins/refresh; recorded physical-to-virtual map; diagnostic totals. Bring PTIMER across as the **final** implementation after 0015/0021/0059/0074/0077, not the initial immediate-summary version. Preserve upstream queue locking, KDPC.Inserted, IRQL brackets and unrelated bridge/async-I/O safety additions. Record physical mappings in the public memory function used by the upstream bridge. Apply 0103 to the lazy resolver too. See existing stand-in size issue below. |
| 0011 console memory statistics | **Keep** | Keep 64 MB accounting minus 2 MB kernel allowance, XBE image size, live heap blocks and contiguous allocations; keep `xbox_HeapLiveBytes` declaration/implementation. Upstream still reports host-memory-derived available pages. This is required to avoid Def Jam's undersized 18 MB main arena and failed loader allocations. |
| 0018 guest clocks and one guest CPU | **Keep/rework** | Keep the ten-second guest boot epoch, guest KeTickCount/performance/interrupt time, `xbox_GuestUptimeMs`, and `xbox_PinToGuestCore`; fold the fine-QPC uptime from 0067. Keep upstream's separate robust absolute SystemTime implementation (INIT_ONCE, QPC/FILETIME and overflow-safe scaling). Audit every newly introduced upstream guest-code entry, especially APU IRQ, for affinity. Host GPU/audio work must remain able to run independently. |
| 0032 DISPATCH_LEVEL excludes DPCs | **Split/rework** | Keep dispatch exclusion and real KeRaiseIrqlToSynchLevel (26). Merge into upstream `irql_changed` rather than replacing it: retain `fs:[0x24]` publishing, raised-count transitions and holder diagnostics. DPC calls need the dispatch lock **and** upstream EnterInterrupt(2)/LeaveInterrupt brackets. Runtime ISR threads must avoid acquiring the guest dispatch lock on their own raises. Preserve upstream ISR EnterInterrupt(16) brackets. |
| 0059 64-bit kernel count | **Keep/fold** | Upstream still has `static int g_kernel_call_count` and associated `%d` formats. Keep the 64-bit counter and all matching formats. Fold PTIMER timing/rate diagnostics into the final PTIMER implementation. |
| 0065 DPC queue lock | **Drop queue portion; split diagnostics** | Upstream commit `1dc92c8` protects insert/remove/drain with an INIT_ONCE critical section, rejects an already inserted KDPC, clears Inserted before invocation, and supports cancellation. This covers and improves our queue synchronization. Retain the OHCI two-second-MIE-masked diagnostic if useful; it is absent upstream and explains a lost USB DPC. Never hold the queue lock during guest invocation. |
| 0067 fine vblank and guest clocks | **Keep/fold** | Upstream vblank remains coarse GetTickCount64 + 16. Keep QPC period/deadline accumulation, lag skip, `RECOMP_VBLANK_HZ`, measured rate logging and fine guest uptime. Merge with the final GPU interrupt model separately; do not restore the old initial 0001 delivery mechanics. |
| 0069 thread priority reaches host | **Keep/rework** | Resolve the guest thread object through the 0001 stand-in table to the host thread handle before SetThreadPriority. Upstream's bridge still passes a translated object pointer as if it were a host HANDLE. Preserve return-value normalization and diagnostics. Upstream now also bridges KeQueryBasePriorityThread; check its corresponding stand-in interpretation rather than assuming it follows the fixed setter. |
| 0074 PTIMER counts from reset | **Keep/fold** | Essential correction: `now = origin_count + elapsed_since_reset`; do not add elapsed since reset to the last value issued. Preserve reset detection and periodic measured alarm rate. Upstream does not implement this PTIMER clock. |
| 0077 PTIMER stall diagnostics | **Keep/fold** | Carry future-deadline and fired-but-not-rearmed warnings, rate limited, into final PTIMER. These distinguish slow clock, lost alarm and missing guest rearm. |
| 0103 timer signal not lost on rearm | **Keep** | Reset host event and guest SignalState **under g_timer_lock before arming**. Upstream still resets after releasing the timer lock. Also create/check lazy object shadow under g_ke_shadow_cs so setter and waiter cannot create distinct events; upstream has no lazy resolver. |

### Files and save storage

| Patch | Decision | Recipe and dependencies |
|---|---|---|
| 0006 writable TDATA | **Keep/fold** | Keep the specific `Partition1\\TDATA\\` rule before the general Partition1/disc rule, to `save\\TitleData`. Combine with final 0030 storage behavior; the old comment about UDATA remaining on disc is obsolete. |
| 0025 status mapping and kernel call trail | **Split/rework** | Keep Windows ntdll RtlNtStatusToDosError lookup, kernel trail armed by paths, directory result diagnostics and bridge event/APC arguments. Upstream expanded the portable status table (`bc699b0`, includes timeout/reparse/buffer overflow/EOF/etc.); retain this larger fallback instead of restoring our earlier limited one. Preserve upstream shared POSIX `xbox_LastFileError`/`xbox_LastHostPath` placement. Passing event/APC arguments does not by itself implement asynchronous completion; no new claim of async correctness is warranted. |
| 0030 writable UDATA | **Keep/fold** | Keep both Partition1/UDATA and bare UDATA routing to `save\\UserData`, and first-run disc template copying without overwriting existing saves. Upstream path translation has no corresponding rules. Preserve original data and save-guard discipline. |
| 0104 closed directory drops search | **Keep** | Retain `xbox_dir_context_drop` under the directory lock and call it on the resolved native handle before CloseHandle, guarded to Windows. Upstream NtClose already calls `bridge_forget_async_handle(raw_handle)`; keep **both** cleanup operations. Dropping async metadata does not dispose of a FindFirstFile search. |

### USB and input pipeline

| Patch | Decision | Recipe and dependencies |
|---|---|---|
| 0007 physical OHCI addresses/frame clock | **Split/rework** | Upstream covers two-window pointer checking, bus resolution and multi-TD descriptor continuation, but uses an image/high-water heuristic. Keep our exact physical map lookup first, apply resolution to pre-walk eligibility checks as well as dereferences, retain transfer destination/read-back diagnostics. Fold clock behavior to final 0064, and retain pad bMaxPacketSize0=32 (upstream remains 8). Use upstream's cached control reply, WDH ownership/ack, ack-sequence stuck-source guard and OUT endpoint separation. |
| 0024 Controller S hub, periodic list and XID | **Split/rework** | Keep usb_hub.c/.h and CMake registration, hub/default-address routing, reset/enable/class requests, per-device control state and status-change NAKs. Keep unchanged-pad report NAK and final 0064 periodic cadence. XID/capability/GET_REPORT portions are upstream-covered; retain upstream's broader request support while preserving accepted class SET_REPORT/SET_IDLE. Adapt to indexed pad signatures below. Retain upstream shared done queue for control/periodic/bulk, WDH back-pressure and no control-state reset on rumble endpoint OUT. |
| 0029 OHCI clock declaration | **Drop/fold** | Historical compile-order fix, not a separate feature. Upstream has no `ohci_frame_now` yet. If final 0064 helper is introduced, declare before the register read callback (or define before it); preserve the final clock without carrying an isolated old patch. |
| 0038 script anchor and sampled press log | **Keep/rework** | Keep `xbox_ScriptSeconds`, process/file-open anchor semantics, per-step `[PAD] script:` evidence and polling totals. Upstream's script epoch is first report and its syntax differs. Downstream timed frame captures call this API, so parser substitution alone is insufficient. Preserve upstream portable path globals while adding anchor behavior. |
| 0041 sample every 4 ms/minimum hold | **Keep/rework** | Upstream does not have the independent sampler/latch or minimum-hold guard. Keep real-pad fast-press capture and `RECOMP_PAD_MIN_HOLD_MS` (120 default), adapting latches/hold state per pad if indexed APIs retained. Do not confuse upstream 150 ms synthetic script spans with a real-input hold guarantee. |
| 0044 pad on game port 1 | **Split/rework** | Upstream covers four root-port write/power semantics but defaults to two root ports, raw USB port 0 and direct pads. Preserve our four ports, HC0 root3 default, `RECOMP_PAD_PORT=1..4` mapping 3/4/1/2, and hub reset tied to the correct root/controller. Keep upstream's write-1-clear **before** starting a new reset so an old PRSC clear cannot erase the just-generated change. Raw `RECOMP_USB_PORT`/`RECOMP_USB_HC` are not the same interface as game-port mapping. |
| 0045 pad script file anchors | **Keep/rework** | Keep `xbox_FileOpenSeconds("substring#N")`, registered watches and `@anchor` parser transitions that close earlier stages when a later screen arrives. Upstream `@file` instead means load a script file; resolve the shared syntax deliberately, with our current harness unchanged. |
| 0046 anchor events | **Keep** | Preserve public `xbox_NoteAnchorEvent`: frontend tracing in src/recomp_manual.c uses it to anchor screen/function events. Upstream has no equivalent. |
| 0047 longer script chains | **Keep/fold** | Preserve 32 watches, 4096-character script limit with refusal rather than truncation, and 256 tokens/log markers. Upstream PAD_SCRIPT_MAX=256 counts differently parsed steps and does not cover anchor watch capacity or safe refusal of our syntax. |
| 0063 repeating script presses | **Keep/fold** | Preserve `name:from:to:period:hold` parsing and anchored phase. This is used to drive long fight spans; upstream has no equivalent in its timeline parser. |
| 0064 millisecond frame clock | **Keep/rework** | Keep QPC clock shared by register/HCCA, missed-frame periodic walks capped to one 32-slot lap, and report/poll diagnostics. Upstream increments four frames per sleep pass, retains read-count-derived register values, and sweeps all 32 periodic slots each pass. That prevents starvation but is different cadence. Do not combine both clocks or both walkers. Retain upstream control/periodic/bulk done-queue ownership and IRQL gating. |
| 0093 scripts ignore host pad | **Keep/rework** | Keep script-present default that disables host input, with `RECOMP_PAD_HOST=1` escape hatch. Upstream always merges host input and scripts. A plugged-in drifting stick can make an otherwise deterministic route fail. Apply consistently to sampler and report path. |

### Audio and related memory behavior

| Patch | Decision | Recipe and dependencies |
|---|---|---|
| 0002 AC97 reset, IRQ summary, contiguous base | **Split/rework** | Upstream `35a74ea` supplies synchronous AC97 write-trap reset completion, stronger than this patch's asynchronous clearing; use upstream trap. Upstream `423263b` also reserves first contiguous page; drop duplicate allocator change. Upstream relocates main TIB to 0x4000 for 16 KB host pages; our 0x8000 also clears them, but no evidence requires 0x8000 specifically—retain upstream placement unless a downstream address dependency is found. GPU summary preservation belongs to final 0015/0021 model and parent GPU audit, not a replay of the initial 0002 ack bypass. |
| 0012 dynamic DSP doorbell | **Keep/rework** | Upstream still requires explicit RECOMP_APU_DSP_ACK addresses and incorrectly documents doorbell as non-derivable. Keep the automatic GPSADDR SGE[0]+0x810 path, derived each poll as guest programming changes. Insert into upstream public `mcpx_apu_dsp_ack_poll`, retaining its frame-thread call regardless of frontend trap/halt. Prefer shared physical resolver for SGE reads where appropriate; preserve explicit-address override. |
| 0016 APU physical window/trace | **Split/rework** | Upstream covers routing all physical helpers and streaming ADPCM copies through public `mcpx_apu_phys`; keep this symbol and callers while giving its implementation our exact recorded-map/generation cache semantics. Keep notifier count, voice-on/off and status/list diagnostics. Upstream image/high-water fallback is not exact for non-image low buffers. Requires 0001 recorder plus map generation. |
| 0048 DSP memories plain | **Drop** | Exactly covered by upstream `bdfd497`: only registers/VP 0x00000..0x2FFFF trapped; GP/EP 0x30000..0x7FFFF plain RAM. Preserve upstream implementation. |
| 0068 audible APU output | **Split/rework** | Keep XAudio2 accumulator of the DSP's 256 samples per output period instead of zeroing/repeating into 1024, rate-aware per-voice interpolation/reset handling, six-speaker downmix/headroom, final PCM/peak/routing/voice diagnostics. Upstream monitor/output and rate-ignoring resampler remain unchanged. Retain upstream underrun loop limit and per-frame APU mutex release. Its new all-bin even/odd mixdown conflicts with our accepted speaker downmix; choose one policy explicitly. |
| 0070 APU interrupts | **Split/rework** | Upstream `591dcb9` covers line assertion and set_irq processing, plus vector-5 ISR delivery with worker stack/TIB/IRQL brackets from APU frame thread. Our polling API `xbox_ApuIrqPending` and timer-thread delivery are absent. Recommended baseline-preserving carry: keep line bookkeeping and locked APU fairness improvements, export pending status, deliver exactly once from pinned kernel timer thread using existing generic interrupt/DPC path. Disable the second APU-frame delivery path. If frame-thread delivery is chosen instead, reconcile guest affinity/IRQL/dispatch locking first; do not pin all host audio work by accident. |
| 0076 output diagnostics | **Keep/fold** | Carry XAudio2 dropped/starved counters and output reports; voice F8..FA PCM dumps remain useful Def Jam diagnostics. Fold into 0068's final audio implementation. Upstream has none of these counters/capture hooks. Captures contain game audio and remain local. |
| 0102 APU trace length | **Keep/fold** | Preserve RECOMP_APU_TRACE=n configurable report budget (default 12), with notifier/voice status from 0016. Upstream lacks the status trace rather than merely using a different budget. |

## Public APIs and integration order

Upstream signatures that invalidate a mechanical overlay:

```c
int usb_gamepad_control(int pad, const UsbSetup *setup, uint8_t *out, int max);
int usb_gamepad_report(int pad, uint8_t *out, int max);
uint8_t usb_gamepad_address(int pad);
int usb_gamepad_configured(int pad);
#define USB_GAMEPAD_MAX 4
uint8_t *mcpx_apu_phys(uint64_t addr);           /* apu_shim.h */
void mcpx_apu_dsp_ack_poll(MCPXAPUState *d);     /* apu_state.h */
int xbox_IrqlBlocksInterrupts(void);
int xbox_IrqlRaisedCount(void);
int xbox_IrqlEnterInterrupt(int level);
void xbox_IrqlLeaveInterrupt(int saved);
int xbox_IrqlTransitions(void);
void xbox_IrqlDumpHolders(void);
ULONG_PTR __stdcall xbox_MmGetPhysicalAddress(PVOID BaseAddress);
```

`usb_hub.c` currently calls `usb_gamepad_reset(void)` directly. Carrying the indexed
API requires an explicit `usb_gamepad_reset(int pad)` implementation and adapting
hub/control/report/address callers; copying the old header silently discards upstream
multipad API changes. A single tested hub can initially address pad 0; extending that
to multiple hubs needs separate routing/state and measurement, not an assumption.

Our required public support APIs remain absent upstream:

```c
uint32_t xbox_PhysicalToVirtual(uint32_t pa);
uint32_t xbox_PhysMapGeneration(void);
uint32_t xbox_HeapLiveBytes(void);
ULONGLONG xbox_GuestUptimeMs(void);
void xbox_PinToGuestCore(void);
int xbox_DispatchLockEnter(void);
void xbox_DispatchLockLeave(void);
void xbox_IrqlInterruptThread(void);
KIRQL __stdcall xbox_KeRaiseIrqlToSynchLevel(void);
void xbox_KernelTrail(int calls);
double xbox_ScriptSeconds(void);
double xbox_FileOpenSeconds(const char *spec);
void xbox_NoteAnchorEvent(const char *text);
void xbox_dir_context_drop(HANDLE FileHandle);  /* Windows directory backend */
int xbox_ApuIrqPending(void);                  /* if timer delivery retained */
```

Carry the final integrated families in dependency order:

1. Dispatcher objects/timer races, console statistics, physical recorder, guest clocks
   and affinity. Put physical recording behind the public memory function so both
   dispatch routes retain the same arithmetic and map population.
2. Final GPU/PTIMER interrupt family with QPC vblank/origin correction, plus dispatch
   exclusion merged into upstream IRQL. Keep upstream DPC queue implementation.
3. Save routing and directory-close/search behavior, preserving portable globals and
   upstream async-handle bookkeeping.
4. Shared script/anchor family, then USB hub/port/cadence and indexed pad adaptation.
5. Audio physical access, dynamic DSP poll, output/resampler/downmix and diagnostics;
   select one guest APU ISR delivery route.

The families can be consolidated as coherent commits; there is no benefit in retaining
intermediate versions only to supersede them in the next patch. Every original patch
still needs a ledger entry pointing at its retained behavior or exact upstream coverage.

## Existing review issues and limits

- **Concrete existing allocation mismatch:** 0001 defines XBOX_OBJ_STANDIN_SIZE=0x100
  and allocates that many bytes, but `xbox_ObjectRefreshThread` writes a DWORD at
  `object + 0x120`. The current pre-rebase bridge retains this. The write is outside
  the requested allocation. This review did not attribute a measured crash to it.
  Root agent should decide whether to fix this bounded defect in the carry-forward
  object commit and validate it, or record it explicitly; do not silently describe
  the existing implementation as bounds-correct.
- Recorded physical inverse lookup is bounded to 512 page entries and uses a
  fallback when unknown; it is stronger evidence than the heuristic where recorded,
  not a complete hardware memory model. The cache generation must remain coupled
  to map updates. This audit did not stress map exhaustion or concurrent updates.
- 0032's bounded DPC lock wait comment says about 200 ms, but the loop includes
  Sleep(1) in its final 1000 iterations. Do not turn that comment into an exact
  timeout acceptance claim. It intentionally permits progress after a stuck guest
  raise; preserve existing diagnostics and examine measured timing if relevant.
- Our sampler/minimum hold and anchor clock implementations have historical
  threading assumptions. Indexed upstream support means global latch/hold state
  cannot automatically be treated as per-controller. No multipad measurement was
  taken here.
- The DSP remains a passthrough/doorbell-ack stub, not DSP56300 emulation. Neither
  our six-bin downmix nor upstream all-bin parity summation proves hardware-equivalent
  effects routing.
- The rare no-sound boot and one-off total debug freeze remain open. This static
  comparison cannot close them, and the timer-signal fix does not establish that
  those two symptoms have the same cause.

Acceptance evidence still belongs to the established pipeline: route/parser contract,
save-guard equality and directory-name checks, P1 input/enumeration and quick real-pad
presses, movie clock/audio position progression, sound output/pitch/center dialogue,
fight/vblank/PTIMER cadence, full regress and the required boot soak. Passing compiler
checks alone would not distinguish the semantic conflicts above.
