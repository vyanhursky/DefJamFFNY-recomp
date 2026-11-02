# Fighter Mod Support: semantic-to-native adapter

2026-11-02. Continuation of the [first checkpoint](fighter-mod-implementation-2026-11-01.md),
on local `research/custom-fighter-mods`. Owner authorized continuing the approved
v0.15.0 plan; no push or public PR. No external implementation code used.

## Implemented

`setup/fighter_native.py` connects the general resolver to the native SODB
builder. It exports a local retail manifest from a hash-verified original SOD,
resolves whole enabled packs, translates supported definitions into native
records, and reports exact stable-key/native bindings and localization entries.
No caller supplies raw offsets/native numbers through a pack manifest.

`config/fighter-native-baseline.json` pins the supported original SOD hash;
using an already modified database as the retail baseline fails. This is an input
integrity pin, not a Vendetta-specific compatibility branch. The exporter derives
retail keys from original native names and rejects identity collisions rather
than adding offset-based suffixes. It exports 75 fighters/300 resource references.
These draft retail keys still need contract freeze/migration policy before release.

Resource bindings currently reuse complete known retail donor bundles. Their
opaque per-donor compatibility labels are conservative; they are **not decoded
skeleton/event signatures**. The general resolver can express more, but the
native adapter explicitly rejects new asset resources, AI/cinematic components,
incomplete bundles/stats and retail core reassignment until those adapters exist.
No ignored unsupported component can silently produce a different fighter.

The SODB builder now applies named edits to existing records as well as additions.
It rebuilds all affected keyed indexes, including string/numeric indexes, while
retaining original ordinal positions and untouched record bytes. Added fighters
clone authored donor records before edits, matching the resolver's inheritance
rule. The new records inherit their donor's one-based core ID; no new core,
animation bank, voice bank or executable payload is created.
Before rebuilding, original index keys must agree with their schema-addressed
record values; an unknown key encoding is rejected instead of guessed.

`scripts/fighter-registry.py` adds `export-retail` and `compile-native-preview`.
The latter writes nothing unless `--write-cache` is present. It then stages a
content-addressed cache under ignored logs, publishes the directory only after
construction, and verifies existing data/report bytes on reuse. The cache key
covers the adapter, input/snapshot/output hashes, bindings and complete report.
Generated reports have a distinct 32 MiB budget checked before publication.
Corrupt cache/report files are diagnosed without replacement.

See [authoring prototype](../fighter-mod-authoring.md) for exact commands. Every
preview retains `runtime_ready: false` and `launch_allowed: false`; runtime gates
are listed explicitly. There is no launcher capability or install path yet.

## Native selection findings and architectural implications

The primary checked the relevant generated C and the owner's XBE strings;
bounded independent agents supplied additional call-chain leads.

| Native path | Verified behavior | Required integration |
|---|---|---|
| `54420` / Game.GetCharacterList | Collects Character handles into dynamic `count × 4` storage; qsort comparator `53F70` resolves property `ca10191c` (DisplayName) and compares strings; `53A10` then reorders entries using context `+C14..+C30` | Simply appending SOD records will not put custom fighters below retail. Preserve retail mode-specific ordering and partition custom entries explicitly. Do not label the context's fields as the SOD Order member without tracing the link. |
| `54420` output | Native strings at `295CAC/295CB4/295CB8` are Count/BE/FE; helper calls append corresponding key/value entries into shared buffer `341768` | Audit shared buffer growth and every movie's interpretation of BE/FE before widening selection. |
| `47BC0` / shared GameMode vtable `+40` | Builds 32-byte records, with a text field at `+4`, followed by dwords at `+18/+1C`; qsort comparator `45A90` compares the NUL-terminated `+4` strings | This is shared state, not one player's page. Sort/identity changes must cover both native list paths. |
| `47BC0` text copy | Converts localized UTF-16 text through `45320` into scratch buffer `39E858`, then copies bytes into row `+4` until NUL without a 20-byte bound | More than 19 UTF-8 bytes can overlap the following fields. Preserve full visible names while correcting the native row/storage/comparison path; do not silently truncate or use arbitrarily long public keys as native labels. |
| Missing localization | `47BC0` falls back to a literal at `289954`: SOD/LOC MISSING STRING | Custom DisplayName values require localization registration composed with language mods. Literal pack names cannot simply be written as if already registered. |
| ControllerSetup/StartGame | `558E0` stores byte selection data; `46E40` uses signed `SX8(LO8(...))` and maps 99 to 98 | Selection key expansion/virtual binding still needs the complete native handoff and created-fighter paths. |

Preview native symbols are bounded `fm-` plus 16 hex digits from the stable
fighter key. Colliding native hashes/names fail in the builder. DisplayName is
that generated localization key; desired Unicode text is a separate report
entry. A desired label exceeding 19 UTF-8 bytes adds `native-label-buffer` to the
blockers. This does not fix the native copy or impose a final authoring limit.
Default examples use short names but remain blocked from launch.

## Save investigation: narrowed leads, no wire-format claim

Earlier `21240`/`1ECE0` paths are constructors/runtime initialization. The pointer
stored by `21240` is the SODB object passed by `200E0`, not a demonstrated vtable.
`200E0` also constructs `C21D0` with SODB/profile pointers; bounded reads of its
methods show SODB lookup/validation, not disk serialization. Do not equate a
SODB-backed in-memory loader with the profile file reader.

Registrar `53700` exposes QuerySave `52990`, Save `52B60`, QueryLoad `52E40`,
Load `52E60`, LoadGlobal `52ED0`, and current-user setters. The save/menu route
stages profile data (including a `0x5904` copy) and pending UI rows, then enters
dialogs/state transitions through `D2780`. Bounded follow-ups reached `D20D0`
and a call to `D00C0` with staged-row context. `D00C0` then reaches request
initialization at `1987A0` through `197270`; that initializer submits through
unresolved virtual slot `[[object+14]+18]`. Its descriptor arguments and ownership
still need tracing; it is not yet a confirmed profile payload writer.
**No actual serialized payload
reader/writer was identified.** The copy size does not establish the save file
layout or identity domain. D3A remains unproved; D3B remains authorized if needed.
No profile files were opened for writing or modified.

## Validation

- Synthetic inspector/resolver/SODB/adapter suite: **67 passed**. Covers two
  independent packs, multiple fighters, retail edits without donor mutation,
  exact no-op, native-resource rejection, complete stats, long/Unicode labels,
  high selection keys, index reconstruction and cache corruption/budget handling.
  A post-review focused rerun also covers rejection of unknown native index-key
  encodings and leaves the real preview hashes unchanged.
- Full unit suite: **678 passed, 165 skipped, 1 slow deselected**, 27.06 s.
  Command: `python -m pytest -q tests/unit -m "not slow" --basetemp
  logs/pytest-fighter-native-full`; output `logs/fighter-native-unit-results.txt`.
  Junction tests used Windows filesystem permissions. Skips remain fixture/
  build/platform prerequisites; no actual game acceptance is implied.
- Real pipeline: two synthetic definition packs, one with two fighters and one
  with one, resolve against the supported original database. Result: **78
  Character records**, new selection keys 100/101/102, inherited core IDs 4/5/23.
  The existing generated CPU parser oracle finds fighters from both packs.
- Cache SHA-256:
  `bf167238894d8733863eee9d9d29c8edd0c6c779db58452c208d1ca91fdf2121`.
  Final report/cache key:
  `6ef2f715b249e977a6bc1823b69724da27c66adfe953bec7531e83d8a26daa7d`.
  Evidence: `logs/fighter-native-preview/pipeline-result.json`, and native oracle
  `logs/fighter-sod-oracle/1793608835933508300/result.json` (key 100) /
  `1793608836311854500/result.json` (key 102). The oracle source/input hashes
  identify the exact constructed database, even where an earlier report key differs.
- Two repeated CLI compilations produce identical reports and reuse the verified
  final cache. A modded SOD is rejected as a baseline with `baseline-hash`.
- No game/graphics/audio/controller run, save modification or playable fighter
  acceptance. Generated/game-derived bytes remain under ignored logs.
- Source publication check: **551 tracked source files, 0 failures**; staged
  whitespace check passed. Feature-branch state is here, not in PROGRESS.md.

## Next native integration step

1. Implement merged localization registration and safe native label handling.
   Trace both roster-output consumers and movie context. Preserve retail order,
   then append custom entries; retain the per-player page option only after its
   ownership/bounds are established. No global roster swap for one participant.
2. Finish selection/core/resource lifetime boundaries and table capacities. Use
   the connected pipeline for one native fighter, then independent packs; replace
   donor-only native restrictions with typed asset decoders and normal resource
   adapters. The prototype is an internal implementation stage, not the final scope.
3. Resolve the real save payload path from `D00C0`/`1987A0` async request slot
   `[[object+14]+18]` and the corresponding
   load path. Prove the companion bridge or adopt the authorized isolated-profile
   fallback with stable missing-content state before any runtime activation.
4. Wire validated snapshots into loader/caches, launcher Fighters transactions
   and restart gates; complete the original native/platform acceptance matrix
   and ordinary-format Vendetta conversion. Keep work local.
