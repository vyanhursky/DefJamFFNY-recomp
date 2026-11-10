# Retail appearance overrides and selectable extra outfits

The owner requested two private Pockets red-pants test packs: replacing his
existing retail appearance, and preserving it while adding an extra selectable
outfit. Source integration combines the Workshop performance and retail-authoring
branches. Original game resources, projects and captures remain private.

## Runtime contract

Appearance-only overrides use the existing `overrides` manifest contract. They
retain the original native core and retail identity. The owned appearance PNG
compiler emits a native fallback and a namespaced HD texture layer. Retail UI
art replacement is still refused by the existing ownership guard.

An added fighter may declare `outfit_of: retail/NAME`. The resolver verifies
that its non-appearance/non-portrait components equal the parent's, including
moveset, stats, voice and AI. Native compilation creates an owned immutable
appearance record with the parent's combat core, not a separate public fighter.
The original selector's parent CCharacter receives another aDataSets entry.
ControllerSetup consequently submits the hidden logical identity selected by
the ordinary clothing control. Parent groups remain limited to three outfits.

FWR1 remains byte compatible. FWR2 uses the last row word as retail selection+1
(zero means an independent fighter), including retail selection zero. Native
decoding bounds it to the original selection domain. Progress insertion and
ready unlock projection map costume identities to the canonical retail handle;
loading/results use the canonical retail selection. Battle retains the owned
appearance record. No new supervisor setting or user-supplied guest pointer is
introduced. The selector Back wrapper retains bindings for ready retail parents
that own hidden outfits, as it already does for independent custom fighters.

## Focused evidence

Windows x64 release build uses the pinned xboxrecomp 4801dc1 toolchain and the
same verified lift/manual-override inputs as the performance integration.
Native original APT templates compile for the real owner's dump. Invented
fixtures cover unchanged parent records/cores, shared-component refusal, outfit
capacity, menu parent bounds, Back ownership mapping and FWR1/FWR2 admission.

The Workshop's real Qt/WebChannel retail editor opens the portable outfit
project, disables unrelated combat controls, renders Pockets with red pants,
and positions the viewer to the right of customization. Normal package
installation, activation and production compilation accept both independent ZIPs:
override adds0/edits1; extra outfit adds1/edits0, with the addition hidden from
the public roster.

Initial native selector investigation reached the original Pockets cell and
the original clothing control showed choices1/2. Choice1 retained his green
pants. Choice2 submitted logical100/core64, and a subsequent scripted native
match rendered the red-pants appearance under the Pockets name. The selector's
inherited portrait is a static original image; body atlas edits do not recolor
that separate artwork. A corresponding authored portrait remains optional.

## Final Windows native qualification

Both final 200-second runs used the rebuilt FWR2 retail-selection+1 runtime and
installed ZIP manifests, with actual original-menu navigation (no StartGame
fighter-ID replacement):

| Case | Exact selector identities | Combat | Frame samples | Save/fault checks |
| --- | --- | --- | --- | --- |
| Extra outfit |100,56 (Pockets red, Blaze) |5/5 |100 two-second samples, min104/median120/max120 | restored identical; one verified generation; zero fault signatures |
| Retail override |76,56 (Pockets, Blaze) |5/5 |100 two-second samples, min100/median120/max120 | restored identical; one verified generation; zero fault signatures |

Combat checks verify well-formed telemetry, native setup, human movement,
human attack and target damage. Captures show red pants on the battle models
with the Pockets HUD name. The extra outfit's original green appearance remains
choice 1 in the original clothing selector. Both packs independently install,
activate and compile through the normal Manager path.

Local receipts: `logs/pockets/final-outfit-result.txt`,
`logs/pockets/final-override-result.txt`, native logs
`logs/run-20261110-112649.log.err` and `logs/run-20261110-113023.log.err`.
Focused checks: 50 passed; final real Qt/WebChannel preview/control check passes.
No broad regression or decisive result/rematch qualification is claimed.

CI initially found that the existing extracted-function unlock-projection
fixture omitted the new canonical-progress helper. Its fixture now compiles the
actual helper and insertion function. An additional native case verifies that
stale standalone progress metadata for an outfit key cannot duplicate or alter
its retail parent's mark on selection, while actual insertion keeps metadata
and adjacent guest words intact. The expanded focused suite passes56 tests.
The correction leaves the fresh-progress native cases above unchanged.

## Retained negative evidence and limits

The first native attempt stalled at startup with a D3D fence wait and no
presented frames. No fence/toolchain bypass was introduced. A no-mod control
and subsequent same-binary selector runs rendered normally. This does not prove
the cause of the original stall. One command exceeded the native16-capture
limit and was rejected before launch. Early interactive runs only reached
selection or the venue screen; they are not battle acceptance. A later test
incorrectly expected Blaze's alternate selection81 while choosing original56;
that assertion must not be reported as a passing command.

Qualification is limited to the documented private Pockets case on Windows.
Full regressions and other OS/gameplay combinations are deferred per the owner.
There is no release, merge or asset-publication approval.
