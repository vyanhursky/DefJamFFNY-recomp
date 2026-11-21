# PS2 save conversion — issue #248

Investigation on November 21, 2026. Source inputs were downloaded by the owner
from the [GameFAQs save listing](https://gamefaqs.gamespot.com/ps2/920171-def-jam-fight-for-ny/saves).
Only hashes and findings are retained here; saves, icons, captures and generated
code remain local. User instructions: [importing PS2 saves](../importing-ps2-saves.md).

## Samples and archive differences

Five representative saves cover the four supplied wrapper families and both
observed regional identities:

| Download ID | Export | Actual profile | Source archive SHA-256 |
|---|---|---|---|
| 28091 | MAX, European | RANE | `74ef84acfe5dc3833d9dc3aba0a1a0b9c0eee6ebc263c1a528835fe68705c815` |
| 6992 | CodeBreaker, US | AMP | `2e2423f958be5e7938b348fcea353ff3d42e44c2739b047dd9a9d2aa37e99b32` |
| 5249 | SharkPort, US | GUASAP | `b495421b012f2c11448dfd391bfb79fac0ada46fb346419b6cd792cfcff1ece3` |
| 30862 | MAX, US | ERICK | `17d15a32645f0d7a693545cc088247d176a7620aa8b08aebd4c9d31396eaf4dc` |
| 33775 | ZIP of two European PS2 PSV exports | ALPEREN and Options | `35087d5fecd7203f90788d132f721faa96f234bea26f9b4aa363e81bc9278661` |

The additional inputs 24785/Z, 33730/EBERT, 33773/PLAYER1, 35089/ALPEREN and
35472/ULT1MATE were unpacked and passed the same inner MC02 checks. All nine
Story profiles have 22,888 bytes and the same version/build identity.

- MAX uses the conventional whole-file CRC with its checksum field zeroed,
  followed by a size-bounded LZARI stream and aligned file records. 28091 stores
  the uncompressed size in both size fields; 35089 excludes the four-byte output
  size from its compressed-size field. The reader accepts these measured writer
  variants while checking the archive CRC and exact member boundaries.
- CBS 6992 puts total file length in its compressed-length field; 33730 puts
  compressed-body length there. Both decode to 62,772 bytes containing the same
  three file roles. Despite its listing as European, 33730 contains
  `BASLUS-21004EBERT`, a US identity.
- SPS 5249 wraps the same three file roles without compression. Its outer legacy
  trailing checksum is not verified; the three inner MC02 CRCs are verified.
- Each supplied PSV ZIP contains Options and ALPEREN. The ZIPs 33775 and 33776
  are duplicates, and ALPEREN's inner save also matches MAX 35089 exactly.
  PSV's PS3 signature is not verified; bounded nonoverlapping member offsets,
  ZIP CRCs and the inner FFNY MC02 CRCs are checked.
- Z/24785 has training stats of 55, above the normal 50-point limit; ULT1MATE
  has no completed fighter yet. The converter preserves these source values.
  They must not be treated as ordinary completed-profile acceptance controls.

Contained PSV MC02 fingerprints (not the PS3 wrapper):

- Options: `59bd79540087c16aae0aefdbe1928dd6b6888f7dba299bfefe3c8310380fc166`.
- ALPEREN: `0038f12b9bbc6ac415b90376143b50e68449f123d8a02b7035a627b159393178`.

## MC02 and layout evidence

All observed PS2 profiles use little-endian `MC02` (`20CM` bytes), a 28-byte
header, a 64-byte identity and a `0x590C` Story payload. Global Options uses
`0x1494`. The three checks cover identity, payload and the first 24 header bytes.
They use EA's non-reflected polynomial recurrence, not zlib's reflected CRC.
The independently implemented recurrence matches every checksum in all inputs.
The identity is version 17/build -2048007603; the supported Xbox identity uses
version 17/build -2030886228. The existing Xbox importer supplies the signing
implementation and native folder hash.

Xbox's original `sub_000148B0` initializes a `0x5904`-byte serialized profile;
`sub_000D23B0` stages that exact size. The original profile initialization and
accessors identify the embedded arrays, flags and two following inline event
lists. The observed mapping is:

| PS2 payload span | Xbox destination | Behavior |
|---|---|---|
| `0:0x17E` | `0:0x17E` | Same profile/currency/stats/style/counter prefix |
| `0x17E:0x184` | none | Six zero padding bytes |
| `0x184:0x4D8E` | `0x17E:0x4D88` | Embedded data, completion/milestone flags and counter |
| `0x4D8E:0x4D90` | none | Two zero padding bytes |
| `0x4D90:0x590C` | `0x4D88:0x5904` | Remaining lists, inventory and appearance |

The counter at PS2 `0x4D8D` must survive at Xbox `0x4D87`. Removing two bytes
from `0x4D8A` instead produces the right total size but shifts this field; that
early prototype was superseded before final conversion tests. Appearance moves
from `0x5560` to `0x5558`, as separately observed in the Workshop PS2 reader.
This is a mapping for the observed retail layout, not a general platform ABI.

Options conversion uses the existing native Options as its template. It copies
`0x1214:0x148C`, containing venue/fighter counts and backing lists, redeemed-code
flags and retail music order/count. The native prefix and final four bytes stay
unchanged. This avoids copying PS2 audio/preferences and its two differently
laid-out final flags. Counts and table/row limits are checked before writes.
The supplied Options has 24 venues, 74 fighters and 32 retail songs.

## Native acceptance

Test executable: the existing macOS arm64 `posix-release` beta.3 build (recorded November 14;
executable SHA-256 `3139dfb8760b3237bf6f1145ef93e0a20b2a43eecad6e5f05f61d06bb8ec7c6f`), toolkit
`8e61aec4f2506aa5faf20f78154d26bf7a0a1fc5`. No runtime source, toolkit pin or
build behavior changes in this PR. Native checks run serially against separate
throw-away data roots, with `RECOMP_UNLOCK_ALL=0`, `RECOMP_SETTINGS=none` and the
complete-save-root guard. Original downloads and the owner's live save are not
modified. Game-free unit tests use invented data only.

Five representative profiles reached the Crib with the final converter, with
source cash, development points, styles and training stats observed in the log:

| Profile | Native log | Additional coverage |
|---|---|---|
| RANE | `ps2-final-RANE-20261121-144150.log.err` | European MAX, clothing-shop entry; gym anchor not reached |
| AMP | `ps2-final-AMP-20261121-144500.log.err` | US CBS |
| ALPEREN | `ps2-final-ALPEREN-20261121-144555.log.err` | European PSV ZIP plus Options unlock transfer |
| ERICK | `ps2-final-ERICK-20261121-145333.log.err` | US MAX, native save; fresh-process reload below |
| GUASAP | `ps2-final-GUASAP-20261121-145638.log.err` | US SPS |

All five save guards restored byte-identically. Native run logs/captures stay in
`logs/`; these are loading/field/persistence checks, not full fight acceptance.
Final aggregate test results are recorded in the PR description. The batch
check converted all nine unique Story files, verified every output's 22,928-byte
size and three native signatures, and verified all nine input hashes unchanged
(`logs/ps2-import-batch.json`). Full unit suite: 2,602 passed / 78 skipped on
Python 3.12 and 3.13; focused PS2 + existing Xbox import tests: 40 passed.
The original Python 3.11 run had two environment failures (old tarfile API and
macOS `/var` alias rejection); the modern runs used `TMPDIR=/private/tmp`.

ERICK reached Crib Exit -> Yes and the game called `MemCard.Save`, then
`Game.StartMainMenu(3)` (`ps2-final-ERICK-20261121-145333.log.err`). Its saved
profile changed, stayed 22,928 bytes, retained the cash/development/counter
fields and passed all three native signatures. No checksum/profile bytes were
patched after the game saved. A fresh process loaded that exact native-saved
profile back into the Crib with the same cash, points, styles and stats
(`ps2-final-ERICK-20261121-145509.log.err`); the PS2 converter was not rerun
for the reload. Both complete-save-root guards verified byte-identical restores. The initial
sandboxed launch failed before boot because macOS denied Xbox address-space
mapping; that was an environment failure. A corrected unrestricted launch
listed RANE. An initial pad recipe selected Create User ID and did not prove
Story loading; corrected profile selection reached the Crib. The RANE gym
recipe reached the clothing shop instead and failed its gym completion anchor;
it establishes Crib/clothing coverage, not a gym pass. The early ERICK exit
recipe likewise entered the map/shop and did not prove an in-game save; a second
recipe selected the default No in the exit dialog. Both negative probes are
retained; the corrected Yes recipe is the save evidence above.

Qualification remains limited to measured profiles/paths on macOS. It does not
prove every chapter, venue, outfit, modded database, region, or Windows/Linux
native gameplay. Full release regression is not required for this standalone,
unit-tested script under CONTRIBUTING.md; this is not a runtime qualification.

## Format references and attribution

- [Ross Ridge's mymc](https://github.com/ps2dev/mymc): public-domain MAX/CBS/PSU/SPS
  reference. The decoder adapts the decoding portion of `lzari.py` to Python 3;
  the CBS permutation and format descriptions originate in `ps2save.py`.
- [PCSX2 myMCpp PSV reader](https://github.com/PCSX2/myMCpp/blob/master/src/core/formats/PS2SaveFile.cpp):
  PSV field-layout reference; our reader does not copy its implementation.
- [EA MC02 checksum reference](https://gist.github.com/NWPlayer123/191de6941915f2ddb4ff65e0bded9e78):
  corroborates the polynomial/byte-feed rule; our table is generated from the
  polynomial and verified against the local samples and an independent unit oracle.
