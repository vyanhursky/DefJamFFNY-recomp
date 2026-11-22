# Fighter packs and online forks: what we guarantee

For projects that build an online mode on top of this port and want to use its fighter packs
unchanged. Every statement below is backed by a test or a recorded run, or is marked **not
guaranteed**. Nothing here adds networking to this project; it describes what a fork can rely on.

Fighter Mod Support is an experimental beta. **No part of the pack format
(`fighter-registry-draft-1`) is promised stable before v1.2.0 final**; treat it as a draft.

## 1. Identity

- The identity of a fighter is the string `pack-id/fighter-id`, together with the pack's version.
  It is the only fighter identity that should leave a PC.
- Handles, selection keys, native symbols, core and voice indexes are internal numbers. They are
  derived from the identity and are not part of this contract.
- Since v1.2.0-beta.3 those numbers depend only on the set of enabled packs, not on install history.
  Two PCs with the same enabled packs, the same dump, runtime version and language get the same
  numbers and compile the same files (tested with three pack sets, section 7). Use the string anyway.

### Moving the key range (forks only)

The game's own fighters use selection keys below 100. By default custom fighters get logical keys
from 100 up, one each in sorted stable-key order, and during a match each is mapped onto one of four
native bank rows, keys 100 to 103. A fork that uses part of the range above the retail roster for
its own fighters or venues can move both starts at build time:

| Setting | Default | Allowed | Where |
|---|---|---|---|
| First bank key | 100 | 100 to 124 | `BANK_FIRST` in `setup/fighter_keys.py`, `DEFJAM_FIGHTER_BANK_FIRST` in `src/hooks/fighter_keys.h` |
| First logical key | 100 | 100 to `0x7ffffff0` | `LOGICAL_FIRST`, `DEFJAM_FIGHTER_LOGICAL_FIRST` |

- Change both files; `tests/unit/test_fighter_keys.py` fails if they disagree.
- The fighter manifest records the pair (`fighter_keys=` in `[manifest]`, schema 3). A game built
  with another pair treats the manifest as stale. If the rebuild still disagrees, the game starts
  without packs and says so.
- There is no setting, launcher control or pack field for it. A pack never chooses a native number.
- For example, `BANK_FIRST = 124` and `LOGICAL_FIRST = 1000` leave 100 to 123 free.

*Tested:* the compiler and the native window decoder with the pair (124, 1000) and with the defaults,
including FWR3 standalone outfit parents; each decoder refuses the other pair's window
(`test_fighter_keys.py`). The native ControllerSetup shim also passes banks 100–103 and 124–127 as
decimal arguments while preserving its call frame (`test_fighter_controller_shim_native.py`). **Only the defaults are
tested in the game** by this project; a moved range is the fork's to test in play.

## 2. Roster order

The custom fighters appear in the roster in the order of their stable keys (sorted), after the retail
roster; there is no grouping by tier (the menu compiler sorts the custom rows by selection key and
appends them, `setup/fighter_menu.py`). It is a function of the enabled set alone. A pack can give a
fighter a native roster category (`tier`); every pack tested so far used one category for all its
fighters, so whether a different category moves a fighter in the grid is **not tested**. *Tested:*
`test_fighter_numbers_follow_the_enabled_set_not_install_history` (three install histories, one
result), and a game run where enabling a second pack that sorts first moved 2Pac one tile on and
the same fighter was still selected by its new tile.

## 3. The fighter set digest (`fighter-set-1`)

One value that says which fighter packs are enabled:

```
SHA-256 over, for each enabled pack sorted by pack id:
    id  NUL  version  NUL  sha256(bytes of that pack's fighters.json)  LF
lower-case hex; no pack enabled gives the empty string
```

`fighters.json` carries the SHA-256 of every file it declares, so the digest covers every byte the
compiler reads from a pack; README and LICENSE files are left out. It does not change with install
order, folder paths, the language pack, the runtime version or the fighter numbers. Anyone can
compute it from the ZIPs: the installed `fighters.json` is byte-identical to the one in the ZIP.

**What it does not cover.** Equal digests mean equal packs, nothing more. The compiled files also
depend on the game build (the runtime version and its fighter compiler) and on the retail files they
are compiled from: a fighter that inherits from a retail fighter takes content from the dump. Setup
checks the dump's executable by hash, its required paths and its file count, not every data file. So
a fork should compare its own build fingerprint as well as the digest, and treat the dump as part of
what must match. The fighter compiler's cache key (the name of the folder under
`mod-manager/fighter-cache/` that the manifest points to) already covers all of these: the hashes
of the retail files it reads, the compiler's own sources, the packs, the fighter numbers and the
language pack; it was the same in both folders of the section 7 test. It is a useful check, but **not
part of this contract**: its inputs and format may change during the beta.

Where to read it:

| Where | What |
|---|---|
| `mod-manager/fighter-manifest.ini`, `[manifest]` | `digest_schema=fighter-set-1`, `digest=<hex>`, `packs=<ids>` |
| `python setup/mods.py fighter-digest --data-dir DATA` | `{"event":"digest","schema":"fighter-set-1","digest":...,"packs":[{"id","version","sha256"}]}`; changes no state, takes no lock, works while the game runs |
| In the game process: `pc_fighters_set_digest()` (`src/hooks/pc_mods.h`) | the digest of the packs **this process loaded**, or `""` |
| The game log at start | `[FIGHTERS] set digest=<hex> packs=<n>` |

*Tested:* the formula (`test_fighter_set_digest_is_the_documented_formula`); unchanged by order,
paths, README or language and changed by a version, a declared file or a pack added or removed
(`test_fighter_set_digest_ignores_order_paths_language_and_readme_and_follows_content`,
`test_manifest_records_the_digest_with_or_without_a_language`); the three process states of
`pc_fighters_set_digest()` (`test_the_game_reports_the_digest_of_the_packs_it_loaded_and_nothing_otherwise`);
in the game, the manifest, the command and the start-up log gave the same value.

**Limit, not guaranteed:** the digest says which packs are enabled. At Play the game trusts compiled
files whose size and modification time still match the manifest; it does not hash them again. A
player who edits the compiled cache by hand is not detected. That is a fairness question for the
fork, not a sync guarantee from us.

## 4. Activation

- Packs are enabled and disabled whole.
- No pack changes while the game runs: the game holds `mod-manager/runtime.lock` for its whole life,
  and `fighter-enable`, `fighter-disable`, installs and removals then fail at once with an `error`
  event and change nothing (*tested:* `test_fighter_packs_cannot_change_while_the_game_runs`).
- The game reads the fighter manifest once, before the game starts, and never again in that process.
- If the packs fail a start-up check, the game starts again **without** packs and says so; in that
  process `pc_fighters_set_digest()` returns `""`. A fork should advertise the digest from that
  function, not from the manifest file.

## 5. Command line

Another launcher can install, enable and inspect packs without a window: see
[Mod manager, Command line](mod-manager.md#command-line). *Tested:*
`test_command_line_install_and_enable_contract`,
`test_command_line_refuses_a_bad_zip_with_one_error_and_no_change`. The validator
(`scripts/fighter-contract.py validate`) runs without a display on a machine with an extracted dump.

## 6. A separate data folder, and unlocks

- **Separate data folder.** Set `DEFJAM_DATA` for the game and `--data-dir` for `mods.py` to a
  folder of its own. It keeps its own saves, custom unlocks, packs and caches; nothing has to be
  copied into it (the dump is found through `--game-dir` and the installation's `game` link).
  *Tested in the game:* an empty folder set up by command line played a 2Pac match and the normal
  data folder (821 files) stayed byte-identical.
- **Unlocks.** Custom fighters need no unlock: a fresh save with unlock-everything off could pick
  2Pac at once (*tested in the game*). Retail fighters are locked or unlocked by each player's own
  save, so two players with the same packs can see different fighters as selectable, in the same
  grid positions. An online build that wants the same selectable roster for everyone should run in
  its own data folder with `[debug] unlock_all = true` (`RECOMP_UNLOCK_ALL=1`), which unlocks every
  retail fighter and venue in that folder's saves. **Not guaranteed:** that every player's save
  holds the same other progress (points, Story state).
- **Unlock-everything changes how a match plays.** The same pinned fight plays differently with the
  setting on than with it off (95 state records against the golden 80, every time; the cause is not
  known, `docs/09-testing-harness.md`). So every player in a room must have it the same, on or off.
  The replay results in section 7 were recorded with it on (`RECOMP_UNLOCK_ALL=1`).

## 7. Loading and timing

| Statement | Status |
|---|---|
| Two PCs with the same packs compile byte-identical files, whatever the install order and folder | **Tested:** two data folders, different paths, opposite install and enable order: all 230 compiled files (fighter cache, UI cache, generated UI texture pack, identity file) identical, same cache keys, same digest. `fighter-manifest.ini` differs by design (it holds paths and times). The same held for two packs with authored fighters: with DMX (intro, Blazin and victory owned) 225 files, and with the Vendetta roster (46 authored fighters) 1,278 files, identical in both folders. |
| Our fighter modules use no clock, random source or thread of their own | **Tested** by a word search (`test_fighter_determinism.py`). One allowed use: the clock names a damaged unlock file that is moved aside. Says nothing about the base game. |
| The same match plays the same with a custom fighter in it | **Tested.** The seed-pinned, step-timed replay (the switches of `regress.py`'s `replay` row), 2Pac (custom) against a retail CPU fighter picked through the menu, `scripts/fighter-replay-check.py`: two runs from one data folder and one from a second folder with the opposite install order produced the **same game-state stream** (positions, health, buttons, events) over the full window, 81 records to fight step 1,771, and all three reached the result screen. This was with the base game's time-seeded generators pinned (`--isolate-crowd`) and unlock-everything on (`RECOMP_UNLOCK_ALL=1`, section 6). |
| ... and with an authored fighter, whose owned files load during the fight | **Tested.** The same check with a fighter whose intro cinematic and Blazin finisher are the pack's own files: DMX (`dmx-ffny` 0.2.0; four runs, two from each of two folders with opposite install order) and a Vendetta roster fighter (`vendetta-roster` 1.0.0, 46 authored fighters enabled; five runs over the two folders). Every run that reached the fight recorded the **same game-state stream** for its pack over the full window to fight step 1,771 and reached the result screen. In every run the owned intro was loaded at match setup, before the first fight step, and the owned Blazin clips were read during the fight, at fight step 51, through the game's asynchronous loader. One further Vendetta run stalled during start-up, before the main menu, recorded nothing and is not counted; it did not happen again. **Limit:** the stream compares positions, health, buttons and events, not guest memory. The owned pool's address is not compared and does differ (next rows), so a fork that hashes raw guest memory can still see a difference. Not tested: a Blazin finisher actually performed inside the window (the clips were loaded, not played). |
| ... without pinning the base game's time-seeded generators | **Not guaranteed, and not ours.** Without `--isolate-crowd`, two runs from the two folders were identical but a third differed from fight step 781, in the **retail** CPU opponent's choice of move. That is the base game's known behaviour (issue #98, `docs/research/deck-determinism-98.md`): two match-logic generators are seeded from the CPU time-stamp counter and one is drawn once per presented frame, so host timing can change any CPU fighter's choices. An online mode that compares game state needs those pinned, whatever the fighters. |
| The replay needs a save whose first-time hints were seen | A fresh save stops the fight at the first tutorial hint (for example the crowd-weapon hint), which waits for A; step-timed input does not advance during it. Use a played save for such tests. This is game behaviour, not a fault. |
| Owned files are bound before the first simulated frame | **Not guaranteed.** Created-fighter (CAF) packs such as 2Pac load everything at match setup and never use the owned animation pool. Packs with authored cinematics or Blazin finishers read those files when the game plays them, through the game's own on-demand, asynchronous loader, which can be during the fight. In the replay runs above the owned intro loaded at match setup and the owned Blazin clips were read at fight step 51; another recorded run reserved the pool when an intro cinematic was selected after the match had started. |
| The 32 MiB owned animation pool | Reserved on the first owned cinematic or finisher read, from the host's guest heap, not the game's own arena. Its address depends on earlier host allocations: **not guaranteed** to be the same on two PCs. On one PC it was the same in every run with the same packs, and different between two pack sets (`01486180` with DMX, `01486700` with the Vendetta roster). It holds at most 512 allocations. |
| Cinematic variants | Our code chooses none: the game's own data selects the clip category (intro, outro or Blazin phase) and we substitute the one owned clip compiled for that core and category. The retail created-fighter row's counted random variants are left as they are and are never given to a new fighter; any choice among them is the game's own. |
| Load completion order | The game's own asynchronous loader decides it; `src/patches/fighter_film_async.c` only keeps request ownership by handle and adds no thread. |

## 8. Files the fighter compiler writes

It never changes the dump. It writes its own copies of `assets/djv2.sod`, `assets/v2ip.viv`,
`assets/entity.xml`, `assets/nis.viv`, the screens archive and the behaviour files into its cache,
and the game loads those copies (`runtime_environment` in `setup/fighter_packages.py`). A second tool
that also patches copies of these files (for example to add clothing parts) **cannot be combined with
fighter packs today**: the game loads one copy of each. Combining them needs one tool to take the
other's output as its input.

### Where the compiler reads its base files (forks only)

On the launcher's compile path, every read of the five files the compiler writes copies of, and
every retail pin, goes through `setup/fighter_base.py`: `path(game, relative)` and `pins()`. The five
are listed there (`assets/djv2.sod`, `screens/screens.viv`, `assets/entity.xml`,
`assets/nis.viv`, `assets/v2ip.viv`). This build always returns the file in the dump and its retail
pin; `test_fighter_base.py` fails if a launcher module reads one another way.

A fork whose own tool patches one of these files can point `path()` at the patched copy and give
`pins()` its hash, in that one module, so that its tool runs first and ours composes on top.

- **Nothing else changes:** every structural check of the compiler stays as it is. A patched file
  that moves a table the compiler relies on is refused with the normal error, and the game starts
  without packs.
- **Not guaranteed:** that any patched file compiles, now or after a later compiler change.
- **Not yet:** a documented override (an input folder that is hashed and recorded in the cache key,
  the manifest, the log and a game function). It would follow once a real patched file is shown to
  compile through the resolver.

*Tested:* with the real dump, a compile with `path()` pointed at byte-identical copies of the five
files in another folder produced the same compiled files as a normal compile.
The CAF cinematic donor path also uses this resolver through `fighter_workshop.original()` and
`pins()`. A synthetic test reaches that read through cinematic composition and verifies both the
redirected bytes and rejection of an incorrect hash (`test_fighter_base.py`). Rig, topology and
facial-capacity checks remain in place.

## 9. Created fighters

One recipe format, `caf-fighter-1`. Recipes refer to existing clothing rows; they do not add parts.
Core IDs 87 to 141 are used for created-fighter combinations, 142 and above for authored fighters.

## 10. Limits

- The same custom fighter cannot be picked for two participants (no mirror match of a custom fighter).
- Four participant bindings per match.
- The owned animation pool: 32 MiB and 512 allocations.
- The Steam Deck replay difference in the base game (issue #98) is open; nothing here has run on
  macOS, Linux or the Deck.
- The items the beta 2 notes list as not verified in a game still apply.
