# Fighter grid isolated drawable templates — 2026-11-04

Read-only follow-up to `fighter-portrait-registration-2026-11-04.md`. Original assets were read in memory with Archive/unpack; ELF section/symbol/relocation tables were parsed with bounded struct reads, including symbol section/value plus relocation addend. No implementation/build/game run or asset export. Only this report was written.

## Closure findings

The chooseF3/4 selected Shape4 has the same small isolated structural closure as chooseF2 selected Shape2: **1096 bytes,42 method-2 pointer relocations (29 local,13 imported),four exports,zero local outgoing references beyond the span and zero incoming local references from outside**. All offsets below are `.data` relative unless explicitly stated. These are concrete hash-pinned templates, not evidence for arbitrary ELF support.

| movie / selected APT Shape | span [start,end) | model root | BBOX export | VB export | RM export | original texture / UID |
|---|---|---|---|---|---|---|
|chooseF2 /2|[F450,F898)|F7C8|F680|F4F0|F5EC|1 /2644|
|chooseF3 /4|[2ACC0,2B108)|2B038|2AEF0|2AD60|2AE5C|3 /2951|
|chooseF4 /4|[2AE10,2B258)|2B188|2B040|2AEB0|2AFAC|3 /2863|

Exact exports are `__Model:::2`, `__BBOX:::2`, `__VB:::__GPvb_9_0_2`, `__RM:::__GP_RM_2_0` forF2; replace2 with4 forF3/F4. All four symbol sizes are4, which does not describe inline object extent.

| movie | original O SHA256 | closure SHA256 |
|---|---|---|
|F2|bb9f1082f3115e6f4a68b0229b36b54196a7f06365f726175908dc4520731e6e|0ed73b48312f8f4d1b183c132e2bf87df8307f64b132fe8f5c38842c68107376|
|F3|2f7ae152ac917a663218660e5b0e794fb739c8215deafc6eaf81b4c004d06868|2684fc4a9483f3d4ffe453f36bf5ccca6cfd26c7a1983978c94c7324bb0c3c3e|
|F4|77fd4000c19f4cd9c2e941023924905b9d6f4f723c6d2bb740aadc46aa551e35|522a777ff70a2b05f8824ca434d512b8423416637a405028b76a1aa6bedb54f4|

The local graph is identical after subtracting each span start. Complete normalized relocation-site -> resolved-target list (hex):

```
444->24C 43C->340 434->32C 430->324 42C->258 418->25C
378->2E0 32C->320 31C->000 310->2B4 300->2A0 2F0->280
2E0->260 25C->25A 254->1D4 224->0B4 214->080 204->070
1FC->050 1F4->000 1D4->19C 1CC->188 1B0->184 1A8->180
1A4->170 19C->0DC 0D4->0B4 0B0->0B4 0A0->0D0
```

Inline model root is span+378, extentD0. Its root+B4 site (span+42C) points to model name span+258; root+A0 (span+418) points to material-name pointer array span+25C, whose first pointer names span+25A. Strings are `2`,`1` forF2, `4`,`3` forF3/F4. Root+CC (span+444) points to render-group span+24C. Rename owned model/material strings via appended terminated strings and explicit pointer updates; longer decimal names cannot safely overwrite adjacent original strings.

## Imports and runtime allocation identities

Complete imported-site normalized map:

| site(s) | original import |
|---|---|
|334,1E4|TAR runtime allocation (same symbol at both sites)|
|30C,1DC|GeoPrimState runtime allocation (same symbol at both sites)|
|2FC,21C|`__COORD4:::ColourTranslate`|
|2EC,20C|`__COORD4:::ColourModulator`|
|1EC|`__const MATRIX4:::EAGL::ViewPort::gpModelViewProjectionMatrix`|
|1C8,1B8|`ParentRM_TextureApt`|
|184|`TextureApt0__EAGLMicroCodePS`|
|180|`TextureApt0__EAGLMicroCodeVS`|

Both UID-bearing import strings must be cloned/rebound for an owned drawable; renaming only TAR leaves an original runtime allocation identity attached to new geometry. Preserve repeated-site sharing within the new clone. Exact original strings parameterized by U/T from the first table:

```
__EAGL::TAR:::RUNTIME_ALLOC::UID=U;SHAPENAME=T,1;XBOXEXTOBJ_SetClampU=EAGL::XBOXCM_CLAMP;XBOXEXTOBJ_SetClampV=EAGL::XBOXCM_CLAMP;
__EAGL::GeoPrimState:::RUNTIME_ALLOC::UID=U;;SetTransparencyMethod=EAGL::TM_ALPHA;XBOXEXTOBJ_SetAlphaBlend=EAGL::XBF_SRCALPHA,EAGL::XBF_INVSRCALPHA,EAGL::XBO_ADD;SetTextureEnable=true;SetPrimitiveType=EAGL::PT_TRIANGLESTRIP;
```

Absolute TAR sites: F2 F784/F634; F3 2AFF4/2AEA4; F4 2B144/2AFF4. Absolute GeoPrimState sites: F2 F75C/F62C; F3 2AFCC/2AE9C; F4 2B11C/2AFEC.

**Native identity limit:** this establishes distinct typed import names and repeated relocations, not the native allocator's UID cache key/scope or lifetime policy. Existing `fighter-m1-loader-audit-2026-11-04.md` establishes SHAPENAME resolution through a supplied module's SHAPE table (`sub_00102130`), not a global image registry. No bounded native allocator entry was provided or established here; consequently a collision-free runtime UID range and whether identity is keyed by full import string, type+UID or module+UID remain unproven. Do not invent a global UID allocator based solely on these strings. A template compiler can require reviewed unique identities, but native acceptance or a targeted resolver trace is still required to establish the exact ownership rule. Shared shader/parent/matrix/color imports above should retain original bindings.

## SHPX and drawable extent

Selected Image IDs are1/3/3, with SHPX names `1   ` / `3   ` / `3   `. All three selected entries have identical original image content SHA256 `d84100c0e37d6c60935768703cebaa3ed0f7e2c80bdb93b11efc37a1ac3438ef` and `UITextures.controls[name]` digest `98841a5860cf161e833ac60a5d46c08cc386958392528491775d3c91a432cbff`.

All are kind0x62 DXT5,64x64,not swizzled,4096 pixel bytes,no palette; attachment kinds `[0x62,0x69,0x7c,0x70]`. Pixel offsets within unpacked XSH are F2 1536,F3 480256,F4 475904. Shape bounds in each original selected APT record are `(-18.5,-18.5,18.5,18.5)`; texture64x64 maps to art37x37 at grid pitch39. New custom states can use this same selected-template geometry for both ordinary and selected frames, explicitly accepting identical art in both states. Original ordinary-state texture treatment is different and was not cloned in this proposal.

Unpacked original XSH SHA256: F2 `41c7c65ce62e953bb80590a3905117556656b54e1bc5b38ce4c025663ecd8394`; F3 `9ec0cc2552f361b0dad620ee1585301fedeedea9fdde42dd6b00a6705269f2bc`; F4 `5404a9aaf271beafb66acd7d278075c90d96c8097d1d701f577d32d71967705c`.

The earlier registration report supplies exact APT frame/character structure. With these F3/4 closures, static frame-bank composition is now bounded to the same1096-byte template for all layouts. Its remaining specific risk is native import identity ownership, not an unbounded UI mesh decoder. Native runs must still verify selection, deselection, redraw, scrolling and retail coexistence. No runtime acceptance is claimed.

## Simpler static option: whole result-movie data template

Follow-up read of original `t_MS_55_2p/3p/4p` establishes that **copying its complete1120-byte .data is a bounded alternative** to the selected-grid closure, while directly reusing the current authored result texture's UV/control contract. All three have42 pointer relocations: the same29 local graph entries listed above, now relative to result .data start0, and the same13 imported-site map. All local resolved targets lie within [0,1120); no imports reference another source section. There is no need to decode arbitrary geometry. No native transfer/acceptance was performed.

| original result | O SHA256 | .data SHA256 | UID |
|---|---|---|---|
|t_MS_55_2p|0a2db3c047c6e173fc4c130852e2c74206451980c6353515f0be695f7de64954|d5146f01f5e502a4bd6b754cf8f4a854c930f80abfa90d5c5cabb72ac472b497|1599|
|t_MS_55_3p|784e631a97322d18d7e17f2b375a233857d80c89b58e4080ea3a6c279e530c84|5942b7338485c4b6cc3e00005d7f9c44fe109ee620e74404bc76d04c3fadae02|2775|
|t_MS_55_4p|c6ccb53a3c59d1d23be3256d12e7065a8eb36a70e18dd82805e75164c7890e8b|8e6c2a27b6540f559a846ebe7e6e4e7154c71ed8439a22ff9127070136157494|580|

All three use section order null,.data,.rel.data,.shstrtab,.symtab,.strtab, with .data1120bytes, relocation336bytes, symbol table304bytes. Original imports have identical names/control suffixes to the table above, with result-specific UID and SHAPENAME1. Both TAR and GeoPrimState must receive owned allocation identities and both repeated sites must bind the new corresponding symbol.

Five original exports, all size4:

| export | .data offset |
|---|---|
|`__Model:::2`|378|
|`__BBOX:::2`|230|
|`__VB:::__GPvb_9_0_2`|0A0|
|`__RM:::__GP_RM_2_0`|19C|
|`__EAGL_TOOLLIB_VERSION:::EAGL_TOOLLIB_VERSION-4`|000|

**Do not append the version export unchanged:** chooseF already exports that exact name (verified F2 at.data0). It is shared tool metadata, not a fifth custom drawable identity. Retain the destination export rather than adding a duplicate. Copying source.data0 is still necessary for the internal local references to0 at sites31C/1F4; do not redirect those geometry-local references to destination.data0 just because the version export happens to name it. Original result.data0 begins float1 followed by zeros, same sampled destination prefix; that numerical match is not permission to alias geometry.

Model root378 has name pointer42C->258 (`2`), material-name-array pointer418->25C->25A (`1`), render-group pointer444->24C. Rename new model and material with appended strings and rebind only these pointers. Rename the four drawable exports to collision-free owned model/RM/VB/BBOX names; preserve original destination symbols and original imports. Rebase every source local target and relocation site by the append offset; map imports explicitly; do not copy source symbol indices into the destination relocation table.

Original result APT has Shape2 model ID2 with bounds `(0,0,L,L)`, L44/39/32 for2/3/4p. For a new thumbAll frame whose original cell wrapper centers at18.5, a self-contained placement matrix `(37/L,0,0,37/L,-18.5,-18.5)` maps that result quad to the original centered37x37 art bounds. Matrix factors here are APT floats, **not ActionScript percentages**. The custom Shape record retains source bounds and receives the owned numeric model ID. This uses the result geometry UVs and the exact compiled result image, avoiding crop/retile/resampling. Both custom selected/ordinary frames can place the same Shape with that matrix; differing retail state shading is not reproduced.

Original result SHPX entries all have name `1   `,kind0x62,no swizzle,no palette,attachments `[0x62,0x69,0x7c,0x70]`,pixels offset128. The2p/3p images are64x64/4096bytes; **4p is32x32/1024bytes**. Reuse the authored matching result variant, not a forced64x64 grid contract. Rename directory/material attachment identity and the cloned O TAR SHAPENAME together. Preserve all other controls through the existing typed UITextures adapter.

| result | unpacked XSH SHA256 | UITextures control digest |
|---|---|---|
|55_2p|8ceedc51b8255b068e1d21371e7ce8a35c3e0b0bb86ad5205c98a1d3b296d5b3|63b5c661092caacfd772d13040119552f66fcb1596421d7937607ca353a40bc6|
|55_3p|f2b65ed1502f33be390e9c87a70dcc19bff4d1dbe34afbb31d7c5f7b95611779|4d7bba015febb9b6ebe029b5d0aed4c7d2ef590b97d132bde487e30c3bc7ce47|
|55_4p|c8602769c7a9afd830a2580c3bdf2ad2ab42b86f39af8b865d09d37a486e40ec|700b3ba5aefff5e3df77f47f5d6275f29b6936e2f669a82d423145271fd6bd87|

This is preferable to the dynamic external-movie prototype when preserving ordinary synchronous thumbAll redraw/select/deselect behavior is the goal: no per-cell asynchronous load lifecycle, no nested dynamic clip ownership, and no need to rebuild authored thumbnails. It still needs a typed ELF append/symbol/relocation composer, APT frame/character appender, SHPX entry appender, owned import identities and focused native acceptance. The source-only evidence supports this narrowly pinned template; it does not prove native UID cache semantics or appearance after transfer.

## First static native padlock diagnosis (2026-11-04 late run)

Read-only inspection of actual composed cache `logs/fighter-ui-preview/a6f656330cf93f3a936630c32f49d16efefc2affa4282814f9e2164de449cd1c/screens/screens.viv` associated with run235407: generated mapping action0x16500 sets `_recompFighterThumbs[100]=300`, `[101]=301`; `CCharacter.getThumbID` body0x1676C correctly gets semantic getID, looks up that map and returns owned token when defined. Original redraw body0x11F5C and replacement body0x167F4 coexist, as expected for appended prototype rebinding. No wrong donor-map literal was found.

The first controlled candidate is the new PlaceObject flag: `fighter_grid.append_grid` writes flags6 (HasCharacter+HasMatrix), with depth1, without MOVE. Original thumbAll frame1 uses6; subsequent normal replacement frames2/3/5 use3 (MOVE+HasCharacter). Original frame6 removes depth1 before frame7 creates flags6; frame16 removes before frame17 creates6. Ordinary frames150/151 use3. Original bank contains131 flags3 placements versus22 flags6. Added frame301 immediately follows lock frame300 at depth1, and added later sparse frames do not remove that object. A full self-contained **replacement** should be trialed with flags7 (MOVE+HasCharacter+HasMatrix), keeping the authored transform. This is consistent with a padlock remaining at occupied depth1 instead of an O/texture error. It is a strong asset-semantics hypothesis, not a traced native-placement proof: original later sparse frames241/250/300 also create6 after gaps, and exact goto reconstruction policy has not been established. No fixed300-frame native cap was proved. Primary agent owns the controlled retry and native acceptance; this audit performed no source edit or run.

## Flags7 retry follow-up — 2026-11-05

Primary reports flags7 still shows padlocks, so MOVE alone is not an accepted fix. Bounded re-read finds **no300 clamp** in original redraw/selectChar/deselectChar: no frame-range comparison/modulo/saturation. The only explicit300 route is `CHAR_LOCKED=300` (F2 initialization0x10816–0x1081C,duplicate0x1168A–0x11690). Original redraw calls isLocked at0x1210D–0x12118, true branch goto300 at0x12124–0x1212D, else getID+150 at0x12134–0x12149. Select's frame expression is getID+1 at0x128F0–0x12911. Its unconditional updateChar afterward means a correct large portrait **does not by itself prove the grid unlocked branch ran**.

Actual flags7 artifact `17a8bd6c8af7b3e719ed719f620577177fd6562d04cde3aaa9aa2734e106c394`: generated redraw0x167F4/676bytes, locked goto0x169C5, unlocked getThumbID0x169D4 and goto0x169E7; deselect0x16AD8/131bytes,getThumbID0x16B39,goto0x16B59; select0x16B9C/244bytes,getThumbID0x16C69,goto0x16C86. They retain distinct branches and targets; no wrong static token map was found.

CCharacter lock path does not consume artwork identity: `isLocked(SetIndex)`0x118B0 (duplicate0x10A3C), when parameter undefined, returns whether getFirstUnlockedSet equals BAD_INDEX. `getFirstUnlockedSet`0x11938 (duplicate0x10AC4) loops aDataSets, creates CSimpleParam, advances nextValuePair three times, compares numeric getValue to UNLOCKED, returning the first index or BAD_INDEX. Explicit indexed isLocked similarly parses data. Neither calls getID/getThumbID or a native unlock hook. `getID`0x117C8 (duplicate0x10954) separately parses dataset selection identity. No `firstUnlockedClothingSlot` symbol was found in current src or menu compiler. No static route was found for300/301 presentation tokens to enter these lock getters.

Generated getThumbID uses literal strings and no ConstantPool instruction; cloned grid methods bind the original captured pool while registering. The only four redirected calls are visual getID consumers across redraw/select/deselect; the CHAR_HERO semantic getID comparison remains. No concrete constant-pool collision was found.

**Next diagnostic:** primary should instrument one temporary runtime-owned wrapper to emit semantic getID, getThumbID, isLocked, getFirstUnlockedSet, requested frame, target `_totalframes` and `_currentframe` before/after goto, for each of the two custom cells. Log before returning getThumbID too, to prove the call is reached. If isLocked true, inspect authored roster dataset unlock field; if false and request450/451 but `_totalframes=300`, investigate native sprite loading/cached frame count; if total451/current450 yet padlock, inspect native frame reconstruction/new frame placement/model resolution. These are distinct hypotheses; original APT alone cannot resolve them. No implementation/build/game run was performed by this follow-up.

## Native in-place frame fixup: concrete shared-pointer defect — 2026-11-05

Primary's runtime diagnostic now establishes semantic IDs103/104, thumb tokens300/301, isLocked=false, `_totalframes=451`, `_currentframe=301/302` matching requests301/302. Neither locked branch nor300 cap explains this run. A private known-retail-Shape2 plus explicit-remove trial also preserved the padlock, directing attention to frame loading.

Bounded generated-native read identifies forward counterpart **sub_00160720** in `src/recomp/gen/recomp_0010.c` (function begins line88646), versus reverse **sub_00160B90** (begins89412). The original reverse site0x161043/0x161052 restores character signature09876543 and later subtracts blob base from character pointers. Forward0x160760/0x16076C adds blob base to character table entries, writes its runtime signature/context at character+4 at0x16077E, and dispatches by character kind. Sprite kind5 at0x1608F5 passes `sprite+8` into **sub_0017DD70** (`recomp_0011.c`,function starts52664).

`sub_0017DD70` is the decisive forward frame walker:

-0x17DDD1 adds blob base to sprite frame-array pointer (`this+4`, where this=sprite+8).
-0x17DDE3–0x17DDF2, for **every frame**, rebases that frame's item-list pointer in place.
-0x17DE10–0x17DE21, for **every item**, reads the item-list element and adds blob base **to the element in place**. There is no already-fixed/visited guard.
-0x17DE2D dispatches on the referenced item's kind. Action kind1 at0x17DE4E–0x17DE55 rebases Action+4 (code pointer) in place, then invokes sub_00156110 (tail to00155AD0) at0x17DE7B.
-PlaceObject kind3 at0x17DEB8/0x17DEBF rebases nonzero name pointer+34;0x17DEDC rebases nonzero clip-event pointer+3C and then walks nested events.
-The loops use the actual sprite frame count at0x17DF6D, not300.

**The current custom state frames share the same item-pointer list**, Action record and PlaceObject record between token and token+149. This is invalid under the proven walker: the second state visits the same list and adds the blob base again to its entries, corrupting both states' list contents. This does not depend on MOVE flags or custom model resolution. Making only the frame lists unique is insufficient if both refer to the same Action record, whose code pointer is then independently rebased twice. Prefer independently emitted list and records for every new state. Stop/End instruction bytes contain no internal absolute pointer, but unique instruction blocks are the simplest ownership rule and avoid future nested action fixup aliasing. A PlaceObject with all optional pointer fields zero has no pointer rebasing inside its record, but unique records remove reliance on that incidental property.

Original thumbAll provides a useful integrity reference:174 nonempty frames have174 unique item lists;327 frame items have327 unique record addresses. None has the custom alias pattern.

This proves a concrete loader-incompatible asset graph, with an exact correction target. It does not claim to have observed the corrupted native memory or prove it is the only remaining issue. Primary should independently emit both state graphs, then retry the known-retail drawable control before attributing any residual issue to ELF/model transfer. This audit changed no implementation and ran no game/build.

## Four-player flat-quads follow-up — 2026-11-05

Primary reports independent state graphs now render correct2p faces, while4p remains flat-colored quads. Bounded source/data/import read found **no concrete ELF alias or relocation defect** explaining that difference.

Original `t_MS_55_2p` versus `t_MS_55_4p`1120-byte.data differs only in float bounds/centers/radii at offsets23C,240,358,35C,368,36C,374,3C4,3C8,3D4,3D8,3F4,3F8,404,408,410. Vertex/UV/layout/RM/control bytes otherwise match exactly. Import strings are identical after replacing UID numerals; the differing symbol order is harmless because the compiler maps by source symbol index to destination name. Both use the same TextureApt0 VS/PS, ParentRM_TextureApt, viewport matrix, color imports and runtime allocation control suffixes. No source32x32-specific shader/coordinate-format requirement was found. Existing working result4p is itself evidence against declaring32x32 unsupported generally.

Actual cache `021ce66560a84acfad6bf2ce3341056f7f64b9e4c5f92cd6a4b99ba1438b3130`: chooseF2 custom models430/432; chooseF4 custom models433/435. Compared each complete copied.data block to matching original result template after masking the42 pointer words: **all1120 remaining bytes match**. For every original local pointer except the three intended renamed-string sites, destination target equals append_base+source_target. Every imported relocation resolves to an identical normalized source import string. Renamed model-name42C, material-name25C and shape-key32C resolve consistently. In4p model433 uses image432, TAR/GeoPrimStateUID3272; model435 uses image434,UID3273, with both repeated sites bound consistently. No accidental alias to original texture or source.data was found.

The next useful controlled comparison is to put the **exact accepted2p original result geometry+compiled64x64 image** into the4p grid, using37/44 placement scale, leaving the4p selector/container intact. Success would narrow the remaining issue to32x32 raster binding/upload in this multi-image module or its copied controls, rather than4p APT frame handling or general cloned-model support. Failure would instead keep4p container/module/render-state differences in scope. This is a diagnostic recommendation, not implementation or acceptance; no code/build/game change was made by this audit.

## Native lookup order and UV lead — 2026-11-05

Original chooseF2/4 SHPX directories are strictly lexically sorted (184/181 entries); appending432/434 after99 breaks that property. However, the proven original APT lookup path **does not require directory sorting**:

-Loader callbacks are assigned in `recomp_0011.c` around63396: `[3B1E38]=0017F2F0` (Image), `[3B1E44]=0017FC00` (Shape).
-Image callback0017F2F0 obtains the XSH at0017F327, reads count atXSH+8, loops index0..count-1 at0017F338–0017F35D in8-byte directory strides, gets the entry name using001DECFB, converts with atoi0017F34F, compares requested numeric image ID, and returns its raster root at0017F375. No binary search/order comparison occurs.
-Shape callback0017FC00 calls0017EFF0. That function enumerates Model exports using0010A970 at0017F026/0017F05F, atoi of model-root+B4 name at0017F042, and equality comparison to requested ID. It does not binary-search appended export names. A separate model-table helper0017F080 also enumerates exports and writes table[atoi(name)]=model.
-Generic TAR SHAPENAME resolution00102130 uses00119470 key-table lookup and supplied module0010A440 lookup rather than direct lexically ordered SHPX-directory binary search. Native00119470 hashes then compares bucket entries; this is distinct from assuming on-disk order.

Primary GPU observation (run004701,frame6380) further establishes that the4p custom quads bind valid64x64fmt0F raster addresses, while UVs remain about0..44 instead of normalized0..1. This specifically weakens a missing-raster lookup/sorting explanation.

A nearby **unconfirmed normalization lead**,001813E0 (recomp_0011.c61481), constructs a512-entry model table with0017F080 at00181430, derives reciprocal power-of-two width/height factors from a supplied raster at00181466–001814BB, then loops models at00181530–001815B8, obtains render data with00112CC0/00112D30, applies001EA920 and writes matrices back, followed by00112C90. Its callsite/reachability and whether it modifies vertex UVs versus model texture matrices were **not established** here; do not cite it as the proven missing path. A targeted native trace or own-XBE data-function-pointer xref can settle that without changing generic renderer behavior. No implementation/build/run was performed.

## Verified missed image-owned matrix key — 2026-11-05

Primary identified the remaining semantic name; independent source verification confirms both original2p/4p result templates have **local relocation.data+310 -> .data+2B4 -> `ScaleMatrix::1::TextureMatrix`**. The earlier compiler rewrote model42C and image25C/32C names but preserved this image-owned matrix key. The structural relocation audit correctly found it rebased to the original target string, but that is semantically wrong when image1 becomes an owned image432/434. This corrects the earlier incomplete assessment of all image-key consumers.

Native normalization reachability is now established: initialization assigns `[3B1E40]=001813E0` (`recomp_0011.c63398`). In character finalization, **0015F9C3** (`recomp_0010.c86191`) is Image/type7 case: pushes Image+8 raster pointer, current image character index ebx, and context, invoking callback at0015F9CD. In001813E0 the second argument (image index) is formatted with the ScaleMatrix format at00181404. Its reciprocal width/height calculation and per-model matrix lookup/update at0018153B–00181598 therefore operate on the **image-specific key**, not a generic fixed ScaleMatrix1. The copied key must change with its owned image identity.

The exact correction target is append a terminated string `ScaleMatrix::<owned-image-ID>::TextureMatrix`, then set cloned local relocation site310 to that new string. Do not overwrite the original in-place or globally rename keys belonging to retail images. Current new APT Image character IDs equal their numeric image IDs; the callback proves that equality matters for this normalization path and should be asserted by the compiler. Name25C/material,32C/shape-key,310/scale-matrix and TAR SHAPENAME must describe the same image ownership.

This explains the GPU symptom: raster binding is valid but the custom model's texture matrix retains pixel-unit UV scaling when its key fails to match the new image's normalization visit. Why2p looked correct is not proven here; accidental use of original image1's scale is a plausible explanation that still needs the primary's native control. Primary owns correction/test/run. No code/build/game changes were made by this audit.
