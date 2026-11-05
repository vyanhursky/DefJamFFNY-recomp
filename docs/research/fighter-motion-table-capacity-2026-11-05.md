# Shared motion-table capacity — 2026-11-05

Bounded static follow-up to `fighter-behavior-registration-2026-11-04.md`, `fighter-motion-core-table-audit-2026-11-04.md` and `fighter-m2-motion-audit-2026-11-04.md`. Read own generated C and `setup/fighter_motion.py`, `fighter_motion_links.py`, `fighter_motion_records.py`. No implementation, build, game run, or external code. Existing unrelated workspace edits were left alone.

## Result

**Appending shared WAZA/FZUI rows in a newly composed main_all.dat is structurally viable at the inspected native registration/read boundary.** The initializer retains pointers into the loaded file, and readers decode one selected row into existing fixed-size actor buffers. There is no observed allocation of an826-element primary move array or2088-element primary parameter array that must also grow. Those populations are source-data counts, not native fixed capacities. This does not by itself admit a new core: the separate static core descriptor table still stops at141, so new zero-based core IDs>=141 need the previously specified descriptor-reader adapter.

Keep all original row ordinals/content, original group populations and original core0/1 behavior. Append new rows, update enclosing chunk lengths/counts, preserve alignment, reconstruct NAME tables if extended, and add WPAR/WWAZ pairs behind the six shared chunks. Native1A47B0 discovers the following chunk through the updated length, so moving the subsequent chunks is supported by its pointer arithmetic. Never append bytes without correcting lengths; never enlarge the static141 descriptors into adjacent globals.

## Exact six-chunk registration

Let H be a chunk header (tag at+0, payload byte length at+4), P=H+8.1A47B0 input is EAX=first H. Source order is WAZA0,FZUI0,NAME0,WAZA1,FZUI1,NAME1, then WPAR/WWAZ pairs. Every next H is current H+length+8. All fields below are dwords except NAME offset entries. Generated evidence: `recomp_0012.c:23359–23422`.

| Payload | Descriptor globals | Contents |
|---|---|---|
| WAZA0 |3B85D8,DC,E0,E4,E8,EC| payload length; packed stride=P[0]; row count=P[4]; group count=P[8]; group-population pointer=P+C; packed row pointer=P+C+4*groupCount |
| FZUI0 |3B85F0,F4,F8,FC| payload length; packed stride=P[0]; row count=P[4]; row pointer=P+8 |
| NAME0 |3B8600,04,08,0C| payload length; name count=P[0]; u16 relative-offset array=P+4; string-pool pointer=P+4+2*nameCount |
| WAZA1 |3B8610,14,18,1C,20,24| same WAZA layout |
| FZUI1 |3B8628,2C,30,34| same FZUI layout |
| NAME1 |3B8638,3C,40,44| same NAME layout |

The chunk lengths and counts are32-bit fields, not141 or8-bit counts. WPAR/WWAZ descriptor pairs have length/pointer/length/pointer, and the native loop writes141 of these only. WPAR is per-core data, **not a third shared parameter table**. Its64 packed bytes decode to232 actor bytes through1A3AD0. The term shared parameters in this report means FZUI.

`MotionIndex` requires WAZA stride32, FZUI stride39, WPAR64 bytes, WWAZ780 bytes (130 six-byte action rows). It permits added WAZA rows after original grouped rows: sum(group populations)<=rowCount. The initializer only calculates pointers from groupCount; it does not walk populations or require sum==count. Its six descriptors therefore do not need a new group for each new core.

## Consumer and allocation census

A complete direct-literal census of3B85D8..3B8644 in generated `.c` files identifies these consumers, in addition to the initializer:

| Function | Reads / result |
|---|---|
|1B4930 (`0012:64433–64519`)| primary WAZA stride/base85DC/85EC; secondary8614/8624; decodes one32-byte packed row through1A3630 into64 bytes at output+F6C |
|1B4B20 (`:64622–64631`)| primary WAZA stride/base; same per-row decoder, output-state selection preserved |
|1A85A0 (`:32628–32649`)| primary FZUI stride/base85F4/85FC; secondary862C/8634; decodes one39-byte row through1A38B0 into136 bytes at actor+2BC |
|1BC900 (`:82513–82531`)| passes NAME0 or NAME1 descriptor to1A3610 based on ID<10000 or ID-10000 |
|1A3610 (`:20997–21019`)| descriptor-relative NAME reader: rejects negative or index>=nameCount, reads u16 offset, adds string-pool base, returns pointer |

No other direct reads of the shared row counts/group-population pointers/lengths occur in this census. In particular no loop copies count decoded WAZA/FZUI rows into a fixed native global array and no per-row host array is allocated here. The backing file owner/resource free and borrowed-pointer invalidation boundary remain8B730/89310 as established in the behavior-registration report. Decode cursors at3BE104/3BE108 are shared scratch, not arrays dimensioned by move count.

This is a bounded generated-reference result, not proof against every possible computed alias or downstream game-system use of decoded fields. No runtime resource-memory capacity measurement was performed. The composer must bound total bytes and32-bit arithmetic itself.

## Namespace and reachable-index limits

| Namespace / path | Observed width or partition | Consequence for added rows |
|---|---|---|
|Core descriptor index| actor+2C dword; static rows0..140| unrelated to move counts; core>=141 must dispatch to sidecar before table access; no byte truncation at this boundary |
|WWAZ action slot|130 six-byte entries per core| preserve action slots rather than adding arbitrary new action IDs;1A7F30 reads boundaries2..124 and synthetic terminal125 |
|WWAZ word0 -> primary WAZA| low12 bits, high bits flags;FFFF absent| index0..4095 representable, so at most4096 primary rows are addressable by this path; exactFFFF must remain absent, not row4095 |
|Decoded WAZA+3C -> primary WAZA|12 input bits, stored u16; read by1A8F00 as signed16 then1B4B20| same0..4095 target domain, no row-count check; this field has no sentinel rewrite |
|External WAZA ID| signed ID>=10000; normalized ID-10000 indexes WAZA1| no12-bit mask here; existing paths directly address32-bit indices, subject to valid nonnegative arithmetic and actual table count; other serialization/caller widths were not exhaustively audited |
|Primary FZUI|1A7F30 result from WWAZ word2(u16 base)+local delta| not restricted to12 bits or2048 rows; validate each reachable result against FZUI0 count |
|Secondary FZUI|ID>=10000, normalized ID-10000| same explicit external partition as secondary WAZA; bound separately against FZUI1 count |
|NAME offsets|u16 offsets relative to computed string pool| every referenced string start must fit0..65535 relative bytes; extra rows/count do not widen that field |

The0..4095 primary move bound is an encoding reachability limit, not an initializer capacity. Keeping4096 rows is a simple compatible format ceiling for **primary WAZA referenced by these edges**, even though MotionIndex's generic inspection budget permits65535. WWAZ flags andFFF/FFFF values must remain distinct. WAZA+3A rewritesFFF toFFFF but is not established as a general move-table edge; +3E is likewise opaque here. Do not infer extra limits or links from either field.

For normal primary FZUI resolution the encoded ID is participant*1000+local ID, local0..999. WWAZ word1 chooses boundary; previous row's word2 is the unsigned16-bit base. Result is base+(local-lowerBoundary), computed as32-bit. Thus a single base is at most65535 but a final reachable row may exceed65535 by the local delta; **65535 is not a proven whole-table count ceiling**. With valid local domain and nonnegative increasing boundaries, delta<=999 gives an arithmetic envelope up to66534, not a promise every such row is practically reachable. The actor-kind41 branch can substitute a signed16-bit decoded field with its existing2/3-unit correction. `MotionLinks.parameter_row` correctly validates the final result and state-dependent special branch. A compiler should allocate actual reachable segments, avoid overflow, and validate all permitted actor-state cases instead of imposing an invented universal FZUI count cap.

The10000 partition belongs to incoming encoded motion identifiers, not to primary FZUI ordinals returned by1A7F30. A primary FZUI row>=10000 remains primary when reached by that scan;1A85A0 does not repartition the return value. Conversely secondary move/parameter ID10000+n addresses independent partition1 ordinal n, not primary row n+10000. Shared external IDs used on both paths require both target partitions to contain their intended ordinal; their row counts need not be globally equal.

FZUI's packed11-bit fields are decoded timing/state values in the inspected consumer trace, not FZUI table indices. Retail FZUI0 already has2088 rows, disproving a blanket2048-row cap. Preserve their individual sentinel/conversion semantics without equating field width with table population. WPAR16-bit tails likewise do not by themselves establish shared-table bounds.

NAME1BC900 uses the incoming<10000 partition, so primary NAME lookup IDs must remain below10000 at this consumer and secondary names normalize by10000.1A3610 additionally checks descriptor count; name counts/row counts are distinct. The direct NAME consumer does not allocate a fixed count-sized name cache.

## Concrete composition and manual-reader surface

A feasible bounded first implementation can preserve original shared rows byte-for-byte, append primary moves only while new references fit12 bits, append FZUI segments with validated WWAZ u16 bases/local ranges, retain group-population values, and update all six lengths/counts/pointers by composing a new immutable main_all.dat. Native registration automatically repoints shared bases into that loaded composed resource. This avoids per-core copies of the shared moves and preserves retail ordinal behavior. Additional core pairs remain owned by the composed resource or a retained guest sidecar generation.

Required core dispatch remains1A47B0 plus1A7F30,1B2090,1B4930,1B4BA0. The custom branches must resolve sidecar WPAR/WWAZ while using the newly registered shared bases; retail branches stay original. Preserve0/1 special handling in1AACA0/1AAD00 and actor-kind41 behavior; do not renumber retail cores to make room.

For robust admission/bounds checking,1A85A0 is the FZUI boundary (both namespaces),1B4B20 is the extra primary WAZA edge boundary, and1B4930 is the direct action/external WAZA boundary.1A3610 already bounds NAME count; an offline composer still validates string offset/termination. A lower-level decoder hook at1A3630 or1A38B0 sees only source/destination pointers, so it lacks the clean partition/core context needed for routing; use the named readers for contextual checks. Native direct calls bypass lookup-only hooks; use the established manual exclusion/real generated call-target convention and verify generated wrappers after re-lift.

No additional fixed per-shared-row allocation was found that must be enlarged for the proposed append-only composition. This supports a candidate M2 registration design, **not runtime-safe move authoring or milestone acceptance**: animation/event/behavior semantics and live resource lifetime still need their existing independent validation and native acceptance gates.
