# Workshop capability discovery

`scripts/fighter-contract.json` is a source-only API 1 manifest for tools that
inspect a game installation without running its compiler. It lists the contract
commands and the current CAF recipe format. It contains no game data.

The Workshop reader prefers this manifest and uses legacy Python source
inspection only when it is absent. Ship the reader before relying on this file;
the initial producer keeps the script's existing argument declaration intact so
older Workshops still discover this runtime. No command or recipe changes here.

When adding/removing an authoring command or changing the CAF recipe, update the
manifest alongside the implementation. `test_fighter_capabilities.py` compares
the JSON against the actual argparse declaration and recipe constant without
importing or executing runtime code. Refactoring the parser should update that
drift test while preserving this manifest's external contract.

Optional `extensions` lists finer-grained authoring features without changing
the command names or API number. `retail-animation-preview-1` means
`workshop-animation --pack <one-pack>` can use the pack's selected, hash-bound
retail body. Readers must not infer this extension from command presence alone.
Older readers ignore the optional field and retain existing behavior.

`standalone-retail-outfits-1` permits up to three looks under one standalone
retail-derived fighter. Hidden appearance records may declare a same-pack
independent parent through `outfit_of`; generated FWR3 bindings retain that
parent's progress and each look's own loading/result artwork. Original retail
outfits continue to use FWR2. Packs containing independent fighters only retain
FWR1. The public package schema is unchanged.

Companion Workshop reader:
[Workshop PR #14](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/14).

`caf-sculpt-normals-1` adds bounded, reference-bound packed neck normal
corrections to CAF face coordinates. Only projects using them emit FCAF
container version 2; coordinates-only containers retain version 1. It needs
matching authoring tools and a rebuilt game. See
[sculpt normal corrections](workshop-sculpt-normals.md) for the contract and
original-normal fallback on unsupported live layouts.
