# Workshop and pending runtime PR integration

On 2026-11-10 the owner approved GPLv3-only for the separate Fighter Workshop
and merging all pending Workshop/runtime PRs. This supersedes earlier no-merge
wording in those PRs. It authorizes source integration, not a new release or
publication of artwork, saves, compiled game executables or private projects.
The runtime's own software license is unchanged.

## Included runtime work

| PR | Scope | Evidence and remaining limits |
| --- | --- | --- |
| #202 | glibc decode-buffer mmap/trim policy | Deck five-match comparison passes; owner's Game Mode hitch/pop-in review remains open under #166. Windows/macOS heaps are unchanged. |
| #213 | Standalone CAF recipes and portraits | Original native export/selection/combat and profile evidence retained in the PR. |
| #217 | CAF textures, outfits, finishers and complete UI art | Native Windows menu/battle/result/save and multiplayer UI evidence retained. |
| #218 | Retail resource authoring and HD RGB atlases | Private Windows pilot/export/installation pass; private pilot art/logo failures and unverified supplied paired/victory clips remain explicit. |
| #219 | Template-bound facial geometry | Native two-participant position/ownership proof; arbitrary topology and broader facial cinematic/outfit coverage remain experimental. |
| #220 | Retail movesets for authored and Story CAFs | Native standalone/direct-profile pilots; broader career/rematch/platform qualification remains deferred. |
| #221 | Independent voice, AI and cinematic authoring | Typed compiler/native identity fixtures; complete CAF v6 mixed gameplay remains for joint testing. |
| #222 | Thunderstore ZIP wrappers | Package validation, capability fallback and real-data throwaway installation; actual launcher/storefront rollout remains separate. |
| #223 | Grid-state routing and actual portrait references | Synthetic independent-state rasters and original-reference checks; full interactive 2/3/4-player state review remains unqualified. |
| #224 | Retail appearance overrides and extra outfits | Native original-menu selection/battle checks for Pockets, exact identities, guarded save restoration and canonical-progress C fixtures. |

The six Workshop PRs (#3–#8) supply the corresponding editors and workflows.
The Workshop additionally retains its own dependency licenses and game-art
exclusions when moving from MIT to GPL-3.0-only. Existing MIT releases keep their
original terms. Runtime use of the Workshop authoring API remains a separate
process/tool contract.

## Integration and validation policy

Use merge commits, retaining every reviewed source head and the existing pinned
xboxrecomp revision. The final fighter head incorporates the already-reviewed
Linux, installer and Grid changes before its combined CI run. This avoids
silently replacing a toolkit pin or treating isolated passing checks as proof
of the combined source. Intermediate stack merges whose tree is identical to
the qualified final head reuse that evidence; a new merge SHA does not require
another identical native regression.

The owner previously deferred broad regressions to joint testing. Preserve
that decision and the concrete native evidence in each feature's research/PR
record. Hosted game-free builds do not qualify untested gameplay platforms.
Do not close #166 or publish a release merely because this source integration
is merged.
