# Importing PlayStation 2 saves

`scripts/save-import-ps2.py` converts Def Jam: Fight for NY PS2 profiles into
Recomp's Xbox save format. It uses Python 3's standard library; no emulator,
console key or Python package is needed for the conversion. The PS2 copy still
cannot build the game: Recomp needs your own supported Xbox dump.

## Steps

1. **Close Recomp and PCSX2.** Keep a copy of your original memory card/export.
2. If your save is in a PCSX2 `.ps2` memory-card image, use
   [mymc](https://github.com/ps2dev/mymc) to open a **copy** of the card, select
   the FFNY save and export it as `.psu`. Export **Options** separately too if
   you want its global fighter/venue/music unlocks. A PCSX2 folder memory card
   can be read directly. Savestates (`.p2s`) are not memory-card saves.
3. Get a source checkout containing this script and its two helpers
   (`ps2_save_containers.py`, `ps2_lzari.py`) in `scripts/`. From that checkout,
   validate your export:

   ```sh
   python scripts/save-import-ps2.py "my-profile.psu" --check
   ```

   On macOS/Linux use `python3` if `python` is unavailable. The tool also reads
   `.max`, `.cbs`, `.sps`/`.xps`, PS2 `.psv`, raw FFNY save files, ZIPs containing
   these formats and extracted save folders. It does not modify a memory card.
4. Preview, then import into the **save** folder in your Recomp data folder
   (the folder selected during setup):

   ```sh
   python scripts/save-import-ps2.py "my-profile.psu" --save-dir "<data folder>/save" --dry-run
   python scripts/save-import-ps2.py "my-profile.psu" --save-dir "<data folder>/save"
   ```

   The data-folder discovery options match the Xbox importer: `DEFJAM_DATA`,
   `--install <folder>` or the macOS default install. An explicit `--save-dir`
   avoids ambiguity. To replace an existing profile, add `--force`; the whole
   previous profile folder is moved into `save/import-backup-<unique ID>/`
   before replacement. Both current and legacy native folder names are recognized.
5. Start Recomp and select the imported User ID. Saves remain one-way: the
   converted files are for Recomp, not a PS2 or a real Xbox.

Multiple exports can be supplied together. Identical profiles are deduplicated;
conflicting copies with the same User ID are refused before anything is written.
Import conflicting copies separately into different test save areas to choose
which one you want. The converter does not rename or merge Story profiles.

## Options and unlocks

A Story save and **Options** are separate files on PS2. A completed Story profile
alone does not necessarily carry every global Battle unlock.

Start and close Recomp once so it has its own native Options file, then import
an exported PS2 Options file explicitly:

```sh
python scripts/save-import-ps2.py "my-options.psu" --save-dir "<data folder>/save" --include-options --force
```

This replaces the global venue/fighter unlock lists, cheat-redemption flags and
retail music selection/order with the PS2 values. It preserves native preferences,
leaderboards and final platform-specific flags. It **replaces**, rather than
unions, the unlock state, so a less complete Options source can remove unlocks.
The previous native Options folder is backed up. Without `--include-options`,
Options is reported and skipped; `--check` still validates it.

PS2 icons are not Xbox save images. They are not copied. An imported profile can
initially show a default/empty small thumbnail. Enter and leave Wardrobe, then
use Crib Exit and accept the save to regenerate native thumbnails, as described
in [thumbnail recovery](research/v0121-created-fighter-thumbnail.md).

## Differences and supported scope

- MAX Drive uses LZARI compression; CodeBreaker uses its fixed RC4 permutation
  and zlib; SharkPort/X-Port and PSU wrap uncompressed files; PSV uses a file
  table inside a PS3 export. These wrappers do not change the FFNY payload.
- The observed US (`BASLUS-21004`) and European (`BESLES-52507`) saves share one
  version-17 profile layout. Actual contained identities matter; a download's
  region label or extension can be misleading.
- PS2's MC02 header is 28 bytes with three EA CRCs. Xbox's is 76 bytes with three
  HMAC-SHA1 signatures. Re-signing the PS2 bytes with the Xbox importer alone
  cannot convert the profile.
- PS2's `0x590C`-byte Story payload has six extra padding bytes at `0x17E` and
  two at `0x4D8E`. Removing those precise spans produces Xbox's `0x5904` bytes,
  preserving the intervening flags/counter, event lists and appearance. The
  identity block is changed to the supported Xbox build and signed with the
  existing importer's Recomp key. Unknown revisions, sizes, nonzero padding,
  checksum damage and out-of-range event/unlock lists are refused.
- The tool preserves modified source stats/currency; it does not certify that a
  community save has normal gameplay values. Other regions/revisions, modded
  database layouts, full card images and savestates are outside the supported
  conversion scope. Windows/Linux native gameplay has not been qualified by
  the macOS checks below.

Measured sample identities and native results are in the
[PS2 save investigation](research/ps2-save-import.md). No downloaded save, icon,
game bytes or capture is distributed with this tool; unit fixtures are invented.
