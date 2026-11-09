# Workshop CAF v2: native atlases and saved finishers

This extends the standalone CAF contract from PR213. It targets the Workshop
roadmap's custom textures and fighter modpack authoring, preserving FCA1 recipes
and original retail CAF assembly. It does not add custom meshes, high-resolution
admission, arbitrary moves or Story-save conversion.

## Portable input

A `caf-fighter-2` resource names the same hash-bound recipe descriptor as v1.
The recipe retains v1 stats, styles, appearance and colors, with optional:

- `finishers`: four lowercase eight-digit SODB record identities, resolved through
  table47D305FD/member6FC83815 against the original dump; choice must be0–81.
- `atlases`: A, B, C, D, D1 and D2 slot descriptors with relative PNG path and
  SHA-256. PNGs are at most1MiB and exactly256×256. Import retains source bytes.

Package inventory follows only atlas descriptors in the hash-verified recipe.
Undeclared files, traversal, modified recipes and modified PNGs fail admission.
Existing v1 JSON and the232-byte FCA1 native row are unchanged.

## Compiled sidecar and ownership

`fighter-caf-extras.bin` is bound by `caf_extras_sha256` and the corresponding
RECOMP_FIGHTER_CAF_EXTRAS / RECOMP_FIGHTER_CAF_EXTRAS_SHA256 variables. Header:
FCX1, uint32 version1, count, row stride48. Each little-endian12-dword row holds
logical selection, finisher-present flag, four choices, then six atlas offsets.
Zero offsets mean inherited art. Payload blocks are256×256×4 BGRA, deduplicated
by content; the full sidecar is bounded to16MiB. Admission validates lengths,
row membership/uniqueness, choice/flag ranges, dense block use and offsets.

After original64170 builds a participant's CAF,92BE0 converts declared bitmap
slots to owned32-bit surfaces. RGB writes respect FSH's0x2000 Morton layout;
original alpha remains at each native address.98270 rebinds only this visual's
materials. Superseded owned outputs are freed, borrowed A24C bases are preserved,
and the original context visual destructor owns replacements. No global hash
replacement or shared base texture mutation is used.

Before original1A8180 builds its paired-motion mask, the exact active CAF
participant receives its four choices at3B9288+slot*16. Actor/context ownership
and core are checked. The existing retail paired-motion machinery consumes them.
Clearing CAF state restores the previous matrix only if our last assignment
still owns it; a newer native profile initializer is preserved. Repeated setup
keeps the original journal. Failed extras startup also releases recipe state.

## Qualified evidence

Windows build uses toolkit4801dc1 against PR213 head81ce1d7. 52 focused compiler,
package and actual native C fixtures pass: independent rows, malformed sidecars,
linear/Morton RGB with varying native alpha, finisher routing/ownership/clear,
mixed audio and existing teardown. Cross-platform fixtures are included in CI.

Private original-art pilot: bodyA, style order Kickboxing/Streetfighting/Wrestling,
core101, four choices52/38/30/39. `run-20261109-152651.log.err` completed native
logical100 versus retail17, with five applied atlas slots, selector portrait,
seven combat/result assertions, two acknowledged Options saves, no crash,
watchdog or unresolved call, and byte-identical guarded save restoration.
Captured torso/jeans/normal-face RGB equals supplied PNG RGB exactly. Native
alpha is unchanged. D1/D2 are installed; every injury frame is not qualified.
All four Blazin' cinematics were not exercised. Source PNGs and game bytes stay
private; HD restoration and arbitrary atlas resolutions remain pending.

Retained failures: initial clone-only conversion failed closed; an initial
linear write into a Morton surface was visibly wrong and was stopped normally.
The correction is supported by capture comparisons and nonuniform native C
fixtures. An earlier stock pass had a wrong expected opponent in its command;
its separate verdict records actual identities rather than rewriting that run.

Stock quick regression and cross-platform CI results are recorded in the PR.
This is a development extension requiring a matching runtime, not a shipping
release claim. No source assets, saves, captures or generated guest code ship.
