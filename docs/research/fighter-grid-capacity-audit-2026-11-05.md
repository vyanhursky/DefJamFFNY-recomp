# APT model normalization capacity — 2026-11-05

Bounded read-only audit of original generated APT loader/normalization code. No implementation, build or run. This report extends the grid template audit.

## Proven512 hazard

`sub_0017F080` (`recomp_0011.c55465`) clears ECX dwords at EBX, enumerates all `__Model` exports via0010A970, converts each root+B4 model-name string to an integer, and writes `table[integer]=model` at0017F0D2. It does **not** check index against the supplied clear count. Generated direct-call search of all `src/recomp/gen/*.c` finds exactly one caller: **001813E0 ->0017F080 at00181430**. The dispatch-table entry is not another caller. No other absolute function-pointer registration of0017F080 was established.

001813E0 reservesA8C stack bytes and passes ECX=200(hex)=512 with EBX pointing to its stack table. It iterates that table0..511 at00181530–001815B8. Thus a model ID512 or greater does not merely skip normalization: **0017F080 writes beyond the allocated512-pointer table**, corrupting neighboring stack state. A compiler guard must bound every existing and added numeric model ID below512, not only image count. Source1120-byte drawable cloning does not remove this native limit.

## Minimal replacement strategy

Replace the **normalization callback001813E0**, preserving its ABI/registration `[3B1E40]`, rather than enlarging a hard-coded stack allocation or globally changing the model enumerator.

The original already enumerates the required module models through0010A970 with `__Model` category and a local iteration cursor;0017EFF0 and0017F080 demonstrate this API. The replacement can enumerate models directly and apply the original per-model normalization sequence without constructing a model-ID-indexed table. Preserve image-specific formatted names (`ScaleMatrix::<APT Image character index>::TextureMatrix`), reciprocal texture extent calculation, matching matrix lookup00112CC0/00112D30, transformation001EA920 and model update00112C90. Keep enumeration bounded by a reviewed module export budget and abort on malformed/null returned roots or nonprogress, rather than inventing a new native ID limit. Enumeration order should not affect independent per-model updates, but duplicate model-pointer exports must be rejected/deduplicated or explicitly audited to avoid repeat normalization.

This removes both the unsafe indexing and unnecessary512-model scan per image; it does not require a general native model loader. Keep the existing guard until the adapter is implemented and accepted on a sparse model ID above511 plus large installed roster and removal/reload. Preserve original raster dimensions/normalization arithmetic exactly; do not compensate by pre-normalizing source vertices while leaving native normalization active.

## Image identity and related bounded structures

The finalization Image/type7 branch0015F9C3 passes the **APT character-table index**, Image+8 raster and context into the normalization callback. The image callback0017F2F0 likewise compares directory numeric identity to requested character index. Therefore generated numeric image ID must equal its APT Image character index; keep this explicit assertion. This constraint is independent of512 model indexing. Original image lookup loops actual XSH count at0017F338–0017F35D; no fixed512 or sorted-directory requirement occurs there. Shape lookup0017EFF0 enumerates actual module exports; sprite frame fixup0017DD70 loops actual frame count. No additional fixed model/image-ID-indexed array was found in these inspected paths.

There are adjacent **256-entry structures**, but they must not be mislabeled as a256-fighter cap:

-001811F0 scans `[3B37A0]` in110(hex)-byte records, at most100(hex)=256, testing each record's leading state.001819D0 similarly scans this pool in groups of four at001819F0–00181A0C, terminating at256. This is a movie/context resource-state pool, not the per-module APT character or texture directory. Its lifetime/count should be checked if a future design introduces hundreds of external movie loads; static additional frames do not directly allocate one pool record per fighter.
-00180F10 initializes a counter plus256 dword slots toFFFFFFFF;00180F50 increments its index and appends without a demonstrated bounds check.00180F60 searches/removes entries and explicitly compares removal index toFF. No caller/type relationship to custom grid image/model registration was established in this bounded read, so this is an adjacent fixed structure requiring a targeted caller audit **only if the new adapter uses it**, not a basis for changing capacity now.

The inspected256-byte stack reservations around0017F100/0017F390 and adjacent helpers are filename/name work buffers, not evidence for256 models. Generic render queue/view stacks near00181640 are outside the requested model/image registration capacity and were not treated as roster limits.

The concrete smallest safe change is direct model enumeration inside the image-normalization callback, with the compiler's existing character/image ownership constraints preserved. This is an implementation proposal from the exact inspected call chain, not accepted runtime behavior.

## Implementation follow-up (primary agent)

`fighter_ui.c` now enumerates models through the original module API, validates
numeric identities, rejects duplicates and sorts by numeric ID to preserve
the original visitation order. It feeds dense batches of at most512 pointers
to the unchanged1813E0 body through a scoped17F080 wrapper. The indices in that
temporary table do not escape1813E0; image/model names remain unchanged. This
retains the native reciprocal-dimension and matrix arithmetic rather than
reimplementing it. The enumeration budget is16384 models; four-digit compiled
names are a separate constraint. The host array is released after the callback,
and ordinary runs bypass both adapters. Nested state is thread-local and scoped.

Seven compiled synthetic tests pass: empty modules,511/512/513 boundaries,
1100 models, sparse IDs above511, ascending once-only visitation, scratch-buffer
canaries, restored callback arguments/registers, inactive retail calls and
enumeration exhaustion. Re-lift verification confirms1813E0_gen calls the real
17F080 wrapper. Full MSVC unit gate:1393 passed,27 skipped,1 deselected.

A local native test is running with402 generated portrait resources (two real
fighters' artwork plus400 unused diagnostic templates),600 module models,
and reversed allocation so the visible custom thumbnails use IDs above1200.
The log reports two normalization batches, the four-player capture displays
correct portraits, and all four custom selections reached combat. Final run
and restoration acceptance is pending; this is not a400-fighter roster test.

Final010829 result: six combat assertions passed, four native identities verified,
124 frame reports78/120/121, no faults, one save generation and byte-identical
restoration. This accepts the600-model/sparse-ID control; it does not establish
large-roster lifecycle or release performance bounds.
