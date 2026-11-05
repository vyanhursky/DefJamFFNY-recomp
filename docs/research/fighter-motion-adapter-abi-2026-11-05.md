# Motion adapter ABI brief â€” 2026-11-05

Bounded source-independent behavioral specification derived from own generated C. No implementation/build/game run. Complements the behavior-registration and motion-table-capacity reports. **S denotes guest ESP at entry, including return address at[S].** Descriptors contain guest pointers; a host pointer is never a substitute. Integer arithmetic below is32-bit unless stated. Actor+28 is participant slot, actor+2C full32-bit core, actor+30 actor state/type: these are distinct fields.

## Entry and return ledger

| Entry | Inputs | Guest return / output | Explicitly preserved registers |
|---|---|---|---|
|1A47B0|EAX=loaded main motion chunk header|plain ret: ESP=S+4; no semantic return|ESI (other nonvolatile registers untouched) |
|1B2090|[S+4]=actor|plain ret; void; **argument slot[S+4] overwritten with stat sum**|EBX,ESI,EDI; EBP untouched |
|1B4930|[S+4]=output, [S+8]=context, [S+C]=motion ID|plain ret; void|EBX,EBP,ESI,EDI |
|1B4BA0|[S+4]=context, [S+8]=sample/action ID|plain ret; EAX=0 or1|nonvolatile registers untouched |
|1A7F30|ECX=participant*1000+local motion ID|plain ret; EAX=primary FZUI ordinal (or0 on scan exhaustion)|EBX,EBP,ESI,EDI |
|A02E0|ECX=bank manager; [S+4]=participant slot; [S+8]=bank number|**ret8: ESP=S+C**; no semantic success result|EBX,ESI,EDI,EBP |
|89310|ECX=main resource owner (normally349760)|plain ret; no semantic return|ECX,EBX,ESI,EDI; EBP untouched |

Plain-ret stack arguments remain for caller cleanup. EAX/ECX/EDX are scratch except EAX return values explicitly listed; don't rely on undocumented final scratch values of void routines. Exact replacement must not accidentally consume stack arguments. Preserve guest g_ebp/g_seh_ebp conventions around nested generated calls. Current generated direct calls do not gain interception merely from a lookup entry: use actual call-target/manual exclusion wrappers and inspect regenerated names.

## 1A47B0: registration boundary

Reads six length-prefixed shared chunks in order WAZA0/FZUI0/NAME0/WAZA1/FZUI1/NAME1, writes descriptors3B85D8..3B8644, then writes141 sixteen-byte core descriptors at3B8648..3B8F18. Core descriptor words are WPAR length, WPAR payload pointer, WWAZ length, WWAZ payload pointer. Every source advance is8+chunk payload length; no allocator/free/callee, no source count validation. The loop is fixed by destination end, not source core count.

Hook may invoke native registration unchanged for retail/shared tables, then independently publish validated sidecar rows for cores>=141. Keep backing source alive and invalidate its generation before89310 frees it. Shared registration offsets/counts/strides are fully tabled in the capacity report; don't derive new pointers from obsolete precomposition offsets.

## 1B2090: WPAR plus participant override

Resolve actor.core descriptor+4 WPAR payload and call1A3AD0 with stack arguments(destination=actor+AE4,source=payload). Decoder clears/writes232 bytes (AE4..BCB), advances shared packed-bit cursor globals3BE104/3BE108, and uses existing raw WPAR conversion rules; it does not allocate a core-count-sized array.

Then read seven dwords at3B9128+actor.participant*1C. Compute their sum modulo2^32 and write that sum into original argument slot[S+4] (`recomp_0012.c:57845`, after three nonvolatile pushes). If sum!=0, copy seven dwords in order to actor+B34..B4C; if sum==0, leave the just-decoded values there unchanged. Do not treat this auxiliary array as core-indexed or grow it for custom cores. The unusual argument-slot overwrite is observable native behavior, even though ordinary callers discard that stack argument.

## 1B4930: populate motion state

Output and context are **independent pointers**, even when retail caller passes related actors. First set output+FAC=output, output+FB0=context, output+F50=motionID. Call1C60D0(output), store its EAX at output+F58. This helper is pure reads: output+30 values45h/46h/48h return motionID-31h;47h returns motionID-37h;4Ah/4Bh return motionID-1Fh; all others return0. It performs no allocation or state writes.

Clear output bytesF68,F69,F6A and dwordFB4. Select one branch:

- IDs31..34 decimal or38..41 decimal: slot=id-31 orid-38. Set F54=FFFFFFFF,1020=id,F5C=id. Resolve secondary WAZA row `(output[BB8+slot*4]+8Ehex)` using stride3B8614/base3B8624, decode via1A3630 into output+F6C. Read context.core WWAZ byte at action*6+1; bit80 sets output+F68.
- Other IDs<10000: obtain context.core WWAZ word0 at action*6; lowFFF is primary WAZA ordinal. Store ordinal to output+F54,+1020,+F5C; word0 bit8000 sets F68. Decode primary row through stride3B85DC/base3B85EC into output+F6C. Set FB4 to unsigned WWAZ word1 plus **output.participant*1000**. This last multiplier is output+28, not context+28 (`0012:64495â€“64510`), correcting earlier prose that conflated them.
- IDs>=10000: set F54=FFFFFFFF,1020=id,F5C=id; decode secondary row(id-10000) into F6C. Decoded byte output+F71!=0 sets F68.

Final common effects: sign-extend decoded first16-bit word at output+F6C into output+3C0. Set bit0 of output byte926 for the two special ID ranges; clear bit0 otherwise, preserving other bits.1A3630 clears/writes64 decoded bytes and advances shared bit cursors; it does not allocate. Return void. Do not replace the1C60D0 prelude with guessed constants, lose F69/F6A clearing, or use context participant for FB4.

Admission bounds for custom branch: nonnegative motion ID, valid130-row action for WWAZ branches, actual WAZA count for normalized/special ordinal, checked pointer arithmetic. ExactFFFF absent action must be rejected before this decoder branch; native code masks it without checking and would select4095. Preserve high flags separately from ordinal; primary linked WAZA fields remain12 bits.

## 1B4BA0: presence query

If sample/action ID==0 return EAX0 **without dereferencing context/core**. Otherwise resolve context.core WWAZ payload, read u16 at6*sampleID and return1 iff word!=FFFF. No actor/global mutation, allocator, decoder, or other callee. Validate nonzero custom sample below130 before dereferencing. This checks whole word equality, not low12 bits.

## 1A7F30: local ID to primary FZUI

Split valid nonnegative ECX into participant=ECX/1000, local=ECX%1000. The participant record is3B92E0+participant*12E8; resolve its full32-bit core at+2C. Preserve the existing four participant records; custom core number does not encode participant number.

Initialize previous action=1, lower boundary=0. Scan candidates2..125:2..124 use unsigned WWAZ word1 as boundary,125 uses synthetic1000 without reading that row's boundary. If local<boundary, select previous action and delta=local-lower. Otherwise, a greater boundary replaces both lower and previous; an equal boundary replaces previous only when candidate WWAZ word0!=FFFF. Continue by six-byte action stride. If exhausted, return0.

Normal selected result is previous action's unsigned word2+delta. If delta>=2 and participant actor+30==41h, substitute `signed16(actor+FA6) - (((actor.byte91A &4)|8)>>2) +delta`; preserve this exact2/3 correction. No callee, allocation, actor writes or global writes. Validate final result against FZUI0 count at the contextual boundary1A85A0; the scan result is not repartitioned when>=10000. Valid input requires participant0..3/local0..999 and sidecar WWAZ envelope; do not reinterpret ECX as core*1000 or elapsed time.

## A02E0: bank registration/lifetime

Manager is normally main+488. Per-participant record is manager+slot*2C; slot is0..3, **not core ordinal**.87090 passes bank number=core+1 for populated core IDs, retaining32-bit identity. A02E0 formats paths, loads MNL source at record+8, establishes resource context at+1C/+20, uses MNL first dword N as item count, allocates N*16 at+C, parses names and resolves resource handles viaE68E0. Manager flag4 enables another N*16 array at+10. **Flags1 and2 additionally allocate N*12 arrays at+14 and+18**, filled throughA0140. Record+4 receives N. It removes its temporary ELF registration via10AA90, releases temporary source through294D0 and closes its temporary handle via1E3D10 before returning. These operations have resource-loader/allocator side effects; there is no boolean failure contract to imitate by a dummy EAX value.

For custom use, retain native body whenever merely changing validated input resource resolution suffices. If replacing, preserve every enabled array/context/source ownership and native cleanup9FE50(manager), which loops four slot records. Validate N*16/N*12 overflow, actual MNL rows, bounded names/resource existence and all guest allocations first. New core does not require a fifth bank record. A02E0 is **ret8**, so don't also caller-pop its two arguments.

## 89310: invalidate then delegate full teardown

This is broad main-owner teardown, not a tiny descriptor free. It releases participant-related/resource state through many callees; when owner flags include200h it calls9FE50(owner+488). At894DE it obtains owner+0 source;294D0 releases it at return address894E6, and it clears owner+0 before894FA. The borrowed shared/core descriptors are not cleared, so they can retain stale guest addresses afterward. Its remaining teardown includes owner resource contexts/handles and UI/runtime cleanup; don't replace this body just to add a sidecar free.

Adapter strategy: capture owner ECX and invalidate the matching generation **before** calling native teardown. Delegate native body unchanged, preserving its side effects and ECX-restoring ABI. Free custom guest allocations only when no live actor/source readers remain; process-lifetime retention is defensible until quiescence is demonstrated. Never free the composed native source separately and then let89310 free it again.

## Retail invariants and implementation acceptance boundary

Keep cores0..140 on native branches, notably0/1 special checks in1AACA0 and1AAD00; actor+30==41h scan correction is a different state-based rule. Preserve actor+28 participant slot and32-bit actor+2C custom ID>=141, including>255. Do not borrow retail descriptor slots, overwrite adjacent3B8F18, swap a retail row temporarily, or lose native shared frame bases when composing the file.

Recommended semantic checks cover all motion branch families, absent action, sample0 short circuit, distinct output/context participants, stat sum wrap/zero and argument-slot overwrite, four slot bank allocation flags, teardown invalidation/reload, and native0/1 behavior. This brief specifies candidate adapter contracts; it does not certify runtime acceptance or all transitive callee internals.


## Follow-up omission audit: additional scalar consumer (2026-11-05)

**The four descriptor readers are the complete bounded direct descriptor-reference set, but they are not sufficient by themselves for arbitrary custom core IDs. Add1B2C60 to the adapter inventory.** This function walks the four participant core fields beginning3B930C in12E8 strides. Each occupied participant (preceding+28 slot field!=FFFFFFFF) indexes a separate static float table as `2F0088 + core*4`, with no141/255 bound. Exact read blocks are guest1B2C7D (`recomp_0012.c:60165â€“60167`),1B2D2D (`:60271â€“60273`) and1B2DF0 (`:60386â€“60388`). These scalar values drive branch classification and diagnostics; every inspected per-participant444E0 call passes literal1.0 (see the detailed contract below); this is not a descriptor access that the four sidecar readers automatically redirect. It is directly called at1A2EEF, return address1A2EF4 (`:20014â€“20015`), after participant setup, so it must not be dismissed as unreachable debug-only code merely because it also prints diagnostics.

Own-image bounded inspection finds first141 scalar entries in {approximately0.95,1.0,1.05}; index141 reads zero at2F02BC, index142 reads100.0 at2F02C0.2F02C0 is independently used as the base of a different five-element parameter array elsewhere (`0012:25695`, initialization/reference at`:68653`). Thus permitting a custom ID142 would silently read unrelated parameter data, even before ID255; the zero at141 is not evidence of a reserved extension entry. No direct writer or capacity count for2F0088 was found. A custom scalar must be supplied by explicit sidecar metadata/policy and resolved in1B2C60 while retaining the native mixed-participant comparison/application logic. A neutral1.0 is a possible product policy, not a decoded property of a new WPAR row. Do not temporarily replace actor core IDs or overwrite adjacent static floats.

The whole-generated literal census of descriptor interval3B8648..3B8F18 (including field addresses and initializer computed+0/+4/+8/+C writes) reconfirms only1A47B0 and readers1A7F30/1B2090/1B4930/1B4BA0;3B8F18 itself is adjacent state read by1BAA00. No additional descriptor reader was found. Direct participant-core absolute references also include1A6E40 (3B930C sentinel comparison, not table indexing), known0/1-special1AACA0, and1B2C60 above. Within the inspected motion/actor generated module, the tempting1B1CA0 object+2C indexing at1B2039 derives its object from a separate96-byte configuration subrecord selected at`:57279â€“57286`, not actor+2C; it is not evidence of another core*24 array.1AC490+2C is consumed as a mask in its object path, likewise not proven participant core provenance. These were not conflated with actor core merely because the offset matches.

No further8-bit narrowing or141/255-indexed actor-core array was established in this bounded pass. This is **not** exhaustive alias/dataflow proof for every subsystem: arbitrary computed pointers and unrelated structures with+2C fields remain outside the confirmation. The concrete newly required omission is1B2C60's scalar lookup. Descriptor/bank/initializer/teardown hooks plus this scalar path form the revised candidate inventory; live acceptance remains required.


### 1B2C60 replacement contract and donor scalar

Own generated extent is guest1B2C60..1B2E76 (exclusive end1B2E77,535 bytes). This is small enough for a complete source-independent implementation with a scalar resolver; its535 guest bytes expand into about360 lines of generated flag/FPU bookkeeping. There is **no downstream callee boundary that can prevent the three earlier unchecked scalar-table reads**. Preserve actor.core and resolve custom scalar from the declared retail donor core0..140. Do not alter actor IDs or retail memory even briefly.

ABI: no arguments, plain ret (ESP=S+4), no semantic return. Saves/restores EBP,EBX,ESI,EDI; ECX/EAX/EDX are scratch (ECX's initial push is scratch space discarded by frame restoration, not a restored argument). It aligns its temporary stack to8, uses x87 scratch without an intended floating return, and loops only occupied participants (actor+28!=FFFFFFFF). Scalar reads are float32, compared using the existing x87 precision/ordered-comparison behavior. Input from a valid donor is finite.

First pass independently counts scalar values within **strict absolute difference<epsilon**, epsilon=float32 at292378 (approximately0.01), of H=float32 at2C9348 (approximately1.05), N=float32 at289478 (1.0), L=float32 at2A2C38 (approximately0.95). These are three independent tests; don't reinterpret epsilon as equality or change to<=. With validated donor scalars they form the observed three classes. The own-image range2F0088..2F02BB contains141 values; next word2F02BC iszero and following2F02C0 is another table's100.0. This identifies a usable donor domain, not a symbol-proven array allocation length.

Branch selection after counts:

| Counts | Per-slot diagnostic scalar |
|---|---|
|H>0,N==0,L>0|adjusted: start from donor scalar; if nearL set exact float32 0.95 literal3F733333; then if the resulting value is nearH set exact1.0; use format2C9308 |
|H>0,N>0; or H==0,N>0,L>0; or all three counts0|raw donor scalar; format2C9324 |
|remaining cases (only one observed class populated)|constant double1.0 from2A7338; format2C92E8 |

In **every branch**, for each occupied slot p, call444E0 with two caller-cleaned arguments(p,float1.0), then call11520 with diagnostic format, one-based slot p+1 and promoted double scalar as above. The generated caller reuses its two setter argument stack words as the variadic double's storage; an independent implementation can use balanced normal guest arguments instead of reproducing that scratch-layout trick.444E0 resolves slot through441C0, then calls9E410 with literal1.0;9E410 selects an embedded rendering object according to mask1 (bit0) at object+ABB4 and passes three copies of the scalar to24C20. Thus the observed applied scale is **always1.0**, even where the log reports raw0.95/1.05. Do not silently start applying the diagnostic donor scalar as a gameplay/render change.11520 is a diagnostic callee; its implementation was not recovered in this generated tree.

Retail-preserving implementation choice: delegate wholly retail participant sets to the original body; for mixed/custom sets run the same classification/setter/diagnostic algorithm with a resolver returning native2F0088[core] for retail or2F0088[donorCore] for custom. This avoids OOB and retains mixed-participant behavior without modifying global actor state. A reduced custom path that simply applies1.0 and omits diagnostics could preserve the observed setter effect, but it would intentionally drop native log/classification behavior; the full535-byte semantic replacement is the cleaner exact contract.
