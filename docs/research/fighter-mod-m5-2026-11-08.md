# Extended M5 continuation — November 8, 2026

Continues the [November 7 checkpoint](fighter-mod-m5-2026-11-07.md).
All recorded approvals remain in force. The owner made the native test machine
available on November 8 and authorized up to six hours of continued work.
Everything remains local: no push, PR, merge, pack publication or release.
This checkpoint is being updated during implementation; pending tests below
are not acceptance results.

## Verified starting state

Runtime branch `research/custom-fighter-mods` was clean at `7e99539`;
Tools branch `feature/fighter-authoring-m5` was clean at `269077f`.
Toolkit stayed at `d569ca10811cef67ec4e9fa2173088c2f9fd0580`.
No game was running when native work resumed. Original dump and immutable
Vendetta extraction remain the input sources, with generated data under ignored
`logs/`. No source asset is being silently replaced by a donor.

## Native explicit-absence result

The corrected single-voice626 component probe completed:
`logs/fighter-m5-voice4-1108-native.txt`, native log
`logs/run-20261108-043812.log.err`. It used a fresh guarded profile store,
selected logical menu100 against retail17, and passed five native combat
assertions. The harness reported zero crashes, watchdogs, debug-layer errors,
truncated batches or unresolved calls. The save area was restored identically.
There were zero verified save generations in this fresh-profile probe; it is
not new persistence acceptance. Presentation counters:129two-second windows,
minimum107, median120, maximum120.

Actual requests for the owned voice600 returned bank-row65535 for missing
Taunts families16625/16626 and Enviro40962/40963. Read-only sampler receipt
`logs/fighter-m5-voice4-1108-live.json` records838consistent reads, zero skips,
mask1 after loading and no different nonzero masks. The earlier pre-load mask0
is retained. This proves actual omitted-category resolution while Character
was registered. It does not yet prove a positive Character playback request,
device audio fidelity, or a second-match voice reload. The fixture still
inherits retail appearance/behavior and is not the full conversion.

## Lossless cinematic numeric reconstruction

`setup/fighter_animation_numeric.py` reconstructs typed18/20/21 leaves from
quantized seeds/deltas, dynamic/constant partitions and ordered destinations.
It retains explicit/implicit time, block alignment, float32 constants and the
two unused vector-header bytes. It does not resample into independent seeds.

`scripts/fighter-conversion-cinematic-numeric-audit.py` rebuilt all1512numeric
leaves in184bundles/1012members:644type18,623type20,245type21.
All174214decoded key-pose/interpolation comparisons passed. Receipt:
`logs/fighter-m5-cinematic-numeric-1108.json`. Body outputs use the established
94*48byte allocation; camera output uses the original256byte allocation.
This audit retains source envelopes solely for offline comparison. It does not
admit them as packages or establish native camera playback/scheduling.

## Versioned five-role admission — implementation in progress

New ordinary source `fighter-blazin-3` uses explicit slots containing
`fighter-motion-graph-1` documents. Earlier sources retain their existing
quaternion contract. The coordinator obtains actual compiled/retail appearances,
checks ordered rig joins and palette sample capacities, and generates FBP3
proofs after typed reconstruction. Creator packages cannot provide proof tables.

The new native path checks the whole compiled .data payload after normalizing
each relocation against the compiler's target offsets. The active CPU resource
must cover the complete payload. Five parents and the actual skeletal/root
indices are sealed. The legacy FBP1/2 type11 guard remains in place.

Palette provenance is captured around native21500/215E0 constructors through
the existing109F80 pre-fixup hook. This covers shared hands, normal faces and
created-fighter borrowed face components. Both21670/216A0 invalidate the wrapper
before underlying storage release; temporary loader metadata destruction does
not. The runtime checks current roots, bounded samples/destinations, numeric
values, frame requirements and output bounds. Each paired activation resolves
the actual participant's visual/model, checks pose initialization and a sealed
skeleton identity, then validates the actual face and hand context.

Focused host and native-C proof suites passed166tests before the new full
pair-composition fixture; the latter and existing graph tests passed34tests.
Native rejection cases cover stale/unobserved lifetimes, out-of-span arrays,
bad destinations/numerics, relocation/payload changes, wrong rig/initialization,
created faces and provider rebind. Full game playback is pending the re-lift and
Release build; no native full-graph acceptance is claimed here yet.

## Camera scheduling qualification

Original category2 scheduling already has four phases and ten cache entries.
The supplied `blazin_activation.txt` explicitly assigns BZ to shot1 and BY to
shots2–4. Native phase4 normally sets flag8: a separate absolute venue camera.
Earlier phases use same-bundle actor-relative cameras. An authored profile must
declare and test camera policy; merely renaming BY does not settle it. The source
contains no installer code or runtime patch establishing phase4 coordinate mode.
The two excluded source files are catalogue metadata `mod.ini` and cover art
`couverture.png`; the older phrase "installer/cover-art" was imprecise.

Remaining gates are tracked in the [acceptance ledger](../fighter-mod-acceptance.md).
The full ordinary Vendetta package and release acceptance remain outstanding.

## Subsequent native and installed-tool results

The first full-graph probe correctly stopped at its post-constructor byte seal.
Independent original-code inspection established that E68A0 initializes embedded
type25 dispatch fields before A0C40 returns; evaluator attachment mutates more
cache fields later. The corrected hook seals relocated bytes at E68A0 entry,
before those writes, and remembers the actual bank/allocation lifetime. FBP3
also seals legacy banks when mixed with full graphs, retaining their type11 guard.
It never rehashes serialized bytes after trusted native mutation. Relift/build
receipts: `logs/fighter-m5-preconstruct-relift-1108.txt`,
`logs/fighter-m5-preconstruct-build-1108.txt`. New constructor-mutation and
mixed-profile fixtures pass; final focused native proof suite94pass.

Corrected single-source626 graph fixture passed five combat assertions and menu
100/17, with no native faults: `logs/fighter-m5-fullgraph-1108b-native.txt`,
native `run-20261108-052243.log.err`. It loaded all eight owned graph banks;
that run did not execute a finisher.

The two-fighter human/CPU fixture then executed source slot2 twice, ordinal877
subject/878counterpart, with both actual actor contexts admitted. Native
`logs/run-20261108-053621.log.err` shows both role bindings and native teardown
releasing all8owned allocations to the full33553888byte free block. Presentation:
140two-second counters, minimum109/median120/maximum120; zero faults. One verified
save generation occurred; guarded user save restoration was identical. The
original probe's expected fixture keys were supplied in reverse lexicographic
allocation order. The corrected read-only verification in
`logs/fighter-m5-fullgraph-cpu-verified-1108.json` passes both identities,
immutable materializations and all7combat/result checks against that same log.
It does not rewrite the run or conceal the original assertion failure.

Installed Tools wheel adds `fighter pair`, calling shared runtime `export-pair`
before publishing typed source. All47source pairs/94roles exported and compiled
through the installed console from outside its checkout, including exact source
control matching and input sealing. Receipt:
`logs/fighter-m5-pair-export-corpus-1108/report.json`. Tools focused37tests pass.
The older `fighter-motion-graph-draft-1` research files are not implicitly upgraded;
new exported files explicitly declare `fighter-motion-graph-1`.

`eagl-portrait-2` now expresses all18selector/result/loading portrait and logo
variants. It reuses pixel-only templates and per-ID logo visibility, preserving
text fallback for other fighters. Retail oldMLoad's reversed-ID list has maximum82,
so appended logical IDs>=100 need no Rvariant. Offline validation compiles46/46
fighters and all828source UI files through the ordinary eighteen-role path:
`logs/fighter-m5-portrait18-1108.json`. Updated full input accounting
`logs/fighter-m5-source-accounting-art18-1108.json` has1313converted offline files,
184exact inherited files,384blocked and2excluded; every1883input remains
accounted. The single18-role fixture passes ordinary contract validation.
Native extended-artwork acceptance is in progress.

## Newly established event-timeline requirement

Exact donor FZUI behavior is not equivalent to the source event timelines.
All94source paired tag rows retain their mapped donor payload sequence but change
ticks. All47camera schedules differ; removing shake events leaves identical
non-time payload sequences. All4821changed/new tag events and all418added camera
events use complete payload tuples found in the verified original. This permits
a general typed baseline-event reference plus authored tick/order adapter.

The snapshot name at1A3ECF selects BOTH camera and tag lookup. It must remain
donor-owned for source3; an owned timeline profile must admit both together.
Tags also contain native state/effect callbacks, not just sounds. Do not truncate
events to animation key count or parent duration:56/94source rows have later
tags. The source camera XML contains five duplicate labels; original AC100 uses
the first matching timetable. A faithful conversion must explicitly account for
the shadowed appended schedules instead of silently selecting a different one.
The coupled timeline adapter is now implemented; full callback scheduling
acceptance remains outstanding.

## Coupled timeline and distinct grid implementation

`fighter-blazin-4` compiles explicit tag/camera timelines, FBP4 ownership flags
and FTE1 archive/hash/label claims. Baseline payload references prohibit raw
opcodes, arguments or replacement XML. Exact paired tag payload order and camera
non-shake order are checked. Native first-match camera lookup is preserved;
five source appended schedules are shadowed and reported. Installed Tools wheel
exports/compiles all47pairs/94roles with `--tags` and `--cameras`:
`logs/fighter-m5-timed-pair-export-1108/report.json`. Creator focused38tests pass.
Native snapshot labels use bounded process-generation storage after mask release.

`eagl-portrait-3` adds six independently authored normal/selected grid rasters
to the eighteen other artwork roles. Source chooseF2/3/4 scripts/geometry are not
pack input. A verified original selected-grid closure supplies geometry/material
controls; the compiler emits its own identity placements and Stop actions.
All46fighters/1104role inputs compile, including276grid states:
`logs/fighter-m5-portrait24-1108.json`. The canonical extractor preserves exact
source DXT5 pixels; source F2 states differ from F3/F4. Derived result portraits
would lose those differences. New synthetic closure/state tests pass.

Native `run-20261108-063447.log.err` validated all8timeline identities and
played both roles of source slot2, but combat/result assertions failed at a
tutorial/input stall. Do not count it as combat acceptance. Corrected movement
uses `lright` rather than menu D-pad `right`.

Native `run-20261108-070938.log.err`, driver result
`logs/fighter-m5-grid24-native-1108c.txt`, passes7combat/result checks and native
menu identities102/103. A copied native profile retained prior dormant IDs,
hence allocation begins102; stable keys remain authoritative. It validates all8
timeline labels and actual pair roles873/874 with actual94bone body/face/hand
contexts. Zero crash/watchdog/debug-layer/unresolved signatures;180two-second
counters min105/median120/max120. One native save generation committed; user save
restored byte-identically. Captures are private under
`logs/fighter-window-runs/2ce185ef2a2942ad9001e25da1b8e5e6/captures`.
Moses selector portrait/logo and independent grid artwork were visually reviewed.
Slot1, late callback dispatch, created counterpart and within-process pool reuse
remain distinct gates; this run does not close them.

## Complete cinematic graphs and async ownership

The ordinary `fighter-cinematic-2` / `fighter-blazin-5` profiles now rebuild all
numeric body/root, empty face, hand and camera graphs from fresh ELF/BIG writers.
Original envelopes supply verified opaque controls only. Constants, independent
quantized seeds/deltas, explicit timestamps and parent timing are retained; no
donor tracks or resampling substitute for supplied content. The nested numeric
leaf profile remains the explicitly named `fighter-numeric-curve-draft-1` inside
the new outer `fighter-cinematic-graph-1` profile. Original camera `__Model`/BBOX
exports are not required AnimationBank inputs; independently checked native
camera consumers resolve only their animation banks. All184bundles/1012members
round-trip; installed creator export also passes184/184. Earlier numeric oracles
checked1512leaves with174214pose/interpolation comparisons.

FCP1 authenticates the composed cinematic archive and each relocated data image,
with exact role, rig, palette requirements and relocation list. E68A0 seals the
whole CPU-owned bundle before constructors mutate it. A1FA0 joins the selected
cinematic to its actual live manager/descriptor/visual/actor and camera banks.
Empty face/hand graphs do not imply unbounded output contexts; nonempty palette
graphs require the actual face/shared-hand capacities. Created-visual lookup uses
the already established ABB4 flag and correct Model pointer. Proofs are compiler
output; packs cannot supply native tables or hooks.

Early native trials073910/074605 rejected safely because the asynchronous loader
made a later untracked final copy. The native1AD30/1E6690 request and1AA10 callback
are now correlated by full generation handle, including immediate/nested callbacks
and cancellation. Only the reviewed1AA99/1AACF final29500copy calls can select the
CPU pool, after checking native slot/handle/flags/copy state. Native decompression,
copy and free remain authoritative. The whole bundle is owned; embedded.o members
borrow that allocation. Per-load seals support repeated instances and release
after the original native destructor, with bounded tables and fail-closed checks.

Relift/build logs: `fighter-m5-film-async-relift-1108.txt` and
`fighter-m5-film-async-build-1108.txt`. Native `run-20261108-075857.log.err`, result
`fighter-m5-fullfilm-async-native-1108.txt`, passes7combat/result checks, native
menu102/103 and one acknowledged save generation. User save restored identically.
It admitted15actual full cinematic contexts: both entrance slots, both fighters'
four activation phases and CPU victory.179two-second counters min104/median120/
max121; zero reported crash/watchdog/debug-layer/unresolved signatures. Private
captures: `fighter-window-runs/7f8e26333bce4d8ab158abc81e03fd5d/captures`.
This run ended at results and does not prove within-process pool reuse.

## Exhaustive source accounting and ordinary candidate

New `fighter-conversion-global-audit.py` reconstructs the entire source
`animtags.dat` byte-for-byte from typed original-payload references:204new rows
plus10explicit existing-row edits. The ten edits affect original ordinary motions
as well as supplied pairs; ignoring collisions would lose source behavior.
`tag-override` resources pin the original row hash and preserve the declared
verified template's complete payload sequence. Identical claims deduplicate;
conflicting claims identify their resources rather than choose load order.

All559original camera schedules remain unchanged.47appended schedules contain
only verified payloads; five duplicate labels remain shadowed by the native first
match and are explicitly reported. The source paired-name list preserves all164
original names and adds exactly94owned names, without collisions. All46source
core records differ from mapped ordinary-combat donors only in the four finisher
choices; complete WWAZ and all other native-unpacked WPAR fields match. Packed
padding does not supply additional native fields. New optional `retail_slots`
preserves original choices0–81 that differ from a donor, alongside owned pairs.

The original SOD byte prefix differs only at five derived count/index/string
pointer words; all75original records remain unchanged. Added records have one
further semantic difference from donors: `Character.Tier` at word24/descriptor6.
Native47BC0 orders unlocked fighters by equality buckets1,2,4,8. All46source
additions use8. New inline `tier` preserves it through inheritance, explicit
conflicts and native compilation; it is separate from combat stats.

Both source XML files preserve original bytes and add48simple registrations.
46are the actual fighters.606A/607A have no Character references or source/original
appearance payload; their dangling registrations are explicitly excluded at
subrecord level, rather than inventing two fighters or substituting models.
All46activation mappings match their source models. The28`cri` annotations exactly
equal the actual BZ callback timelines; the other18BZ and all46BY explicitly lack
tag rows. Four activation phases retain all supplied numeric content.

The extra source `V2IP_126A.o` is an actual retail Crow appearance edit, not one
of the46additions. Its94bone rig, materials, UVs, indices and skin are unchanged;
30669bytes in vertex payloads differ, including bounded position edits and an
uninterpreted four-byte stream. The geometry compiler retains those payloads.
`eagl-appearance-2` adds explicit shape-name mappings, rewriting only checked
TAR/SHPX names and symbol tables. It preserves vertex/pixel content and rejects
automatic collision repair. The converter emits an explicit retail/crow override
using its original own-dump texture/face files and isolated declared shape names.

`fighter-conversion-grid-audit.py` verifies all three whole source menus and276
new drawable closures against original controls. Scripts/constants, unaffected
drawables and original textures are preserved; new state actions are only the
reviewed identity placements/Stop/End.24independent rasters per fighter compile.

Final offline ledger: `logs/fighter-m5-source-accounting-complete-1108.json`,
**1697converted /184exactly inherited /2excluded**, all1883input hashes rechecked.
The archive hash remains42645b4ad0d4b9bb502dec3db88095b7a21f061a20ad9091387b3272137f415f.
The two whole-file exclusions remain catalogue metadata and cover art; dangling
XML exclusions are separately enumerated. Converted is an offline classification,
not native acceptance. Complete faithfulness remains false because the archive
does not encode the original legacy fourth-shot camera coordinate/use policy.
The ordinary adapter currently retains the reviewed native venue policy and
preserves unused helper graphs; it does not infer usage from their presence.

Tools `fighter convert-legacy` assembles all sealed exports and stable mappings
into a normal46fighter/285resource folder, validates it through the shared compiler
and publishes only a new local folder. The earlier full ZIP
`vendetta-roster-1.0.0-local-1108.zip` (SHA256
dbeeb93285d443024c47507076ec48146d9f410bc0d6c33ef9ff9f6f2e7c5dfc)
predates the Tier and explicit retail-slot corrections and is superseded as a
candidate. Installed-wheel corrected conversion is in progress; do not use the
old ZIP as final fidelity evidence.

## Current validation and normal managed-path correction

Current focused fighter suite:1399passed in46.55s, log
`fighter-m5-final-focused-b-1108.txt`, including compiled-C cases and permitted
disposable junctions. Earlier sandbox-only run had14junction WinError5 failures,
all separately passed with permissions; the final run is fully green. Installed
creator package/audio/motion40tests pass. New native bridge10tests pass.

The first ordinary full-pack plus independent starter launch correctly refused
unsupported new timeline/film settings at the native bridge, before guest boot;
the helper had prepared its supervised profile. Native error was observed and
dismissed; full save guard restored identically. No combat claim for
`run-20261108-084756.log.err`. Added the six exact timeline/cinematic proof keys
to the normal bridge allowlist and a positive managed-helper test, retaining
rejection of test-only settings. Release build passes in
`fighter-m5-managed-bridge-build-1108b.txt`; the initial sandbox MSVC C1902 attempt
is preserved separately. The next normal managed native run must use the corrected
candidate and prove repeated-match bundle release/reuse.

Extended M5 remains open. Remaining gates include phase4 legacy policy, actual
slot1 playback, created/mixed/human full-graph contexts, positive/reloaded owned
audio, full converted-pack menu/result/ownership/lifetime matrix and broader
visual review. M6 physical inputs, installed Setup/platform acceptance, final RC
checks and owner playtest are separate. No release/publication is authorized.

The corrected installed-wheel conversion finished: folder
`logs/fighter-m5-vendetta-candidate-1108`, report
`logs/fighter-m5-installed-conversion-1108.json`, normal local ZIP
`logs/vendetta-roster-1.0.0-candidate-1108.zip`,4651files, SHA256
**e288a716e7f77540e149dfc244a2fa1d8c2664a272f45b94ac1a8cce9552ad0a**.
Creator wheel SHA25600982e85ea746d4eaa134b9cadb5a79bab1b26fc6f979b99a7a869acfa2fcbe2.
The installed executable ran outside the Tools checkout, with no PYTHONPATH.
Packaging rechecked exactly the successfully validated input hashes.

Review then closed an admission gap: FIC2/FBZ2 mark each full-graph role/phase.
Before loading, the runtime requires all corresponding body/face/hand and expected
camera FCP1 member proofs, including when the proof file or a whole bundle is
omitted. FIC1/FBZ1 legacy quaternion inputs retain their separate guard. Empty
hand tracks still require a nonnull actual hand context because native evaluation
dereferences it.115focused writer/native cinematic/proof/graph cases pass,
`fighter-m5-required-film-unit-b-1108.txt`; Release build passes
`fighter-m5-required-film-build-1108.txt`. These binding bytes change cache hashes;
the ordinary source ZIP is unchanged. Managed corrected-candidate retest follows.

## Ordinary installed-layout native acceptance

`run-20261108-092012.log.err`, result
`fighter-m5-managed-installed-native-1108.txt`, used the ordinary Manager with
the corrected ZIP and independent `zz-fighter-check` pack enabled. Native helper
discovery ran from a separate source-layout copy using the actual isolated Setup
Python runtime, not a development interpreter override.1344Python files were
checked against an existing installed Setup manifest before copying; all71fighter
modules import under that runtime with `-I`. The tracked source-only Setup copy
contains the four new modules. Process evidence:
`fighter-m5-installed-native-processes-1108.json`; layout evidence:
`fighter-m5-installed-layout-1108.json`. This is installed-layout/helper acceptance,
not execution of a newly built installer or cross-platform acceptance.

Startup admitted47motion cores,44voice bindings,46activation sets,47cinematic
bindings,474timeline identities,1472cinematic member proofs and94paired bindings.
The compiled immutable records preserve all46source Tier values and all46four-slot
choice sets, including exact original choices. Verified report/script:
`fighter-m5-managed-installed-verified-1108.json` /
`fighter-m5-managed-installed-verify-1108.py`.

Arrii and Briggs were selected and materialized in two actual native match epochs.
Both entrances and the CPU's four activation phases passed actual-context proofs
in each epoch; the first match naturally reached victory/results and native Quit.
All23owned allocations then released to the original33553888-byte free block;
motion generation2 and fresh cinematic seals prove reuse in the same process.
Two native save batches were acknowledged. User save guard restored identically.
263two-second presentation counters min107/median120/max121; zero reported fault
signatures. The independent pack was enabled but its fighter was not selected.

This driver omitted start/combat telemetry, so do not claim new automated damage
assertions from this log. The second match ended at the harness bound rather than
native Quit; the helper recovered the last complete generation after process exit.
Its first native release plus second-match reuse closes that bounded pool gate,
not every clean-exit or longer-soak requirement. Warm launch preparation still
took about123seconds with this large validated pack; final launch/cache performance
needs further work and measurement.

## Slot1 and human contexts

`run-20261108-093617.log.err` selected two actual human participants100/101 in the
full-film fixture. Join the playback to FBP4 rows, not allocated P filenames:
core141 slot1/template21 maps to873/874, `P0000_A/B`. Both roles executed with
actual94bone rig/face/hand checks. Receipt: `fighter-m5-slot1-roles-1108.json`.
All four P1 activation phases also passed full-context checks; all30owned
allocations released to33553888bytes. One save generation acknowledged and guard
restored identically.209two-second counters min108/median120/max121, zero reported
fault signatures. This deliberately mixed component fixture uses Moses appearance
and voice626; the real conversion independently preserves Moses voice611 and
V.Masa voice626. Fixture labels are not a claim of whole-source fighter fidelity.

The two-human combat assertion failed because P2 did not land an input-linked
damaging hit. Movement, P1 attack/damage and actual human counterpart graph
admission remain positive observations; do not report the entire combat assertion
set as passed. Private screenshots are under
`fighter-window-runs/e95d954661884e19b67d7898f90dca66/captures`.

The harness previously appended stock combat-tail buttons even when an explicit
same-anchor stage replaced them. It now removes only those matching raw-tail
groups, preserving later result/reselection stages. This prevents stock input
from disrupting scripted pause/quit. The probe also exposes a bounded private
`--pad-live` file for the existing native controller protocol; it cannot write
guest state.99host harness/probe cases pass,1platform-specific skip. Final focused
fighter suite before the later live-path test:1412passed in38.79s,
`fighter-m5-final-focused-c-1108.txt`.

Setup asset inspection now requires every fighter module and imports the complete
set with the bundled isolated interpreter on its native platform.73game-free
Setup/source-policy cases pass; missing transitive adapters are tested. This does
not build/run a new Setup installer. Local owner instructions and launcher:
`logs/fighter-m5-owner-playtest-1108.md` / `.ps1`. Exact conversion reproduction:
`logs/fighter-m5-reproduce-conversion-1108.ps1` with a new `-Out` folder. All remain
private/local. Full ordinary four-participant mixed-pack acceptance is in progress.

## Expanded selector failure and bounded correction

The first mixed4run `run-20261108-094514.log.err` crashed before combat, after
only Arrii was selected. Do not count it as mixed-pack/four-participant playback.
The crash was an arbitrary patch-list write in native111400, called from112610
with the drawable Model+D0. Its argument00353135 is exactly ASCII`515\0`, the
model-name string placed immediately after the cloned data. This was a truncated
static drawable, not animation memory exhaustion or a native resource limit.

The selected-grid extractor copied448hex bytes, ending at Model+D0. The original
native Model consumesE0hex bytes beginning378hex bytes into that closure; its
D0/D4/D8/DC fields must exist even when zero. All three original templates have
24zero bytes from448through45F, with no additional relocations or references.
The compiler now retains the complete aligned460hex-byte closure and verifies
that tail.42relocations remain exact. Tests explicitly check optional control
fields after identity strings are appended and reject truncated/changed tails.
22focused grid/portrait/results tests pass.

Source audit now verifies those complete tails for all276source states:
`fighter-m5-grid-source-audit-1108b.json`. Updated exhaustive file ledger:
`fighter-m5-source-accounting-complete-1108b.json`, unchanged1697/184/2totals.
The ordinary ZIP is unchanged because packages contain typed pixel resources,
not native UI Models. Content-addressed screen output changes after recompiling.
The installed-layout overlay is exactly setup/fighter_ui_model.py SHA256
56e0388cea7b044e6a9b8d1ae7c3a7cad12674832f9ef5d09107edcd9c1dbb89.
No native C/toolkit change or relift is needed. Corrected native rerun is underway.

## Corrected mixed-four acceptance

The corrected run `run-20261108-095445.log.err` selected Arrii100, independent
Check146, retail Blaze56 and Briggs101. The native participant window and all
four immutable cores matched. All five available combat assertions passed:
telemetry, four-participant setup, movement, P1 attack and damage. Receipt:
`logs/fighter-m5-managed-mixed4-verified-1108.json`. Both converted entrances
passed full actual-context admission. The independent fighter inherits retail
assets. This bounded run did not prove an owned paired evaluation, result or
native Quit/pool release. Save guard restored identically; zero reported faults.
326two-second counters min16/median120/max121; preserve the low sample rather
than claiming a uniform timing floor.

## Additional legacy runtime reference and absolute camera

The owner identified Comoria's runtime as the additional legacy instructions.
Behavioral reference was pinned to
[aca317a0](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1219-L1234).
It replaces both body and separate camera names with BY for phase4 while
retaining flag8. This supersedes the earlier unresolved/native-venue conclusion:
Vendetta requires its owned camera in absolute coordinates. No third-party
implementation code was copied.

Own native A3B60 writes the venue name after the existing A3160 hook. A new
posthook preserves its thiscall/ret4 and return value, then selects the owned
camera before native allocation. FBZ3 adds a phase4 absolute-policy mask; older
bindings remain supported. Absolute cameras now require sealed CAM_TARGET/EYE
members and actual nonnull output context, in addition to the body/face/hand
proofs.98focused compiler/native tests pass in
`fighter-m5-absolute-camera-unit-1108.txt`; relift and Release build pass in
`fighter-m5-absolute-camera-relift-1108.txt` and `...-build-1108.txt`.

The reference's phase1 D0=1 write changes XML shot-count metadata. Own Blazin
state7 playback uses89BC0 and explicitly compares its phase counter to4; it
does not consult that descriptor count. Our typed four-phase D0=4 contract has
no identified playback difference here. Generic intro sequencing does consult
D0; this finding is restricted to Blazin.

New installed-wheel conversion: `logs/fighter-m5-vendetta-absolute-1108`, report
`logs/fighter-m5-installed-conversion-absolute-1108.json`. All46fighters and
285resources compile. Normal4651-file ZIP:
`logs/vendetta-roster-1.0.0-absolute-1108.zip`, SHA256
**d493f0aa580748a29a6a45bf99c34f8274d87049e5df70abd04e931c2cfe0c01**.
This supersedes the e288a716 native-venue draft. Installed creator wheel SHA256
2d2952ed66abda71b731ce27afa22aac0a74c65212e75de025364b1a633cdefb;
40focused installed creator tests pass. Source ledger was recomputed with all
1883hashes: `fighter-m5-source-accounting-absolute-1108.json`, unchanged
1697converted/184exactly inherited/2excluded. Its global audit includes the pinned
camera reference. Source classification does not assert complete native fidelity.

Native absolute-camera fixture `run-20261108-102136.log.err` has selected B00003
and verified actual full contexts for all four human activation phases, including
the owned absolute camera. Final teardown/save/driver status is recorded below
when the bounded run ends. The mixed Moses/voice626 fixture is component evidence,
not a new whole-fighter conversion test. Extended M5 and M6 remain open for the
broader native/audio/content/mode, lifetime/performance, physical controls,
platform, fresh installer and owner acceptance matrix. No publication authorized.

The absolute-camera fixture finished420seconds with209two-second counters
min104/median120/max121, zero reported fault signatures, all32allocations released
to33553888bytes, one acknowledged save generation and byte-identical guard
restoration. Native menu identities100/101 verified. Its complete two-human combat
assertion still fails because P2 did not land an input-linked damaging hit; do not
claim the entire combat suite passed. Result/clean application exit are not gates
closed by this fixture. Driver: `logs/fighter-m5-absolute-native-1108.txt`;
captures: `fighter-window-runs/1f4565152b2045578d1242134b52fed9/captures`.

Final complete focused fighter suite passes1416tests in42.16seconds:
`logs/fighter-m5-absolute-final-unit-1108.txt`. No game ran during native C
fixtures. Source checks report805tracked files/0policy failures. Tools source
commit89b0b06 carries the corrected converter and guide (524files/0failures).
The new ZIP was installed via the normal Manager transaction into only the
disposable managed profile. The isolated installed-layout helper overlay hashes
are in `fighter-m5-installed-absolute-overlay-1108.json`; this is not a fresh
installer. A final bounded normal managed smoke is recorded separately below.

Final managed smoke `run-20261108-103025.log.err` admitted the latest complete
pack plus independent starter through the actual isolated helper. All47cores,
44voices,46activation sets,47cinematics,474timelines,1472full-film member proofs
and94paired bindings validated. Actual cache:
`e9e951e51a5ae66718bfb0fe66574110a709ad06e31e07616e1576ba65c18dec`.
All46FBZ3rows have full mask15/absolute mask8; every source Tier8 and four-slot
choice set was independently rechecked. Receipt:
`logs/fighter-m5-managed-absolute-verified-1108.json`.

The210second wall bound includes helper preparation. It reached the selector,
not a match; do not count new whole-pack gameplay or phase4 playback here.
40two-second counters min107/median120/max120, zero reported fault signatures,
save guard restored identically. No native game/helper remains running. The
earlier complete-pack gameplay and dedicated absolute-camera fixture retain
their explicitly bounded scopes. Longer warm preparation remains an open gate.
Final Tools handover commit is f7bd523; source implementation is89b0b06. Final
continuation instructions are in `fighter-mod-handoff-2026-11-08.md`.
