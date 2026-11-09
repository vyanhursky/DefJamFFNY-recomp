# Fighter Mod Support: runtime changes and compatibility review

This is a source implementation review, including the general adapters exercised
by the local ordinary-format Vendetta conversion. Extended M5 and M6 remain open.
The owner authorized publishing source branches and PR notes on November 8, 2026.
The original mod archive, converted pack, models, textures, animation/audio data,
screenshots, saves, native executables and generated code remain local.

The branch now integrates main's launcher/app transition and published toolkit
pin `4801dc1`. The [integration checkpoint](research/fighter-mod-main-integration-2026-11-08.md)
records the current source/build evidence separately from the earlier native
results below. Packaged-app and new native acceptance remain open; the retained
legacy Setup test path does not restore retired production release assets. This
review does not authorize a PR merge, pack publication or release.

## What the runtime changes

### A bounded CPU animation pool

The original title uses a small GPU-capable asset arena for resources that also
include CPU-evaluated animations. A four-participant custom-motion fixture exposed
fragmentation: a 263,378-byte texture allocation could not fit the largest free
block of 218,784 bytes despite 271,488 bytes free overall. The resulting graphics
failure was not a demonstrated hard animation-count limit.

`fighter_cpu_pool.c` routes admitted owned paired-motion banks and supported full
cinematic allocations to a separate 32 MiB pool backed by the host guest heap.
Only reviewed archive-reader/final-copy allocation paths qualify. Retail banks,
textures, geometry and unrelated allocations retain their original paths.

The pool is allocated lazily on the first qualifying allocation. It is one pool
for the process, not one allocation per fighter or pack. Native allocation headers
and destructor/free behavior remain in use. Match teardown must return the pool
to its original coalesced free block; the backing 32 MiB remains reserved for
reuse until process exit. Repeated-match release/reuse has native Windows evidence.

This is general infrastructure, not a test for a Vendetta pack ID. Donor-only
fighters do not need new animation storage. Independently owned paired moves and
supported full cinematics use this path. Other ordinary animation edits retain
their separate supported loading path; not every custom track is redirected.
The 32 MiB and 512 recorded-allocation bounds are current implementation budgets,
not platform-wide capacity promises or a guarantee that arbitrary content fits.

### Independent activation caches

The original activation cache shares ten variant records. Custom participants
need independent ownership so one fighter cannot replace another's descriptor,
camera, request state or loaded bank. The adapter appends ten records for each of
four participant positions: 40 descriptors plus 40 request records, totaling
18,560 bytes (18.125 KiB), excluding the animation data itself.

This bookkeeping activates when Blazin bindings are loaded, including retail-only
matchups in that session. Actual owned banks are requested for participating
owned cores. Original records and their stock logical count remain intact during
stock loading. Native constructors, asynchronous loaders and destruction own the
resources; live actor contexts are not copied between fighters.

Multiple native variant entries may currently load the same authored phase
resource. Deduplication is a possible optimization, not an accepted explanation
or fix for the earlier long actor-update pause in a diagnostic fixture.

### Paired move identities and behavior tables

Custom finishing animations get separate subject/counterpart entries and explicit
bindings to the fighter's selected slot and verified behavior template. Original
motion entries remain intact. The same move template can be used with different
owned animations without globally replacing the template's original animation.

This is active adaptation: added paired ordinals use the donor's complete verified
behavior record. Full graphs preserve body, arena movement, rotation, face and
hand tracks. Versioned timeline support can preserve owned camera/event schedules;
older profiles intentionally inherit donor schedules. Merely changing a version
number does not admit an older or unsupported asset.

### Stable roster identities and four native participant bindings

An installed fighter's stable identity is separate from its native selection,
core, voice and motion indexes. A larger logical menu is mapped into four active
participant positions at audited match boundaries. This supports logical rosters
beyond 255 without increasing the four-participant match limit or preloading
every installed fighter's assets.

Bindings freeze for a match and release at the native lifecycle boundary.
Selecting the same installed custom fighter for two participant positions is
currently rejected; duplicate/mirror selection is not an accepted capability.
Processing/file limits such as 16,384 definitions and 16,380 window records are
validation bounds, not playable-roster memory guarantees.

### Asynchronous ownership and actual-resource checks

Full cinematic loading passes through multiple callbacks and final copies.
Generation-tagged request ownership routes the final allocation correctly even
when native request rows are recycled. The adapter does not route arbitrary
allocations based on a static debug label or a process-global loading mode.

Compiler proofs cover the required members, relocations and output destinations.
Runtime joins check the actual actor rig, face/hand resources and camera output.
Full-graph flags make missing proof data a rejection rather than a fallback to
legacy admission. Empty hand tracks still require the nonnull context native
evaluation dereferences.

### Voices, appearance resources and UI

Owned voices have independent IDs and explicit category masks. A deliberately
missing Character, Taunts or Enviro bank emits no substitute donor bank. Native
alternative-event and shared-family rules still apply; absence is not a universal
mute. Supported compressed R2 payloads retain their coded samples and event-family
assignments instead of requiring a lossy WAV transcode.

Appearances, facial palettes, texture names and portraits are validated and rebuilt
against verified layouts. Explicit texture-name isolation handles declared
collisions. Native roster presentation supports independent normal/selected grid,
selector, loading and result artwork/logos: up to 24 roles per fighter. Opaque
source menu movies or arbitrary rendering/control programs are not package input.

A selector crash during expanded testing exposed a truncated selected-thumbnail
Model record. The compiler now preserves the complete aligned native closure and
checks its optional tail fields; the corrected mixed-four run reached combat.

### Managed saves are a persistent workflow change

On first managed Play, existing profiles are imported read-only once into a
committed Store. The original import folder remains a backup. Every later Play,
including with all fighter packs disabled, continues from the latest verified
managed generation. Editing the old import folder does not merge it into the
active career. Missing fighters retain dormant progression by stable identity;
re-enabling the same identities restores their association.

Native save intent alone is insufficient. Complete native-close receipts,
signatures, identity/payload agreement, companion metadata and the expected parent
generation must verify before publication and acknowledgement. Recovery uses the
last committed generation, never arbitrary files from an abandoned workspace.
Native profile deletion also requires its completion witness and exact absence.

A transient receipt access denial occurred on Windows after atomic publication.
Reads now retry permission errors for at most 0.9 seconds. Persistent denial,
malformed receipts and other I/O failures still fail without acknowledging a save.
The local playtest shortcut uses a separate disposable managed career; this is
not evidence that a player's original career should be reset or re-imported.

## Base-game and performance implications

Optional owned-resource hooks return to native behavior when their relevant
bindings/resources are absent. This does not mean zero overhead: the binary still
contains hooks and fixed metadata-table capacity. Major finisher/cinematic arrays
alone reserve approximately 1.67 MiB of static capacity, before other modules;
that figure is not a measured RSS increase. The lazy 32 MiB backing is separate.

Ordinary added resources are isolated; explicit edits to existing components are
a distinct operation and can affect retail content. Mixed retail/custom combat,
native resource release and same-process reuse have bounded Windows evidence.
There is no claim of a universal frame-rate, memory or cross-platform guarantee.

Full ordinary-pack warm preparation measured 126.49 seconds and remains an open
performance gate. A RefPack optimization preserves all output hashes and reduces
one in-memory original-model corpus test from 4.32 to 3.05 seconds; this does not
establish a comparable whole-launch speedup. R2 canonical parsing avoids redundant
inspection while preserving canonical byte equality. No global admission cache
was introduced to skip source/resource validation.

## Vendetta compatibility and explicit existing-content edits

The local conversion represents 46 added fighters, despite metadata advertising
44. It accounts for all 1,883 source files: 1,697 converted, 184 exactly inherited,
and two metadata/cover exclusions. Two dangling XML registrations are separately
explained. Ordinary combat/AI donor reuse is supported by exact comparisons.
The result is an ordinary 46-fighter/285-resource package; none of its files is
part of this source PR.

### Crow appearance

The supplied model `V2IP_126A.o` also changes existing retail Crow. The explicit
ordinary override changes appearance only: original own-dump textures and face
are retained with isolated texture-name aliases. Crow's stats, moves and voice
are not overridden by that manifest entry.

The source comparison identifies vertex-payload changes, including positions and
a four-byte vertex stream whose meaning is not inferred. Rig, material controls,
UVs, indices and skin remain unchanged. The file difference is understood more
precisely than its intended visual meaning. Creator/owner visual confirmation
would help establish whether this retail appearance edit was deliberate.

### Ten existing animation-event rows

The legacy archive replaces ten existing tag rows, grouped as five A/B pairs.
These are callback-sequence changes as well as retiming, not merely cosmetic
camera adjustments. The supplied sequences equal other verified retail template
sequences; event times then differ from those templates in 390 of 404 events.

| Existing target family | Verified template | Event counts A / B, original to supplied |
|---|---|---|
| `N0601` | `N06I9` | 8 to 36 / 22 to 60 |
| `N06E8` | `N06N9` | 25 to 42 / 33 to 52 |
| `N06I2` | `N06L5` | 14 to 31 / 20 to 43 |
| `N07E0` | `N07H9` | 20 to 30 / 33 to 33 |
| `N07J8` | `N07J5` | 17 to 32 / 28 to 45 |

The aggregate changes from 220 to 404 events. A matching event count does not
imply an unchanged sequence. These ten target labels are absent from the original
retail Blazin name list. Three families do occur in ordinary-motion name banks:
`N0601` in six, `N07E0` in nine and `N07J8` in seven, spanning 19 distinct original
banks. The other two have existing tag rows but no consumer established by that
name-bank scan. Bank presence is not a complete active-action/playback audit.

The converter preserves all ten as explicit global edits, pinning each original
row hash and enforcing its declared template payload order. The complete supplied
tag file reconstructs byte-for-byte. No raw tag table or callback payload is
published here. Detailed gameplay/effect/audio semantics and creator intent are
not fully mapped. It is an inference that name reuse could cause unintended
retail effects; the source difference alone cannot establish that intent.

Creator clarification would help decide whether these should remain global or
apply only to new owned animations. Removing or restricting them would be an
explicit compatibility-policy change, not a silent conversion fix.

### Cameras and registrations

Original camera rows are preserved. The legacy source appends 47 schedules,
including five labels shadowed by native first-match lookup. The converter
reports that behavior rather than silently selecting the last row. Whether the
unused appended schedules were intended to become active is a useful creator
question, not a fact inferred from their presence.

The owner's [pinned additional runtime reference](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1219-L1234) establishes owned absolute coordinates
for the fourth activation camera. General `owned-absolute` support preserves it;
legacy venue-camera profiles remain supported. The source was used as a pinned
behavioral reference, with independent native-ABI verification; third-party
implementation code was not copied. The reference's phase-one shot-count write
has no identified effect in the actual four-phase Blazin sequencer; this finding
does not generalize to entrance sequencing.

## Verification and remaining gates

The [acceptance ledger](fighter-mod-acceptance.md) and
[November 8 checkpoint](research/fighter-mod-m5-2026-11-08.md) retain exact local
logs and limitations. Key evidence includes:

- Earlier complete runtime unit suite: 2,209 passed, 27 platform/optional skips in 133.98
  seconds (`fighter-pr-full-unit-1108.txt`). The earlier focused fighter suite
  passed 1,424 tests, including compiled native fixtures.
- Earlier complete companion creator suite: 218 passed, three skipped and 51 subtests
  passed in 4.99 seconds (`fighter-pr-full-unit-b-1108.txt`).
- Re-lift and Windows Release build after the cinematic posthook.
- Installed creator exports, complete ordinary validation and a separate source
  layout using the actual isolated Setup Python; this is not a fresh installer.
- Complete pack plus independent starter enabled: two match epochs with Arii and
  Briggs, first result/save/Quit, full pool release and same-process reuse.
- Corrected mixed-four test: Arii, independent Check, retail Blaze and Briggs;
  five combat assertions pass, without a result/owned-pair/Quit claim for that run.
- Full-film diagnostic fixture: actual four-phase human activation including owned
  absolute camera; full pool release. Earlier fixed-schedule P2-hit failures remain
  recorded and are not converted into passes.
- Latest normal managed complete-pack run: all six two-human combat checks pass,
  both entrances verify, one save is acknowledged, native Quit returns to menus
  and all 24 allocations release. Its application later ends at the harness bound;
  this is not a clean-application-exit or natural-result proof. The normal helper
  cleared the requested readiness diagnostic; no new activation/pair playback is
  claimed from this run.
- Save guards restore byte-identically; the actual local playtest shortcut opens
  the normal launcher with both packs enabled and was closed after verification.

Current main v1.1.1 (`482897f`) is integrated at `7c6394d`, retaining toolkit
`4801dc1`, the app/launcher and CAF authoring commands. Integrated runtime tests
pass 2,356/56 skips before the subsequent strict-CI/helper cleanup; 140 focused
native cases pass afterward. Preparation changes pass 97 manager/probe and 69
voice/resource cases. All-platform source CI is green at `d6f7bac`. Latest main's
setup-handoff/engine/update/Fighter packaging suite passes 141/10 skips. Companion
source and newly installed wheel each pass 248/3 skips/51 subtests.

The newer native `d6f7bac` run passes six two-human combat checks, both owned
entrances and the composed music database. It times out before final Quit; it
does not replace the earlier positive lifecycle evidence or prove that lifecycle
on the newer snapshot. A real Windows first install from the inspected local
development payload passes in 407.2 seconds in a short isolated path. Earlier
compiler Temp/deep SDL/Ninja path failures remain recorded. The v1.1.1 app builds
and passes payload/import inspection, including 71 Fighter modules. These local
development checks do not establish the default install path, final app GUI,
update/repair, RC or POSIX acceptance. The integration checkpoint records exact
snapshots and subsequent actual-installed-runtime results.

Remaining work includes broad content/audio/event
and created/retail/mixed contexts, source-fidelity visual review, negative resource
paths, performance and long-run lifecycle measurements, physical controllers,
final installed-app placement/handoff, default-path installation, macOS/Deck/Linux and
final release-candidate/owner acceptance.
An approximately 90-second actor-update pause in an earlier diagnostic fixture
occurred while rendering remained regular; its cause is not established.

Source publication is authorized. Asset/pack publication and release readiness
remain separate decisions.

The subsequent actual installed 0d7850d run passes two human matches in one
process, six combat checks each, both pause-Quit menu returns, one pool
registration/reuse, two complete24allocation releases and acknowledged normal
window close. A separate installed mixed-four run passes five combat checks,
native Quit/release/close with Arii, independent Check, retail Blaze and Briggs.
Both save guards restore identically. Neither adds a natural-result or owned
paired/activation playback claim. The earlier pause-Quit repeat failure and its
teardown-boundary fix remain recorded in the integration checkpoint.

Actual inspected development-payload CLI update passes in236.69seconds with
all25protected data hashes unchanged. Actual app GUI now imports both the
independent and complete46fighter ZIPs, retains enabled packs/stable identities
and protected profile hashes, then starts/closes the installed game through
Play. The compiled installed playtest launcher is separately verified. These
are local Windows observations, not final RC/default-path/platform acceptance.

GUI Repair additionally exposes a general helper issue: Python writes64pyc
files into the otherwise verified payload, so its exact allowlist rejects the
next setup operation before mutation. All47protected files and the receipt
remain unchanged. Fix0fc3969 invokes shared mod helpers with Python-B, preserving
the payload without disabling compiled Fighter asset caches or changing pack
formats. A compiled regression fails before the fix, then97focused tests/4skips,
native rebuild and inspected app rebuild pass. The subsequent clean-payload
GUI update/repair results follow below. Keep the failed payload and repair evidence;
do not describe allowlist relaxation or deleting unexpected files as the fix.

The clean 0fc3969 payload subsequently passes actual GUI Update Game (369.8s)
and, after actual Mods/Fighters use, GUI Repair (133.7s). All 47 protected file
hashes remain unchanged after both operations, the payload inventory stays exact,
and the installed executable passes freshness verification. The test app is
closed. This is bounded local Windows development/short-path evidence; default
placement, final RC/platform/input and broader M5 fidelity/performance gates are
still open. The integration checkpoint preserves the failed repair and exact
positive receipts instead of overwriting the failure.

## Owner playtest follow-up

The owner's subsequent DMX/Chucklez test exposes loading portraits for Arii/
Briggs and voices reverting to retail donors on Rematch. Loading's native
GetMatchInfo formatter reports private participant banks100..103 rather than
the selected logical identities. A narrowly scoped formatter adapter now maps
only those presentation fields through the verified participant window; venue,
mode, retail/created sentinels and actual native participants remain unchanged.
It derives the participant from FWR1's bank domain, not a locally lifted EBP
counter. Result fields retain their existing frozen-selection checks.

Native rematch audio setup reconstructs the audio-template rows while retaining
the registered speech banks and bypassing the loader that previously applied
owned voice IDs. The setup wrapper now reapplies just those owned IDs after
both native/template-adapted setup paths. It does not reload live banks, change
their ownership or alter pack formats. Compiled actual-wrapper regressions fail
before both changes;59focused voice/presentation/window/teardown cases pass,
including category absence, shared voices, unrelated fields and ABI preservation.
Actual in-game revalidation is still required at this checkpoint.

The owner also reports Proof/Funk Flex exiting with access violation0xC0000005
inside native camera parsing1E6EC0 after a null resource lookup. The failed run
selects Inferno mode7 and venue24. A copied-profile default-venue bout reaches a
result, so it does not reproduce or close that venue/mode failure. Preserve the
owner's raw log and test the exact combination before claiming it fixed. All
private packs, captures, reports and saves remain local.

### Bounded cinematic request admission

Custom activation preloads also need to respect the native asynchronous I/O
table: 32 request rows, separate from the 32 MiB animation-memory pool. On a
full table, the native submitter returns zero. Its caller retains that token;
the completion lookup can then match a previously consumed row whose done flag
remains set but whose buffer has been cleared. A private CPU oracle executing
the unchanged original submit/poll bodies reproduces that completed-NULL result.
The owner's null-resource crash is consistent with this mechanism; that oracle
alone does not establish that every observed crash has the same cause.

The owned cinematic scheduler now admits one body/camera pair at a time and
waits for native request capacity before starting it or requesting its camera.
It continues polling admitted work even when its own requests fill the remaining
rows. The original manager polls first, allowing retail work to finish while
custom work waits. Each fighter keeps independent descriptors, native loaders
and destruction; no live resource is shared or substituted. This general adapter
applies to supported custom activation content, without pack-specific branches,
larger native request tables, new pack fields or extra pool reservations. Retail
matches without owned activation bindings retain their existing path. Custom
preparation may take more polling turns; there is no claimed universal timing
improvement.

The compiled regression fails against the old scheduler, then 94 focused
cinematic/voice/presentation/async/pool cases pass. It covers 32 and 31 occupied
rows, delayed completion at full occupancy, independent progress across two
participants and untouched unrelated requests. Logs remain private:
fighter-owner-cinematic-admission-before-1108.txt,
fighter-owner-cinematic-admission-unit-1108.txt and
fighter-owner-async-oracle-1108/comparison.json. Windows Release build passes.
The corrected fresh Proof/Flex Inferno7/venue24 run214322 passes five combat
checks, reaches a natural decisive result, returns through native Game.Quit and
releases all37owned allocations back to the33,553,888byte free block. Normal
window close exits0, supervisor completes and the save guard restores exactly.
The early loading capture visibly shows Proof/Funkmaster Flex with their own
portraits/logos. Read-only sampling observes at most two asynchronous rows in
this run; this is a bounded observation, not a table-pressure stress result or
proof of the original preceding two-bout sequence.

The preceding actual DMX/Chukklez sequence reaches two natural results and uses
the real result-screen Rematch. Owned voice keys 615/627 are reapplied without
bank reload and remain correct in the second bout's live audio rows. This is
routing/identity evidence, not a new subjective listening comparison. Its next
retail-placeholder setup hits the unlock-capacity guard before the intended
Proof/Flex test; preserve that exit1 and do not report a three-bout pass.
