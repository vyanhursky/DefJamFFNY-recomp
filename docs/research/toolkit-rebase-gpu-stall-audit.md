# Toolkit rebase GPU stall source audit

2026-10-03. Bounded source/log review of candidate
`logs/rebase-work/migration` against preserved original toolkit
`logs/rebase-baseline-20261003-114518/toolkit-live`. No source changes, builds,
game runs or new process samples were performed for this audit. Generated C
was unavailable to ordinary reads and was not inspected. Source line numbers
refer to the candidate as read; symbols are preferable if the main agent edits it.

## Finding

**No concrete missing GPU queue, software-method acknowledgement or semaphore
release was found in this comparison.** The scanner matches the original
byte-for-byte. The NV2A ack thread's resumable walk, GET publication, delayed
release pump, stuck-only fence follow and idle catch-up policies remain the
same. The source changes that can affect guest interrupt synchronization are
the upstream KDPC insertion/cancellation contract and the upstream ISR/DPC
IRQL brackets combined with local dispatch exclusion. Those deserve targeted
trace evidence, but this review does not establish either as the cause of the
failed route.

Do not replace the ordered execution/prefetch model with unconditional fence
completion, remove the servicing gate, or roll back DPC synchronization on
the strength of the present logs.

## What the existing evidence establishes

- `run-20261003-162319.log.err` stopped presenting at five flips and repeatedly
  reported USER DMA_GET `02A13BF8`, DMA_PUT `02A15C00`. The same log had already
  delivered GPU interrupts and run `sub_002239A0`; neither a wholly absent ISR
  nor a wholly absent DPC explains it. This m4a run failed without native-stack
  sampling, according to the main agent.
- `regress-live-samples.txt` places the guest thread in host code belonging to
  `sub_0021EC50`, with the semaphore pointer in RCX and its value in RDX.
  `regress-live-state.txt` shows semaphore `0x15`, requested fence `0x1f`, stable
  across its three samples. This is a real outstanding fence, not evidence that
  its release command was actually submitted or reached.
- The state sampler's PFIFO PUT/GET values are zero while the runtime logs
  report non-zero USER-area pointers. The engine uses USER offsets
  `FD800040/FD800044`. The new PFIFO constants at `FD003240/FD003244` are
  diagnostic definitions, not mirrored engine pointers. These zeros cannot
  establish an empty command queue.
- `PGRAPH INTR unreadable` is expected for an external raw read of the
  PAGE_NOACCESS page owned by `src/hooks/nv2a_regs.c`. It cannot establish either
  a pending or acknowledged software method. Runtime hook reads access its
  shadow, whereas the existing raw sampler does not.
- The intro run `run-20261003-163410.log.err` initially held at zero/two flips,
  but subsequently reached at least 139 translator frames. Its recorded state
  samples show semaphore/tick progress: semaphore `0x15` in the earlier live
  sample, then `0x1f` and `0x21`; intro tick counts `0x18` then `0x1f`.
  That rules out a permanent initial GPU acknowledgement failure in that run.
  Native-stack sampling took several minutes, so its elapsed route time and
  frame count are **not a clean performance measurement**.
- The main agent reported release regression 4/9 and soak 3/3. Three successful
  boots do not establish that intermittent boot stalls are inherited variance;
  the planned 20 clean boots and route reruns remain necessary. Fight/crib/gym
  profile loading failures and the unre-lifted D21 correction are separate,
  unresolved evidence, not a GPU diagnosis supplied by this report.

## Source contracts checked

| Path / symbol | Comparison and implication |
|---|---|
| Candidate `src/kernel/nv2a_pb_scan.c`, `nv2a_pb_run`, `pb_segment`, `nv2a_pb_stall` | Byte-identical to preserved original. Packet continuation, transfer decoding, return-stack state and stopping at the end of a software-method packet have no scanner source regression. The external method callback's behavior can still change. |
| Candidate `src/kernel/nv2a_pb_exec.c`, `nv2a_pb_exec_method` around lines 3898–3917 | Retains ordered `subch==0 && method==0x1d70` semaphore release; subchannel 5 pattern reference update; non-zero method `0x0100` queues `kernel_nv2a_software_method` and calls `nv2a_pb_stall`. Translator forwarding precedes these as before. No clean merge removed this path. |
| Candidate `src/nv2a/nv2a_pgraph_d3d11.c`, `pgraph_d3d11_method` | Changes its silently accepted flip method names to canonical `0x120..0x130`, and adds the host frame-end callback wrapper. It does not own the kernel software-method queue or acknowledgement and has no new NOP/semaphore consume path. The executor's flip constants were already canonical in the baseline. |
| Candidate `src/kernel/xbox_memory_layout.c`, `nv2a_ack_thread` around lines 1415–1588; `xbox_Nv2aSemaphoreRelease`, `xbox_Nv2aReleasePump` | Core control loop unchanged. A stalled packet resumes only when `kernel_nv2a_swm_busy()` allows it. Releases flush after sufficient prefetch, at PUT, or after the existing 20 ms stalled exception; fence follow remains stuck-only. Differences inside the thread are disabled-by-default DSP/POKE probes and report cadence. No new unconditional GET/fence completion is present. |
| Candidate `src/kernel/kernel_bridge.c`, `kernel_nv2a_software_method`, `kernel_pgraph_present`, `kernel_nv2a_swm_busy`, `kernel_nv2a_deliver` around lines 2537–2657 | Producer publishes queue contents before its tail. One method is presented at a time. Busy retains queued entries, non-zero PGRAPH status, FIFO-disabled state and `g_gpu_servicing`. Servicing brackets both ISR invocation and DPC draining, preventing resume between early status acknowledgement and later fixup completion. These mechanics match the original. |
| Candidate `src/kernel/xbox_memory_layout.c`, register hooks around lines 209–253; parent `src/hooks/nv2a_regs.c`, `nv_write`, `intr_after_write`, `host_read`, `host_write` | Runtime hook routing unchanged. Guest writes at the status offset clear the written bits and recompute PMC summary; hardware writes deposit bits directly. Hook ownership is registered before PAGE_NOACCESS protection. The ack loop still leaves hooked status pages to their owner. No new double-W1C or PMC-summary erasure found. |

## New DPC and IRQL contracts: source checks and remaining uncertainty

The baseline DPC queue was already protected by an SRW lock. The candidate
uses upstream's INIT_ONCE critical section and additionally rejects a KDPC
whose guest byte `+2` is non-zero, marks it when queued, clears it under the
queue lock **before** invoking its routine, and permits cancellation. It
never holds the queue lock across a guest call. Clearing before invocation
allows a running DPC to requeue itself; cancellation tombstones the pending
entry and clears the flag. No source path found here leaves the flag set after
normal dequeue or cancellation.

Byte `+2` is exactly the upstream `1409a7d` bridge's insertion field, and
`bridge_KeInitializeDpc` zeros the 32-byte guest object and sets the Type at
`+0` and routine/context at `+12/+16`. It is not a newly transcribed merge
offset. The public `XBOX_KDPC` in `kernel.h` is a separate host representation
containing native pointers; it is **not** a guest layout proof. Without the
guest initialization/direct-access sites, this audit cannot independently
certify the Xbox field offset or show whether Def Jam writes that byte itself.
The relevant source risk is changed return/duplicate-call behavior, not an
observed flag-offset error. Existing fixture pass results do not by themselves
certify this title's driver contract.

The candidate brackets guest DPCs with `xbox_IrqlEnterInterrupt(2)` / restore,
and guest ISRs with level `16` / restore. The original did neither. Entry and
exit now publish `fs:[0x24]` and track global raised depth, so guest code that
reads IRQL directly sees different, deliberate values. This is a semantic
change even though the source queue is otherwise sound.

The local exclusion remains correctly layered: `kernel_run_dpc` explicitly
takes the dispatch lock, enters DPC IRQL, invokes the routine, restores the
saved IRQL, and releases the lock only when acquired. The timer thread marks
itself as an interrupt thread before guest calls. Its ordinary raises/lowers
therefore do not implicitly acquire or release that explicit lock. Interrupt
entry/restore itself adjusts tracking/publication without changing dispatch
lock ownership. Guest threads crossing upward acquire exclusion before
publishing raised IRQL, and downward crossings publish the lower level before
releasing it. No new double-release or acquisition-after-publication found.

Two bounded risks remain, without causal evidence:

1. ISR entry uses the hard-coded upstream level 16 rather than a level preserved
   from `KeInitializeInterrupt`; the bridge still stores only routine/context/
   vector from that object. A guest IRQL-dependent branch could differ from
   baseline. Inspect that branch before changing the level.
2. The dispatch runner retains the original timeout that can run a DPC without
   its lock after prolonged contention. It is inherited, not a rebase fix.
   An `[IRQL] ... running a DPC anyway` or `[IRQLBUG]` trace would be concrete
   evidence to follow; ordinary capped DPC log lines cannot measure totals.

## Next discriminator

Use the main agent's already planned serial clean run with
`RECOMP_FENCE_TRACE`, `RECOMP_PGRAPH_SWM_TRACE`, `RECOMP_IRQL_TRACE` and the
existing watchdog/state diagnostics. Do not sample all native driver stacks
during the timing run. In one stalled interval, establish separately:

- Walker position and waiting state versus PUT; pending release, actual fence
  and latest issued reference.
- Whether a method was queued, presented, acknowledged and finished servicing;
  PGRAPH status/FIFO/gpu-servicing must come through existing shadow-aware
  diagnostics rather than the unreadable raw page.
- Whether KDPC `0x0023641c` is actually still queued or spuriously rejected,
  and whether raised IRQL depth/holder stops changing.

If the trace points at a guest IRQL/dedup interaction, the exact generated
functions needed for the next bounded review are `sub_002239A0` (GPU DPC),
`sub_00223760` and `sub_002234F0` (software-method handling), `sub_0021EC50`
(fence wait), and the ISR address reported by `KeConnectInterrupt` for vector
3 in that run. Stage only those bodies and their directly implicated helpers
for ordinary reads. A trace showing no method awaiting service while GET is
stationary instead directs attention to flip/pacing or guest submission, not
to an assumed lost DPC.

The present conclusion is **source contracts largely preserved, runtime cause
still unresolved**. Boot variance is plausible but has not been established
as the explanation for m4a's five-flip failure.
