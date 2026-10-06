# Known issues and validation limits

Playable Windows x64 was accepted by the maintainer on October 4, 2026. Test
routes cover menus, setup, a fight, Story intro/creator, crib/gym and Unlock
Fighters selection. They do not cover every mode or a full Story campaign.

## Remaining investigations

- **Unresolved jump targets.** The translated code has about a hundred placeholders for
  jump targets the translator could not resolve; reaching one skips real code. v0.2.1
  replaced the seven that are simple function exits, one of which caused the Terrordome
  crash. Roughly seventy more decode as real code and need the translator's function
  extents fixed. `python scripts/stub-targets.py` lists them. None is known to be reached.
- **A rare crash in the sound library (guarded since v0.2.3).** One of three Debug runs of the
  scripted four-fighter Terrordome match crashed in the game's DirectSound code
  (`sub_002626B5`, on the audio interrupt's thread). The interrupt routine looks up the client
  of a hardware voice the audio chip reported idle and does not expect to find none; the chip
  model services that trap about a millisecond late and lets a later event overwrite the voice
  number, so the entry can be empty. The lookup (`sub_0025FB7C`) is now hand-written with the
  missing test and logs `[DSOUND] idle trap ... with no client` when it fires. It has not
  fired in the six Debug and Release runs since, so the guard is unproven against the real
  event; the model's trap handling is the underlying fault and is unchanged
  (`docs/research/dsound-voice-list-crash.md`).
- **A dropped audio buffer at a knockout.** Both scripted fights that were played to a
  knockout dropped exactly one audio buffer in the slow motion after it, and none before.
  Not investigated; it has not been noticed by ear.
- Two-pad play is covered by a scripted match (`versus`: both emulated pads join, pick fighters
  and land hits). Real controllers, and three or four pads, have not been checked.
- Long-session memory use over multiple fights remains to be measured.
- Earlier builds had a rare silent boot and a rare crash at guest `sub_001A3310`.
  The clean rebase soak does not prove those are eliminated.
- Previously recorded visual issues include a loading-bar glitch, black profile
  thumbnails, Blazin' film grain and half-pixel alignment. None was observed in
  the owner's accepted play-test; wider coverage remains backlog.
- Optional CPU vertex-program fallback performance is unmeasured after rebase.
- Audio counters do not prove fidelity of every track/effect; owner listening
  accepted the experience.

## Future features

MSVC is the supported compiler. Clang is not a validated build path: expanded CI
exposed a 32-bit NEG flag test failure under Clang optimization and a switch
fixture compilation issue. The Release gate selects MSVC for the shared CPU
fixture; it does not establish Clang or native Linux correctness.

A settings file, borderless full screen, a resizable window and render-scale choice
arrive in v0.2.0. Exclusive full screen is not offered; the flip-model borderless window replaces it. Vsync
paces the game only on displays whose refresh rate is a multiple of 60. Changing `render_scale` needs
a restart. Other controllers, keyboard gameplay controls, an in-game settings menu,
true 16:9 and texture packs are planned for later M6 releases ([plan](07-m6-plan.md));
music replacement and frame rates above 60 are not planned for M6. Proton, Steam Deck, macOS
and native Linux are unvalidated platforms. Network play is not supported.

See the [improvement backlog](04-improvement-backlog.md) and
[rebase acceptance](research/toolkit-rebase-acceptance.md) for details.
