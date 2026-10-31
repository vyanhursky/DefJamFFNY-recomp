# Combined HD Widescreen Menus 1.4.0 candidate — 2026-10-31

The owner approved all four final held revisions and requested the combined pack,
necessary PRs and exact total size before approving Cloudflare upload. All **1,343**
accepted menu/UI restoration mappings are included: 390 from published 1.3 and
953 additional mappings. Five explicitly accepted sources retain baseline artwork.
All existing widescreen scenery, map and repaired joins are retained. Faithful HD
is optional and is not bundled.

## Exact staged artifact

- ZIP: **601,895,156 bytes** (601.9 MB / 574.0 MiB).
- Unpacked: **605,772,797 bytes** (605.8 MB), 1,746 files.
- SHA-256: `f3d79f86a024b5786919ef2d6f38b1f599cb49a151d031b4a85023a5f480848d`.
- Root: `menu-ui-hd-wide-v1-4-0`.
- Private ZIP: `logs/menu-ui-v1.4/publication/menu-ui-hd-wide-v1.4.0.zip`.
- Native mappings: 1,522; widescreen registrations: 80; PNGs: 1,744.
- Source summary: `config/menu-ui-v1.4-candidate-2026-10-31.json`.

The combined ZIP is 77,732,175 bytes smaller than published 1.3 while adding all
953 accepted mappings. This is the actual complete package, not a sum of preview
crop sizes. Upload has **not** occurred. The content-addressed Cloudflare plan is
private and awaits owner approval of this exact size/hash.

## Native assembly and lossless encoding

953 newly approved mappings resolve to 812 logical masters and 963 native atlas
exports, including ten supporting context atlases. Forty mappings are new to the
pack manifest. Every export has its original 4× native dimensions. Two review
references were already 4× and correctly retain their existing replacement size.

193 logical multi-material artworks are rendered once and then split using the
verified source rectangles. The exported sampled regions reproduce their common
master's visible RGBA exactly. Complete-master context adoption is explicit in
the source records, including GAGNANT; its independent white corner is preserved.
Original fractional quad/UV offsets are retained by the game. Integer registered
canvas checks do not claim pixel-identical rendering for every fractional overlap;
CORRUPT ID's inherited half-texel overlap remains documented in source provenance.

95 glyphs are individually registered in their original page cells and baselines.
4,528 HD texels of proven opaque RGB127 runtime markings are protected. The three
venue badges use their decoded sampled prefixes plus clamped guards in full
native canvases. No pure-neon green contamination was found in the 963 exports.
Parent inspected the registered font, protected layers, venue badges and native
capture contacts. No new image generation was required for assembly.

All 1,744 packaged PNGs have verified exact decoded RGBA, including hidden RGB,
and exact non-IDAT metadata through lossless optimization. Newly assembled PNGs
saved 11,884,409 bytes (9.88%); 781 unchanged PNGs reuse the earlier verified cache.
Across the complete final pack, PNG bytes fell from 715,434,318 to 603,774,586,
saving **111,659,732 bytes (15.61%)**. Raw imagegen masters remain immutable.
The exact final ZIP passed CRC checks and the unchanged released 0.12.1 installer.
An isolated released-helper test installed local 1.3 against the live signed index,
updated to the exact 1.4 payload using an explicit in-memory unsigned future-index
fixture, verified all installed/backup hashes and rolled back to 1.3. Its save marker
remained exact. This proves payload/update/rollback compatibility, not production
trusted-network 1.4 publication; that check follows approved upload.

## Native validation

Six serial isolated runs used the **exact ZIP-extracted artifact**. All restored
the complete save root byte-identically and had no measured runtime faults or
permanent texture replacement rejections. Across runs, trace confirms
420 distinct replacements loaded, including 290 newly
approved mapping IDs; this is representative coverage, not all 953 sources.

| Route | Aspect | Captures | Log |
|---|---|---:|---|
| front | 16:9 | 5 | `run-20261030-234116.log.err` |
| battle | 16:9 | 10 | `run-20261030-234410.log.err` |
| ffa | 16:9 | 6 | `run-20261030-234545.log.err` |
| front | 4:3 | 5 | `run-20261030-234737.log.err` |
| front | 32:9 | 5 | `run-20261030-234855.log.err` |
| story | 16:9 | 4 | `run-20261031-000700.log.err` |

Total: 35 native captures. The front route covers Main Menu, Options,
Beatbox and High Scores; battle/FFA cover match selection, fighter/venue menus,
loading and fight start. The Story fixture reaches Crib, the map screen and Gym.
Two initial Story attempts selected fresh profiles and reached character creation;
they missed the requested gym anchor, restored saves and are retained separately.
The corrected fixture selects VY2 explicitly. A successful route was repeated to
fix the capture schedule's Map anchor; no pack pixels changed between runs.

Limits: these routes do not visit every source, language or loading-banner variant.
Some loading captures show the LOADING interstitial or transition black frames.
The inherited SELECT USER ID title on fighter select was previously reproduced
unmodded; this data pack does not change game code. Native run receipts and captures
are private under `logs/menu-ui-v1.4/`; the source ledger pins their provenance.

## PRs, compatibility and publication handoff

- [Game source records PR152](https://github.com/vyanhursky/DefJamFFNY-recomp/pull/152).
- [Native registration/compression Tools PR1](https://github.com/vyanhursky/DefJam-Modding-Tools/pull/1): 88 tests / 12 subtests, wheel and source policy pass; macOS, Windows and Linux CI green.
- [Draft catalogue PR9](https://github.com/vyanhursky/DefJamFFNY-mods/pull/9): append-only metadata; 14 tests and CI pass; do not merge/publish before upload approval.

All PRs use the owner's v0.12.2 milestone. The game milestone is already closed;
its existing PR assignment is preserved. No game/runtime code or version bump is
needed for this pack. It loads on **0.12.1 without reinstalling the game** using
`textures-v1` / `wide-v1`; update the mod through the launcher and restart the game
once its catalogue entry is published.

Current signed catalogue revision 8 was verified with the existing public
key. All historical versions and unrelated mod entries are preserved. Local
revision 9 is an **unsigned preview**, not a published index. At actual
publication, refetch the live index and derive the next revision again.

After the owner approves this exact artifact: upload it at its immutable
content-addressed key, verify public size/hash, complete protected download/archive/
malware gates, merge the catalogue metadata and publish the signed index. Do not
reuse old release signatures or change earlier versions. Source and artwork
recovery is pinned separately in `config/menu-ui-v1.4-checkpoint-2026-10-31.json`.
