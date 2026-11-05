# Fighter behavior registration audit — 2026-11-04

Bounded static reading of this checkout's generated C and existing motion reports. No source changes, build, game run, external code, or game bytes exported. Addresses are guest VAs. Generated line references are local evidence, not distributable code. This supplements `fighter-motion-core-table-audit-2026-11-04.md`; its detailed motion branching remains applicable.

## Registration and ownership

`1A47B0` is the fixed descriptor writer (`recomp_0012.c:23352–23448`). Input is **EAX**, not a stack argument. It first walks six length-prefixed shared chunks, publishing metadata into `3B85D8..3B8644`. Each chunk advances by its payload-length word at +4 plus eight header bytes. The following loop has destination `3B8648`, increments by16, and compares against exclusive `3B8F18` (signed less). Thus141 rows, independently of any source count. Each row describes two consecutive source chunks:

| Offset | Meaning |
|---|---|
| +0 | first chunk payload byte length |
| +4 | first chunk payload guest pointer (chunk+8) |
| +8 | second chunk payload byte length |
| +C | second chunk payload guest pointer (chunk+8), WWAZ six-byte records |

These are borrowed payload pointers. The fixed descriptors themselves are static guest storage, never separately allocated here. The writer does not validate lengths, available source bytes, or count. Its caller is `1A4D90` at guest return address `1A4DF6` (`recomp_0012.c:24203`), only when its initialization parameter is zero. Immediately before that, `44170` returns `MEM32(349760)` in EAX (`recomp_0002.c:10741–10746`). A nonzero initialization parameter skips rematerialization; it is not permission to free payloads.

The backing source now has an identifiable owner: main object rooted at `349760`. `8B730` receives that object in ECX, loads the resource named by format constant `2A0B04` through `1E46E0` with global resource context `2DBC0C`, and stores the returned guest pointer at object+0 (`recomp_0004.c:30741,30783–30802`). `8BB00` calls it with its saved object (`:31352`). Matching cleanup is `89310`: after participant/resource cleanup, it passes object+0 to `294D0` at `894E6`, then clears object+0 at `894FA` (`:25952–25964`). `8BE60` reaches this cleanup (`:31901`); `895E0` also tail-calls it (`:26181`). This is resource-owner teardown, **not descriptor-table teardown**: no matching clearing of `3B8648..3B8F18` occurs there. Rows and shared metadata can consequently retain stale addresses between owner release and next initialization. An adapter must invalidate borrowed-source generations at owner cleanup, even if it keeps its own custom allocations alive.

`8CB90` also initializes object+0 to zero (`:34548`); that is object construction/reset, not a descriptor writer. `8CAD0` is an intrusive-list destructor and must not be mistaken for the core-resource free simply because it also writes object+0.

## Reader ABI and semantic boundaries

These contracts follow actual register/stack reads, not lifter CC guesses. Entry stack offsets include the return address. All return with plain `ret`; caller owns stack arguments.

| Reader | Entry contract | Descriptor access |
|---|---|---|
| `1B2090` | actor at `[ESP+4]`; void | actor+2C full32-bit core, shifted4; +4 payload passed to `1A3AD0(actor+AE4,payload)` |
| `1B4930` | output `[ESP+4]`, actor/context `[ESP+8]`, motion ID `[ESP+C]`; void | actor+2C full32-bit core; +C WWAZ, six bytes/item |
| `1B4BA0` | context `[ESP+4]`, sample ID `[ESP+8]`; EAX bool | sample0 immediately false; otherwise word at +C payload + sample*6 differs fromFFFF |
| `1A7F30` | ECX encoded participant*1000+local ID; EAX translated ID | participant record core at `3B930C+participant*12E8`, shifted4; +C WWAZ |

`1B2090` separately indexes seven-word auxiliary state at `3B9128 + actor[28]*1C`. Actor+28 is participant slot here, not a second core index; do not grow this four-slot array for new cores. Its sum-zero behavior preserves existing actor stats. `1B4930` uses WWAZ word0 low12 bits as frame ID, high-bit flag as state+F68; word1 becomes state+FB4 with participant slot*1000. Special motion ranges31–34 and38–41 use state+BB8 slots and shared `3B8614/3B8624` frame bank; IDs>=10000 use that shared bank directly. Ordinary frames use shared `3B85DC/3B85EC`. A new +C payload alone therefore does not introduce independent global frame storage; retain compatible retail shared frame references or route custom frame metadata in the custom reader.

`1A7F30` scans boundaries in six-byte records2–124, then synthesizes boundary1000 for record125. It returns previous record word2 plus local delta; actor kind41 has its existing FA6-based correction. This bound is125, not141. See the preceding motion-core report for exact state writes and special-path behavior. None of the four readers bounds core against141 or narrows it to8 bits.

## Reference census and limits

Literal field-address search across all generated `.c` files gives the complete following direct-reference set in this checkout:

- `3B8648`: only initializer destination (`0012:23423`).
- `3B864C`: `1B2090` (`:57805`).
- `3B8650`: no direct literal reference (initializer writes computed +8).
- `3B8654`: `1A7F30` three accesses (`:31492,31518,31551`), `1B4930` three (`:64451,64465,64500`), `1B4BA0` (`:64691`). All are computed core*16 plus this field address.
- `3B8F18`: initializer end comparison (`:23442–23443`); separate adjacent-global read by `1BAA00` (`:77900`). It is not spare descriptor storage.

The computed writes at initializer destination+0,+4,+8,+C are included above; searching just the base misses all four readers. Searching range literals `3B8600..3B8EFF` finds shared metadata accesses as well; these are not extra row readers. The141 descriptor constraint is the **computed byte span8D0/end pointer**, not a `cmp core,8D`.

A whole-generated-tree exact141/0x8D comparison/assignment candidate census also found functions `195C0`, `1FE70` and overlapping `1FFFC..200A6` lifts; `D6EE0`, `DDDB0`, `DE4A0`; `100700`, `1066E0`, `10B930`; `1132E0`; `15A3F0`; `1D1D00`. These are candidate constant uses, not evidence of descriptor accesses: none joins the descriptor address census. This bounded pass does **not** prove absence of arbitrary address construction through unrelated arithmetic or image-embedded pointers. Do not describe a literal census as exhaustive pointer dataflow analysis.

## External animation bank join has independent limits

`87090` receives the main object in ECX. It takes each nonnegative core from the four words `3B90B8..3B90C4`, increments it as a full32-bit value, keeps absent entries atFFFFFFFF, sorts four (slot,bank-number) pairs, and calls `A02E0(main+488,slot,core+1)` (`recomp_0004.c:20743–20849`). This confirms the existing `wres%03d` core+1 join; a three-digit minimum formatting width is not an8-bit core constraint.

`A02E0` has ECX bank-manager base, stack slot at+4 and bank number at+8; it uses `base + slot*2C`, **not core*2C** (`:88503–88535`). The four participant bank records are initialized explicitly by `9FDC0` (`:87109–87132`). Loaded MNL pointer goes at per-slot+8; the first32-bit word in that file is the resource-item count N. It allocates **N*16** through `296B0` into per-slot+C (`:88595–88620`), then loops unsigned index<N to construct four-word item records, obtaining ORD/ORL handles via resource-context lookup (`:88673–88736`). Flag4 enables a second N*16 array at per-slot+10 (`:88750–88776`). These item arrays are bounded by the loaded bank's N, independently of141 descriptors and independently of the four simultaneous participants. They must be validated for multiplication overflow, actual MNL entry count, referenced resource existence and guest-allocation size before custom publication; there is no141 check at this boundary.

External bank cleanup is `9FE50(manager)` (`:87143ff`): it loops four slot records, frees optional arrays according to manager flags, frees the always-owned per-slot+C item array and releases per-slot+8 source via294D0, resets slot state, and releases the per-slot+1C resource context. `89310` calls it with main+488 when main flags include200 (`:25940–25950`). Reusing an actor slot must respect this lifecycle; custom core number does not imply a fifth bank record.

## Viable adapter hookpoints (design only)

1. Register a validated host-owned map keyed by full32-bit core, permitting IDs>255, with separately guest-addressable descriptor payload storage. Keep lengths and per-core frame-bank metadata in the host map; never insert host pointers into guest MEM reads. Use an immutable published generation and retain allocations while any actor references that generation.
2. Intercept `1A47B0` to run native initialization unchanged, record the new retail backing generation, and publish custom descriptors only after complete validation. Do not enlarge the fixed table or temporarily replace a retail row. Intercept `89310` before resource release to invalidate borrowed retail/core source references; either retain custom allocations for process lifetime initially or free them only after all actor readers are quiescent. Object construction `8CB90` is an additional reset boundary, not a substitute for release.
3. Replace all four direct readers above with custom-ID dispatch; native0..140 follows original code unchanged. For custom IDs implement the documented ABI/state effects using sidecar descriptor and per-core metadata. Missing custom mappings must reject selection before actor initialization rather than falling through to a retail fixed-table access. `1B3110` already carries core in a full32-bit actor+2C; preserve participant slot+28 and four native actor records.
4. At `87090/A02E0`, preserve retail loading. Custom branches map core to validated bank source/paths and preserve per-slot record size, N-bounded item arrays and `9FE50` ownership. This can use existing core+1 numbering for filesystem-compatible resources or an explicit map for arbitrary custom paths. Descriptor extension and external bank registration are separate requirements.
5. Implement hook bodies at real generated call targets or add generated entry hooks and re-lift. **Adding only `recomp_lookup_manual` entries is insufficient:** current `RECOMP_ABI_CALL` macro expands to direct `(fn)()` (`recomp_types.h:1162`); tail calls also directly name functions. Check generated names after regeneration and use the project's manual exclusion plus `_gen` wrapping convention. The prose claim in the earlier report that v0.16 direct calls necessarily consult lookup is too broad for the observed checkout. Do not patch generic MEM macros.

This is a concrete registration design, not runtime acceptance. Unknown arbitrary computed references remain a verification limit; the earlier report's unestablished backing-source release is resolved above. No implementation is included.
