# Public documentation readiness review

Reviewed 2026-10-04 after rebase integration `c23b44a` and acceptance closure `5bffcba`.
Scope: local, read-only documentation/provenance audit for the first public source
release. No source changes, builds, game runs, generated-C reads or external
compatibility research. This report recommends documentation corrections; it does
not change milestone definitions or reopen the accepted rebase.

## Closure

The recommendations below were applied: README, portable build/play guide,
docs index, known issues and contribution/release guides now reflect the
accepted Windows build. Private PR #2 is merged and CI/release validation
is green. A sanitized one-commit preview is ready; original history stays
private pending owner approval of the proposed repository transition.

## Summary (original review)

The accepted Windows Release build is much further along than the public README
describes. The README still says nothing renders and implies Steam Deck support.
The workflow page mostly reflects the current fork and launcher, but its initial
setup assumes Vlad's paths and its first run is a short Debug diagnostic. The test
plan mixes intended checks, historical observations and implemented automation.
These are the main corrections needed before a public source release.

The root license already distinguishes project-owned MIT code from the toolkit's
MIT/LGPL components and excluded game code/assets. Preserve the toolkit's notices
and credit the upstream project alongside the actual pinned fork. No missing
license file was identified in this bounded review.

## Current public claims

Use [PROGRESS.md](../../PROGRESS.md) and
[the accepted rebase report](toolkit-rebase-acceptance.md) for current status:

- Windows Release rendering, menus, Story routes and fights have owner acceptance.
  Both final regression presets passed 9/9; Debug completed 20/20 boot checks.
- The toolkit is pinned to published fork commit
  `aa1a1b91dea9fd266acb3a3fe51dfcec3b2e6bbc`, atop upstream `1409a7d`.
  Fifteen logical commits replace the 108 historical patches. Patch replay is
  retired; [the archive README](../../patches/xboxrecomp/README.md) already says so.
- M4 is closed by D45, with its explicitly retained backlog. M6 is next, then M5
  Proton/Steam Deck and M9 macOS. These future targets are not current support.
- The validated input is the USA Xbox dump in
  [dump-manifest.json](../../config/dump-manifest.json), title ID `45410049`, XDK
  5849. Do not imply every region or revision is supported.
- Release is source only. Users supply their own game dump and generate the
  translated C locally. Game files, generated game code, captures and compiled
  game executables are not release contents.

Frame statistics and owner listening/rendering acceptance are evidence from the
documented machine and routes, rather than universal performance or audio-parity
guarantees. The acceptance report already makes that distinction well.

## Corrections to public entry points

| File | Finding | Minimal correction |
| --- | --- | --- |
| [README.md](../../README.md), lines 3–9 | Steam Deck is described as part of the port; status says nothing appears on screen. | State validated Windows support and accepted gameplay/rendering status. List Deck/Proton and macOS as later milestones. |
| README, quick start | Missing portable data-path setup, extractor placement, repo-local game junction, Release selection and exact fork model. | Link the canonical workflow; give a short clone/build/play sequence consistent with it. Set `DEFJAM_DATA` before extraction or environment initialization. |
| README, prerequisites | VS 2022 is required even though accepted builds use VS 2019/MSVC 14.29. Python `3.10+` is stated without a matching tested matrix. | Document tested versions: VS 2019 worked locally; CI uses Python 3.12 and local work uses 3.13. Distinguish tested versions from any broader compatibility claim. |
| README, roadmap | Old milestone ordering and shortened M6 wording obscure the accepted next work. | Link the roadmap and current status; preserve M6's established definition and order. |
| README, toolkit attribution | Only upstream is linked even though the build consumes a maintained fork. | Credit upstream xboxrecomp, link the fork and pinned commit, and link toolkit license/notice files. |
| [03-workflows.md](../03-workflows.md), lines 3–19 | Owner-specific absolute paths; first run is Debug with a 10-second watchdog. | Use a generic example external data directory, an explicit repository working directory, and separate normal Release play from bounded diagnostics. A watchdog run is intentionally short. |
| Workflows, setup | Scripts fall back to `C:\Users\Vlad\code\defjam`; the extractor is not installed by `pip`. | Explicitly set `DEFJAM_DATA`, install/place `extract-xiso.exe`, verify the dump and create the ignored `game` junction. Do not let a new user discover the owner-specific fallback by failure. |
| Workflows, bring-up section | Reads `run-*.log`; important runtime diagnostics are in `.log.err`. Toolkit Python module commands also depend on working directory. | Name both log streams, prioritize `.log.err` for diagnosis, and give the required working directory for toolkit commands. |
| Workflows, optional tools | Ghidra/JDK and xemu are described as already installed. | Label these as optional developer/reference tools with the setup state of the original workstation, rather than public prerequisites. |
| Workflows, watchdog table | "When the title stops making progress" suggests a progress-sensitive detector. | Describe the existing timer as a bounded diagnostic deadline; it can fire during a normally running title. |

The recent `run.ps1` fix is current: absent `RECOMP_VBLANK`, `RECOMP_PB_EXEC`,
`RECOMP_PB_D3D11` and `RECOMP_USB` receive defaults, explicit overrides are
preserved, and temporary values are removed on exit. Normal public play should use
that script. Direct executable launch still requires the runtime environment.
Do not imply setting all presence-based runtime flags to `0` disables them.

GitHub source archives do not embed submodule contents. Recommend a recursive
clone or an exact release-tag checkout followed by
`git submodule update --init --recursive`. Do not advertise the automatic ZIP as
a complete ready-to-build checkout unless release tooling deliberately packages
the pinned toolkit sources and their notices.

## Current, planned and historical documentation

[01-plan-review.md](../01-plan-review.md) is explicitly a 2026-09-17 research review.
Keep its original toolkit maturity, toolchain, function-count and legal observations
dated. They should not become undated compatibility or legal assurances in the
public README. Its living roadmap can remain authoritative without refreshing the
historical review or changing milestone gates.

[02-test-plan.md](../02-test-plan.md) needs a small current-implementation note or
table, separate from intended test levels and milestone exit criteria:

- Current root CI checks source hygiene, 67 synthetic Python tests, Windows MSVC
  native save compatibility (19 tests) and the runtime-only build. Full game
  builds and game regressions require the private dump and are local.
- Root runtime CTest currently has no registered targets. A successful CTest
  invocation therefore is not evidence that the named kernel/audio/D3D fixtures
  ran in CI. Standalone fixture results and the toolkit CPU suite are recorded
  local acceptance evidence; distinguish them from CI execution.
- Golden checking is implemented through `scripts/frame-signature.py` and
  `scripts/regress.py`, with signatures in `tests/golden/`. The PSNR/SSIM and diff
  mask description is an old plan, and `docs/checklists/*.md` does not exist.
  Link the implemented scripts and inline milestone checklist instead.
- Smoke S3 accepts device/Present markers or a positive draw count; S4 follows
  S3 without a crash. Those coarse log stages do not independently prove every
  formal Present, sustained-progress or gameplay criterion. Keep formal gates
  intact while describing actual smoke grading accurately.
- The xemu section reports the observed 2026-09-19 baseline and limit. Claims
  that an issue remains open, no emulator can reach a screen, or no fix exists
  should stay dated unless independently verified. The PTIMER description is
  historical bring-up evidence, not the current register/interrupt architecture.
- The M3 xemu comparison in docs01 and the xemu limitation in docs02 disagree.
  Explain the current native golden/console comparison evidence alongside that
  historical mismatch; do not silently redefine the M3 exit criterion.

[05-reference.md](../05-reference.md) correctly identifies itself as reference,
and its fork/replay/save sections are current. Bound its older diagnostic facts:

- Dynamic heap addresses "stable across runs," the 402 jump-table count, the
  broad "ruled out" list, and the 27-second lift/ten-minute full-loop timings
  belong to the earlier investigation and workstation. Date or label them as
  historical observations rather than current runtime guarantees.
- Describe the current executor/adapter directly. Historical patch numbers
  0003/0004 can link the ledger, but should not suggest the current build replays
  those patches.
- Keep the M4d backlog and accepted closure distinction. The rare crash, two-pad
  play and three-fight memory check must not disappear under an unqualified
  "everything supported" claim.

The original plan, worklogs and dated research need no wholesale rewrite. A clear
index and small current-status notes prevent readers from treating them as setup
instructions.

## License, credit and provenance

- [Root LICENSE](../../LICENSE) already limits its MIT grant to this repository's
  own code, identifies the toolkit's separate licenses and excludes game data.
- The pinned toolkit contains `LICENSE`, `NOTICE`, `CONTRIBUTORS` and
  `LICENSES/LGPL-2.1.txt`. Its NOTICE lists xemu-derived LGPL components, their
  copyright holders, and reference/algorithm provenance. Preserve these files
  in any source bundle that embeds toolkit content.
- A short public credits paragraph can credit xboxrecomp's upstream creator and
  contributors, the maintained Def Jam fork, and xemu-derived components by
  linking their canonical notices. Copying an exhaustive contributor list into
  the parent README is unnecessary.
- Avoid a single undifferentiated "all MIT" label or an absolute "no emulation"
  claim. Static recompilation describes the game CPU code; the runtime still
  supplies kernel/hardware models and an optional CPU vertex interpreter.
- Keep dump hashes, synthetic fixtures, signature JSON and source provenance
  public. Keep the already ignored dumps, assets, generated C, executables,
  screenshots and save material outside release payloads. The current CI hygiene
  gate is useful evidence of this source-release policy, not a full license audit.

No external license interpretation or current emulator/platform claim was
verified in this local review.

## Minimal public documentation structure

1. **README:** current supported platform/status, source-only/own-dump model,
   concise prerequisites and build/play entry, known limitations, roadmap link,
   credits/licenses.
2. **`docs/README.md` index:** group the existing documents by purpose. Link
   workflows03 for setup/play, reference05 for architecture/diagnostics, test
   plan02 for implemented automation and formal gates, roadmap01/backlog04,
   rebase06 and its accepted outcome. Label original plans, research and worklogs
   as dated records. Link PROGRESS as the detailed living project record.
3. **Workflow03:** the single canonical portable setup/build/Release-play guide,
   followed by developer/test/diagnostic workflows. README should link it rather
   than duplicate every command.
4. **Release notes:** identify the exact parent tag and toolkit pin, tested dump,
   source-only contents, tested toolchain, accepted local versus CI evidence,
   known backlog and future platforms. Link the existing acceptance report.

This requires no documentation site, duplicated research archive, new milestone
scheme or broad rewrite. README and portable workflows are the immediate public
entry-point corrections; the index and test-plan implementation note make the
remaining documentation understandable.

## Coverage

Reviewed README, root LICENSE, `.gitmodules`, PROGRESS current status/hand-off,
docs01/02/03/05, documentation inventory, patch-archive README and rebase acceptance.
Read the pinned toolkit's LICENSE/NOTICE/CONTRIBUTORS and license-file inventory.
Checked setup/build/lift scripts, current CI, dump manifest, smoke grading,
regression golden invocation and signature format only to substantiate the
documentation findings. Historical research/worklog archives were not refreshed.
