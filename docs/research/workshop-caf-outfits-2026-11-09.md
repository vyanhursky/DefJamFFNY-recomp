# CAF v3: one fighter with three outfits

Owner-approved extension of Workshop fighter modpack authoring. A fighter keeps
one registry key, one canonical selection and one progress identity. The native
clothing selector offers one to three appearances, independently per participant.
Existing CAF v1/v2 packages retain their native formats.

## Source contract

`caf-fighter-3` uses the same hash-bound `selection` JSON descriptor. Root
`stats`, `styles` and optional four `finishers` apply to every outfit. Root
`caf_values`, `caf_colors` and optional `atlases` describe the default outfit;
`outfit_name` names it. Required `outfits` holds zero to two additional records:

```
{"id":"red-jersey","name":"Red jersey","caf_values":[...],
 "caf_colors":[...],"atlases":{"a":{"path":"outfits/red/a.png","sha256":"..."}}}
```

IDs are unique bounded lowercase slugs; `default` is reserved. Each appearance
passes the original CAF recipe/resource checks and each atlas retains CAF v2
size, hash, inventory and alpha rules. Optional `portraits` maps outfit IDs to
normal, declared, validated portrait-resource keys in the same pack. Missing
entries inherit the fighter's default portrait/presentation donor. Portraits
use existing typed resources and native UI templates, never supplied bytecode.

## Compiled formats

For a compilation containing v3, `fighter-caf.bin` starts with `FCA2`, uint32
version 2, row count and stride 240. Each row preserves the 232-byte FCA1 prefix,
followed by uint32 zero-based outfit index and uint32 presentation alias. The
reader requires unique (selection,index), dense indices 0–2 with a default,
identical combat/core/style/audio fields, and unique valid presentation aliases.
The maximum is three times the existing 16,384-fighter recipe capacity.

`fighter-caf-extras.bin` uses `FCX2`, version 2, stride 52: its existing 48-byte
prefix followed by the outfit index. Atlas payloads are content-deduplicated,
retaining the 16 MiB sidecar budget. Its reader verifies exact recipe membership,
unique pairs, consistent shared finisher overrides and original offset bounds.
Mixed compilations encode legacy fighters as outfit zero. Legacy-only inputs
still emit FCA1/FCX1; their native readers remain supported.

Presentation aliases start at 0x60000000, skip all current registry selections
and are deterministic within a compiled cache. They are visual paths only:
never ledger entries, native actor/core IDs, unlock marks or saved progress.

## Original selector and participant lifetime

Measured CCharacter construction does **not** parse repeated FE_ID fields as
clothing datasets. Its CLOTH count consumes successive Game.GetNextFighter
responses. Owned fighters are appended after that retail stream ends. The
compiler initializes each with an ordinary CLOTH=1 dataset, then fills its
additional `aDataSets` locally with the same canonical FE_ID. `numClothes` and
the original clothing navigation then work unchanged. Semantic `getID` and
ControllerSetup retain the canonical selection for every outfit.

The owned keyXHandler wrapper snapshots participant grids before invoking the
original handler, then reports `Fighters.Outfit(slot,selection,index)` afterward.
Only declared multi-outfit characters emit it. The runtime accepts canonical,
bounded commands only before freezing, and updates only a matching confirmed
participant binding. Browsing grids do not gain ownership. Controller reset,
retail selection and ready-mask cancellation retire the relevant outfit choice.
Context teardown clears visuals/finisher journals but retains menu choices for
Rematch. Re-entering the roster resets them through ControllerSetup(-1,...).

An owned visual `getPortraitID` serves only updateChar's portrait lookup.
Loading/result identity adapters return the selected visual alias. Grid art and
fighter names remain canonical; aliases receive the same display name. Native
CAF assembly selects exactly one recipe/extras pair for each participant and
keeps all atlas writes local to that visual, including original material alpha.

## Acceptance

Compiler and actual C-reader tests cover dense/unique pairs, combat mismatch,
alias collision, undeclared extras, independent participants and rematch choice
lifetime. Windows Workshop exercises real UI switching/copy/remove/Undo/Reset,
three portrait captures and complete-project persistence. Native game evidence,
source hashes and remaining platform qualifications are recorded in the PR;
private source art, captures, saves and packages are not tracked.
