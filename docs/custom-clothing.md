# Custom clothing

Clothing packs add new clothes for your Story mode fighter. Each item is a new look for a clothing item
the game already has (its *base* item): it uses the base item's 3D model, fits and colour list, and
brings its own textures, painted on the same layout as the base item's textures. An item is either in
your **Wardrobe** from the start, or sold in the **stores** of the Shop District at a price you choose.

A pack can hold one item or a whole set (up to 64 items). Packs are turned on and off as a whole on
the launcher's **Mods > Clothing** tab.

Your saves stay ones the original game can read. A custom item you wear is written to the save as its
base item; the custom item is remembered next to the save and comes back the next time you load it,
as long as its pack is enabled. With the pack off, your fighter wears the base item instead.

## Using a pack

1. Launcher: **Mods > Clothing**, then **Browse for ZIP...** (or type the path) and **Install or update
   from ZIP**.
2. Tick the pack. The launcher prepares its clothes for the game (a few seconds).
3. Play Story. Wardrobe items are in **Crib > Wardrobe** under their category (a T-shirt under
   Tops > T-Shirts, jeans under Bottoms > Jeans). Shop items are in the store that sells their
   category, for example jeans in Syndicate Urban Streetwear.

Untick a pack before you remove it. Unticking keeps what you bought and wore with it: tick it again
later and it all comes back.

## Making a pack

You need the game installed (setup's data folder or a build from your own dump) and Python with Pillow,
which every installation has. The commands run from the game's source folder; `game` is the folder of
your extracted dump (the `game` folder of a build).

1. **Pick a base item.** List the game's clothing:

   ```
   python setup/clothing_pack.py list --game game
   ```

   Each line is a Type number, the item's name, its price and number of colours, and the name of its
   texture set, for example `5  Jeans_Dark Cargo  ($45, 2 colour(s), V2CP_121_0027_A04)`.

2. **Export it** into a new pack folder. This writes the base item's textures as PNGs, one per colour,
   and a `clothing.json` describing the item:

   ```
   python setup/clothing_pack.py export --game game --base "Jeans_Dark Cargo" --pack my-clothes --id red-cargo --name "Red Cargo Jeans"
   ```

   Run it again with another base and id to add more items to the same pack (a set).

3. **Paint** the PNGs (`my-clothes/red-cargo/01.png`, `02.png`, ...). Keep the layout: every part of
   the image lands on the same place of the 3D model as in the original. A PNG may be the same size as
   the original or 2x / 4x that size (it is scaled down to the game's size). Transparency in your PNG is
   ignored: the game keeps the original texture's alpha, which it uses for its own shading. Leave out a
   colour's PNG (remove its line from `textures`) to keep the original texture for that colour.

   **Fits.** Many items come in several fits (jeans: Standard, 1 Ankle Up, Both Ankles Up, ...). The game
   keeps a texture of each fit, all drawn on the same layout, so your colour PNG is painted onto every
   fit, each fit keeping its own shading. To give one fit its own picture, add a key `"01@5"` (colour 01,
   the fit whose model number is 5 above the base's); `list` prints the fits' offsets.

4. **Update the hashes** after editing (clothing.json records each PNG's SHA-256):

   ```
   python setup/clothing_pack.py rehash --pack my-clothes
   ```

5. **Check it** against your game:

   ```
   python setup/clothing_pack.py validate --game game my-clothes
   ```

6. **ZIP it** with the pack folder at the top (`my-clothes/clothing.json`, `my-clothes/red-cargo/01.png`,
   ...) and install it as above.

### clothing.json

```json
{
 "format": "clothing-pack-1",
 "name": "My clothes",
 "items": [
  {
   "id": "red-cargo",
   "name": "Red Cargo Jeans",
   "base": "Jeans_Dark Cargo",
   "price": 45,
   "availability": "wardrobe",
   "textures": {
    "01": {"path": "red-cargo/01.png", "sha256": "..."},
    "02": {"path": "red-cargo/02.png", "sha256": "..."}
   }
  }
 ]
}
```

| Field | Meaning |
|---|---|
| `id` | Short lowercase name (letters, digits, `-`), unique in the pack. The pack folder and the id identify the item in your saves' side files. |
| `name` | What the game shows, up to 40 characters (the game's font has plain letters, digits and punctuation). |
| `base` | The game's name of the item it is based on, as `list` prints it. |
| `price` | The store price (0-99999). Optional: the base item's price. |
| `availability` | `wardrobe` (owned from the start) or `shop` (sold in the stores). Optional: `wardrobe`. |
| `textures` | Colour number (`01`, `02`, ...) to a PNG in the pack and its SHA-256: that colour on every fit. `01@5` is colour 01 on one fit only (offset 5). Colours without an entry keep the base item's texture. |

A pack contains `clothing.json`, the PNGs it lists, and optionally `README.md`, `CHANGELOG.md`,
`LICENSE.txt` and `preview.png`. Anything else is refused at install. Nothing in a pack is run.

Limits: 64 items per pack, 256 enabled together, 99 custom items on one base model.

### Not yet supported

- New 3D models: an item always uses its base item's model.
- Your own shop and wardrobe pictures: an item shows its base item's pictures (the pictures are
  renamed copies; replacing them is planned).
- Jewelry, hair and tattoos: the same design should work, they are separate tables in the game.
- Custom clothing on Workshop fighters made with Create-a-Fighter packs.

## How it works

For maintainers. The research behind it is in the pull request that added it; this is the contract.

### Before Play: the compiler

`setup/clothing_pack.py compile` (run by the mod manager when a clothing pack is enabled, disabled,
updated or removed) writes `<data>/cache/clothing`:

| File | Content |
|---|---|
| `items.txt` | `clothing-items-1`, then `#clothing-set-1<TAB><digest>`, then one tab-separated line per item: key (`<pack folder>/<id>`), base row, texture-set code, colours, price, availability, name |
| `v2cp_N-add.viv` | Files added to `assets/v2cp_N.viv`: each new texture goes into the archive that holds its base's textures |
| `parts-add.txt` | `clothing-parts-1`, then one line per item and fit: key, category, fit model, the base's own texture-set code. The game inserts the item's texture sets into the parts catalogue from these (below) |
| `screens-add.viv` | The items' thumbnails, added to `screens/screens.viv` |
| `receipt.json` | `clothing-cache-2`: the compiled items, the digest and the hash of each file |

The compiler checks a texture PNG's size from its header before it decodes anything: it must be the
base texture's size or 2x/4x that.

How the game finds an item's files (from the lifted code):

- The Clothing table of `assets/djv2.sod` has one row per item: word 1 model number, word 2 texture-set
  code (`A01`...), word 3 colour list, word 4 price, word 5 display name, word 6 fit list, word 8 Type.
- `sub_0001FE70` builds the names: the Type picks the category from a 16-entry table at `0x002898D8`
  (111 ... 144); garments are `V2CP_<cat>_<model>_<set>_<colour>.xsh`, shop and wardrobe thumbnails
  `screens/shopThumbs/100/V2TN_<cat>_<model>_<set>_<colour>[_t].big`.
- A fit (word 6: count, then 3-word records) gives a model offset in its record's second word; the
  creator builds the garment texture name from model + that offset (hats, category 141, use the model
  itself). The game has one texture set per fit, drawn on the same layout (Dark Cargo, model 27, 20 fits:
  sets at models 27-46).
- The creator reads a body part's files from one fixed archive, as `assets/v2cp_N.viv|<name>`
  (`sub_000990B0` maps the part to N), and only builds a texture set listed under its mesh in the parts
  catalogue `createplayer_parts.xml`.

So an item is a copy of its base row with its own texture-set code (`Z01`, `Z02`, ...; see the letter
range below; a code is chosen free on every fit model of the base, since fit ranges of different bases overlap), its
textures for every fit in the base's archive, its set listed in the catalogue under every fit's mesh, and copies of
the base's thumbnails renamed to the new code (a thumbnail is a small archive whose files carry its own
name; the codes have the same length, so the rename keeps every offset).

### In the game: `src/patches/clothing.c`

At start (after the songs, so it builds on the language pack's, the fighters' and the songs' copies of
the same files), it reads the cache and serves through the game-file redirect:

- `assets/djv2.sod` with one row per item appended (`src/hooks/pc_sod.c`: a byte copy of the base record,
  so the colour and fit lists are the base's; new name, texture-set code, price and display name). Each
  row name is `Custom_<key>~` plus 7 characters computed so its hash is exactly the table's highest hash
  + 1, + 2, ... in `items.txt` order (sorted pack, then manifest order; the approach of FFNY Online's
  clothing draft; a search is the fallback). So retail rows keep their ranks and the record handles
  (`table << 24 | colour << 16 | rank`) that saves hold stay valid, and the added rows rank in a known
  order. Custom ranks never reach a save, so they may change when packs change.
- `assets/v2cp_N.viv` and `screens/screens.viv` with the added files (`src/hooks/pc_big.c` appends to a
  copy; only `createplayer_parts.xml` may be replaced).

The served copies are written to `<data>/cache/clothing/served` and rewritten only when they change.

**Chain safety.** Everything is built on the copies the redirect chain serves before clothing starts
(the language pack's, the fighters', the songs', and a fork's own layer if it installs one first), not on
the retail files:

- *Codes.* The compiler picks a code free in the player's retail archives. At start, the game checks it
  again against the names in the served `v2cp_1`...`v2cp_4`, the served parts catalogue, the thumbnails in
  the served `screens.viv` and the items before it; if it is taken, it takes the next free code from
  `Z01`...`Z99` (the log says so: `Z01 is taken in the files served before ours; it uses Z02`) and
  renames the item's garments and thumbnails to it. An item with no free code is left out, with a log line;
  clothing stays on for the others.
- *The parts catalogue.* `createplayer_parts.xml` (byte-identical in `v2cp_0` and `v2cp_3`) is read from
  the served `v2cp_3`; for every line of `parts-add.txt` the item's texture-set block is inserted under the
  fit mesh's existing blocks and its `<count>` raised. Everything else, lines another tool added
  included, is kept byte for byte (line endings and tabs too). The patched file replaces the catalogue in
  both archives.

**Letter range.** Texture-set codes are a letter and two digits. Retail uses `A`-`L`. This project's
clothing packs use `Z01`-`Z99`; FFNY Online's Studio uses `Y`. Another tool that adds texture sets should
pick an unused letter and tell us, so the list here stays complete. Because codes are checked against the
served files, two layers that do share a letter do not break each other; the one served later moves.

**For forks.** `src/patches/clothing.h`:

- `clothing_set_digest()`: the `clothing-set-1` digest of the enabled packs (`""` when none), for a content
  print. It is SHA-256 over `clothing-set-1\n` plus one `<pack folder, lower case>\t<SHA-256 of its
  clothing.json>\n` line per pack, in sorted order (clothing.json carries every PNG's SHA-256). Like
  `fighter-set-1`, it does not cover the player's dump or what other layers serve. `python setup/mods.py
  clothing-digest` prints the same digest without starting the game.
- `clothing_base_handle(handle)`: the retail base item's handle for an added item's handle (same colour);
  any other handle comes back unchanged.
- `clothing_retail_parts(parts, out, count)`: a Story hero's part array (38 words) with every added item
  replaced by its base item, as a save holds it.

**Item states.** The profile manager keeps one state set per item kind (`+0x14E4` hair, `+0x153C`
tattoos, `+0x1594` clothing, `+0x15EC` jewelry, `+0x1644` ...): a sorted array of keys
(`colour << 16 | handle`, built from the database by `sub_000151C0` for clothing) and 2 bits per key
(0 locked, 1 unlocked, 2-3 owned) in a fixed block of each profile slot, which saves hold. Added keys
would sort between retail ones and shift every retail state, and overflow the block. So the set keeps
only retail keys (`clothing_after_build`), and its methods (`sub_00017260` get, `sub_000173A0` set,
`sub_00017410` or-all, `sub_00017310` any, `sub_00017480` or, `sub_000174D0` clear, and the retail
cheats' `sub_000168E0` set-all) answer for added keys from a table in `clothing.c`, one per profile slot.
A new hero (`sub_00016240`) resets every set of its profile with set-all 0 after the slot setup; for
added items that puts back their starting state (owned in the wardrobe, unlocked in the shop) rather
than locking them, and a nonzero set-all (the cheats) is added to the starting state. Two of the originals would write through a `-1` index for a key they do not know.

The shop list builder (`sub_0004E650`) walks the database rows of one Type and asks the set for each,
so added rows appear in stores and in the Wardrobe without further changes. Names: a DisplayName string
that has text is shown as it is (retail names have none and go through the language's string table);
the string-table lookup (`sub_00045180`) is answered too, for the same names.

**Saves.** A profile row (`slot + 0x1788`, 0x5904 bytes) keeps the appearance in two 38-word part arrays,
at `+0x5558` (worn) and `+0x5618` (the creator's undo copy); clothing is parts 12-19. While
`sub_000D23B0` copies a row into a save (a synchronous `memcpy`), every added item there is its base item
with the same colour, and right after, the row is put back. `<data>/clothing-state/<profile>.txt` records
what was swapped (`worn <offset> <base handle> <key> <colour>`) and the items' changed states
(`state <key> <colour> <state>`, e.g. a bought shop item). When `sub_000156D0` loads a row, the next
front-end call restores: an added item comes back where the save still holds the recorded base handle
and its pack is enabled. Lines of packs that are not enabled are kept when the file is rewritten.

The file (`clothing-state-2`) is named after the profile, as the save is, and its second line,
`row <fingerprint>`, is FNV-1a 64 over the row as that save holds it (0x5904 bytes). A load copies the
save's row byte for byte, so the file is used only when the loaded row has that fingerprint: a hero
deleted and made again under the same name, or a save written by a build without the file, does not get
another save's items (the log says so). Saves made with no clothing pack enabled update the fingerprint
and keep the lines, so the items return when a pack is enabled again. `sub_000148B0` sets up a profile
slot, for a load and for a new hero (`sub_00016240`); the slot's added items start from their initial
states there.

Diagnostics: `RECOMP_CLOTHING_TRACE=1` logs the state calls answered for added items,
`RECOMP_CLOTHING_PROBE=1` the clothing state set and the clothing handles in the current profile row,
`RECOMP_CLOTHING_CACHE=<folder>` reads a compiled cache from another folder.

### Tests

`tests/unit/test_clothing.py`: the compiler's parts (painting keeps format, size and alpha; the
parts lines; variant codes; manifest checks; the digest), the mod manager's install/enable/disable/remove, a
layer served before clothing that already uses `Z01` and has its own catalogue lines, and a
native run of `clothing.c`, `pc_sod.c` and `pc_big.c` on a synthetic database, synthetic archives and
synthetic guest memory: the served files, the item states, the save swap and the reload, with the pack on
and off; a clothing file is not used for another save of the same name, and follows saves made with no
pack enabled.
