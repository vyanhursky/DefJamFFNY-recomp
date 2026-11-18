# Workshop sculpt normal corrections

The optional API-1 extension `caf-sculpt-normals-1` admits
`caf-face-coordinates-2` alongside the unchanged coordinates-only version 1.
Workshop stores the corresponding `ffny-face-sculpt-2` project section.

Version 2 adds `neck_normals`: 1–128 unique records per outfit. Each contains
`slot` (3 neck or 12 top), `rm` (0–15), `vertex` (0–65534), `position` (three
finite bind-space floats bounded to ±100, with height strictly between 10 and
30), and `original` / `replacement` (valid packed 11:11:10 u32 normals).
Unknown keys, duplicate targets, invalid packed values and non-finite positions
are refused. The existing head fingerprint, topology, deltas and protected seam
checks still apply. This is bounded compatibility support, not arbitrary mesh,
rig, shader or native-pointer import.

The compiler emits FCAF container version 2 only when corrections are present.
The 64-byte header uses reserved words 52/56 for normal-section offset/count;
word 60 stays zero. The normal section follows existing face rows. Its 40-byte
rows are selection/outfit/slot/rm/vertex u32, reference XYZ float32 and two packed
normal u32 words. At most 8192 rows are admitted per container. Version-1
containers retain their exact layout and remain readable; older games reject
version 2 instead of losing its data.

Before applying an outfit the adapter checks its live native coordinates and
original packed words. It resolves the original material/RM wrappers and bounded
opcode-9 vertex bindings, then copies the draw parameters and normal stream into
participant-owned storage. Render groups use the private wrapper so drawing sees
the corrections; morph channels need not contain a normal stream. Source buffers
stay unchanged. Owned metadata is detached
before native context destruction. A live reference/topology/ownership mismatch
logs a fallback and leaves original normals in place; it does not terminate the
game. Unknown project formats fail during startup admission.

Both the matching authoring tools and rebuilt game executable are required for
normal-corrected exports. The capability is discovered explicitly by Workshop.
This companion feature targets v1.2.0 and is not a published release.
