# Fighter Mod Support: local authoring prototype

Target v0.15.0; local R&D. The [approved architecture](fighter-mod-support.md)
defines the intended feature. This document covers the first working definition
and conflict tools. **These drafts cannot be installed or played.** The schema
will evolve as native assets, menus and persistence are integrated.

## What the prototype checks

`setup/fighter_registry.py` resolves one or many fighters from each enabled pack,
including shared resources, exact dependencies, inheritance and component edits.
All enabled packs are resolved together. It emits a deterministic snapshot with
an explicit `runtime_ready: false` gate and a content hash.

The baseline is a locally authored/extracted `retail` document using the same
shape. The retail namespace is reserved. There is no automatic retail baseline
exporter yet. The synthetic tests show the full shape without distributing game
data: `tests/unit/test_fighter_registry.py`.

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
      "inherits": "retail/example-donor",
      "components": {"stats": {"health": 60}}
    },
    {
      "id": "second-fighter",
      "name": "Another Fighter",
      "inherits": "retail/example-donor",
      "components": {"stats": {"speed": 70}}
    }
  ],
  "overrides": []
}
```

`retail/example-donor` is a placeholder. This example needs a baseline defining
that donor; it is not an existing retail ID. Remove the second entry for a
single-fighter pack. The resulting permanent keys are
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
{"target":"retail/example-donor","components":{"stats":{"health":80}},
 "supersedes":[]}
```

An explicit compatibility pack can supersede competing providers. Every
superseded provider must be an exact dependency. This avoids relying on launcher
ordering to decide gameplay behavior.

The helper accepts a choice for **every** conflicting fighter/component and
prints a draft patch plus the validated preview hash:

```powershell
python scripts/fighter-registry.py suggest-compatibility baseline.json alpha.json beta.json --id example-compat --choose retail/example-donor:stats=alpha
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

The native-cache experiment can clone Character records and rebuild indexes. It
retains the donor's core ID; it does not allocate new movesets or make fighters
playable. There is deliberately no install/build-cache CLI yet.

Before publishing creator instructions, implement asset conversion/validation,
native registration, preview/selection, profile lifecycle, package transactions
and component-specific acceptance cases. Reusable conversion/package/preview
tools belong in DefJam-Modding-Tools; the game owns runtime adapters and the
versioned contract. Vendetta conversion must emit this ordinary general format
once that contract is proven.
