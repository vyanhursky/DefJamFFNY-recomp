# Fighter portrait registration audit — 2026-11-04

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
