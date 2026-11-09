# Fighter portrait registration audit â€” 2026-11-04

Read-only bounded audit of the existing registry/SODB/UI asset route. No code changes, builds, game runs, external reference implementation, or copied game bytes. Only this finding is written. The current M1 appearance acceptance (new models 610/611) is supplied context; this audit does not rerun it.

## Finding

The donor portrait is expected from the current compiler. Appearance registration and UI portrait registration are separate. Changing Model or registering model 610/611 cannot change the selector's preauthored 2D portrait. The existing compiler deliberately copies retail portrait movies and maps custom grid artwork back to donor thumbnail frames. A new semantic portrait resource needs both a portrait-movie texture adapter and separate thumbnail registration; changing SODB Thumb alone will not accomplish this.

## Verified registry and SODB behavior

- `setup/fighter_registry.py`: `portrait` is an independent resource kind/component with no skeleton/event compatibility requirement. There are no separate semantic `icon`, `profile`, or `win` components today.
- `setup/fighter_native.py`: `RESOURCE_FIELDS['portrait'] = ('Thumb',)`. Catalog resources are retail donor bindings. `compile()` accepts authored appearances through `appearances`, but authored portrait resources still fail `native-resource`. Added fighters record a separate `portrait_donors` mapping.
- `setup/fighter_sod.py`: Thumb is a native string field. On the local original `game/assets/djv2.sod`, `name_hash('Thumb') = 0xD36C52A5`, schema lookup `hash ^ CHARACTER` gives `(23, 1)` (word slot 23, string descriptor 1). Every Character metadata row has Thumb symbol **SomeThumb**. Examples: Ludacris selection54/core4, D-Mob2 selection83/core51, Trejo selection7/core23 all use that same symbol. It therefore cannot encode their different selector portraits.
- The same bounded schema check found no Character members named exactly `Icon`, `Profile`, `Win`, or `Portrait`. This is not proof that no differently named native members or other tables serve those roles.
- No new native lookup hook is needed to explain this symptom: current setup code explicitly chooses the donor artwork. Generated guest source was not rewritten, executed, or broadly reverse engineered.

## Exact archive registration already implemented

`scripts/fighter-runtime-probe.py:prepare_portraits()` derives `{custom selection_key: portrait donor selection_key}` from bindings, then calls `setup/fighter_archive.py:portrait_aliases(..., results=True)`. The output is a content-addressed composed `screens/screens.viv`, based on the original or verified language-composed archive.

| Consumer | Outer BIG entry inside screens/screens.viv | Key convention |
| --- | --- | --- |
| Large Choose Fighter portrait | `screens/portrait/p_CF/p_cf_<K+1>_<N>p.big` | logical selection K plus one |
| Match summary portrait | `screens/portrait/t_MS/t_MS_<K>_<N>p.big` | exact logical selection K |
| Match summary logo | `screens/portrait/l_MS_<K>_<N>p.big` | exact logical selection K; custom currently blank |
| Small Choose Fighter grid | `screens/battle/chooseF<N>.big` | frame selection inside its own APT and SHPX |

Here N is 2, 3, or 4 participants. Thus K=100 needs `p_cf_101_2p.big` etc. and `t_MS_100_2p.big` etc., independently of model number610. Do not derive these paths from model IDs, core IDs, SODB handles, or array position.

The large/result portrait BIG contains `<stem>.apt`, `<stem>.const`, `<stem>.o`, `<stem>.xsh`. Existing aliasing decompresses the donor BIG, requires exactly this envelope and no embedded basename references, renames all four entries, and recomposes it without changing their payloads. The logo exception instead wraps the original `screens/trans/empty2.big` (APT/CONST only), avoiding donor branding over custom names.

`prepare_portraits()` also compiles chooseF2/3/4 APT/CONST and matchSm2/3/4 APT/CONST. `setup/fighter_menu.py:presentation_action()` registers `_recompFighterThumbs` and a `CCharacter.getThumbID()` getter. Only visual getID consumers in `CThumbGrid.redraw`, `selectChar`, and `deselectChar` become getThumbID; created-player identity comparisons and ControllerSetup retain actual getID. The original grid methods add their native thumbnail state offsets and call gotoAndStop. Large portrait aliases and thumbnail donor frames are distinct registrations, even though the current compiler derives both from the same donor pairs.

## Local asset samples and shape IDs

Read directly through the repository's Archive/RefPack reader from the original local screens archive; no assets were exported. These are exact sample facts, not a census asserting identical layouts for every fighter.

| Entry | SHPX directory names (raw four bytes) | Image dimensions |
| --- | --- | --- |
| `p_CF/p_cf_1_2p.big` | `1   `, `2   `, `3   `, `4   ` | 32x128, 128x128, 32x256, 128x256 |
| `p_CF/p_cf_1_3p.big` | `1   `, `2   ` | 128x128, 128x256 |
| `p_CF/p_cf_1_4p.big` | `1   `, `2   ` | 128x128, 128x256 |
| `t_MS/t_MS_0_2p.big` | `1   ` | 64x64 |
| `t_MS/t_MS_0_3p.big` | `1   ` | 64x64 |
| `t_MS/t_MS_0_4p.big` | `1   ` | 32x32 |

All sampled root image attachment kinds are `0x62` (DXT5 under the existing SHPX decoder). Sample selector portrait APTs have one frame; p_cf_1_2p has Image records1..4 and Shape record5. The image records' payload words at record+8 are1..4 respectively. t_MS_0_2p has Image1 (payload1), Shape2. These numeric image IDs correspond to the displayed numeric, space-padded SHPX directory names. Exact `.o` shape/material topology and render UVs were retained opaque, not decoded in this audit.

The chooseF2/3/4 SHPX directories contain184/183/181 entries respectively. Example chooseF2 names include `1   `, `101 `, `103 `, `105 `, all sampled64x64. These names are movie-local texture IDs, not evidence that texture101 belongs to fighter selection101. Original p_CF and t_MS families each contain222 BIG entries; l_CF contains228. l_CF was observed as a separate family referenced by chooseF2 constants, but its visual/branding role was not separately established here.

**Important implementation boundary:** `setup/fighter_xsh.py:Textures` currently calls `shape_name()`, which only permits `[A-Za-z0-9_]{4}`. It rejects these legitimate UI names containing spaces. Reusing the appearance validator unchanged will fail. Do not globally relax authored appearance shape identities just to accept these UI assets: add a separately typed, bounded UI texture adapter that accepts the exact verified template namespace.

## Bounded data-only adapter proposal

1. Add a versioned portrait `source` contract with safe relative paths and hashes for image data, explicit retail layout template, and logical resource ownership. Do not accept package-provided APT, executable actions, arbitrary BIG replacements, native IDs, or destination paths. Keep portrait resources independent of appearance/rig donors.
2. First implement **large selector + result portraits only**, preserving reviewed original APT/CONST/O and SHPX directory names, root controls, attachment structure, dimensions and UVs. Replace only validated pixel payloads (and palettes if applicable). Require exact template hashes and explicit2/3/4-player coverage. A first authored image may be cropped into the existing tile layout offline; that crop policy needs visual acceptance. Do not assume p_CF uses one whole image: the sample has multiple tiles of different sizes.
3. Generate the six portrait BIGs per selection from runtime-owned paths above and compose through Archive, rejecting occupied destinations and case-insensitive collisions. Preserve blank custom result logos. Cache fingerprint includes portrait source hashes, layout template hash, adapter version, binding ledger and verified language base. Add a validated portraits map beside `appearances`; retain donor fallback only when explicitly requested, and report which consumers remain borrowed.
4. Small grid icons require a separate step. Editing the shared donor texture changes retail fighters too. Keep getID semantic, allocate movie-local custom artwork/frame states using typed APT/O/SHPX composition, then map getThumbID only to those owned frames. The existing bounded action cloning is useful infrastructure, but it does not itself append drawable frames, images or geometry. Until that registration is implemented, explicitly retain/report donor grid icons rather than claim complete portrait support.
5. Offline checks should verify source hashes/budgets, RefPack/BIG envelopes, exact renamed members, SHPX dimensions/format/pixel ranges, unchanged opaque controls, ownership conflicts, and stable identity under install order/removal. Native acceptance then separately checks selector large portraits and grid normal/selected/deselected states for2/3/4 participants, match-summary portraits/logos, retail artwork unchanged, and language composition. No such new acceptance was run in this audit.

## Verified limits / open points

- `portrait` is one semantic component today, but selector portrait, small grid and result portrait use different physical assets and key/state conventions. They cannot be treated as one interchangeable native slot.
- No universal shared `icon/profile/win/menu` mapping was verified. Match-summary artwork is established; Story profile portraits, win-specific art/cinematics, l_CF logos, legacy `screens/portrait/<number>_<N>p.big`, and created-fighter generated render targets need explicit consumer evidence before being included in this adapter.
- The safe first patch can deliver authored large selector/result artwork without touching guest functions or the native model loader. Complete custom grid registration remains additional typed data work. Model registration alone must not be reported as portrait acceptance.

## Follow-up: exact Choose Fighter grid registration

Additional bounded read of the original chooseF2/3/4 APT/CONST/O/SHPX. No implementation, build, game run or exported assets. All APT offsets below are file-relative; O offsets are **.data-relative** and must not be mixed with APT positions.

### The exported drawable is thumbAll

| Original movie | Movie root | Character count / pointer table | thumbAll character / Sprite record | thumbAll frame array |
| --- | --- | --- | --- | --- |
|chooseF2|0x814|429 / 0x160|303 / 0x1FF8|0x2B78|
|chooseF3|0x884|432 / 0x1C4|306 / 0x20A4|0x2C64|
|chooseF4|0x8E8|432 / 0x228|305 / 0x20FC|0x2D00|

All three thumbAll sprites contain **300 frames**. The APT prefix export directory contains a `thumbAll` name-to-character-ID entry (export count u32 at file+8; entries begin file+0xC and are8-byte string-offset/character-ID pairs). Existing `CThumbGrid.redraw()` attaches that exported movie to each grid cell. The597-frame sprites seen elsewhere are unrelated animation timelines; they are not the thumbnail bank.

Native frame expressions, independently read in all three original movies:

- `selectChar`: `artworkID + 1`.
- `redraw` and `deselectChar`: `artworkID + CHAR_SELECTED_OFFSET`, with `CHAR_SELECTED_OFFSET = 150`.

There are **two drawable states**, not three: deselection returns to the same ordinary state used by redraw. The symbol's wording should not obscure the actual expressions. Existing getThumbID redirection already covers these visual consumers while retaining semantic getID. Every sampled explicit drawable frame has a Stop/End action.

An owned presentation token S>=300 can therefore use sparse added frames **S+1 and S+150**, leaving original frames1..300 unchanged. For S=300 these are301 and450; the sprite needs450 frames, with empty intermediate frame headers where no artwork is assigned. This is a proposed allocator domain, independent of selection keys: do not globally set `CHAR_SELECTED_OFFSET` differently or use logical fighter keys as raw frames. Multiple custom tokens need collision checks for both state-frame sets (e.g. a token149 apart would overlap another token's other state). Preserve created-fighter identities and their existing frame300.

### One concrete donor drawable chain

For donor artwork token0, selected frame1 and ordinary frame150 resolve as follows:

| Movie | Frame1 Shape character / APT offset | Frame150 Shape character / APT offset |
| --- | --- | --- |
|chooseF2|2 / 0x85C|153 / 0x1430|
|chooseF3|4 / 0x8FC|156 / 0x14DC|
|chooseF4|4 / 0x960|155 / 0x1534|

These are Shape type1 records, signature0x09876543, four float bounds at+8..+0x14 and numeric geometry/model ID at+0x18. The geometry ID equals the listed Shape character ID in these samples. Shape size is28 bytes. Image type7 records have the same signature and a numeric image ID at+8 (12 bytes total). In chooseF2, selected Shape2 follows Image1 at0x850 (image ID1); ordinary Shape153 follows Image152 at0x1424 (image ID152). These are distinct retail images, so preserving exact retail visual treatment does not mean overwriting both with one texture.

For a custom single64x64 bitmap, a bounded initial adapter can explicitly use the **same new Shape/Image** in both states; the state frames remain separate. It would not reproduce retail state shading differences automatically. If separate selected/ordinary image treatment is required, author two images or introduce an explicitly verified color-transform policy instead of implying one image supplies the original two appearances.

ChooseF2 thumbAll frame1 header is0x2B78, its two-item pointer list0x6F9C points to Action0x7DD8 and PlaceObject0x7DE0; frame150 header0x3020, list0x7220 points to Action0x9380 and PlaceObject0x9388. Action is an8-byte kind1/instruction-offset record. The sampled PlaceObject occupies64 bytes including kind3: flags at+4, depth+8, character ID+0xC, matrix at+0x10, followed by color/ratio/name/clip fields. Frame1 uses flags6, depth1 and identity matrix; frame150 flags3 inherits the matrix from prior state. **New isolated state frames should clone the self-contained flags6/identity placement**, not depend on inheriting an arbitrary prior matrix. They can reuse the original immutable Stop/End action pointer after verifying it, or append an owned identical stop action.

The frame array is8-byte `(item_count,item_pointer_list_offset)` records; each item pointer list consists of u32 absolute APT file offsets. Sprite+8 is frame count and+0xC is frame-array offset. Movie root+0x14 is character count and+0x18 is character-pointer-array offset. An append-only composer can copy the old arrays into larger appended arrays, retain all old pointers, add Image/Shape pointers and frame headers, and update only these typed header fields. Existing character IDs and exported thumbAll character ID stay unchanged. No arbitrary search/replace of integer values is required or appropriate.

### O model/material chain and what cannot be reused unchanged

The original chooseF2 O has197 `__Model` exports (matching197 APT Shape records),184 Image records/SHPX entries,206 `__RM` exports and206 `__VB` exports. The section order is `null,.data,.rel.data,.shstrtab,.symtab,.strtab`, with local section symbols for multiple sections. `fighter_elf.Model` rejects this layout; `fighter_geometry.Geometry` additionally requires exactly one inline model and appearance-specific vertex layouts. The existing appearance compiler therefore cannot directly clone this UI drawable.

For selected Shape2, own-O evidence establishes:

- `__Model:::2` export at.data+0xF7C8; its inline root includes name pointer at root+0xB4 ->0xF6A8 (`2`), material-name array pointer root+0xA0 ->0xF6AC ->0xF6AA (`1`), and render-group pointer root+0xCC ->0xF69C.
- `__BBOX:::2` at0xF680; `__RM:::__GP_RM_2_0` at0xF5EC; `__VB:::__GPvb_9_0_2` at0xF4F0.
- The RM's texture import relocation at0xF634 (RM+0x48), and another at0xF784, reference the **same TAR import** containing `UID=2644;SHAPENAME=1,1;` with clampU/V controls. That numeric1 links to APT Image ID1 and SHPX raw name `1   `. O model ID2 is not texture ID2.
- A bounded donor template span **[0xF450,0xF898)** (1096 bytes) covers the observed linked structures through the0xD0-byte inline root. It has42 relocation sites and exactly the four exports above. All local relocation targets from this span stay inside it; there are no incoming local relocations from outside it. Imported shader/parent/matrix/color/GeoPrimState/TAR references remain external dependencies. Export size4 alone is not the complete drawable's size.

This is strong evidence for a **hash-pinned UI template clone**, rather than a need to decode/rebuild arbitrary UI meshes before the first thumbnail. A dedicated composer can append this exact known span, copy its42 relocation records with offsets rebased, rebase local .data addends, and append/rebind the four owned exports. It must change the cloned internal model-name string, cloned material-name string, and both TAR relocation bindings to the owned new image ID; allocate fresh runtime allocation identities where required. Longer numeric names need separately appended terminated strings and adjusted cloned pointer sites, since in-place substitution can overwrite neighboring data. Preserve existing imports/exports, original geometry bytes and original relocation indices; append new symbols/strings and update section offsets/counts/links consistently.

The TAR import's complete typed string, not a four-byte global replacement, owns SHAPENAME. Reusing the old TAR symbol would keep drawing the retail donor texture. Renaming a movie basename or only appending an SHPX entry does not register drawable geometry. Similarly, reusing `__Model:::2` for custom artwork changes the shared donor consumer. The1096-byte closure is verified for chooseF2's particular Shape2 only; derive and pin corresponding template closures for chooseF3/4 before using their differing numeric IDs/layouts. No claim of a generalized arbitrary-O geometry schema follows.

### Minimum next implementation and verification

For each movie: append one owned64x64 UI SHPX image entry (bounded numeric ID and exact template controls), one Image record, one cloned Shape record with owned model ID, the pinned O template closure with matching model/material/TAR identities, and two self-contained thumbnail state frames. Grow/repoint the movie character array and thumbAll frame array; update the existing getThumbID map to an owned presentation token. Pixel-only portrait template replacement and whole-O name rewriting are insufficient for this addition.

Offline verification should reparse all three modified movie graphs, require unchanged original frame/character/export mappings and old SHPX pixels, validate new frame IDs and every added pointer/relocation, resolve new Shape -> O Model -> TAR SHAPENAME -> Image/SHPX identity, and reject collisions. Native review still needs first draw, cursor selection, deselection, scrolling/redraw and2/3/4-player views with original fighters alongside custom ones. No such modified assets or native acceptance were produced by this read-only follow-up.
