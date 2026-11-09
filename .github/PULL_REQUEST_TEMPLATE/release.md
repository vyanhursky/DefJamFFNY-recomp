## Release vX.Y.Z

<!-- Release PR for a release train (docs/releasing.md). Open with ?template=release.md, or
     gh pr create --body-file from a filled copy. Merge with a merge commit, never squash. -->

Milestone: vX.Y.Z

### Contents (merged into this branch with merge commits)

| PR | Title | Toolkit commits | Decisions |
|---|---|---|---|
| # |  |  | D-new → D |

Toolkit pin: `<sha>` on fork branch `defjam/release-X.Y.Z` (base `<sha>` + cherry-picks).

Not included (and why):

### Candidate gate

Runtime commit tested: `<sha>` · final source/tag commit: `<sha>`

Toolkit / build preset / settings / fixture: `<identity>`

Evidence reused from: `<report and tested commit, or first full run>`

Later differences and focused verification: `<why the tested runtime remains qualified>`

| Gate | Platform | Result | Log / run |
|---|---|---|---|
| CI (incl. three setup builds) | GitHub | | |
| Full `regress.py` | Windows | | |
| Full `regress.py` | macOS | | |
| Full `regress.py` | Steam Deck / Linux | | |
| Setup install from CI artifacts | Windows | | |
| Clean Update from vPREV | Windows | | |
| Owner play-test | | | |

Reuse an applicable full result across merge/tag/release metadata, docs,
packaging and behavior-preserving compiler fixes; see `docs/releasing.md` §4.
Do not rerun the full suite for a new SHA alone. Before any repeat full run,
record the invalidating runtime change/failure and why focused checks are insufficient.

### Records

- [ ] `PROGRESS.md`: decisions numbered, work log, §0, §7 hand-off
- [ ] `CMakeLists.txt` version, `docs/releases/vX.Y.Z.md`, README setup link, issue links and release qualifications
- [ ] `python -m pytest -q tests/unit` and `python scripts/check-source-tree.py`

### Checklist

- [ ] No game data, saves, captures, memory dumps or translated game code, in files or in text.
- [ ] AI assistance disclosed, if used.
