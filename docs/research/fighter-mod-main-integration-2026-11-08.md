# Fighter Mod Support: current-main integration

The owner authorized resolving main conflicts and continuing M5/M6 acceptance.
Source-only PR publication remains authorized; all original and converted
Vendetta files, game assets, saves and captures remain local. Neither PR may be
merged and no pack or release may be published without further authorization.

## Integration scope

Runtime main initially `15e366b`, then `482897f` (v1.1.1), is integrated into the
feature branch; latest integration commit `7c6394d`. This imports the
current app/launcher, songs, cheats, settings catalogue and rendering repairs.
Its published toolkit pin is `4801dc171da7d39ebf23c2fe709d14e4b50a1733`, replacing
this branch's earlier `d569ca1` pin. No toolkit source is modified. Earlier native
evidence remains historical evidence for its exact source/toolkit snapshot;
it does not validate this integration automatically.

The research index keeps main's consolidated organization with Fighter Support
links added. Payload inspection keeps both the fighter import probe and main's
Linux toolchain validation. Settings, telemetry and manual-hook resolutions
retain both feature and main behavior, including song/cheat callbacks, the
isolated-RNG test path and cinematic render timing.

Mods retains the current app's Installed/Browse workflow, generated-texture
action, save-error handling and install-and-enable behavior, inside the approved
Textures/Languages/Fighters categories. Fighter installation uses its resource
validation/activation transaction rather than texture-pack settings. Both success
and refusal are exercised by the native helper bridge fixture; the fixture aborts
if either result touches the texture/language settings registry.

Startup must compose the database in order: language, admitted fighters, then
extra songs. Merely concatenating the two startup paths would make Fighter
Support reject the competing song database redirect. Fighter runtime metadata
admission now happens within settings initialization after the managed helper,
before song preparation and before loading the XBE. Songs extend the resulting
database while preserving unrelated tables and existing string/rank identities.

## Offline evidence

- Integrated runtime suite: 2,334 passed, 57 skipped; 21 failures were Windows
  junction creation denied by the sandbox. The permitted rerun passes all 21
  cases. Combined result: 2,355 passed, 57 skipped, without weakening a test.
  Logs: `fighter-main-integrated-unit-1108.txt` and
  `fighter-main-unit-permitted-1108.txt`.
- Actual complete-pack cached database passed the native song writer: one
  synthetic song added, all 27 unrelated tables unchanged, all 79 native
  participant-window Character rows retained, original string IDs retained.
  Byte changes within the old image are restricted to the Song header/index
  pointers and string-section pointer. This is offline composition evidence,
  not native gameplay. Receipt: `fighter-main-song-composition-1108.json`.
- Companion tools integrated main `9bb5b83`, preserving CAF inspection/profile
  dispatch and its accepted history alongside the fighter CLI. Full source and
  newly built installed-wheel suites each pass 248 tests, three skips and 51
  subtests; installed command help exposes both `fighter` and `caf`. No live
  authoring/viewer service or private review/queue/outfit state was changed.
- Source policy: runtime 874 files and creator 538 files, zero failures before
  this new checkpoint is staged. Creator instruction files remain byte-identical.

Fresh analysis found 18,446 functions; re-lift published 21 generated C files
locally and the Windows Release build passes. The first build found duplicate
profile-load wrappers at `sub_00014540`; the single final wrapper retains fighter
validation before the native load, song-state restoration and saved-volume
restoration afterward. The corrected source was re-lifted before rebuilding.
Logs: `fighter-main-analyze-1108.txt`, `fighter-main-relift-b-1108.txt` and
`fighter-main-build-b-1108.txt`; failed first build retained as
`fighter-main-build-1108.txt`. No generated C was edited or tracked.

Packaged-app acceptance and native compatibility checks are in progress.
Do not infer them from these offline results. The
[acceptance ledger](../fighter-mod-acceptance.md) and subsequent results below
must retain the remaining M5/M6 fidelity, audio/event, lifecycle/performance,
physical-controller, fresh-install and platform gates.

## CI and packaging continuation

Final integrated full Windows suite passes2,356tests/56skips in154.14seconds
(`fighter-main-final-unit-1108.txt`). Local game-free app/payload build and
inspection pass, including all71fighter imports (`fighter-main-app-build-1108.txt`).
It is an explicitly local development candidate, not a published release asset.

First integrated CI42523388374 passes the no-game-data gate, Windows runtime,
macOS/Linux runtime fixtures and all three game-free setup builds, but its Linux
scripts/unit job fails: unused header helper, misleading indentation, cinematic
token formatting and a refused-launch helper retaining its inherited pipes.
Warnings are fixed in source without weakening `-Werror`. A descriptor token
uses a buffer large enough for any formatted integer and must still be exactly
eight characters before its nine-byte native field is copied.

An unadmitted managed session now requests helper stop, waits a bounded interval,
and terminates/reaps only its own unresponsive helper; the original refusal is
preserved. Admitted supervisors keep their existing lifetime. Focused native
suite140passes, including cooperative and ignored-stop refusal cases, file hashes,
AI/animation/cinematic/film-proof and voice fixtures (`fighter-main-ci-fix-unit-b-1108.txt`).
POSIX CI revalidation remains pending; Windows passing is not a POSIX claim.

The first fresh-engine attempt stopped before installation on a denied global
AppData lock. Retry uses a fresh disposable install/data root and an isolated
per-user lock/cache directory. Desktop app access approval timed out; visual
acceptance is pending, while command-line setup/native checks continue. No live
installation, original career, shortcut, pack publication or release was changed.

CI42538105548 is green on103b81e, including strict Linux scripts/unit, Windows
runtime, macOS/Linux runtime fixtures, source hygiene and three game-free setup
builds. This is synthetic/source CI, not native fighter gameplay on POSIX.

## Preparation and remaining first-install gate

The profile records666million calls and440.92seconds with profiling plus a
competing build; that duration is not a launch benchmark. It identifies repeated
path metadata reads and repeated R2 scans as useful targets. Each link check now
uses one `lstat` result, retaining Windows junction and POSIX symlink rejection.
Every admission still checks the current leaf and ancestors; no global trust
cache is added. Live/dangling redirects, newly introduced redirects and denied
metadata remain negative cases. Manager/probe/launch suite97passes.

Canonical R2 input still receives complete source packet validation. When the
reconstructed output is byte-identical, a second scan of those same bytes is
unnecessary; changed headers keep the independent output inspection. Voice/R2/
behavior/package suite69passes. Validation budgets and coded samples are unchanged.

An unprofiled paired warm comparison on the same installed complete pack and
independent starter measures146.05seconds with the103b81e functions and126.77seconds
with these changes (13.2% in this pair). Both produce runtime keye9e951e5 and UI
SHAae9b00e1; the manager state hash is unchanged. Reports:
`fighter-main-preparation-legacy-1108.json` and
`fighter-main-preparation-optimized-1108.json`. This single Windows comparison
does not promise a universal improvement or close the roughly two-minute
preparation gate; earlier runs also measured about126seconds under other load.

The fresh-engine retry's compiler temp is now isolated. It then fails in the
deeply nested SDL architecture probe with Ninja unable to load its rules file;
the long test-install path is retained as failed evidence. A shorter isolated
destination remains to be tested; do not claim a fresh install passed yet.

Main's soundtrack preferences remain in its existing outer-data `song-state`
sidecars. They are separate from the native-profile/Fighter-extension transaction;
the integration does not silently relocate or adopt those preferences into the
Fighter Store. Backups should retain the complete data folder, and coexistence
acceptance must keep this boundary explicit.

## New integrated native observation and newer main

Normal development-source helper plus the actual isolated payload Python runs
the complete pack and independent starter on d6f7bac/toolkit4801dc1. Native log
`run-20261108-172016.log.err` verifies47logical bindings, both owned entrance
contexts FI00001/FI00002 and the composed33-song database. The House profile's
jukebox loads33rows through the combined profile hook. All six two-human combat
assertions pass: both participants walk and land input-linked damaging attacks.
Original save guard restores identically and one native batch is acknowledged.
The actual game renders Arii/Briggs and the native pause/quit confirmation.

The run reaches its720second cap before final quit confirmation; it does not
reach the second battle-mode menu, release the pool through native match
destruction or exit the application cleanly. Preserve the failed lifecycle
criterion despite the six combat passes. The early live pause navigation was
not reliable with tightly queued presses; individually observed menu inputs
reach Quit and its confirmation. Repeat with a focused, calibrated lifecycle
route after the fresh install. Receipt: `fighter-main-managed-native-1108.json`.
Frame reports297two-second samples, minimum107presents, median120; this is bounded
evidence, not a universal rate guarantee.

Main subsequently advanced independently to482897f (v1.1.1 setup handoff hotfix).
It merges into this feature branch without conflicts; toolkit4801dc1 stays
unchanged. Neither feature PR is merged or released. The current first-install
test retains its frozen d6f7bac development payload in the short disposable
`fmi`workspace; do not relabel its result as the newer source snapshot. Validate
the newer setup path separately, including its update/repair handoff.

The short-path first installation now passes in407.2seconds using the inspected
current development payload (d6f7bac/toolkit4801dc1), the immutable own dump,
isolated per-user locks and compiler temp, and no shortcut creation. Real engine
analysis179.6seconds, lift83.2seconds, configuration and game build complete,
followed by verified activation. Log: `fighter-main-fresh-short-1108.txt` and the
private `fmi/setup.log`/installation receipt. This is a local development payload
first-install result in a short Windows path; it does not erase the failed deep
path, establish the default installation path, or substitute for final RC/app UI,
update and platform acceptance. Native installed fighter admission/play remains
to be exercised.

Latest main's setup-handoff/engine/update and fighter packaging focused suite
passes141tests/10platform skips (`fighter-main-hotfix-integration-unit-1108.txt`).

The7c6394d development app builds and its fresh-directory asset inspection passes
all71Fighter imports. The first final packaging check correctly rejects the reused
output directory containing both1.1.0 and1.1.1 artifacts; the preserved old files
are not removed to conceal that failure. Logs: `fighter-main-hotfix-app-build-1108.txt`
and `fighter-main-hotfix-app-inspection-1108.txt`. The extracted inspected payload
records1.1.1/source7c6394d/toolkit4801dc1; it remains local development material.

The actual first-installed d6f7bac source/executable passes its own build-state
verification. Its adjacent installed Python runs ordinary Manager ZIP installation
and whole-pack activation of Vendetta plus independent starter. No interpreter
override is used for the subsequent native process; process evidence confirms its
direct child runs that adjacent Python and installed `setup/mods.py`. The complete
immutable private save fixture was copied and hash-checked into the fresh disposable
data root; the source baseline remains unchanged. Receipt:
`fighter-real-install-prepare-1108.json`. Native repeated play/teardown is pending.

## Actual installed pause-Quit failure and correction

The real first-installed run `run-20261108-180515.log.err` passes all six
two-human combat assertions, both owned entrances and song/profile coexistence.
Native pause Quit returns to Battle and releases all 24 owned allocations,
restoring the CPU pool's original 33,553,888-byte free block. A native save batch
is acknowledged and the original save guard restores identically. This is real
installed admission/play evidence, with no Python override.

Second-match setup then stops safely at `ControllerSetup(-1,0,0,0)` because the
selection window is still frozen. The process exits 1; the supervisor completes
cleanly, but this is a failed repeat test, not clean game exit or pool reuse.
The pause path reaches native CLogic teardown `89310` without calling the
front-end `Game.Quit` callback `462C0`, where selection was previously thawed.

The correction also finishes immutable selection ownership after `89310` returns
and after motion, cinematic, finisher, film and CPU-pool lifetime checks. It does
not permit a menu command to clear an active match or free retained model records.
The older front-end callback remains supported. A compiled probe uses the actual
wrapper/selection implementation and real window state: clearing stays blocked at
every teardown phase, a pool-check failure prevents thaw, inactive/unapproved
reuse modes stay unchanged, and two cycles retain identities until explicit clear.
Focused window/probe/pool/finisher/teardown checks pass 113 tests in 5.48 seconds
(`fighter-pause-quit-unit-1108.txt`). Re-lift/build and a new installed repeat test
are required before the correction receives native acceptance. Keep the first
installed failure report `fighter-real-install-native-1108.json` unchanged.
