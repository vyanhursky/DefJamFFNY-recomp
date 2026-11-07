# M5 continuation: explicit voice absence and conversion tools

Local continuation of the November6 checkpoint, targeting v0.15.0. **Extended
M5 and M6 remain open.** All recorded approvals, architecture and publication
restrictions in the November7 handover remain in force. No push, PR, merge,
publication or release is authorized. Runtime PROGRESS.md is unchanged.

## Verified starting state

Runtime branch `research/custom-fighter-mods` was clean at `d6c4305`, following
implementation `16720ff`. Tools `feature/fighter-authoring-m5` was clean at
`38a610e`. Toolkit was clean at `d569ca10811cef67ec4e9fa2173088c2f9fd0580`.
No native game was running. The game junction still targets the owner's
`defjam/extracted`; original data has not been modified. The handover was read
in full, with its mandatory runtime/Tools documents and instruction files.
The original `.mod` SHA256 matches42645b4a in full; all1883 extracted files,
207429829bytes, match the prior inventory exactly, with zero changed/missing files.

## Versioned explicit voice category absence

`fighter-voice-4` retains mandatory intro/extro and all three category keys.
Present banks have exactly `state`, `template_voice`, `family`, `samples`;
absent banks are exactly `{"state":"absent"}`. Missing declarations and bank
data attached to absence fail validation. Earlier voice versions stay supported.

The compiler emits no absent HDR/DAT members. Receipt schema
`fighter-voice-archive-2` and binding table FVA2 carry a three-bit mask in
Character/Taunts/Enviro order. Legacy FVA1 is all-present. Before emitting the
table, the compiler verifies present hashes/voice IDs, absent member omission,
intro/extro and consistent masks for shared IDs. Native parsing rejects unknown
bits and inconsistent shared IDs; loading deduplicates IDs and queues only
their present categories. Retail and supplemental native loading is retained.
All-absent categories with owned intro/extro are admitted and tested.

Native omission is not a category-wide mute. Unchanged original135CB0 returns
FFFF on an absent exact pair without changing its output handle.137780 returns
false and138070 stops before sample selection. Family-only135C50 ignores voice
ID; mode2 additionally checks matrix bounds through135D40.138CA0 retries the
event's explicit candidate list at138EDA. Another registered family bank or
event alternative can therefore still play. No automatic donor substitution
or playback-path suppression was added.

`scripts/fighter-voice-absence-oracle.py` runs six original generated bodies
unchanged in an ignored CPU-only executable. **34 cases pass**, covering exact
hits/misses with dirty upper WORDs, sentinel preservation, family-only lookup,
valid/boundary/FFFF matrix cases, sample-selection early-out, alternative
success/exhaustion and stop-on-first-success. Eligibility/random/sample/device
helpers are counted stand-ins. This is original-body semantic evidence, not a
native device playback test. Body SHA256
`b8ca71297c11c516674c8819349f10bdd7c2be4b765fbe16bec68f88918c7f4f`;
receipt `logs/fighter-voice-absence-oracle/comparison.json`.

## Reusable creator export and actual source corpus

`fighter-contract.py voice-catalog` exports normalized event identities only
for templates accepted by VoiceBankTemplate in the verified original archive.
The current dump yields214 templates. Physical offsets/alignment and voice ID
are excluded from event identity; category family is validated separately.
All other metadata bytes remain part of the match.

Tools `defjam-tools fighter voice` requires each category exactly once via
`--bank CATEGORY=HEADER.hdr` or `--absent CATEGORY`, plus both cinematic streams.
It matches original templates, preserves exact source R2 streams/logical clip
ordinals/families, and reports unindexed bytes. It writes an authoring fragment
and audio files into a new work folder. Before publishing it, `validate-voice`
runs the shared Reader, native voice compiler and binding encoder against the
staged source. This catches unsupported native predictor/header/packet profiles
and per-category expansion budgets that decoder-export inspection alone cannot
prove. An installed-console bad-predictor test rejects without publishing output
(`logs/fighter-m5-voice4-installed-negative.txt`). Ordinary validation/packaging remains
required after integrating the fragment. No arbitrary HDR metadata enters a
package. Guide and runtime reference describe this supported workflow.

The rebuilt wheel was reinstalled into the existing disposable `m5-wheel-env`
without touching the gallery/review service. From outside the Tools checkout:

- Installed console exported real voice626 with template504, family1 and explicit
  absent Taunts/Enviro. It retained the original intro and extro, not a placeholder.
- Installed API exported all44 supplied custom voices:129 banks,2777 banked clips,
  88 cinematic streams,76,353,040 exact source stream bytes. The only omissions
  are Enviro614, Taunts626 and Enviro626. Report:
  `logs/fighter-m5-voice4-corpus/report.json`; private reproducible driver:
  `logs/fighter-m5-voice4-corpus.py`. Two other fighter voices intentionally inherit
  their original verified retail resources; this corpus is not the full pack.
- The final installed wheel repeats all44 exports with authoritative staged
  component compilation enabled for every voice. All44pass:
  `logs/fighter-m5-voice4-verified-corpus/report.json` and each voice's
  `voice-export.json`/`voice_validation`. Installed console also exports the
  final626source from outside the Tools checkout. The negative predictor case
  exercises the same CLI and shared validator before any final output directory.
- A real voice626 component pack, explicitly inheriting Blaze appearance/behavior,
  passed installed-console ordinary packaging alongside the independent
  single-fighter example. Local ZIP `logs/fighter-m5-voice4-626.zip`, SHA256
  `92a16a87f23c353cf07959441b8f235c614e04cbb976a5a769b64d51410e8a22`.
  This is a component fixture, not a converted Vendetta fighter or pack.

Focused creator/audio suite32pass. Runtime reader/compiler/native-loader suite
58pass before the additional event-identity fixture; that fixture and all23
voice compiler cases pass afterward. Native C covers FVA1/FVA2, shared IDs,
zero masks, mixed retail, repeated loads and malformed/conflicting masks. A
Release build passes (`logs/fighter-m5-voice4-build-permitted.txt`). The sandboxed
build hit MSVC C1902; the permitted local build succeeded without source changes.
Wheel creation needed its normal setuptools/wheel build dependencies and a
workspace temporary directory; no game assets or generated binaries are tracked.
Final offline compiler/contract/package/portrait/graph/context/matching suite:
**121pass**, `logs/fighter-m5-offline-sealed-final-unit.txt`. This includes
source/audio mutation rejection through staged voice compilation and mixed
legacy/absent resources in one FVA2generation. Two initial
contract tests could not use the sandbox's system temporary directory; the same
suite passes with TEMP/TMP and pytest basetemp under ignored workspace logs.

## Native acceptance trials

First probe `run-20261107-102747.log.err` is **not a voice acceptance pass**.
The two-player grid was accidentally driven with the recorded three-column
four-player sequence. It selects retail60/17; no custom voice is selected.
The outer identity assertion fails. Full save-root restoration is identical,
one generation verifies, and no crash/watchdog/debug-layer/unresolved signature
is reported.112 two-second presentation reports25/87/120 are counters, not FPS.
The read-only sampler obtained837 consistent reads/zero skipped but no owned
voice registration; those reads cannot prove absence handling. Retain this
failed trial rather than relabeling retail playback as custom acceptance.

The corrected route uses the existing six-column calibration: eleven Down,
three Right before confirmation, plus a fresh disposable profile history.
Native missing requests, category registrations, lifetime/reload and actual
audio remain acceptance gates until that trial produces evidence.
Its repeat preflight found a different native game in `defjam-custom-songs`,
PID33100 at that check, and correctly refused to launch. The owner explicitly
said to leave that game running and continue offline. It was not terminated or
sampled. No further native game, build or native-C fixture was started after
that instruction. Refresh process identity before any eventual native work;
the recorded PID is historical, not authority to terminate a process.

## Full-graph integration findings and remaining work

The offline94-bank writer remains outside package admission. Read-only review
confirms that paired integration belongs in `fighter_blazin_pairs.py`; the
similarly named Blazin compiler handles activation shots. Current paired
resources apply the owner's rig to both roles, and native execution does not
validate the opponent appearance. New graph admission must seal actual compiled
face/rig contexts for both roles, plus exact verified shared-hand identity.
The baseline now pins misc.viv and the decoded share_hp.o identity. Keep the legacy type11
guard unchanged for its existing proof version. Mixed old/new resources need
per-motion versioned discrimination, not a global permissive switch.

Source choices come from each actual SOD core C's WPAR record C-1, fields88–91;
do not inspect appended cores only. Source blazin.mnl has258 ordered tokens;
choice c maps positions2*c/+1. The older94-bank receipts use generic templates0/1.
New reusable `fighter_motion_matching.py`/`fighter-motion-match.py` compare full
packed and native WAZA[142+c] plus FZUI[709+2c/+1] records. All47 added choices
match exactly one retail template. The six shared chunks reconstruct byte-for-byte:
165792bytes, SHA256
`f782f86a2a45ff30e74d149e69e05c2e347242e0632395a71c23b0347cabeb5c`,
zero unexplained bytes. Secondary WAZA replaces32original zero-padding rows and
appends15; FZUI appends94. Four other chunks are wholly unchanged.
Receipt: `logs/fighter-m5-finisher-template-matches.json`.

`fighter_motion_contexts.py` records actual model, pose, topology, permutation,
face identity/capacities and separate hand allocation. The repeatable
`fighter-conversion-motion-audit.py` compiles all46 appearances through the
ordinary compiler, proves their source pose identity survives, and rebuilds all94
role banks using their actual matched retail templates. It passes5734bounds/
identity joins across46rebuilt appearances and75retail normal opponent contexts.
All121normal models have94bones, one topology/permutation, and face capacities
13/15 or26/30. Exact face bytes remain separately identified. Receipt:
`logs/fighter-m5-actual-motion-joins.json`. This is offline evidence, not new
package admission or native blending/created-fighter acceptance.

## Portrait and complete input accounting

An initial portrait audit wrongly selected the combat donor as the UI layout
donor: only1/46matched. No validation guard was relaxed. The reusable
`PortraitBaseline.matching_layouts` compares all six variants' exact tile IDs,
formats, dimensions, swizzle and crop/material controls against verified original
layouts, independently of combat. The corrected audit compiles46/46fighters,
276source selector/results files, through ordinary pixel-only Portrait.
Receipt: `logs/fighter-m5-portrait-matched-layouts.json`. Their other source
artwork and whole menu edits are still separately accountable.

`fighter-conversion-accounting.py` checks the complete hashed extraction and
emits a row for every source file plus46stable fighter/component mappings.
`logs/fighter-m5-source-accounting-verified.json` accounts for1883files/207429829bytes:
761converted offline components,184exactly inherited combat/AI files,936blocked,
and2excluded installer/cover-art files. Converted components are not native
acceptance. All paired/cinematic source data, remaining artwork, source globals
and the extra V2IP_126A model stay explicitly blocked where semantics/admission
are unresolved. No unidentified file is implicitly dropped. `coreid.txt` supplies
the explicit custom voice mapping; raw source SOD SpeechId retains donor values.
The stable mapping records both domains and must be retained across future updates.

The46-fighter voice-component manifest also passes ordinary installed-console
validation alongside an independent single-fighter starter:47added entries,
cache `b1b1a04ebec6df0da19f7e2b085704bc66b74cad9293d654f004259f77904c63`.
Receipt: `logs/fighter-m5-voice4-roster-contract.json`. It explicitly inherits
retail appearance/behavior/cinematics and is not the finished conversion.

## Cinematic format evidence

All184source bundles/1012members need a broader typed profile than the paired
writer. Read-only census:1656type15parents,644type18,623type20,245type21 and276type25
leaves. All18/20/21use implicit time. Source parents scale by29or30, not60.
Bodies use dynamic/constant partitions over49or69sparse destinations up to93.
Camera leaves include zero-channel/constant-only curves and25dynamic shift3
curves whose seed/delta arithmetic must survive exactly. All184face parents
are empty;46BYhand parents are empty, while138others use selector1then0, with
samples covered by the32/32shared-hand bank. Vector header bytes+18/+19 are
not uniformly zero. Do not zero them or resample to evade the unsupported profile.

Source metadata maps BZ to activation shot1 and BY to shots2–4; intro/extro XML
separately maps46models to CI/CE. BY contains camera helpers, while the current
phase4adapter uses venue cameras. Native scalar-output allocations, helper
control semantics and actual scheduling must be audited before faithful
admission; this census alone does not settle them.

Remaining extended-M5 gates: versioned five-role runtime admission and native opponent joins,
slot1 and new CPU-pool second-match reuse, cinematic/camera/helper conversion,
resolution of the explicitly blocked source-accounting rows, full46-fighter ordinary ZIP and normal-launcher native
acceptance with another pack. The voice work above does not close these gates.
See the [acceptance ledger](../fighter-mod-acceptance.md) for release coverage.

## Reproduction and next native window

Local implementation commits: runtime `5a9eafb` (voice4/FVA2/export API),
`8e0ff36` (actual graph/context/portrait and source-accounting tools), `3a45ecf`
(staged voice input sealing); Tools `269077f` (installed voice exporter/guide).
The final documentation commit records this checkpoint and acceptance ledger.
Both worktrees are intended to be clean at delivery. Toolkit pin is unchanged.

All commands remain local; choose new report/output destinations. Offline:

```powershell
python scripts/fighter-motion-match.py --source C:/Users/Vlad/code/defjam-fighter-data/vendetta-42645b4a/motion/main_all.dat --first 82 --last 128 --out logs/NEW-finisher-matches.json
python scripts/fighter-conversion-motion-audit.py --source C:/Users/Vlad/code/defjam-fighter-data/vendetta-42645b4a --out logs/NEW-motion-joins.json
python scripts/fighter-conversion-portrait-audit.py --source C:/Users/Vlad/code/defjam-fighter-data/vendetta-42645b4a --out logs/NEW-portraits.json
python scripts/fighter-conversion-accounting.py --source C:/Users/Vlad/code/defjam-fighter-data/vendetta-42645b4a --inventory logs/fighter-mod-research/vendetta-inventory.json --motion-report logs/fighter-m5-actual-motion-joins.json --portrait-report logs/fighter-m5-portrait-matched-layouts.json --voice-root logs/fighter-m5-voice4-verified-corpus --out logs/NEW-accounting.json
```

When the owner makes the native test machine available, refresh process state;
do not terminate another checkout's game. The corrected voice probe should use
`--fresh-profiles --profile-store logs/NEW-voice4-store`, its existing component
manifest `logs/fighter-m5-voice4-626-verified-pack/fighters.json`, and these
native selection stages:

```text
getscreeninfo(battle/choosef2=down@10+0.8x11;right@20+0.8x3;a@26
controllersetup(0=right@4;a@7
getscreeninfo(battle/chsvenue=a@8+4x4
```

Use `--binding-window --immutable-reuse --route fighter-roster`, expect
`m5-voice4-626/test` and `retail/crack`, supply the existing combat/taunt stages
and allow260seconds. Refresh the owned PID before the read-only
`fighter-voice-live-proof.py PID SECONDS 600 1 NEW_REPORT` sampler. Require an
actual owned registration and missing-category request, not silence or mask0
before loading. This corrected run has **not** been performed. Then extend
load/unload/reload/device evidence and full-graph admission/native oracles.
No background fighter task remains after this checkpoint's delivery.
