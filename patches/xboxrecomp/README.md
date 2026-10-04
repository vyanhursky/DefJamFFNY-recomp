# Historical xboxrecomp patches

The 108 numbered patches reproduce the old `6f55eaa` baseline. They are retained as history.
vyanhursky approved publication on 2026-10-03; the fork branch is published at `aa1a1b9`.
Their final behavior is consolidated into 15 logical commits atop upstream `1409a7d` on
`vyanhursky/xboxrecomp`, branch `defjam/rebase-2026-10`. Build the exact commit pinned by
the parent gitlink after `git submodule update --init --recursive`; do not replay these patches.

See [the rebase ledger](../../docs/research/toolkit-rebase-ledger.md) for each patch's outcome,
replacement commit and evidence. `ours-on-pin` (`dc32f30`) and the ignored baseline snapshot
preserve the previous live state locally. No game data or compiled output belongs in this archive.
