# Import Xbox and PS2 saves

Open the game launcher and select **Help → Saves → Import saves…**. It imports
Story profiles from Xbox or PS2 into the installation you are using, without a
terminal, source checkout or separate Python installation. Save import is planned
for **v1.3.0**; earlier releases do not have this button.

Your supported USA Xbox dump is still needed to build the game. Importing a PS2
save does not let a PS2 disc build Recomp. Conversion is one-way; the imported
files are for Recomp, not an original console.

## Import a save

1. Close the game and the emulator that is using the source save. Open the
   launcher, staying on its settings screen before **Play**.
2. In **Help**, find **Saves** and select **Import saves…**.
3. Use **Choose file…** for a save export or ZIP, or **Choose folder…** for an
   extracted save folder. You can also paste a path. The importer detects the
   platform; no Xbox/PS2 selection is needed.
4. Leave **Include shared unlocks (Options)** off to import Story profiles only.
   Leave **Back up and replace matching profiles** off to keep existing profiles.
5. Select **Check saves**. Read the profile names, platforms and planned actions.
   Checking changes no saves. To replace a matching profile, enable replacement
   and check again. To transfer Options, enable both checkboxes and check again.
6. Select **Import**. Wait for the result, then close the dialog and select **Play**.
   In Story mode, choose the imported User ID rather than creating a new one.

The destination is shown in the dialog and is always this installation's save
folder. The original exports are never edited. Identical copies of one profile
are deduplicated; different saves with the same User ID are refused. Import them
separately to choose which version you want. Story profiles are not renamed or
merged. If a source or destination changes after checking, check again.

## Choose the right source

| Source | What to select |
|---|---|
| Original Xbox or Xbox emulator | A ZIP or folder containing the FFNY profile folders from `E:\UDATA\45410049\`. Each needs `SaveMeta.xbx` beside the file named after the profile; `saveimage.xbx` is optional. |
| PCSX2 memory-card image (`.ps2`) | With [mymc](https://github.com/ps2dev/mymc), open a copy of the card, select the FFNY save and export it as **PSU**. Then select that `.psu` file in the launcher. Export Options separately if wanted. |
| PCSX2 folder memory card | Select the FFNY save folder, or a folder containing its Story and Options saves. |
| PS2 save export | Select `.max`, `.cbs`, `.sps`/`.xps`, `.psu`, a PS2 `.psv`, a raw FFNY save, or a ZIP containing these exports. |

Whole Xbox disk images, PS2 memory-card images and emulator save states (`.p2s`)
are not save exports and cannot be imported directly. Extract/export the FFNY
save first. Large folders containing many unrelated games are refused; select
just the FFNY saves.

The observed US (`BASLUS-21004`) and European (`BESLES-52507`) PS2 saves share
the supported version-17 layout. The actual contained identity matters, not the
download's region label or extension. Unknown layouts, damaged PS2 checksums
and unsupported database references are refused. Xbox console signatures use an
unknown console key, so the importer checks their structure and signs them for
Recomp; it cannot authenticate the original console's signatures. Modified
source stats and currency are preserved.

PS2 icons are not Xbox save images and are not copied. A converted profile may
initially have a default/empty thumbnail. Enter and leave Wardrobe, then use Crib
Exit and accept the save to generate a native thumbnail; see
[thumbnail recovery](research/v0121-created-fighter-thumbnail.md).

## Shared unlocks and backups

**Options** contains global fighter/venue unlocks, cheat-redemption flags and
retail music selection/order. Importing a completed Story profile alone does
not necessarily unlock everything in Battle.

Start and close the game once so this installation has its own Options save.
Import the exported Options with **Include shared unlocks (Options)** and
**Back up and replace matching profiles** enabled. The source unlock state
replaces the native unlock state, so a less complete source can remove unlocks.
The installation's preferences, leaderboards and final platform flags are kept.
These rules are the same for Xbox and PS2 sources.

Every replacement moves the whole previous profile folder into a unique
`save/import-backup-…/<profile folder>/`. The completion message shows the
backup's location. **Help → Saves → Open** opens the save folder. To undo an
import, close the game, move the imported profile folder out of
`save/UserData/45410049/`, and copy its backup folder back into that directory.
New imports do not need a backup because they replace nothing. A failed batch
publication restores the profiles it had already replaced.

The importer refuses to write while another Recomp instance or a mod operation
holds the data folder's runtime lock. Close the game and try again.

## Advanced: command line

The launcher and both script names use the same importer, validation and backup
rules. The shipped app supplies its own interpreter and helpers. For source
builds, use Python 3 with the repository's `scripts/` directory intact; no extra
Python packages are required. Use `python3` on macOS/Linux if needed.

```sh
python scripts/save-import.py "save.zip" --check
python scripts/save-import.py "save.max" --save-dir "<data>/save" --dry-run
python scripts/save-import.py "save.psu" --save-dir "<data>/save"
python scripts/save-import.py "Options.psv" --save-dir "<data>/save" --include-options --force
```

You can supply multiple sources together, including a mixture of platforms.
`--check` validates sources without needing a destination; `--dry-run` previews
the destination too. Both leave saves unchanged. `--force` means back up and
replace. Without an explicit destination, discovery uses `DEFJAM_DATA/save`,
then the receipt in `--install <installation>`, then the default macOS install.
An explicit `--save-dir` avoids ambiguity. `save-import-ps2.py` remains a
compatibility alias; it no longer has a separate conversion or installation path.

## Functional retest on each operating system

Use a disposable installation/data folder or a verified complete backup. Keep
exported saves local; do not attach them to a PR. Test the packaged app as well
as a source build so bundled-helper and picker behavior are covered.

| Check | Expected result |
|---|---|
| Open Help → Saves → Import saves; cancel each file/folder picker and close the dialog | Launcher stays usable; no save files change. The in-game overlay directs you back to the launcher. |
| Choose a PS2 MAX, CBS, SPS/XPS, PSU, PSV/ZIP and folder export; check before importing | Correct profile/platform/actions; no save changes until Import. Include at least one US and one European profile. |
| Choose an Xbox save ZIP and an extracted `UDATA/45410049` folder | Correct profiles; imported files are re-signed for Recomp, with their Xbox thumbnails when supplied. |
| Import each platform's Story profile | User ID appears in Story; correct fighter, clothes, styles, stats, cash and progress; enter Crib, shops and gym, then play a Story fight. |
| Save normally through Crib Exit, quit, relaunch and reload | Profile remains loadable and new progress survives, without importing it again. |
| Check/import a matching User ID with replacement off, then on | Off keeps every existing byte; on preserves an exact previous-folder backup, then loads the new profile. Check the documented restore steps too. |
| Import each platform's Options with both checkboxes on | Shared Battle unlocks/music change; native preferences and leaderboards stay intact; exact prior Options backup exists. With Options off it is skipped. Missing native Options gives a clear error. |
| Change the source/destination between Check saves and Import | Import refuses; rechecking enables the new preview. No unexpected replacement. |
| Choose a damaged/truncated PS2 export, unknown layout, whole `.ps2` card or `.p2s` | Clear error/guidance; existing saves and original exports stay unchanged. A failed mixed batch writes no profiles. |
| Use spaces and non-ASCII characters in source, install and data paths; cancel/retry after an error | Pickers, preview, import and backup paths work. No terminal or separately installed Python needed in the packaged app. |
| Run a second game instance using the same data folder, then attempt import | Import refuses while it is running; succeeds after it closes. Play stays blocked while the current launcher is importing. |
| At small window / large text size and with a controller | Import dialog scrolls; source, results and buttons remain reachable. On Steam Deck, also check Desktop Mode pickers and the on-screen keyboard. |

Technical sample analysis and the earlier macOS native evidence are in
[PS2 save conversion](research/ps2-save-import.md). The PR records which of these
checks passed on its current launcher build; source-format tests alone do not
qualify Windows/Linux gameplay or the packaged app.
