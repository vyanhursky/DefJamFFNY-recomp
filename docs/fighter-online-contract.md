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
  numbers and compile the same files (tested, section 7). Use the string anyway.

## 2. Roster order

The custom fighters appear in the roster in the order of their stable keys (sorted), after the retail
roster. It is a function of the enabled set alone. *Tested:*
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

Where to read it:

| Where | What |
|---|---|
| `mod-manager/fighter-manifest.ini`, `[manifest]` | `digest_schema=fighter-set-1`, `digest=<hex>`, `packs=<ids>` |
| `python setup/mods.py fighter-digest --data-dir DATA` | `{"event":"digest","schema":"fighter-set-1","digest":...,"packs":[{"id","version","sha256"}]}`; read-only, no lock, works while the game runs |
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

## 7. Loading and timing

| Statement | Status |
|---|---|
| Two PCs with the same packs compile byte-identical files, whatever the install order and folder | **Tested:** two data folders, different paths, opposite install and enable order: all 230 compiled files (fighter cache, UI cache, generated UI texture pack, identity file) identical, same cache keys, same digest. `fighter-manifest.ini` differs by design (it holds paths and times). |
| Our fighter modules use no clock, random source or thread of their own | **Tested** by a word search (`test_fighter_determinism.py`). One allowed use: the clock names a damaged unlock file that is moved aside. Says nothing about the base game. |
| The same match plays the same with a custom fighter in it | **Tested, over a shorter window than planned.** The seed-pinned, step-timed replay (the switches of `regress.py`'s `replay` row) with 2Pac (custom) against a retail CPU fighter, picked through the menu: two runs from one data folder and one from a second folder with the opposite install order gave the same game-state stream (positions, health, buttons, events) for as long as all three ran: identical up to fight step 631 in all three, and the two runs that stopped there matched record for record. The stream could not cover the full 1,800 steps because the fight stops advancing in this replay setup (next row). |
| The replay setup itself | **Not guaranteed; under investigation.** In this long replay setup the fight simulation stops advancing after a while, while the picture keeps being drawn: with the custom fighter at step 651 or 1,397 depending on the run, and **without any fighter pack, on a build of `main` too**, at step 1,633. The retail runs on `main` and on this branch produced the same events step for step up to that point. It is therefore not caused by fighter packs, but it limits how long a replay comparison can run until it is understood. |
| Owned files are bound before the first simulated frame | **Not guaranteed.** Created-fighter (CAF) packs such as 2Pac load everything at match setup and never use the owned animation pool. Packs with authored cinematics or Blazin finishers read those files when the game plays them, through the game's own on-demand, asynchronous loader, which can be during the fight (seen in a recorded run: the pool was reserved when an intro cinematic was selected after the match had started). |
| The 32 MiB owned animation pool | Reserved on the first owned cinematic or finisher read, from the host's guest heap, not the game's own arena. Its address can depend on earlier host allocations: **not guaranteed** to be the same on two PCs. It holds at most 512 allocations. |
| Cinematic variants | Our code chooses none: the game's own data selects the clip category (intro, outro or Blazin phase) and we substitute the one owned clip compiled for that core and category. The retail created-fighter row's counted random variants are left as they are and are never given to a new fighter; any choice among them is the game's own. |
| Load completion order | The game's own asynchronous loader decides it; `src/patches/fighter_film_async.c` only keeps request ownership by handle and adds no thread. |

## 8. Files the fighter compiler writes

It never changes the dump. It writes its own copies of `assets/djv2.sod`, `assets/v2ip.viv`,
`assets/entity.xml`, `assets/nis.viv`, the screens archive and the behaviour files into its cache,
and the game loads those copies (`runtime_environment` in `setup/fighter_packages.py`). A second tool
that also patches copies of these files (for example to add clothing parts) **cannot be combined with
fighter packs today**: the game loads one copy of each. Combining them needs one tool to take the
other's output as its input.

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
