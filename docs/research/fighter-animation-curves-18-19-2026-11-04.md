# Serialized animation types18/19 — 2026-11-04

Bounded static follow-up to `fighter-animation-bank-records-2026-11-04.md`. Read the owner's generated `src/recomp/gen/recomp_0007.c`, mapped vtables through section VA/raw offsets in the local XBE, and inspected only wres001 ORD/ORL/MNL through existing setup readers. No game runs, builds, implementation changes, external code, or asset exports. This establishes structural ranges and consumer boundaries, not a complete numerical decoder or runtime acceptance.

## Dispatch and native entry points

| Serialized type | Constructor | Vtable VA | Attach (+0x48) | Duration (+0x10) | Evaluation (+0x18) | Coverage (+0x44) |
| --- | --- | --- | --- | --- | --- | --- |
|18|F4880|2B5E78|F55C0 -> F6BA0|F4900|F5BD0|F5540|
|19|F2220|2B5DE0|F22B0|F22C0|F2580|F4280|

E6220 supplies the constructor dispatch. The vtable words above were independently read from `game/default.xbe`, not inferred from adjacent function order. Type19 also has a concrete +0x54 filtered evaluator F33C0: F22F0 and the nonnull third-argument branch of F2580 dispatch there. Type18's nonnull third argument goes to F55D0 directly. The unfiltered routes below were the primary bounded read; the filtered routes were inspected for the same output addressing/cache behavior, not exhaustively decoded.

Constructors allocate mutable wrapper state separately from serialized R. Both store R at W+0xC. Type19 attach simply assigns that pointer; its first evaluation lazily calls F4600. Type18 attach immediately calls F6BA0. No embedded serialized wrapper prefix like type25 was established for either type.

## Shared serialized header and time domain

| Offset in R | Proven access |
| --- | --- |
|+0 u16|type discriminator|
|+2 u16|metadata through shared EB850; semantic label not assigned|
|+4 u16|K, number of decoded key states|
|+6 u8|C, animated four-scalar channel count|
|+7 u8|type18: static channel count Z; type19: block exponent q|
|+8 pointer or zero|optional u16 transition-time array T|
|+0xC pointer|C destination indices, each **one byte**|
|+0x10 onward|type-dependent inline payload|

With T absent, evaluation converts incoming time to an integer key and clamps to0..K-1; duration returns float(K). With T present, cached interval search considers T[0] through T[K-2], uses an implicit initial state at time0, and duration is `float(T[K-2]+1)`. Interpolation's first interval divides by T[0]; later intervals divide by differences of adjacent transition times. T therefore requires **K-1 u16 entries**, not K, for the observed K>=2 profile.

For an offline supported profile require positive K, and K>=2 when T is nonnull; bound T with relocation-backed reads and require positive T[0] and increasing subsequent times. These last time constraints are safety policies supported by the measured corpus below, not checks performed by native code. No independent proof of the physical time unit was obtained; do not name these values seconds or frames solely from appearance.

Both duration helpers test the relocated pointer value for zero. A future parser must handle an explicit serialized zero separately from relocation-backed local targets, and reject an unrelocated nonzero word. All sampled records had a local T relocation.

## Type18: grouped compressed four-scalar channels plus static channels

F6AE0/F6460 establish the inline storage arithmetic, independent of any semantic channel name:

- u8 q at R+0x10, byte R+0x11 not assigned semantics.
- Descriptor array begins R+0x12: C descriptors, **16 bytes each**, eight u16 values. F6BA0 converts the first four through scale-and-subtract-one to runtime additive values; the last four through scaling to runtime multipliers. The descriptors are not inline float32 arrays.
- P = R+0x12+16*C is the compressed stream base. B=`1<<q` states per block; S=`align2(3*C*(B+1))` is full block stride. A block has6*C bytes of absolute seeds (four12-bit scalar values packed in6 bytes per channel), followed by3*C bytes per delta state. Each delta channel uses three bytes: their upper6 bits form the first three quantized components; concatenated lower2 bits form the fourth. F64C0 adds decoded deltas; F6610 reverses them by subtraction to reuse cached states.
- Let Q=`K//B`, U=`K%B`. F6AE0 computes the static-index list at `J=P+Q*S+(3*C*(U+1) if U else 0)`. J contains Z byte destination indices. F6460 computes static seed base `A=align2(J+Z)`; A contains **6*Z bytes**, decoded with the same four12-bit absolute seed layout. This handles a short final block without rounding it up to a full block. Native arithmetic has no visible checked overflow; offline arithmetic must be bounded before reading.
- Minimum full serialized inline range for this shape is R through A+6*Z. The C dynamic destination bytes at R+0xC's pointer and K-1 time entries are additional independently bounded ranges. They may reside elsewhere in .data; do not assume a destination/time pointer immediately follows the inline stream, or use its address as the stream's length.

F5BD0 writes four decoded/interpolated float32 values per dynamic channel and four decoded values per static channel. Its direct and interpolated routes write to output **O+0x10+48*d**, offsets0,4,8,0xC, where d is the respective byte destination. This is a48-byte caller element stride with a16-byte leading offset; it is not the type13 float-slot indexing convention. F5540's coverage traversal visits the C dynamic destination bytes; it is not proof that this helper includes all Z static destinations.

W+0x10 holds converted32-byte-per-channel descriptors and the allocation from which two16*C-byte state buffers are carved. W+0x14 is P, W+0x18 is S; W+0x1C and W+0x28 are mutable key/cache indices; W+0x24/+0x30 are current/next buffer pointers which can swap; W+0x34 points at J; W+0x38 points at A; W+0x3C switches cache handling on the unfiltered route. These are runtime mutable controls, not fields to serialize as authored pointers.

## Type19: axis-selected compressed four-scalar channel groups

F4600 establishes a distinct inline structure:

- q is R+7. C descriptors begin R+0x10, **14 bytes each**. Six u16 quantities occupy+0..+0xA; the final u16 at descriptor+0xC is an axis selector. F4600 reads the leading two quantities to construct constant runtime transforms through EED20; later evaluation reads the remaining quantities as quantized offset/scale controls and the axis selector. Exact Euler/quaternion/bone naming is outside this finding.
- P=`R+0x10+14*C`. B=`1<<q`; S=`align2(C*(B+1))`. Absolute block seeds occupy2*C bytes: one byte for the chosen spatial scalar, one for the fourth scalar; other spatial scalars start at zero. Later states add **one byte per channel per delta**; its high nibble and low nibble drive the chosen spatial/fourth updates. Runtime cache permits reuse within a block.
- The observed full stream structural bound is `P+(K//B)*S+(C*(K%B+1) if K%B else 0)`. This matches the seed/delta read arithmetic:2*C seed bytes plus(B-1)*C deltas for a full block. All computed ranges fit .data in the sample; this does not by itself establish semantic correctness of all descriptor values.
- Axis selector0/1/2 selects different component/control paths. The unfiltered evaluator contains normalization (`sqrt(sum of four squares)` followed by reciprocal) and composition with the constant runtime transforms. Finite decode and nonzero normalization magnitude therefore remain numerical checks beyond byte bounds. Do not declare arbitrary u16 descriptors safe just because their arrays fit.
- The C byte destination list again selects **O+0x10+48*d**, with four float stores. F4280 marks/query-checks those destination indices through an external bitset and accumulates coverage/count bounds; no trusted output capacity is encoded in the record.

F2220 initializes W+0x18/+0x1C to-1 and buffer pointers to zero. F4600 lazily sets W+0x10 to the inline descriptor array, +0x14 to P, +0x18 to S, allocates16*C bytes each for mutable decoded state and two constant-transform buffers at +0x28/+0x2C, and uses W+0x1C as the key cache. Attach does not reset or build all those buffers, so offline assets must not contain live copies of wrapper/cache state.

## Independent wres001 measurements

Source: `game/motion/wres_all.viv` entries `wres001.ord`, `.orl`, `.mnl`, decoded with Archive/unpack, AnimationEnvelope and AnimationIndex; only graph-reachable unique records are counted. Hashes of decoded parts:

- ORD `faff20095502bd8ffa6ef82160d4514fa5fe8d1af364cba45b03d3459a32725b`
- ORL `1bb14e0d2b0eed7759ff5e166984a756e9c6eafd43bfd5899f9943df2ec6b70a`
- MNL `861b825828d8b84eac0d04930a2106b7faf8d778a7722be0d0183b79179e4cc0`

| Observation | Type18 | Type19 |
| --- | --- | --- |
|Unique reachable records|129|129|
|K range|8..132|8..132|
|C range|20..33|2..11|
|Block exponent q|3 in all129|3 in all129|
|Additional static count Z|0..17|not present in this layout|
|T relocations|129 local|129 local|
|T[0] range|1..17|1..17|
|T[K-2] range|40..300|40..300|
|Non-increasing adjacent transitions|0|0|
|Dynamic destination range|0..92|0..92|
|Duplicate dynamic destination records|0|0|

Type18 byte+0x11 was zero in every record. Its static destinations also range0..92; no static duplicates or overlaps with the same record's dynamic list were found. Type19 descriptor axis selectors measured0:265,1:462,2:17; no other values. These findings justify a conservative observed profile (q=3, known axis values, reserved byte0), not general claims about every game animation bank.

First type18 record by ascending .data offset: R=0x21D0, metadata16163, K10, C24, Z1, q3; time target0x1F08 and dynamic destinations target0x21B7. First type19: R=0x2088, metadata16163, K10, C11, q3; same time target0x1F08 and destination target0x207C. Both point backward, reinforcing that pointed-to arrays cannot serve as implicit inline lengths. No payload bytes are included in this report.

The computed type18 descriptor+stream ranges (before static list/seed tail) were1222..14834 bytes from R; type19 descriptor+stream ranges104..712. All were checked through `model.data_range`; type18 static list and6*Z seeds were separately checked, as were T and dynamic destinations. This is structural checking, not evaluation or a complete relocation/overlap ownership policy.

## Admission boundary and unknown external context

Each output write needs `output_bytes >= 0x10+48*d+16` relative to the supplied O. The sampled d<=92 requires at least4448 bytes for these writes. That number is **not a proven native allocation size or bone count**. An offline validator must receive a separately trusted caller output shape and require every destination to fit it. Coverage/filter bitsets also need capacity for each destination (word index d>>5), plus valid caller pointers; the record supplies no bitset size.

These two types do not visibly choose an external sample bank like type25. Their compressed samples are local, but evaluation still requires the caller's output buffer, optional filter/selection context, allocator/manager state, and initialized wrapper caches. Their ultimate bone/channel mapping and the native caller's allocation extent were deliberately not reverse engineered here. Filtered evaluator completeness, numerical reproduction/finite-result checks, all-bank corpus acceptance, event linkage, and runtime ownership remain open. Existing `runtime_ready`/full-record-validation flags should stay false until implementation and independent acceptance cover those boundaries.

Evidence anchors in generated `recomp_0007.c`: F22B0/F22C0, F2580..F33B0, F4280, F4600..F4803; F4900/F49B0..F4C09; F5540/F55C0/F55D0; F5BD0..F613D; F6460/F64C0/F6610/F6AE0/F6BA0. Native VAs are written unpadded in lifted literals; function declarations retain padded names.
