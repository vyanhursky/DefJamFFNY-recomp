# Publication audit: tracked source and reachable history

Date: 2026-10-04. Repository: `defjam-recomp`. Audit base:
`5bffcba3e261aa94911f2ed1c5e0ab778b1dd932`.

**Do not change the original repository's visibility yet.** Its reachable history
and current research documents contain copied guest-function bodies/disassembly.
They contradict this project's explicit prohibition on publishing lifted game
code. Removing the current copies alone does not remove their historical blobs.
The proposed publication approach retains the original privately and prepares a
sanitized public snapshot; the repository rename/new-public-repository transition
still requires the owner's approval. This report and map support that approach. No history rewriting,
publishing, visibility change, release, build, or game run was performed here.

## Publication outcome, 2026-10-04

Vlad approved a different public name (D58), so the original repository was
not renamed. `vyanhursky/DJFFNY-recomp` remains PRIVATE with its development
history. Fresh PUBLIC `vyanhursky/DefJamFFNY-recomp` starts at sanitized root
`67c2672`; v0.1.0 includes the README attribution correction at
`89688c040f42629dfc369648cfb60004a841967b`. None of the original parent history
is reachable from it. The source v0.1.0 Release is published after public CI
7/7 and source-release workflow9/9. The two supplied README visuals are an
explicit owner-approved exception with exact paths/SHA-256 fingerprints;
no general game-data or capture exception was introduced.

## Inventory and scanner scope

| Item | Count |
|---|---:|
| Current tracked entries, including one toolkit gitlink | 244 |
| Distinct historical paths | 255 |
| Reachable commits | 251 |
| Reachable trees | 887 |
| Reachable blobs | 697 |
| Total reachable blob content | 27,667,022 bytes |
| Blob plus commit content scanned | 27,913,623 bytes |
| Non-UTF-8 or NUL-containing blobs | 0 |
| Current tracked Markdown files | 68 |
| Markdown fenced blocks inspected, including indented fences | 197 |

The local refs audited were `main`, `toolkit-rebase`, and their cached origin
counterparts. Origin/main matched the audit base; toolkit-rebase matched
`c70f86d5ed18485dbe2b0ff98e99da5f32e5c2a6`. All objects reachable from `--all`
were enumerated and the blob/commit contents scanned with `git cat-file --batch`.
No potential secret values or lifted bodies were emitted by the content scanner.

An optional read-only remote-ref advertisement failed immediately because this
agent's sandbox could not connect to GitHub. Thus this is an exhaustive audit of
**locally reachable history**, not a claim about unadvertised GitHub PR refs,
server caches, reflogs, or unreachable objects. The parent is verifying remote
publication state separately. The already-public toolkit fork was outside this
parent-history scan; its current license/attribution files were inspected.

## Assets, binaries, secrets and private references

No tracked or historical path matched the inspected game/build/log/save/capture
directories or asset/binary/archive extensions. The generated directory has only
its empty tracked `.gitkeep`; no generated translation unit was tracked. All
697 blobs decoded as UTF-8, with no NUL-containing blobs and no long encoded
binary-content candidates. The largest blobs are versions of the September
worklog, below 240 KB each.

The scans found no private-key headers, GitHub/AWS/Slack/OpenAI token patterns,
credential-bearing HTTP URLs, long inline authorization values, or plausible
literal password/API-secret/token assignments. No Git LFS pointers, UNC-share
paths, private-IP candidates, or known dump-source-site-name candidates matched.
These are bounded pattern checks, not a guarantee that every possible credential
format has been recognized.

URL hosts and GitHub repository references were inventoried without printing
query credentials. The owner's private parent repository is intentionally named
in documentation and origin; that is project identity, not a credential. A fresh
public snapshot should update its own links and avoid directing readers to
private PRs. References otherwise point to development/reference projects and
public documentation. No unrelated private-repository credential or internal
service URL was identified.

Windows user-directory paths occur in 20 historical source/document paths.
They disclose the maintainer's workstation layout, already reflected in the
repository's name/license metadata. Prefer portable examples in the public
snapshot; they are not the same blocker as copied guest bodies.

## Copied guest-code documentation: concrete blocker

The initial function-definition scan found complete or shortened guest bodies
in these eight reports. Their prose explicitly describes reads/quotes from
`src/recomp/gen/recomp_*.c`, including original ranges and generated-file lines.
They are not maintained native hooks in `src/recomp_manual.c`.

| Report under `docs/research/` | Representative original fence ranges | Evidence |
|---|---|---|
| `codeseg-corruption.md` | 146-181; 264-271 | Full `001E9040` body and `001E9E70` tail wrapper, cited to generated source |
| `m3-command-pointer.md` | 32-46; 138-147; 155-170; 203-236 | Pointer-clear/read methods and three constructors read from the lifted image |
| `m3-command-poster.md` | 86-100; 113-123; 133-146; 300-332 | Constructors and full `0019E8E0` method, explicitly labeled READ/generated source |
| `m3-frontend-wait-loop.md` | 122-139 | Guest handle wrappers `001EDD70` / `001EDD40` |
| `m3-level0-load.md` | 24-49 | Guest string/loader wrapper `001423F0`, cited to generated source |
| `m3-node-lifetime.md` | 192-240; 255-310; 320-356 | Full linked-list methods `00146910`, `00146C30`, `00146C90` |
| `usb-port-giveup.md` | 30-58 | Guest/XDK `002837AE`, described as read in full |
| `usb-slot-status.md` | 17-35; 64-119; 196-227; 231-249 | Full guest/XDK slot and retry helpers |

Broader inspection found additional partial excerpts and indented fences.
The machine-readable map is:

`logs/rebase-work/public-redaction-map.json`

It contains path/range/classification metadata only, with base HEAD, document and
block hashes. It identifies **132 conservative redaction candidates across 21
Markdown files, totaling 1,862 fence-body lines**: 102 generated-C-shaped excerpts,
5 guest-disassembly excerpts, and 25 derived behavior/pseudocode blocks. The
latter category includes reconstructed control-flow descriptions and live-state
examples; it is not a claim that every such block is a verbatim copied body.
Replace these blocks with paragraph summaries while retaining factual addresses,
field layouts, observed behavior, findings, and uncertainty.

The 21 mapped documents are the eight above plus `d3d-pushbuffer-wrap.md`,
`m2-vblank-isr.md`, `m3-flash-notification.md`, `m3-main-loop-exit.md`,
`m3-movie-display.md`, `m4-usb-enumeration.md`, `m4a-apt-matrix.md`,
`m4b-controller-ports.md`, `shutdown-spin.md`, `tutorial-task-completion.md`,
`usb-enumeration-dpc.md`, `xemu-loading-screen-freeze.md`, and
`docs/worklog/2026-09.md`.

The map also identifies four inline measured USB descriptor byte sequences at
`usb-slot-status.md:278,299` and `docs/worklog/2026-09.md:558,736`. These are
hardware-model protocol output, not game artwork/assets. The parent reviewed and
retained them as protocol facts; they are not an unresolved guest-byte blocker.
No raw instruction-byte fenced block was identified.

The map retains the generic manual-dispatch example in
`m2-render-path.md:137-148`. Maintain the native hooks and synthetic tests:
`src/recomp_manual.c` contains native replacements/diagnostics, not copied
generated bodies; `tests/unit/test_lift_audit.py:1` explicitly identifies its
fixture strings as synthetic; patch 0095's function definitions are synthetic
manual-entry-hook test inputs. Do not delete these solely because they use a
guest-address-shaped symbol.

Historical reachability is confirmed: the eight reports' guest-shaped bodies
exist as reachable blobs, and report changes appear in seven reachable commits
(`f7aeb9b`, `a9fb885`, `cc85169`, `06931ad`, `19e1398`, `3299552`, `0708e69`).
Publishing the original Git history would expose them even after current cleanup.

The parent subsequently applied all 132 mapped fenced-block replacements across
21 documents, checking the recorded hashes before editing. Surrounding findings
and address/layout facts were retained. This deliberately conservative cleanup
also covered derived pseudocode, not only verbatim bodies. Parent-reported current
source-policy checks inspected 243 tracked parent source files with zero failures;
the default project suite reported 67 passes and 19 native-test skips. These are
parent-supplied closure results, not tests run by this reviewer. The ignored map
remains a record of the pre-redaction ranges, which no longer describe the current
line positions. **The original reachable-history blocker remains unchanged.**

## Author and coauthor metadata

Full email addresses were not printed. Across 251 commits:

- The maintainer has three distinct author/committer email identities: corporate
  domain (231 author plus 231 committer records), Gmail (19 plus 19), and GitHub
  noreply (one author record).
- GitHub supplies one separate service committer identity.
- 241 `Co-authored-by` trailers share one Anthropic-domain identity, with three
  Claude model display labels. They are agent attribution, not another human
  maintainer identity.

The corporate-address exposure is real publication metadata, but is not an
additional original-history blocker when that repository remains private. A
fresh snapshot can use the maintainer's GitHub noreply identity and preserve
contributor credit in prose. Do not misattribute the original toolchain or its
third-party sources when replacing history with a snapshot.

## Credits, license and patch provenance

The parent `LICENSE` names Vlad Yanhursky and limits its MIT statement to project
code. Its footer identifies the separate toolkit and xemu-derived LGPL components.
The pinned gitlink is the public fork commit
`aa1a1b91dea9fd266acb3a3fe51dfcec3b2e6bbc`.

The checked-out toolkit retains its MIT license/copyright, `NOTICE`,
`CONTRIBUTORS.md`, and `LICENSES/LGPL-2.1.txt`. Its attribution names upstream
maintainer Ned Heller / sp00nznet, other toolkit contributors, and xemu-derived
components with their original copyright notices. Retain these references in
public documentation; the fork relationship alone is not a substitute for credit.

The 108 archived patches total 785,552 bytes and affect 52 distinct toolkit
paths. No removed copyright-notice line was found. Six patches modify the
explicitly LGPL-listed APU components: 0012, 0016, 0068, 0070, 0076, 0102. The
patch archive should be described as modifications to the separately licensed
toolkit, not relabeled wholesale as exclusive MIT project code. Patch 0019 cites
xemu/Cxbx for vertex-program encoding and behavior; 0024 cites xemu's USB/XID
behavior. These are provenance references, not proof of copied implementation.
No game program bytes or generated guest bodies were identified in the patches.

## Source release and final gate

A read-only in-memory `git archive HEAD` inspection yielded 243 parent files,
264 members total, and no executable/asset/binary-extension member. It also
confirmed that the archive contains only the **toolkit directory entry**, not the
submodule's source or license files. A source-only release must explain recursive
clone/submodule initialization at the pinned release commit, or provide separately
attributed matching toolkit source. Do not present the parent ZIP as a standalone
complete toolchain or attach the locally built recompiled game executable.

The parent independently verified the advertised original refs with GitHub and
`ls-remote`: main `5bffcba`, toolkit-rebase `c70f86d`, and no tags. These match the
locally audited refs; there is no claim here that a future visibility change would
erase any old server-side copy.

The concrete publication proposal is to preserve the existing repository and its
history privately as `DJFFNY-recomp-history`, then create a fresh public
`DJFFNY-recomp` containing the sanitized snapshot. The parent requires owner
approval before this repository rename/new-public-repository step. This avoids
rewriting the original development history, preserves recovery and attribution
records, and prevents the copied historical bodies from becoming publicly
reachable merely because the current tree is clean.

After approval, validate the fresh public snapshot and all its reachable objects,
keep the original/private refs out of it, update README/credit/license links, and
inspect the actual source-release manifest. This audit has not approved a future
snapshot or release merely because the original tree contains no binary files.
