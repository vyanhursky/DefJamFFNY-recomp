# Workshop sculpt normal corrections

The optional API-1 extension `caf-sculpt-normals-1` admits
`caf-face-coordinates-2` alongside the unchanged coordinates-only version 1.
Workshop stores the corresponding `ffny-face-sculpt-2` project section.

Version 2 adds `neck_normals`: 1–128 unique records per outfit
(`setup/fighter_neck_normals.py`). Each contains `slot` (3 neck or 12 top), `rm`
(0–15), `vertex` (0–1023), `position` (three finite bind-space floats with
|x| and |z| ≤ 1.1 and height 17.5–19.5, the neck boundary) and `original` /
`replacement` (packed 11:11:10 u32 normals). A replacement may turn the normal by
at most 35°. Unknown keys, duplicate targets, degenerate packed values and
positions outside the neck boundary are refused. The existing head fingerprint,
topology, deltas and protected seam checks still apply. This is bounded
compatibility support, not arbitrary mesh, rig, shader or native-pointer import.

The compiler emits FCAF container version 2 only when corrections are present.
Header word 48 is the total size including the normal section; words 52, 56 and
60 hold the section's offset, group count and byte count. The section follows the
existing face rows as one fixed-size group per corrected outfit: selection key,
outfit index and record count (three u32), then 128 slots of 32 bytes (slot, rm,
vertex u32; reference XYZ float32; original and replacement packed u32), unused
slots zero. Version-1 containers keep their exact layout and stay readable; older
games reject version 2 instead of losing its data.

The game (`src/patches/fighter_caf_face.c`) validates every group against an
admitted face row at start-up. When an outfit is applied it checks the live
neck/top render programs (bounded opcode-9 position and packed-normal streams),
copies the parameters and normal stream into a participant-owned 64 KiB arena and
points that part's render wrapper at the copy, so drawing sees the corrections
while the original buffers stay unchanged. The D3D11 vertex-stream path checks
the private stream's ownership and hash before each draw; a mismatch skips that
upload, restores the original wrapper and quarantines the arena. A live
layout/ownership mismatch logs a fallback and keeps the original normals; it does
not stop the game. Unknown project formats fail during start-up admission.

Both the matching authoring tools and the rebuilt game are required for
normal-corrected exports. Workshop discovers the capability explicitly. Shipped in
v1.2.0 (PR #282; it replaced the first implementation from PR #274, whose
container and runtime were not compatible with it).
