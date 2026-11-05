# Fighter animation curve types 20 and 21 — 2026-11-04

Bounded static audit of the user's own XBE/generated C plus read-only decoding of retail `motion/wres_all.viv`, bank `wres001`. No builds, native evaluation, game runs, or source edits. This identifies structural reads and does not certify numerical curve behavior or runtime readiness.

## Shared serialized header

Both types use a minimum 0x14-byte record header R followed by inline compression descriptors and packed bytes:

| Offset | Read / role |
|---|---|
| +0 u16 | 20 or21 type discriminator |
| +2 u16 | metadata returned by EB850 |
| +4 pointer | N u16 destination indices, float-slot offsets into caller output |
| +8 pointer or zero | optional transition-time u16 array |
| +0xC u16 | K, pose/sample count |
| +0xE u16 | N, animated channel count |
| +0x10 u8 | block shift s; block width B=1<<s |
| +0x11 u8 | C, constant channel count |
| +0x12..13 | not given semantic meaning by this audit; observed nonzero in type20 |

Native shift semantics mask the shift count; an offline supported format should explicitly bound s rather than emulate arbitrary counts or allocate from them. Retail wres001 uses s=3 in all153 records examined. Do not assume +0x12..13 are reserved zero.

A nonzero +8 must be an explicit local pointer relocation for an offline data-only adapter; a zero field is a supported native alternative. With no times, evaluation chooses an integer sample by truncating/clamping input time to 0..K-1 and duration returns K. With times, it searches transitions, with an implicit first pose before the first transition and final pose after transition K-2. Minimum transition array length is K-1 u16 values. Duration F2140(type20)/F05D0(type21) reads T[K-2], increments as a **u16**, then converts to float: 65535 wraps to0. Require K>=2 for this duration route when times exist; do not merely accept K1 plus a nonzero time pointer.

Times order: native searches and divides by interval width without a general monotonicity check. The actual153 wres001 arrays read in this audit are strictly increasing; zero duplicates and zero descents. This is an observation on these arrays, not proof that every native animation requires a global strict-increasing rule or that other banks meet it. Rejecting ambiguous duplicate transitions may be a supported-profile policy, but label it as policy.

## Type20: three-component channels

Constructor F06B0 installs vtable `0x2B5D50`, wrapper type20. Main evaluation slot+0x18 is F14F0, filtered path F0700; slot+0xC F06E0 delegates to it, duration F2140, coverage F1460, attach F2120. Wrapper attach stores R at wrapper+0xC and resets cached indices +0x10/+0x1C to-1.

Descriptors start R+0x14, stride36 per animated channel. F1250 reads float32 values at descriptor+0,+4,+8 (three bases) and +0xC,+0x10,+0x14 (three ranges/scales), and u16 values +0x18,+0x1A,+0x1C,+0x1E,+0x20,+0x22. It derives runtime compression coefficients from those scalars. Those six float values per channel should be finite for an offline safe profile. No native finite checks were found. Animated samples decode packed bytes into three components and write output float slots destination,destination+1,destination+2. A channel has a sixteen-byte runtime cache slot, but only three output floats are copied by the direct route.

## Type21: scalar channels

Constructor EF320 installs vtable `0x2B5CC8`, wrapper type21. Main evaluation slot+0x18 EFD80, filtered path EF370; slot+0xC EF350 delegates, duration F05D0, coverage EFCF0, attach F05B0. Attach stores R and resets cached indices as in type20.

Descriptors start R+0x14, stride12 per animated channel. EFBD0 reads float32 descriptor+0 base and +4 range/scale, plus u16 +8,+0xA, then creates runtime coefficient records. Animated samples decode packed bytes into one scalar per channel, written at output[destination]. The two descriptor floats should be finite as an offline supported-profile constraint; the native path performs no finite check.

## Inline packed and constant ranges

The following range construction follows the address arithmetic at F1DB8..F1E80(type20) and F02C6..F037E(type21). Use checked integer operations. Let D=3 for type20,1 for type21; descriptor stride L=36 or12; `align2(x)=(x+1)&~1`, `align4(x)=(x+3)&~3`.

1. `packed = R+0x14+L*N`.
2. `stride = align2(D*N*(B+1))`.
3. `end = packed + (K>>s)*stride`.
4. `rem = K & (B-1)`. If rem>0, `end=align2(end+D*N*(rem+1))`.
5. If N==0, native additionally computes `end=align2(end)` (increment then clear bit0).
6. Constant destination table begins at end and contains C u16 entries.
7. Constant float values begin at `align4(end+2*C)`, containing D*C float32 values.

The packed region therefore contains block base/delta byte rows, with a B+1 factor, not simply K*N byte values. The final constant section is inline, not another pointer relocation. Finite-check its D*C float values. Type20 writes three floats per constant destination; type21 one. A zero C causes the constant copy loop to skip. The primary animated destination pointer covers N entries; it does not substitute for the independent inline constant table.

These formulas were exercised against all146 type20 and7 type21 records in retail wres001: every calculated region is inside validated .data and every descriptor/constant float inspected is finite. This confirms these structural ranges against this sample; it does not verify decompression outputs or exclude all cross-record overlap. To establish exclusive record ownership, a parser needs an explicit span/overlap policy rather than relying solely on whole-section bounds.

## Runtime state and external context

These are ordinary separately constructed wrappers, unlike type25's embedded mutable prefix. Constructors/attach/evaluation update wrapper caches and allocated arrays: cached indices +0x10/+0x1C, sample arrays +0x14/+0x18 and+0x20/+0x24, filter state +0x28, derived coefficient array +0x2C. F1250 allocates N*16 twice plus N*48 derived coefficients; EFBD0 allocates N*4 twice plus N*16 coefficients. Those are runtime allocations, not serialized payload lengths. No audited write was identified as modifying the serialized header/descriptors. Do not classify wrapper cache pointers as imports that must be allowed in an ELF.

The unfiltered paths read their sample bytes/descriptors from R and write caller output. They do not select an external sample-bank table as type25 does. Filtered routes also consume caller selection/bitset context. Coverage F1460/EFCF0 divides destination indices by12 to choose bitset entries. Destination-table values and constant destinations still control caller output offsets; .data bounds and finite floats alone cannot establish those writes fit the skeleton/pose output. An offline structural parser can expose the highest destination and component width; native admission must check against the actual output shape and selection context. Negative/NaN/infinite input time, exact interpolation, float overflow, filtering and output compatibility were not exercised here.

## Actual wres001 observations

| Type | Records | K range | N values | s values | C values | Timed arrays | Highest destination |
|---|---:|---|---|---|---|---:|---:|
| 20 |146|8..132|1|3|0|146|8|
| 21 |7|12..71|1,2|3|1,2|7|10|

First type20: R=0xC64F0, K29,N1,s3,C0, first transitions5,10,18,24,27,29,31,37; destination8; packed end relative to R158. First type21: R=0xC72EC,K23,N1,s3,C2, first transitions4,8,10,12,16,20,23,26; animated destination9; constant destinations8,10 and constant values0,0; packed end relative to R60. Offsets are .data-relative, not file offsets or guest VAs.

The paired report `fighter-animation-bank-records-2026-11-04.md` covers the bank loader and type15 parents. Keep runtime_ready false: this audit supplies a type20/21 structural schema and observed range checks, not a native activation result.
