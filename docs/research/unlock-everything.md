# Unlocking everything for playtests and regression runs

2026-10-15, branch `research/unlock-all-profile`. A dated record: the source is authoritative.
Everything below was read from the user's own USA dump (`default.xbe`, `gconfig.xml`) and
confirmed in live runs of the macOS build against a throw-away copy of the save area.

## Short answer

Yes. The retail game has no working unlock cheat, but it still contains the developers'
unlock-everything routine; nothing the player can press reaches it. The port can call it.
`RECOMP_UNLOCK_ALL=1` makes every fighter and venue available on **any** profile, a fresh one
included, so a regression run does not depend on what the save area holds.

| | Without | With `RECOMP_UNLOCK_ALL=1` |
|---|---|---|
| Unlock Rewards, Unlock Fighters | `UNLOCKED 20 / 74`, 15 points, locked silhouettes | `UNLOCKED 74 / 74`, "You've unlocked all the fighters" |
| Battle, Choose Venue map | about 4 venue pins | about 10 pins |
| Crashes, watchdogs, save-area restore | none, identical | none, identical |

With the switches off the build behaves as before: `regress.py --quick` passed 5 of 5 (unit tests,
the three golden frames, a 120 s fight). The runs above used the retail `gconfig.xml`
(`buildtype` 1) on a copy of the Mac profiles under a throw-away data root; the owner's own save
and data folders were not used.

It is runtime-only. In the flows tried (a played One on One, browsing Unlock Rewards, Story into
the crib) the game never wrote the unlocked state into a profile file, so it leaves no trace in a
save and cannot be carried in one. See "Why not a save".

## What is built in

All addresses are guest virtual addresses in the USA dump.

### 1. The Extras cheat-code screen (retail codes)

`SubmitCheatCode` is a script method of the Extras object, handler `sub_00049D00`. It asks the
classifier `sub_000493D0` what kind of code was typed, then switches on the answer through the
nine-entry table at `0x00049F18`.

| Type | Meaning | Codes |
|---|---|---|
| 1 | a song, once | MILITAIN BIGBOI CHOPPER KIRKJONES CHOCOCITY RESPECT PLATINUMB GONBETRUBL ULTRAMAG PUMP LOYALTY GHOSTSHELL POWER SIEZE CARTAGENA AKIRA |
| 2 | reward points, once per amount | THESOURCE 25, GETSTUFF 50, DUCKETS 100, CROOKLYN 250, NEWJACK 500 |

That is 925 points in all, not "100 each" as some guides say, and the points cannot buy 54 fighters.
The classifier only ever returns 1 or 2 (or 0 for no match). No code unlocks fighters or venues.

### 2. Dead developer branches in the same handler

Cases 5 to 8 of the switch are still there and do real work; the classifier never selects them, so
they cannot be reached from the screen.

| Case | What it does | Reaches |
|---|---|---|
| 5 | on the strings `BIGBANG`, `MSGS`, `LQA` | `BIGBANG`: **`sub_000158F0`** (unlock everything, below) and `sub_00013590(1)`, reply "Bling"; `MSGS`: `sub_00013590(2)`; `LQA`: byte `[game-data object + 0x1AD5] = '1'`, which the front end exposes to its Flash screens as `g_LocalCheat` (`sub_0006B760`) |
| 6 | "Debug" | `sub_000B4CE0(1)`, which stores the byte at `0x0039C1DA` |
| 8 | "Holla" | byte `[game-data object + 0x1AD4] = 1` |

The strings for cases 6 and 8 are not in the image, so their code words are unknown.

### 3. `sub_000158F0`: unlock everything

Fetches the game-data object (slot `0x18` of the manager at `0x002FB148`), which holds the profile record at `+4` and the data tables at `+8`, then:

1. walks the character table (hash key `0x4CE5B1B2`) and inserts each id into the profile's
   unlocked-character set (`sub_00017000` tests membership, `sub_00016810` inserts);
2. does the same for the venue table (`0xD7DCA628`) and the venue set;
3. sets the reward points (record + `0x50`) to `0x2710` (10,000) and notifies the profile's owner. The points are read from the code; the shop was not looked at after the call.

`BuyCharacter` (`sub_00054080`) and `BuyVenue` (`sub_000543C0`) are the same operation one id at a
time: price from `sub_00053C50` / `sub_00054150`, subtract it from the points, insert. Its only
caller is case 5 above.

### 4. The debug flag at `0x0039C1DA`

`sub_000B5AD0` runs every frame. When the byte is non-zero and the game state `[0x00340374]` is 2
(a fight), it prints a debug label under each fighter's health bar (seen: `N4007 A`, `N06M2 B`;
it looks like the current animation node). Normal play shows nothing there. Holding the byte at 1
with `RECOMP_POKE=0x39C1DA:1` works with no code change (it writes four bytes, so the three after
the flag are zeroed; nothing visible depended on them in the runs tried).

### 5. Things that looked promising and are not

- `gconfig.xml` has `<buildtype>` with a comment listing 0 "Debug FE" to 5 "Online FE", and
  `<StoryModeCheatFile>cheats/smoke.smc</StoryModeCheatFile>`. The second string is not in the image at all (ASCII or UTF-16),
  so nothing reads it. `buildtype` is read into the game-data object at `+0x33C` (the function that registers the object as slot `0x18`, near `0x000126B5`).
  With it set to 0 the boot reaches the same main menu with the same front-end call sequence. Its
  effect past the main menu was not explored.
- `sub_0002CA20` draws a `DEBUG MENU -- %s` panel and `sub_0002CF80` begins "JUMP STARTING THE DAMN
  GAME!!!" (a match started straight from default fighters, with the four difficulty names `dirty`,
  `nuffrespect`, `rockandroll`, `manup`). Both have no direct callers, so they are reached through a
  vtable, and what enables them was not found. This is the best lead for a regression that skips the
  menus altogether (see "Next").

## What was added

| File | Change |
|---|---|
| `src/patches/dev_unlock.c` | `RECOMP_UNLOCK_ALL=1`: from the front end's call stream, once `Game.StartMainMenu` has been seen, run `sub_000158F0` on every `Control.GetScreenInfo(...)`. `RECOMP_DEV_DEBUG=1`: hold the debug flag at 1. Both off by default. |
| `src/recomp_manual.c` | one call to `defjam_unlock_all_on_funccall(text)` in the existing `funccall_hook`. |
| `scripts/harness.py` | `DEFJAM_HARNESS_SNAPSHOT_SAVE=<dir>` keeps the save area as the run left it, before the guard restores the original. |
| `tests/unit/test_harness.py` | covers the snapshot. |

The profile can change between screens (the user-ID screen loads one), so running the routine on
every screen change keeps the unlock in step with whichever profile is current. It only inserts
ids that are missing; what it repeats is setting the points back to 10,000.

Using it, from the repository root (use a disposable data root; the harness guard restores the save area):

```bash
DEFJAM_DATA=/path/to/data-root RECOMP_HEADLESS=1 python scripts/harness.py run unlock --env RECOMP_UNLOCK_ALL=1
python scripts/harness.py run fight --env RECOMP_UNLOCK_ALL=1 --env RECOMP_DEV_DEBUG=1
```

For a build you start by hand the variables work the same:
`RECOMP_UNLOCK_ALL=1 ./build/posix-release/defjam_recomp`.

## Why not a save

A profile is a 22,928-byte file (`20CM` magic, a header whose bytes `0x10` to `0x4B` change with any
change in the contents, then fixed-size tables). Two id lists in the owner's profiles have a fixed
number of slots (ten and eight; they look like characters and venues, which is unconfirmed), while the
game shows 74 fighters, so a full unlock probably does not fit the file as it is and the
on-disk list is not obviously the same thing as the in-memory set. A hand-edited file would also need
the header reproduced. With the unlock active, no profile file changed in any flow tried (One on One
to the result, Unlock Rewards, Story into the crib); the Options file was rewritten by the fight, and
whether the unlock touches it was not checked. So there is no game-made save to keep, and the runtime
switch makes one unnecessary for tests. It also means nothing is shared (saves are not published).

## Not covered

- **Story progress and cutscenes.** Story chapter state is in the profile and `sub_000158F0` does
  not touch it. The Story routes (`intro`, `crib`, `gym`) still need their profile, as the backlog
  item on golden saves says.
- **Songs** (Extras): codes only, once each. Typing the sixteen codes through the harness would do it.
- **Clothing, tattoos, items, moves**: bought in Story with cash; not looked at.
- **A real save.** The routine tells the profile's owner it changed. On a profile you care about,
  do not use it until it is known which flows save it.

## Next

1. A named harness route that asserts the unlock (reads `unlocked 74/74` from game state rather than a screenshot).
2. Find what enables the debug menu and jump start (`sub_0002CA20`, `sub_0002CF80`, found through their vtable); a direct "start this fighter on this venue" would replace menu scripting for any stage/fighter combination.
3. Decide whether Story checkpoints should be produced by a route (backlog item, option 2), now that characters and venues no longer depend on them.
4. A setting in `settings.ini` and the overlay instead of an environment variable, if testers need it outside the harness.
