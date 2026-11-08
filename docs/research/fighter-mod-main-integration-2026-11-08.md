# Fighter Mod Support: current-main integration

The owner authorized resolving main conflicts and continuing M5/M6 acceptance.
Source-only PR publication remains authorized; all original and converted
Vendetta files, game assets, saves and captures remain local. Neither PR may be
merged and no pack or release may be published without further authorization.

## Integration scope

Runtime main `15e366b` is integrated into the feature branch. This imports the
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
