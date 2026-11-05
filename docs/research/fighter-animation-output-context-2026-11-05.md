# Fighter animation output context â€” 2026-11-05

Bounded read-only audit of original generated C in `src/recomp/gen/recomp_0007.c`. No source modifications, builds or game runs. This report establishes the consumer contract and specific remaining ownership gap; it does not certify native output-context admission.

## Concrete consumer contract

Type11 ED000 accepts `(time, float_output, optional_selection)` via vtable+0x18. With null selection its ED027..ED124 route obtains K from R+8, D from R+4, S from D, destinations from R+0xA. It decodes S dense cache scalars and writes four floats at each `float_output+4*destination`. Fractional interpolation goes through FC8A0 with group width4. Its direct ED0F3 loop writes destination lanes0..3, increments cache cursor by4 and destination cursor by1. There is no destination count/range/alignment/uniqueness check against output allocation in this consumer.

Type13 ECBB0 is a slot+0x0C adapter that forwards a null selection to slot+0x18, ED300. ED327 gets K from R+0xC, D from R+4, T from R+8, destinations from R+0xE. The direct ED470 loop likewise writes four floats per destination with dense cache group cursor. Both records therefore require externally established output storage reaching `max(destination)+4` floats; their S*4-byte cache allocation is not the size of the scattered output.

**Type13 interpolation is a separate numerical route:** ED3F7 decodes the next four scalars with FC3F0 into a stack temporary; ED41A..ED43E invokes EA010 with the current cache group, temporary next group, mapped output address and time weight. It does not use FC8A0 here. EA010 (EA010..EA127) computes a four-component dot product and branches between a direct difference interpolation and a different signed/sum path at EA0BB. Matching full scalar poses and FC8A0 weighted deltas does not validate this type13 interpolation operation. The scalar audit's helper formulas remain valid, but must not be promoted to a claim about ED300's interpolated pose.

Selection paths are ED130 onward for type11 and ED4AD onward for type13, delegating to routines such as EC100/ECBD0. The stored selection pointer changes reset the cached scalar index. Coverage EC710 (type11) and ECDF0 (type13) use S>>2 destination entries and derive selection item `destination/12`, then a bitset word/item. This establishes a twelve-float per selection-item convention, but not that arbitrary four-float destination starts are semantically valid. In particular these functions do not enforce destination%4==0 or destination%12 in {0,4,8}.

## Caller propagation and ownership boundary

Type15 EDF90 is the immediate aggregate caller. EDFD0..EDFE6 sends the **same** output and selection pointers to each child slot+0x18, visiting children from count-1 down to0. It lazily creates only the child-wrapper array through EE400. It neither sizes the output nor partitions child output ranges. Therefore a parent can intentionally combine distinct channel records into one output, but the type15 count does not establish the float capacity.

The blend caller EAB50 supplies further concrete context evidence:

- EAB6D..EAB88 forwards caller output at frame+0xC and selection at frame+0x10 to child wrapper+0x18, after subtracting the child's time origin.
- EACDD..EAD1A instead evaluates the two children into blend-object buffers at object+0x10 and+0x14.
- EAD38 loads N from the object referenced at blend-object+0xC, field+8. EAD46 computes a record stride of48 bytes (`3*N <<4` for the last element), then blending walks those records backward. This is consistent with twelve floats per item, and agrees with destination/12 coverage.
- EAA90/EAB00 initialize the child references and time parameters, but do not allocate those +0x10/+0x14 buffers. Their allocation/attachment owner was **not resolved by this bounded read**.

Accordingly the exact unresolved link is: identify who constructs/attaches the blend object's +0xC context, sets its item count at context+8, and allocates/assigns buffers+0x10/+0x14 (or the external output passed at EAB50 frame+0xC). Until that link is established, `N*12` is a demonstrated processing shape, not a verified allocation capacity. Do not infer an admitted bone count from the bank, S, the greatest serialized destination, or the selected-bitset coverage function. The output consumers themselves have only a raw pointer, without a byte-length parameter.

## Duplicate and overlapping destination semantics

There is no rejection or deduplication in the audited consumers. Direct copy loops visit serialized groups in order, so repeated destinations leave the final group's four values; partially overlapping groups likewise overwrite earlier lanes. Type15 visits child wrappers in reverse order, so cross-child overlaps follow that ordering.

The interpolated path matters: FC8A0 (type11) first scatters all current cache groups, then adds weighted deltas in group order. Duplicate destinations can therefore combine deltas over whichever base group was scattered last; it is not simply a last-group interpolation. Type13 ED3F7..ED43E fully computes/writes each interpolated group in order through EA010. These distinct outcomes prove that a duplicate is not necessarily a native memory fault, but they do **not** prove it is a valid skeleton authoring contract. No native duplicate/overlap acceptance assertion was found. An offline owned-output evaluator can report these ordered semantics; native context admission needs the actual producer contract.

## K1 and leading65532 -> 0

Type11 K1, null selection, finite ordinary nonnegative time: ED027..ED077 clamps index to0; FC3F0 old-1,target0 copies bases; ED0A2 tests next index1 against K1 and skips fractional interpolation. ED0F3 scatters the base group. This route needs no packed delta rows. This is a route-specific observation, not a validation of selection or every vtable method for K1.

Type13 K1 is not an equivalent self-contained base-only shape. EC8C0 reads T[0] unconditionally before any K guard; ED590 reads `T[K-2]`, hence T[-1] for K1, then adds1. Even when one evaluation input might take a base route, the native duration contract accesses before the nominal time array. Retain K>=2 for the established type13 structural profile.

Type13 transition words are unsigned. EC8C0 zero-extends T[0], converts it to float, and returns pose0 for time<T[0]. ED300 then differs from type25: at ED379 it uses implicit first boundary0; for positive time not equal0, ED3C6 computes weight `time/T[0]` and interpolates pose0 toward pose1 through EA010. Thus a leading65532 followed by0 is **not** type25's constant-first-sample clamp. At ordinary small positive times it makes the first transition exceptionally slow; the descending following transition is hidden until the initial threshold is passed. ED590 still computes duration from final T[K-2]+1, potentially yielding a short duration inconsistent with that first transition threshold.

No signed -4 reinterpretation occurs at EC8C0/ED3C6. No sorting, wrap normalization, or negative-time semantics is justified by this consumer. This report audits the consumer only: it did not recount which type13 records in the corpus have this leading descent. The earlier exact eight base00 offsets belong to **type25**, and must not be relabeled as type13 evidence.

## Evidence boundary

Established: raw output pointer arguments; four-float scattered writes; reverse type15 child order; twelve-float context processing stride in blend caller; no consumer duplicate or capacity validation; different type11/type13 interpolation routes; type11 base-only K1 route versus type13's unconditional time accesses.

Unresolved: precise output allocation owner/extent, semantic valid channel starts, skeleton/name binding, allowed cross-track overlaps, all filtered routes' complete external bitset bounds, and the corpus identity/usage of type13 descending-time records. Keep native output_context_validated/runtime_ready false. Main code anchors are EDF90, EAB50/EACDD/EAD38, EAA90/EAB00, ED000/ED0F3, ED300/ED3F7/ED43E/ED470, EC710/ECDF0, EC8C0, ED590 and EA010.


## One-layer follow-up: constructor and buffer attachment

The blend wrapper is **serialized/wrapper type6**. E6220 slot6 calls 23970 (`recomp_0000.c`); 23970 installs vtable0x28B108, type6 at+8, clears context+0xC and buffers+0x10/+0x14, sets special index+0x28=-1 and clears+0x7C/+0x7D. The local XBE table independently places EAB50 at vtable+0x18 and EB1E0 at+0x0C. This identifies the object class exactly; its constructor performs no output allocation.

A concrete attachment helper is **22A50** (`recomp_0000.c`, original22A50..22A86). With ECX=W its three arguments are `(context C, buffer A, buffer B)`. It stores A at W+0x10 and B at W+0x14, invokes `E9010(C,A,null_selection)` and `E9010(C,B,null_selection)` to initialize them, then stores C at W+0xC. Thus buffers are caller-owned inputs; this helper does not allocate either one. E9010 reads C+8 as item count and writes the supplied pose using context contents; it is an initializer, not evidence that the supplied pointer has the required capacity.

No generated direct call to22A50, EAA90 or EAB00 was found. A bounded scan of the original XBE for direct relative CALL targets also found none to these three functions. Therefore this layer ends at an exact API boundary: **the caller of22A50 (or equivalent inlined buffer attachment) must supply C,A,B**. Constructor23970 and attachment22A50 do not establish the actual allocated byte size. The input-capacity obligation is at least48*C[8] bytes for the demonstrated N-item full pose traversal, but no allocation call has yet tied that quantity to A/B.

There are embedded constructor copies: 23A30 installs the same wrapper at enclosing object+0x20; 25810 installs it at enclosing object+0x160. Those functions zero the corresponding context/buffer fields and do not allocate pose buffers. Field offsets in other unrelated objects are not evidence of buffer ownership. This follow-up deliberately stops at the attachment boundary rather than inferring an allocator from equal-looking +0x10/+0x14 fields elsewhere.

Next exact bounded question: inspect the higher-level owners of the embedded type6 wrapper (23A30/25810) and identify an inlined equivalent of22A50 that passes two allocated pose buffers plus the skeleton/context. Until such a producer is identified, preserve the allocation/context admission gap above.


## Allocation producer resolved:22A90 and26760

This supersedes the earlier unresolved allocation-owner statements **for the initialized actor path below**, while preserving the context/rig compatibility gap for arbitrary records and arbitrary raw caller outputs.

`22A90` (`recomp_0000.c`,22A90..22B96) owns the pose container Q that embeds the type6 wrapper at W=Q+0x20. The allocation/attachment chain is explicit:

1. 22A9A calls10A970 with interface identifier0x2B726C and two out-parameter addresses. On successful return22AC5 stores the first returned pointer as `C=Q[+4]` and a second result at Q+8. C is the exact context later stored in W+0xC; its field+8 supplies N.
2. 22AC5..22AF3 computes `(N+2*N)<<4`, exactly48*N bytes with native32-bit arithmetic, and calls296B0 with that size, label0x28A9EC and flags|0x400. Return A is stored at Q+0xC.
3. 22AF3..22B0E repeats48*N allocation with label0x28A9F8; return B is stored at Q+0x10.
4. 22B0E..22B29 repeats48*N allocation with label0x28AA04; return D is stored at Q+0x14. This third buffer is separate from the two blend temporaries.
5. 22B29..22B5F initializes all three using E9010(C,buffer,null_selection), and stores N at Q+0x1C.
6. 22B5F stores A at Q+0x30 (=W+0x10), B at Q+0x34 (=W+0x14), initializes them again through E9010 and at22B87 stores C at Q+0x2C (=W+0xC). This is the **inlined equivalent of22A50** that explains the absence of a direct22A50 call.

296B0 (`recomp_0001.c`,296B0..296D9) passes requested size to29500, then zero-fills exactly that size via1ECF40. 29500 handles allocator selection/alignment and returns allocated storage; it does not turn the48*N request into a smaller logical pose. The arithmetic in22A90 is unchecked32-bit arithmetic: this native producer is evidence of intended capacity, not a reason to allow unbounded externally supplied N or assume allocation success.

The real enclosing actor caller is `26760` (`recomp_0001.c`), specifically268A6..268BE: it calls22A90 with ECX=actor+0x140 and inputs obtained from actor+0x128 plus caller arguments. Therefore Q=actor+0x140 and W=actor+0x160. This exactly matches25810's embedded type6 constructor at actor+0x160. The gate2689B checks actor+0x124 and flags at+0x138; after a successful22A90 return268C2 sets mask0x1 in actor+0x138. This is an initialized path, not unconditional proof that every actor instance has those buffers.

Ownership is confirmed by22BA0: it releases Q+0x14,+0x10,+0xC through29760, clears them and initialization state.25BE5 calls22BA0 with the embedded container; the type6 wrapper itself has no independent buffer allocation/destruction responsibility.

### Exact usable capacity contract and remaining gap

For Q successfully initialized through22A90, the two W buffers have **48*N bytes =12*N floats**, where N is read from the same C+8 used by EAB50's later twelve-float item traversal. A four-float destination write fits either buffer exactly when `destination+4<=12*N` (checked arithmetic). This closes the previous allocation-size bridge for this native path.

It still does not prove semantic membership: the consumer does not establish which four-float channel starts are legal for this C, whether a particular bank record is bound to that C, or whether overlapping records are intended. It also does not cover an arbitrary external output pointer passed directly to EAB50/EDF90. Those must be tied to the matching owned Q buffer or another independently established allocation. The next bounded semantic question is10A970's lookup for identifier0x2B726C and the returned C's rig/name/channel producer; that identity was not expanded here. No build, execution, or native admission was performed.
## Skeleton lookup and channel identity

Own-image identifier0x2B726C is the string Skeleton.10A970 is a lookup wrapper, not a constructor: it calls10A8B0, which enumerates entries through10A6A0, compares resource names at10A8F0..10A919, and returns the matching payload pointer C.10A6A0 resolves section-relative values at10A762..10A77E. No rig copying or bone renumbering occurs here.

26760 stores the resource handle returned by10B430 at actor+0x128 (267BD) and passes it to22A90 at268A6. Therefore C is the Skeleton payload from the actor's selected resource handle, rather than from the animation bank. Identifying every actor variant's exact body/face asset and its motion-bank assignment remains outside this bounded chain.

E9010 establishes the row-to-pose mapping: N=C[+8]; inline row b starts C+0x10+112*b. Row's first three words become float slots12*b+0..2; row+0x10 four words become12*b+4..7; row+0x20 three words become12*b+8..10. Slot12*b+3 comes from the optional C[+0xC][b] array or constant0x289478; slot12*b+11 uses that constant. See E9170/E91E0, pose increment0x30 and row increment0x70.

Pose helper22910 writes four-component groups at buffer+48*b+0x10, and22940 copies the same group.228E0 writes the first triple at buffer+48*b;229A0 writes the last triple at buffer+48*b+0x20. Thus native group starts are12*b+0,+4,+8; destination//12 is the bone/item index and destination%12 the within-item scalar. The middle group is the four-component value consumed by type13's EA010 interpolation. First/last groups have auxiliary fourth slots that triple consumers do not overwrite.

The evaluator does not enforce aligned group starts, and this audit has not proved that every type11 may drive all three groups or type13 must use only+4. Bounds destination+4<=12*N prove capacity only; permitted type/group combinations require producer/corpus evidence.

These112-byte rows contain numeric transforms/hierarchy rather than inline bone-name strings. The existing model envelope represents names through separate __Bone exports mapping to integers;10A6A0's generic symbol mechanism supports that separation, but this bounded chain did not find the native name-to-index consumer linking those symbols with motion-track names. N, physical row order and destination units are established; named rig compatibility and moveset-to-actor binding remain unvalidated.
## Per-type destination binding audit (bounded leaf dispatch)

The native paths audited here do **not** perform a track-name to Skeleton-bone-name remap. E68E0 searches a motion name in the AnimationBank and yields a record index; E6A40/E6990 and E60B0 construct/attach that selected record. EDF90 forwards caller buffers to its children. The selected leaf then treats its serialized destination as an already-authored numeric coordinate. No call from these leaf evaluation paths resolves a __Bone name or rewrites destinations to match C's physical bone order. C+8 is not a leaf argument used for range checking in these paths.

The following are native **addressing contracts**, not blanket semantic admission policies. O is the actual output pointer, N the Skeleton count belonging to that O's verified allocation.

| Type | Proven destination source and output | Capacity condition | Group restriction actually forced by native arithmetic |
|---|---|---|---|
|11|Inline u16 d at R+0xA; ED000/ED0F3 and FC8A0 write O[d..d+3]|d+4<=12*N|None; arbitrary d is used literally. No d%12 assertion.|
|13|Inline u16 d at R+0xE; ED300/ED470 or ED41A..ED43E write four floats at O[d]|d+4<=12*N|None numerically; interpolated groups are passed to EA010 as four-component values.|
|18|Dynamic byte d from R+0xC list and inline static byte destinations; F5BD0, F5DC0/F5F60/F6054 write four floats at byte address O+48*d+16|d<N|**Forced middle group:** float offset12*d+4. Both static and animated destinations need checking.|
|19|Byte d from R+0xC list; F2580/F318C/F3222/F337C ultimately writes four floats at O+48*d+16|d<N|**Forced middle group:**12*d+4. Axis selector affects values, not bone-index remapping.|
|20|u16 float offset d in animated destination table and independent inline constant table; F14F0/F16C3/F1A23/F1C30 writes three floats at O[d]|d+3<=12*N|None; no enforced d%12. Scalar offset8 happens to address final triple in a12-float item.|
|21|u16 float offset d from animated and independent inline constant table; EFD80/EFF43/F0163/F0231 writes one float at O[d]|d+1<=12*N|None; scalar channels can numerically address any slot.|
|25|u16 d in the **external selected sample-bank** destination list, not in R; FDB40 writes four-float groups and three-float groups|d+4<=12*N or d+3<=12*N respectively|No enforced modulo. Bank selector/sample/destination ownership is an additional context contract.|

For18/19, d is a bone/item index rather than a float-slot offset; applying max(d)+4 as a float bound would be wrong. For11/13/20/21/25, d is a float-slot offset rather than a bone index; simply checking d<N would likewise be wrong.

The supplied wres005 observation (all369 type13 destinations congruent4 modulo12) is consistent with type13 driving the middle four-component Skeleton group and with18/19's forced addressing. It is not a native assertion: ED300 will also write a differently aligned d without rejecting it. This bounded audit does not establish an authored-format guarantee that all11/13 destinations must be congruent4, nor does it justify inventing a modulo policy for20/21. The native group shape and the numerical capacity inequality should be recorded separately from any conservative authored-profile restriction.

### Type25 calling contract remains distinct

FDB40 reads its second stack argument as the bank context (`Q=*(arg2+8+4*R[6])`) and writes through its third argument as output. ED000/ED300 instead read argument2 as output and argument3 as optional selection. The sample-bank method therefore cannot be admitted merely by applying ordinary scalar-leaf output checks to an EDF90 invocation. The call/wrapper layer that supplies this distinct external context, the selected bank's dimensions/destination list, and the actual output allocation must be established together. This audit proves FDB40's local addressing and does not resolve that higher-level calling-contract bridge.

### Exact remaining name/rig binding gap

Known linkage is motion token -> bank name -> bank record -> precompiled numeric destinations, separately actor resource handle -> Skeleton payload ->12*N-float pose. What remains missing is the native producer/binding edge proving that a chosen motion bank's physical bone indices agree with the selected actor Skeleton's physical row order. Neither matching N nor matching the set of __Bone names establishes that edge by itself. No native name remapper was found in the bounded chain, so an authored replacement cannot rely on evaluation to correct different bone numbering. Retain explicit animation_compatibility/output-context admission gaps until the bank-to-actor binding or a verified template identity is established.
