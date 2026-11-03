# Fighter Mod Support: local authoring prototype

Target v0.15.0; local R&D. The [approved architecture](fighter-mod-support.md)
defines the intended feature. This document covers the first working definition
and conflict tools. **These drafts are not installable launcher packages.**
Internal native acceptance probes run donor-backed fighters using guarded,
isolated profiles; the production capability remains disabled. The schema
will evolve as native assets, menus and persistence are integrated.

## What the prototype checks

`setup/fighter_registry.py` resolves one or many fighters from each enabled pack,
including shared resources, exact dependencies, inheritance and component edits.
All enabled packs are resolved together. It emits a deterministic snapshot with
an explicit `runtime_ready: false` gate and a content hash.

The baseline is a locally extracted `retail` document using the same shape. The
retail namespace is reserved. Export the supported original database locally:

```powershell
python scripts/fighter-registry.py export-retail path/to/assets/djv2.sod > logs/retail-fighters.json
```

The exporter verifies the original SOD hash pinned in
`config/fighter-native-baseline.json`; modified/unsupported databases are rejected.
The output contains 75 retail definitions and 300 resource references, with no
game assets. The synthetic tests show the shape without distributing extracted
fixtures: `tests/unit/test_fighter_registry.py`.

Each document has exactly these fields:

```json
{
  "schema": "fighter-registry-draft-1",
  "id": "example-pack",
  "version": "1.0.0",
  "requires": {},
  "resources": [],
  "fighters": [
    {
      "id": "first-fighter",
      "name": "Example Fighter",
      "inherits": "retail/ludacris",
      "components": {"stats": {"health": 60}}
    },
    {
      "id": "second-fighter",
      "name": "Another Fighter",
      "inherits": "retail/ludacris",
      "components": {"stats": {"speed": 70}}
    }
  ],
  "overrides": []
}
```

This example reuses Ludacris's retail donor bundle; it supplies no new model,
animation or voice assets. Remove the second entry for a single-fighter pack.
The resulting permanent keys are
`example-pack/first-fighter` and `example-pack/second-fighter`. Display names may
match between independently keyed fighters. Never publish native IDs or record
offsets as these keys.

IDs use lowercase letters/digits separated by single hyphens, up to 80 characters
per part. Versions are stable `major.minor.patch` values; prereleases/ranges are
not implemented. Dependencies map pack ID to an exact version. Resource/fighter
references outside the current pack or retail require an explicit dependency.

Inheritance copies the authored donor before overrides. Changing the donor later
does not silently change independently authored descendants. Numeric stats merge
with inherited stats; their current draft range is integer 0–100. It is not yet
a conversion contract for native game stats.

Supported draft component names are `appearance`, `moveset`, `voice`, `ai`,
`portrait`, `intro`, `victory`, `blazin` and `stats`. Everything except stats
references a typed resource key. Resource definitions have `id`, `kind` and
`compatibility`, for example:

```json
{"id":"example-moves","kind":"moveset",
 "compatibility":{"skeleton":"example-pack/joints","events":"retail/events"}}
```

Appearance requires a skeleton label; movesets and cinematics require skeleton
and event labels; voices require an event label; AI/portraits have empty
compatibility objects. Resolved fighters need appearance and moveset resources.
Their skeleton/event labels must agree. **These labels are author assertions in
this prototype.** Production asset decoders must verify the corresponding file
structures. No assets, paths, archive payloads or executable instructions are
accepted by this draft resource schema. Pack intake and native format validation
remain separate work; rejecting unknown JSON fields is not sufficient asset
validation.

The native exporter uses conservative `retail/binding-<fighter>` compatibility
labels. They identify a known retail donor bundle, not a decoded skeleton or
event fingerprint. This prevents unverified cross-donor animation/voice mixing;
it may reject combinations that future asset validation will establish as valid.

## Check packs and diagnose conflicts

```powershell
python scripts/fighter-registry.py resolve-preview baseline.json alpha.json beta.json
```

Success prints a canonical-order JSON snapshot. Failure returns exit code 1 and
structured JSON with an error code/message/details. Competing edits list the
fighter, component, providers and each proposed value. Independent portrait and
voice edits can compose; two different edits to the stats group conflict. Stats
are deliberately one coarse group for now, including edits to different stats.
Skeleton/event checks still apply after independent components are combined.

An override contains `target`, `components` and `supersedes`:

```json
{"target":"retail/ludacris","components":{"stats":{"health":80}},
 "supersedes":[]}
```

An explicit compatibility pack can supersede competing providers. Every
superseded provider must be an exact dependency. This avoids relying on launcher
ordering to decide gameplay behavior.

The helper accepts a choice for **every** conflicting fighter/component and
prints a draft patch plus the validated preview hash:

```powershell
python scripts/fighter-registry.py suggest-compatibility baseline.json alpha.json beta.json --id example-compat --choose retail/ludacris:stats=alpha
```

The user must choose a provider listed in the error. The helper copies the chosen
component, declares exact dependencies and supersedes the competing claims. It
resolves the full composition again, so an incompatible skeleton/event combination
still fails. It does not adapt assets. Output is a report containing `patch`, not
a directly installable pack; review/extract that object for further local tests.
No command changes installed packs, launcher settings, original data or saves.

Input budgets are 1,024 enabled packs, 16,384 total definitions/edits, 8 MiB per
JSON document and 32 MiB combined CLI input. These are prototype processing
budgets, not selectable fighter limits. Duplicate JSON keys, non-finite numbers,
unknown fields, invalid references and dependency cycles are rejected.

## Native inspection and remaining creator tools

```powershell
python scripts/fighter-registry.py inspect-native path/to/assets/djv2.sod
```

This prints native Character metadata and source hashes. Its selection key,
one-based core ID, string IDs and record offsets are separate native concepts;
none is a stable public fighter key. Keep output/game-derived caches local.

Compile packs into a native cache preview:

```powershell
python scripts/fighter-registry.py compile-native-preview path/to/assets/djv2.sod example-pack.json another-pack.json
```

Without options this prints the preview report and writes no cache. Add
`--write-cache` to publish a verified content-addressed preview beneath the
repository's ignored `logs/fighter-native-preview/`. Existing cache bytes and
reports are checked before reuse; corruption fails without overwriting them.
Generated reports have a separate 32 MiB budget, checked before publication.

This adapter translates retail donor resources, complete stats, localization
keys and permitted edits into native records. Pack order is irrelevant. It
retains donor core IDs and all untouched retail record bytes. Donor inheritance
uses authored retail data before overrides. New asset resources, AI/cinematic
components and retail core reassignment fail with explicit unsupported errors.
Complete appearance/moveset/voice/portrait and all four stats must be present,
directly or through inheritance, for this adapter to produce a preview.

Custom names become a validated FML1 name cache keyed by bounded generated
native symbols; the report includes its hash. Ordinary preview commands do not
activate it. Long names retain a conservative blocker while native views are
audited: one transient menu sort field is 20 bytes, although its exact relationship
to `DisplayName` is not established. This is not a permanent public name limit.
Selection keys above 127 are reported separately. Every preview
retains `runtime_ready: false` and `launch_allowed: false`: it does not allocate
new movesets, install a mod or make fighters playable.

The runtime-owned binding ledger now retains historical fighter handles and
selection tokens across pack removal and re-enable. FMB1 translates those
identities to each snapshot's physical native rows; authors never choose either
number. The internal probe can consume a previous cache's ledger with `--ledger`.
The ledger must remain tied to its profile/save namespace before production use.

Inspect a model/face envelope, either raw or RefPack compressed:

```powershell
python scripts/fighter-registry.py inspect-model path/to/model.o
```

The validator permits the observed data-only ELF layout, bounded symbols and
pointer relocations. CPU executable sections, absolute address symbols,
out-of-range/duplicate relocations and oversized expansion are rejected. The
report lists imports/exports for dependency resolution and the observed exported
bone name/index map. Bone indices must be unique and contiguous. Matching this
map establishes only matching names and indices; it does not establish parent
relationships, bind poses, skin weights or animation compatibility. Typed reader
helpers distinguish inline data from explicit pointer relocations and reject
unresolved imported pointers and reads beyond the data section. Passing this inspection
does not validate EAGL geometry, materials or texture references and
does not grant a runtime asset capability.

When present, the observed inline `__Skeleton:::root` resource receives a separate
typed check: bounded 112-byte records, one ordered parent tree, matching exported
bone indices, finite transforms, normalized quaternions and a complete opaque
permutation. The reader preserves every stored matrix, including authored
corrections. It reports topology and pose hashes separately. Matching topology
does not establish matching poses, skin joint mapping or animation compatibility;
those last two checks remain false in inspection metadata. A face/pose module
without a skeleton is reported with `skeleton: null`, rather than treated as a
complete fighter model.

Inspect the currently understood geometry structures separately:

```powershell
python scripts/fighter-registry.py inspect-geometry path/to/model.o
python scripts/fighter-registry.py inspect-geometry path/to/model.o --textures path/to/textures.xsh
```

This checks explicit material-to-render-resource links, bounded vertex buffers,
finite positions/UVs, matching stream lengths, known index headers and uint16
index bounds. It distinguishes surface strips, untextured helpers and sparkle
point streams. The optional texture check requires every referenced shape in
the supplied validated file; a missing shared sparkle atlas is an error until
its original-library dependency is resolved. Unknown index/stream variants are
rejected. Imported render commands, native parameter bindings and skin weights
remain unvalidated, and this command still reports `runtime_ready: false`.

Inspect a supported SHPX texture archive, raw or RefPack compressed:

```powershell
python scripts/fighter-registry.py inspect-textures path/to/textures.xsh
```

This checks single-level indexed/BGRA/DXT1/3/5 textures, dimensions, complete
pixel and palette ranges, attachment chains, shape references and overlaps.
Unknown formats or mip layouts require a validated adapter. The data-only shape
renamer edits verified directory/material fields and rejects collisions. It
does not guess references inside model data. All 46 community-pack texture
archives pass this file-format gate; model/material compatibility and actual
native loading remain separate requirements.

The [active runtime research note](research/fighter-mod-runtime-2026-11-02.md)
records isolated native probes. `scripts/fighter-runtime-probe.py` is an internal
acceptance driver, using disposable guarded saves under `logs`, not an install
or activation command. Combat start controls do not prove native menu selection.
The probe's `--expect-fighter` assertions verify original ControllerSetup
submissions and actual match IDs without overriding them. Two-player custom
headers, donor thumbnails/portraits and selection now have native evidence;
other layouts, full save lifecycle and authored resources remain acceptance gates.

The native-menu compiler owns bounded header text fields, with independent
bindings for each player and line. Display wrapping never changes a fighter's
saved identity or unwrapped HUD name. Native stat percentages are capped for
custom fighters after the original display getter; authored gameplay values in
the database remain intact. Two-player visual tests cover a health-88 update,
the complete wrapped name and returning to the created fighter without stale
text. Three-/four-player long-name and result acceptance remain required.

The internal probe can also use `--language-pack PATH`. It verifies the existing
language deltas against the supported original screens archive, applies fighter
presentation to that language base, and requires native hashes of both the
actual language cache and final output before one redirect is adopted. Other
language files keep their native handling. A language pack that edits the fighter
database receives a composition error until a semantic database adapter exists.
This research option does not enable a launcher capability.

Use repeated `--texture-pack PATH` options to exercise existing texture packs
in native precedence order alongside the fighters. The language and texture
folders must share one native mods root. The probe validates their image paths,
rejects linked subdirectories, duplicate selections and pack lists that the
native loader would truncate. Installed packs are read without modification;
the research option does not enable a launcher category.

For the repeated-match research route, `--immutable-reuse` retains canonical
custom records for the process lifetime while ending selection ownership after
native Game.Quit. Repeat `--expect-match key-a,key-b` once per expected match.
The driver checks each match's fresh submissions, stable bindings and actual
materialized cores independently. This does not expose process-lifetime native
IDs to packs, or claim that Game.Quit acknowledges resource destruction.

The internal `--binding-window` prototype appends typed logical CCharacter
entries while retaining four native participant slots. A 300-custom-fighter
research roster has selected logical ID 361 through the native menu and reached
combat with its correct name and stable identity. This is capacity evidence,
not a supported package capability or a permanent roster limit. The ordinary
draft format has no bank numbers or engine addresses.

Its profile research uses a separate store of immutable generations. Each
generation binds native MC02 files to the historical ledger and custom unlock
extension. A sealed native save journal is only intent: every complete native
file must verify before the exact batch can replace the committed generation.
The probe keeps all stores and working copies under `logs`; normal profiles
remain outside this entry point. Bank lifetime, real custom-progress save/reload,
missing-content behavior and production helper failure handling remain gates.

Before publishing creator instructions, implement asset conversion/validation,
native registration, preview/selection, profile lifecycle, package transactions
and component-specific acceptance cases. Reusable conversion/package/preview
tools belong in DefJam-Modding-Tools; the game owns runtime adapters and the
versioned contract. Vendetta conversion must emit this ordinary general format
once that contract is proven.
