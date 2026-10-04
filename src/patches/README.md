# src/patches — gameplay patches (opt-in)

Behavioural changes to the game, each behind a runtime toggle so the vanilla path stays testable:
- `framerate.c` — delta-time / 60 FPS unlock (M6),
- `display.c` — resolution and aspect handling for 16:9 and Steam Deck 16:10 (M5),
- `input.c` — 4-pad mapping, Steam Input quirks.

Do not add anything here before M4 (a playable match) is reached; bring-up fixes belong in `src/hooks` or `src/recomp_manual.c`.
