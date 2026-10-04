# Lifter and ABI carry-forward review

Date: 2026-10-03. Scope: patches 0005, 0008, 0009, 0033, 0053, 0066, 0075,
0083, 0090, 0095, 0107 and 0108, compared with cached upstream commit
`1409a7d7801d3e931fb1074be6104209ddd9a33e`. This is a source review, not a test
result. No source was changed, no build/test/game run was performed, and no Git
state or remote reference was changed for this investigation. The main agent
owns migration and measurement. This report is the only file written.

## Coordinates and conclusion

`U` below means the exact cached upstream commit above; paths following `U`
are relative to `tools/xboxrecomp/`. `O` means the existing dirty toolkit on the
old pin, with the complete local patch stack, as inspected before migration.
Its line numbers are historical coordinates and will move during the rebase.
`P` means a file in `patches/xboxrecomp/`; patch line numbers describe the patch
text, not the resulting source. Game references are relative to this project.

Use upstream's CFG flag propagation, eager result snapshots, atomic operations,
rotate helpers and guarded-call machinery as the base. Carry forward the
remaining behaviors as small topics. Applying these twelve historical patches
as wholes would reintroduce older implementations and lose upstream fixes.

| Patch | Decision | Semantic units to carry forward |
|---|---|---|
| 0005 | Split | I/O-port runtime plus 0008 IN/OUT emission; tail-site diagnostics separately |
| 0008 | Split | Dynamic boundary flags; IN/OUT; proven switch-slot fallback; tail-site diagnostics. Drop old count-one RCL/RCR |
| 0009 | Partial | Full last-pair string flags and zero-count preservation; unknown LOOP ZF fallback |
| 0033 | Drop code | Upstream narrow rotate helpers cover it; retain useful measured cases |
| 0053 | Keep, split | MMIO-aware REP MOVS access; full APU trapping belongs to runtime topic |
| 0066 | Partial, split | Dynamic boundary flags remaining after upstream CFG work; texture diagnostics belong to GPU topic |
| 0075 | Keep | PUSHAL/POPAL plus implicit register, flag-preservation and continuation-proof handling |
| 0083 | Keep, adapt | Caller-cleanup failure semantics, including guarded SAFE_AT calls and new ADD emission |
| 0090 | Mostly covered | Residual XADD snapshot and common-ZF merge snapshot; avoid old general clobber engine |
| 0095 | Keep, extend | Entry hooks, protected before upstream function coalescence |
| 0107 | Drop | Upstream tests already isolate their function database |
| 0108 | Drop code | Upstream FRNDINT covers rounding modes and signed zero |

## Patch-to-code recipes and regression cases

### 0005 + IN/OUT part of 0008: one I/O topic

0005's title mentions rotate-through-carry, but its actual diff contains
`xbox_IoRead8/16/32`, `xbox_IoWrite8/16/32`, reporting, declarations and
`RECOMP_ITAIL_AT`. The IN/OUT lifter dispatch and old RCL implementation are in
0008. See P0005:9-18, 83-122, 132-141 and P0008's instruction dispatch.

Port the six runtime functions into upstream `src/kernel/kernel_hal.c`, retain
matching prototypes in `src/kernel/kernel.h` and
`templates/runtime/recomp_types.h`, and port IN/OUT instruction emission into
the current dispatcher. Preserve port truncation to 16 bits, AL/AX/EAX read
width and write width; byte/word reads must preserve the other register bits.
These are a zero-read/drop-write bring-up model, not full chipset emulation.
Do not silently strengthen its claim when publishing. The fixed-size tracking
array is diagnostic state; review concurrency separately because upstream now
has real guest threads. It must not change returned guest values.

Proposed regression: immediate and DX ports at all three widths, upper-register
preservation, truncation of DX, emitted helper linkage, deterministic zero
reads, and no accidental guest flag changes. There is no matching IN/OUT
upstream implementation to substitute merely because an I/O runtime exists.

### 0008 / 0009 / 0066: shared dynamic boundary-flag topic

Upstream improves known incoming states considerably: U `translator.py`:31-96
merges compatible comparisons and common result destinations; :2227-2304
builds predecessors and settles a fixed point; U `lifter.py`:1866-1942 publishes
result/source snapshots. Keep all of that. It is not full coverage of the
local dynamic fallback. U `lifter.py`:2657-2696 still falls back to `_flags`
when no tracked predecessor state is available; `setcc`/`cmovcc` at :2727-2736
have the same boundary issue. An unknown branch cannot infer its flags merely
from the variable's initialization.

O `lifter.py`:2010-2112 and :2534-2580 carry `_zf`, `_sf`, `_of`, comparison
classification and conditional CF through block boundaries. O :2114-2156 and
`translator.py`:917-972 connect ALU producers/declarations. Carry the behavior,
not those whole helpers: upstream `_fa/_fb` now have different roles, notably
ADD/SUB result/source and INC/DEC overflow markers. Copying old assignments
such as `_fb = _fa` would destroy upstream ordered-condition calculations.

Precise integration recipe:

1. Retain upstream known-state conditions and fixed-point analysis. Add dynamic
   state for the local supported ZF/SF/OF fallback, plus CF where required.
   Either use dedicated boundary operands/classification or publish flags at
   producers; do not reinterpret upstream `_fa/_fb` in place.
2. Update the producer emitters using width-masked pre-write operands and final
   results. Keep INC/DEC's CF unchanged, and keep the special flag-preserving
   instruction/zero-count cases. Publish to the fallback used by unknown
   `jcc`, `setcc`, `cmovcc` and LOOP consumers.
3. Extend declarations/detection at U `translator.py`:2117-2147 so functions
   whose only producer is a string compare have the required locals. Avoid
   introducing undeclared temporaries in a REP-only function.
4. Keep upstream `_function_needs_cf` (:1212-1245) and the optimized no-CF case.
   Add the remaining boundary readers instead of replacing it with the old
   detector. Preserve `_flags` compatibility for existing string/LAHF paths
   until each consumer is deliberately migrated.

O `_lift_rep_compare` publishes the last operand pair and ZF/SF/OF/CF only if
at least one iteration ran. U `_rep_compare`, `lifter.py`:2832-2867, currently
publishes ZF and optional CF only. Capture each pair once, before advancing
ESI/EDI, including signed extension by operand width; publish the local signed
comparison behavior as well. With initial ECX zero, retain all previous flag
state. U `lift_basic_block`:3953-3957 already seeds known incoming ZF before a
possibly empty REP; preserve that and make the unknown incoming case work.
Retain bare CMPS/SCAS support (:1455-1462), DF handling, and MOVSD/SSE ambiguity
handling. Porting the old string dispatcher wholesale loses these additions.

U `_lift_loop`:2700-2725 already decrements ECX and uses tracked ZF. Keep it;
only replace the unknown incoming fallback with actual saved ZF, and ensure
LOOPNE uses its negation. O LOOP aliases include LOOPZ/LOOPNZ; preserve supported
aliases. LOOP instructions preserve guest flags.

Upstream tests to retain are `test_flag_join.py`:19-39,
`test_flag_join_backedge.py`:52-84, `test_lifter_zero_test_merge.py`:39-88,
`test_lifter_rep_compare_flags.py`:167-197 and `test_lifter_loop.py`:45-72.
Mixed operations, widths and unknown predecessors must still refuse an
unjustified static merge. Tests that explicitly require the old `_flags`
fallback text should be adapted to the corrected dynamic expression, without
weakening that merge refusal. The REP tests include useful compiled unsigned
and CF consumers; retain their negative controls and no-CF optimization.

Add compiled cases for mixed CMP/TEST/ALU predecessor joins followed by JE/JNE,
JS/JNS, signed relations, SETcc and CMOVcc, with intervening flag-preserving
MOV/LEA/POP. Include the existing 0066 AND/padding/INC/DEC route and SUB-to-JB
boundary fixture. Sweep signed CMPS/SCAS operands at byte/word/dword widths,
initial ECX zero with both previous flag outcomes, forward/backward DF and bare
compares. Add LOOPE/LOOPNE zero/nonzero saved-ZF cases at an unknown join.
Do not port the 0066 assertion that an ADD followed by CMP emits no snapshot:
upstream deliberately publishes eagerly.

0066 also changes `nv2a_pb_exec.c` texture diagnostics (patch beginning).
Move those hunks to the GPU topic; they are unrelated to this CPU change.

### 0008: corrupt jump-table fallback and tail diagnostics

U `_lift_jmp`, `lifter.py`:2585-2655, preserves a valid runtime target by testing
it against known arms, then uses ITAIL. The local fallback enumerates the
source index when the runtime table value is corrupt and the table is small.
That behavior remains useful, but copying the old `enumerate(targets)` fallback
is unsafe on upstream. U `_analyze_switch_table`:2504-2564 can return targets
from a shifted table base or backward scan, without original slot ordinals.
An index of 1 or -3 must not be mapped to arm zero.

Keep the runtime-value comparisons first. Derive explicit `(guest index,
target)` pairs from the actual XBE slots and validated addressing expression;
carry the original displacement/base/scale relationship. Retain the old small
table bound (64 arms). Initially permit only proven 32-bit, scale-four indexed
tables; refuse ambiguous census ordering or base-as-index guesses. If there
is no proof, preserve ITAIL diagnostics. Keep upstream manual external-call
and forced-tail routing. Do not replace `_lift_jmp` wholesale.

Keep U `test_switch_table_offset_index.py`:63-72 and add compiled corrupt-slot
cases for ordinary, positive-shifted and negative-index tables. A valid runtime
target must win over the index fallback; out-of-range or ambiguous indices must
take the diagnostic path. Test table targets recovered/coalesced upstream.

Tail-site support comes from O `recomp_types.h`:946-963 and
`src/recomp_manual.c`:511-530. The current game defines
`uint32_t g_itail_site` at :511, while the header only declares it. Do not add a
second runtime definition without changing the game's definition in the same
step. Initial migration may retain the game owner. For a generic public fork,
prefer one runtime-owned `RECOMP_TLS uint32_t g_itail_site` beside the register
globals (U `xbox_memory_layout.c`:1113), a matching TLS extern in the template,
and removal of the game's definition. This atomic ownership change avoids
LNK2005 and makes diagnostics work across guest threads. A header-static
variable would create separate state per translation unit and is wrong.

Port `RECOMP_ITAIL_AT(addr, site)` around the existing upstream ITAIL path
(:1055-1064), and use it on failed indirect tails. Keep the established failure
callback/log format. Preserving/restoring a previous site for nested calls is
a sensible separate improvement; do not silently change baseline behavior
during the mechanical carry-forward. Test successful/failed tails, exact site,
clearing/restoration policy, two translation units and single symbol ownership.

### 0033 and rotate part of 0008: use upstream helpers

U `lifter.py`:2135-2189 uses `RC_ROT` for general RCL/RCR counts and dedicated
ROL/ROR helpers for 8/16/32-bit operands. This supersedes the local count-one
carry implementation and local narrow rotate emission. Preserve upstream's
helper/declaration changes and U `test_lifter_rotate_width.py`:37-84 and
`test_lifter_rotate_carry.py`:35-115. The latter has emission tests plus a
Python mathematical reference; it is not a compiled test of the actual helper.

Retain/add the measured CL-byte case (0xC0 rotates to 0x81), register upper-bit
preservation, counts 0/1/width/width+1/31 and both carry inputs. Compile and
execute the actual current helpers for the broader sweep. The old local test
prelude defines only ROL32/ROR32 and must be adapted, not copied over upstream's
same-named width test file.

### 0053: REP MOVS and APU trapping are not covered

O `_lift_rep_string` excludes source/destination starts at or above
`0xFD000000` from the plain memcpy fast path and uses volatile MEM8/16/32 loops.
U `lifter.py`:2740-2830 already has useful overlap/DF handling but no MMIO guard;
its byte slow path still uses plain pointer indexing. Port the hardware-window
guard while retaining upstream forward non-overlap and backward/overlap
semantics. Use volatile guest accesses for hardware slow paths at every width,
including byte. Preserve ordinary-memory optimizations. Consider range-crossing
copies explicitly; the original start-only condition is not proof that the
entire copy avoids MMIO or guest-address wraparound.

Keep U `test_lifter_direction_flag.py`:22-74. Add byte/word/dword copies with
hardware source, hardware destination and both, using an access-counting MEM
fixture; cover overlap and DF=1. The local 0053 tests omit word coverage.

The same patch restores full APU trapping after the earlier plain-DSP-memory
approach could hang movies. U `src/kernel/xbox_memory_layout.c`:2425-2433 sets
`APU_TRAP_BYTES = 0x00030000`, leaving GP/EP as RAM. O's final setting is
`0x00080000`. Therefore upstream APU work does not automatically cover 0053;
it reopens the retired behavior. Carry this runtime policy separately from the
lifter, and require the parent's movie/skip baseline plus APU runtime checks
before deciding to change it.

### 0075: PUSHAL/POPAL needs upstream integration in three places

Port the 32-bit stack emission into U `lifter.py`'s stack dispatcher
(:1393-1397). PUSHAL/PUSHAD pushes EAX, ECX, EDX, EBX, original ESP, EBP, ESI,
EDI; POPAL/POPAD pops in reverse and skips the saved ESP slot. Preserve the
original ESP before the first push. Add implicit EBX/ESI/EDI/EBP uses at U
`translator.py`:1937-1949 so C locals are initialized and ABI save/restore
follows the existing convention.

Add POPAL/POPAD to flag-preservation tracking. U `_EFLAGS_PRESERVE`,
`lifter.py`:421-438, already includes PUSHAL but not POPAL/POPAD/PUSHAD.
Also update indirect-continuation proof: U `translator.py`:1350-1362 treats
POPAD as a register clobber but omits Capstone's POPAL spelling. Both aliases
must invalidate restored-register constants; PUSHAL must model ESP's change
while preserving the other registers. Otherwise a newly implemented POPAL can
make an upstream indirect jump follow a stale proven constant.

Regression: compile the local `60 31f6 61 c3` fixture, check all eight stack
slots and original ESP, modify the saved ESP slot to show it is ignored, check
all restored registers and total ESP delta, and place CMP/JE across each
operation to verify flag preservation. Add a POPAL followed by indirect JMP
whose register had a different pre-POP constant; continuation proof must reject
that stale value. Do not expand this topic to unsupported 16-bit PUSHA here.

### 0083: caller cleanup, guarded-site variant, and ADD snapshots

O `translator.py`:83-100 marks safe indirect calls followed by caller cleanup;
O `recomp_types.h`:911-928 pops only the return address on lookup failure.
Without this, rewinding to pre-arguments ESP followed by `add esp,N` leaks N
bytes. U SAFE (:1003-1019) and SAFE_AT (:1029-1046) still use that rewind.

Keep upstream `_fixup_icall_esp_save`, `translator.py`:120-223 and :2353; it
has stronger barriers and support for SAFE_AT. Add CC variants for both plain
and site-aware safe macros. The site-aware variant must retain
`RECOMP_ICALL_OBSERVE_SITE`, ABI wrapping, guard-hit/miss accounting, failure
logs and both missing-target branches. U `lifter.py`:2411-2426 now emits guarded
calls with SAFE_AT fallbacks, so a plain SAFE-only rewrite misses normal calls.

There is a second textual matcher hazard: U `_lift_alu_binop`:1910-1922 emits
`_fb = ... /* add source */` before `esp = esp + N`. The old marker stops at
that new snapshot statement. Prefer identifying a bounded, immediate caller
ADD from decoded instructions and attaching the decision to call emission.
If retaining postprocessing, recognize only the precise generated snapshot
lines and validate the real current emission; do not skip arbitrary guest
instructions merely to find a later ADD. The old ret-N exclusion remains
necessary. Handle branch/label boundaries conservatively.

Extend U `test_icall_guarded.py`:43-83 and
`test_icall_guarded_runtime.py`:59-75 with actual translated ADD-ESP output and
both guarded and ordinary calls. Example: ESP=0x1000, 8 argument bytes, then
return address gives 0xFF4; CC failure pops to 0xFF8 and caller cleanup returns
to 0x1000. Check non-code and unresolved-code failures, guard hit, guard miss,
recorded site, multiple arguments, no-cleanup/stdcall behavior, ret-N and
instruction barriers. A handcrafted `esp = esp + 8` string test alone misses
the new regression.

### 0090: upstream result snapshots cover most, but two residuals remain

U `_RESULT_SNAPSHOT_SETTERS`, `lifter.py`:355-359, eager producer snapshots
(:1866-1942), `test_lifter_result_clobber.py`:140-182 and
`test_incdec_result.py`:11-57 replace most of the local `_SavedFlagResult`,
alias/clobber scanner and `_fres` declaration. Preserve the compiled negative
controls. Do not resurrect the entire old basic-block tracker over upstream's
CFG state machinery.

First residual: U XADD conditions (:984-990) still read the live destination;
XADD is absent from the result snapshot set. U atomic emission (:1725-1737)
returns the original value into the source but does not snapshot the sum.
Preserve upstream's atomic operation. Capture the original addend before it is
overwritten and publish the result from `_old + original_addend` inside that
block, using the current snapshot convention; do not reread mutable memory
later. Add XADD/LOCK XADD to declaration/tracking only as their supported
consumer semantics require. Register/narrow XADD is currently outside that
upstream memory-32 implementation; do not claim it is fixed by this change.
Regression: memory XADD followed by a MOV/POP or memory overwrite before JE/JNE,
zero/nonzero sums and source alias concerns, while retaining
`test_lifter_atomics.py`'s atomicity checks. Keep unsupported forms explicit.

Second residual: common-ZF merge uses `__zf_from_dest`; U `_make_condition`
(:525-531) rereads the live destination despite each producer publishing its
result into `_fa`. Read the compatible width-masked snapshot instead, retaining
the existing destination/width merge criteria. Add a compiled two-arm join
(e.g. SUB on one arm, DEC on the other), with MOV overwriting the common
destination on both arms before JE/JNE. Existing agreeing-destination tests
without an intervening clobber do not establish this case.

### 0095: protect hooks before coalescence, then emit once at true entry

O `manual_scan.py`:62-70 recognizes `sub_XXXXXXXX_enter` definitions after
stripping disabled `#if 0`; :73-99 keeps them separate from replacements,
wrappers and references. O `translator.py`:1036-1038 emits a hook before the
first guest instruction. Game hooks at `src/recomp_manual.c`:661 and :718 are
the fence/gamma hooks; ordinary lookup replacement alone does not intercept
direct calls to generated code.

Upstream introduces a new ordering requirement. U `__main__.py`:89-97 loads
manual protected starts before constructing BatchTranslator (:264-268).
Entry-hook starts must be in this protection set, or function coalescence can
remove the generated function before emission. Do not add hooked functions to
manual replacement sets or the skip/wrap/reference partitions at :440-475.

Port `entry_hooks` scanning (missing file -> empty set, definitions rather than
declarations, nested disabled blocks stripped). Load the hook set before
BatchTranslator; union its guest addresses into protected starts. Pass/store
that set for emission and reset it for each CLI invocation, including the
no-manual-file case. At U `translator.py`:1908 use `func_addr`, not a possibly
renamed function name (:1916), to match hooks. Emit the declaration/call before
the first block label, after the entry setup near :2208-2211; a guest jump to a
block label must not repeat a true-entry hook. Keep generated naming/recovered
labels intact.

Extend U `test_manual_scan.py`:67-107 and
`test_function_coalescence.py`:1045-1071 with hook-only definitions, disabled
definitions, declarations, missing files, consecutive CLI invocations and a
hooked start that otherwise coalesces. Verify it remains generated, receives
exactly one entry call, and is not skipped/renamed as a manual wrapper. Add
direct-call, lookup-call and renamed-function fixtures. Parent game validation
must check the existing fence/gamma route effects.

### 0107 and 0108: covered, retain upstream versions

U `test_icall_feedback.py`:96-119 already passes an isolated nonexistent
`--functions` file for the alignment fixtures, covering 0107. Preserve :123
and :157 seed behavior tests; no source carry-forward is needed.

U `recomp_types.h`:307-322 and `lifter.py`:3660-3668 honor guest FRNDINT rounding
modes. Upstream additionally preserves signed zero. Keep U
`test_lifter_frndint.py`:28-97 (all rounding modes, host-mode independence,
signed zero and non-finites) and its shared helper behavior with FIST
(:325-330). No 0108 code carry-forward is needed; parent still checks the
project's unlock route after the upstream lift/build.

## Suggested serial integration order

1. Freeze the existing patched toolkit and untracked source/test files as the
   parent baseline; compare against the fixed upstream revision above.
2. Keep upstream covered pieces first. Port I/O and tail-site diagnostics with
   explicit symbol ownership, then PUSHAL/POPAL and entry hooks with early
   protection. These establish a compilable feature surface.
3. Port MMIO MOVS and APU trap policy as separate lifter/runtime topics.
4. Integrate the shared boundary/string flags and 0090 residual snapshots on
   top of upstream's existing state machinery. Adapt text assertions only when
   the runtime behavior under test is preserved or deliberately repaired.
5. Add caller-cleanup variants using the actual new emitter, then a proven
   slot-index jump fallback. Preserve all guarded-call and switch-index tests.
6. Run focused compiled tests and the normal toolkit suite, then the parent's
   full lift/build and saved game route regressions. This report supplies
   proposed cases; none have been run here. Test passes or game parity must be
   recorded by the agent performing that measurement.

These units consolidate the historical lifter patches without discarding the
project's measured behavior. They are proposed implementation decisions; the
main agent should verify each against its preserved baseline before accepting
the resulting fork commits.
