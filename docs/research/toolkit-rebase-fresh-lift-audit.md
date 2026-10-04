# Fresh-lift census and bounded continuity audit

2026-10-03. Read-only source and metadata review; no builds, tests, game runs, source edits or Git changes. The only written artifact is this report.

**Confirmed preservation regression:** fresh sub_001D5270 drops the baseline D21 loaded-target checks and all 15 index fallbacks. Its recovered arms preserve the sampled return behavior, but dispatch now relies entirely on mutable guest table contents. Restore the baseline value-first, index-second dispatch for foreign arms before accepting the migration. This finding does not establish the cause of the observed filename mutations or fence stalls.

## Counts and function-set changes

Both complete summary records were directly read. The baseline is the preserved snapshot, rather than the stale documentation figure of 17,862 translated / 108 stubs.

| Field | Preserved baseline | Initial candidate | Delta |
|---|---:|---:|---:|
| total | 17,874 | 17,890 | +16 |
| translated | 17,871 | 17,887 | +16 |
| manual_functions | 3 | 3 | 0 |
| unresolved_stubs | 111 | 111 | 0 |
| failed | 0 | 0 | 0 |
| total_lines | 2,087,159 | 1,835,714 | -251,445 |

Sources: [baseline summary][baseline-summary], [initial candidate summary][candidate-summary]. The parent subsequently re-lifted to update provenance for the new recomp_unimpl host contract and reports unchanged semantics/function addresses; this audit did not independently re-read that replacement summary.

The parent's [generated census][census] was directly inspected. It reports 17,870 → 17,886 sub_ definitions, 16 additions, no removals, two Original extent deltas, one common-function switch delta and no hook deltas. The definition count is one below the translated-summary count on both sides; this unchanged counting discrepancy should not be converted into a removed function claim.

The additions are:

- Fifteen existing switch destinations: 001D5295, 001D52A0, 001D52AB, 001D52B6, 001D52C1, 001D52CC, 001D52D7, 001D52E2, 001D52F8, 001D5303, 001D530E, 001D5314, 001D531F, 001D5337 and 001D5350. These explain +15 callable generated bodies without adding newly discovered guest addresses.
- 00201954, newly recognized as seed_vtable_thunk with 153 bytes / 54 instructions. The address already exists in the unchanged seed input ([seed source, line 15][seed]); recognition is new, rather than a newly introduced seed.

Disassembler analysis counts are 17,875 → 17,876. The fifteen arm entries account for the larger generated-body delta. Upstream [discover_jump_table_entries, line 885][arm-discovery] explicitly creates callable entries for arms outside the dispatcher extent. Its [whole-arm check, line 974][whole-arm] rejects incomplete arms and arms reading dispatcher-produced flags. These rules explain the new arm partitioning; they do not preserve the removed D21 dispatch fallback automatically.

The census lists 409 switches on both sides. That aggregate hides loss of the local 15-way switch in sub_001D5270 and addition of a four-way local switch in new sub_00201954. Equal switch totals are therefore not a coverage or dispatch-equivalence gate.

## sub_001D5270: coverage retained, D21 fallback lost

The generated Original extent changes from [001D5270,001D535B), 235 bytes / 64 instructions, to [001D5270,001D5295), 37 bytes / 8 instructions. Both baseline and candidate disassembler metadata already bound this entry to 37 bytes. This is a changed recomp/recovery policy, rather than a newly shortened disassembler bound at this address. The existing 001D5350 detection remains unchanged at 192 bytes / 94 instructions.

In the [baseline dispatcher, line 33][baseline-dispatch], the loaded guest table value is first compared with all known destinations. If it matches none, [lines 49–64][baseline-fallback] dispatch by the proven slot index. The final unknown case retains the raw indirect tail call. The slot mapping is:

| Index | Target | Index | Target | Index | Target |
|---:|---|---:|---|---:|---|
| 0 | 001D5295 | 5 | 001D52E2 | 10 | 001D52C1 |
| 1 | 001D52B6 | 6 | 001D52D7 | 11 | 001D531F |
| 2 | 001D52F8 | 7 | 001D52AB | 12 | 001D52A0 |
| 3 | 001D5314 | 8 | 001D530E | 13 | 001D5303 |
| 4 | 001D52CC | 9 | 001D5337 | 14 | 001D5350 |

The [candidate dispatcher, line 26][candidate-dispatch] goes directly to RECOMP_ITAIL_AT using the loaded table value. It has neither the known-target checks nor the index fallback. This removes an established preservation behavior for an overwritten guest table and is an explicit D21 regression, regardless of whether all fifteen destinations remain callable.

The sampled generated arms do preserve continuity:

- [001D5295][arm-5295] sets EAX to 0x1B4, adds 0xFFFFFE4C and consumes one existing guest return address, matching the baseline local arm.
- [001D5350][arm-5350] sets EAX to 0x1C0, applies the same adjustment and consumes one guest return address, matching the default arm.
- [001D52E2][arm-52e2] preserves the signed comparison against 10 and both EAX branches.
- [001D530E][arm-530e] preserves the comparison against 5 and the fallthrough to the 001D5314 result.
- The shared loc_001D5355 epilogue is copied locally into both conditional arm functions. The parent's [mapping extract][tail-mapping] confirms both labels exist and no global dispatch/stub entry for 001D5355 is needed.

The candidate dispatcher publishes CMP's CF/ZF/SF/OF validity with _fv = 7 before its unsigned JA. No mismatch was found in this bounded CMP/JA comparison. This is not a general flag-correctness claim.

Smallest preservation repair: keep foreign callable arms, restore baseline loaded-value checks followed by the exact slot mapping, and leave raw indirect tail dispatch only for an unmatched value and unproven index. Foreign tail dispatch must not push another guest return address; the arm epilogue consumes the caller's existing one. There is no need to force the old broad function extent solely to restore D21 behavior.

## sub_00201810 / sub_00201954: different extent, no demonstrated fallback removal

The second generated and disassembler extent delta is [00201810,00201952), 322 bytes / 121 instructions, to [00201810,0020189F), 143 bytes / 58 instructions. New seeded entry 00201954 occupies [00201954,002019ED). The neighboring 002019ED entry is unchanged.

Both the [baseline entry, line 17][baseline-201810] and [candidate entry, line 13][candidate-201810] immediately perform the same POP EDI / restore ESP from EBP / POP EBP / guest return. The removed trailing text follows that unconditional return at this entry. Its removal does not by itself demonstrate a runtime regression for calls to 00201810.

All four retained foreign table jumps were already raw indirect tails in the baseline (lines 45, 52, 80 and 83); their table/index pairs remain in the candidate (lines 42, 50, 71 and 74), now carrying guest call-site addresses. No baseline index fallback was removed from those four sites.

The [new 00201954 body, line 11][candidate-201954] copies six dwords, advances ESI/EDI and reaches a four-way local table switch. Its [dispatch, line 33][new-switch] preserves both loaded-target checks and proven indices 0–3 before raw fallback. The four arms preserve the visible saved-register/frame return sequence, with 0–3 final byte copies as appropriate.

Thus the shared foreign-table policy deserves generic D21 hardening, but this bounded evidence identifies a removed fallback only at 001D5270. It does not establish all alternate-entry paths or all copy-loop semantics as equivalent; the candidate also changes generated copy/DF handling, beyond this continuity check.

## Hooks, stubs and audit limits

The census records unchanged required hooks: sub_0021EB90_enter in sub_0021EB90 and sub_002203C6_enter in sub_002203C6, with an empty hook-delta object. That verifies the parent's census result; their exact insertion ordering relative to guest work was not independently read in this audit.

Both complete summary records report 111 unresolved stubs. The actual stub address sets were not compared. No removed generated functions were reported by the census, but this does not substitute for checking manual dispatch and unresolved-stub identity.

Only the staged complete functions listed above were read for generated semantics. The function/extent census is a parent-produced extraction, independently inspected rather than independently regenerated. The broader flag changes, every recovered arm, and causal relation to route failures remain unverified.

## Existing lift-audit.py is not a dynamic-flags correctness gate

[scripts/lift-audit.py][lift-audit] documents _flags as a REP-compare fallback and tracks a linear per-function/per-label state: assignments to _flags or _zf change the state, labels reset it, and a _flags occurrence outside the flags state is counted unless it has the old fallback-marker comment.

That model does not represent the candidate's dynamic _flags/_fv design. It does not inspect the validity mask, distinguish individual flag bits, model masked updates, or propagate state over control-flow edges. Its assertion that an unmatched _flags read is silently always false is not valid for the new representation. Existing thresholds cannot establish semantic preservation between lifters.

Its fcmp_fallback and cmps_then_sbb metrics likewise recognize old textual shapes, rather than general arithmetic, REP comparison or flag-consumer correctness. It scans recomp_0*.c rather than every generated artifact and treats unknown --max names as zero via counts.get. Keep it as a historical pattern scanner; do not use a low count as a migration acceptance gate. This audit did not run it.

## Runtime evidence reported by the parent

The following is attributed to the parent's measurements:

- Candidate Debug boot reached the main menu and looked correct in run-20261003-161055.log.err; saves restored identically and no crash, ICALL failure or truncation was reported.
- Later routes passed m2/m3, while m4a stalled before title, fight reached battleID without Start progressing, and intro stalled in sub_0021EC50 at a fence wait. The preserved baseline passed 9/9. Behavioral equivalence is not established.
- The new UNIMPL reporter exposed baseline CLI/STI/WBINVD and PUSHFD/POPFD at 00130B46/00130B50. The parent checked the baseline and separated nine known baseline PUSHFD/POPFD sites diagnostically.
- Directory names ending ...0036/0037 were later requested as ...0032/0033, and another name changed ...4ADF → ...4ADD. The baseline reportedly does not mutate these names. These are concrete data-corruption clues; the dispatch regression identified here is not proven to cause them.

The next useful acceptance evidence is restored D21 behavior under overwritten table contents, meaningful flag/copy fixtures around the mutated filename path, and repeat preserved-baseline versus candidate route checks with save restoration. A title boot, zero failed translations, stable counts or equal switch totals do not resolve the current failures.

## Filesystem/tool obstacle and resolution

Direct sandboxed generated-C reads failed with Access is denied. An elevated read-only inventory/hook search waited approximately 3,282 seconds and was aborted without output. No conclusions were derived from that failed call.

The parent subsequently completed metadata extraction and staged complete requested functions under logs/rebase-work/readable-gen with ordinary workspace ACLs. Those reads succeeded normally and support the bounded findings above. Additional exact snippets should use that staging approach rather than repeating the blocked broad scan.

[baseline-summary]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-baseline-20261003-114518/analysis/tools_recomp_output/summary.json
[candidate-summary]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/tools/recomp/output/summary.json
[census]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/generated-census.json
[seed]: C:/Users/Vlad/code/defjam-recomp/config/seed_functions.json:15
[arm-discovery]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/tools/recomp/translator.py:885
[whole-arm]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/migration/tools/recomp/translator.py:974
[baseline-dispatch]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/baseline-sub_001D5270.c:33
[baseline-fallback]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/baseline-sub_001D5270.c:49
[candidate-dispatch]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_001D5270.c:26
[arm-5295]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_001D5295.c:7
[arm-5350]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_001D5350.c:11
[arm-52e2]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_001D52E2.c:10
[arm-530e]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_001D530E.c:10
[tail-mapping]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/001D5355-mapping.txt
[baseline-201810]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/baseline-sub_00201810.c:17
[candidate-201810]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_00201810.c:13
[candidate-201954]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_00201954.c:11
[new-switch]: C:/Users/Vlad/code/defjam-recomp/logs/rebase-work/readable-gen/candidate-sub_00201954.c:33
[lift-audit]: C:/Users/Vlad/code/defjam-recomp/scripts/lift-audit.py

## Parent final candidate census, 2026-10-03

After the switch repair and D52 save replacement, generated definitions number 17,885 plus the entry helper (summary 17,886 translated / 4 manual / 111 stubs). The one removed generated body, 001F8360, is the explicit game-specific compatibility replacement; the 16 additions remain explained above. Both hooks precede the first guest instruction. The complete 111-address unresolved stub set is identical. 001D5270 now emits 15 proven foreign slots with runtime-target precedence and guest-tail dispatch.

Required audits: 409 local tables, zero missing arms; code-byte coverage 2,288,422 to 2,288,431 (+9), 87.95% on both. The new prologue hint is precisely the replaced 146-byte 001F8360 body, not a missing seed. Evidence: `logs/rebase-work/{baseline,candidate}-{jump,coverage}-audit.txt` and `generated-census.json`. Foreign dispatch is separately checked because the historical local-table scanner does not parse its new shape.

`scripts/lift-audit.py` now excludes dynamic `_fv` functions and refuses historical `--max` gates on them. Unknown metric names also fail rather than defaulting to zero. Current candidate contains 9,531 such functions; the compiled recompiler suite remains the flag-behavior evidence. Full game acceptance remains pending.

The fresh actual-submodule analysis/lift reproduces these counts and audits at
published `aa1a1b9`. Final Release `regress-20261003-191107.txt` and Debug
`regress-20261003-202026.txt` are 9/9; the Debug soak is 20/20 with zero hangs/failures.
The initial preservation finding above is resolved by `c6140ae`. Artifact/save
review and the separate owner play-test gate are tracked in `toolkit-rebase-acceptance.md`.
