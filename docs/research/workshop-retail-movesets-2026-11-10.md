# Workshop retail CAF movesets

Owner requested complete retail movesets as an alternative to CAF combinations,
including directly edited Story profiles. This extends Workshop modpack/CAF
authoring; it does not add arbitrary animation import or an editor animation
player. Source, invented fixtures and evidence summaries only; all game/profile
bytes and native captures remain private.

## Explicit contracts

Workshop project v6 adds optional shared `fighter.retail_moveset`, a stable
`retail/<original-symbol>` identity. Its original CAF `styles` remain available
as a fallback. CAF v5 accepts the same key alongside the v4 appearance/outfit,
atlas, sculpt, portrait and four-finisher fields. Compilation resolves the
trusted original Character record's motion core (1..86), rather than inferring
a CAF combination from its style mask. Costume records sharing a core collapse
to one menu option; the original Xbox database yields 69 distinct choices.
Original style metadata supplies the retail moveset's menu classification.
Appearance, training, voice donor and separately selected finishers stay authored.

A compilation containing a retail CAF emits `FCA3`, version3, stride240. Row
byte225 explicitly marks retail-motion mode (1); its core at +4 must be1..86.
Mode0 retains the87..141 CAF bounds. Bytes226/227 remain zero. Outfit index+232
and presentation alias+236 keep FCA2 semantics. FCA1/FCA2 remain unchanged and
cannot silently accept retail cores. Full pack validation, hashes, immutable
selection identities, per-participant contexts and existing sculpt/atlas guards
still apply.

## Direct profile boundary

The verified saved Battle core is payload byte0x137 (native profile+0x143).
The separate Story mirror at payload0x4d87 (native+0x4d93), component styles,
bonuses, career data and all unrelated bytes remain untouched by retail mode.
Original style-training/recompute actions can replace the Battle byte normally.

Original match setup consumes that byte into service+0x168+4*participant. Match
config starts at service+0xc0, so config+0xa8 refers to this same core array;
config+0x128 refers to the native CAF context-selection flags at service+0x1e8.
Original1E410/8B730 own profile-to-context lookup, assembly, events and cleanup.
The adapter observes those contexts instead of preassembling a Story profile.

Actor/WPAR setup consumes the selected retail core before1A8180. Original CAF
intro/presentation paths87BA4/87C60 also gate on config+0xa8>=87. The adapter
therefore restores only the Story CAF's presentation-config core to its career
class after actor/finisher initialization, retaining the live actor motion core
and saved profile unchanged. Clear restores its config write only while owned.
The existing real-profile audio route retains its original speech selection.

Original1A8180 copies profile Blazin' choices into actors only for CAF cores.
The CAF adapter explicitly binds its four chosen values to retail-core actors
before mask construction. Direct Story values come from the original resolved
profile matrix; standalone values come from the validated extras sidecar.
Both are bounded to the original82-choice pool; unrelated participants retain
native behavior. This is independent of moveset selection.

## Qualification

Workshop editor/history/save/round-trip and complete pack compilation passed.
Native standalone CAF Blaze/D-Mob selection started a match with cores5/51 and
authored CAF models. Initial direct-profile retail tests stalled in the intro;
the unchanged profile control reached combat, so those failed runs remain
negative evidence. With the presentation boundary, `run-20261110-084737.log.err`
reached match_start with actor core50 (D-Mob's one-based core51), authored VY3
CAF model, original201.6 health, speech538 and profile choices77/49/49/49. Combat
damage events followed; the12s/22s captures show the saved CAF during intro and
combat.77 presentation intervals, median120 presents/2s, no crash/watchdog,
unresolved calls or debug-layer errors; copied saves restored identically.

58 final focused runtime tests pass, including native C reader refusal cases,
Story profile/context ownership, four-choice binding and mixed audio ABI/lifetime.
The final new-match cleanup guard was unit-checked and built after that pilot.
The broader unit run had2489 passes and34 sandbox permission failures; all five
affected files reran outside that sandbox with127 passes/2 skips. Source hygiene
passes. Workshop has163 Python and7 viewer tests plus actual Qt save/reopen and
complete three-outfit/sculpt/art export checks.

Owner deferred broad regressions on2026-11-10 to joint testing after further
features. Direct-profile Blaze, Story career fights, rematches, multi-profile
transitions and the broader retail roster remain for that session. Windows
focused native evidence does not imply macOS/Linux gameplay qualification.
