# Fighter animation bank native record audit — 2026-11-04

Scope: bounded static reading of the user's own XBE and generated C. No source changes, builds, game runs, external code, or asset publication. Addresses below are guest VAs. Generated C is ignored evidence, not a deliverable.

## Result

The MNL linkage is now concrete: a token `N` selects bank names `N_t` and `N_s`. Crucially, `sub_000E68E0` returns an **integer index**, or signed `-1`, not a record pointer. `A02E0` stores those indices in its 16-byte motion-name rows. A bank lookup resolves its record through a separate pointer table. This establishes a typed structural validation route, but does not establish complete curve semantics or runtime readiness.

## MNL and loader path

- XBE strings read through section VA-to-file mapping: `0x2A5D70 = %s_t`, `0x2A5D78 = %s_s`, `0x2A5E30 = .`; all are NUL terminated.
- `A03ED..A040B`: MNL pointer is slot `+8`; first u32 is name count. Slot `+0x28/+0x2C` start at MNL+8. Allocation is count times 16.
- `A0410..A0459`: find the next period with `200DA0`, copy preceding bytes to a zeroed 256-byte temporary through `2010A0`, advance both cursors past the period. Native copying here has no visible explicit 255-byte bound; an offline parser must impose its own token budget.
- `A0459..A04BF`: format token with `%s_t`, binary search bank at slot+0x20, store result row+4; repeat `%s_s`, store row+8; row+0xC becomes -1. Row+0 is not initialized by this particular loop, so do not invent its meaning.
- `A04BF..A04E2`: increment row by 0x10 until MNL count. This loop does not require either lookup to succeed.
- `A03BC..A03D8`: `217B0` receiver is slot+0x1C, arguments ORD pointer, ORD size, ORL pointer. `217B0` creates a 0x30-byte loader through `10B430` and resolves resource class string at `0x2B7254`, verified `AnimationBank`, through `10A970`. It stores loader at receiver+0 and resolved bank at receiver+4 (slot+0x20). This separates the loader wrapper from the bank root.

## Bank root: proven minimum layout

These are post-relocation guest pointers; an offline implementation must follow `fighter_elf.Model.pointers` and preserve section-relative offsets rather than treat the serialized word as a host address.

| Root offset | Type / role | Direct evidence |
|---|---|---|
| +0x00 | unknown u32 | Not assigned a meaning in this audit |
| +0x04 | signed/nonnegative count of named entries | E6850, E6870..E6890 return it; E68E0 searches indices 0..count-1 |
| +0x08 | unknown u32 | No interpretation established |
| +0x0C | unknown u32 | No interpretation established |
| +0x10 | pointer to count-sized array of record pointers | E6860 returns array[index]; E6960/E6A40 dereference it |
| +0x14 | pointer to count-sized array of C-string pointers | E68E0 compares array[mid] with requested name |

Minimum root extent is 0x18. `E68E0` performs bytewise case-sensitive lexicographic binary search, so names must be in matching sorted order. Equal returns midpoint; failure returns 0xFFFFFFFF. The function checks search bounds, but not the string/pointer-array extents. `E6860` and `E6A40` have no index bounds check.

`E6960(root,index)` reads u16 type at record+0 and returns u32 record+4 only for types 15, 22, 23; otherwise zero. `E6A40` obtains record pointer and passes it to `E6990`. The latter uses record type 15..25 to choose wrapper construction, including embedded wrappers at record-0x18 or record-0x14 for particular types. Thus a universal assumption that every pointed-to record is an independent fixed-size blob would be wrong.

## Type 15 record and curve consumers

The default manager vtable at `0x2B59D4` was read from the XBE. Slot +0x24 is `E60B0` (construct from serialized record); slot +0x28 is `E6220` (construct by type). `E6220` type 15 calls `E5C80`, establishing a wrapper with vtable `0x2B5850`, wrapper+8=15, wrapper+0x10=0. Its vtable +0x48 is `EDEC0`, which attaches the serialized record at wrapper+0xC and clears the cached child-wrapper array.

| Type 15 serialized offset | Proven use |
|---|---|
| +0x00 u16 | type discriminator |
| +0x02 u16 | returned by E5CC0 |
| +0x04 u32 | returned by EE3F0; precise semantic name unresolved |
| +0x08 u16 | child/curve record count |
| +0x0A u16 | converted to float by E5CD0; optionally divided by wrapper byte+0x15 (time scaling) |
| +0x0C | inline array of child record pointers, count entries |

The minimum serialized extent is `0x0C + 4*count`; arithmetic and every child pointer need independent bounds validation. `EE400` allocates count*4 bytes for cached child wrappers, reads the inline pointers in reverse order, and invokes manager vtable+0x24 (`E60B0`) for each child. `E60B0` reads each child's u16 type. Types 22/23 use an embedded wrapper at child-0x18; type25 uses child-0x14; others dispatch to `E6220`, then invoke resulting wrapper vtable+0x48 to attach the child record. Embedded-prefix ranges therefore also need validation for those types.

Evaluation routes through the cached children (count again from serialized+8): EDF90 invokes child vtable+0x18; EDF10 +0x24; EE000 +0x30; EE070 +0x28; EE0D0 +0x20; EE130 +0x2C; EE210 +0x1C; EE3A0 +0x44; EE450 +0x0C. Several routes multiply incoming time by wrapper byte+0x15 when byte+0x14 enables scaling. EE190 uses child+0x34 and can divide a returned time by the same scale. EDE70 releases children and their array. These are curve/child consumers, not proof of channel names, bone mappings, interpolation, or event semantics.

`E6220` dispatches a broad type family: 0..21 and24 have constructors; 22/23 bypass normal construction through embedded wrappers;25 is special-cased in E60B0. Relevant constructors for deeper decoding include E51E0(type0), E5260(1), E5420(2), E5340(24), E5C20(14), E5C80(15), E5D40(16), F6D10(17), F4880(18), F2220(19), F06B0(20), EF320(21). This audit does not assign human names or safe lengths to those child types.

## Bounded acceptance implications and remaining uncertainty

A structural successor to the current envelope-only adapter can validate the bank root minimum extent; count-sized relocation-backed name/record arrays; bounded terminated names in sorted order; exact token `_t`/`_s` lookup (including explicit handling of native -1); and type15 inline child-pointer ranges. It must not silently promote these checks to curve correctness.

Still unproven: meanings of root+0/+8/+0xC; record+2/+4/+0xA semantic labels; the relationship of `_t` versus `_s` to translation/rotation/skeleton; all type-specific child lengths and channel encodings; event linkage; malformed/cyclic child graphs; actual corpus distribution of record types. No ORD/ORL corpus enumeration was performed here. In particular, a name ending `_t` must not be labeled translation solely from its suffix.

Current `setup/fighter_animation.py` correctly leaves `animation_records_validated`, `motion_name_links_validated`, `event_links_validated`, and `runtime_ready` false. The findings justify a next typed structural parser, not flipping those flags without implementation and corpus checks.

Evidence locations: `src/recomp/gen/recomp_0004.c` A02E0 (notably lines 88570..88745); `recomp_0000.c` 217B0 and21890; `recomp_0007.c` E60B0/E6220, E6850..E6A56, E5C80/E5CC0/E5CD0, EDEC0, EDF10..EE4BE. Function addresses are stable anchors when generated line numbers change. To search string constants, use unpadded forms (`0x2A5D70`); function names use padded forms (`sub_000E68E0`).

## Follow-up: serialized types 13 and 25

Static follow-up requested after the main agent's retail wres001 traversal found types 13,15,18,19,20,21,25. That traversal/count is supplied context, not independently reproduced in this subsection.

### Type 13: compressed four-scalar channel groups

`E6220` type13 constructs `E56D0` (vtable `0x2B5670`). Vtable methods relevant to serialized reads are EB850 (+2 metadata), EC7F0 (attach), ECBB0 -> ED300 (evaluation), ED590 (duration), ECDF0 (output coverage); the filtered evaluation route is ECBD0. These read one serialized record `R`:

- u16 R+0 type13, u16 R+2 metadata; pointer D=R+4; pointer T=R+8; u16 K=R+0xC; inline destination u16 indices at R+0xE.
- D begins with u16 S (scalar count), u8 B at D+2 (compression bits). FC3F0 supports B=4,8,16. D+3 is not interpreted by the audited decoder.
- D+4 contains S triples of float32, stride12: additive offset at +0, multiplier at +4, base value at +8. FC3F0 initializes the scalar output from the base values and accumulates quantized deltas with multiplier and offset. The packed sample region follows at D+4+12*S, using S components per delta step. Sixteen-bit and byte encodings have strides 2*S and S; nibble encoding rounds `(S+1)/2` per step, with special handling for odd scalar offsets.
- T is a u16 time array. EC8C0 interval search, ED300 interpolation and ED590 duration read it. Duration reads T+2*K-4 and adds1; evaluation reads T[interval] only on an interpolated segment; the final interval clamps using T[K-2]. The implicit initial key precedes the first transition time. A safe structural shape requires K>=2 and at least K-1 u16 transition-time entries, with strictly increasing time values to avoid zero interpolation divisors. Native does not validate these constraints.
- The inline destination array has S/4 entries for the ordinary four-scalar group route; ED300 advances the scalar loop by4 and destination cursor by2; ECDF0 explicitly uses S>>2. For a conservative supported profile require S>0 and S%4==0, minimum record extent `0xE+2*(S/4)`. Destination values are float-slot offsets into caller output; they are not byte offsets. Each ordinary group writes four floats, so destination+3 must fit the caller's output. ECDF0 derives affected bitset items by dividing destination by12. That relationship alone does not establish a trusted bone limit.

The descriptor's fixed minimum is `4+12*S`, with all triples finite as an offline acceptance policy. The complete packed extent depends on FC3F0's key-index delta-step calls. ED300 requests current key index and next key index; safe conservative storage is `(K-1)*ceil(S*B/8)` after the triples (for B=4 with S divisible by4 this is exact whole-byte stride). The distinction between key count and delta count matters: the base pose is already in the triples. The audited code does not store a payload length alongside the pointer; parser must bound the computed range against .data and avoid trusting a neighboring symbol as an implicit size.

EC7F0 allocates S*4 bytes of runtime scalar cache, records R at wrapper+0xC, resets wrapper+0x10=-1. ECBD0 constructs an optional selected-channel cache, reads the same inline destinations and descriptor, and invokes FC3F0 on selected four-scalar groups. Thus validating only descriptor header/time arrays is insufficient; base/scale/offset floats, packed deltas, destination ranges and caller output shape remain separate checks.

No native checks for finite triples, S divisibility, increasing times, or destination range were found in these routes. Those are safety constraints for an offline supported profile, not claimed native assertions. Full numerical reproduction of FC3F0 was not implemented in this read-only task.

### Type 25: external sample-bank selector with embedded mutable wrapper

`FDB00` constructs type25 wrapper: vtable `0x2B6160`, wrapper+8=25, u16 wrapper+0x10=0. The serialized record `R` minimum is 0x10:

| Offset | Proven read |
|---|---|
| +0 u16 | type25, consumed by manager dispatch |
| +2 u16 | metadata returned by FE240 |
| +4 u16 | K, key count in FDB40 |
| +6 u8 | selector of a bank from caller evaluation context |
| +7 u8 | no audited semantic use |
| +8 pointer | byte sample-index array, K bytes |
| +0xC pointer | u16 time array, K entries |

FDB40 clamps before the first and after the last key, otherwise searches times starting from wrapper's cached u16 key index, optionally reads next time/index, and interpolates. Require K>=1, bounded arrays, strictly increasing times for interpolated pairs. K=0 is unsafe because the first time is read before the last-index arithmetic. No serialized float32 payload is read directly by this type.

The evaluation's second input supplies an external context C. It selects bank Q=`*(C+8+4*R[6])`, then reads sample float-array pointer Q+0, u16 destination-index-array pointer Q+4, u8 channel counts Q+9 and Q+0xA. The selected byte sample index chooses one fixed-stride frame with `(Q[9]+Q[10])*16` bytes. First Q[9] groups are four-float groups (EA010 interpolation); remaining Q[10] groups use three floats from sixteen-byte sample slots. Destination indices select output float slots. Both selected and next sample frames are read when interpolating; direct copy uses one frame. None of these external pointers/counts is bounded by the type25 record itself, so a bank-local parser cannot establish its full read/write safety or finite sample values. The caller context, sample count/array size, channel destinations and output size must be supplied and checked separately.

Prefix: E60B0 for type25 uses W=R-0x14, reads `vtable=*(W)`, and **immediately invokes `*(vtable+0x48)`** with ECX=W and argument R. It does not run FDB00 or seed a zero vtable first. The known type25 vtable+0x48 is FDB20. FDB20 writes pointer R into W+0xC (R-8) and resets u16 W+0x10 (R-4) to0. FDB40 later mutates that u16 key cache. Thus at native dispatch time the prefix is a live object containing native dispatch state; the record-8 pointer and record-4 cache are mutable. Zero prefix bytes cannot be treated as sufficient native-ready seeds without identifying a prior loader fixup/constructor that installs the vtable. The subsequent bounded fixup read below resolves who initializes this prefix. A data-only offline parser should report prefix compatibility separately and must never execute that serialized dispatch pointer.


### Type25 prefix fixup resolved

Correction to the initial interpretation: E68A0 is the bank **initialization** callback. E66F0 registers E68A0/E68D0 for AnimationBank through 117AC0. E68A0 loops root+0x10 record pointers, invokes manager vtable+0x30 (E6110), and E6110 maps serialized type25 to EE890. The mapping was checked directly against the XBE switch bytes at E6180 (entry25=5). EE890 constructs a temporary FDB00 object on the stack, copies **only its vtable word** to R-0x14, then destroys the temporary with EB810. This supplies native vtable 0x2B6160 before E60B0 attaches the record. E68D0 is a no-op. E6110 also routes type15 to EE260, a recursive initializer, so child type25 records are reached through parent initialization.

Independently reproduced on retail wres001: first type25 at .data-relative 0xC6784 has prefix words `(0,0,25,0,0)` and no pointer relocations in the twenty prefix bytes. Therefore the zero dispatch word is an expected serialized seed, **not an unsupported native-pointer requirement**. The offline supported profile can require this exact non-executable seed shape for observed type25 records, while native initialization installs its own dispatch pointer. Never serialize a live guest/host vtable back into a distributable asset.

Also independently read first type13 at 0xC6668: descriptor at 0xC65AC, header scalar-count4, bit-width8, reserved0; key-count23. These are one-record observations, not corpus-wide constraints. For type13, the time list models K-1 transitions between K poses (duration uses transition K-2). The recommended minimum times range above reflects this; requiring K entries would consume adjacent data unnecessarily.
