# Fighter Mod Support agent handover prompt

Latest beta continuation: [v1.2.0-beta.1 qualifications](../releases/v1.2.0-beta.1.md) and current `PROGRESS.md` D371–D382. The owner subsequently authorized this experimental runtime release; the historical local-only restrictions below do not revoke that later authorization. All original and converted Vendetta files remain local.

Latest continuation: [November 8 checkpoint](fighter-mod-m5-2026-11-08.md).
For the final local package, source commits and exact next steps, read the
[November8 handover](fighter-mod-handoff-2026-11-08.md) after this file.
On November 8 the owner made the machine available and authorized up to six
hours of continued local work, superseding the earlier native-testing pause.

Continuation evidence: [November7 M5 implementation checkpoint](fighter-mod-m5-2026-11-07.md)
and [acceptance ledger](../fighter-mod-acceptance.md). They supersede implementation
status below where explicitly updated; all owner approvals/constraints remain.
Continuation code commits: runtime `5a9eafb`, `8e0ff36`, `3a45ecf`; Tools `269077f`.
The owner subsequently requested leaving the other checkout's native game running
and continuing offline. Do not start serial native work until the machine is free.

Copy the prompt below into the next coding agent, or instruct that agent to read
this entire file before acting. Snapshot date: November 7, 2026,
America/Vancouver. This is an implementation handover, not a declaration that
M5, Vendetta compatibility, or release acceptance is complete.

---

You are taking over **Fighter Mod Support**, targeting **v0.15.0**, for Vlad's
Def Jam: Fight for NY static recompilation. Finish the extended M5 work,
faithfully convert the supplied Def Jam Vendetta modpack into the ordinary
supported fighter package format, and finish the outstanding acceptance work
on this feature's roadmap. Work from the existing local implementation; do not
restart the research, replace the architecture, or merely produce another plan.

## 1. Owner directions and authorization

- Keep all implementation, builds, converted assets and testing **local**.
  **Do not push, open a public PR, merge, publish a pack, or release anything.**
  The owner originally allowed a PR, then explicitly withdrew publication
  authorization. That restriction remains in effect. Local source commits are
  appropriate. Release readiness does not authorize release publication.
- The feature is named **Fighter Mod Support**. Its launcher category is
  **Fighters**, alongside Textures and Languages.
- Build a maintainable, reusable system. Vendetta is a real compatibility test,
  not a special runtime mode. No hash-specific runtime branches, hardcoded
  Vendetta ID maps in the engine, or temporary retail-slot replacement solution.
- One-fighter and multi-fighter packs use the same contract. Multiple independent
  packs must coexist, including shared resources and declared dependencies.
- Modpacks contain validated data/assets. They cannot supply executable code,
  native hooks, arbitrary patch tables, or unvalidated native databases.
- Do not copy code from `https://github.com/comoria08/defjam_recomp`. Earlier
  research inspected behavior/data, but this implementation is independent.
  Prefer the existing research and independently checked original-game code;
  do not needlessly inspect the other project's implementation again.
- Do not substitute donor assets to conceal unsupported custom content. Exact
  byte-equivalent donor reuse is legitimate when established and recorded.
  A new face, animation, recording or cinematic must remain its intended content.
- The owner explicitly extended M5 to **general adapter R&D** needed for faithful
  conversion. Do not close M5 as just creator tools while quietly deferring the
  difficult source components. If a real technical blocker remains, explain the
  evidence and get a scope decision before calling the milestone complete.
- The owner approved custom **2D portraits in the native selector**, with new
  3D models verified in entrances and combat. Do not build a new live 3D selector
  preview. Native selection menus remain authoritative, including P1/P2/P3/P4.
- Whole-pack activation is approved. Changes apply after restart, not by hot
  mutation of a live match. Keep stable fighter identities across pack changes.
- Compose compatible component edits. Conflicts must identify what the user can
  fix. A compatibility helper is desirable when practical, but automatic conflict
  repair and last-pack-wins gameplay behavior are not required or approved.
- The owner gave full testing control of this computer and authorized subagents.
  Follow repository delegation rules: bounded read-only audits may be delegated;
  the main agent owns edits, builds and serial native runs.
- The owner waived another **routine stock regression** during development.
  Run focused tests and native acceptance appropriate to changed behavior. Do
  not repeatedly spend hours on unchanged stock checks. M6 release-candidate
  platform/regression obligations still need explicit accounting; do not confuse
  the development waiver with proof of release acceptance.
- Keep the modding guide current. Each section starts with beginner-friendly
  human explanation, followed by the required technical detail. Explain what a
  fighter contains, how to create a valid pack, and which tools actually exist.
- Ask only for genuine missing decisions/access. Existing D1–D6 decisions and
  normal implementation work are approved. Do not repeatedly ask to continue.

## 2. Exact workspaces and starting state

Runtime/game feature checkout:

```text
C:\Users\Vlad\code\defjam-fighter-mods
branch: research/custom-fighter-mods
latest implementation commit at handover: 16720ff
```

Important local commits, newest first:

```text
16720ff feat(fighters): rebuild typed motion graphs and verify cached evaluation
d27ca58 feat(fighters): isolate owned animation memory and prove parent timing
8e069fe feat(fighters): add explicit voice families and per-slot finisher proofs
49ae973 feat(fighters): decode timed quaternion curves
1ee8033 feat(fighters): add bounded R2 voice resources
```

The handover document itself may be a later documentation-only commit. Verify
HEAD/status instead of assuming the implementation checkpoint is still HEAD.
The worktree was clean before adding this handover. Do not reset it if somebody
has subsequently made changes.

Creator tools checkout:

```text
C:\Users\Vlad\code\DefJam-Modding-Tools
branch: feature/fighter-authoring-m5
HEAD at handover: 38a610e
```

Recent Tools commits:

```text
38a610e docs(fighters): explain full motion conversion evidence and remaining gates
8f59e61 docs(fighters): update animation memory and graph evidence
c5a25a9 docs(fighters): explain voice families and experimental finisher slots
8084d88 fix(fighters): preserve signed audio count semantics
```

Toolkit checkout at `defjam-fighter-mods\tools\xboxrecomp` is clean and pinned
to `d569ca10811cef67ec4e9fa2173088c2f9fd0580`. Do not change it casually.
The last work changed game/project adapters, not the toolkit.

Local game junction:

```text
C:\Users\Vlad\code\defjam-fighter-mods\game
  -> C:\Users\Vlad\code\defjam\extracted
```

Treat the user's extracted game as immutable. Never edit it to make a test pass.

Vendetta input and read-only extracted copy:

```text
C:\Users\Vlad\Downloads\Def Jam Vendetta.mod
SHA256: 42645b4ad0d4b9bb502dec3db88095b7a21f061a20ad9091387b3272137f415f

C:\Users\Vlad\code\defjam-fighter-data\vendetta-42645b4a
```

The input inventory contains **1,883 files**, **207,429,829 uncompressed bytes**.
The package/database contains **46 added fighters**, despite metadata advertising
44. Preserve the original input and extraction; write conversion outputs to new
private working directories, never over the source.

## 3. Mandatory startup and document precedence

1. Read runtime `AGENTS.md`, then run `python scripts/progress.py brief`.
2. Read Tools `AGENTS.md` and `PROGRESS.md` before changing Tools.
3. Check both branches/statuses and the toolkit pin. Verify whether any native
   game process is running before builds or native C test executables.
4. Read these runtime documents, in this order:
   - `docs/fighter-mod-support.md`: approved feature roadmap and D1–D6.
   - `docs/research/fighter-mod-m5-2026-11-06.md`: latest M5 evidence and remaining
     gates; especially its final five-role reconstruction section.
   - `docs/fighter-mod-authoring.md`: implemented package/adapter reference.
   - `docs/research/fighter-mod-m4-2026-11-06.md`: ordinary launcher workflow.
   - `docs/research/fighter-mod-m3-2026-11-06.md`: save/lifecycle guarantees.
   - Current summary and final handoff in
     `docs/research/fighter-mod-m1-m2-2026-11-04.md`.
5. Read Tools `docs/fighter-modding-guide.md` and examples under
   `examples/fighters/` before changing the creator contract.

The Fighter feature's M1–M6 are **not** the recomp project's older M0–M8 port
milestones. Do not accidentally work on unrelated old port tasks from the main
PROGRESS handoff.

Older research documents intentionally retain failed trials and superseded
hypotheses. Later accepted results override earlier “underway” paragraphs.
For example, M3's current result is native profiles plus a versioned extension;
do not mistake the earlier isolated-profile prototype for the final product.
Likewise, later CPU-pool success supersedes earlier failed routing trials.
Preserve historical evidence, but reconcile current summaries/checklists.

On this runtime feature branch, **do not edit runtime PROGRESS.md**. Record
feature decisions/results in the research checkpoint and handoff. Tools has a
different rule: update its PROGRESS.md in the same turn as Tools work and keep
AGENTS.md/CLAUDE.md byte-identical.

## 4. Roadmap state that must not be lost

| Feature milestone | Current state | Work still relevant |
|---|---|---|
| M1 appearance | Implemented; local Windows acceptance | Cross-platform smoke/release coverage; do not redo the feature |
| M2 behavior | Implemented for admitted typed profiles; local Windows acceptance | M5 extends formats for faithful external data; generic arbitrary behavior remains excluded |
| M3 lifecycle/saves | Implemented; focused Windows acceptance | Revalidate changed adapters' lifetimes; M6 longer stress/platform coverage |
| M4 launcher | Implemented; focused Windows acceptance | Installer/platform acceptance and expanded formats through the ordinary path |
| M5 creator/conversion | **In progress** | Full-graph runtime admission, missing voice categories, cinematic/source accounting, complete Vendetta package and native acceptance |
| M6 release acceptance | **Outstanding** | Windows/macOS/Steam Deck, installed setup, physical inputs, performance/resource soaks, release checks and owner playtest |

M1/M2 already include two ordinary independent authored packs, genuine new
geometry, portraits/grid artwork, native menus, humans/CPU, four participants,
motion/voice/AI/intro/victory/activation/paired-finisher adapters. Their detailed
qualifications remain in the checkpoint. An older accepted full match passed
eight combat/result assertions; a stock quick regression passed 5/5 with 1,769
unit tests at that checkpoint. Do not present those historical totals as the
current full-suite count.

M3 includes stale-session compare-and-swap, interrupted-save recovery, native
IO witnesses/acknowledgements, pack removal/update/re-enable, dormant progression,
zero-pack Story saves, profile deletion, repeated matches, actual SDL virtual
disconnect/rejoin, ready/cancel/reselection and signed-in Story/created-fighter
interactions. Native and extension state commit together as complete generations.

M4 includes ZIP install/update/rollback/remove, whole-pack enable/disable,
Fighters UI, active-play locks and a Python profile supervisor launched by the
native launcher. Real managed custom combat and zero-pack continuation of the
same Story career passed. Its authored test packs remain installed but disabled
in `logs/fighter-m4-managed-data` at its recorded checkpoint; inspect current
state before reuse.

After first adoption, managed history remains authoritative even with no packs
enabled. `<data>/save` is an import-time backup, not a fallback career. Never
force re-import by deleting an adoption marker or splice individual files from
different generations. A missing/corrupt adopted head must fail safely.

Dedicated arbitrary post-adoption save merge/import UI is a documented follow-up,
not an already delivered feature. Do not implement destructive recovery shortcuts.

## 5. Architecture and identity contracts

- Canonical typed registry + dependency/conflict resolver + immutable roster
  snapshot + native adapters. No relational database server is needed.
- Hybrid data compilation and audited runtime hooks are approved. Verified
  original data is composed locally; mod files do not directly replace arbitrary
  global native tables.
- Package ID, stable fighter/resource key, native menu/selection index, core ID,
  voice ID, SOD handle and player slot are different domains. Never conflate them.
- Persist stable identities. Do not recycle a missing fighter's identity for a
  different fighter. Content changes need explicit versions/migrations.
- D1 is not a universal 255 limit. Earlier native evidence selected logical361
  from 300 enabled custom fighters and entered combat through bounded engine
  bindings. Later four-participant tests covered254/255/256/257. This does not
  prove unbounded resources or all platform limits. Keep separate budgets for
  selectable entries, cores, voices, animation resources, memory and active slots.
- Native menus must preserve retail order and other players' selection/readiness.
  No launcher-only fighter picker or separate host-rendered roster browser.
- Package schema currently uses `fighter-registry-draft-1`; ZIP has one pack-ID
  root folder, `fighters.json`, declared hash-checked resource files and allowed
  README/LICENSE text. Use the ordinary parser/manager for the converted pack.
- Snapshot/cache identity must include relevant adapter/schema versions and
  resolved content. Changed serialization/admission must invalidate stale caches.

Important runtime Python modules:

```text
setup/fighter_registry.py, fighter_build.py, fighter_native.py
setup/fighter_bindings.py, fighter_composition.py, fighter_behavior.py
setup/fighter_behavior_files.py, fighter_resource_files.py
setup/fighter_packages.py, fighter_launch.py
setup/fighter_profile_store.py, fighter_profile_session.py, fighter_save_journal.py
setup/fighter_appearance.py, fighter_model_compile.py, fighter_rig.py
setup/fighter_geometry.py, fighter_skin.py, fighter_face.py, fighter_xsh.py
setup/fighter_menu.py, fighter_grid.py, fighter_portrait.py, fighter_results.py
setup/fighter_animation*.py, fighter_blazin_pairs.py, fighter_blazin_compile.py
setup/fighter_voice.py, fighter_voice_bank.py, fighter_voice_r2.py, fighter_voice_compile.py
setup/fighter_motion*.py, fighter_moveset.py, fighter_ai.py, fighter_cinematic_compile.py
```

Native adapters are in `src/patches/fighter_*.c/.h`; dispatch/ABI wrappers are in
`src/recomp_manual.c`. In particular inspect `fighter_finishers.c`,
`fighter_cpu_pool.c` and singular `fighter_voice.c` for the remaining M5 work.

## 6. Creator tooling already delivered

Tools owns offline `defjam-tools fighter catalog/new/validate/package/extract`
and `fighter audio`. Runtime `scripts/fighter-contract.py` exposes
`fighter-authoring-api-1`, sharing the actual compiler/validation/menu composition.
Do not fork validation into an independent evolving Tools implementation.

Tools sources: `src/defjam_tools/fighter_pack.py`, `fighter_audio.py`, CLI wiring,
packaged examples/resources and the corresponding tests. There are also older
fighter art/catalog modules: preserve their private gallery workflows.

Existing evidence:

- Twelve creator tests originally covered deterministic package contents,
  post-validation mutation, exact-member extraction and exclusive output.
- Twenty-six creator/audio tests passed at the audio checkpoint.
- Installed wheel in `DefJam-Modding-Tools/logs/m5-wheel-env` created, compiled
  and packaged a single starter outside the source checkout. Two-fighter starter
  also compiled/packaged. Ordinary manager installed/enabled both together in
  disposable data, then disabled them without creating a profile.
- Installed wheel audio exports preserve exact R2 bytes and produce a correct
  24kHz WAV; final installed package rejects negative signed sample counts.

These are creator/host tests, not a native Vendetta playtest. Re-test an installed
wheel when changing Tools code/resources, not merely editable imports.

Preserve live gallery `http://127.0.0.1:8768` and all art/review workspaces,
IDs, approvals and drafts. Do not restart/migrate them for fighter CLI testing.

Generic Blender-to-EAGL mesh/rig reimport and PNG-to-native-portrait export are
not currently provided. Explain actual supported workflows and remaining gaps;
do not tell modders to rename extensions or imply those exporters exist. Assess
whether a practical export tool is needed for the promised creator workflow;
do not silently expand M5 into an unrelated general DCC suite.

## 7. Established facts about Vendetta

- Source SOD has121 characters versus75 retail:46 additions. In the comparison,
  existing75 records/native bindings are unchanged.
- All46 appearances now compile through the general model/material/texture/face
  path, including their genuinely different face palettes. Native coverage is
  still one partial component probe, not visual acceptance of every fighter.
- All46 ordinary combat ORD/ORL/MNL banks are byte-identical to mapped retail
  donor banks after unpacking. All5,980 compared action rows match. Record this
  as faithful donor reuse, not a placeholder.
- All47 added finisher choices82–128 have WAZA/FZUI behavior matching specific
  retail templates. Their94 paired subject/counterpart animation banks differ
  and must be rebuilt as owned resources. Do not append shared gameplay tables
  unnecessarily or replace their animations with donor tracks.
- AI profiles match mapped donors. Account for all comparisons in the final
  conversion report rather than assuming every shared file can be dropped.
- All1,012 supplied cinematic/activation member files pass envelope/index/curve
  structural inspection. This is **not** complete numerical or native acceptance.
- All129 supplied voice banks/2,777 banked clips rebuild with normalized event
  metadata preserved, including45 explicit family-key differences.
- All2,865 referenced R2 clips in217 files were exported/checked;138,547,695
  samples and85,685 packets preserve coded blocks in the runtime typed path.
  WAV transcoding is not bit-identical native decoding. The earlier FFmpeg48kHz
  default was corrected to the actual24kHz source contract.
- Missing categories are real: Enviro614, and Taunts626/Enviro626. Do not invent
  donor recordings or fabricate zero-entry banks as an equivalent absence state.
- Portrait layouts for six supported selector/results slots are understood;
  remaining ancillary art/global edits still need explicit accounting.

Useful private audit files under runtime `logs/` include:

```text
fighter-m5-vendetta-audit.py/.json
fighter-m5-vendetta-render-audit.py/.json
fighter-m5-face-inspection.json
fighter-m5-face-compile.json
fighter-m5-face-joins.py/.json
fighter-m5-retail-face-contexts.py/.json
fighter-m5-face-native-evidence.json
fighter-m5-cinematic-audit.py/.json
fighter-m5-voice3-bank-audit.py/.json
fighter-m5-voice-event-matches.json
fighter-m5-voice3-original-correlation.json
fighter-full-graph-audit.json
```

Read existing scripts/receipts before reconstructing inventories. Private scripts
can encode old assumptions: verify their current purpose and inputs. Promote
reusable logic into the proper tracked module/CLI with documentation and tests.

## 8. Latest work: typed full-motion reconstruction

Commit16720ff added:

```text
setup/fighter_animation_graphs.py
scripts/fighter-full-graph-audit.py
scripts/fighter-quaternion18-oracle.py
scripts/fighter-vector-oracle.py
scripts/fighter-pose-baseline-oracle.py
tests/unit/test_fighter_animation_graphs.py
```

It also added time sampling/destinations to `fighter_animation_quaternions.py`.

Internal format **`fighter-motion-graph-draft-1` is offline R&D only**. It is
not yet accepted by package readers/creator commands/runtime admission. Do not
describe94 successful offline reconstructions as94 playable converted motions.

Each source role bank contains five type15 parent graphs:

| Name suffix | Role | Source children |
|---|---|---|
| `_s` | body rotations | one type18 |
| `_t` | root movement | one type20 |
| `_d` | rotation helper | one type13 |
| `_f` | face palette selection | two type25 |
| `_h` | hand palette selection | two type25; **not hair** |

`FullMotionTemplate` rebuilds local pointers, inert wrappers, typed quantized
samples/coefficients, timestamps and parent duration/scale. It uses verified
template opaque controls, checks unknown fields/ranges/capacities, checks helper
quaternion norms, reparses output and compares exact typed values. Float32
canonicalization does not mutate creator input. Source conversion rejects
unaccounted named graphs and unknown controls. Non-body child controls match
by ordinal; an agent review caught and fixed an unsafe set comparison.

Initial profile: independent type18/type20 seeds (block_shift0, no constants),
one type13 helper quaternion at float destination4, root vector at destination8,
and ordered palette selectors0/1 for face/hands. Future supported profiles need
their own validation/evidence; do not silently broaden the format.

All94 source role banks pass exact typed rebuild/read-back using one representative
94-bone V2IP_610A appearance with13/15 face frames and the validated shared hand
resource (57 output items,32/32 frames). Maximum generated ORL was976 bytes.
This audit uses one verified envelope per participant role to prove the codec;
it does **not** establish the actual47 matched gameplay bindings, every fighter's
palette/rig join, opponent compatibility, full blending or in-game playback.

Source body animations have40 sparse destinations in a94-bone rig; retail
templates commonly have36/37 and different sparse destinations/codecs. Enforcing
donor destination equality would alter source intent. Preserve the source mapping
and validate actual output ownership. The compiler intentionally reports
`unwritten_pose_channels_validated: false` until broader integration is proved.

Native semantic facts already established:

- Parent duration is not child key count. Body/root parent control16163,
  helper5120, face49729, hand50460 match the verified templates in the audited
  source. Attribute table is count1/key1/size1; low byte60, upper padding0x303030.
  Source durations differ from donors for93/94 body and92/94 other graphs.
- Type25 padding byte is234 in the audited source/retail profiles, not zero.
  Preserve trusted template padding and compare source controls during conversion.
- E5CD0 reports parent duration divided by enabled scale; EDF90 multiplies input
  time. EE190 also rescales returned time. Fresh wrappers are mandatory when
  changing graph shape: EDEC0 destroys old cache using the **new** child count.
- `_d`:9FAE0 reserves48 stack bytes;9FAF6→222A0→22150 evaluates into them.
  9FB08 consumes output+16 through44E90/447A0. Context+20 is time, not output.
- Normal face ownership:9DC51 passes visual+20 to97BD0;97710 loads `%s_F.o`;
  97AA0 resolves PosePaletteBank at owner+430 = visual+450.9DF40 copies its
  wrapper to paired context+20;245B0/22150 pass the palette root. Created-fighter
  alternate visual+A6B0 is outside this normal-appearance proof.
- Hand ownership:1265E/21500 loads `assets/misc.viv|share_hp.o`, global33AB30;
  8B440 stores visual+ABB8;9DF40 copies to paired context+24;24790 binds its root.
  Source sample maxima20/20 fit32/32 frames. Motion borrows the bank;216A0 owns
  release. Face sample maxima11/14 fit the rebuilt13/15 frames.
- Root/body output:22A90 resolves resource `Skeleton`, stores its root at
  context+4 and allocates48*bone_count. Success sets the bit enabling23F56's
  22BF0 reset before body/face/hand evaluation.22BF0→E9010 refreshes every compact
  output item from skeleton translation/quaternion/scale, plus auxiliary weight
  or1 at+12 and1 at+44. It is not a raw48-byte memcpy. Strings28A9EC/F8/AA04 are
  allocator labels `CSkeleton`, not pose templates. Later virtual blend paths
  and actual converted-match behavior still need proof.

Current oracle/test evidence:

- Type18:243 invented curves;32,562 fresh/retained-cache evaluations;
  36,990,432 bytes compared, zero differences. Includes sparse output,40 channels,
  constants, implicit/explicit time, forward/backward/cross-block seeks, shifts0/1/3.
- Type20 and21: each405 curves and49,410 fresh/retained evaluations, zero byte
  differences (7,233,624 and6,838,344 compared bytes respectively).
- Type13:20,160 evaluations,2,078,720 compared bytes, zero differences across
  24/53-bit x87 precision. Source94 curves also passed188 keys/1,128 samples.
- Parent oracle:48 original-body scale/duration/cache/same-count-reattach cases.
- Pose reset oracle:30 original-body cases,1/2/40/94/256 bones, auxiliary/default
  weights, changed-source resets and output guards.
- Latest focused Python graph/curve suite: **83 passed**.

Filtered evaluators are not covered by the new cache oracles. Keep all these
proof scopes distinct from native full-graph acceptance.

## 9. Finisher slots and the solved memory problem

`fighter-blazin-2` supports four explicit slots0–3, each with template_choice0–81
and independent subject/counterpart typed quaternion tracks. Same-choice slots
may own different animation pairs. Missing slots inherit. FMC3 changes only
WPAR fields88–91; FBP2 binds core, action-derived slot, template and owned ordinal.
Actions31–34/38–41 select slots. Current admitted owned body validation still
expects the existing typed profile (type11); full graphs require a deliberate
versioned admission path, not simply deleting that check.

A full16-pair fixture originally exhausted/fragmented the title's main arena:
texture allocation263,378 bytes could not fit largest free block218,784, despite
271,488 total free. Native swizzler then corrupted viewport state. This was not a
hard motion-count ceiling. Do not shrink the fixture or remove ownership checks
to hide the problem.

Commitd27ca58 added a bounded **32MiB CPU-only animation pool**, native key63,
backed by guest heap. Exact admitted owned `motion/blazin.viv|Pdddd_A/B.ord`
allocations route there while preserving native allocation headers and free
behavior. Textures and unrelated allocations keep their original paths.

Relevant implementation facts:

- `fighter_cpu_pool.c/.h`; ownership checks in `fighter_finishers.c`; indirect
  allocator bridge in `recomp_manual.c`.
- Verified three-argument callbacks:1E3F20,1E4057,1E4453,1E473D,1E477A.
  **Do not include1E43E8**, which has a different argument shape.
- The initially missed1E4057 uncompressed path caused an explicit ownership
  rejection. That was fixed; temporary routing logs were removed.
- Native constructor1E9640 registers pool key63 at registry3C9254.
  Free fallback294D0→2A180→1E9F90 reads allocation-header owner key.
- Backing remains reusable; after native provider destruction the adapter
  checks the original single fully coalesced free block and sentinels.

Acceptance already obtained:

-52 focused native CPU-pool/finisher cases passed; relift and Release build passed.
- `run-20261106-224908.log.err`:700 seconds, full16-pair/four-fighter fixture,
  all8 combat/result assertions, menu identities103/105/104/106, zero reported
  crash/watchdog/debug-layer/unresolved-call signatures, save tree restored exactly.
-39 evaluated custom resources, including12 paired roles across six subject/slot
  combinations, zero ownership mismatches. **Slots0/2/3 observed; slot1 still needs
  targeted playback proof.** Sampler also had960 unreadable/transitional samples;
  do not claim every sampling attempt succeeded.
-15-second headroom sample:8 changed consistent snapshots, no failed reads;
  minimum main-pool largest free block7,876,464 bytes; CPU pool21,061,344 free.
- `run-20261106-231010.log.err`: separate300-second scripted quit returns to
  Battle;32 owned allocations released;33,553,888-byte original free block restored.
  Within-process second-match reuse of this new pool still needs native proof;
  C fixtures cover reuse but this exit-only run does not.

Evidence/drivers:

```text
logs/fighter-m5-slots-cpu-fixed-native.ps1/.txt
logs/fighter-m5-slots-cpu-fixed-live-proof.json
logs/fighter-m5-slots-cpu-headroom.json
logs/fighter-m5-cpu-cleanup-scripted-native.ps1/.txt
logs/fighter-m5-cpu-cleanup-native.py
logs/fighter-m5-slots-cpu-native.py
logs/fighter-m5-cpu-pool-routing-unit.txt
logs/fighter-m5-cpu-pool-routing-build.txt
```

Fixture manifests are
`logs/fighter-appearance-packs/appearance-{alpha,beta}/behavior-m5-slots.json`.
The retained immutable compiled cache is
`logs/fighter-native-preview/e11b6496bed8d1e1bcba3b37e274b8d90f242f2dfd28f10218d86315b12eb62b`.
It has16 independent pairs,32 owned motions,34 active motions including two retail,
196 provider slots and about12.5MB of ORD/ORL data. Reuse only after verifying
hashes/current adapter compatibility; never assume a stale cache is current.

Native input lessons: results Continue uses **A**, not B. Pause Quit sequence is
Start, Down four times, A, Left to Yes, A. The successful cleanup driver anchors
this after Game.StartGame. Read the script instead of manually guessing timing.
Two-second presentation counters are not FPS measurements.

## 10. Voice work remaining

`fighter-voice-3` supports verified per-category templates and explicit families:
Character0/1, Taunts16625/16626, Enviro40962/40963. Intro/extro are explicit owned
streams. Typed R2 preserves source coded blocks/header semantics. Existing
voice1/2 inputs must remain backward-compatible unless explicitly migrated.

The current compiler requires all three present category banks; runtime queues
all three. Therefore the actual missing categories cannot yet be represented
faithfully. Implement a general **explicit absent category** contract, not a
source-specific skip and not an empty dummy bank.

Suggested design already researched, **not implemented or frozen**:

- A new versioned voice source format; all three category keys remain required.
  Each explicitly present bank has verified template/family/samples; an absent
  one is exactly something like `{"state":"absent"}`.
- Compiler emits no HDR/DAT members for absent categories. A versioned runtime
  binding table carries a three-bit presence mask per owned voice/core mapping,
  authenticated by the composed archive digest/receipt.
- Preserve FVA1 compatibility. Current actual binding magic is **FVA1**;
  do not implement against a remembered hypothetical FVB name.
- Reject unknown bits, conflicting masks for shared voice IDs, missing present
  banks, unexpected members and incomplete declarations. Intro/extro remain
  mandatory unless separately justified/versioned.
- Runtime queues only declared present banks for owned IDs; retail and unrelated
  supplemental categories keep native behavior. Shared voice IDs deduplicate
  consistently, including all-absent cases if admitted.

Read `setup/fighter_voice_compile.py`, `setup/fighter_behavior_files.py`,
`src/patches/fighter_voice.c`, and their Python/compiled-C tests first.

Native absence evidence: exact pair lookup135CB0 misses withFFFF and leaves the
initialized handle unchanged;137780 initializes-1 and137780/138070 return false
before playback for missing pairs. Zero-entry banks can register successfully
and are not equivalent. Event alternatives138EDA and family-only lookup modes
need explicit audit/acceptance; absence of an exact pair does not imply no other
intentionally referenced event can play. Add a focused original-body test and
native missing-category probe before declaring this solved.

Existing native original-voice600 test (`run-20261106-213135.log.err`) resolves
family1. Device correlation0.408 versus next distinct0.167 identifies one original
line. This is one positive observation, not acceptance of all voices/events.

## 11. Execution plan from this checkpoint

### A. Finish reusable full-graph admission and native acceptance

1. Review the new offline graph writer and existing behavior/Blazin reader,
   compiler, receipt, cache-key and native ownership boundaries together.
2. Define/version the ordinary package-facing graph resource contract. Reuse the
   validated writer, expose supported export/validation via the creator/runtime
   shared API, and preserve existing quaternion-track packs.
3. Bind each subject/counterpart graph to its actual verified rig and face/hand
   output contexts. The representative94-bank audit is not this join. Account
   for opponents from other packs and retail, not just the owner's appearance.
4. Use actual matched retail behavior templates for the47 new choices. Preserve
   source parent timing, root/helper/face/hand data, local relocations and namespace
   isolation. Keep fresh wrappers for changed shapes.
5. Extend native admission deliberately with typed/versioned proof. Check archive
   and binding hashes, bounds, resource names, provider lifetime and output contexts.
   Do not relax the old type11 guard globally or accept arbitrary raw ORD/ORL.
6. Add meaningful malformed-input/cross-resource/compiled-C tests, build, then
   run a controlled actual converted pair before scaling up. Verify both roles,
   transitions, faces/hands/root motion and result return visually and via evidence.
7. Close slot1 playback coverage and new CPU-pool repeated-match reuse. Preserve
   the challenging four-fighter16-pair fixture and save guarantees.

### B. Complete voice absence and source event fidelity

Implement/test the versioned explicit-absence path above; convert the three real
missing categories faithfully. Preserve category family/event metadata and exact
R2 streams. Extend native evidence to intros/extros, representative original
predictive clips and absent-category requests, including load/unload/reload.

### C. Finish cinematic and remaining source accounting

Inventory every remaining source component against the user's verified dump.
Separate ordinary inherited combat, owned paired motion, four-shot activation,
intros, victories, cameras, event/helper data, portraits, voices, AI and shared
tables. The1,012 inspected cinematic files still require supported conversion and
native evidence. Reuse generic adapters where semantics match; extend them only
with explicit contracts where necessary. Do not silently preserve donor timing,
root movement, helper graphs or cameras when those source values differ.

Build a per-fighter/per-component conversion matrix and a source-file accounting
report. Every source file/change should be classified as converted, exactly
inherited, explicit dependency, intentional nonfighter/global content excluded
with explanation, or blocked. A global/shared change needed for fighter behavior
cannot be dismissed as unrelated to avoid implementing it.

### D. Produce the ordinary Vendetta package

Create stable pack/fighter/resource identities and an explicit legacy-to-new
mapping outside the engine. Share resources where genuinely compatible; preserve
distinct assets when different. The package should contain all46 supported
fighters and their intended components, not only the advertised44 or a successful
subset presented as complete.

Run the normal creator validate/package path and runtime manager admission. Emit
the local ZIP, SHA256, manifest, dependencies, reproducible converter instructions,
per-file/component report, and any precise limitations. Do not publish source
assets, generated archives, game executables or screenshots in Git.

### E. Exercise the converted pack through the normal launcher

Install/enable through Mods > Fighters with an independent authored pack. Verify
retail preservation, names/portraits/results, native P1–P4 navigation, humans/CPU,
entrances, combat, damage, all finisher slots, victories, audio, mixed-pack
opponents, repeated matches, return to menus and clean exit. Check per-resource
ownership, allocator release, save acknowledgement and stable identities.

Exercise update/rollback/disable/remove/re-enable and missing-content recovery
using disposable profiles. Include zero-pack continuation of the same adopted
career and relevant Story/created-fighter interaction. Reuse existing M3/M4
evidence for unchanged mechanisms, but test new adapter failure/lifetime surfaces.

### F. Finish creator documentation and M5 assessment

Keep the beginner guide and runtime reference synchronized throughout. Add real
supported conversion/export commands and game-free single/multiple-fighter
examples that validate with the installed Tools package. Document every component,
file role, rig/event/palette dependency, safe donor reuse, explicit absence,
conflict remedy, package update and backup procedure. Clearly distinguish
supported workflows from planned exporters and internal research formats.

Assess M5 against the approved exit criteria. Do not mark it complete based on
structural parsing, one component probe or a ZIP that has not played through the
ordinary launcher. If any required source semantics remain blocked, present the
specific evidence and decision needed rather than silently cutting scope.

### G. Complete remaining roadmap/release readiness work

Build an acceptance ledger from `docs/fighter-mod-support.md`, marking each row
with its actual evidence and remaining platform/scope gaps. Existing unchecked
boxes are not proof that already accepted M1–M4 work needs reimplementation.

For M6, complete local Windows release-candidate coverage and available macOS/
Steam Deck/Linux native acceptance. Locate existing machine/build/test access
before asking the owner for anything. If a machine or physical input test is
unavailable, finish independent work and report the exact access/input needed;
do not claim cross-platform success from Windows or Python tests.

Cover actual setup/installer source packaging and installed launcher/helper
discovery, POSIX close/finalization, physical controllers, language/texture
coexistence, >255 and boundary selections, sparse/high identities and sentinels,
resource admission limits, repeated loads/exits, cold/warm cache timings, memory
and performance soaks. Large installed rosters must not preload every fighter.
Treat32MiB CPU backing as a measured research budget, not a platform-wide promise.

Re-lift must retain direct/indirect hook coverage without generated-source edits.
Run appropriate release-candidate checks once at the proper point, accounting for
the owner's routine-regression waiver. Prepare the owner playtest build and
instructions, then obtain/report that human acceptance separately. Record
remaining limitations honestly. Completion of local release readiness still
does not authorize a push, PR, catalogue upload or release.

## 12. Build, test and investigation rules

- Native game runs are serial. Verify the process is stopped before source
  mutation/builds/native C fixtures. Never terminate unrelated apps/processes.
- Ordinary sandbox process/log reads have sometimes been stale. Use the permitted
  escalated read-only process/log query when necessary to establish actual state.
  Do not infer a clean exit from a stale process snapshot.
- Use full save-root guards and disposable fixture copies. Require byte-identical
  restoration; preserve failed backups. Never experiment on the owner's live career.
- Read `docs/agent/harness.md` before scripted runs; `triage.md`/`diagnostics.md`
  for faults; `lifter-overrides.md` before manual overrides; `environment.md` for
  shell/build issues; `delegation.md` before subagents.
- `src/recomp_manual.c` is a lift input: changing even an indirect alias/bridge
  requires `scripts/recomp.ps1` before the Release build. Do not patch generated C.
- Use `rg --no-ignore` for ignored generated files/logs. Pass directories plus
  `-g` patterns; PowerShell wildcard paths such as `setup/fighter*` fail with rg.
- Do not dump whole native logs. Run triage, then bounded line/regex slices.
- PowerShell commands should preserve the real failure exit code when printing
  a log tail. Pytest's default sandbox temp root has failed; use a new explicit
  ignored `--basetemp=logs/<unique-test-run>` directory.
- CUA only through the currently available computer-use skill/API. Prior native
  tests used project harness/pad scripts and `RECOMP_PAD_LIVE`; no direct game
  memory pokes to force positive results. Refresh window/process IDs.
- Check before using any old diagnostic switch: game-free oracle, structural
  compile, runtime injection test and normal launcher acceptance are different.
- No active game/test sessions from the previous agent should be presumed alive.
  Re-discover state. Existing subagents are historical read-only investigators,
  not owners of ongoing edits; ask them only if available and useful.

Useful commands, run from the runtime root, only when relevant:

```powershell
. ./scripts/env.ps1

# New offline graph/curve tests; choose a fresh basetemp for your run.
python -m pytest tests/unit/test_fighter_animation_graphs.py tests/unit/test_fighter_animation_quaternions.py tests/unit/test_fighter_animation_vectors.py tests/unit/test_fighter_animation_curves.py -q --basetemp=logs/pytest-handover-graphs

# Existing native pool/finisher tests; requires MSVC env and no active game.
python -m pytest tests/unit/test_fighter_cpu_pool_native.py tests/unit/test_fighter_finishers_native.py -q --basetemp=logs/pytest-handover-pool

# Original-body CPU-only oracles; outputs remain under ignored logs.
python scripts/fighter-quaternion18-oracle.py
python scripts/fighter-vector-oracle.py --kind 20
python scripts/fighter-vector-oracle.py --kind 21
python scripts/fighter-type13-oracle.py
python scripts/fighter-parent-oracle.py
python scripts/fighter-pose-baseline-oracle.py

# Repeat the documented representative-context 94-bank offline audit.
python scripts/fighter-full-graph-audit.py --source ../defjam-fighter-data/vendetta-42645b4a/motion/blazin --model ../defjam-fighter-data/vendetta-42645b4a/assets/v2ip/V2IP_610A.o --face ../defjam-fighter-data/vendetta-42645b4a/assets/v2ip/V2IP_610A_F.o

# Only after changes requiring lift/build, with the game stopped:
./scripts/recomp.ps1
./scripts/build.ps1 -Preset win-x64-release

# Inspect a specific native result rather than reading its whole log:
python scripts/triage.py logs/run-20261106-231010.log.err
```

These are references, not an instruction to rerun every passing test immediately.
Focus validation on new changes and unresolved acceptance.

## 13. Source hygiene, progress and delivery

Never track game data, lifted C, native binaries, logs, private models, captures,
voice clips or converted packs. Keep generated oracle C/data/executables in
ignored logs. Do not copy private art/review histories into the public source tree.

Before every source commit: `git add -A --dry-run`, review exact paths, stage
explicitly, run `git diff --cached --check` and `python scripts/check-source-tree.py`.
Write a UTF8-no-BOM commit-message file and use `git commit -F`; avoid shell
interpolation of backticks/`$()` or fake literal newlines. Last source checks were
runtime757 tracked files/0 policy failures and Tools521/0 before this handover.

Keep frequent concise updates while doing long work. State what is newly proved,
what remains uncertain and what the next test resolves. Do not leave the owner
thinking a finished turn continues running in the background. If asked for
screenshots, use actual local native captures and describe what they show; do not
offer generated mockups as test evidence.

Final delivery should include:

1. Local source commits and exact worktree state for runtime and Tools.
2. The ordinary converted Vendetta ZIP and SHA256, stable mapping and full source
   accounting report, or a precise evidence-based blocker if not achievable.
3. Updated beginner guide, runtime contract, reproducible conversion commands and
   validated single/multiple-fighter examples.
4. A completed feature acceptance ledger with native evidence by component,
   player mode, lifetime/save scenario and platform; clear unresolved gaps.
5. Resource/capacity/performance measurements and documented supported limits.
6. Owner playtest instructions and release-readiness status, with publication
   still deferred unless explicitly authorized later.

Start by verifying this checkpoint, then implement the remaining general
adapters and acceptance work. No new owner architecture decision is currently
pending. Do not stop at another high-level proposal.
