# UI runtime allocation identity — 2026-11-04

Bounded read-only follow-up to `fighter-grid-template-audit-2026-11-04.md`. Read the owner's generated C at102130,109F80,10B430 and their named resolver/destructor callees; resolved native constants using `scripts/string-va.py ... game/default.xbe` and its section mapping. No code changes, build, game run, external code, or asset export.

## Conclusion for the composed chooseFUI.O

For the observed **TAR and GeoPrimState runtime allocators, numeric UID is not an allocator cache key at all**. The allocators recognize the parameter name `UID` and set a caller-provided ownership byte; they do not parse or store its numeric value, search a UID table, or compare it against other objects. The loader caches each result in the particular ELF **symbol-table entry** used by relocations. Multiple relocation sites referencing that one entry share the result; a new independent symbol entry can allocate independently even if its name string is identical. A composer should still emit distinct full import names for owned clones and preserve repeated-site sharing, avoiding accidental symbol-table deduplication by its own linker/compiler.

Consequently a unique UID within the composed module is sufficient for distinguishing the clone names from its original names **provided the entire resulting typed import string is distinct**, and a new global numeric UID range is not required by either native allocator inspected here. Preserve the UID token: its presence activates cleanup ownership. TAR and GeoPrimState can deliberately use the same numeric UID because they have distinct type-qualified names; there is no numeric cross-type cache in these paths. This is a finding about these two allocators and this loader, not every conceivable runtime type.

## Exact resolution path and scope

`10B430` constructs the module wrapper, clears its owned lists, calls109F80, and normally10AC20 (`recomp_0007.c:98309–98355`).109F80 builds module-local symbol hash buckets at internal+20, chain array+420 and a definition-eligibility bitmap+424. For each original symbol, the bitmap is set only when its section index is positive and smaller than the ELF section count (`:95211–95229`); undefined imports start false. It links the internal module into the global module list rooted at3A52A8 (`:95247–95262`).

10AC20 walks relocation sections and selects the referenced symbol via `relocation.info >>8`, multiplied by16 (`:97048–97078`). A defined/already resolved symbol skips the undefined resolution path. For unresolved entries it first tries other loaded modules through10A7D0, then the module's optional callback, then registered external symbols at3A52AC, then recognizes `RUNTIME_ALLOC::` (`:97087–97244`). The search key passed to other modules is the **complete ELF symbol name**, not a numeric UID extracted from it.

10A7D0 hashes that complete name through109EB0, follows the module's collision chain, checks its original definition bitmap+424, and compares complete strings byte-for-byte through the NUL (`:96074–96212`). Therefore native defined exports can resolve globally by complete-name equality, but a formerly undefined runtime import is not turned into a globally eligible export merely by changing its section index:10AC20 does not update+424. This excludes the suggested global type+UID cache on the inspected path.

The runtime branch extracts the type-qualified part preceding the runtime delimiter and queries registry3A52C0 using117BB0 (creation function) and117BD0 (destruction function) (`:97246–97260`). That registry is a **type-to-callback registry**, not a UID-to-instance cache. Registration at10B6D7 binds `EAGL::GeoPrimState` to113F30/1141A0;10B6F0 binds `EAGL::TAR` to102130/102AD0 (`:98798–98810`). Native string VAs verified independently:2B72BC=`RUNTIME_ALLOC::`,2B7C70=`EAGL::GeoPrimState`,2B7C84=`EAGL::TAR`,2B63C4=`UID`,2B63C8=`SHAPENAME`,2B8480=`UID`.

The creator receives five stack arguments: runtime-parameter substring, module wrapper, output auxiliary/count word, output ownership byte, and original complete symbol name (`:97262–97277`). Once created, the loader writes the returned address into this ELF symbol's value (relative to wrapper+38), writes section index1, and marks symbol type5 (`:97328–97337`). Following relocations to that same symbol entry consume its stored value. There is no comparison with the value of any `UID=` parameter here.

**Practical distinction:** changing only the UID digits is enough to change an import name and prevent a composer from interning it with the original symbol, but it does not ask a native UID cache for a new instance. Conversely, merging distinct symbol entries because their strings happen to match is a compiler choice; the observed native loader itself does not deduplicate unresolved entries within the current module by that name.

## TAR and SHAPENAME

102130 parses the property list through103380. At UID-name match it only writes1 to its output ownership byte and proceeds (`recomp_0007.c:79015–79045`). No value conversion follows that branch. SHAPENAME is handled separately (`:79047ff`): it resolves the named SHAPE resource using the supplied module through10A440 and native symbol names. Thus the copied TAR must name the **new texture SHAPE name** in the composed chooseFUI module; keeping its old SHAPENAME can still bind the old texture regardless of UID.

TAR creation can allocate an array of80-byte elements based on the SHAPENAME arguments; the creator returns its auxiliary count for teardown. Its destructor102AD0 iterates that count, calls1029B0 for each80-byte element, and releases the array through allocator callback2E398C (`:80373–80421`). This ownership is attached to the module's recorded runtime allocation, not to a numeric ID or asset-wide global slot.

## GeoPrimState

113F30 always starts by allocating0x54 bytes and constructing it through113E80 (`recomp_0008.c:20700–20738`), then walks parsed properties. Its UID branch compares the four-byte name `UID` and writes1 to the output ownership byte (`:20754–20787`); it never examines the corresponding UID value. Other properties configure the allocated state.1141A0 releases that0x54-byte allocation through2E398C (`:21148–21160`). A cloned GeoPrimState import should therefore be a separate symbol with a distinct typed full name, and all sites belonging to that clone should reference that same entry.

## Cleanup owner and composition rules

When the creator reports ownership and returns nonzero,10AC20 allocates a16-byte node containing destructor, returned object, auxiliary/count value and next pointer, links it at **module-wrapper+0C** (`recomp_0007.c:97280–97326`).109F00 traverses that list, calls each destructor with object and auxiliary value, releases the node, and clears the head (`:94466–94506`). Wrapper destructor10B490 first removes/frees internal ELF registration via10AA90, then calls109F00, then releases its remaining tracking allocation (`:98372–98403`). This establishes module ownership and destruction; there is no matching numeric-UID unregister operation.

For the bounded static-grid composer:

1. Clone both runtime imports (TAR and GeoPrimState) into new ELF symbol entries; retain the original allocation strings and bindings for retail geometry.
2. Give each owned clone a distinct full typed name, conventionally by a fresh positive decimal UID token; enumerate the composed module's names to ensure no accidental alias/deduplication. No unsupported global numeric UID namespace is needed.
3. Preserve UID presence, property syntax and order; update TAR SHAPENAME to the new SHAPE texture name. Preserve the two repeated relocation sites per owned runtime symbol as one shared symbol entry.
4. Leave shared parent/shader/matrix/color imports bound as before. Keep all allocations attached to the module loader's cleanup list and unload the whole composed module through the native wrapper lifecycle.

This closes the prior report's UID-scope uncertainty for these templates. Native UI acceptance (redraw, selection, unloading/reloading, retail coexistence) remains unperformed and is not claimed.
