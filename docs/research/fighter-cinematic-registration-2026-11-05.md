# Independent intro/victory resources: local implementation checkpoint

M2 remains open. Native selection and body binding now pass for authored
intros and one decisive victory; visual sequence acceptance remains open.
No M3 or publication.
This work uses the player's local data and own lifted code, with no external code.

## Data compiler

`setup/fighter_cinematic_compile.py` composes simple CI/CE templates from the
verified `assets/v2ta.viv`. Its SHA-256 is
`7385473c185e40525c2b821888b1e29da3a4d21e6fb69fcdc73725fb6d5da6c7`.
Each resource declares its local template association, exact rig identity and
full quaternion samples. Existing authored-animation validation handles pose
bounds, finite/unit quaternions, quantization and inherited duration.

The compiler assigns seven-character FI/FV identifiers independently of core,
appearance and logical resource IDs. It rebuilds the body skeletal record while
preserving the paired root track and trusted camera/face/hair resources. Parsed
bank exports, indexed animation names, nested filenames and the outer filename
are renamed together. Numeric/curve payloads are never searched and replaced.
Camera logical names CAM_EYE/CAM_TARGET and their p1/p2 variants stay intact.
This is a bounded simple-sequence profile, not arbitrary cinematic scripting.

FIC1 binds full cores141..16383 to intro/victory identifiers. The header is
88bytes: magic/version/count, bank-archive size, NIS-archive size, reserved0,
then two SHA-256 values. Each20byte row is core u32, intro8bytes, victory8bytes.
Each name is seven ASCII characters plus NUL. Records are sorted/unique.
Generated `fmcNNNNN` XML labels separate cinematic identity from appearance.
Both referenced archives and individual generated resources are rechecked.

Six game-free tests pass. Local CI_113A/CE_113A composition also succeeds:
`logs/fighter-cinematic-compiler-probe.py` and its receipt directory. This is
compiler evidence only; the typed track used in that probe is a static rig pose.

## Native selection and ownership boundaries

Primary source inspection confirms the following chain. Agent audits informed
the investigation; lifted-body inspection is the basis for implementation.

- `87AF0(manager,C,request)`, thiscall/ret8: request+4 is participant index;
  request+C is category. Native code obtains appearance name from manager's
  +2DB34 pointer array and passes it to A1F60.
- `A1F60(C,name)`, ret4, copies the lookup label to C+A8. C+A8 survives
  A3FA0 initialization and asynchronous resource selection.
- `87DB9` sets C+98 from request+18 (camera selector), C+A4 from request+C
  (category), then calls A3FA0 and A3E80. C+98 is not the participant index.
- `A3E80 -> A3E20` kind1 dispatches A3830. It looks up C+A8 in
  `assets/nis.viv|assets/IntroExtro.xml`. Category table2E1D00 selects
  intro0/extro1/blazin2. Non-HERO labels bypass counted HERO variants.
- `A3160(C,selectedName)`, ret4, creates one0x68 actor row and copies the
  selected ID. A3E80 loads `assets/v2ta.viv|<ID>.viv` through category17.
- `A2020` loads body/face/hair `<ID>.o`, `<ID>_f.o`, `<ID>_h.o`. A2190 uses
  numbered camera helpers for category0 and unnumbered helpers for category1.
- `A1FA0 -> 9E640 -> 24290` binds `<ID>_s`/`<ID>_t` to the actor pose through
  native ELF/AnimationBank lookup and22010. Face/hair use24430/24610.
- `8818C -> A1ED0` associates the ordinary row0 with the visual table entry
  for request+4. Native allocation, loader ownership and teardown remain native.

Proposed runtime scope: capture descriptor/core during87AF0, change its label
after A1F60, restore nested context on return. Validate kind1, categories0/1,
participant0..3, matching full core from manager config+A8 and3B90B8 globals.
The manager's +2B9EC flag0x02000000 enables a separate two-actor path; reject
owned simple sequences there rather than silently taking unsupported ownership.
Preserve request+20 and C+D4; ordinary/HERO setup with that flag clear yields
one actor. A3160 can validate the selected name using the persistent generated
label, including after asynchronous loading outside87AF0.

## Remaining acceptance

Implement/test the scoped native binding and both-archive receipt checks;
show different sequences for fighters sharing one appearance; verify actual
body evaluation at entrances and a decisive victory; verify camera helpers,
resource cleanup and unchanged retail sequences. Blazin combat special moves
remain a separate investigation: the venue-scoped blazin_ko XML parser is not
a fighter moveset binding. No inference from paired filenames alone is accepted.


## Native implementation and first acceptance checkpoint

The scoped adapter and three real wrappers are implemented. FIC1 verifies both
archive hashes and sizes, rejects invalid/duplicate/out-of-range core rows and
malformed/padded names, and only activates under the isolated research driver.
The runtime preserves native request, row, camera and loader ownership. The
persistent label is checked against the selected clip at A3160; mismatches stop
instead of silently inheriting another fighter's sequence.

27 focused Python/MSVC tests passed before adding one archive-budget test;
subsequent Python suite7passed, including malformed receipt shapes. Build and
relift PASS: logs/fighter-cinematic-relift-nov05.txt and
logs/fighter-cinematic-build-nov05.txt (51wrappers,21Cfiles,67MiB generated).
Read-only review found a malformed nested receipt could escape as KeyError;
shape validation and rejection coverage now address it.

Human050022 PASS6combat assertions,199frame reports95/120/121; zero
crash/watchdog/debug-layer/truncated-batch/unresolved-call faults; one verified
save generation restored byte-identically. Native log
logs/run-20261105-050022.log.err; result logs/fighter-authored-cinematic-human-native.txt;
captures logs/fighter-window-runs/07fa527cb94945dab9919c85e1ffc8e1/captures.
The game displayed two intros in this four-player match: selected FI00000 for
core256 and FI00002 for258, with corresponding24290 body-bind calls. This does
not prove the other two cores' intros or any victory. A late read-only sampler
started after those sequences had ended and found no current cinematic poses;
that empty sample is not failed playback evidence.

A CPU follow-up places two fighters sharing an appearance in the first two
intro slots, runs toward a decisive result, and monitors currently bound poses.
Two initial attempts were rejected before native launch: duplicate screenshot
labels, then a noncompact direction schedule exceeding the pad-script budget.
Both recorded0save generations. Corrected route is prevalidated at1003bytes /
68entries and saved in logs/fighter-authored-cinematic-cpu-native.ps1. Current
native run051136 is still in progress; no victory or full M2 claim yet.

## CPU result and live ownership evidence

Run051136 finished successfully: eight combat/result assertions,324 frame
reports min101/median120/max120, zero crash/watchdog/debug-layer/truncated-batch/
unresolved-call faults, one verified save generation restored byte-identically.
Result: logs/fighter-authored-cinematic-cpu-native.txt; native log:
logs/run-20261105-051136.log.err. Preserved captures are under
logs/fighter-window-runs/583bc35bd5e54c0baa0d46af83375dc7/captures.

All four cores256..259 selected FI00000..FI00003 respectively, including
distinct resources for the two fighters sharing the same appearance. Native
24290 body-bind calls followed each selection. The first live sampler captured
matching owned descriptors and parent/child/record-cell edges in all four
participant poses. Its intro/victory descriptors are identical fixture data,
so its candidate rows cannot independently distinguish FI from FV.

The improved sampler additionally checks the bank's indexed record name and
stable current pose pointers. It captured core259, slot3, FV00003_s during
phase3, with the generated child wrapper pointing to the expected serialized
child. The native A3160/24290 trace independently selected/bound FV00003.
Evidence: logs/fighter-motion-probes/78dce1e261684655af27e73e2c60d63a/
cinematic-live-named-proof.json. This proves the winner's owned skeletal
resource binding/evaluation structure, not the aesthetic quality of the pose.

The early1..9second screenshots show the venue fly-in; result-relative shots
show the summary after the victory. Neither set visually accepts the authored
intro/victory pose. A follow-up should anchor captures to the actual FI/FV
selection diagnostic, with action input delayed until intros have finished.
Current fixture tracks are deliberate rest poses plus arm oscillation, not
finished choreography. Stock regression is now running separately.
