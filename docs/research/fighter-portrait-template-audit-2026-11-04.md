# Fighter portrait template audit — 2026-11-04

Bounded read-only comparison of the supplied local community ZIP and the user's own `game/screens/screens.viv`. No source edits, builds, game runs, asset exports or external code. Only hashes, counts and format observations are recorded.

## Result

Both community `p_cf_102_2p.big` and `p_cf_103_2p.big` have an exact original layout template: **`screens/portrait/p_CF/p_cf_56_2p.big`**. Their decoded `.apt`, `.const` and `.o` payloads are byte-for-byte identical to the corresponding retail56 files. No basename normalization is necessary inside those payloads; only BIG entry names differ. Their SHPX nonpixel bytes are also identical to retail56. Copying just each community image's pixel ranges into the original56 XSH reconstructs the community XSH byte-for-byte.

This supports selecting original56 controls/movie/geometry for these two supplied2p images. It does not establish movie registration, selector-grid integration,3p/4p support, or visual/native acceptance.

## Evidence

| Original56 decoded payload | Bytes | SHA-256 (also source102 and103 where equal) |
|---|---:|---|
| .apt |228|c52e1dd72131000b7fbe315d3b01b801b32507999a0ccd97212dc7dce41e27a9|
| .const |32|3bc8b12d1a21ffc0777248db83f0c0ef12796f35c43dfda603c8494194c24846|
| .o |3914|a222b105a7c4ea26b05270878e5e0daf108aae7184928d2f61ccea1ef7610bf3|
| .xsh |98816|bdb04314c75f614833f263ccf07bc9e656ed525ef7691db552527c5a13ef0c60|

The `.o` has ELF magic; exact equality preserves its geometry data and associated structure without interpreting UVs. Decoded source102 XSH SHA-256 is `3fc254d5e828f5259901c0b6920444a1b1ba0948f687a3fb35d195d6f77385b5`; source103 XSH is `1d488d5e2ae95d8983e5c95bdd5a7a8f3a35046b7179c4ae5f90345cb4026e2e`.

The two pixel ranges in all three matching XSH layouts are `[128,32896)` (32768 bytes) and `[33152,98688)` (65536 bytes). An in-memory call to `PortraitTextureTemplate(original56_xsh, verified_digest).compile(source_xsh)` equaled the full source XSH for each102/103. No outputs were written. This proves equality of every nonpixel byte as well as accepted tile dimensions/format for these inputs.

## Template census and why dimensions alone are insufficient

Decoded all222 original archives under `screens/portrait/p_CF/` through `Archive`/`unpack` and parsed each XSH using `UITextures`. A comparison allowing basename differences (`p_cf_<id>_<2/3/4>p`) found exactly one original with all three source movie/control payloads `.apt/.const/.o`:56_2p. A raw comparison then verified that this match needs no normalization. Source102 and103 have identical movie/control payloads.

Ten originals share the two image container dimensions256x128 and256x256, format0x62, numeric IDs1/2:13_2p,17_2p,18_2p,28_2p,32_2p,46_2p,56_2p,72_2p,73_2p,8_2p. Only56_2p also matches the source's per-ID `UITextures.controls` signatures. Thus choosing any original with matching container dimensions would accept nine layouts without equivalent control evidence.

Original56/source102/source103 per-ID control hashes:

- ID `1   `: `a9dfb98d1f4d4fbad12c5a81b589a95f291b8151700f6f02719a02e9fba4ce50`.
- ID `2   `: `3c82c3df794762ec1868c9aa24fbf0b965a9bda09a148aa7b6dd54bd3e1f129a`.

Original Blaze57_2p has four containers128x128,128x128,128x256,128x256 and is not compatible with the source two-tile shape. Retiling the source into57 would require a separately decoded and visually accepted crop/geometry transformation.

## 0x7C attachment observations

For both matching source portraits and original56:

| Tile | Container | 0x7C payload u32s at+4,+8,+12 |
|---|---|---|
|1|256x128|1,253,121|
|2|256x256|1,253,256|

For original57 the corresponding four triples are `(1,84,121)`, `(1,128,121)`, `(1,84,256)`, `(1,128,256)`. These are plainly different from allocation/container dimensions. They are consistent with logical used extents and padding/cropping metadata, but **native consumers were not resolved in this audit**, so that semantic label remains inference. Do not rewrite them based on container dimensions. Preserve the complete original attachment and movie/geometry bytes.

`UITextures` correctly keeps space-padded directory IDs separate from NUL-padded0x70 names. IDs1/2 are texture identities local to this movie layout, not fighter IDs. The existing parser recognizes0x7C's first word as a0/1 flag and hashes the remaining words into controls; the last two words must continue to participate in compatibility checks.

## Recommended supported-profile rule

For a source already tiled into native SHPX, choose a verified original template by exact reviewed `.apt/.const/.o` content plus exact per-ID nonpixel/control layout, not by fighter identity, container sizes, or texture IDs alone. For102_2p and103_2p, pin original56_2p and its XSH digest above. A stronger pixel-only input check can require equality of all bytes outside pixel spans, as demonstrated here; this avoids guessing which unknown controls are geometric.

The current low-level pixel compiler compares tile sets/format/dimensions and copies pixels into original controls. Its caller must establish the source-to-original layout match; those dimensional checks by themselves do not prove the selected controls crop the authored image correctly. With source controls differing, fail closed or require explicit offline retile/crop authoring and visual acceptance. Do not change original controls or load community APT/CONST/O merely to make dimensions fit. Keep runtime_ready false until registration and native acceptance are independently demonstrated.

## Extension: complete six-role template set

Extended the comparison to source102 large portraits2p/3p/4p and source101 thumbnails2p/3p/4p. Read all444 original p_CF/t_MS portrait archives. A single original identity supplies every role under the established selector+1 convention: **large p_cf56 with thumbnail t_MS55**.

| Community role stem | Original role stem | Original decoded XSH SHA-256 |
|---|---|---|
|p_cf_102_2p|p_cf_56_2p|bdb04314c75f614833f263ccf07bc9e656ed525ef7691db552527c5a13ef0c60|
|p_cf_102_3p|p_cf_56_3p|70f9907029ef29af7f72e3fb9d38e7eb0eb7b56307417df7ca47b96faf2f1aed|
|p_cf_102_4p|p_cf_56_4p|e6c25d0b3237f8de8f690dc18d2f15933fbea934c1c4e5281521e73d449ce99c|
|t_MS_101_2p|t_MS_55_2p|8ceedc51b8255b068e1d21371e7ce8a35c3e0b0bb86ad5205c98a1d3b296d5b3|
|t_MS_101_3p|t_MS_55_3p|f2b65ed1502f33be390e9c87a70dcc19bff4d1dbe34afbb31d7c5f7b95611779|
|t_MS_101_4p|t_MS_55_4p|c8602769c7a9afd830a2580c3bdf2ad2ab42b86f39af8b865d09d37a486e40ec|

For **all six pairs**: decoded APT/CONST/O are raw byte-identical, per-image XSH controls match exactly, and the current in-memory pixel-only compiler reconstructs the full community XSH byte-for-byte from the original template. Basename-normalized comparison therefore requires no exemption for these pairs: there are no raw control/movie hash differences to explain. Only outer archive entry names differ. No community UI code needs to enter the output.

The large3p layout is four containers32x128,128x128,128x256,128x256; large4p is two128x64,128x256. Thumbnail2p and3p use one64x64 container; thumbnail4p one32x32. All are image kind0x62. Correct role-specific template selection remains necessary despite repeated thumbnail dimensions.

Exact movie matches are unique to the selected original for all three p_CF roles and t_MS3p/4p. t_MS101_2p also matches original t_MS54_2p movie bytes; t_MS55_2p supplies a coherent common identity with the other five roles and has exact control/nonpixel compatibility as tested. This is a template choice, not evidence that the fighters or source logical IDs should be remapped to that retail identity.

Additional shared source/original raw movie hashes:

| Role | APT SHA-256 | O SHA-256 |
|---|---|---|
|p_CF3p|588233d707ee4fac5b07ceac082d9f83ed45ddbdce0d9442294d313da3954af0|024c4d70ac8413880eb33eeaca3997f8ebbf581496f509bc12611949e1a76ae7|
|p_CF4p|ca135a1bcae7b8768c6c284f9b576c6a601fa194055fa565d054bd8326c74ab7|26c06a2acbb28f9385dc0a6a816acf54c06d820a2bbd58ffaca65f750e4b44a1|
|t_MS2p|9b18401b4eeb92893134081401130944fee295d6745582aadb683103eb64f0a0|0a2db3c047c6e173fc4c130852e2c74206451980c6353515f0be695f7de64954|
|t_MS3p|840be19222cadcdd3c6d032c687fd75b3d6fb94c0ce0f833c6b09aca486d7ad0|784e631a97322d18d7e17f2b375a233857d80c89b58e4080ea3a6c279e530c84|
|t_MS4p|5efd027a1d253af643c1e604e132211d4dfd2b33dbe9af28e18fd4dad33f4333|c6ccb53a3c59d1d23be3256d12e7065a8eb36a70e18dd82805e75164c7890e8b|

CONST3p p_CF hash is `45d7213be28c02e866b8ec325ce66674b2e908834fe1a9c8253e5569920689ed`; p_CF4p uses the previously recorded p_CF2p constant hash. All three thumbnail CONST hashes are `a1ad3e00ac7bbddc09e024f79918f45b33879cfd9abc89c4da2b9ce0f88ce6dc`.

An exact source-controls policy is compatible with every tested pair. Although annotation attachments could theoretically differ without changing geometry, no such exception is needed for this six-role set. The stronger outside-pixel equality remains established here, avoiding an unverified assumption about which annotations are safe to ignore.
