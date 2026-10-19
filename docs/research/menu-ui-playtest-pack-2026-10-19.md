# Menu/UI source-shaped playtest pack (Mac), 2026-10-19

First playable delivery from [the handover](../menu-ui-modpack-handover.md): the approved menu
artwork exported as sparse, source-shaped schema-1 PNG packs for the existing loader, on a Mac
build of v0.10.4 (`110d50e` merged into this branch, toolkit `32aab4d`). No new artwork, no
runtime or loader change, nothing installed into an existing game install. True widescreen
scenery is **not** in this pack (see Gaps).

## What was built

| Component (local, `<playtest-data>/mods/`) | IDs | Status |
|---|---|---|
| `menu-ui-restored-test-v1` | 39 | Owner-approved artwork (D128/UI–D156/UI) |
| `menu-ui-mode-conditional-test-v1` | 8 | Mode Select, conditionally approved (D132/UI); separate so it can be turned off on its own |

- Mapping: `config/menu-ui-source-shaped-exports.json` (source ID, approved artwork path, crop),
  hashes only. Export: `scripts/export-menu-ui-pack.py` refuses unpinned artwork, a second export
  of one ID, non-uniform or out-of-range scale, and an existing pack folder (packs are immutable).
  Each component has a `receipt.json` with input pins, crops and output SHA-256.
- All 47 exports are exactly 4× their source texture. Before export each was box-reduced to 1×
  and compared with the Faithful HD tile of the same ID: RGB mean difference 0.0–3.2 (of 255),
  alpha 0.00–0.02, which confirms tile order, crop and alpha registration.
- Title city/tower and the four Mode layers are split from the approved 4× mosaics using
  `batch2/references.json` tile order (`[6|5]`, `[11|10]`, `[14|13]`, `[5|4]`, `[18/17]`,
  `[53|52]`); the other 35 are the approved source-shaped tile files unchanged.
- Mip policy `opacity`, as the Faithful HD component that held these IDs. Pack order:
  faithful opacity; faithful channels; menu restored; menu Mode (last wins).

## Runtime evidence (Mac Vulkan, `RECOMP_TEXTURE_TRACE=1`)

Harness `two-matches` and `unlock` with the four packs, native captures, save guard restored
identical. 29 of the 47 IDs were uploaded from the new packs, each with result 1 (loaded):
title city/tower (4), all 8 Mode Select, Battle setup (2), 2- and 4-fighter select (4), rematch
(1), 2- and 4-player results papers (8), Rewards/Unlock wall (2). Unlock Fighters capture reviewed:
wall drawn, no seams/alpha faults. Not visited by any scripted route, so unproven at runtime:
Options (3), Jukebox (2), High Scores (2), 3-fighter select (2), 1- and 3-player results (8),
reward earned (1). They use the same identity scheme as the 29 that hit and as the Faithful HD
pack that already replaces them, so a miss would be surprising; the playtest should confirm.

`unlock` passed. `two-matches` reached its end with 0 crashes/watchdogs but reported one
`[ICALL] target 0x80003344 is not code` at log line 859, while `entity.xml` loads during boot,
before any menu texture is requested. Texture packs are host-side, so this is not expected to be
caused by the pack; another game run was active on the same Mac at the time (AGENTS.md says
runs are serial), and it was not re-run. Logs: `logs/run-20261019-153015.log.err`,
`logs/run-20261019-154012.log.err` (local).

## Playtest

```bash
/Users/vlad/Code/defjam-data/playtest-menu-ui/play.sh            # menu packs on
/Users/vlad/Code/defjam-data/playtest-menu-ui/play.sh faithful   # compare: Faithful HD only
/Users/vlad/Code/defjam-data/playtest-menu-ui/play.sh nomode     # menu packs without Mode Select
/Users/vlad/Code/defjam-data/playtest-menu-ui/play.sh original   # no packs
```

The playtest data folder holds its own `settings.ini` (packs on, `render_scale = 4`, 1440×1080
window, `aspect = 4:3`, `skip_intro = true`, brightness 100, vignette defaults), a clone of a
save, its own shader cache and logs; the Faithful HD components are symlinks to the existing
install's immutable packs. Rollback: run `faithful`, or remove the two menu names from `packs`.

Checklist: Press Start city/tower (skyline and logo are still Faithful HD), Mode Select spotlight,
door, selection and the right 4:3 border (D132/UI condition), Options scroll, Jukebox strip,
Battle setup, 2/3/4-fighter select, Rewards/Unlock Fighters/Unlock Venues, High Scores live
text, rematch, 1–4 player results and reward earned papers.

## Gaps and issues

1. **Retained Faithful HD (24 of 71 IDs).** Title logo and the 21 emblem tiles: approved
   repaired canvases are not native-shaped and need registration (handover blocker). Title
   skyline (2): only the wide master/art-space crops are approved, no source-shaped tile.
2. **No widescreen scenery.** In 16:9 and wider the game keeps menus 4:3 with the existing
   blur/black side fill; the approved wide masters are not drawn. That is the separate
   engineering stage in the handover (layer extension with matching motion/masks, explicit
   fallback), not started.
3. **Mode Select condition** cannot be judged fully here: it is about the wide composition's
   right 4:3 border; the source-shaped pack shows only the 4:3 centre.
4. 18 IDs not yet seen at runtime (above). Windows D3D11 and Deck not run.
