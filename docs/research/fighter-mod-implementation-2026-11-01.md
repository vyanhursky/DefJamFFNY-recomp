# Fighter Mod Support: first implementation checkpoint

2026-11-01, target v0.15.0. Local branch `research/custom-fighter-mods`, based on
public v0.13.0 `e7d35e1637b1eb63ee1d8bb3b3153f3b0d083e62`; toolkit pin
`d569ca10811cef67ec4e9fa2173088c2f9fd0580`. All D1–D6 directions are approved in
the [plan](../fighter-mod-support.md). No push/public PR is authorized.

## Implemented scope

- `setup/fighter_registry.py`: strict draft typed definitions; whole-pack
  resolution; stable keys; exact dependencies; shared resources; copied donor
  inheritance; independent component composition; actionable conflicts;
  skeleton/event consistency; deterministic snapshots/content locks.
- `scripts/fighter-registry.py`: local native metadata inspection, resolution
  previews and compatibility-patch suggestions from explicit user choices.
  The helper revalidates the final composition, without adapting assets.
- `setup/fighter_sod.py`: bounded SODB v2 reader and an offline Character-record
  extension experiment. Retains original records/string IDs, rebuilds indexes
  and reports changed name-index ranks and signed-byte overflow.
- `scripts/fighter-sod-oracle.py`: CPU-only parser oracle using four fixed
  functions extracted locally from the owner's generated source. Only the
  source-free harness generator is tracked.

All snapshots/cache-construction reports say `runtime_ready: false`. No launcher
category, runtime hook, asset validator, save bridge or playable custom fighter
is advertised. The [authoring prototype](../fighter-mod-authoring.md) describes
the executable draft contract and its limits.

## Independently established native format

SODB v2 has a 24-byte header: magic/version/schema fingerprint and offsets to
`SKMA`, `DATA` and `STRT`. Its generic index contains count, stride, optional
sorted keys, then **interleaved** value tuples. Stride zero means unkeyed ordinal
values. SKMA maps sorted member keys to `(word offset, type descriptor)`; DATA
maps table symbols to absolute table headers. A table header has symbol,
primary/secondary member-map offsets and record count. Each member map points
to indexes of the same record set. STRT contains `(hash, absolute string offset)`
pairs; string payloads may precede a relocated directory.

Native symbol hashing is case-sensitive djb2, seed 5381, **including terminating
NUL**. `Character` hashes to `4ce5b1b2`; a member schema key is the table hash XOR
member-name hash. Retail Character has 75 records of 26 words/104 bytes; the
supplied mod has 121. The inspector validates section/index bounds, sorted keys,
counts, record-set agreement, string bounds/encoding and hashes.

Two native identity members have independently checked roles:

| Schema key | Word | Role |
|---|---:|---|
| `fcdba74e` | 8 | Selection key compared with front-end selection in StartGame |
| `232d89a7` | 10 | One-based core ID materialized into match setup; active lookup subtracts one |

Their English schema names remain unknown. They are not interchangeable with
the record's name-index rank, tagged SOD handle, voice ID or public fighter key.
The extension clones the donor core ID, explicitly named `inherited_core_id` in
its report. It does not allocate an independent core/moveset.

The owner's `fighter.xml` is malformed XML and stale against the loaded SOD.
A bounded model-key crosscheck matched each candidate identity field in only
70/75 rows; alternate records also reuse core IDs. XML is supporting evidence,
not an authoritative retail registry. Preserve original SOD data as the input.

## Measurements and limits of the result

Original SOD SHA-256:
`90cc4655680e1f7c1c8ffb140eb81208648682259e5c68e4e8e8cf65b2c8a803`.
Supplied mod SOD SHA-256:
`efa49a80f188bb3c2dcb0af0de7eb2b9b7ab86973ac70b8483de789d60fe3916`.

The cache experiment added **300 synthetic Character definitions** to the 75
retail records: 375 total, 340,008 bytes, about 22 ms construction in this run.
All original 104-byte records were byte-identical. Output SHA-256:
`b4feeb9e8e1f79ae0d5947883b8979582968d5b5061c8c5f52043e271d224cb4`.
272 added keys exceed 127, and 58 original name-index ranks change. This rank
movement requires auditing any retained handles; it does not prove those ranks
are serialized into profiles.

The independent CPU oracle ran the unmodified generated parser/index bodies
at `BE310`, `BE3D0`, `BE480`, `BE4E0`, with checked guest memory and a file-open
stub returning the already loaded buffer. The stock 75-record SOD passed, then
the 375-record SOD passed and found `synthetic/fighter-257` with selection key
**276** and its correct native string. The initial harness failed on stock due
to passing a pointer-cell address instead of its offset value; that scaffold
argument was corrected before either reported successful run.

Generated `recomp_0005.c` SHA-256:
`35bb1296b10b8d015d8692839aeebd381be6cc4c384687b3f44803116ce80d0a`.
Local evidence:

- `logs/fighter-mod-research/native-375-roundtrip.json`
- `logs/fighter-sod-oracle/1793597564106693800/result.json` (retail)
- `logs/fighter-sod-oracle/1793597564562346000/result.json` (expanded)

This proves the native database loader/index can handle that constructed size.
It exercises no actual game, selection movie, combat, graphics/audio/input, save
or distinct added asset. It does not establish playable capacity beyond 255.
The [capacity audit](fighter-mod-capacity-2026-11-01.md) records the signed-byte
front-end bottleneck and fixed 141-row moveset initializer.

Reproduce the cache experiment from the repository root, using local paths for
the owner's original SOD and retained generated source. This Python snippet
writes only an ignored local cache; it never installs it:

```python
import json, sys
from pathlib import Path
sys.path.insert(0, 'setup')
from fighter_sod import Database
db = Database(Path('path/to/own/assets/djv2.sod').read_bytes())
donor = next(r['record_offset'] for r in db.character_metadata()['characters']
             if r['name'] == 'Ludacris')
additions = [{'key': f'synthetic/fighter-{i}', 'template': donor,
              'fields': {'Health': 50}} for i in range(300)]
data, report = db.extend_character_records(additions)
out = Path('logs/fighter-mod-research')
out.mkdir(parents=True, exist_ok=True)
(out / 'expanded-synthetic-375.sod').write_bytes(data)
(out / 'bindings.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
```

```powershell
. ./scripts/env.ps1
python scripts/fighter-sod-oracle.py --generated path/to/own/src/recomp/gen --sod logs/fighter-mod-research/expanded-synthetic-375.sod --expect-count 375 --probe synthetic/fighter-257
```

## Native UI and persistence handoff

Bounded reads found two native enumeration candidates:

- `47BC0`: DB root at `+2C`, Character lookup, dynamic `count × 32`
  allocation, accepted count stored as a dword at `+4`, then item
  processing through `2008E0`. It excludes selection key 98. XBE pointer
  `2931A0` identifies vtable `293160` slot `+40`; `46E10`, registered as
  `Game.GetGameMode`, returns fixed object `341330` using this vtable.
  This is **shared game-mode state, not a proven per-player selector**.
- `54420`, registered as **`Game.GetCharacterList`**: global root `341540`, dynamic `count × 4` pointer list, exclusion
  involving context `+C10`, then UI construction through `53A10`, `5F7B0`,
  `5F8B0`; returns shared address `341768`. Context/mode ownership remains open.

Neither has direct call sites in the retained generated chunks. The registration
route is now resolved from the owner's XBE strings and generated registration
calls: `54A30` binds `GetCharacterList` (string `295B9C`) through `45610`;
`55E00` similarly binds `Controller.ControllerSetup` (string `296244`) to
`558E0`. ControllerSetup handles selection/controller properties, not roster
enumeration. The primary independently checked the strings, pointer and call
sites. Trace their movie/script callers and context data before choosing appended
entries or a per-player page. A page switch cannot simply replace shared
Game.GetGameMode/GetCharacterList data for one participant. Verify all menu
variants and independent P1–P4 browsing/ready state through native tests.

The persistence audit traced slot-18 constructor `200E0`: main allocation
`0x5AC80`, initialization through `16160`, sixteen records with stride `0x5950`.
Reset method `16240` invokes six embedded callbacks at vtable slot `+14`.
Reading the owner's XBE mapped all six to **168E0**, a bit-array reset/fill;
they are not serialization callbacks. Vtables: `28627C`, `2862A8`, `2862D4`,
`286300`, `28632C`, `286358`. Nearby `1EC50` also initializes runtime fields.
These allocations/resets prove neither persisted capacity nor key identity.
Find actual class-specific save/load callbacks before attempting D3A. If safe
isolation cannot be established, D3B is already authorized; document the evidence
and preserve the original profile. No real profiles have been changed.

## Validation and exact next work

Synthetic tests cover one/multiple packs, shared resources, deterministic
reordering, inheritance, dependency/cycle errors, independent/conflicting edits,
compatibility helper choices/revalidation, strict CLI JSON/intake budgets,
malformed SOD indexes/strings/counts, record preservation, ordinal stability,
numeric-index high keys and reserved token 99. Test counts/results are recorded
in `logs/fighter-mod-research/implementation-validation.json`:

- Focused inspector/SOD/resolver/CLI/helper suite: **60 passed**.
- Full unit suite, `python -m pytest -q tests/unit -m "not slow" --basetemp
  logs/pytest-fighter-full`: **671 passed, 165 skipped, 1 deselected**, 29.35 s.
  Windows junction tests ran with the required filesystem permissions. Skips
  reflect unavailable fixture/build/platform prerequisites in this lane.
- Native metadata reader parsed both original 75-record and supplied 121-record
  SODs after the implementation changes; hashes match those above.
- No actual game build/run or gameplay/profile/menu acceptance claimed.
- Staged source publication check: **547 tracked source files, 0 failures**;
  whitespace checks passed. Only source, synthetic tests and documentation staged.

Continue with:

1. Trace the registered native roster callbacks into movie/selector contexts and
   find real save/load entrypoints.
   Finish the identity/table/allocator/lifetime matrix before choosing D1 layout
   changes or virtual bindings. The signed-byte boundary is earlier than 255.
2. Build a verified retail semantic exporter and native binding adapter. Keep
   skeleton/event assertions distinct from decoded asset validation. Add typed
   format validators before accepting payloads; do not expose template offsets
   or raw field writes as a package contract.
3. Implement a one-fighter native vertical slice through the general resolver,
   then two independent packs. Audit new core/animation/voice/cinematic storage,
   cache invalidation, menu previews and all native table consumers. This is an
   internal implementation step, not a limited compatibility product.
4. Prove save lifecycle or use the authorized isolated-profile fallback; then
   integrate whole-pack transactions/restart handling and the Fighters category
   into the existing mod manager. No selectable category before runtime support.
5. Complete authoring tools, ordinary-format Vendetta conversion and the plan's
   native/platform acceptance matrix. No public push/PR until requested.

No reference-project code was copied. Game-derived/generated files and oracle
executables remain under ignored local logs. `PROGRESS.md` is untouched because
this is a feature branch; this note carries its local handoff.
