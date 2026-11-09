# Fighter animation type11 and type25 equal times — 2026-11-04

Bounded static audit of the user's own generated C and XBE. No code changes, builds, native evaluation, or game runs. Corpus counts (22 type11 records across 446 banks) are supplied context, not independently recounted here. Runtime readiness, numerical decoder validation and output-context validation remain false.

## Type11 dispatch and structural schema

`src/recomp/gen/recomp_0007.c` E6220 has an explicit proven switch slot11 at E635D, calling E6510. E6510 sets wrapper type11 and vtable 0x2B5958. Independently reading that table from the local XBE gives attach slot+0x48 EC010, evaluation slot+0x18 ED000, alternate evaluation slot+0x0C EC490, coverage slot+0x44 EC710. This is a separately constructed 0x24-byte wrapper; it does not require type25's embedded prefix fixup. EE260 is the recursive type15 initializer and EE890 specifically installs type25's prefix vtable; those are not type11 evaluators.

Let R be the serialized record and D its descriptor:

| Field | Proven use |
|---|---|
| R+0 u16 | type11 dispatch |
| R+2 u16 | inherited EB850 metadata |
| R+4 pointer | descriptor D |
| R+8 u16 | K sample/pose count |
| R+0xA inline | S/4 u16 destination float-slot offsets |
| D+0 u16 | S scalar count |
| D+2 u8 | quantization width B; FC3F0 branches for4,8,16 |
| D+3 u8 | no semantic interpretation established |
| D+4 | S triples of float32, stride12: offset, multiplier, base |
| D+4+12*S | packed delta rows |

The supported structural profile should require K>=1, S>0 and S%4==0, B in4/8/16, an explicit local relocation at R+4, finite descriptor triples, checked arithmetic and complete .data bounds. Minimum inline R extent is `0xA+2*(S/4)`; descriptor extent is `4+12*S+(K-1)*ceil(S*B/8)`. With S divisible by4 this is whole-byte exact for all three widths. FC3F0 initializes from bases and accumulates delta rows; pose0 has no packed delta row. ED000 requests the clamped current index and, when fractional time has a following pose, FC8A0 requests the next index. This is the same codec used by type13, but type11 has no time-array pointer: it uses integer sample positions directly.

EC010 allocates S*4 runtime cache bytes, stores R at wrapper+0xC and resets cached index wrapper+0x10 to-1. E6510 zeros wrapper+0x14,+0x18,+0x1C,+0x20. These are mutable runtime state, not serialized pointer ranges. ED000/EC490 truncate the incoming float time, clamp the direct sample index to0..K-1, and use fractional time to interpolate when a next pose exists. Negative/NaN/infinite time and exact numerical codec behavior are not validated by this structural audit.

Each ordinary output group reads one destination at R+0xA, copies four scalar-cache floats and advances scalar cursor by4. Therefore `required_output_floats=max(destinations)+4`; actual caller output must cover this range. EC710 uses S>>2 groups and divides destination by12 for selection-bitset coverage. Filtered paths also consume selection context and runtime caches. There is no external sample-bank table like type25's, but destination/output and selection-bitset compatibility are still external context obligations. This layout does not prove bone names, exclusive span ownership, numerical finiteness after accumulation, or runtime admission.

Primary anchors: E6220/E635D; E6510; EC010/EC04A; ED000/ED027..ED124; EC490/EC4C6..EC571; EC710; FC3F0/FC443..FC4D1 and quantization branches; FC8A0. Generated line numbers may change, so use addresses.

## Type25 equal-time semantics

The corpus log records retail base00 as the sole strict-time supported-profile rejection. The generic strict-increase rule is a policy, not a native assertion. FDB40's exact key-selection code provides evidence that **nondecreasing duplicate times are consumed deliberately by the search**, with qualifications below:

- FDB40 first clamps `t<=T[0]` to key0 (FDB78), and `t>=T[K-1]` to key K-1 (FDB91).
- For interior times it starts from the mutable cached key and compares u16 times against trunc(t). FDBAA..FDBCF advances while following times are <=trunc(t); FDBD1..FDBE4 moves backward while current times are greater. For a nondecreasing array this selects the rightmost key at or before trunc(t), skipping duplicate runs.
- FDBEB compares the original float time to the selected key time. Exact equality takes FDF40, clears interpolation, and directly copies that key. Otherwise FDC01 computes `(t-T[i])/(T[i+1]-T[i])`.

Thus an interior equal-time run acts as a key/sample change: immediately before the time interpolation approaches the first key of the run; at the time the rightmost key is selected. A duplicate run at the first timestamp has an endpoint exception: at/before that timestamp key0 wins; just afterward the rightmost duplicate participates. A duplicate final timestamp selects the last key at/after it. Equal-time keys can have distinct sample indices. This is meaningful discontinuity behavior, not grounds to sort/deduplicate serialized keys or require equal sample indices.

For finite nonnegative t and nondecreasing times, a chosen interpolated pair has positive width because the search skips all next times <=trunc(t), whereas remaining next time is an integer greater than t. This establishes no analogous semantics for descending times: searches assume ordering, and next-key arithmetic/interpolation can become invalid. Keep K>=1 and all K sample bytes/K u16 times bounded. Native sample-bank context, external sample bounds, destination bounds and finite samples remain independently unvalidated.

### Actual base00 rejection: unsigned descents, not duplicate times

Read-only extraction through Archive/unpack/AnimationEnvelope/AnimationIndex independently inspected every type25 record in retail base00. Exactly eight records have nonincreasing pairs, each solely at index0: **65532 -> 0**. There are no equal-time pairs among those printed failures. Coordinates below are .data-relative.

| Record R | K | Time pointer |
|---|---:|---|
| 0x6AF5C |11|0x6AF30|
| 0x6AF14 |11|0x6AEE8|
| 0x6AEAC |11|0x6AE80|
| 0x6AE64 |11|0x6AE38|
| 0x6A4DC |12|0x6A4B0|
| 0x6A494 |12|0x6A468|
| 0x6A42C |12|0x6A400|
| 0x6A3E4 |12|0x6A3B8|

For R0x6AF5C times are (65532,0,5,9,19,26,29,32,41,62,69), sample indices (0,20,3,19,19,19,19,19,0,19,1). For R0x6A4DC times are (65532,0,3,5,23,26,29,32,42,45,49,61), samples (0,0,20,0,0,0,19,20,20,20,3,20).

65532 could resemble signed -4, but FDB40 explicitly zero-extends time words (ZX16 at its first-time and final-time reads), then converts to float. Reinterpreting as signed would therefore contradict this exact consumer. With this array the initial clamp selects sample0 for ordinary finite t<=65532; t>65532 passes the first clamp and then selects the last key because t>=69 (or61). This surprising native behavior is not evidence to normalize or repair the serialized values. Further producer/context investigation is necessary to determine whether these tracks are ever used or intentionally inert. **Keep this corpus rejection: changing strict increase to nondecreasing would not resolve it anyway.** Keep all runtime_ready/numerical/output-context flags false.
