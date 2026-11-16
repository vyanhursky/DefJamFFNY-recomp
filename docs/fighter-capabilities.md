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

Companion Workshop reader:
[Workshop PR #14](https://github.com/vyanhursky/defjam-ffny-fighter-workshop/pull/14).
