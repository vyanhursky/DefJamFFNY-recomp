# Fighter Mod Support handover — November 8, 2026

Read this and the [implementation checkpoint](fighter-mod-m5-2026-11-08.md).
The [November7 handover](fighter-mod-handoff-2026-11-07.md) remains authoritative
for approvals, architecture, immutable inputs, workspace boundaries and operating
rules. This continuation supersedes its implementation status where stated.

All work remains local. No push, public PR, merge, publication or release is
authorized. The earlier six-hour machine window ended09:37 Pacific/17:37UTC November8.
The owner subsequently renewed continued local work, requested a playtest shortcut
and confirmed the creation-guide draft; no new timebox was specified.
Never run games concurrently, kill
another checkout's game, or edit/build native C/run C fixtures while a game runs.
Use disposable supervised saves and the full save guard. Preserve the routine
stock-development regression waiver; it does not waive final RC acceptance.

## Source state

- Runtime `research/custom-fighter-mods`: latest fixes203821a/aa35b4e, cinematic implementation4075ad3; earlier
  1539007,3c67a3b,bb48186 and224fd98 contain this session's general adapters,
  compiler, source accounting, setup discovery, complete grid-model tail and
  harness corrections. A later documentation-only handover commit may follow.
- Tools `feature/fighter-authoring-m5`:5d6cc06, converter implementation89b0b06, following00debce,e74a646,4cbba85.
  Guide and PROGRESS are current; AGENTS/CLAUDE remain identical.
- Toolkit remains clean at d569ca10811cef67ec4e9fa2173088c2f9fd0580.
  No generated C, native executables, game data or converted pack is tracked.
  Runtime feature-branch PROGRESS was intentionally unchanged.

## Deliverable and reproduction

Ordinary folder `logs/fighter-m5-vendetta-absolute-1108`:46fighters,285resources,
4651files. ZIP `logs/vendetta-roster-1.0.0-absolute-1108.zip`, SHA256
**d493f0aa580748a29a6a45bf99c34f8274d87049e5df70abd04e931c2cfe0c01**.
This supersedes the e288a716 native-venue draft and all earlier packages.

Installed creator report `logs/fighter-m5-installed-conversion-absolute-1108.json`
contains stable mapping and full validation; packaging receipt has the ZIP basename
plus `-package.json`. Reproduce into a NEW folder using
`./logs/fighter-m5-reproduce-conversion-1108.ps1 -Out C:/work/new-vendetta`.
Installed wheel in Tools `logs/m5-absolute-wheel` has SHA256
2d2952ed66abda71b731ce27afa22aac0a74c65212e75de025364b1a633cdefb.
Use existing cached setuptools for offline wheel builds; set TEMP/TMP to existing
logs and PIP_DISABLE_PIP_VERSION_CHECK=1. Do not leave pip spinning after success.

`logs/fighter-m5-source-accounting-absolute-1108.json` rechecks all1883input hashes:
1697converted,184exactly inherited,2metadata/cover exclusions. Two dangling
606A/607A XML registrations are explicit subrecord exclusions. All24artwork
roles, voices and explicit absence, full cinematics,47paired moves, exact original
slot choices, Tier8, Crow appearance and10global tag edits are represented.
Complete source tags reconstruct byte-for-byte. Ordinary combat/AI donor reuse
is exact, not a substitute for unsupported custom content.

The owner's additional reference resolves phase4 cameras as owned absolute:
[pinned Comoria behavior](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1219-L1234).
No third-party implementation code was copied. FBZ3 and a native A3B60 posthook
preserve that behavior with actual member/output proofs. Reference phase1 D0=1
is inactive shot-count metadata in Blazin state7; own sequencing compares to4.
Do not generalize that observation to intro sequencing.

## Verification and open gates

Final focused fighter suite1424passes in42.48s; installed creator40passes.
Relift/Release build pass. Runtime source policy805tracked/0failures before this
new handover; Tools524/0. Detailed receipts/logs are in the checkpoint.

Normal installed-layout full pack plus independent pack ran Arii/Briggs through
two match epochs, first result/save/quit,23allocation release and same-process
reuse. Corrected four-participant test selected Arii, Check, retail Blaze and
Briggs, with five combat checks passing; no result/owned pair/Quit claim there.
Human slot1 subject/counterpart full graphs were evaluated. Latest absolute-camera
fixture evaluates all four human activation phases, releases32allocations to
33553888bytes and acknowledges one save; saves restore identically. Its P2
damaging-hit assertion fails. Do not report complete two-human combat acceptance.

The latest ZIP is installed in disposable `logs/fighter-m5-managed-vendetta`.
Private owner instructions/launcher: `logs/fighter-m5-owner-playtest-1108.md/.ps1`.
Separate installed-layout source plus real isolated Setup Python has71fighter
imports; overlay receipts identify changed compiler files. This is not a newly
built installer. Preserve profile adoption; never force reimport or delete markers.

Extended M5 remains open for broader actual content/audio/callback/visual tests,
created/retail/mixed full-graph contexts, language/texture coexistence, failures,
lifetimes and performance. Warm full-pack preparation is about123seconds. M6
still requires physical controls, fresh installer and platform acceptance,
final RC checks/soaks and owner playtest. Historical macOS/Deck results are not
new feature evidence; no current remote endpoint was found. Do not mark the
roadmap or complete-faithfulness ledger done from compilation or partial probes.

## Last bounded managed smoke

`logs/fighter-m5-managed-absolute-native-1108.py/.txt` runs the latest complete
candidate through the normal installed-layout helper with diagnostic ready-Blazin,
telemetry and disposable saves. Final log `run-20261108-103025.log.err` validates
all47cores/44voices/46activation sets/47cinematics/474timelines/1472member proofs/
94paired bindings. Actual cache e9e951e51a5ae66718bfb0fe66574110a709ad06e31e07616e1576ba65c18dec
has all46FBZ3full masks15/absolute masks8, all46Tier8values and four-slot choices
rechecked. Receipt `logs/fighter-m5-managed-absolute-verified-1108.json`.

The210second bound included helper preparation; it reached the selector but no
match.40presentation counters min107/median120/max120; zero reported faults and
save guard restored identically. This closes latest-pack normal startup only.
The game and native helper are stopped; no background continuation remains.
Check actual process state again before any future C/build/fixture work.

## Later owner-requested continuation

The confirmed beginner guide was reviewed throughout, not just its newest
appendix. Main sections now reflect full graphs,24artwork roles, explicit texture
isolation, Tier, current native observations and correct export-fragment placement.
Manual BT4 export defaults to native-venue; the guide explains the owned-absolute
edit and separate asset subfolders. A new installed two-fighter starter/package
command proof passed. Runtime save reads now retry transient permission denial
for <=0.9seconds;99focused tests retain rejection of corrupt/persistently denied
receipts and other I/O failures. Native failed attempt110250and recovered retry
110817are retained in the checkpoint. Decoder changes preserve the complete
e9e951e5/ae9b00e1cache/UI bytes; measured warm preparation126.49seconds remains open.

Latest normal full-pack human run111731passes all six combat assertions for
Arii/Briggs. Both humans walk and land input-linked damaging hits. Both entrances
pass full-context proofs; native match Quit returns to menus and releases24owned
allocations, with one acknowledged save and identical guard restoration. No new
owned activation/pair or natural-result claim; application later ends at harness
bound and helper recovers the last complete generation. Receipt:
`logs/fighter-m5-managed-human-live-1108-verified.json`.

Desktop shortcut `Def Jam - Fighter Mod Playtest.lnk` is created and actually
launched/visually verified. Normal launcher shows vendetta-roster46fighters and
independent starter1fighter both enabled. It uses the disposable managed data,
normal input and normal unlock-all test setting. Settings persist across launches;
pack enable/disable remains available. Wrapper and verified launch receipt are
in ignored logs; owner instructions `fighter-m5-owner-playtest-1108.md`.
Launcher closed successfully; no owned game/helper/wrapper left running.
No source publication or release. Remaining roadmap gates above still apply.
