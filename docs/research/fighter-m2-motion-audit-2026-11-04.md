# M2 fighter motion semantics audit

**Follow-up corrections:** FZUI now has an independent native-byte oracle gate:
6,274 records matched every decoded byte and round-tripped exactly; see the
[M1/M2 checkpoint](fighter-mod-m1-m2-2026-11-04.md). Statements below describing
FZUI as awaiting that comparison record an earlier audit stage. Primary review
also corrected the1A7F30 scan: it reads boundaries from rows2..124, then uses
synthetic bound1000 at row125. Its input is participant*1000+local ID, not time.
See the [core-table follow-up](fighter-motion-core-table-audit-2026-11-04.md)
for the exact special-state calculation and native field offsets.

2026-11-04. Bounded read-only audit of the native motion decoders and consumers. No game run, build, or engine changes. Generated C was inspected locally; it is not copied into this report.

## Evidence and scope

`setup/fighter_motion.py` establishes only the chunk envelope and partition dimensions: two `WAZA/FZUI/NAME` groups followed by fixed-size `WPAR/WWAZ` core pairs. It explicitly leaves move semantics, animation links, and runtime readiness false. The oracle record `logs/fighter-motion-decoder-oracle/verification.json` reports zero mismatches between traced bit widths/values and independently derived bitstream fields for 2,181 WAZA rows consuming 250 bits each and 320 WPAR rows consuming 512 bits each. The follow-up `logs/fighter-m2-typed-motion-oracle-comparison.json` independently compares `PackedRecord.native_bytes()` with the original native oracle `decoded_hex`: 2,181 move rows and 320 core rows, zero native-output byte mismatches, and lossless packed round trips for both sets. This validates the raw field extraction and storage conversions against these sampled source records; it does not establish game-level field meanings or resource links.

Generated source inspected: `src/recomp/gen/recomp_0012.c`, including `sub_001A3530`, `sub_001A3630`, `sub_001A38B0`, `sub_001A3AD0`, initializer `sub_001A47B0`, `sub_001A7F30`, `sub_001A85A0`, `sub_001A8F00`, `sub_001B2090`, `sub_001B4B20`, `sub_001B4930`, and `sub_001B4BA0`. The prior motion-table inspection is summarized in `fighter-mod-runtime-2026-11-02.md`.

## Decoder output that is concretely established

`sub_001A3530` is an MSB-first bit reader. Its caller supplies the bit count, source pointer, and current bit cursor; it advances the global cursor state. It joins source bits across byte boundaries and masks the requested width. The global at `0x3BE104` is the bit offset within the current byte; `0x3BE108` is the byte offset. The oracle computes consumed bits as `byte_offset * 8 + bit_offset`. The two record decoders call it in a fixed sequence; this gives an exact wire schema by output offset and width, but does not assign game-level names or enum meanings to opaque fields.

For WAZA, `sub_001A3630` clears a 64-byte destination and writes the following typed fields. Each listed value is stored unsigned at the stated width unless noted. The five fields stored as `MEMF` come from 6-bit unsigned values (0..63), converted to float32 and multiplied by the game scale constant. The generated code uses a signed-to-float conversion with a `+2^32` correction branch for general unsigned dwords; these 6-bit values are nonnegative, so they are not signed 6-bit values. The field widths below are in bits and follow the oracle's order:

| Output offset | Stored type | Input bits | Status |
|---|---:|---:|---|
| `+00` | u16 | 8 | Verified storage width |
| `+02` | u8 | 6 | Verified storage width |
| `+03` | i8 | 6 | sign-extended from the six-bit value when bit `0x20` is set; domain meaning unknown |
| `+04..+0D` | 10 × u8 | 7,4,3,3,5,5,5,5,3,4 | Verified storage widths |
| `+10,+14,+18,+1C,+20` | 5 × f32 | 6,6,6,6,6 | Unsigned value scaled to float; semantic units unknown |
| `+24..+2A` | 7 × u8 | 4,5,4,5,4,3,6 | Verified storage widths |
| `+2C,+30` | 2 × u32 | 32,32 | Opaque values |
| `+34,+36,+38` | 3 × u16 | 8,10,7 | Opaque values |
| `+3A` | u16 | 12 | `0xFFF` is rewritten to `0xFFFF` sentinel |
| `+3C,+3E` | 2 × u16 | 12,12 | Opaque values |

The consumed fields total 250 bits. Padding and the remaining bytes of the 64-byte output are zero because the decoder clears 16 dwords before populating these offsets. The decoder explicitly establishes widths/storage and one sentinel only; naming additional fields as enums, booleans, durations, or indexes is not supported by this audit.

For WPAR, `sub_001A3AD0` clears 58 dwords, then performs 94 unsigned bit extractions totaling 512 bits. These can be implemented independently as a typed raw schema without guessing domain meanings. `dword` and `byte` below describe destination storage; values remain unsigned raw integers. Fixed loop counts are 5 entries at `+0x28`, 5 at `+0x3C`, 47 bytes at `+0x6C`, then 3, 3, and 4 dwords at `+0xBC`, `+0xC8`, and `+0xD4` respectively. The equality-to-7 rewrites at fields 1 and 2 are verified sentinel handling.

| Field(s) | Output offset(s) | Count | Input bits each | Output storage | Verified transform |
|---|---|---:|---:|---|---|
| 0 | `+0x00` | 1 | 3 | u32 | raw |
| 1 | `+0x04` | 1 | 3 | u32 | value 7 becomes `0xFFFFFFFF` |
| 2 | `+0x08` | 1 | 3 | u32 | value 7 becomes `0xFFFFFFFF` |
| 3–4 | `+0x0C,+0x10` | 2 | 5 | u32 | raw |
| 5–9 | `+0x14..+0x24`, stride 4 | 5 | 2,2,3,3,3 | u32 | raw |
| 10–14 | `+0x28..+0x38`, stride 4 | 5 | 4 | u32 | fixed array |
| 15–19 | `+0x3C..+0x4C`, stride 4 | 5 | 4 | u32 | fixed array |
| 20–26 | `+0x50..+0x68`, stride 4 | 7 | 4 | u32 | raw |
| 27–73 | `+0x6C..+0x9A` | 47 | 6 | u8 | low byte of raw value |
| 74–81 | `+0x9C..+0xB8`, stride 4 | 8 | 3 | u32 | raw |
| 82–84 | `+0xBC,+0xC0,+0xC4` | 3 | 7 | u32 | fixed array |
| 85–87 | `+0xC8,+0xCC,+0xD0` | 3 | 7 | u32 | fixed array |
| 88–91 | `+0xD4,+0xD8,+0xDC,+0xE0` | 4 | 8 | u32 | fixed array |
| 92–93 | `+0xE4,+0xE6` | 2 | 16 | u16 | raw |

This completely maps the decoder's writes and loops. It establishes the raw bitfield schema, field order, storage widths, two sentinel transforms, and zero-filled gaps; it does not establish C-level semantic names, enums, pointers, or units for these fields. The later native-output byte comparison validates this 232-byte storage layout for the 320 sampled core records, but does not validate semantic names or uses.

## WWAZ, core index, and consumer constraints

`WWAZ` is a sequence of 130 six-byte entries (`780 / 6`). The examined consumers establish that each row has a first u16, second u16, and third u16. `sub_001B4930` indexes the row by `move_index * 6`, loads the first u16, masks it with `0x0FFF`, and tests bit `0x8000` of that same first word to set the flag at the caller record `+0xF68`. `sub_001B4BA0` tests the first word against `0xFFFF`; `sub_001A7F30` also checks that same first word for `0xFFFF`. The `0x8000` bit in the first word is a flag; treating it as a selector for the second WAZA partition contradicts the observed original rows. The low-12-bit index resolves into the first WAZA table (826 entries in the inspected streams). No inference from numeric fit is made for the second/third words.

External move IDs `>= 10000` take a separate path in `sub_001B4930`: the ID is reduced by 10000 and used with the secondary external descriptor base at `0x3B8624`, then passed to the same WAZA decoder. For in-range IDs the consumer applies special ID windows (31–34 and 38–41) and otherwise reads packed WWAZ data. These are dispatch behaviors, not proof of arbitrary ID-to-animation relationships.

## Core-bank indexing and remap boundary

`sub_001A47B0` initializes a 16-byte descriptor per core in `0x3B8648..0x3B8F18`. Each row stores four dwords: WPAR chunk byte length at `+0`, WPAR payload pointer at `+4`, WWAZ chunk byte length at `+8`, and WWAZ payload pointer at `+12`. It advances by 16 until the exclusive end `0x3B8F18`, exactly 141 rows. The next dword at `0x3B8F18` is live adjacent state (read by `sub_001BAA00`), so there is no safe in-place extension inferred from this layout.

Direct descriptor readers found in `src/recomp/gen/recomp_0012.c` are:

| Function | Descriptor access | Core-index source / use |
|---|---|---|
| `sub_001A7F30` | `descriptor + 12` at three WWAZ scan paths (`0x3B8654`) | Input ID selects participant record by its thousands component; the participant record's dword `+0x2C` chooses the core row. |
| `sub_001B2090` | `descriptor + 4` (`0x3B864C`) | Current fighter record dword `+0x2C`; fetches WPAR and copies the per-core parameter/stat values into the live actor record. |
| `sub_001B4930` | `descriptor + 12` at three paths (`0x3B8654`) | Passed participant/actor context dword `+0x2C`; fetches that core's WWAZ for move resolution. |
| `sub_001B4BA0` | `descriptor + 12` (`0x3B8654`) | Passed participant/actor context dword `+0x2C`; checks the selected WWAZ first-word sentinel. |

The four functions above account for every generated-source reference to the descriptor member bases `0x3B864C` and `0x3B8654`; `sub_001A47B0` is the initializer. `0x3B8F18` is not another descriptor. The all-source literal scan is bounded evidence about generated code, not proof that there are no derived pointers or other runtime users.

The active core index is per participant and stored as a dword. Match initialization reads `0x3B90B8[slot]` and passes it as the third argument to `sub_001B3110`; that function writes the argument with `MEM32(record + 0x2C)`. The setup path documented in `fighter-record-fields.md` supplies this per-slot value from setup `+0xA8` minus one. This same record path is used when fighter records are created, including CPU-controlled fighters; no byte conversion is visible in these table-reader paths. The inspected consumers use dword indexing and 16-byte descriptor stride. No 8-bit core-index field was found in this bounded setup-to-consumer path. That does not prove every save, UI, or asset format stores core identity at 32 bits.

This per-record dword makes participant-specific selection possible in principle: two live fighter records can carry different descriptor indices, and the unchanged readers select through each record. It does not make arbitrary virtual indices usable. An index beyond row 140 would address adjacent memory through the existing absolute-base reads. Serving new content without changing these readers would therefore require repointing an existing descriptor row (or using a genuinely unused row) to a new WPAR/WWAZ pair. A row is global: if another participant still references it, both would see the replacement. No specific descriptor index is proven reserved or unused here; all 141 entries are initialized, and duplicate-looking chunk contents or numeric high slots alone would not establish that they are safe to repurpose. A separate overlay table or virtual-index resolver would require redirecting every listed reader and dealing with their absolute table-base references.

Core selection is consumed repeatedly through the lifetime of player and CPU actor records. WPAR is materialized into actor fields by `sub_001B2090`; WWAZ is consulted for move lookup and sentinel tests by `sub_001A7F30`, `sub_001B4930`, and `sub_001B4BA0`. Animation/move paths also keep decoded state in per-actor/event buffers (for example WAZA at `+0xF6C` in `sub_001B4930` and FZUI at `+0x2BC` in `sub_001A85A0`); the source inspected here does not establish whether all such state can be safely rebound after a core change. Thus participant-specific core indices help express a virtual binding, but do not prove persistent animation pointers, descriptor-slot availability, safe cache invalidation, or runtime capacity.

## Proven retrieval links and their limits

The initializer `sub_001A47B0` constructs the two WAZA/FZUI/NAME descriptor triplets. For each WAZA chunk it stores payload stride at `0x3B85DC` / `0x3B8614`, row count at `0x3B85E0` / `0x3B8618`, group count at `0x3B85E4` / `0x3B861C`, and row base at `0x3B85EC` / `0x3B8624`. For FZUI it stores row stride at `0x3B85F4` / `0x3B862C`, row count at `0x3B85F8` / `0x3B8630`, and row base at `0x3B85FC` / `0x3B8634`. `sub_001A38B0` decodes a 39-byte (312-bit) FZUI row into a zero-initialized 136-byte output and rewrites 11-bit `0x7FF` values in output fields `+0x30` and `+0x34` to `0xFFFFFFFF`.

`sub_001A85A0` gives one proven WWAZ-to-FZUI retrieval chain. For IDs below 10000 it calls `sub_001A7F30` with the ID, then uses that routine's returned value as an index into FZUI table 1 (`row_base 0x3B85FC + index * stride 0x3B85F4`) and passes that row to `sub_001A38B0`. IDs at least 10000 are reduced by 10000; that normalized value directly indexes FZUI table 2 (`0x3B8634 + index * 0x3B862C`) and is decoded by the same routine. This proves the selected FZUI rows and the arithmetic join. It does not name the resulting FZUI fields or connect them to a particular animation-bank record. The decoder caller does not check the index against the corresponding FZUI count; those counts are in `0x3B85F8` and `0x3B8630` and must be enforced by an independent parser/runtime boundary. The inspected streams contain 2,088 rows in FZUI table 1 and 873 in table 2; these observed populations are data facts, not fixed format limits.

`sub_001A38B0` clears 34 dwords (136 bytes) and reads from a 39-byte packed row. The ordered bit-reader calls consume 311 bits, leaving one trailing input bit unused. Values are unsigned unless shown as float conversion. The fields below are named only by output offset. `u32`/`u16` and `f32` give native storage; the listed `0x7FF` rewrites are the exact observed sentinel transforms.

| Native output offset | Input bits | Native storage | Conversion / note |
|---|---:|---|---|
| `+0x00,+0x0C,+0x18,+0x24` | 11 each | u32 | Repeated field group, first field in each 3-field group |
| `+0x04,+0x10,+0x1C,+0x28` | 11 each | u32 | Repeated field group, second field in each group |
| `+0x08,+0x14,+0x20,+0x2C` | 7 each | u32 | Repeated field group, third field in each group |
| `+0x30` | 11 | u32 | Raw `0x7FF` becomes `0xFFFFFFFF` |
| `+0x34` | 11 | u32 | Raw `0x7FF` becomes `0xFFFFFFFF` |
| `+0x38,+0x3C,+0x40,+0x44` | 11 each | u32 | Raw |
| `+0x48` | 11 | u32 | Becomes `0xFFFFFFFF` when raw `+0x48` is `0x7FF` and raw `+0x44` is not `0x7FF` |
| `+0x4C,+0x50,+0x54` | 11 each | u32 | Raw |
| `+0x58` | 3 | u32 | Raw |
| `+0x5C` | 7 | u32 | Raw |
| `+0x60` | 4 | u32 | Raw |
| `+0x64` | 11 | u32 | Raw |
| `+0x68` | 2 | u32 | Raw |
| `+0x6C` | 5 | u32 | Raw |
| `+0x70` | 11 | u32 | Raw |
| `+0x74` | 2 | u32 | Raw |
| `+0x78` | 8 | f32 | Unsigned integer converted to float and multiplied by `MEMF(0x292378)` |
| `+0x7C` | 8 | f32 | Unsigned integer converted to float and multiplied by `MEMF(0x292378)` |
| `+0x80` | 8 | f32 | Unsigned integer converted to float and multiplied by `MEMF(0x292378)` |
| `+0x84` | 16 | u16 | Low 16 bits stored |
| `+0x86..+0x87` | — | zero | Cleared destination bytes, not written by decoder |

The wire order is `+0x30,+0x34,+0x38,+0x3C,+0x40,+0x44,+0x48,+0x4C,+0x50,+0x54,+0x58,+0x5C,+0x60,+0x64,+0x68,+0x6C,+0x70,+0x74,+0x78,+0x7C,+0x80,+0x84`, followed by the four 3-field groups at `+0x00..+0x2F` (each group is 11, 11, then 7 bits). The `+0x48` branch compares the immediately prior raw field at `+0x44` with `0x7FF`; it rewrites `+0x48` only when `+0x44 != 0x7FF` and raw `+0x48 == 0x7FF`. Thus this is not a paired-maximum sentinel. The first two explicit sentinels and this conditional transform are decoder behavior, not semantic names. The native-byte oracle comparison described above covers WAZA and WPAR only; this FZUI offset map is directly traced from the generated decoder and has not received the same sampled native-byte comparison. The two FZUI tables remain separate index namespaces: table 1 is selected by the result of the internal WWAZ scan, table 2 by external ID minus 10000. Each ordinal must be bounded by its own declared count before row access.

## FZUI consumer trace and animation-link boundary

In `sub_001A85A0`, `sub_001A38B0` writes the decoded row at actor `+0x2BC`. The caller immediately reads native offsets `+0x30` and `+0x34` at actor `+0x2EC` and `+0x2F0`. If either is `0xFFFFFFFF`, it replaces it with a value returned by `sub_00200BCC` using the actor's float at `+0xA4`; the results are stored back into those fields. It also reads the field at output `+0x48` (actor `+0x304`) and passes it through the same conversion when it equals `0xFFFFFFFF`. The output `+0x64` (actor `+0x320`) has a separate equality check against `0x7FF` and a conversion using actor `+0xA4` and global `0x3B8F2C`. These are direct post-decode transformations, not resource-index joins.

`sub_001A3310` reads output `+0x38` and `+0x3C` through actor offsets `+0x2F4` and `+0x2F8`, converts them to floating-point for comparisons against actor `+0x9C`, and changes actor state bits / may call `sub_001A8050` based on those comparisons. `sub_001A63B0` reads the four triples at output offsets `+0x00..+0x2F`: for each triple it checks the third member against `0x1A`, and, when selected, admits the first two members unless equal to `0x7FF`; it then sorts/uses the collected values in float comparisons and passes the computed values to `sub_00011520` and `sub_001A5DD0`. No target row from WAZA, NAME, an animation-bank descriptor, or animation-event table is selected by these observed consumers. The call to `sub_00011520` is present in generated C, but the corresponding implementation is outside the inspected generated source; it does not establish a resource join.

Within this bounded trace, the proven relation is WAZA lookup to FZUI row, followed by FZUI field use in actor-state checks and a value-processing path. No animation-bank linkage from FZUI `+0x30/+0x34/+0x38/+0x3C` or the four `+0..+0x2F` triples is established. Keep these as opaque decoded fields and do not author cross-resource edges from matching numbers or row order.

Within `sub_001A7F30`, the internal-ID path obtains the active fighter's WWAZ pointer from its 16-byte core descriptor and scans row offsets `+0x0C` through `+0x2EE` in steps of six (124 rows). It reads each row's second u16 at `+2` as a comparison value, and consumes the third u16 at `+4` in the returned-value calculation when the comparison selects that row. These are actual inputs to the result used for FZUI table-1 indexing; their domain meanings remain unresolved. The scan is shorter than the complete 130-row WWAZ chunk. The separate `sub_001B4930` path reads the first u16 (`+0`) for low-12-bit WAZA-row selection and bit-15 flagging.

A WAZA-to-WAZA retrieval is also proven. In `sub_001A8F00` (block at `loc_001A9033`), code reads `SMEM16(edi + 0xFA8)`, which is WAZA output `+0x3C` when the decoded row is at `edi + 0xF6C`, and passes it to `sub_001B4B20`; that helper multiplies the value by first-WAZA stride `0x3B85DC`, adds first-WAZA row base `0x3B85EC`, and invokes `sub_001A3630` on that row. Thus WAZA `+0x3C` is a first-table row selector in this consumer. The helper has no visible row-count check. In the inspected generated code, no direct read of decoded WAZA `+0x3A` or `+0x3E` was found; `+0x3A` still has the decoder-proven `0xFFF` to `0xFFFF` rewrite. The 12-bit selector can represent 0..4095, while the inspected first-table count is 826, so a safe independent implementation must require the `+0x3C` selector to be below the declared first-WAZA count before following it. This is a format/index bound, not proof that every retail move uses this link.

The initializer also pairs each core's WPAR and WWAZ chunks, but this audit has not established a cross-resource join from WPAR fields or WAZA `+0x3A/+0x3E` to NAME strings, animation ELF records, animation events, or voice rows. Counts, ordinal coincidence, and matching numeric ranges do not establish those links. No relocation/capacity conclusion follows from these consumer reads.

The minimum safe next implementation is an offline typed decoder/index layer that preserves the verified WAZA/WPAR raw layouts, validates WAZA `+0x3C` against the first-table row count, models the WWAZ scan and its 124-row bound separately from its 130-row envelope, and bounds both FZUI index paths by their declared row counts. Keep unresolved domain labels opaque until resource-level joins are traced. Before runtime use, the 141-row core descriptor table needs a separate relocated storage/indirection design with every retained pointer and consumer traced; the literal scan alone does not prove relocation safety or runtime capacity.

## Dangling-reference validation rules and unresolved terminal fields

The generated-code address arithmetic gives three separate index namespaces that an offline graph validator can enforce without assigning semantic names:

| Source and field | Proven target namespace | Required validation | Evidence / caveat |
|---|---|---|---|
| Core descriptor index in actor `+0x2C` | Core descriptor rows, zero-based `0..core_count-1`; inspected native population is 141 | Require index below the parsed core count before resolving either WPAR or WWAZ | Initializer uses 16-byte rows; participant setup stores a dword index. The native absolute table cannot safely accept an out-of-range ordinal. |
| WWAZ row selected by ordinary move ID | Six-byte rows `0..129` in that actor's selected core | Require move ID in the ordinary-row domain `0..129` before `id*6`; handle the explicit special ID windows separately | `sub_001B4930` indexes by `id*6` without a row-count guard. `sub_001A7F30` uses a distinct scan over only rows 2..125 (byte offsets `+0x0C..+0x2EE`), so its result relation must not be conflated with the direct lookup. |
| WWAZ first word at row `+0` | WAZA table 1, index `word & 0x0FFF` | Treat exact `0xFFFF` as an absent/sentinel link; otherwise require decoded index `<` that WAZA table's declared row count (826 in the inspected stream) before following it | `sub_001B4930` masks low 12 bits and propagates bit 15 to actor `+0xF68`, then decodes the selected primary WAZA row. It does not test `0xFFFF` or compare against the row count before dereference. `sub_001B4BA0` separately tests the same WWAZ first word against `0xFFFF`; callers that use the direct decoder still need explicit validation. Bit 15 is retained as a flag, not a second-partition selector. |
| WAZA output `+0x3C` | WAZA table 1, index stored as u16 from 12 input bits | Require value `<` the declared primary WAZA row count before following it | `sub_001A8F00` reads actor `+0xFA8` (decoded WAZA buffer base `+0xF6C`, hence record `+0x3C`) and calls `sub_001B4B20`; the helper uses primary stride/base and performs no count check. Primary count observed here is 826. No sentinel rewrite is performed on `+0x3C`. |
| External move ID `>=10000` | WAZA table 2 after subtracting 10000 | Require normalized ordinal `<` the declared secondary WAZA row count | `sub_001B4930` computes `id-10000`, multiplies by secondary stride, and adds secondary base; no count check is visible. Do not apply first-table bounds to this namespace. |
| `sub_001A7F30` return / external normalized ID | FZUI table 1 / FZUI table 2 respectively | Require resulting ordinal `<` the corresponding declared FZUI count | `sub_001A85A0` consumes the returned or normalized index to fetch FZUI. Counts are stored separately (`0x3B85E0` and `0x3B8618` for WAZA; `0x3B85F8` and `0x3B8630` for FZUI). |

The status of the remaining WAZA tail fields is now precise at the consumer boundary. The decoder writes `+0x3A` as a 12-bit value and converts `0x0FFF` to the stored `0xFFFF` sentinel. `+0x3E` is stored as an unmodified 12-bit value. In the generated files searched, there are no direct reads at actor offsets `+0xFA6` or `+0xFAA` (the corresponding WAZA output `+0x3A` and `+0x3E`). The observed `+0xFA8` reads pass the `+0x3C` field to `sub_001B4B20`. Thus this audit has no evidence that `+0x3A` or `+0x3E` is a join to a WAZA row, FZUI, NAME, animation event, or voice record; retain both as opaque values and do not reject or resolve them as links absent further consumer evidence. The absence finding is limited to direct generated-C offset reads, not proof that no indirect or pointer-based consumer exists.

For an independently authored graph, the smallest validated adapter is therefore: (1) parse the two WAZA descriptors and each core pair, (2) keep core ordinal, WWAZ row ordinal, WAZA partition ordinal, and FZUI ordinal as distinct typed keys, (3) preserve WWAZ first-word flags separately from its low-12-bit candidate index, treating `0xFFFF` as no edge, (4) bounds-check every non-sentinel edge against its target descriptor's declared count, and (5) apply the proven WAZA `+0x3C` to primary-WAZA edge. Preserve external IDs as table-2 keys only after subtracting 10000 and validating against table 2. Do not materialize edges from WAZA `+0x3A/+0x3E`, WWAZ second/third words, NAME order, or numerically fitting animation IDs; this audit has not established those joins.
