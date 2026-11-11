# Fighter Mod Support: runtime authoring contract

Experimental ordinary-format support is available in **v1.2.0-beta.1**;
the original **v0.15.0** target is historical. Ordinary Fighter ZIP installation,
whole-pack activation, native menus and managed profile persistence are implemented.
This is the runtime contract reference. The beginner-first creator guide lives in
`DefJam-Modding-Tools/docs/fighter-modding-guide.md`; offline creator commands are
maintained in that repository. The owner authorized source-only PR publication
on November 8; converted packs and assets remain local. See the
[review notes](fighter-mod-review-notes.md) for base-game/resource/save effects,
known limits, and the [integration checkpoint](research/fighter-mod-main-integration-2026-11-08.md)
for current-main source/build and outstanding acceptance.

The Workshop companion adds a development `caf` resource, format `caf-fighter-1`:
a hash-bound fighter-only recipe, original retail style combinations and optional
PNG-derived native portraits. It uses this same ZIP and installation workflow
without importing a Story container.

There is one recipe schema. The stats, styles, appearance values and colours are
required; everything else is an optional section: retail finisher overrides and
hash-bound native atlases, up to three outfits under one fighter identity (each
with its own portrait, atlases and face sculpt, shown through the original
clothing selector), a retail moveset, and a voice donor. A recipe that omits a
section behaves as it did before the section existed. See the
[outfit contract](research/workshop-caf-outfits-2026-11-09.md) and the [CAF
contract and native acceptance](research/workshop-caf-export-2026-11-08.md) for
validated fields, current composition limits and platform qualifications.

The compiler writes all CAF data to one file, `fighter-caf.bin`, and the launcher
hands the game that file and its SHA-256 (`RECOMP_FIGHTER_CAF`,
`RECOMP_FIGHTER_CAF_SHA256`). It is a 64-byte header followed by three sections
that must tile the file exactly: recipe rows, finisher and atlas extras, and face
sculpts. Every offset and width is defined once in `setup/fighter_caf_layout.py`;
`scripts/gen-fighter-caf-layout.py` writes the C header the game reads, and a unit
test fails if the two differ.

CAF is **not in v1.2.0-beta.1**. On the development branches, CAF fighters can
compile alongside independent packs with owned appearance, voice, AI, motion and
cinematic resources. Each CAF uses retail behavior and voice donors, its
recipe-built appearance and optional sourced portraits; giving the CAF itself an
owned appearance or Blazin' resource is refused. Mixed pack gameplay, Rematch
and cleanup need qualification with actual CAF packs before this development
feature can ship.

## Package shape and identity

The development helper (after Beta 1) reuses a locally verified composition when the enabled pack
bytes, original game inputs, compiler policy, language and identity ledger are
unchanged. This includes the composed menu artwork. The first preparation after
an input or compiler change still runs the complete compiler. Every preparation
checks the installed files and cached output bytes; file timestamps do not grant
reuse. Pack authors do not ship caches or authentication keys. A damaged cache
refuses launch rather than silently accepting its files. Removing its complete
generated cache directory allows the normal compiler to reconstruct it; retain
the installed pack and profile Store.

The development Workshop retail studio can import original/owned appearance
resources independently of the combat donor. It uses this ordinary package
contract and the complete native compiler. The typed `eagl-appearance-png-1`
extension adds hash-bound native/2×/4× RGB atlas PNGs with exact original material
alpha, scoped texture names and a verified HD layer. See the
[retail authoring contract](research/workshop-retail-fighters-2026-11-09.md).

A package is one ZIP root folder named after its pack ID. It contains
`fighters.json`, its declared resource files and optional root README/LICENSE
`.md` or `.txt` files. No save, executable, opaque shared database or undeclared
asset is accepted. File extensions alone never establish format validity.

```json
{
  "schema": "fighter-registry-draft-1",
  "id": "example-roster", "version": "1.0.0",
  "requires": {}, "resources": [],
  "fighters": [
    {"id": "river", "name": "River", "inherits": "retail/ludacris", "components": {}},
    {"id": "stone", "name": "Stone", "inherits": "retail/ludacris", "components": {"stats": {"speed": 70}}}
  ],
  "overrides": []
}
```

This complete starter adds two identities using retail assets from the player's
own dump. Remove one fighter for a single-fighter pack. It is not a conversion
of an external fighter's appearance or behavior.

Root fields are exact. IDs use lowercase letters/digits separated by single
hyphens; the semantic resolver permits 80 characters per part, while creator
commands conservatively use 63 for launcher folder compatibility. `retail` is
reserved. Versions are canonical nonnegative `major.minor.patch`, without
ranges/prereleases. `requires` maps other pack IDs to exact versions.

Each fighter requires `id`, `name`, `components`, with optional `inherits`.
Use `pack-id/local-id` references. Names may change while IDs remain stable;
transient selection/core indexes are never permanent identities. Native names
currently require ASCII and fit the 96-character authoring bound.
Inheritance copies the donor's authored components before overrides. Partial
stats merge with inherited stats. Native compilation requires complete health,
speed, toughness and charisma, each an integer 0–100, plus the required resource
bundle. All pack dependencies must be present for combined validation/activation.
`tier` is a separate inline integer category, inherited like other components.
Its only accepted values are1,2,4,8. Native `Character.Tier` orders unlocked
roster categories; it is not a combat stat or a combinable bitmask. Conflicting
tier overrides require an explicit compatibility choice.

## Resources and file descriptors

Resource fields are `id`, `kind`, `compatibility`, plus `source` for an authored
resource. Component references and resource kinds are not always the same:

| Fighter component | Resource kind | Exact compatibility keys | Source format |
|---|---|---|---|
| appearance | appearance | skeleton | eagl-appearance-1 / 2 |
| moveset | moveset | skeleton, events | fighter-moveset-1 |
| voice | voice | events | fighter-voice-1 / 2 / 3 / 4 |
| ai | ai | none | fighter-ai-1 |
| portrait | portrait | none | eagl-portrait-1 / 2 / 3 |
| intro, victory | cinematic | skeleton, events | fighter-cinematic-1 / 2 |
| blazin | blazin | skeleton, events | fighter-blazin-1 / 2 / 3 / 4 / 5 |

Compatibility values are stable keys such as `retail/binding-ludacris`, exported
by the verified retail catalog. They are checked against actual rig/template
relationships during compilation; changing a label cannot adapt incompatible
assets. An empty compatibility map is `{}`. Stats are inline, not a resource.

Every ordinary file descriptor is exactly `{"path":"assets/file.ext","sha256":"..."}`,
with a real 64-character lowercase SHA-256. Paths are relative, portable, and
must remain inside the package. Links, traversal, duplicate/case-colliding paths,
missing files and mismatched hashes are rejected. Reused files must have the
same digest in every descriptor. Documentation is UTF-8 and bounded at 1 MiB.
Voice2/3/4 audio descriptors additionally require `format: "wav-pcm16"` or
`format: "ea-adpcm-r2"`; this is a validated codec choice, not a file extension.
Current inventory bounds: 65,536 files, 512 MiB total, 64 MiB per asset;
individual format/aggregate composition budgets are often tighter.
Manifests are bounded at 8 MiB each and 32 MiB combined. Resolver limits are
1,024 packs, 16,384 total definitions including baseline, inheritance depth 128.
These are processing limits, not platform memory guarantees.

## Source fields and current admission limits

All field lists below are exact unless marked optional. `format` is always
required. File arguments mean hash-checked descriptors, not unverified paths.

- **Appearance:** `format`, `donor`, `model`, `textures`, `face`. Three distinct
  files; raw or supported RefPack data. Models are data-only EAGL ELF, textures
  are native SHPX. The validator checks geometry, skinning, texture references,
  render layouts, skeleton topology/names/order and the established permutation.
  Accepted geometry is rebuilt into trusted render templates. Faces may reuse the verified donor or supply bounded PosePaletteBank data,
  rebuilt from typed samples/destinations into a trusted donor envelope. The
  current two-palette profile needs at least 13/15 sample frames, finite active
  values, unit quaternions and destinations within the matched body rig. This
  local adapter has one partial native component test; full legacy conversion
  is still in progress. A Blender/GLB file is not an accepted native model.
  `eagl-appearance-2` adds an explicit `shape_names` mapping of old to new
  four-character texture identities. It changes only parsed TAR imports, counted
  model shape keys and SHPX directory/material names. Vertex/pixel payloads stay
  intact. Use this declared namespace when reusing original textures with an
  authored model would otherwise conflict; version1 never silently repairs it.
- **Portrait:** `format`, `donor`, `selector_2p`, `selector_3p`, `selector_4p`,
  `result_2p`, `result_3p`, `result_4p`. Six distinct SHPX files must match the
  donor layout/dimensions. Current aggregate input is 16 MiB per resource.
  The runtime owns menu expansion; whole selector/result movie replacement is
  not an authoring interface. PNG artwork needs a native exporter first.
  `eagl-portrait-2` adds twelve mandatory files: `selector_logo_Np`,
  `result_logo_Np`, `loading_Np`, `loading_logo_Np`, each for N=2,3,4. These use
  the same verified-layout/pixels-only contract. Authored logos replace generated
  name fields for their identities; other fighters retain text names. Loading
  aliases use appended logical IDs>=100, outside the verified retail reversed
  portrait list (maximum82). No reversed variant is inferred from arbitrary IDs.
  `eagl-portrait-3` adds six mandatory pixel sources: `grid_normal_Np` and
  `grid_selected_Np`, N=2,3,4. Each is a canonical single-image SHPX, ID1,
  matching the verified original selected-grid texture. The compiler supplies
  original grid geometry and fresh Stop/placement frames. Normal/selected images
  remain independent; source APT actions, ELF models and texture controls are
  never copied into the runtime generation. Versions1/2 keep derived thumbnails.
- **Moveset:** `format`, `donor`, `selections`, `tracks`. At least one authored
  selection or track. `selections` has at most 124 canonical string ordinal keys
  0–124 mapping to integers 1–124. Composition further rejects special actions,
  self-selections, incompatible flags, aliases and ambiguous motion intervals;
  supported ordinary families have one or two motion entries in the same donor
  bank. `tracks` maps at most 999 native ASCII tokens (letters/digits/underscore,
  1–64 characters) to quaternion files. Global WPAR/WAZA/FZUI replacement is not
  exposed. Root motion/events remain template-owned.
- **Voice:** `format`, `template_voice`, `samples`, `intro`, `extro`.
  `template_voice` is an integer 0–65534, further checked against the template.
  `samples` maps optional `Character`, `Taunts`, `Enviro` categories to canonical
  string slot ordinals 0–254 and WAV descriptors; actual template slot counts
  apply. Missing overrides inherit template clips. Intro/extro are mandatory.
  WAV input is mono signed PCM16, 8,000–48,000Hz, at most 4,000,000 samples per
  encoded stream. The runtime encodes its own native bank/stream output.
  Version2 keeps those fields and accepts explicitly typed WAV or bounded mono
  revision3/ADPCM R2 descriptors, preserving original R2 coded blocks.
  Version3 instead has `format`, `banks`, `intro`, `extro`. `banks` contains
  exactly the three categories; each has `template_voice`, `family`, `samples`.
  Families are Character0/1, Taunts16625/16626, Enviro40962/40963. Templates are
  verified separately per category; all other event metadata stays template-owned.
  Version4 keeps `format`, `banks`, `intro`, `extro` and requires an explicit
  `state` for every category. A present bank has exactly `state: "present"`,
  `template_voice`, `family`, `samples`. An absent category is exactly
  `{"state":"absent"}`. Missing keys, mixed implicit/explicit declarations and
  data attached to an absent category are errors. Intro/extro remain mandatory.
  The compiler emits no HDR/DAT for absent categories. FVA2 binds each owned
  core/voice ID to Character/Taunts/Enviro bits0/1/2; FVA1 remains all-present.
  Shared voice IDs must have the same mask, including zero. Hash-checked receipts
  validate archive members against each declaration before emission.
  Absence omits this owned bank; native event alternatives and family-only
  requests can still select another intentionally referenced registered bank.
  The declared events namespace must match the moveset; family alternatives
  are not an automatic donor fallback.
- **AI:** `format`, `template_profile`, `tendencies`. Template basename is 1–31
  ASCII letters/digits/underscore/hyphen. Tendencies must contain `easy`,
  `normal`, `hard`, each with slots `0`, `1`, `2`, `3`. Each slot has at least
  one named integer1–5 edit from `fighter_ai.EDITABLE`; stage programs remain
  inherited. `Specification_environment` is not editable. No raw AI XML input.
- **Cinematic:** `format`, `template`, `track`. Template names match `CI_XXXX`
  or `CE_XXXX` (four alphanumerics), but only verified simple plans compose.
  Track is quaternion data. The intro/victory component determines its use;
  both resource kinds are `cinematic`.
  Version2 instead requires `format`, `template`, `graph`, `tags`. Graph is a
  file descriptor for `fighter-cinematic-graph-1`: exact rig identity/count,
  intro or single-camera layout and every body/root/face/hand/camera role.
  Numeric18/20/21 leaves preserve blocks, constants and time grids; empty parents
  are explicit. Tags are a descriptor for a typed timeline or exactly
  `{state: "absent"}`. Closed intro/victory/activation payload profiles prohibit
  arbitrary callbacks. FCP1 seals every fresh member before construction and
  actual A1FA0 binding joins the loaded body/face/hands and selected camera banks
  to the participant's initialized rig. Camera output is bounded to256bytes;
  cinematics use their verified own-body rig, not an opponent wildcard.
- **Blazin:** `format`, `shots`, optionally `pairs`. Four shot objects in native
  order, each with `template` and optional quaternion `track`. Template forms
  are `BT1_nn`, `BT2_nn`, `BT3_nn`, `BT4Cnn`, checked per phase and ownership.
  Optional pairs map 1–4 canonical finisher-choice ordinals 0–81 to objects with
  both `subject` and `counterpart` quaternion files; actual inherited choices,
  rigs and timing must match. Camera/event graphs remain template-owned.
  Version2 has exactly `format`, `shots`, `slots`, with the same shot rules.
  `slots` maps 1–4 canonical string slot ordinals0–3 to `template_choice`
  (integer0–81), `subject`, `counterpart`. It can change the selected verified
  behavior independently for each slot. Native FMC3 proof permits only these
  four choice fields plus independently proved ordinary action edits. FBP2 binds
  core/slot/template to owned paired motions, distinguishing duplicate templates.
  Omitted slots inherit; `pairs` and `slots` cannot be combined in one source.
  Version3 keeps the version2 field list and shot rules, but each slot's
  `subject`/`counterpart` file is `fighter-motion-graph-1`. This explicit profile
  preserves five coordinated body/root/rotation-helper/face/hand tracks, including
  their individual time grids and palette references. It supports the observed
  type18/type20 independent seeds, timed type13 helper and ordered type25 palette
  selections. Bounds and actual compiled appearance joins are checked. The
  compiler emits FBP3 relocation/output proofs; packages cannot supply those
  native tables. FBP1/2 retain their type11-only native guard. Source3 still
  explicitly inherits the behavior template's camera AND animation-tag timelines;
  matching combat records alone does not establish legacy source timeline fidelity.
  Version4 retains four shot rules and adds `subject_tags`, `counterpart_tags`
  and `camera` to each slot. The first two are hash-checked JSON descriptors;
  camera is exactly `{template, timeline}`, with a verified original timetable
  name and a JSON descriptor. Tag/camera documents use
  `fighter-tag-timeline-1` / `fighter-camera-timeline-1`, each with `events` rows
  `{tick, template}` referencing complete verified payloads. Tags retain the
  selected behavior's payload sequence; cameras retain non-shake sequence and
  may select verified shake events. FBP4 and FTE1 couple both native lookups.
  Tick ranges are tags0–32767 / cameras0–65535; simultaneous tag ticks are valid,
  camera ticks strictly increase. Event clocks are independent of curve keys.
  Native snapshot names are generation-owned, so cached snapshots do not borrow
  per-match metadata. Versions1–3 retain their original inheritance behavior.
  Version5 keeps version4 pairs/timelines and uses four complete cinematic shot
  objects `{template, graph, tags, camera_policy}`. Owned slots may be empty;
  omitted choices inherit, while `retail_slots` can name other exact originals.
  Policies are `owned-relative` for
  phases0–2. Phase3 accepts `native-venue` or `owned-absolute`; the latter uses
  the supplied camera graph while retaining native absolute-coordinate flag8.
  Vendetta conversion uses `owned-absolute`, following the pinned legacy runtime
  reference identified in the current M5 checkpoint.
  Optional `retail_slots` maps canonical slot0–3 strings to verified original
  choices0–81. It is disjoint from owned `slots` and changes the selected choice
  without duplicating its exact original animation. Omitted slots inherit.
  A source's retail choices can differ from its ordinary-combat donor: the
  converter must preserve these explicitly rather than assume inheritance.
  Compiler-owned FIC2/FBZ2/FBZ3 bindings mark full-graph roles and require the complete
  body/face/hand/camera proof set before native loading. Legacy bindings retain
  their original guards; omitting a full-graph proof is not a legacy fallback.

- **Explicit global tag edit:** resource kind `tag-override`, empty compatibility,
  source `fighter-tag-override-1` with `target`, `original_sha256`, `template`,
  `timeline`. The original target row must hash exactly; the typed replacement
  retains the declared verified donor's full payload sequence. It may change
  ordinary motions using that label. Conflicting edits identify both resources;
  no last-pack-wins behavior. This is a declared data adapter, not raw TAGS input.

Use installed `defjam-tools fighter pair` with explicit `--recomp`, `--game`,
`--model`, `--face`, `--subject-data`, `--subject-links`, `--counterpart-data`,
`--counterpart-links`, `--template-choice` and a new `--out` folder. The runtime
matches opaque controls to the verified template, rebuilds both roles and seals
input hashes before the tool publishes typed files. Copy `subject.json` and
`counterpart.json` into the pack, adjusting the two relative paths in
`pair-source.json` when assigning it to a version3 slot. Keep `pair-export.json`
outside the package. Full validation still joins the actual appearance and all
opponents. Component export is not a native playtest or a complete legacy import.

Quaternion files have exactly `schema: "fighter-quaternions-1"`, `rig_sha256`,
`bone_count`, `poses`. Every pose contains a complete bone-ordinal list of
`[x,y,z,w]` unit quaternions; finite values, consistent adjacent hemispheres,
verified rig digest and template time layout are required. Bounds: 1–4096 bones,
1–65535 poses, at most 4,194,304 scalar values. These inputs do not contain
arbitrary frame times, translations, event code or native dispatch words.
Behavior input is bounded at 64 MiB per file and 256 MiB combined.

The executable authorities are `setup/fighter_registry.py`,
`fighter_resource_files.py`, `fighter_behavior_files.py` and their native
composers. Successful schema validation alone does not prove native admission.

## Runtime authoring API and creator commands

The matching Modding Tools checkout provides:

```powershell
defjam-tools fighter catalog --recomp RECOMP --game GAME
defjam-tools fighter new --recomp RECOMP --game GAME --out NEW_FOLDER --id example-roster --donor retail/ludacris --fighter 'river=River'
defjam-tools fighter validate PACK_FOLDER --recomp RECOMP --game GAME
defjam-tools fighter package PACK_FOLDER --recomp RECOMP --game GAME --out NEW_ZIP
defjam-tools fighter voice --recomp RECOMP --game GAME --bank Character=SOURCE.hdr --absent Taunts --absent Enviro --intro INTRO.asf --extro EXTRO.asf --out NEW_WORK_FOLDER
```

Repeat `--fighter` for multiple fighters. Repeat `--with-pack` for dependencies
or coexistence validation; `--language` selects a language pack folder for native
screen composition. Only the primary folder is packaged; dependencies remain
separate archives. Starter/output destinations must be new.

The read-only bridge `scripts/fighter-contract.py` exposes JSON protocol
`fighter-authoring-api-1`, with `catalog --game GAME` and
`validate --game GAME --pack FOLDER [--pack FOLDER ...] [--language FOLDER]`.
It uses the same inventory, full native compiler and portrait/menu composer as
the runtime, in temporary caches, without installing packs or changing profiles.
The success receipt identifies every validated file by SHA-256 and explicitly
sets `native_playtest: false`. Errors return nonzero with an error report.
The packager rereads exactly those files and refuses changes, writes a stable
ZIP, verifies CRC readback and exclusively creates its output. It does not
accept a bypass-validation switch or a manually supplied success receipt.

`fighter voice` matches normalized legacy category event metadata against
`voice-catalog` from this same API. The catalog contains only templates accepted
by the verified compiler. The exporter preserves exact bounded R2 streams,
logical entry ordinals and explicit family assignments. It writes an authoring
source fragment, audio files and an accounting report. Before publishing the
work folder, `validate-voice --voice-source FILE --game GAME` compiles the staged
source through the shared Reader/compiler/binding encoder. It pins source and
audio hashes through compilation and enforces the actual R2 and native-bank
budgets. This does not install or validate a complete fighter. Copy the fragment into a voice resource and its
audio directory into the pack, leaving reports outside, then validate/package.

Diagnostic `scripts/fighter-registry.py` commands remain available:
`export-retail`, `inspect-native`, `inspect-model`, `inspect-skin`,
`inspect-geometry`, `inspect-textures`, `inspect-motion-index`,
`inspect-motion-record`, `inspect-animation-envelope`, `resolve-preview`,
`compile-native-preview`, `suggest-compatibility`. Use each command's `--help`.
An inspection or semantic preview is not full package acceptance.

## Conflicts, installation and testing

### Existing retail appearance and additional outfits

An appearance-only retail replacement uses an ordinary `overrides` entry with
the existing `retail/NAME` target. It edits that record and preserves the retail
combat core and roster identity. Owned texture shape namespaces prevent the
imported atlas from replacing another fighter's shared texture accidentally.
The current retail UI-art replacement ownership guard remains in force.

A selectable extra outfit uses a normal fighter definition plus `outfit_of`:

```json
{
  "id": "red-pants",
  "name": "Red pants",
  "inherits": "retail/pockets",
  "outfit_of": "retail/pockets",
  "components": {"appearance": "example-pack/red-pants"}
}
```

Declare the referenced appearance resource in the pack as usual. The target
must be an original retail fighter. All components except appearance/portrait
must resolve identically to the parent. The compiler adds a hidden native
appearance binding and extends the original clothing selector, retaining one
public retail cell. Original and added outfits together must not exceed three.
Use the matching runtime with FWR2 support. Progress, loading and results keep
the retail identity; the selected battle appearance uses the owned resource.
The selector portrait is separate artwork and does not change merely because
the body atlas changes. See [native evidence and limits](research/retail-overrides-outfits.md).

### Conflicting component claims

An override has `target`, `components`, `supersedes`. Incompatible claims to
the same fighter/component fail; stats form one conflict group. A compatibility
pack explicitly depends on the competing versions and selects a reviewed result.
`suggest-compatibility` helps construct that declaration; it cannot repair a rig
or interpret unsupported native data. No implicit load-order winner is used.

Install the generated ZIP in **Mods > Fighters**, then enable the whole pack.
The launcher revalidates installation, activation, update, rollback and launch.
[Launcher/profile behavior](fighter-mod-support.md#local-m4-launcher-workflow)
includes stable identity persistence and dormant missing content. Pack contents
never supply native save files. Logical roster IDs can exceed 255 through the
four-participant binding window; the 16,380 window-record bound is not a promise
that every size of fully authored roster fits memory.

Playtest native 2/3/4-player selection/results, cancel/ready paths, human and CPU
roles, entrance/combat/victory/Blazin, voices, repeated matches and Story-created
fighters using a disposable test profile. Check combined language/texture packs.
Record compilation and actual native acceptance separately. M1–M4 Windows
fixtures have native evidence; newly generated starter ZIPs are not automatically
claimed as a new native playtest. Platform/release acceptance remains M6.

## Legacy conversion status

The original Vendetta archive is not an ordinary Fighter ZIP. Current direct
inspection finds 46 added characters and no changes to the 75 existing SOD
character records. All 46 appearances now compile through the bounded facial
palette adapter, individually and together. Actual offline rig/face/hand identity
and sample-bound joins cover46rebuilt appearances and75retail normal opponents.
Broader native facial acceptance and dynamic created-fighter contexts remain open.

Its 46 mapped action tables are identical to their retail donors (5,980 action
rows), and all three unpacked parts of their ordinary combat banks are exactly
equal to the mapped retail donors. All 47 added finisher behaviors match retail
templates, but their 94 paired animation banks contain different curves.
Per-slot binding is implemented;94full typed motion/root/helper banks rebuild
against their actual47matched behaviors and pass ordinary package admission.
Representative paired/cinematic native proofs pass; whole-pack and broader
mode/platform acceptance remain incomplete. All 129 speech banks
can preserve their event metadata through version3 templates/families; missing
categories now have an explicit version4 omission contract and template-matched
exporter; native missing-category acceptance remains separate. A faithful converter must account
for these data, facial poses,
voices, portraits, AI and cinematic links; it cannot silently substitute donor
assets or copy whole shared databases. Offline full-component source accounting
now covers1697converted,184exactly inherited and2excluded files. Two dangling
nonfighter XML registrations are separately excluded and reported. A local
ordinary46fighter candidate exists. The additional legacy runtime reference
establishes owned absolute phase4 cameras; native and wider acceptance remain
separate gates before declaring complete faithful acceptance.
See the [current M5 checkpoint](research/fighter-mod-m5-2026-11-08.md).
