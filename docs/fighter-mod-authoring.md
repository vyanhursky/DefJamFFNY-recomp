# Fighter Mod Support: runtime authoring contract

Target **v0.15.0**, local development. Ordinary Fighter ZIP installation,
whole-pack activation, native menus and managed profile persistence are implemented.
This is the runtime contract reference. The beginner-first creator guide lives in
`DefJam-Modding-Tools/docs/fighter-modding-guide.md`; offline creator commands are
maintained in that repository. Neither branch has been published.

## Package shape and identity

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

## Resources and file descriptors

Resource fields are `id`, `kind`, `compatibility`, plus `source` for an authored
resource. Component references and resource kinds are not always the same:

| Fighter component | Resource kind | Exact compatibility keys | Source format |
|---|---|---|---|
| appearance | appearance | skeleton | eagl-appearance-1 |
| moveset | moveset | skeleton, events | fighter-moveset-1 |
| voice | voice | events | fighter-voice-1 / 2 / 3 |
| ai | ai | none | fighter-ai-1 |
| portrait | portrait | none | eagl-portrait-1 |
| intro, victory | cinematic | skeleton, events | fighter-cinematic-1 |
| blazin | blazin | skeleton, events | fighter-blazin-1 / 2 |

Compatibility values are stable keys such as `retail/binding-ludacris`, exported
by the verified retail catalog. They are checked against actual rig/template
relationships during compilation; changing a label cannot adapt incompatible
assets. An empty compatibility map is `{}`. Stats are inline, not a resource.

Every ordinary file descriptor is exactly `{"path":"assets/file.ext","sha256":"..."}`,
with a real 64-character lowercase SHA-256. Paths are relative, portable, and
must remain inside the package. Links, traversal, duplicate/case-colliding paths,
missing files and mismatched hashes are rejected. Reused files must have the
same digest in every descriptor. Documentation is UTF-8 and bounded at 1 MiB.
Voice2/3 audio descriptors additionally require `format: "wav-pcm16"` or
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
- **Portrait:** `format`, `donor`, `selector_2p`, `selector_3p`, `selector_4p`,
  `result_2p`, `result_3p`, `result_4p`. Six distinct SHPX files must match the
  donor layout/dimensions. Current aggregate input is 16 MiB per resource.
  The runtime owns menu expansion; whole selector/result movie replacement is
  not an authoring interface. PNG artwork needs a native exporter first.
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
  Missing entire banks are not supported. The declared events namespace must
  still match the moveset; family alternatives are not an automatic fallback.
- **AI:** `format`, `template_profile`, `tendencies`. Template basename is 1–31
  ASCII letters/digits/underscore/hyphen. Tendencies must contain `easy`,
  `normal`, `hard`, each with slots `0`, `1`, `2`, `3`. Each slot has at least
  one named integer1–5 edit from `fighter_ai.EDITABLE`; stage programs remain
  inherited. `Specification_environment` is not editable. No raw AI XML input.
- **Cinematic:** `format`, `template`, `track`. Template names match `CI_XXXX`
  or `CE_XXXX` (four alphanumerics), but only verified simple plans compose.
  Track is quaternion data. The intro/victory component determines its use;
  both resource kinds are `cinematic`.
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

Diagnostic `scripts/fighter-registry.py` commands remain available:
`export-retail`, `inspect-native`, `inspect-model`, `inspect-skin`,
`inspect-geometry`, `inspect-textures`, `inspect-motion-index`,
`inspect-motion-record`, `inspect-animation-envelope`, `resolve-preview`,
`compile-native-preview`, `suggest-compatibility`. Use each command's `--help`.
An inspection or semantic preview is not full package acceptance.

## Conflicts, installation and testing

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
palette adapter, individually and together. Full normal-combat face-context
provenance and broader native facial acceptance remain open.

Its 46 mapped action tables are identical to their retail donors (5,980 action
rows), and all three unpacked parts of their ordinary combat banks are exactly
equal to the mapped retail donors. All 47 added finisher behaviors match retail
templates, but their 94 paired animation banks contain different curves.
Per-slot binding is implemented; full typed motion/root/helper rebuilding and
native acceptance of the source animations remain pending. All 129 speech banks
can preserve their event metadata through version3 templates/families; missing
categories still require explicit accounting. A faithful converter must account
for these data, facial poses,
voices, portraits, AI and cinematic links; it cannot silently substitute donor
assets or copy whole shared databases. See [M5 investigation](research/fighter-mod-m5-2026-11-06.md).
