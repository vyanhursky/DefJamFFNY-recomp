# Known issues and validation limits

Playable Windows x64 was accepted by the maintainer on October 4, 2026. Test
routes cover menus, setup, a fight, Story intro/creator, crib/gym and Unlock
Fighters selection. They do not cover every mode or a full Story campaign.

## Remaining investigations

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

Player-facing settings, resolution/aspect controls, texture/music override folders
and keyboard gameplay controls remain future PC work. Proton, Steam Deck, macOS
and native Linux are unvalidated platforms. Network play is not supported.

See the [improvement backlog](04-improvement-backlog.md) and
[rebase acceptance](research/toolkit-rebase-acceptance.md) for details.
