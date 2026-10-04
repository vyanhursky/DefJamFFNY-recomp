# Launcher defaults and documentation review

2026-10-04. Bounded read-only review of normal launch recipes, runtime feature
gates and `run-20261004-093647.log.err` / `run-20261004-093829.log.err`. The main
agent owns launcher changes and live verification. This audit edits only this
report; it did not build, launch the game or modify source/instructions.

## Verified closure

The main agent corrected `run.ps1` to supply these four settings when absent,
preserve existing overrides and remove its additions in `finally`. A clean
environment launch through Windows PowerShell 5.1 created the real game window,
initialized D3D11 and OHCI and rendered frames in
`logs/run-20261004-094353.log.err`. The two stuck processes were stopped; the
corrected game was left running for Vlad with disposable review profiles.
Workflows, reference, acceptance instructions and PROGRESS now record the fix.
Automated harness tests covered the configured runtime but missed the fresh-shell
manual launcher. No runtime change or executable rebuild was required.

## Finding

The documented owner Release launch does not reproduce the tested harness
environment. At the time of review, `scripts/run.ps1` forwards its inherited
environment and sets only the optional watchdog variable. It does not supply
`RECOMP_VBLANK`, `RECOMP_PB_EXEC`, `RECOMP_PB_D3D11` or `RECOMP_USB`.
`scripts/env.ps1` configures the toolchain/data root, not those runtime flags.
`scripts/harness.py` explicitly supplies all four as `1` for every child run.

The application already defaults AC97 readiness, six-speaker mixdown and the
anchored-seconds script grammar, but did not default these four features.
Consequently, a fresh-terminal `run.ps1 -Preset win-x64-release` can pass its
build certificate, load the XBE/kernel/APU and still never create the renderer
window. A valid executable certificate does not certify the launch environment.

`d3d11_translator_init` at
[d3d11_translator.c:127](C:/Users/Vlad/code/defjam-recomp/src/hooks/d3d11_translator.c:127)
returns before window creation when `RECOMP_PB_D3D11` is absent. The other gates
enable the push-buffer executor, GPU vblank and USB model. The launcher option
`Start-Process -NoNewWindow` concerns the process's console; it does not suppress
the game's own GUI window. It is not the renderer failure described here.

Both failed logs initialize the kernel and APU but contain no `[TRANS]`,
`[PGRAPH-D3D11]`, D3D device creation or OHCI initialization marker. Their tails
continue kernel-call summaries. That is consistent with the missing-feature
configuration, not evidence for a new shader, fence or GPU synchronization
regression. The logs do not dump the environment, so source/recipe review is
the decisive evidence for the configuration mismatch.

## Exact documentation corrections

Line anchors refer to files as read before the main agent's corrections.

| File / current instruction | Minimum correction after the verified default fix |
|---|---|
| [toolkit-rebase-acceptance.md:155](C:/Users/Vlad/code/defjam-recomp/docs/research/toolkit-rebase-acceptance.md:155), owner play-test block at 159–164 | Highest priority: explain that normal launches now enable the four required features. Keep the existing disposable `DEFJAM_DATA` setup and `try/finally` restoration, then use bare `run.ps1 -Preset win-x64-release`. Until the default fix is verified, this block must explicitly supply all four flags. |
| [docs/03-workflows.md:14](C:/Users/Vlad/code/defjam-recomp/docs/03-workflows.md:14), pipeline block ending in bare watchdog launch | Add a short **Playing** recipe with the Release command, data-root explanation and the four normal defaults. Label `-WatchdogSecs 10` as a bounded bring-up diagnostic rather than the owner play-test command. The existing pipeline can continue using it for diagnosis. |
| [docs/05-reference.md:86](C:/Users/Vlad/code/defjam-recomp/docs/05-reference.md:86) | This is the one current instruction that correctly states the four flags are required. Replace the manual prerequisite with the verified default behavior and retain the explanation of each flag's role. Say both normal launch and harness have the same required features. Link to the canonical Playing recipe rather than duplicating environment setup. |
| [README.md:20](C:/Users/Vlad/code/defjam-recomp/README.md:20), quick-start step 4 | Split build/analysis from play and show `run.ps1 -Preset win-x64-release` after the matching Release build. Link to the canonical Playing recipe and say no runtime-feature setup is required for normal play after the fix. Do not imply a Release executable exists after the default Debug build. |
| [README.md:6](C:/Users/Vlad/code/defjam-recomp/README.md:6), status paragraph | Remove the stale claim that nothing is on screen and the renderer is only a bring-up diagnostic. A concise current statement can say menus, Story and fights render; the toolkit rebase awaits owner play-test. This claim otherwise makes the actual configuration failure look intentional. |
| [AGENTS.md:60](C:/Users/Vlad/code/defjam-recomp/AGENTS.md:60) and matching [CLAUDE.md:60](C:/Users/Vlad/code/defjam-recomp/CLAUDE.md:60) | Add one sentence that normal game launches supply the four required features and link to the workflow recipe. If either file is edited, update both identically. Keep the iterative diagnostic/watchdog loop distinct from owner play. |
| [PROGRESS.md:205](C:/Users/Vlad/code/defjam-recomp/PROGRESS.md:205), current owner play-test hand-off | Record the launch mismatch/fix and the verified log filename in the work log/hand-off; give the same canonical Release recipe. Keep the rebase pending owner play-test. Earlier harness gates stay valid for their recorded environment. |

`docs/06-toolkit-rebase-plan.md` asks for the play-test but has no incomplete
launch command of its own; a link to the canonical recipe is enough. No roadmap
or test-plan milestone definition needs changing to correct this launch issue.

The historical worklog already records this exact trap at
[2026-09.md:1399](C:/Users/Vlad/code/defjam-recomp/docs/worklog/2026-09.md:1399):
neither launcher nor smoke supplied the four flags. Preserve that historical
record. Research bring-up notes and old experiment recipes describe opt-in
toolkit behavior and should not all be rewritten into current user instructions.

## Canonical wording and semantics

After the main agent's source/live verification, the normal play paragraph can
read:

> From the repository root, run `scripts/run.ps1 -Preset win-x64-release`.
> Normal launches enable GPU vblank, push-buffer execution, the D3D11 renderer
> and USB controller support. `DEFJAM_DATA` selects the data/save root; use the
> preserved disposable profiles for the rebase play-test. The resulting log is
> written to `logs/run-*.log.err`.

Keep the acceptance report's existing `DEFJAM_DATA` save/restore PowerShell
block. Restoring that environment variable does not roll back files created in
the disposable root; automated harness runs separately provide their full save
guard. Do not label a manual run automatically save-guarded.

Current toolkit gates check **presence**, so setting any of the four variables
to `0` still enables it. Documentation must not invent a `=0` disable recipe.
If the main agent adds explicit suppression/diagnostic launch semantics, record
the exact implemented interface and its tests. Normal defaults and diagnostic
overrides must be described consistently across the main application, launcher
and harness.

`tests/smoke/boot-smoke.ps1` invokes `run.ps1` and does not independently set
these flags. Defaulting them before runtime initialization therefore also
corrects smoke launches. It does not add the harness's save guard, scripted
input or route assertions to smoke/manual play. `-WatchdogSecs` remains an
explicit diagnostic option and should not become a normal-play default.

The minimum documentation patch is the acceptance recipe, workflow Playing
paragraph, reference prerequisite, README launch/status text and synchronized
agent/hand-off note. Verify the bare Release command from a clean environment
and cite renderer/controller startup and presentation evidence before telling
the owner the recipe is corrected.
