# Fighter grid: external movie option — 2026-11-04

Bounded read-only audit of the user's original `game/screens/screens.viv`, using `fighter_archive.Archive`, `fighter_assets.unpack`, `fighter_apt.parse_const/parse_character/read_characters_list/disassemble_block` and `fighter_menu.functions`. No implementation, builds, game runs, external implementation, or exported game bytes. This document is the only output.

## Finding

An external movie per custom cell is a credible, substantially smaller alternative to cloning UI ELF geometry. Original APT already dynamically creates clips and loads external movies into clips. The existing pixel-only result movie is especially suitable: one Shape, one Image, one identity placement, no root action. This establishes an original-player feature and an asset-compatible proposal; it does **not** prove native acceptance, load completion ordering, or cancellation behavior. Do not claim it is equally proven as the ordinary `thumbAll` frame route until the focused native trial below passes.

The safe first version can use one static image for both ordinary/selected states and retain the original player-colored `hiliteClip`. Original thumb artwork has two distinct frame treatments; a result movie does not acquire them merely by loading.

## Exact original methods and fields

APT file offsets, function body sizes in bytes:

| movie | constructor | redraw | deselectChar | selectChar |
|---|---|---|---|---|
| chooseF2 | 0xE4C8 | 0x11F5C / 668 | 0x1278C / 126 | 0x1282C / 239 |
| chooseF3 | 0xE86C | 0x12300 / 668 | 0x12B30 / 126 | 0x12BD0 / 239 |
| chooseF4 | 0xEBE0 | 0x12674 / 668 | 0x12EA4 / 126 | 0x12F44 / 239 |

Constructor parameters are `iPlayer,sTargetClip,aCharacters,bHasCreatePlayer,iWidth,iHeight`. It stores `iPlayer,sTargetClip,iWidth,iHeight,bHasCreatePlayer`; initializes `iWindowTop=0`, `oCursorPos={_x:0,_y:0}`, `iNumChars=aCharacters.length` (subtract one without create-player). The constructor/methods access `aCharacters`, `thumbPos`, `depth` as variables, **not established own fields**. A wrapper must use the existing scope/map contract rather than invent `this.aCharacters`.

`redraw` resets `thumbPos` to zero. With create-player at window top zero it attaches `herothumb{player+1}` as `herothumb{player+1}Ctrl`, plus `createPlayerFrame`, consuming the first column. Otherwise it removes the hero controller. It loops `rowIndex=iWindowTop .. iWindowTop+iHeight-1`, columns to `iWidth`; `charNum=rowIndex*iWidth+colIndex`, plus one without create-player. `clipNum` increments before each cell, so cells are `thumb1`, `thumb2`, … even when first column is reserved for hero. For each cell it first `RemoveSprite(sTargetClip+'.thumbNails.thumb'+clipNum)`; if in range it attaches exported `thumbAll` with instance name `thumbN`, `depth++` and the `thumbPos` initialization object. It then adds half its `_width` and `_height` to `_x/_y` and goes to locked frame or `getID()+CHAR_SELECTED_OFFSET`. Finally it removes/re-attaches `hiliteClip` (`hilite` export) at cursor position using the next depth, and creates/sets its `Color` from `cP{player+1}`.

ChooseF2 decisive actions: remove old cell 0x12090–0x1209C; attach 0x120AC–0x120CA; centering 0x120DD–0x1210C; frame 0x12134–0x12149; hilite rebuild 0x12190–0x121F6. Other two methods have matching sizes and observed expressions.

`deselectChar`: cursor cell number is `cursorY*iWidth+cursorX`, plus one unless `(bHasCreatePlayer && iWindowTop==0)`. For an unlocked selected character, finds `sTargetClip+'.thumbNails.thumb'+clipNum` and `gotoAndStop(getID()+CHAR_SELECTED_OFFSET)`.

`selectChar`: preserves semantic `CHAR_HERO`/`iTakenBy`/`BAD_INDEX` checks, initializes `aClothIndex[iPlayer]` via first unlocked set, checks unlocked, then same cell lookup and `gotoAndStop(getID()+1)`. Always ends by calling `updateChar(iPlayer)`. A custom image wrapper must preserve these semantics and the existing large-portrait update. Merely replacing selectChar with an image loader loses behavior.

## Geometry and containment

All three movies set `kThumbXMove=kThumbYMove=39` (F2 0x11E07/0x11E0D, F3 0x121AB/0x121B1, F4 0x1251F/0x12525). Sample selected thumb Shape bounds are `(-18.5,-18.5,18.5,18.5)`: artwork extent37x37, grid pitch39. Do not scale a result movie to pitch39.

| movie | root thumbBox positions (identity linear matrix) | thumbNails within box (character, depth, translation) |
|---|---|---|
| F2 | (60,304), (329,300) | 336,6,(6,7) |
| F3 | (52,306), (232,313), (416,307) | 341,7,(5,5) |
| F4 | (48,311), (184,316), (319.5,307.5), (455,311) | 342,7,(6,5) |

`thumbNails` has identity linear transform in each case. Retain these original parent placements and local coordinates. Avoid a separate root overlay that would have to reconstruct every transform.

Original `t_MS_0_2p/3p/4p`: root at0x18; character0 Movie,1 Image,2 Shape; one frame containing white BackgroundColor and Shape2 placement flags6/depth1, identity transform and translation0,0. Shape bounds are respectively `(0,0,44,44)`, `(0,0,39,39)`, `(0,0,32,32)`. The 550x400 movie header is **not** its drawable extent. To draw37x37, content scale percentages are `100*37/44`, `100*37/39`, `100*37/32`. With origin at cell top-left, position at `(col*39,rowWithinWindow*39)`; if preserving the retail centered `thumbN` wrapper position `(col*39+18.5,row*39+18.5)`, put result content at local `(-18.5,-18.5)`. Native observation must verify BackgroundColor is not painted over the full parent and that scale survives loading. Do not infer it from the header.

## Proven original dynamic actions

The relevant `loadMovie` spelling is largely **compiled to `GetURL2`**, not a named method call. In chooseF2 `updateChar`, 0xF173–0xF1A0 builds `PORTRAIT_PATH + fighter identity/layout suffix + 'p.swf'`, resolves `portrait{nPlayer}.Pic` with GetVariable and executes GetURL2. Locked/dark variants load `.blackPic`; logo uses `.logo`. 0xF094–0xF0A1 loads `trans/empty2.swf` into `.Pic`; corresponding paths clear `.logo` and `.blackPic`. Thus clearing old presentation before changing branch already has an original convention.

Original feloader creates root `clip2` with `createEmptyMovieClip('clip2',2)` at0xCCA7–0xCCAF, `clip3` depth3 at0xCCB1–0xCCBA, `overlay` depth4 at0xCCBC–0xCCC4, and others. At0xD45C `loadMovieClip(sFileName,sTarget)` traces then pushes filename and target and executes GetURL2 at0xD466. `unLoadMovieClip(sTarget)` pushes empty string and target, GetURL2 at0xD487. A clip event at0xDC6C–0xDC7C also invokes named `this.loadMovie('trans/empty2.swf')`. Original chooseF itself proves `attachMovie` with a fourth initialization object (redraw0x120AC–0x120CA), and three-dimensional concerns are absent: it is a display-list child/depth operation.

These are executable original uses, stronger evidence than a string-table name. Native implementation dispatch internals and request cancellation were not established in this bounded audit. Since the port executes the original APT player, its existing native portrait loads are the first practical acceptance reference; no new host HLE support can be declared necessary or unnecessary from this read alone.

## Concrete runtime-owned proposal (not implemented)

1. Generate a trusted mapping `semantic selection -> authored result movie URL` using existing owned `t_MS_<selection>_<N>p.big` aliases and corresponding `portrait/t_MS/t_MS_<selection>_<N>p.swf` requests. Packages supply reviewed pixel payloads only; no APT actions or filenames. Reuse original APT/CONST/O intact through `fighter_portrait`.
2. Save the existing runtime-composed `CThumbGrid.redraw/selectChar/deselectChar` methods under private names. Wrap redraw: remove prior owned custom child containers; run original redraw; enumerate the same visible cells and semantic IDs using the exact rules above; replace only unlocked custom cells. A replacement needs its **own container**, e.g. `thumbN` empty clip at the cell's original depth, and nested `_recompGridArt` content at child depth1. Load external movie into the nested content via proven GetURL2. Keep the outer container for stable local positioning/scaling and ownership across content replacement. These private names are proposed, not original exports.
3. Do not allocate custom art as a sibling above `hiliteClip`: original redraw creates hilite last and cursor handlers move that exact child. Either replace each original cell at its captured depth or use child content inside its existing wrapper, hiding/removing the donor art through a verified mechanism. The latter must verify that changing `thumbAll` frames does not destroy its dynamic child; do not assume it. Empty outer clip replacement is the cleaner candidate if select/deselect wrappers bypass only their custom `gotoAndStop` while preserving all other work.
4. Preserve semantic selection/lock/hero handling and `updateChar`. For first version use identical static art during select/deselect; retain the original hilite as selection cue. Avoid reloading the same external movie on every hover. Separate authored two-state movies/color transforms require a separate verified contract.
5. On redraw or screen destruction remove the complete owned outer clip and all children before replacement, including cells now empty or retail. A generation/identity guard must reject late completion for an old selection/window. Distinct per-generation target names can prevent old requests painting a reused `thumbN`, but their disposal/cancellation still requires measurement. Retain explicit donor fallback while a new movie loads if desired; otherwise blank until loaded. Never let a previously loaded custom portrait remain as the new fighter's apparent image.

## Caveats and comparison

**Pros:** no new ELF schema, relocation rebasing, model/material/TAR identity allocator, APT Shape/Image appending or sparse thumbAll frame expansion; shares current hash-pinned pixel-only compiler and result aliases; confines authored content to existing safe image validation; no retail texture changes.

**Cons:** one external load per visible custom cell per redraw can multiply resource work and transient memory; asynchronous completion/blank flashes/cancellation are unproven; display-list depth, clip lifetime and transform preservation need real acceptance; static result artwork does not reproduce retail selected/ordinary shading; repeated grids may load the same movie multiple times, with unknown sharing. The frame-bank approach costs more offline typed composition but then uses the original synchronous frame switch and cleanup path.

Required trial: two custom fighters next to retail, repeat scrolling both directions quickly while loading; hover/select/deselect and taken/locked handling; empty last-row cells; leave/re-enter screen during pending loads; simultaneous2/3/4 grids; verify old portrait never paints a reused cell, original hilite stays above art, transforms37x37 align at pitch39, large/result portraits still update, retail pixels unchanged. Measure load failures and resource growth. Until those pass this is a **recommended smaller prototype**, not accepted runtime support or a replacement for the existing donor-grid disclosure.
