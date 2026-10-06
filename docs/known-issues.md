# Known issues and validation limits

Playable Windows x64 was accepted by the maintainer on October 4, 2026. Test
routes cover menus, setup, a fight, Story intro/creator, crib/gym and Unlock
Fighters selection. They do not cover every mode or a full Story campaign.

## Remaining investigations

- **Terrordome crashes.** Matches at the Terrordome can freeze and close: a scripted
  four-fighter Free For All crashes within a few minutes on both v0.1.0 and v0.2.0, at
  guest `sub_001B54D0`; a One on One there crashed once at `sub_001A3310` and ran four
  minutes clean in another run. `python scripts/harness.py run ffa-terrordome` reproduces it.
- Two-player gameplay needs an end-to-end check; four-slot USB fixtures are not
  a multiplayer gameplay test.
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
