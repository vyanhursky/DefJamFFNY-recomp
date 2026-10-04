# Superseded hand-offs, September 2026 (archived from PROGRESS.md §7)

> The hand-off blocks `PROGRESS.md` §7 replaced, kept for their address tables and the reasoning
> behind earlier decisions. Newest first. Anything here that contradicts §7 is out of date.

### State as of 2026-10-02 13:10 (superseded 2026-10-02 17:30)

**Where it stands.** M3 and M4a-M4c are met, M4e is met, M4d and M4f are under way. A One on One match plays
to a KO with sound at the right speed. Story mode runs from a new user ID through the cutscenes, the
creator and the tutorial, and Vlad has played Story matches at the Foundation and The Limit with two
profiles. **The release build is the one to play** (`scripts/build.ps1 -Preset win-x64-release`,
`scripts/run.ps1 -Preset win-x64-release`): 60 frames a second through the Story route and a fight. The
toolkit patches run to 0108.

What changed on 2026-10-02 (§6 has each): the start-up hang (0103, a kernel timer's signal lost on re-arm);
the "second profile is damaged" bug (0104, a directory search surviving its handle); batches up to 32,768
indices (0105, the rails in the escort cutscene); the title's gamma ramp applied at presentation (an entry
hook in `src/recomp_manual.c`, no toolkit change; `RECOMP_GAMMA=0` turns it off and the goldens are checked
with that set); texture filtering as the title sets it (0106; everything had been point-sampled).

**Start here: Vlad's check of his 2026-10-02 list** (§6 2026-10-02 10:20 has the list). He compares
against console video (`https://www.youtube.com/watch?v=pJVJiX2_-ao`, "Def Jam Fight for NY (2004) - Xbox
Playthrough - Part 1 4k").
1. Cutscenes and The Limit lighter than the console: the gamma ramp. Unverified by him.
2. The escort scene's missing rails and black triangle: fixed (0105).
3. Green rims on the creator's photographs: the console has them too (baked into the DXT5 photo textures;
   enlarge the video at 4:36). Not a bug.
4. Learn Moves in Stapleton Athletics: the move videos play when X (Preview) is pressed (the `gym` route,
   `run-20261002-125814`); his log of that session shows no movie was requested. Ask whether X was pressed.
5. Only one profile at a time: fixed (0104). His save area has VY1 and VY2, both valid.
Not from his list: the profile thumbnails on Select User ID are black squares; film grain in Blazin' (no
separate pass found); glows in other venues; whether screen positions need a half-pixel shift (tried and
taken back, §6 12:30 -- it needs evidence from hardware or from xemu's source, not from reasoning).

**Driving it unattended.** `python scripts/harness.py run <route>` (routes: boot, fight, crib, gym, intro;
CLAUDE.md §4b) and `python scripts/regress.py` for the whole regression run. Menus are scripted by anchors:
each stage waits for a substring of a `[FUNCCALL]` line. What the routes do, for extending them:
- fight: `getscreeninfo(intmain/mainmenu=right@5;a@8`, then the Battle screens, `@game.startgame(,<presses>`
  (`scripts/pad-chain.py match`). With more than one user ID in the save area Battle asks for one first.
- Story with the first profile in the list (goes to the crib): `getscreeninfo(intmain/mainmenu=a@6`,
  `getscreeninfo(options/userid=down@4;a@7`, `getscreeninfo(story/crib=<presses>`. The crib opens on a
  "Messages Waiting" prompt (down, A for NO); its bar is Map, Messages, Wardrobe, Options, Trophies, Exit.
- Stapleton Athletics from the crib: `getscreeninfo(story/crib=down@4;a@6;a@10;a@16;down@24;a@29` (NO, Map,
  Shop District, down to the gym, enter), then `getscreeninfo(story/gym=down@4;down@6;a@9` opens Learn
  Moves; X previews a move. The map: Shop District -> right Club 357 -> right The Limit; up from Shop
  District is the Foundation.
- Story from a new ID (the cutscenes): on the user-ID screen `a@5;a@7;a@8;a@9;down@11+0.6x9;right@17.5;
  a@19;a@23+3x6` types AAA and takes DONE; `game.startstorymode(=back@9999` lets the cutscenes play (the
  escort shot is 16 s after that anchor in release, the car crash 46-62 s); the creator's first screen is
  `getscreeninfo(story/chardec`; then A presses through the creator, `game.continueload(`,
  `game.showfightingmovie(=a@6;left@9;a@11` (the style prompt defaults to NO), `@game.entertutorialmode(`.
- **The save area**: Story routes run inside the harness's save guard, which copies `save/UserData` aside
  and restores it (the last three copies stay in `$DEFJAM_DATA/save-guard/`). Vlad's profiles are VY1 and
  VY2; `$DEFJAM_DATA/save-UserData.bak-20261002a` is a hand-made copy from 2026-10-02 morning.
- Scripted runs ignore the host's pad (0093); a stage's presses end when the next anchor arrives.
`RECOMP_PB_BATCH_DUMP=shot` dumps the flip after each capture (array-drawn batches are marked `arrays`);
`RECOMP_PB_PROBE=x,y;...` adds the triangles over those pixels; `RECOMP_PB_UNHANDLED_ALL=1` lists every
method the executor does not implement; `RECOMP_PAL_DUMP=<addr>[~<mask>],<file>` writes expanded palettised
textures; `scripts/peek-guest.py <addr> <size>` reads a texture out of the running game (a contiguous
address such as 0x823A8500 is its guest address).

**Other open items.**
- The **start-up hang** was a kernel timer's signal lost on re-arm (0103): 45 of 45 boots after, about
  1 in 15 before. A different stop was seen once since: a debug boot whose log ends mid-frame about 30 s in
  (`run-20261002-110917`), the timer thread included, no crash record. `python scripts/harness.py soak --boots N --preset win-x64-debug` stops at a boot
  that stops presenting and writes its stacks and device state to `logs/hang-<stamp>/`.
- The **D3D11 debug layer** ended at least two debug runs during a Story load with exception 0x87D (WER
  events 2026-10-01 12:38, 12:58). Patch 0091 prints its messages as `[D3D11-DEBUG]` and continues; it has
  not fired since. Grep for that after any silent exit of a debug build.
- **M4d**: two pads, three fights with stable private bytes, the rare `sub_001A3310` crash at a fight's
  start, the loading-bar glitch, a rare boot with no sound (possibly the 0103 timer bug; unverified).
- The fence hold (0095) engages ~500 times a second in a release fight and has never timed out; if a
  scene ever stutters in release, `RECOMP_FENCE_HOLD=0` tells whether it is the hold.
- Face culling is never enabled by the title; a cull path was written and removed unverified.
- `tools/recomp` pytest: 2 failures in `test_icall_feedback` predate this work.
- The work-log archive is by month (`docs/worklog/2026-09.md`, `2026-10.md`).

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:8:8.4,a:14:14.3` holds each button over the given span
of seconds (names: up down left right start back ls rs a b x y black white lt rt). An `@anchor` entry puts
the entries after it on the clock of that anchor and ends the ones before it; `RECOMP_TRANS_SHOT_SECS`
takes the same tokens (at most 16 captures). Captures carry the gamma ramp, as the window does.

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript; transitions are in `screens/feflow.xml`.

**Known loose ends in the GPU model.** Modelled: depth, stencil, blend (constant colour and equation
included), alpha test, combiners, four texture stages, palettes, address modes, min and mag filters, the
surface clip, indexed and array draws, point sprites, the display's gamma ramp. Not modelled: polygon
offset (the title enables it with zero factor and bias), fog (the title sets fog enable and colour; no
final combiner seen reads the fog register), float depth, texture-shader modes beyond plain 2D/3D/cube,
render targets sampled as textures (everything is drawn into one back buffer), mip levels (only level 0 is
uploaded), the G8B8/R8B8 formats' channel mapping, lines and points on the CPU vertex path, batches over
32,768 indices (truncated, with a log line).

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For functions reached
only through data, `scripts/gap-seeds.py` finds them in bulk. For any stall, `scripts/native-stacks.py`
gives every thread's host call stack with names; `scripts/sample-threads.py` gives guest IPs.


### State as of 2026-10-02 01:50 (superseded 2026-10-02 13:10)

**Where it stands.** M3 and M4a-M4c are met, M4e is met (2026-10-02: a debug fight holds 60 frames a
second, three in a row without a crash), M4d and M4f are under way. A One on One match plays to a KO with
sound at the right speed. Story mode runs from a new user ID through the car-crash cutscene, the character
creator, the room cutscene, Choose Style and the tutorial, and Vlad has played a full Story match and saved.
**The release build works and is the one to play**: 60 frames a second through the whole Story route and a
240 s fight, no crash (`scripts/build.ps1 -Preset win-x64-release`, `scripts/run.ps1 -Preset
win-x64-release`). The toolkit patches run to 0106.

What changed on 2026-10-01/02, in the order it was found (§6 has each): packed normals (0089, the pale flat
lighting); a lifter fix for a branch on an overwritten register (0090, the tutorial that never advanced);
constant-colour blending (0092, the Foundation's tint and Blazin's filter); no second draw of inline arrays
(0094, the magenta Message Center); a hold at Direct3D's fence insert through a new lifter entry hook
(0095, the release crash); swizzled textures unswizzled once (0096); DRAW_ARRAYS and point sprites (0097,
car lights, smoke, sparks); method tallies by index and ring buffers for draws (0098, 0099, the frame rate).

**Start here: Vlad's check of the M4f to-do.** Every item from his playthrough of 2026-10-01 has a fix in;
none has had his eye yet. He compares against console video (`https://www.youtube.com/watch?v=pJVJiX2_-ao`,
and "Def Jam Fight for NY (2004) - Xbox Playthrough - Part 1 4k").
1. Intro cutscene: the car lights, smoke and sparks draw (0097); it runs at 60 in release (0098, 0099),
   which should end the camera judder and probably the sound dropping out -- both unverified by ear or eye,
   because captures show neither. "Lighting missing in places" beyond the car lights is not pinned down;
   ask him where.
2. Message Center: fixed (0094).
3. The Foundation's dark green tint and vignette: fixed (0092).
4. Blazin' mode: warm filter and vignette fixed (0092). The dumped frame has no separate film-grain pass;
   if the console's grain is real and not video compression it is still to find.
Then, not from his list: the tutorial past step 1 has only his word ("works"); glows in venues with lights
(the point-sprite path is new, look at any venue with lamps); the stage-3 texture left bound in cutscene
batches (`805D1280`) now matters more, because point sprites sample stage 3.

**Driving it unattended.** Menus are scripted by anchors: each stage waits for a substring of a
`[FUNCCALL]` line. The scripts live outside the repo (scratchpad: `kofight2.sh`, `crib_run.sh`,
`newid_run.sh`, `tut_run.sh`, `chain.sh`, `mkchain.py`; `RECOMP_PRESET=win-x64-release` picks the build).
The chains:
- fight: `getscreeninfo(intmain/mainmenu=right@5;a@8`, then the Battle screens, `@game.startgame(,<presses>`
  (`scripts/pad-chain.py match`). With more than one user ID in the save area Battle asks for one first.
- Story with Vlad's profile VY1 (2% complete, goes to the crib): `getscreeninfo(intmain/mainmenu=a@6`,
  `getscreeninfo(options/userid=down@4;a@7`, `getscreeninfo(story/crib=<presses>`. The pager: A on
  "Messages Waiting", downs to a message, A.
- Story from a new ID (the cutscenes): on the user-ID screen `a@5;a@7;a@8;a@9;down@11+0.6x9;right@17.5;
  a@19;a@23+3x6` types AAA and takes DONE; `game.startstorymode(=back@9999` lets the car cutscene play
  (50-100 s after that anchor in release); then A presses through the creator, `game.continueload(`,
  `game.showfightingmovie(=a@6;left@9;a@11` (the style prompt defaults to NO), `@game.entertutorialmode(`.
  A test ID comes back "Damaged game" on a later run, so `newid_run.sh` first restores the save area.
- **The save area**: `$DEFJAM_DATA\save-UserData.bak-20261001b` is `save\UserData` as Vlad left it on
  2026-10-01 evening (VY1). Restore it after any run that creates an ID
  (`rm -rf save/UserData && cp -r save-UserData.bak-20261001b save/UserData`); it was restored at the end
  of this session. Take a fresh backup before scripted Story runs once he has played further.
- Scripted runs ignore the host's pad (0093); a stage's presses end when the next anchor arrives.
`RECOMP_PB_BATCH_DUMP=shot` dumps the flip after each capture (array-drawn batches are marked `arrays`);
`RECOMP_PB_PROBE=x,y;...` adds the triangles over those pixels; `RECOMP_PB_UNHANDLED_ALL=1` lists every
method the executor does not implement; `RECOMP_PAL_DUMP=<addr>[~<mask>],<file>` writes expanded palettised
textures.

**Other open items.**
- The **start-up hang** (presenting stops before the main menu) was a kernel timer's signal lost on
  re-arm, which stopped the movie player's 120 Hz tick; fixed by 0103 (§6 2026-10-02 04:40): 45 of 45
  boots since, against about 1 in 15 before. If it returns, `hangcatch.sh` + `hangpeek.py` print the tick
  counters (`0x3C9684`) and `scripts/native-stacks.py` shows whether `sub_001F98A2` is parked.
- The **D3D11 debug layer** ended at least two debug runs during a Story load with exception 0x87D (WER
  events 2026-10-01 12:38, 12:58). Patch 0091 prints its messages as `[D3D11-DEBUG]` and continues; it has
  not fired since. Grep for that after any silent exit of a debug build.
- **M4d**: two pads, three fights with stable private bytes, the rare `sub_001A3310` crash at a fight's
  start, the loading-bar glitch, a rare boot with no sound. "Flicker on hits" may have been the dropped
  DRAW_ARRAYS batches (hit sparks are particles); ask Vlad.
- The fence hold (0095) engages ~500 times a second in a release fight and has never timed out; if a
  scene ever stutters in release, `RECOMP_FENCE_HOLD=0` tells whether it is the hold.
- Face culling is never enabled by the title; a cull path was written and removed unverified.
- `tools/recomp` pytest: 2 failures in `test_icall_feedback` predate this work.
- The work-log archive is by month (`docs/worklog/2026-09.md`, `2026-10.md` when October entries age out).

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:8:8.4,a:14:14.3` holds each button over the given span
of seconds (names: up down left right start back ls rs a b x y black white lt rt). An `@anchor` entry puts
the entries after it on the clock of that anchor and ends the ones before it; `RECOMP_TRANS_SHOT_SECS`
takes the same tokens (at most 16 captures).

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript; transitions are in `screens/feflow.xml`.

**Known loose ends in the GPU model.** Modelled: depth, stencil, blend (constant colour and equation
included), alpha test, combiners, four texture stages, palettes, address modes, the surface clip, indexed
and array draws, point sprites. Not modelled: polygon offset (the title enables it with zero factor and
bias), fog (the title sets fog enable and colour; no final combiner seen reads the fog register), float
depth, texture-shader modes beyond plain 2D/3D/cube, render targets sampled as textures (everything is drawn
into one back buffer), the G8B8/R8B8 formats' channel mapping, lines and points on the CPU vertex path,
batches over 4,096 indices (truncated).

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For functions reached
only through data, `scripts/gap-seeds.py` finds them in bulk. For any stall, `scripts/native-stacks.py`
gives every thread's host call stack with names; `scripts/sample-threads.py` gives guest IPs.


### State as of 2026-10-01 13:40 (superseded 2026-10-02 01:50)

**Where it stands.** M3, M4a-M4d are met and M4e (vertex programs on the GPU, default since 0080) is met in
debug builds; M4f (looks like the console) is under way. A One on One match plays to a KO with sound at the
right speed, and Story mode runs: main menu -> profile "AAAAAB" -> character creator -> the intro cutscene
(about 60 s) -> Choose Style. The tutorial fight after Choose Style has not been scripted or checked.
Since 2026-09-29: stencil (0081), register combiners and texture stages 1-3 (0082), caller-cleans indirect
calls skip without shifting the stack (0083, the Story walker crash), luminance texture formats (0085, the
green eyes), the surface clip as a scissor (0086, the cutscene letterbox), the single-index array element
(0087, holes in every odd-length strip: faces in cutscenes, and anything else drawn as strips). Fight
shadows work (stencilled flattened fighters, blob quads for the crowd): §6 2026-09-30 22:45.

**Driving it unattended.** Menus are scripted by anchors: each stage waits for a substring of a
`[FUNCCALL]` line. The session's scripts live outside the repo (scratchpad `story_run.sh`, `kofight2.sh`,
`chain.sh`, `mkchain.py`); the chains they build are:
- fight: `getscreeninfo(intmain/mainmenu=right@5;a@8+4x6` ... `@game.startgame(,<presses>` (see
  `scripts/pad-chain.py match`);
- Story: `getscreeninfo(intmain/mainmenu=a@5`, `getscreeninfo(options/userid=down@5;a@8+3x90`,
  `game.continueload(=back@9999` (no presses after ContinueLoad, or the cutscene is skipped). Give a debug
  run 420-440 s; captures `RECOMP_TRANS_SHOT_SECS=@game.continueload(,10,25,40,55,70` (70 s is Choose Style).
  On into the tutorial: `game.continueload(=a@8+3x40` (skips the cutscene),
  `game.showfightingmovie(=a@6;left@9;a@11` (the style prompt defaults to NO), then presses on
  `@game.entertutorialmode(`; 540 s. The Story load alone is ~105 s in a debug build.
  The profile list is now "VY1" (Vlad's, first) only: the scripted test profile AAAAAB went "Damaged game"
  and was moved to `$DEFJAM_DATA\save-removed-20261001`; `save-UserData.bak-20261001` is the area as it
  was before that day's runs.
`RECOMP_PB_BATCH_DUMP=shot` dumps the flip after each capture; `RECOMP_PB_PROBE=x,y;...` adds the triangles
over those pixels with their depths.

**Start here: the M4f to-do, from Vlad's playthrough of 2026-10-01** (§6 that date: he played the tutorial
and a full Story match on profile VY1, and his progress saved). He compares against console video
(`https://www.youtube.com/watch?v=pJVJiX2_-ao`, and "Def Jam Fight for NY (2004) - Xbox Playthrough - Part 1
4k"). **Do not launch the game until he says to start.** Confirmed good by him: the tutorial end to end, the
button icons (R3 included), the shops; earlier: eyes, letterbox, faces. Open, in his order:
1. **Intro cutscene**: lighting still missing in places, the camera judders, the sound cuts off. The cars
   have no light effects (console: a large white bloom on the headlights, a red glow on the tail lights).
2. ~~Message Center (the pager) magenta~~ **fixed, 0094** (§6 2026-10-01 22:25); needs Vlad's eye.
3. ~~The Foundation's dark green tint~~ **fixed, 0092** (§6 2026-10-01 21:30); needs Vlad's eye.
4. ~~Blazin' mode's yellow filter and vignette~~ **fixed, 0092**. No separate film-grain pass exists in the
   frame; if the console's grain is real and not video compression, it is still to find.

He gave leave on 2026-10-01 evening to test through the night. For the intro cutscene a new user ID is
made by script (`newid_run.sh`: A on Create, three letters, nine downs and a right to DONE); back up the
save area's `UserData` first (`save-UserData.bak-20261001b` is the area before those runs) and remove the
test ID afterwards. Scripted runs ignore the host's pad since 0093.

Smaller, not from Vlad:
- Stage 3 keeps a stale texture bound in 257 cutscene batches (`805D1280`); harmless while the shader-stage
  program names only stages 0-1.
- The tutorial's state, should it stall again: flags `0x3B8598`, step `0x3B859C`
  (`docs/research/tutorial-task-completion.md`).

**Other open items.**
- The **D3D11 debug layer** ended at least two debug runs during the Story load with exception 0x87D
  (no log line; WER events 2026-10-01 12:38, 12:58). Patch 0091 prints its messages as `[D3D11-DEBUG]` and
  continues; grep for that after any silent exit. Not seen again yet.
- The **intro-movie hang** at start-up is still there: 1 of ~12 scripted runs on 2026-09-30
  (`run-20260930-222724`, stopped after `Game.StartMainMenu`), 2 more on 2026-10-01. One was sampled
  (`run-20261001-110621`): the main thread spins in `sub_0021EC50` <- `sub_0021EF60` <- `sub_00218F80` <-
  `sub_00219AA0`, the title's Direct3D, with a second thread in `sub_00223760`. Not analysed further.
- **Release build** (`scripts/build.ps1 -Preset win-x64-release`): 60 fps in fights but crashed in the
  walker before 0083; not re-tested since. Re-test, then M4e's row in §0 can go to ✅.
- Face culling: the title never enables it (the dump's `cull 0` on every batch, menus to fights), so the
  GPU path draws everything two-sided, as the console does here. A cull implementation was written and
  removed unverified (§6 2026-09-30 21:55).
- `tools/recomp` pytest: 2 failures in `test_icall_feedback` predate this work (seed alignment tests).
- Two pads, three fights with stable private bytes, the rare `sub_001A3310` crash at a fight's start, the
  loading-bar glitch, flicker on hits, a rare boot with no sound: unchanged from the previous hand-off.

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:8:8.4,a:14:14.3` holds each button over the given span
of seconds (names: up down left right start back ls rs a b x y black white lt rt). An `@anchor` entry puts
the entries after it on the clock of that anchor and ends the ones before it; `RECOMP_TRANS_SHOT_SECS`
takes the same tokens (at most 16 captures).

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript; transitions are in `screens/feflow.xml`.

**Known loose ends in the GPU model.** Modelled: depth, stencil, blend, alpha test, combiners, four texture
stages, palettes, address modes, the surface clip. Not modelled: polygon offset (the title enables it with
zero factor and bias), fog, float depth, texture-shader modes beyond plain 2D/3D/cube, render targets
sampled as textures (everything is drawn into one back buffer), the G8B8/R8B8 formats' channel mapping.

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For functions reached
only through data, `scripts/gap-seeds.py` finds them in bulk. For any stall, `scripts/native-stacks.py`
gives every thread's host call stack with names; `scripts/sample-threads.py` gives guest IPs.


### State as of 2026-09-27 10:45, as amended to 2026-09-29 (superseded 2026-09-30 22:50)

**Where it stands.** M3, M4a and M4b are met; M4c is most of the way. Battle -> One on One -> join (P1, no
user ID) -> fighter and CPU select -> venue -> a round that runs and draws with correct colours: arena,
crowd, both fighters, weapons, the CPU fighting, our pad's hits landing and scoring
(`run-20260926-130455`, `131326`). Still missing for M4c: a KO and the return to the menu -- six minutes of
button mashing traded evenly with the CPU, then the walker gave out (below). The save area holds one
profile, "AAAAAB" (`$DEFJAM_DATA\save\UserData\45410049\0F3C0F3C0F3D`). Since patch 0064 the pad is
polled every 8 ms (it was reached in bursts three times a second), so presses arrive one by one and the
in-fight hint popups close with A.

**Driving it unattended.** `RECOMP_SCRIPT_ANCHOR=feflow.xml#2` and
`RECOMP_PAD_SCRIPT=$(python scripts/pad-chain.py match)` reaches `Game.StartGame()` about 90 s after the
title: each stage waits for its screen by a substring of a `[FUNCCALL]` line (every ActionScript `FuncCall`
the front end makes is logged). Append `,@game.startgame(,<presses>` to fight (X/Y/A/B attack, right to
close in); keep the whole script under 4 KB. Captures: `RECOMP_TRANS_SHOT_SECS=@game.startgame(,30,60`
(RGB is right as of 13:00; captures before that had red and blue swapped).

**Start here: M4d.** M4c is met (§6 2026-09-28 18:15): a match plays to a KO and returns to "Choose Match
Type". M4d's checklist (`docs/02-test-plan.md`) still needs, most useful first: **sound** -- it plays since 0068-0070 (§6 2026-09-28 22:40); have Vlad listen, then the DSPs (GP
effects are bypassed, the EP too) and anything the title reads back from them; the **pace** -- fixed
(§6 2026-09-29 00:20: PTIMER's count ran away and the frame alarm fired on every tick); have Vlad confirm; **two pads**; **three fights** with
stable private bytes; and the rarer faults -- a crash at a fight's start in `sub_001A3310` (§6 15:45) and
the intro-movie stall. A KO for testing: `FIGHT="right:8:1500:4:1.2,x:10:1500:0.4:0.1,y:10.2:1500:0.4:0.1,
a:600:1500:3:0.2"` with `SECS=2400` (the CPU wins in 13-25 minutes; A then walks the results to the menu).

**Other open items, most useful first.**
- From Vlad's playthroughs (§6 2026-09-27 19:45 on): speed (0074), anti-aliasing (0072) and the crackle
  (0075) are addressed and need his check; the crowd silhouettes are fixed (0078); open: the blurry R3 icon
  in the Blazin' tutorial popup; then the loading-bar glitch, flicker on hits, and a
  rare boot with no sound at all (1 of 7 runs).
- Render targets: `0x82A90000` is a fight's anti-aliased 3D surface (2x wide), filtered into the front
  buffers; the D3D11 path draws everything into one back buffer (supersampled since 0072). An effect that
  samples a drawn surface as a texture still reads guest memory (`RECOMP_PB_SURFACE_TRACE=1` lists them;
  none in a plain round).
- The release build (`scripts/build.ps1 -Preset win-x64-release`, 80 s; `run.ps1 -Preset
  win-x64-release`) ran game time 1.43 times real time for the same reason as the debug build (0074);
  re-measure it.
- The executor's main cost is still the CPU vertex shader (`nv2a_vsh_run`), now decoded once (0073); a
  round presents 34-41 frames a second.
- Start-up still stalls now and then (legal screen, intro movie): 0 of 8 after patch 0062, but the next
  run (`run-20260926-155142`, with `RECOMP_WATCH_EXEC` on) stopped in the EA movie with no release ever run.
  Watched runs (DR-register watchpoints) stalled at start-up three times today; watch after the title if
  you can.

**Known loose end in the GPU model.** Depth, texture-stage enable and palettes are now modelled (patches
0035–0037); register combiners are not (every stage modulates texture by diffuse), nor is stencil, nor float
depth. `RECOMP_PB_BATCH_DUMP` prints each batch's render state and depth range.

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:8:8.4,a:14:14.3` holds each button over the given span
of seconds (names: up down left right start back ls rs a b x y black white lt rt). The "popups ignore input
for 5–15 s" seen before patch 0064 was probably the pad being polled three times a second; repeating A every
4 s through them still does no harm. An `@file#N` entry (patch 0045) puts the entries after it on the
clock of that file's Nth open and ends the ones before it; `RECOMP_TRANS_SHOT_SECS` takes the same tokens.
`main.mus#1` is the main menu appearing.

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript (`intMain/mainMenu.big` is the menu); transitions are in
`screens/feflow.xml`. `RECOMP_WATCH_EXEC_FLOATS` reads a clip's matrix at APT's setter or renderer.

**Known open items.**
- `XInputGetState` crash (`sub_0027E075+0x749`, reading `0xFFFF0003`) about 1 run in 13 at start-up,
  the race patch 0032 was meant to close; seen on the committed baseline too. Scripted
  runs showed the same ("the title ignores the first START now and then", popups that "ignore input").
  Suspects: the report-on-change model in `usb/ohci.c` (a press and its release are one report each; if the
  driver's first transfer after a change is consumed by something else, e.g. the controller-binding logic
  that picks which port is "the" player, the game sees the press late or not at all), or edge detection in
  the title that needs a released state it never saw. Check with `[PAD] script:` times against the
  `[OHCI0] periodic` report numbers, and `RECOMP_WATCH_EXEC` on `XInputGetState` (`sub_0027E075`).
- **Green flashes on the main menu** (Vlad; the purple went with patch 0037, which drew the colour-masked magenta mask quads depth-only). Likely the walker: skipped or misparsed commands
  would draw the colour-masked magenta quads with colour on, or leave stale state. Re-check after the walker.
- Start-up stalls at the loading screen in roughly 1 run in 7–15 (never opens `eagames.mad`), not investigated.
- Lifter: `rol`/`ror` do not set CF; `_CIfmod(-0, π)` returns +0 (sign lost); neither is known to matter yet.
- The APU interrupt line is still not delivered (backlog 6c).
- `$DEFJAM_DATA\save.fresh-20260923-2235` is a throwaway save area and can be deleted.

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For functions reached
only through data, `scripts/gap-seeds.py` finds them in bulk. For any stall, `scripts/native-stacks.py`
gives every thread's host call stack with names; `scripts/sample-threads.py` gives guest IPs.


### State as of 2026-09-26 13:40 (read this first; earlier hand-offs are in `docs/worklog/2026-09-handoffs.md`)

**Where it stands.** M3, M4a and M4b are met; M4c is most of the way. Battle -> One on One -> join (P1, no
user ID) -> fighter and CPU select -> venue -> a round that runs and draws with correct colours: arena,
crowd, both fighters, weapons, the CPU fighting, our pad's hits landing and scoring
(`run-20260926-130455`, `131326`). Still missing for M4c: a KO and the return to the menu -- six minutes of
button mashing traded evenly with the CPU, then the walker gave out (below). The save area holds one
profile, "AAAAAB" (`$DEFJAM_DATA\save\UserData\45410049\0F3C0F3C0F3D`).

**Driving it unattended.** `RECOMP_SCRIPT_ANCHOR=feflow.xml#2` and
`RECOMP_PAD_SCRIPT=$(python scripts/pad-chain.py match)` reaches `Game.StartGame()` about 90 s after the
title: each stage waits for its screen by a substring of a `[FUNCCALL]` line (every ActionScript `FuncCall`
the front end makes is logged). Append `,@game.startgame(,<presses>` to fight (X/Y/A/B attack, right to
close in); keep the whole script under 4 KB. Captures: `RECOMP_TRANS_SHOT_SECS=@game.startgame(,30,60`
(RGB is right as of 13:00; captures before that had red and blue swapped).

**Start here: finish M4c -- a KO and the return to the menu.** Long fights hold up (§6 15:35) and rapid
attacks win (§6 16:00: 9,250 to 1,500 in 90 s), but an in-fight hint popup ("(A) Continue") never closes
under our A presses. Find how that popup reads input -- the fight has no `[FUNCCALL]` traffic; watch
`sub_00142640` (the key-event injector) and XInputGetState callers while it is up -- or keep the fighters
away from the crowd. Then watch what follows the round (a rematch screen, `battle/rematch.swf`, then the
menu). Fight input: `,@game.startgame(,right:8:1200:4:1.2,x:10:1200:0.8:0.15,...` (`name:from:to:period:hold`).
The remaining overruns (3 a long fight) all follow the executor's own releases, likely the 20 ms stall
release; the skips (60) are next after that.

**Other open items, most useful first.**
- Render targets: effects that composite through the `0x82A90000` surface draw white or black; the D3D11
  path draws every surface into one back buffer (`RECOMP_PB_SURFACE_TRACE=1` lists them).
- The release build (`scripts/build.ps1 -Preset win-x64-release`, 80 s; `run.ps1 -Preset
  win-x64-release`) runs game time 1.43 times real time; its frame timer (object `0x27`, `0x802469A0`)
  against the PTIMER alarms (`RECOMP_PTIMER_TRACE=1`) is the place to look. Debug runs near real time.
- The executor's main cost is now the CPU vertex shader (`nv2a_vsh_run`); a round presents 15-30 frames a
  second.
- Start-up still stalls now and then (legal screen, intro movie): 0 of 8 after patch 0062, but the next
  run (`run-20260926-155142`, with `RECOMP_WATCH_EXEC` on) stopped in the EA movie with no release ever run.
  Watched runs (DR-register watchpoints) stalled at start-up three times today; watch after the title if
  you can.

**Known loose end in the GPU model.** Depth, texture-stage enable and palettes are now modelled (patches
0035–0037); register combiners are not (every stage modulates texture by diffuse), nor is stencil, nor float
depth. `RECOMP_PB_BATCH_DUMP` prints each batch's render state and depth range.

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:8:8.4,a:14:14.3` holds each button over the given span
of seconds (names: up down left right start back ls rs a b x y black white lt rt); the popups ignore input for
5–15 s, so repeat A every 4 s through them. An `@file#N` entry (patch 0045) puts the entries after it on the
clock of that file's Nth open and ends the ones before it; `RECOMP_TRANS_SHOT_SECS` takes the same tokens.
`main.mus#1` is the main menu appearing.

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript (`intMain/mainMenu.big` is the menu); transitions are in
`screens/feflow.xml`. `RECOMP_WATCH_EXEC_FLOATS` reads a clip's matrix at APT's setter or renderer.

**Known open items.**
- `XInputGetState` crash (`sub_0027E075+0x749`, reading `0xFFFF0003`) about 1 run in 13 at start-up,
  the race patch 0032 was meant to close; seen on the committed baseline too. Scripted
  runs showed the same ("the title ignores the first START now and then", popups that "ignore input").
  Suspects: the report-on-change model in `usb/ohci.c` (a press and its release are one report each; if the
  driver's first transfer after a change is consumed by something else, e.g. the controller-binding logic
  that picks which port is "the" player, the game sees the press late or not at all), or edge detection in
  the title that needs a released state it never saw. Check with `[PAD] script:` times against the
  `[OHCI0] periodic` report numbers, and `RECOMP_WATCH_EXEC` on `XInputGetState` (`sub_0027E075`).
- **Green flashes on the main menu** (Vlad; the purple went with patch 0037, which drew the colour-masked magenta mask quads depth-only). Likely the walker: skipped or misparsed commands
  would draw the colour-masked magenta quads with colour on, or leave stale state. Re-check after the walker.
- Start-up stalls at the loading screen in roughly 1 run in 7–15 (never opens `eagames.mad`), not investigated.
- Lifter: `rol`/`ror` do not set CF; `_CIfmod(-0, π)` returns +0 (sign lost); neither is known to matter yet.
- The APU interrupt line is still not delivered (backlog 6c).
- `$DEFJAM_DATA\save.fresh-20260923-2235` is a throwaway save area and can be deleted.

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For functions reached
only through data, `scripts/gap-seeds.py` finds them in bulk. For any stall, `scripts/native-stacks.py`
gives every thread's host call stack with names; `scripts/sample-threads.py` gives guest IPs.

### State as of 2026-09-26 07:00 (read this first; earlier hand-offs are in `docs/worklog/2026-09-handoffs.md`)

**Where it stands.** M3, M4a and M4b are met. Battle -> One on One -> the P1-P4 join screen (P1, no user
ID) -> fighter and CPU select -> venue -> the match loads and starts: arena, crowd, both fighters, health
bars, clock, "FIGHT!" (`run-20260926-060124`). Then it crashes (below). What got it there: the pad on game
port 1 (D39), APU DSP memory as plain memory (0048), and the GPU interrupt preempting the title (D40, 0049),
which also fixed the legal-screen start-up stall. The save area holds one profile, "AAAAAB"
(`$DEFJAM_DATA\save\UserData\45410049\0F3C0F3C0F3D`).

**Driving a match unattended.** `RECOMP_SCRIPT_ANCHOR=feflow.xml#2` and
`RECOMP_PAD_SCRIPT=$(python scripts/pad-chain.py match)`: each stage waits for the screen it is for, by a
substring of a `[FUNCCALL]` line (every ActionScript `FuncCall` the front end makes is logged, e.g.
`Control.GetScreenInfo(battle/chsVenue.swf)`, `Game.StartGame()`). Captures take the same anchors:
`RECOMP_TRANS_SHOT_SECS=@game.startgame(,5,15,25`. `Game.StartGame()` comes about 90 s after the title.

**Start here (M4c): play the round.** The round runs and draws (`run-20260926-103431`; §6 10:50). What
M4c still needs (docs/02-test-plan.md): our fighter answering the pad -- extend the chain past
`@game.startgame(` with presses (the fight's controls: X/Y/A/B punches and kicks, the d-pad to move) and
watch the opponent's health bar -- and a KO that returns to the menu. Our fighter does answer the pad
(1,000 points in `run-20260926-105417`, chain: right every 4 s, X/Y/A/B every 0.75 s after
`@game.startgame(`); the round runs near real time since patch 0058. Defects: effects that composite through the
`0x82A90000` surface draw white or black (render targets are not modelled -- the D3D11 path draws every
surface into one back buffer; `RECOMP_PB_SURFACE_TRACE=1` lists them); the CPU vertex shader is now the
executor's main cost; game time runs 1.43 times real time in the release build (§6 12:05: its frame timer,
object `0x27` at `0x802469A0`, against the PTIMER alarms it programs). `scripts/build.ps1 -Preset
win-x64-release` builds an optimised exe in about 80 s; `run.ps1 -Preset win-x64-release` runs it. The walker still skips a few hundred times a match (prefetch model, D40 gate on).

### State as of 2026-09-25 15:00 (read this first; earlier hand-offs are in `docs/worklog/2026-09-handoffs.md`)

**Where it stands.** M3 and M4a are done. The front end draws and navigates: title, both memory-card
popups, main menu, Battle's match-type screen, the user-ID screen with its keyboard and profile panel. The
save area now holds one profile, "AAAAAB" (`$DEFJAM_DATA\save\UserData\45410049\0F3C0F3C0F3D`); delete
that folder to get the new-profile flow back. Drive runs with the anchored script in
`tests/golden/README.md`: `RECOMP_SCRIPT_ANCHOR=feflow.xml#2`, times in seconds after the title loads,
captures with `RECOMP_TRANS_SHOT_SECS`.

**Start here (M4c): the crash just after "FIGHT!".** `sub_001B54D0` is a fighter state update: its
argument (`[esp+0x1E0]` inside, `eax`) is the object and it dispatches on `[eax+0x30]` through a table of 90
handlers on its stack; it is called with `0x041A1852` -- odd, past 64 MB, so it aliases code -- and faults
on the index. Same address in every run. Find the caller and where that pointer comes from:
`RECOMP_WATCH_EXEC=0x001B54D0` with `RECOMP_WATCH_EXEC_STACK=4` (arg and return address), then
`scripts/callers.py`. Then the 3D going black a few seconds into the round (the walker: `[PB]` skip lines).
The chain: the title's `start:14,start:17` and A every
3 s, then `@getscreeninfo(intmain/mainmenu` right 5, A 8+4n; `@getscreeninfo(battle/cmtype` A 5+4n;
`@setmatchtype(` A 5+4n; `@getscreeninfo(options/battleid` START 6+4n; `@controllerbind(0` A 5+4n;
`@setbmcurrentuserindex(` A 5+5n (six); `@controllersetup(0,0` right 4, A 6, right 10, A 12+4n;
`@controllersetup(1,` A 4+4n (each stage's entries stop when the next anchor fires; `[FUNCCALL]` lines name
each screen).

### State as of 2026-09-25 12:30 (superseded 2026-09-25 15:00)

**Where it stands.** M3 is done (D37). Every run plays the legal screen, the intros and the title; START
then A reaches the main menu, and the scripted A presses after it pick Story, which sends a new profile to
`options/userID`, the name-entry screen. Those screens now draw with the right layout, textures and text: brick background, panels, the
keyboard grid, the header, the A/B legends, and the autosave-warning popup. Press like this, so A lands after the
popup: `RECOMP_PAD_SCRIPT` = START every 20 s from 110 s, A 5 s and 10 s after each, over a 240 s run
(the frame counts vary; frames 4,400–5,800 are on these screens).

**Start here: the main-menu golden, then navigation (M4a).** The title, main menu (Story, Battle, Unlock
Rewards, Options, Beat Box, Extras, High Scores, Credits, and the music ticker), the autosave popup and the
name-entry keyboard all draw with text, and typed letters appear (patches 0034–0036). Left:
1. Done: menu titles and the autosave popup (patch 0037). Check the main menu's own header once.
2. A main-menu golden: capture with `RECOMP_TRANS_SHOT_SECS` a few seconds after the first A on the menu
   (the script below reaches it at about 190–220 s; the timing varies with how soon the title appears).
3. Navigation: d-pad over the menu tiles, A into a sub-menu, B back; each checked with a timed capture.
The pad script with presses every 20 s from 110 s to 290 s, and captures every 10 s, covers all of it in
one 300 s run.

**Known loose end in the GPU model.** The walker still loses its place a few times a run (`[PB] run from ...
skipping to PUT`, with the transfers, runs and headers before it): D3D rewrites commands after they were
kicked, and PUT moves backwards. The catch-up keeps that from hanging the title, but commands in the skipped
stretch are not drawn. `RECOMP_FENCE_TRACE=1` prints the fence every two seconds; `RECOMP_PB_DUMP_SKIP=1`
dumps the words at a skip.

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:110:110.4,a:115:115.4` holds each button over the given
span of seconds since process start (names: up down left right start back ls rs a b x y black white lt rt).

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript (`intMain/mainMenu.big` is the menu); transitions are in
`screens/feflow.xml`. `RECOMP_WATCH_EXEC_FLOATS` reads a clip's matrix at APT's setter or renderer.

**Known open items.**
- Lifter: `rol`/`ror` do not set CF; `_CIfmod(-0, π)` returns +0 (sign lost); neither is known to matter yet.
- The APU interrupt line is still not delivered (backlog 6c).
- `$DEFJAM_DATA\save.fresh-20260923-2235` is a throwaway save area and can be deleted.

### State as of 2026-09-24 22:50 (superseded 2026-09-25 12:30)

**Where it stands.** Every run plays the legal screen, the three intro movies and the title screen. START
(then A for the invisible memory-card popup) reaches the main menu: the menu music plays and nothing
crashes (3 of 3). The GPU model is now in step with Direct3D: the executor stops at software methods until
D3D's handler has finished (FIFO access, not the interrupt bit), runs push-buffer subroutines, and completes
fences as it passes their semaphore releases (patches 0027, 0028). Press like this, so A lands after the
popup: `RECOMP_PAD_SCRIPT` = START every 20 s from 110 s, A 5 s and 10 s after each, over a 250 s run.

**Start here: draw the screens after the title (M3's last gate, M4a).** After START+A the front end
runs `memorycard/autoSaveMessage`, `intMain/mainMenu` and `options/userID` (name entry, because there is no
profile yet) — the flow works; the drawing does not. Every sprite after the title gets a rotated,
oversized 2x3 transform in vertex constants `c0`/`c1` (e.g. `c0=(-0.00275, -0.00404, 0, -112.3)`), where
the title's are pure scales (`c0=(0.000244, 0, 0, 3)`), although the movies place those objects at identity
scale and no script rotates them (§6 2026-09-25 08:00 lists what is ruled out). So the C that composes a
sprite's world matrix, or a stage/view matrix it multiplies in, goes wrong once sprites sit inside offset
clips. The upload is `sub_00119910` (register +0x60, D3D's `sub_0021B690`/`sub_0021B740`); its callers are
the APT renderer (`sub_0010F1E0`, `sub_00115CB0`, `sub_00117F30`..`sub_00118CE0`). Measure with
`RECOMP_PB_BATCH_DUMP=<frames>` (each batch's extents and its vertex-program trace, `c0`/`c1` included).

**Known loose end in the GPU model.** The walker still loses its place a few times a run (`[PB] run from ...
skipping to PUT`, with the transfers, runs and headers before it): D3D rewrites commands after they were
kicked, and PUT moves backwards. The catch-up keeps that from hanging the title, but commands in the skipped
stretch are not drawn. `RECOMP_FENCE_TRACE=1` prints the fence every two seconds; `RECOMP_PB_DUMP_SKIP=1`
dumps the words at a skip.

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:110:110.4,a:115:115.4` holds each button over the given
span of seconds since process start (names: up down left right start back ls rs a b x y black white lt rt).

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript (`intMain/mainMenu.big` is the menu); transitions are in
`screens/feflow.xml`.

**Known open items.**
- One run in about fifteen crashed in the USB driver at start-up (`sub_0027E075+0x749`, reading
  `0xFFFF0003`), `run-20260924-211118`. Not yet looked at.
- The APU interrupt line is still not delivered (backlog 6c).
- `$DEFJAM_DATA\save.fresh-20260923-2235` is a throwaway save area and can be deleted.

### State as of 2026-09-24 15:00 (superseded 2026-09-24 22:50)

**Where it stands.** Every run plays the legal screen, the three intro movies and the title screen. The
emulated controller works, and START now leaves the title: the title's memory-card check runs, its popup
takes A, the main-menu music starts and the screen changes (§6 13:10). Give a run 50 s or more to judge
start-up; the title appears at about 100–130 s. Press like this, so A lands after the popup whatever the
timing: `RECOMP_PAD_SCRIPT` = START every 20 s from 110 s, A 5 s and 10 s after each.

**Start here: the crash a few seconds after START (Direct3D's DPC), which is the fence model.** Two of
three runs that reach the menu crash in `sub_0021F1A0`, D3D's push-buffer fixup, run from its DPC
(`sub_002239A0` -> `sub_00223760` -> `sub_002234F0`, cases 12 and 13). The software method's parameter
was ASCII: the executor read push-buffer memory the title had already rewritten. Since patch 0027 the
executor stops at software methods as the pusher does, but the fences (`fence_mirrors_tick` in
`xbox_memory_layout.c`) still set the fence to the submitted reference every tick, so D3D believes the GPU
has passed commands the executor has not run and reuses that space. Holding the fences until the executor
is level with PUT (`RECOMP_FENCE_AT_PUT=1`) is too coarse: the legal screen stopped in 2 of 4 runs. Next:
complete references one by one as the executor passes them. D3D writes each fence as an NV04 pattern
`SET_MONOCHROME_COLOR0` carrying `(push-buffer address << 5) | (reference & 0x1F) << 2` (see the comment
above `fence_mirrors_tick`); decode that in the executor, rebuild the full reference from the submitted
one, and write the fence and `PATT_COLOR0` then. Test with the menu batch (START every 20 s from 110 s, A
at +5 s and +10 s) and the 60 s start-up batch, which must stay at 0 stuck.

**Then: draw the menu.** The screen after the title is 3D-heavy and comes out as white and green blocks;
`[GPU] ... batches skipped as not screen-space` is the counter to watch. Positions far off screen and w
have been an open item since the title.

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:110:110.4,a:115:115.4` holds each button over the given
span of seconds since process start (names: up down left right start back ls rs a b x y black white lt rt).
A host XInput pad drives the same device. `[OHCI0] periodic:` lines log every non-idle report.

**Reading the front end.** `python scripts/apt-dump.py screens/screens.viv screens/intMain/prestart.big
--actions` disassembles a screen's ActionScript; screen names and transitions are in `screens/feflow.xml`.
`MEM32(0x345220)` is the boot flow's pending-screen record and stays `intMain/preStart` after START, so it
does not track the menu. `[KTRAIL]` and `[DIR]` lines show what the title asks the kernel after an open.

**Known open items.**
- 1 in ~15 runs still stalls at the movie start after pinning (the streamer race, rare, as on hardware);
  one of today's runs stalled at the legal screen (125 reads after `feflow.xml`).
- The APU interrupt line is still not delivered (backlog 6c).
- `$DEFJAM_DATA\save.fresh-20260923-2235` is a throwaway save area from a test and can be deleted.
- A start-up race: about one run in ten crashed in `nv2a_ack_thread` reading the trapped PFB page before any
  guest code ran (the runtime's own thread).
- `UDATA` still routes to the game directory (patch 0006, for `TitleMeta.xbx`); a title that creates a save
  there would write into the dump. Nothing has written there yet.

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For functions reached
only through data, `scripts/gap-seeds.py` finds them in bulk. For any stall, `scripts/native-stacks.py`
gives every thread's host call stack with names.

### State as of 2026-09-24 11:20 (superseded 2026-09-24 13:50)

**Where it stands.** Every run plays the legal screen, `eagames`, `thx` and `intro` with sound, then the
title screen, which matches `tests/golden/m3-title-screen.json`. The emulated controller works end to end:
a scripted START skips the intro movie and reaches the title (§6 10:50, 11:10). Give a run 50 s or more
to judge start-up; the title appears at about 100–130 s.

**Start here: what the title waits for after START (the last M3 gate).** On the title (`intMain/preStart`,
pending-screen record `MEM32(0x345220)`, loaded), one START press makes it enumerate the save area
`\Device\Harddisk0\partition1\UDATA\45410049\` (seven directory queries, `kernel_file.c` near line 637),
and then nothing changes: no new screen is requested, no file opened, later presses ignored. Suspects, in
order:
1. **The save enumeration's answer.** The title created `UDATA\45410049` with `TitleMeta.xbx` at start-up,
   so the directory exists and holds no saves. Check what `NtQueryDirectoryFile` returns to each of the
   seven calls (status, and `STATUS_NO_MORE_FILES` at the end) and whether the title's XAPI wrapper
   (`XFindFirstSaveGame`-style) gets `ERROR_NO_MORE_FILES`. A wrong status here is the most likely stall.
2. **A dialog drawn off screen or not at all** ("no profile found"): capture frames just after the press
   (`RECOMP_TRANS_SHOT_FRAME` in steps of 20) and look for any change.
3. **A missing function on the new path** that fails quietly: grep the run for `[ICALL]` lines after the
   press, and run `scripts/gap-seeds.py` again (115 small candidates remain unseeded, D32).
The record can be read live with a small reader on `scripts/guest-regs.py` (name at `+0`, `+0x40` loaded,
`+0x41` in progress); `scripts/icall-window.py` shows the last indirect-call targets.

**How to press buttons.** `RECOMP_PAD_SCRIPT=start:110:110.4,a:120:120.4` holds each button over the given
span of seconds since process start (names: up down left right start back ls rs a b x y black white lt rt).
A host XInput pad drives the same device. `[OHCI0] periodic:` lines log every non-idle report.

**Rendering left for later:** many 3D batches send positions far off screen and need a look at w and
clipping; the copyright panel's colour; one glitched frame (green and yellow blocks) between the intro and
the title in one run.

**Known open items.**
- 1 in ~15 runs still stalls at the movie start after pinning (the streamer race, rare, as on hardware).
- The APU interrupt line is still not delivered (backlog 6c). Nothing in this title needs it yet.
- `$DEFJAM_DATA\save.fresh-20260923-2235` is a throwaway save area from a test and can be deleted.
- A start-up race: about one run in ten crashed in `nv2a_ack_thread` reading the trapped PFB page before any
  guest code ran (the runtime's own thread).
- The fence model is still "the GPU finishes on submit" (the mirror in `xbox_memory_layout.c`).

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For functions reached
only through data, `scripts/gap-seeds.py` finds them in bulk. For any stall, `scripts/native-stacks.py`
gives every thread's host call stack with names.

### State as of 2026-09-23 23:30 (superseded 2026-09-24 11:20)

**Where it stands.** In a good run, the title shows a correctly laid-out legal screen, then plays `eagames`,
`thx` and `intro` with sound paced correctly and video rendered cleanly, then reloads its fonts and
`feflow.xml`. Patches 0016 (APU physical addresses), 0017 (movie textures), 0018 (guest clocks and one guest
CPU) and 0019 (vertex programs) got it there; §6 has the measurements.

**Start-up is reliable now (10 of 10 runs to the intro, 2026-09-24).** The legal-screen stops and the
early crawls are gone: level-triggered interrupts (0021), the pusher following jumps (0020) and buffered
logs (D31). To judge a run, give it 50 s or more; start-up time varies a lot, and a 35 s cut-off misreads
slow starts as stuck.

**Start here: input, so START reaches the main menu (the last M3 gate, and M4).** The title card renders
(§6 09:55). The pad enumerates (M4 row in §0) but no report reaches the title: the OHCI model walks only the
control list, and the pad's interrupt endpoint is on the periodic list (the HCCA's interrupt table). Next:
1. Walk the periodic list in `tools/xboxrecomp/src/usb/ohci.c`: every frame, follow the HCCA interrupt-table
   entry for the current frame number to its EDs and service their TDs like the control list's.
2. Feed the pad's 20-byte report from the host (XInput first; `src/usb/usb_gamepad.c` has the device) with
   START as button bit 4 of byte 2, and complete the TD with the report and `ConditionCode` 0.
3. Verify: hold START from frame ~4,500 (an env var such as `RECOMP_PAD_SCRIPT` that presses buttons at given
   frames keeps it automatic) and capture the frame after; the main menu should replace the title card.
To reach the title quickly: a 170 s run, `RECOMP_TRANS_SHOT_FRAME=5200`, then
`python scripts\frame-signature.py <bmp> --check tests\golden\m3-title-screen.json`.

**Rendering left for later:** blending is hard-coded in `pgraph_d3d11_draw_ready` (source-alpha over), so
the title's blend state is ignored; many 3D batches send positions far off screen and need a look at w and
clipping.

**Known open items.**
- 1 in ~15 runs still stalls at the movie start after pinning: the streamer race can still be hit if the
  reader is preempted between the two stores, as on hardware, just rarely.
- The APU interrupt line is still not delivered (backlog 6c). Nothing in this title needs it yet.
- `$DEFJAM_DATA\save.fresh-20260923-2235` is a throwaway save area from a test; Vlad's own is back in place and
  the fresh one can be deleted.
**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For stack or register
corruption, build `win-x64-abicheck` and read the `[ABI]` lines. Live guest memory is quickest to read
with a small script on `scripts/guest-regs.py` (see `scripts/mem-find.py`); `RECOMP_PEEK` prints at most
six lines. The in-process watchpoints change timing enough to hide the races above; prefer reading memory
from outside. For any stall, `scripts/native-stacks.py` gives every thread's host call stack with names.
**Open, not blocking.**
- **A start-up race:** one run in about ten crashed in `nv2a_ack_thread` reading the trapped PFB page
  (`0xFD100410`) before any guest code ran. The runtime's own thread, not the title's.
- **The fence model is still "the GPU finishes on submit"** (the mirror in `xbox_memory_layout.c`).
- **Input** (M4): the OHCI periodic list, unchanged.

### State as of 2026-09-23 20:30 (superseded 2026-09-23 23:30)

**The intro movies play through.** Legal screen, then `eagames.mad`, `thx.mad` and `intro.mad`, then the
front end reloads `FONTS.VIV` and `screens/feflow.xml`: that reload is the menu flow starting after the
attract sequence. 2,735 frames in 120 s, no crash, smoke S4, 7,616 reads after `feflow.xml`. The last
blocker was the APU model reading and writing low RAM where DirectSound had put its voices in the
contiguous window (patch 0016, §6 20:28).

**Start here: the vertex transform.** The movies render (patch 0017). Everything after them, and the
legal screen before them, is placed wrong, because the D3D11 path treats vertex positions as finished
pixel coordinates. The title sends stage coordinates instead (legal screen: x −2..553, y −2..381) and
relies on the NV2A's transform (fixed-function matrices or a vertex program, plus the viewport) to
map them onto 640x480. The result is text squeezed into the top-left, a magenta full-screen quad
after the intro, and the post-intro loading logo sampled at 0..0 (black). Next:
1. Find which transform the title programs. Run with `RECOMP_PB_UNHANDLED_ALL=1` and read the
   method table: `SET_TRANSFORM_EXECUTION_MODE` (`0x0294`/`0x0394`), the composite and model-view
   matrices (`0x0680`...), vertex-program loads (`0x0B00`, `0x0E00` constants) and the viewport
   (`0x0A20` offset, `0x0AF0` scale).
2. Apply it to the D3D11 path's vertices before `pgraph_d3d11_draw_ready`, in the executor where the
   positions are fetched (`nv2a_pb_exec.c`, the `ready[]` loop). Fixed-function is a matrix multiply
   plus the viewport. A vertex program needs an interpreter; xemu's `vsh` code is the reference.
3. Verify with `RECOMP_PB_BATCH_DUMP=150` (the legal screen) and a capture of the same frame. The
   positions should come out spread over 0..640 × 0..480.

**Audio notes for later.** DirectSound's own voices now play in the model (six are started: `0x40`-`0x43`
and the looping buffers `0xF8`-`0xFA`), so sound should reach XAudio2; nobody has listened yet. The
APU's interrupt line still goes nowhere. This title raised no notification in two minutes, so it does not
need one yet; the design is backlog item 6c.

**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For stack or register
corruption, build `win-x64-abicheck` and read the `[ABI]` lines; the CRT and SEH helpers
(`sub_002030FC`, `sub_00201400`, `sub_00203137`) legitimately move `esp` and can be ignored. Live
guest memory is quickest to read with a small script on `scripts/guest-regs.py` (see `scripts/mem-find.py`
for the pattern); `RECOMP_PEEK` prints at most six lines.
**Still open from earlier:** in 1 of 3 runs the PTIMER alarm stops after about 18 alarms (declined,
retried, then nothing); sample the timer thread with `scripts/sample-threads.py` when `[PTIMER]` lines
stop. The legal screen's layout is offset up and left.
**Open, not blocking.**
- **A start-up race:** one run in about ten crashed in `nv2a_ack_thread` reading the trapped PFB page
  (`0xFD100410`) before any guest code ran. The runtime's own thread, not the title's.
- **D3D issues hundreds of software methods a frame** with parameters like `0x5C280021`. All are
  delivered (queue 256, drained each tick). If this costs frame rate, look at what `sub_002234F0` does.
- **The fence model is still "the GPU finishes on submit"** (the mirror in `xbox_memory_layout.c`).
- **Input** (M4): the OHCI periodic list, unchanged.

### State as of 2026-09-23 15:40 (superseded 2026-09-23 20:30)

**The front end gets past the loading screen.** `intMain/legal1` is marked loaded (`[0x345220]+0x40`
reads `0x0101`: loaded and requested), 8 of 8 movies are fixed up and 3 finalise, and the title draws a
new screen: rows of text-like quads from a 1024x512 texture plus three 512x32 strips, not the loading
logo. 1,703 frames in 70 s, no crash, no stall. **The new screen is garbled:** its textures are format
`0x0B` (8-bit palettised, swizzled) and come out as noise, so the palette is not being applied.

Four runtime fixes got it here, each measured (§6, 13:00-15:40):
1. **`MmQueryStatistics` reports the console's memory** (patch 0011). It returned "half of 64 MB", the
   title sizes its main arena as that minus 14 MB, got 18 MB, and ran out while loading the front end.
   Now 56 MB available, a 42 MB arena, and no failed allocations.
2. **The DSP doorbell is derived, not hard-coded** (patch 0012, `src/main.c`). It is at GP scratch page 0
   + `0x810`, read from `GPSADDR`'s scatter-gather table. The old fixed `0x819E8810` went stale with
   the new heap and would have cleared a word inside the arena every audio frame.
3. **D3D's progress register** (patch 0013). `PGRAPH_PATT_COLOR0` (`0xFD400B10`) now says what the fence
   mirror says: `(DMA_GET << 5) | (reference & 0x1F) << 2`. D3D spins until the two agree
   (`sub_0021E8B0`).
4. **PGRAPH software methods** (patch 0013). A NOP with a parameter now raises PGRAPH's notify
   interrupt with the trapped method and data, delivered PGRAPH-only from the timer thread. D3D waits
   for push-buffer space on an event its handler sets (`sub_0021EC50` → `sub_00223760` →
   `sub_002234F0`).

**Start here: the intro movie (`movies/eagames.mad`) stalls on its stream.** See the 17:52 entry: video
queue empty, audio queue full, reader polling. Measure first: the streamer thread's wait (is it
blocked on ring space?) and the audio consumer's drain rate (`sub_0011F4A0`, `RECOMP_WATCH_EXEC`
totals over time). If it is audio pacing, the fix is in the audio path (DirectSound / APU buffer
position advancing and releasing), not the movie. Two cheaper alternatives if that turns out deep,
both Vlad's call: an opt-in "skip intro movies" patch in `src/patches/` (common in ports, and M3 is
the title screen, not the movies), or pressing a button to skip, which needs M4 (input) first.
**How to find the next missing function fast:** grep a run for `[ICALL] Failed to resolve`, add the
address to `config/seed_functions.json`, then `scripts/analyze.ps1`, lift, build. For stack or register
corruption, build `win-x64-abicheck` and read the `[ABI]` lines; the CRT and SEH helpers
(`sub_002030FC`, `sub_00201400`, `sub_00203137`) legitimately move `esp` and can be ignored.
**Also open from this session:** in 1 of 3 runs the PTIMER alarm stops again after about 18 alarms
(declined, retried, then nothing), so the timer thread probably hangs inside a deferred routine. Sample
it with `scripts/sample-threads.py` when `[PTIMER]` lines stop. Then fix the legal screen's layout,
which is offset up and left.
**Open, not blocking.**
- **A start-up race:** one run in about ten crashed in `nv2a_ack_thread` reading the trapped PFB page
  (`0xFD100410`) before any guest code ran. The runtime's own thread, not the title's.
- **D3D issues hundreds of software methods a frame** with parameters like `0x5C280021`. All are now
  delivered (queue 256, drained each tick). If this costs frame rate, look at what `sub_002234F0` does
  with each parameter.
- **The fence model is still "the GPU finishes on submit"** (the mirror in `xbox_memory_layout.c`).
  Executing semaphore releases in order was tried and is inconsistent with it; see the comment there.
- **Input** (M4): the OHCI periodic list, unchanged.

### State as of 2026-09-23 13:00 (superseded 2026-09-23 15:40)

**M3 has a measured root cause, end to end.** The 08:00 block's framing ("ActionScript runs 144 times
and never asks") was wrong on one point: `sub_00155AD0` is a load-time pass, not the interpreter. The
real chain, each link measured (§6, 11:40–12:50):

```
arena 0 alloc for feloader's decompressed BIGF (587,520 B)   sub_00181D20 -> sub_001E9E70 -> NULL
  -> decompressed onto guest 0x00000000 (0x0..0x95C00)      sub_001E9040(src, dst=0)
  -> .apt/.const "pointers" are bare offsets 0x80/0x10100    sub_001810B0 -> sub_001E7160(container=0)
  -> movie+0x10 = 0x4A0, copied to state+0xC                 sub_00147660, sub_00161160
  -> frame period read from [0x4C4] (clobbered low memory)   sub_00144310, the fixed-timestep stepper
  -> accumulator never reaches it: the timeline never steps   pump sub_00148210 stops after the load burst
  -> no frame actions, no clip events, no screen ever loads
```
Movie 8 (`0x807F26B8`, 614,400 bytes) fails the same way.

**Start here: why arena 0 has no room for 587 KB.** It is 18 MB at `0x80003000` (registered by
`sub_001E9640`, called from `0x001EA215`), arenas 2 and 3 are carved out of it, and it had already served
a 1.98 MB block. Options, cheapest first:
1. **Find the game's own heap report.** The image has `"Largest Avail Memory = %d(0x%08x)"` (file offset
   `0x27BED9`; get the VA with `scripts/string-va.py`) and `"Out of Memory"` (`0x2428DC`). Find their users
   with `lift-audit`-style grep of the generated C, and trigger or watch that function.
2. **Account for arena 0.** Alloc is `sub_001E9AB0` (flags `0x500`, so `& 0x3F` = arena 0), free paths
   write the `FB` tag (`sub_001E9F10`, `sub_001E99E0`). 438 allocs / 281 frees in 30 s. A per-size
   histogram of live blocks at the failure (walk the `BO`/`FB` headers from `0x80003000`) says whether
   it is a leak (something our runtime never frees: a refcount, a callback that never fires) or real
   fragmentation.
3. **Prove causality cheaply** before fixing the cause: a manual override that grows arena 0 (the size
   `0x1200000` is an argument at the `0x001EA215` call site), or makes the two allocations succeed. If
   `feloader`'s timeline then advances and `intMain/legal1` finalises, the chain above is confirmed.
   Check first that the contiguous window has room above `0x81203000`.
The NULL-dereference writes should also stop being silent: consider a `RECOMP_GUARD_LOW` that traps
writes to `0x0..0x10000`. The thread block at `0x8000` sits inside the clobbered range.

**Also changed today.**
- Patch **0009** (D22): rep-compare flags, `loop*`, and SETcc/CMOVcc at a block boundary. Patch **0010**:
  `RECOMP_PEEK_CHAIN` follows `0x8xxxxxxx`. Both were generated against a pristine `6f55eaa` plus
  0001–0008 and apply cleanly. Patches 0005 and 0008 still carry CRLF noise.
- New tools: `scripts/lift-audit.py` (static count of bad lift shapes, `--max` gates; unit test),
  `scripts/apt-dump.py` (APT disassembler, read-only), `RECOMP_WATCH_EXEC_STACK=N` plus
  `scripts/guest-stack.py --log` (call chain at the instant of a breakpoint, even for a burst long over).
- Healthy-run numbers changed: expect about **1,100–1,200 frames in 50 s** (vblank-paced), not 5,000.
  The other §7 criteria stand.
- **Always set the four env vars** below; `run.ps1` and `boot-smoke.ps1` do not.


### State as of 2026-09-23 08:00 (superseded by the block above)

**The title is healthy.** About 5,000 frames in fifty seconds, no crash, main loop running, the front end alive
and all eight screens requested, read, decompressed and made ready. The controller enumerates. What does
not happen is that any screen draws: two texture uploads a run and one draw shape, both the loading
screen's.

**The one remaining blocker, measured end to end.**

```
state 1  queued          sub_00147430   8   one per screen
state 2  loading         sub_001480B0  43
state 3  data in memory  sub_00147660   8   <- all eight get their data
         readiness       sub_00147530   7
state 4  fixed up        sub_0015F950   7   <- seven relocated and ready
         finalised       sub_0017CA50   2   <- only two, and only these notify
```

Finalising is what makes a movie announce itself: the pump `sub_00148210` calls the handler at
`MEM32(0x3B1DFC)` (= `sub_00068D20`), which matches the finished movie's name against the record at
`MEM32(0x345220)` and sets that record's `+0x40`. Read live, the record is `"intMain/legal1.swf"` with
`+0x40 = 0` and `+0x41 = 1`, and the notification only ever arrives for `feloader` and `xHead`. That zero
flag is what the front end waits on for ever.

Finalising requires the movie to be the one currently **bound**: `sub_00147090` is a smart-pointer getter
returning `this->field_4`, and the pump asks whether that equals the movie in hand. Binding happens in
`sub_001470B0`, whose only caller is `sub_00148600` (the ActionScript SetVariable dispatcher). It runs
**three** times a run -- exactly the three variables the C side sets: `g_sLoadFile`, `g_bLoadRequest` and
`_level0`. So the two movies that finalise are the two the C code binds by name, and nothing else is ever
bound.

Every further binding must come from ActionScript inside the loader movie: `feloader` should read
`g_bLoadRequest` and `g_sLoadFile` and ask for `intMain/legal1`. `feloader` does finalise, so it is loaded
and ready. The interpreter runs -- `sub_00155AD0` (jump table `0x156094`, byte index table `0x1560B8`) is
entered **144** times. It runs and never asks.

**Start here.** Find the ActionScript variable *get* path -- the counterpart to `sub_00148600` -- and check
whether a script reading `g_bLoadRequest` sees `"1"`. The C side writes those variables through
`sub_001423F0` -> `sub_00148600` -> the registry; a get that does not find what a set stored is a
self-contained, checkable asymmetry and would explain everything above. If the get is fine, the other
reading is that the 144 dispatches belong to `xHead`'s script rather than `feloader`'s, which the movie
pointer at the dispatch would settle.

**Already ruled out, with the measurement that ruled it out. Do not redo these.**

| Theory | Why it is dead |
|---|---|
| A screen-name key mismatch (`intMain/legal1` vs `intMain/legal1.swf` vs `screens/intMain/legal1.big`) | The finalisation test is an identity check on a bound pointer, not a name lookup. The container stayed constant while the movies varied. |
| The same test being a consumed-against-expected byte count | Same measurement: `ebx` is a per-movie object at a 0x30 stride. |
| Loading, decompression or parsing failing | All eight screens are read in full (125 reads, ~955 KB), RefPack works (six `BIGF` archives live in memory), all eight reach state 3. |
| A size effect | `trans/empty2` is 141 bytes and fails; `feloader` is 191,325 and succeeds. |
| The front-end command queue at `0x2EB73C` | Feeding it synthetic commands (`RECOMP_POST_CMD`) dispatches them correctly and draws nothing. Not the display trigger. |
| M3 being gated on M4 | The controller now enumerates fully and the front end is unchanged. |
| `0x3C9138` being an allocator arena base | It is OR'd into values in a dozen functions -- a flags word. Zero is correct. |

**Two bugs still open, both real but neither blocking the menu.**

1. *A sub-allocator returns code-segment pointers.* `sub_001E9AB0` (free-list, 64 size bins, block tags
   `FB`/`SB`/`BO`/`BM`), reached via `sub_001E9E70`, occasionally returns an address like `0x00011000` or
   `0x00077158`, and `sub_001E9270` -- a compressed-string unpacker, not a CRT routine -- writes there.
   Most calls are fine (26 sampled, all valid `0x8xxxxxxx`). The damage is now contained: D21 makes jump
   tables immune and the thread block was moved to `0x8000`, but it still scribbles on whatever else it
   lands on.
2. *Input does not flow.* The pad enumerates but the OHCI model walks only the control list, and the pad's
   interrupt endpoint lives on the periodic list. That is M4's remaining work.

### State as of 2026-09-21 11:30 (superseded by the block above; kept for the address tables)

Two milestones are open and they may not be independent. **Input is not ruled out as the thing the front
end is waiting for.** An earlier entry in this log said it was, on the strength of an ISR claiming an
interrupt; that is not the same as the title seeing a pad, and XAPI device enumeration is still
deliberately unimplemented. So M4 may be the critical path to the menu, not a parallel track. The test
that would settle it needs a pad that enumerates -- which is M4's exit criterion.

**M4 -- the driver rejects the device after eight bytes.** Enumeration now runs: device arrives, port is
reset, `GET_DESCRIPTOR(DEVICE)` wLength 8 completes with all three TDs at CC=0, WritebackDoneHead is
raised, the ISR claims it and the DPC runs. Then the driver disables the port and starts over, six times,
before abandoning it. The decision point is named:

| Guest address | What it does |
|---|---|
| `sub_002837AE + 0x2F1` | writes `ClearPortEnable` -- **this is the give-up**, start here |
| `sub_00283761 + 0x41C` | writes `SetPortReset` |
| `sub_002837F6 + 0x1274` | clears the port change bits |
| `sub_00284476` | the USB deferred routine (**not** `sub_002239A0`, which is the GPU's) |
| `sub_00284CDA` | builds transfer descriptors |

Next step: read `sub_002837AE` backwards from `+0x2F1` to find the condition that reaches that write. A
sub-agent swept `sub_00284476`'s call graph for a comparison against 8, 0x20, 32 or 64 and found none, so
the check is probably in the XID/XAPI layer above the host-controller driver, not in it.

Already measured and correct, so do not re-examine: TD condition codes (the driver initialises word 0 with
CC `0xE` NotAccessed and the model overwrites it with 0, which is what hardware does); the set-bits and
clear-bits semantics of `HcInterruptEnable`/`HcInterruptDisable`; the HCCA done-head write address (`wr32`
converts physical to guest itself); the TD walker's write-back of `HeadP`; and the ISR-to-DPC path (the USB
DPC is queued once per interrupt, ten times a run).

**M3 -- the front end never asks for an asset.** `screens/feflow.xml` is the last file the title ever
touches, verified two independent ways: the uncapped `[READ]` log holds 299 lines and the kernel's own
ordinal counter reports `NtReadFile` x299, with the last read at line 1,325 of a 4,732-line log. The read
is complete and correct (26,988 bytes on disc, 26,988 read). A write watchpoint on the front-end command
pointer `0x002EB73C` returns **zero hits** in a full run.

The front end is busy, not idle -- `NtSetEvent` x7708, `NtReleaseMutant` x6307, 43,000 critical-section
round trips per run -- so a single never-signalled event is not the shape of this. It is a running system
doing everything except asking for assets.

Asset naming, taken from the dump rather than inferred: `screens.viv` is a BIG4 whose directory names
`screens/intMain/legal1.big`, `bootLoad.big`, `mainMenu.big`, `prestart.big` -- **`.big`, not `.swf`**. The
XBE holds both `%s/%s.big` and `%s.swf`, so each screen is a nested archive containing its SWF. The outer
`.big` would have to be seeked out of the already-open `screens.viv`; no seek or read ever happens. Note
`feflow.xml` says `intMain/preStart` while the archive says `intMain/prestart.big` -- a case difference
that FATX would forgive and a string compare might not. Untested, and cheap to test.

**A standing caution, earned three times today.** Every wrong turn this session came from taking a number
at face value without asking what address space or what budget it came from: a DPC counter capped globally
and read as "queued once"; a host code offset put into a brief as a guest address; a GPU routine read off
an adjacent log line and called the USB one. Two of those reached sub-agent briefs and sent them down dead
ends. Before a number goes into a brief or a conclusion, check whether the counter that produced it has a
cap, and which address space it belongs to.

### Where the title is now
It boots, initialises the kernel, Direct3D, the GPU fence and the display mode, loads all 33 data files off
the disc, initialises audio on the emulated APU, runs indefinitely without crashing or hanging — and
**renders its loading screen**, in a real window, through the push-buffer translator. Smoke stage **S4**.

M2 is met. The open question is M3: the title never advances past loading.

### Where it is now, and what to do next
**The frame clock works.** The title's pacing is the NV2A PTIMER alarm: it programs the rate, resets the
count, reads TIME and arms `ALARM_0` 16,838,770 ns ahead - 16.84 ms, one frame at 59.4 Hz - then enables
`INTR_EN_0`. Nothing raised that interrupt, so the simulation was never credited a frame and the title
rendered a loading screen for ever. `kernel_ptimer_tick()` (patch 0001) raises it, and it now fires at
**80 Hz**.

The subtle half was what happens after. `sub_002239A0`, the deferred routine the service routine queues,
re-reads `PMC_INTR_0` and branches on bit 12 (PGRAPH), bit 20 (PTIMER) and bit 24 (PCRTC). That summary
therefore has to survive from the service routine through to the deferred routine, and the runtime's
acknowledging loop was erasing it in between. The delivery now claims the register before setting a bit,
holds it across the routine *and* a `kernel_drain_dpcs()` called immediately after, and releases it when
both are done.

Since then: the frames-owed counter left zero, the top-level state machine moved from 1 to 2, three
functions the lifter had never seen were discovered and lifted (0 unresolved now), and the title opened
`screens/feflow.xml` - the front-end flow definition. 52 paths against the 46 it sat on for its whole life.

**It is still parked before the menu renders.** The screen shows the loading logo, now animating.

Where to take it, in order:
1. **One asset request never turns into a read, and the archive is never consulted.** The front end is Flash-driven and the loader is waiting
   for `intMain/legal1.swf` - the legal screen. The request record is at `0x8003FD80` (name in the first 64
   bytes, loaded byte at `+0x40`, requested byte at `+0x41`); requested is set, loaded never is, and a
   watchpoint confirms nothing writes it. The asset is present as `screens/intMain/legal1.big` at offset
   `0x00BC7658` of `screens/screens.viv`, whose directory the title reads and whose data it never touches.
   The kickoff is **not** the problem: `sub_00069F10` and `sub_0006BF90` both run to completion (see the
   work log for 2026-09-20 21:15 for the field values that prove it). Start instead at the notification
   path - `0x345240` holds `sub_00180FE0`, a one-byte `ret`, because `sub_00069D30` skips installing the
   table containing the real handler when that slot is already non-zero. A watchpoint on `0x345240` says
   who put the stub there. The work-log entries for 17:20 and 21:15 list everything already cleared.
2. **Watch for the next unresolved indirect call.** `[ICALL] Failed to resolve` fired 3,409 times before
   the last re-lift and cost a stall that looked like a deadlock. Grep every run for it; the fix is the
   four-script loop and it takes about ten minutes.
3. **Expect more interrupt-status work.** The PTIMER path is modelled properly now; PGRAPH (bit 12) and
   PCRTC (bit 24) still go through the older, racier path, and the deferred routine reads all three.
4. **The alarm is declined sometimes** (a few per thousand). Harmless at 80 Hz, but it is the same race in
   miniature and worth removing if the clock ever needs to be exact.
