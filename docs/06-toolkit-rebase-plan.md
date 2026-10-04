# Plan: rebase onto upstream xboxrecomp, then upstream our generic fixes

Approved by Vlad on 2026-10-02 (D46). Background and the overlap analysis are in
`docs/research/upstream-xboxrecomp-2026-10.md`; read that first. This is the work plan, written so an
agent that has never seen this project can carry it out. Read `CLAUDE.md` and `PROGRESS.md` §7 before
starting.

Execution review approved 2026-10-03 (D48). The source reports
`docs/research/toolkit-rebase-{lifter,runtime,gpu}-review.md` refine the overlap
claims below. Consolidate final behavior into logical commits, preserving a
mapping for all 108 historical patches; the old patch filename is not always a
single semantic unit. Keep upstream fixes and the working D3D11/harness path.

## Goal

1. Our toolkit changes stop being 108 patch files against a two-week-old pin (`6f55eaa`, 2026-09-15) and
   become commits on top of upstream `main` (`sp00nznet/xboxrecomp`, `1409a7d` at 2026-09-30, or newer).
2. Whatever upstream already fixes is dropped from our set; the rest is ported to upstream's code.
3. The game works at least as well as before: `python scripts/regress.py` 9 of 9, then Vlad's play-test.
4. Our generic fixes go upstream as small pull requests.

Not a goal: changing game behaviour, new features, M6 work. Keep this branch to the move.

## Ground rules (all from CLAUDE.md; repeated because they matter here)

- The repository will be public. Never commit disc images, XBEs, `.viv/.mad/.xsh`, lifted C (`src/recomp/gen`),
  logs, build output or captures. `git add -A --dry-run` before every commit. Never name the site the dump
  came from; it is "the user's own dump".
- One commit per logical change, message written to a file and passed with `git commit -F`, ending with the
  `Co-Authored-By` line the session gives you. Vlad has given standing permission to push to `origin main`
  of this (private) repository.
- Update `PROGRESS.md` in the same turn as the work (§6 entry via `python scripts/worklog-add.py <file>`,
  §0 rows, §5 questions, §7 hand-off at the end of the session).
- Game data is outside the repo at `C:\Users\Vlad\code\defjam` (`DEFJAM_DATA`). The save area there holds
  Vlad's profiles; the harness's save guard protects it. Do not run the game while Vlad says he is using
  the machine.
- Build from Bash as `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/build.ps1 [-Preset
  win-x64-release]`; re-lift with `scripts/recomp.ps1`. Kill `defjam_recomp.exe` before building.

## Decisions

- **Fork owner and visibility: decided by Vlad on 2026-10-02.** The fork lives on his GitHub account
  (`vyanhursky`) and is **public** from the start. Creating it is covered by that answer.
- **Still to confirm with him, every time:** opening a pull request upstream (or a batch he names). It
  publishes on his behalf.

## Phase 0: preparation (no behaviour change)

1. Confirm the baseline is green: `python scripts/regress.py` on the current build must be 9 of 9. Keep the
   `logs/regress-*.txt` and the captures in `logs/shots/` from it as the "before" picture: copy
   `logs/shots` to `logs/shots-before-rebase` (both stay out of git).
2. Take captures of the screens the goldens do not cover, for comparison later:
   `python scripts/harness.py run intro --png`, `run fight --png`, `run crib --png`, `run gym --png`,
   `run unlock --png`. Copy each `logs/shots/<route>` aside as above.
3. Fork: `gh repo fork sp00nznet/xboxrecomp --clone=false` (public, on `vyanhursky`, as Vlad decided).
4. In the submodule: `cd tools/xboxrecomp`, `git remote add fork https://github.com/vyanhursky/xboxrecomp`,
   `git fetch origin`, `git fetch fork`. The submodule's working tree today is the pin plus all 108 patches,
   uncommitted, including eleven untracked source/test files. **Save it before switching**:
   preserve every changed/untracked source in `ours-on-pin`, review `git add -A --dry-run`,
   stage the explicit source allowlist, and commit with a message file. A plain stash
   misses new source files; an alternative stash must include untracked files.
   That branch is the reference for "what we had".
5. Preserve generated output, builds, captures and the complete writable save root
   outside Git. Run against a verified disposable copy of the save root, keeping the
   harness guard active. Reconstruct the ordered patch history in an isolated LF
   worktree before three-way replay: 190/231 preimage blobs were missing in the original
   object store, affecting 97 patches. Verify all 52 final files, including new files,
   against the saved live baseline; then check all preimages are available. A final-state
   snapshot alone does not provide the intermediate blobs.

## Phase 1: carry our changes onto upstream main

Work on a branch `defjam/rebase-2026-10` in the submodule, created from `origin/main`.

Go through `patches/xboxrecomp/0001-*.patch` .. `0108-*.patch` **in order**. For each patch:

1. Review the historical change and upstream equivalent before attempting
   `git apply --3way ../../patches/xboxrecomp/NNNN-*.patch`. The reconstructed
   history supplies the required blobs. For heavily overlapping families, port the
   final behavior as logical commits rather than reintroducing superseded intermediate
   implementations; map every original patch to those commits in the ledger.
2. Decide which of three outcomes it is, and record it in the ledger (below):
   - **applied**: clean, or with conflicts you resolved. Commit it as its own commit, message
     `NNNN <patch title>` plus a line saying what was adjusted.
   - **covered upstream**: upstream already fixes the same bug (the research doc's table lists the likely
     ones: 0005, 0007, 0009, 0014, 0016, 0019, 0023, 0024, 0033, 0035, 0036, 0038, 0044-0047, 0063, 0065,
     0079, 0082, 0097 in part, 0107, 0108, and others). Read upstream's code and confirm it really covers our
     case before dropping. If it covers part, keep the rest as a smaller commit.
     Do not use `git checkout .` to discard a three-way application: it updates the
     index too. Restore explicit affected tracked paths in both index and worktree
     from the checkpoint, and preserve/check new files before removing them. Use an
     isolated worktree so a failed port cannot alter the baseline.
   - **reworked**: the code it changes no longer exists in that shape (most likely in
     `src/kernel/nv2a_pb_exec.c`, `tools/recomp/translator.py`, `tools/recomp/lifter.py`). Re-implement the
     same behaviour on upstream's code, guided by the patch's own comments (every patch says what bug it
     fixes and why). Commit as above, saying "reworked for upstream's <thing>".
3. Keep going; do not try to build after every patch. Build checkpoints: after 0030, 0060, 0090, 0108.

**The hard part is the GPU executor.** Upstream's `nv2a_pb_exec.c` grew its own vertex programs, register
combiners, four texture stages and clipping (upstream PR #152), YUV sampling (#103), DRAW_ARRAYS (#81),
P8 palettes (#145), and fixed the primitive numbering (#102: our strips may have been drawn wrongly in
some path). Ours forwards everything to the D3D11 translator (`src/nv2a/nv2a_pgraph_d3d11.c`) and the
D3D8-on-D3D11 layer, with vertex programs as generated HLSL. Do not try to merge two executors line by
line. Instead: take upstream's executor as the base, and port our *forwarding* path onto it (patches 0003,
0004, 0019-0028, 0031, 0034-0037, 0049-0062, 0073, 0078-0101, 0105, 0106, in that order), keeping
upstream's CPU-side features where they do not conflict. Where both implement the same thing (combiners,
texture stages), ours is what drives D3D11 today and must keep working; upstream's may be a software path
we do not use. If unsure which path a feature runs in for this title, `RECOMP_PB_BATCH_DUMP=shot` (see
`docs/05-reference.md`) shows what reaches the translator.

**The lifter.** Upstream reworked flag handling (#77, #86, #114, #122, #159), comparisons (#124, #150,
#151), x87 (#47, #49, #126, #149) and function recovery (#111-#116, #163, #164). Our lifter patches 0008,
0009, 0066, 0075, 0083, 0090, 0095, 0108 overlap. Run the toolkit's tests after each lifter commit:
`cd tools/xboxrecomp/tools/recomp && python -m pytest -q` (196 pass on our pin today). Our entry hooks
(0095) are used by this game (`src/recomp_manual.c`: `sub_0021EB90_enter`, `sub_002203C6_enter`); they
must survive.

### The ledger

Keep `docs/research/toolkit-rebase-ledger.md` as you go: one row per patch, with
applied / covered upstream / reworked / split / consolidated outcomes, the replacement
commit(s) or upstream PR/commit, and source/test evidence. It is the record of what
happened to each patch and the input to Phase 4.

## Phase 2: point the project at the result

1. Push the branch to the fork: `git push fork defjam/rebase-2026-10`.
2. In the parent repo, point the submodule at the fork: edit `.gitmodules` (url to the fork, branch
   `defjam/rebase-2026-10`), `git submodule sync`, and commit the submodule pointer. **This replaces the
   rule "never commit the submodule pointer"**; update `CLAUDE.md` §4 step 7 and §2, and
   `docs/05-reference.md` "Standing items" item 3, in the same commit.
3. Retire the patch mechanism: `scripts/apply-toolkit-patches.ps1` and the CI step
   "Apply our patches to the toolkit" (`.github/workflows/ci.yml`) are no longer needed; the CI job should
   build the submodule as checked out. Keep `patches/xboxrecomp/` in the repo as history (add a README
   saying they are superseded by the fork branch and the ledger), or move them to
   `patches/xboxrecomp-archive/`. `scripts/toolkit-patch.py` becomes unnecessary: delete it and its mention
   in CLAUDE.md, or leave it with a note.

## Phase 3: retest

1. Full re-lift (`scripts/recomp.ps1`), build both presets, then `python -m pytest -q tests/unit`.
2. Before running the game, check `config/seed_functions.json` and `scripts/analyze.ps1` still work with
   upstream's disassembler changes (#111-#116, #164 changed how seeds are trusted). If the function count
   or the number of unresolved targets changes a lot, investigate before going further: compare
   `[ICALL] Failed to resolve` counts in a boot log against a pre-rebase log.
3. `python scripts/regress.py` must be 9 of 9. Then compare the captures from Phase 0 with new ones (same
   routes, `harness.py montage` side by side). Differences are either fixes (upstream's) or regressions;
   explain each in the §6 entry.
4. A soak: `python scripts/harness.py soak --boots 20 --preset win-x64-debug`.
5. Ask Vlad for a play-test of the release build: Story route, a fight, the menus. Only after his OK does
   the rebase count as done (§0 row, D-decision entry).

If it goes badly (the game regresses and the cause is not found in reasonable time), the old state is one
command away: point the submodule back at `ours-on-pin` / the pin plus patches. Do not leave `main` broken:
do the work on a branch of the parent repo too (`git switch -c toolkit-rebase`) and merge to `main` only
when Phase 3 is green.

## Phase 4: pull requests upstream

Only after Phase 3. Candidates (generic, not about this title), in rough order of value:
- 0103 a kernel timer's signal lost on re-arm (and the lazy shadow-event race)
- 0104 a closed directory handle drops its search
- 0105 batches over 4,096 indices (and 0101 saying so)
- 0106 texture filters passed to D3D11
- 0100 an evicted texture taken off every stage (use-after-free)
- 0092 constant-colour blending; 0086 surface clip as scissor; 0081 stencil; 0089 packed normals;
  0097 point sprites (if upstream's DRAW_ARRAYS does not already cover them)
- 0095 lifter entry hooks; 0090 a saved flag result before the register is overwritten; 0083 caller-cleans
  indirect-call skip
- diagnostics: 0088 pixel probe, 0084/0031 batch dump, 0091 debug-layer report
Rules for each PR, from upstream's `CONTRIBUTING.md` and its history:
- Small and single-purpose, one bug per PR, branched from upstream `main` (not from our rebase branch).
- Title and description in upstream's style (look at merged PRs #140-#156): the symptom, the cause, the fix,
  and the title it was found on ("Def Jam: Fight for NY"), with a test where the toolkit has one for that
  area (`tools/recomp/test_*.py` for the lifter).
- Provenance: say the code was written with an AI assistant, that xemu was read as a hardware reference and
  nothing was copied from GPL projects (Cxbx-Reloaded, xemu's GPL parts).
- No game data, addresses only as explanation.
- **Opening a PR is publishing on Vlad's behalf: confirm each one (or a batch he names) with him first.**
  Track them in the ledger (PR number, state).

## Done means

- The submodule points at the fork branch; the patch mechanism is retired; docs say so.
- `scripts/regress.py` 9 of 9 on both presets, a 20-boot soak clean, Vlad's play-test OK.
- The ledger accounts for all 108 patches.
- PROGRESS.md §0 has a row for it, a D-decision records the outcome, §7 is rewritten.
- Pull requests opened for the agreed candidates, numbers in the ledger.
