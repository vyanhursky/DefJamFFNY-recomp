# Toolkit rebase pending-ledger source audit

2026-10-03. Read-only code review of the candidate under
`C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration`, based on upstream
`1409a7d7801d3e931fb1074be6104209ddd9a33e`. Candidate HEAD at the start of this
audit was CPU topic `7f7eef9`; the runtime changes inspected here were still
uncommitted. Source changed during review as the main agent repaired reported
issues, so symbols are the durable navigation anchors below.

All **96 rows marked pending** in
[the ledger](C:/Users/Vlad/code/defjam-recomp/docs/research/toolkit-rebase-ledger.md)
are mapped below. This supplements the prior
[runtime overlap review](C:/Users/Vlad/code/defjam-recomp/docs/research/toolkit-rebase-runtime-review.md),
the historical patch files, preserved patched toolkit, and cached upstream source.
It does not change the ledger, choose final commit boundaries, or certify game acceptance.

## Meaning of the outcomes

- **Carried**: the final historical behavior has a concrete implementation in the candidate.
- **Mixed**: local behavior survives alongside an upstream replacement or overlapping implementation; the notes identify the upstream-covered part.
- **Superseded**: a historical intermediate implementation is intentionally replaced by the later behavior named in the row. This is not permission to remove that replacement.
- **Partial**: an identifiable portion is retained, but a behavior/performance property is not established or is no longer implemented as before.

These are **source-coverage** outcomes. Every runtime row remains pending full
game validation and assignment to the eventual consolidated runtime commits.
The earlier pre-rebase game baseline is evidence for the preserved toolkit, not
for this candidate.

## Evidence and integration boundaries

I inspected patch-to-file ownership, the candidate implementations, and the
preserved-baseline/upstream differences. I did not edit source, build, run tests,
launch the game, or change Git. The main agent's saved results independently show:

- [runtime library build](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/runtime-build.txt): kernel library linked, with warnings still present;
- [runtime fixtures](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/runtime-fixtures-results.txt): 9/9 passed, including physical address, IRQL, bridge, directory, object paths, audio setting, dispatch and two upstream APU mixdown modes;
- [USB fixture](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/usb-test-results.txt): 1/1 passed;
- [vertex fixtures](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/vsh-test-results.txt): 2/2 passed, including the canonical epilogue and WARP adapter.

Those logs were read, not rerun. They do not establish game timing, audible
six-speaker output, golden parity, soak stability, real-pad responsiveness or two
working guest controllers. HLSL numeric differences were reviewed separately by
the test-pipeline agent; this audit does not repeat that analysis.

Two host defaults are part of the actual Def Jam integration and must accompany
the toolkit update: [main.c](C:/Users/Vlad/code/defjam-recomp/src/main.c) selects
`RECOMP_PAD_SCRIPT_FORMAT=seconds` when unset and `RECOMP_APU_MIXDOWN=six` when
unset. The generic toolkit retains its upstream timeline/all-bin defaults. A
standalone caller of the toolkit cannot assume that the existing anchored
seconds grammar is selected without that integration or an explicit environment
setting. The host also registers `d3d11_translator_frame_end` through
`pgraph_d3d11_set_frame_end_callback` after translator initialization.

## Candidate file key

Each row names these exact candidate files and the implementing symbols. Header
declarations and the corresponding CMake source lists are included with their
implementation where needed.

| Key | Candidate file |
|---|---|
| KB | [src/kernel/kernel_bridge.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/kernel_bridge.c) |
| HAL | [src/kernel/kernel_hal.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/kernel_hal.c) |
| KM | [src/kernel/kernel_memory.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/kernel_memory.c) |
| KT | [src/kernel/kernel_thread.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/kernel_thread.c) |
| KP | [src/kernel/kernel_path.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/kernel_path.c) |
| KF | [src/kernel/kernel_file.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/kernel_file.c) |
| KH | [src/kernel/kernel.h](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/kernel.h) |
| ML | [src/kernel/xbox_memory_layout.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/xbox_memory_layout.c) |
| MLH | [src/kernel/xbox_memory_layout.h](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/xbox_memory_layout.h) |
| PE | [src/kernel/nv2a_pb_exec.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/nv2a_pb_exec.c) |
| PS | [src/kernel/nv2a_pb_scan.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/nv2a_pb_scan.c) |
| VC | [src/kernel/nv2a_vsh_cpu.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/nv2a_vsh_cpu.c), [header](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/nv2a_vsh_cpu.h) |
| VI | [src/kernel/nv2a_vsh_interp.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/nv2a_vsh_interp.c), [header](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/kernel/nv2a_vsh_interp.h) |
| PG | [src/nv2a/nv2a_pgraph_d3d11.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/nv2a/nv2a_pgraph_d3d11.c), [header](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/nv2a/nv2a_pgraph_d3d11.h) |
| DV | [src/d3d/d3d8_device.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_device.c) |
| DC | [src/d3d/d3d8_combiners.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_combiners.c), [header](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_combiners.h) |
| DR | [src/d3d/d3d8_resources.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_resources.c) |
| DS | [src/d3d/d3d8_shaders.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_shaders.c) |
| DST | [src/d3d/d3d8_states.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_states.c) |
| DH | [src/d3d/d3d8_internal.h](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_internal.h), [d3d8_xbox.h](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_xbox.h) |
| XVS | [src/d3d/d3d8_extvs.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/d3d/d3d8_extvs.c) |
| OH | [src/usb/ohci.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/usb/ohci.c) |
| UP | [src/usb/usb_gamepad.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/usb/usb_gamepad.c), [header](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/usb/usb_gamepad.h) |
| UH | [src/usb/usb_hub.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/usb/usb_hub.c), [header](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/usb/usb_hub.h) |
| AC | [src/apu/apu_core.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/apu/apu_core.c), [apu_shim.h](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/apu/apu_shim.h) |
| AD | [src/apu/apu_dsp.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/apu/apu_dsp.c) |
| AV | [src/apu/apu_vp.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/apu/apu_vp.c) |
| AX | [src/apu/apu_xaudio2.c](C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/src/apu/apu_xaudio2.c) |

## All pending rows

| Patch | Source outcome | Exact candidate owners / symbols | Coverage, replacement and remaining caveat |
|---|---|---|---|
| 0001 interrupts, waits, PTIMER | Mixed | KB `ke_object_resolve`, event/wait bridges, `xbox_ObjectForHandle`, `xbox_ObjectRefreshThread`, `kernel_ptimer_tick`; KM `phys_map_record`, `xbox_PhysicalToVirtual`; KH | Lazy object shadows, wait translation, thread stand-ins and physical inverse mapping carried. Map now has one public memory owner, lock, growth and generation; stand-in is 0x124 bytes. Early interrupt/PTIMER mechanics are superseded by 0015/0021/0074/0077, and the DPC queue by upstream. |
| 0002 AC97 reset/summary/contiguous base | Mixed | ML `ac97_write_veh`, `ac97_clear_reset_bits`, contiguous initialization; MLH `XBOX_TIB_MAIN`; KB `xbox_Nv2aIntrUpdate` | Upstream synchronous write-trap reset and reserved first contiguous page replace the local early fixes. Main TIB remains upstream 0x4000, rather than historical 0x8000. Summary preservation belongs to final level-triggered model. No downstream requirement for 0x8000 found. |
| 0003 forward pushbuffer to D3D11 | Carried | PE `nv2a_pb_exec_method`, `draw_primitive`, FLIP_STALL case; PG `pgraph_d3d11_frame_end` | Method and decoded-batch forwarding retained. Direct dependency on the game host was replaced by the registered frame-end callback; host registration is present. |
| 0004 decoded vertices/texture formats | Carried | PG `pgraph_d3d11_draw_ready`, `ready_out`, `ready_tex_fill`, `pgraph_d3d11_set_texture_ready`; PG header | Ready-vertex API and general texture upload survive, with later cache/format fixes folded in. CPU-ready output remains the established pos/d0/t0 transport; see limitations below. |
| 0006 writable TDATA | Carried | KP `s_rules`, `xbox_path_init` | Specific Partition1/TDATA route precedes generic disc routing and selects save/TitleData. Final UDATA behavior is 0030. |
| 0007 OHCI physical addresses/clock | Mixed | OH `phys_to_guest`, `guest_ok`, `guest_ptr`, `rd32`, `wr32`, `ohci_clock`; UP device descriptor | Exact recorded physical map is consulted; upstream legal-window/done-queue handling retained. Final QPC clock supersedes initial GetTickCount clock. Pad endpoint-zero packet size remains 32. |
| 0010 contiguous-window chain peeks | Carried | PE `peek_chain`, `peek_addresses` | Pointer-chain and final-value reads accept the low and contiguous guest windows, rejecting unrelated addresses. |
| 0011 console memory statistics | Carried | KM `xbox_MmQueryStatistics`; ML `xbox_HeapLiveBytes`, contiguous counters; MLH | Reports console 64 MB minus kernel allowance, image, live heap and contiguous allocations rather than host RAM. Arena/loading behavior still needs game measurement. |
| 0012 dynamic DSP doorbell | Mixed | AD `mcpx_apu_dsp_ack_poll`, scratch-doorbell helper; AC `mcpx_apu_frame_thread` | Automatic GPSADDR SGE[0]+0x810 derivation carried with explicit override; upstream public poll is called even while frontend is trapped/halted. |
| 0013 GPU progress/software interrupts | Carried | KB `kernel_nv2a_software_method`, `kernel_nv2a_deliver`; PE NOP path; ML `frame_counters_tick`, fence helpers; KH | Ordered software-method queue and progress/fence-visible registers survive through final level-triggered and pusher implementations. Early clear-after-delivery mechanics are not restored. |
| 0014 palette expansion | Superseded | PE `bind_texture_ready`, `pal_tex_sig`, `tex_stage_method` | Expansion survives as corrected final 0035/0036 behavior. Historical palette method 0x1B0C and once-per-key cache must not be replayed. |
| 0015 hooked NV2A pages/alarm retry | Carried | ML `xbox_Nv2aSetPageHooks`, `xbox_Nv2aRegRead`, `xbox_Nv2aRegWrite`, ack loop; KB `nv2a_rd`, `nv2a_wr`, `kernel_nv2a_deliver`; MLH | Hook-owned pages retain register ownership; summary is regenerated from latched sources and declined interrupts remain retryable. Hook table now supports eight pages. |
| 0016 APU physical addressing/trace | Mixed | AC `mcpx_apu_phys`, `xbox_ApuIrqPending`, status trace; AV notifier/sample paths; KM physical map | Local recorded-map generation cache is adapted to upstream public physical helper and its callers, including ADPCM memcpy. Notifier/voice/status diagnostics survive. |
| 0017 rewritten textures/linear rows | Carried | PE `linear_row_texels`, UV scaling, `bind_texture_ready`; PG `ready_tex_bytes`, `ready_tex_sig`, refill path | Upload width follows pitch for linear textures, with UV normalization; sampled content changes trigger refills. Final palette handling is 0036. |
| 0018 guest clocks/one guest CPU | Mixed | HAL `guest_clock_init`, `xbox_GuestUptimeMs`, time/tick APIs; KB `xbox_PinToGuestCore`, thread/timer entries; KT wrapper; ML ack timing | Ten-second guest epoch and guest thread/timer affinity carried; upstream robust absolute SystemTime retained. Fine uptime is final 0067. This is source coverage of configured entries, not a new claim that every host worker executes guest code on one core. |
| 0019 CPU vertex programs | Mixed | VI upload setters, `nv2a_vsh_run`; VC `nv2a_vsh_run_ready`; PE `nv2a_vsh_active`, `nv2a_vsh_current`, program draw path; kernel CMake | Canonical upstream interpreter/storage replaces the duplicate local CPU interpreter. Local D3D adapter, viewport mirrors and trace activation retained. Numeric fixture passes do not establish full game parity; CPU decode performance caveat is 0073. |
| 0020 pusher follows jumps | Carried | PS `pb_segment`, `nv2a_pb_run`; ML ack executor | Incrementing/nonincrementing packets, old/new jumps, CALL/RETURN and persistent execution position survive in the final walker, which matches the preserved baseline. |
| 0021 level-triggered GPU interrupts | Carried | KB `nv2a_intr_summary`, `xbox_Nv2aIntrUpdate`, `nv2a_latch`, `kernel_nv2a_deliver`; ML inflight/ack gating | PCRTC/PTIMER/PGRAPH sources coexist; summary follows enabled latched status instead of delivery paths clearing one another. |
| 0022 colour write mask | Carried | PG method state and `ready_state`; DST blend state | Guest channel mask reaches D3D colour writes; final zero-mask skip and later alpha-only behavior retained. |
| 0023 blend/alpha-test state | Carried | PG method state, blend/comparison mapping, `ready_state` | Title blend enable/factors and alpha enable/function/reference are applied to ready draws. Equation/constant factors are extended by 0092. |
| 0024 Controller S hub/periodic/XID | Mixed | UH hub requests/status/reset; OH `usb_route`, `usb_dev_control`, TD/periodic paths; UP indexed control/report; USB CMake | Local hub topology, unchanged-report NAKs and per-device state carried; upstream broader XID/GET_REPORT and shared completion handling retained. Public pad APIs are indexed. One passing fixture is not proof of two pads in game. |
| 0025 status errors/kernel call trail | Mixed | KB `bridge_RtlNtStatusToDosError`, directory bridge, `kernel_thunk_dispatch`, `xbox_KernelTrail`; KF directory results; KP trace arming; KH | Windows ntdll status mapping/local call trail retained alongside upstream expanded portable fallback and async metadata. Event/APC arguments survive; this alone does not certify asynchronous completion. |
| 0026 vertex reads stay in guest RAM | Carried | PE `fetch_attr` | Guest-memory bounds remain enforced with 64-bit address arithmetic; inline offset zero remains valid in the separate inline branch. Invalid streams are treated as absent. |
| 0027 stop at software methods | Carried | PS `nv2a_pb_stall`, `s_stall_request`, `nv2a_pb_run`; KB software-method queue/service; ML resumed position | Walk stops at packet boundary and waits for service/ack rather than executing later commands prematurely. RECOMP_PB_NO_STALL remains diagnostic escape. |
| 0028 fence completion in order | Superseded | PE semaphore-release and pattern-write paths; ML `xbox_Nv2aSemaphoreRelease`, `semaphore_release_now`, release queue, catch/follow helpers; PS pump | Ordered release and main-stream checks survive in final 0039/0040/0043/0054/0062 implementation. Submit/PUT mirroring is not restored as the normal completion path. |
| 0029 OHCI declaration order | Superseded | OH forward declaration and final `ohci_frame_now`/`ohci_clock` | Compile-order requirement is satisfied by the final QPC helper; no standalone clock patch needed. |
| 0030 writable UDATA | Carried | KP Partition1/UDATA rules, `xbox_path_init` template copy | Device/bare UDATA maps to save/UserData. First-run disc templates copy without replacing existing saves. Candidate must run against disposable preserved saves. |
| 0031 batch dump lists | Carried | PE `batch_dump_flip`, batch diagnostics | Comma/list frame selection retained and subsequently extended by capture-request dumping. |
| 0032 DISPATCH_LEVEL excludes DPCs | Mixed | HAL `irql_changed`, `xbox_DispatchLockEnter/Leave`, ISR marker and raise/lower; KB `kernel_run_dpc`; OH interrupt gating | Local dispatch exclusion survives with upstream fs:[0x24] publication, raised tracking and ISR brackets. Acquisition precedes publication; release follows downward publication. ISR thread marker prevents self-acquisition. |
| 0034 texture LRU eviction | Carried | PG ready-texture cache hit/create/evict path | 256-entry cache replaces historical 64 entries, timestamps hits and evicts least recently used. All-stage unbinding is final 0100. |
| 0035 palette method 0x1B20 | Carried | PE NV097 palette constant, `tex_stage_method` | Palette decode uses 0x1B20 plus stage stride; CONTROL0 remains enable/LOD at 0x1B0C. |
| 0036 changed/evicted palettes re-expand | Carried | PE `pal_tex_sig`, `bind_texture_ready`; PG `pgraph_d3d11_replace_texture_ready`, status-returning set API | Palette/index signatures, timed checks, forced refill and cache-hit/miss result preserve expansion after content changes and eviction. |
| 0037 depth/texture-stage enable | Carried | PE `tex_update_valid`, texture CONTROL0; PG depth/clear methods and `ready_state` | Disabled stage is invalid; depth enable/function/write mask, format-dependent normalization and guest depth clear values survive. |
| 0038 script epoch/logs | Carried | KP `xbox_ScriptSeconds`, anchor initialization; UP seconds `apply_script`; OH reporting; KH | Process/file anchor clock and sampled-press logs retained. Def Jam main selects seconds format; standalone toolkit default remains upstream timeline. |
| 0039 first ordered release/diagnostics | Superseded | ML `semaphore_release_now`, `s_semaphore_seen`, `fence_note`, ack diagnostics | First release ownership and diagnostics survive in final release/prefetch/follow model; earlier completion heuristics were revised by later patches. |
| 0040 fence follows passed records | Superseded | ML `fence_follow_executor`, ack-loop call site | Passed-record search survives, but normal eager follow is intentionally replaced by final stuck-only 0062 behavior. |
| 0041 4 ms sampler/120 ms hold | Carried | UP `sampler_thread`, `start_sampler`, `merge_latch`, `min_hold`; OH poll/report counters | Sampler/holds are per pad, one Sleep(4) per sweep, default hold 120 ms. INIT_ONCE fixes early publication of an uninitialized lock. USB fixture is present; real-pad timing still needs measurement. |
| 0042 packets across PUT/stall through ISR | Carried | PS `s_pend`, `pb_segment`, stall state; KB busy/in-service gates; ML resume loop | Partial packets resume only at their exact pending VA. Stall persists across guest interrupt service and is released in order. |
| 0043 main-stream/lap fence checks | Superseded | ML `fence_follow_executor`, `fence_catch_up`, subroutine-aware ack loop | Main-ring, lap and returned-CALL position checks survive as part of final prefetch and stuck-only follow, rather than the earlier unconditional caller. |
| 0044 game port 1 | Mixed | OH `s_game_port_to_root`, `pad_root_port`, reset/power/port state; UH child reset | Default HC0 root 3/hub child 1 and game-port order 3/4/1/2 retained. Four ports advertised/powered; upstream write-one-clear/reset ordering retained. Raw HC/NDP and additional-pad settings remain optional. |
| 0045 file anchors | Carried | KP `xbox_FileOpenSeconds`, watch registration/open notification; UP seconds parser; KH | Substring#N and @anchor transitions retain earlier-stage closure. This @ syntax remains separate from upstream @script-file loading through explicit format selection. |
| 0046 event anchors | Carried | KP `xbox_NoteAnchorEvent`; KH; host `src/recomp_manual.c` callers | Named frontend/function events remain available to script clocks and captures. |
| 0047 longer chains | Carried | KP `OPEN_WATCH_MAX`; UP seconds parser buffer/tokens/logged arrays | 32 watches, 4096-byte refusal boundary and 256 tokens/log markers retained. Excess input is refused rather than cut into a misleading anchor. |
| 0048 plain DSP memory | Superseded | ML `APU_TRAP_BYTES` in `xbox_MemoryLayoutInit`; committed MMIO REP helpers | Candidate deliberately traps the full 0x80000 aperture, replacing both historical plain GP/EP memory and upstream's 0x30000 trap. MMIO-safe REP from CPU topic 032c9f2 is the replacement dependency. Do not label the final candidate simply upstream-covered/plain-memory. Full game doorbell/REP behavior remains an acceptance item. |
| 0049 GPU preempts title | Carried | KB `kernel_gpu_preempt`, `kernel_gpu_behind`; HAL `xbox_IrqlPreemptible`; ML `xbox_Nv2aBacklog` | Kernel-entry waits for software service/backlog with default-on preemption and hysteresis, using guest IRQL/interrupt-thread exclusions. Final deadlock/backoff behavior is 0051. |
| 0050 present vsync option | Superseded | DV `d3d8_present` | RECOMP_PRESENT_VSYNC remains supported; default-on setting is intentionally superseded by default-off 0071. |
| 0051 preempt without holding dependency | Carried | KB `kernel_nv2a_swm_waiting`, `kernel_gpu_preempt`; ML backlog calculation | In-service interrupt thread is excluded; timed backoff/put-ahead handling survive instead of waiting forever on state the held title must change. |
| 0052 live walker backlog | Carried | PS `g_pb_live_va`; ML `xbox_Nv2aBacklog`; KB preempt counters | Backlog uses live walker progress and ring arithmetic; software-method/backlog wait diagnostics retained. |
| 0054 prefetch model | Carried | PS `g_pb_words`, pump call; ML `prefetch_words`, release queue, `xbox_Nv2aReleasePump`, ack/catch/follow | RECOMP_PB_PREFETCH, delayed release, at-PUT flush and follow margin survive. Hardware-fidelity of this title-derived model is not inferred from source presence. |
| 0055 bad-transfer dump | Carried | PS `nv2a_pb_last_ring_xfer`, history; ML bad-run dump in ack loop | Ring transfer selection and bounded surrounding stream dump retained for diagnosing overwritten/misaligned streams. |
| 0056 surface/clear diagnostics | Carried | PE surface tracking, `surf_note_target/texture`, skip controls/batch reports; PG CLEAR_SURFACE diagnostics | Current target/texture relationships, clear values and skip experiments survive after conversion to canonical stage state. |
| 0057 near-plane clipping | Carried | PG `clip_triangle_w`, `clip_batch_w`, ready vertices/header | CPU-ready batches retain screen-to-clip reconstruction and near-W clipping; GPU path clips through host pipeline. RECOMP_NO_W_CLIP preserved. |
| 0058 cached environment | Carried | PE `pb_exec_verbose` and cached core toggles; PS `pb_enabled` | Hot core survey/executor gates cache configuration. This does not claim every diagnostic helper has no getenv calls. |
| 0059 64-bit call count | Carried | KB `g_kernel_call_count`, budget/summary formats, PTIMER diagnostics | Counter and formats are 64-bit; diagnostic clock/rate observations folded into final PTIMER. |
| 0060 60 Hz flip pacing | Carried | PE `flip_pace`, FLIP_STALL case | QPC pacing and RECOMP_FLIP_HZ retain guest frame pacing independently of host vsync. Full fight-clock comparison still pending. |
| 0061 texture/combiner diagnostics | Carried | PE texture-format/dump/sweep helpers, combiner raw-word arrays, batch output | Raw programmed words, texture formats and inspect/dump controls survive alongside canonical Nv2aCombiner state. Diagnostic arrays no longer own renderer state. |
| 0062 follow only when stuck | Carried | ML `fence_note`, `fence_follow_executor`, ack-loop stuck timer | Follow occurs after the idle/stalled threshold with release-pump safeguards and ownership logs; RECOMP_NO_FENCE_FOLLOW remains available. |
| 0063 repeating script presses | Carried | UP seconds `apply_script` | name:from:to:period:hold spans and phase math retained; harness format selection is required as noted above. |
| 0064 OHCI millisecond clock | Carried | OH `ohci_clock`, `ohci_frame_now`, register reads/HCCA update, `ohci_run_periodic` | QPC elapsed milliseconds and fractional frame phase shared; elapsed periodic slots capped to one 32-slot lap. Upstream four-frame/read-derived clock is replaced, not combined. |
| 0065 DPC queue synchronization | Mixed | KB `dpc_lock`, insertion/removal/drain; OH masked-MIE diagnostic | Upstream INIT_ONCE critical-section queue with Inserted/cancellation replaces local SRW implementation; queue lock is released before guest calls. Local two-second masked-MIE/report diagnostics remain. |
| 0067 fine vblank/guest time | Carried | KB `kernel_vblank_tick`; HAL QPC guest epoch/uptime | Deadline accumulation, lag skip, RECOMP_VBLANK_HZ and measured rates retained, with fine guest uptime. |
| 0068 audible APU output | Mixed | AC monitor accumulator; AV `voice_resample`, reset/sample state; AD `mcpx_apu_mixdown_six`; Def Jam main default | 256-sample periods accumulate into output buffers, source-rate interpolation/reset and six-speaker headroom survive. Upstream all-bin policy remains generic default; Def Jam selects six explicitly. Audible parity and drop/starve behavior are game gates. |
| 0069 host thread priority | Carried | KB `bridge_KeSetBasePriorityThread`, `bridge_KeQueryBasePriorityThread`, stand-in resolution | Setter resolves guest object to host handle and normalizes priorities. Query initially retained the upstream raw-pointer mistake; main repaired it during this audit to resolve the same stand-in and avoid returning an error as a priority. |
| 0070 APU interrupts | Mixed | AC pending line/update/set_irq processing; KB timer vector-5 loop | Upstream APU line bookkeeping retained, guest ISR delivery belongs solely to pinned kernel timer thread. APU frame thread maintains line/polls doorbell but does not execute a second guest ISR route. |
| 0071 present without vsync | Carried | DV `d3d8_present` | Host Present defaults to interval 0; explicit RECOMP_PRESENT_VSYNC=1 selects interval 1. Guest flip clock remains separate. |
| 0072 render scale | Carried | DV logical/scaled dimensions, getters, swap-chain creation; DH | 1..4 scale, default 2, and logical coordinate queries retained. Capture dimensions/goldens require the established configuration. |
| 0073 decode-once/reuse | Partial | VC `ensure_decoded`, `decode_all`, `nv2a_vsh_inputs_used`; PE vc_* cache/fetch filtering; VI `nv2a_vsh_run` | Per-upload analysis, used-input filtering and per-batch transformed-vertex reuse survive. Original cached-opcode CPU execution is replaced by upstream interpreter decoding fields/reading operands per vertex. CPU fallback performance is not established; retain this explicit partial/superseded note instead of claiming full performance preservation. |
| 0074 PTIMER reset origin | Carried | KB `kernel_ptimer_tick`, `origin_count` | Count is reset origin plus elapsed QPC-derived ticks, not prior issued count plus elapsed. Reset detection and fired-rate evidence retained. |
| 0076 APU output diagnostics | Carried | AC output reports; AX dropped/starved counters; AV voice PCM hooks | Routing/peak/queue diagnostics and local F8..FA PCM captures survive. Capture content must remain local as before. |
| 0077 PTIMER stall diagnostics | Carried | KB `kernel_ptimer_tick` trace branches | Far-future deadline and fired-not-rearmed warnings remain rate-limited and use final timer model. |
| 0078 texture address modes | Carried | PE stage address state and bind calls; PG `pgraph_d3d11_set_texture_address` | Guest U/V modes are applied to the selected stage, with existing mode mapping/fallbacks. |
| 0079 GPU vertex programs | Carried | VC HLSL/hash analysis; VI shared upload/constant revisions; PE GPU packing/draw; PG program API/cache; XVS; DV external draw; D3D/kernel CMake | GPU backend survives, borrowing canonical storage instead of owning a duplicate program/constant file. Constant updates/start changes invalidate relevant caches; WARP fixture supplies bounded evidence. CPU fallback/backend limits remain documented below. |
| 0080 GPU programs by default | Carried | PE gpu_on initialization in `draw_primitive` | GPU enabled unless RECOMP_VSH_GPU starts with 0, subject to program/primitive/trace suitability gates. |
| 0081 stencil | Carried | PG stencil method state/defaults and `ready_state` | Guest reference/masks/function/operations are mapped; packed clear honors stencil; RECOMP_NO_STENCIL remains diagnostic. |
| 0082 combiners/four stages | Mixed | PE canonical `s_gpu.rc`, `texs[4]`, `tex_stage_method`, `bind_extra_stages`; PG `pgraph_d3d11_set_combiner_state`; DC hardware parse/HLSL/CB | Upstream canonical state owns methods/stages; local D3D register-combiner backend consumes it. Raw diagnostic arrays remain separate. GPU output supports four stage coordinates; baseline CPU-ready limitation retained. |
| 0084 dump after capture | Carried | PE `nv2a_pb_request_dump_next`, `batch_dump_flip` | Capture-triggered next-flip dump request survives alongside explicit dump frame lists. |
| 0085 luminance formats | Carried | DR `d3d8_texel_swizzle`; DC and DS shader generation/CB fill; DH | A8/L/LA sample swizzles are carried through fixed and combiner shader paths. Shader numeric review belongs to the separate audit. |
| 0086 surface clip/scissor | Carried | DV `d3d8_SetScissorRect`; DST rasterizer; PE surface clip call; PG forwarding; DH | Surface clip becomes a scaled host scissor, with full-target default and scissor test enabled. |
| 0087 single-index elements | Carried | PE ARRAY_ELEMENT32 case and index storage | Odd trailing index is accepted at 0x1808. Final storage is 32-bit through fetch; dense GPU indices are safely 16-bit under the 32768 cap. |
| 0088 batch pixel probe | Carried | PE batch-dump probe block in `draw_primitive` | Barycentric/depth/coverage pixel probes and associated depth/blend/stencil/cull diagnostics survive. They are diagnostics, not evidence of correct final host pixels. |
| 0089 packed normals | Mixed | PE `fetch_attr` type 6, selected texture-dump mask helpers | Packed 11:11:10 normal decode is upstream-covered and retained; local selected-key/mask diagnostics remain. |
| 0091 debug-layer break report | Carried | DV `d3d11_debug_break_handler`, InfoQueue initialization | Debug builds collect corruption-break messages rather than silently terminating on the debug exception. Release build success does not exercise this handler. |
| 0092 constant-colour blending | Carried | PG blend equation/factor/color mapping and ready state; DST `d3d8_SetBlendColor`, factors; DH enum/API | Constant colour/alpha/complements and blend equation reach D3D host state; final batch diagnostics include colour. Signed MIN/MAX fallback remains an existing approximation. |
| 0093 scripted host-pad suppression | Carried | UP `sample_now`, host gate, diagnostics; Def Jam script format default | Script-present default disables real host input unless RECOMP_PAD_HOST permits it. Gate applies before host diagnostic probe and sample reads. |
| 0094 no duplicate inline draw | Carried | PG `submit_draw` legacy gate | Decoder's real-format draw owns normal inline batches; guessed duplicate translator draw only enabled by RECOMP_TRANS_INLINE_DRAW. |
| 0096 unswizzle once | Carried | PG `ready_tex_fill`; DR texture resource upload | Raw swizzled bytes are copied into resource memory and the D3D8 upload layer performs the single unswizzle. Palette expansion already produces linear data. |
| 0097 draw arrays/point sprites | Mixed | PE DRAW_ARRAYS, 32-bit indices, point-mode packing; XVS `point_gs`, point mode; DV external GS/topology; PG point API | Upstream DRAW_ARRAYS coverage retained with local widened indexes; local geometry-shader sprites and default point size survive. Existing <3-batch outer gate is a baseline limitation, not a newly proved arbitrary point-count implementation. |
| 0098 indexed method tallies | Carried | PE `note_unhandled`; PS `note` | Indexed survey lookup retained; unhandled lookup validates cached slot after report sorting. Scanner itself matches baseline. |
| 0099 program-draw ring buffers | Carried | DV `d3d8_DrawIndexedExternalVS` | Dynamic vertex/index rings retain NO_OVERWRITE until wrap, DISCARD on wrap, correct byte offset and first-index submission. |
| 0100 eviction unbinds every stage | Carried | PG ready-texture eviction loop | Evicted texture is removed from every stage holding its bare pointer before release. |
| 0101 truncated-batch warning | Carried | PE ARRAY_ELEMENT16 overflow branch | Power-of-two warning budget for exceeding NV_MAX_INDICES retained. It covers that historical indexed path; it does not claim every inline/array cap emits a warning. |
| 0102 APU trace length | Carried | AC frame-thread RECOMP_APU_TRACE parsing/status output | Configurable count/default 12 retained with voice/list/notifier diagnostics. |
| 0103 timer rearm signal | Carried | KB `kernel_set_timer`, `ke_object_resolve` | Event and guest SignalState reset under timer lock before arming; lazy shadow recheck/create under shadow-table lock retained. Existing initialization/lifetime questions are not solved merely by this patch. |
| 0104 close directory search | Carried | KF `xbox_dir_context_drop`; KB `bridge_NtClose` | Directory find context closes/removes under its lock before native CloseHandle; upstream async-handle cleanup is retained too. |
| 0105 32768-index batches | Carried | PE `NV_MAX_INDICES`, idx/ready/gv/gtri arrays; DV external VB capacity | Full 32768 index cap and 16 MB external VB retained. Dense vertex indices fit uint16_t, while guest source indices remain uint32_t; triangle expansion buffer has capacity for 3x index count. |
| 0106 texture filtering | Carried | PE stage filter state/bind calls; PG `pgraph_d3d11_set_texture_filter`, stage filter reset in `ready_state` | Guest min/mag choices applied to the selected stage; unset filter retains linear default. Existing single-level upload omits mip selection. |

## Partial CPU rows with runtime dependencies

The other 12 historical rows are already non-pending in the ledger and are not
reclassified here. Three have runtime portions relevant to this audit:

| Patch | Runtime coverage now present | Ledger follow-up |
|---|---|---|
| 0005 | HAL modeled IN/OUT entry points and diagnostics retained; emitted declarations/runtime ABI checked in the CPU topic. | Associate its runtime portion with the eventual HAL commit; CPU topic history remains authoritative. |
| 0008 | No additional runtime flag owner introduced by this union; CPU joins/consumers and switch/tail handling belong to the already consolidated CPU topics, including later 7f7eef9. | Earlier partial notes may lag the completed CPU follow-up; main agent owns updating them. |
| 0053 | Full APU trap is present in ML and the CPU MMIO-safe REP helpers were committed in 032c9f2. | Runtime aperture restoration resolves the dependency named in the partial ledger row, subject to full game validation. Do not restore 0048's narrower trap. |

Rows 0009, 0033, 0066, 0075, 0083, 0090, 0095, 0107 and 0108 retain their existing
CPU/upstream classifications. Together these 12 plus the 96 table rows account
for all 108 historical patches.

## Concrete findings and acceptance notes

The following were reported during bounded review and are now visibly repaired
in the candidate, so they should not remain listed as missing carry-forward:

1. `nv2a_vsh_active` masks execution mode with `& 3` rather than comparing the raw register to 2.
2. Canonical interpreter restores one-time RECOMP_VSH_TRACE budget initialization; explicit batch-dump arming remains.
3. Combined software/D3D comparison skips a software pass for constant-writing programs so canonical constants are not mutated twice.
4. `bridge_KeQueryBasePriorityThread` resolves a guest stand-in through the same handle table as the setter, instead of passing its native memory address to GetThreadPriority.
5. USB helper state is indexed, reset generation is exposed, caller signatures are adapted, and sampler initialization uses INIT_ONCE.

The principal **remaining partial source property** is 0073: the old decoded
CPU instruction execution was replaced. The canonical interpreter is now the
reference and must not be silently swapped back to an independent state owner
to recover performance. Measure CPU fallback cost if it matters after the game
baseline; decode optimization would be a separate, semantics-preserving change.

The CPU-ready D3D transport still loses secondary colour/fog/tex1..3 and unbinds
extra stages when GPU execution is unavailable. This is an established backend
limitation accepted by the main agent for migration, not a new regression to
expand scope around. Standalone software `transform_vertex` also has its own
absent-attribute default behavior; this audit does not assert equivalence to the
D3D current-attribute fallback.

Do not turn source presence into an upstream-covered claim for whole mixed
patches. In particular, upstream DPC queue coverage does not cover guest
dispatch exclusion; physical arithmetic does not cover the recorded inverse
map; indexed pads do not cover Controller S hub topology or anchored scripts;
all-bin audio does not cover Def Jam's selected six-speaker output; and upstream
plain DSP memory does not describe the candidate's full aperture.

The next evidence required is the approved candidate re-lift/build followed by
the saved-baseline regression and extra intro/fight/crib/gym/unlock routes, save
guards, timing/throughput and audio comparison. Vlad's final play-test remains
separate. Runtime topic commits can be assigned to carried/mixed rows after the
final tree and validation evidence are recorded; this report supplies the
source mapping, not fabricated replacement commit IDs.
