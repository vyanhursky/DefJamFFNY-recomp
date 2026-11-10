# Workshop CAF facial authoring

The owner requested original facial presets, RPG-style proportions and
prioritized imported face geometry for standalone custom fighters. This work
extends the Workshop custom meshes/modpack roadmap on the CAF atlas/outfit/UI
feature stack. No original save, game asset, generated guest code or geometry
is part of this source change. The existing packaged Tupac playtest is unchanged.

## Original contract

CAF values 5–11 select face, eyes, eye color, eyebrows, nose, lips and ears;
eyebrow palette is color slot 8. Original shape ordinals are 1–8; ear 4 maps to
2 during original assembly. Default eyes/nose/lips/ears use 1. Eye color and
eyebrows are texture choices. Internal `9999` texture resources are excluded
from Workshop's retail menu. Story saves retain these original arrays only.

The head base is assembled from original CAF resources and original morphs.
Its supported primary render meshes are 0–7 and 9, with vertex counts
54/218/70/92/73/51/51/81/20 (710 total). Auxiliary mesh 8 is untouched.
The native head part is visual+0x140+2*0x420; its model pointer is part+0x12c.
The model's B8 descriptor starts with a zero word, followed by name/count/rows
semantic groups. Each 16-byte row is RM, packed count/encoding, frame stride,
data pointer. Measured live Coordinates encoding is 24 (12-byte float3), with
frame C0=0 during assembly. Colours encoding is 8. Subsequent group headers
have no repeated leading zero; the initial diagnostic was corrected accordingly.

Original 26140 assigns a weighted morph to model D4 and invokes 1128D0.
This is a position-deformation route, not an arbitrary model/rig importer.
Per-participant head model and coordinate allocations were measured separately.

## CAF v4 / sealed sculpt resource

CAF v4 extends CAF v3 outfits with optional per-outfit `face` descriptors
(`path`, SHA-256). Each points to bounded JSON:

```
schema: caf-face-coordinates-1
template_sha256: canonical Workshop template fingerprint
basis: [body, face, eyes, nose, lips, ears]
meshes: [{rm, positions: [[x,y,z], ...], deltas: [[dx,dy,dz], ...]}, ...]
```

No native pointers, programs, normals, materials, skeleton, UVs or animation
bindings are imported. Every supported mesh/count is required in original order.
Coordinates must be finite, references within native head bind space, per-axis
deltas at most 0.6. The bottom 12% of Y extent stays fixed within 1e-6.
The JSON template hash alone never authorizes a native write.

Compilation emits `fighter-caf-faces.bin`: FCS1/version1/count/stride, followed
by fixed 17072-byte rows (selection, outfit, six basis u32s; 710 interleaved
reference float3/delta float3 pairs). Total budget is 8 MiB. Rows are bound to
existing recipes/outfits and cannot duplicate identities. The resource is
hash-checked through the managed launch environment, including its consumer
allowlist; the old unsupported-runtime-setting error must not recur.

At CAF assembly the adapter validates the original 10-row Coordinates table,
checks all 710 reference XYZ against live original geometry within 0.0002 units,
rechecks the collar, and refuses any peer coordinate-buffer overlap. It builds a
Coordinates-only controller in a bounded process-lifetime guest scratch arena,
calls original 26140, then restores the model's previous D4 pointer. Original
per-context cleanup still owns geometry; no borrowed archive buffer is edited.
After evaluation every target coordinate is checked within 0.0002 units, and
previously registered CAF participants' coordinate buffers must hash identically.
The native evaluator's weight clamp accounts for the measured small residual.

## Measured acceptance (Windows)

Source baseline 3e7b158 plus this feature; toolkit 4801dc1, win-x64-release.
All tests use the owner's dump, copied profiles and isolated data roots.

- Basic Workshop tests verify only explicit facial array slots change and
  unknown choices/bytes survive. Qt/WebChannel/WebGL exercised eight selectors,
  sliders, Save/reopen, Undo, Clear and Reset. Actual template OBJ round-trip
  covers all 710 vertices with serialization error below 5e-8 units.
- `run-20261109-224750.log.err`: two CAFs with identical non-default original
  face presets; distinct model/coordinate ownership. Native menu and combat.
- `run-20261109-225606.log.err`: first deformation stopped before evaluation
  because the initially assumed encoding 6 differed from measured encoding 24.
- `run-20261109-225852.log.err`: bounded width morph through original evaluator;
  both CAFs reached combat. The transient hard-coded probe was then removed.
- `run-20261109-230608.log.err`: normal CAF v4 resource built from an exported
  and reimported OBJ, with an untouched identical-head CAF as control. Native
  menu identities 102/103 verified. 710 target vertices checked; maximum error
  1.5377998e-05 native units; control coordinate buffers unchanged. 77 two-second
  presentation reports, no crash/watchdog/unresolved call; copied save restored
  identically. Private captures in run f3ef7fe180704e24a8b5548171ef603b.
- Focused CAF/face/launch tests: 33 passed at first integrated checkpoint.
  Thirteen native C fixtures additionally exercise the actual face reader and
  adapter: malformed/unbound rows, coordinate reference mismatch, peer aliasing,
  output verification, original D4 restoration and state cleanup.
  Complete Workshop export validated and produced a normal mod ZIP. An overlong
  initial display name correctly failed the existing native header line budget.

These pilot results do not qualify every preset/body, accessory, facial
cinematic, Blazin', repeated match/outfit combination or other platform.
Original normals, rig, eyes, mouth, hair and accessories remain; they are not
automatically refitted. Workshop proportions use approximate smooth spatial
masks, not anatomical landmarks. Keep the sculpt workflow experimental.

## Expert pipeline evaluation

Template sculpting gives a reusable path to improve likeness while preserving
the game's contracts. Arbitrary scan topology needs retopology/registration,
skin/UV transfer, collar stitching, constrained eyelid/mouth fitting and normal
support. glTF morph targets are pre-skin position/normal deltas; compatible skin
joint/weight data is still required. The
[Khronos specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)
supports that interchange model, not automatic compatibility with EAGL.
No arbitrary-topology or external DCC round-trip qualification is claimed here.

D-new: keep v1 position-only and template-bound, with independent native XYZ
verification; preserve original rig/material/UV ownership rather than trusting
mesh-supplied executable/render data. Broader sculpt qualification and owner
playtesting precede release promotion. No merge/release is implied.
