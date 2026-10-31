# HD Widescreen Menus 1.3.0 publication — 2026-10-28

Published the accepted text reconstruction work to Cloudflare R2 and signed catalogue revision **7**. The package replaces **390 source-specific menu/UI mappings** with the accepted image-generated revisions, including **178 additional texture mappings**. It preserves all **80 widescreen entries** and **1,314 nonmetadata files** from 1.2 byte-for-byte. The cumulative pack has **1,482 native texture mappings**, **1,704 PNGs** and **1,706 files**.

## Install and compatibility

On **game 0.12.1 or newer**, refresh the catalogue in Mods, update **HD Widescreen Menus**, then restart the game. No game reinstall is needed. The released 0.12.1 installer and catalogue helper are unchanged and were checked byte-for-byte against the tag. A real network update in a disposable data root moved 1.2.0 to 1.3.0, verified every installed file and the complete rollback copy, and retained the save marker. Rollback restored all 1528 files of 1.2.0 exactly. This did not touch the player's installation.

## Immutable artifact and publication

- [Catalogue PR #7](https://github.com/vyanhursky/DefJamFFNY-mods/pull/7), merged as `f90ead0defc98d8010a06d82a8fcd9b56a133356`; milestone **v0.12.2**.
- [Protected publication](https://github.com/vyanhursky/DefJamFFNY-mods/actions/runs/40815588169), normal append-only publication with bootstrap false, download/content checks and ClamAV.
- [Download 1.3.0](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/menu-ui-hd-wide/1.3.0/82ad6d53f3161b612110cdd84e3f9d0bde2f517a9a9f6410f9e52afcf963de24/menu-ui-hd-wide-v1.3.0.zip): **679,627,331 bytes**, SHA-256 `82ad6d53f3161b612110cdd84e3f9d0bde2f517a9a9f6410f9e52afcf963de24`. Full public download and HTTP range verification passed.
- [Signed catalogue](https://vyanhursky.github.io/DefJamFFNY-mods/index.json): revision **7**, SHA-256 `c4e7aecfaad7daa7319788f9d338a9c1f509ac558fe9342b131cb8deb5e6183a`. Ed25519 signature verified with the unchanged reviewed key; earlier version records are preserved.

## Selection and assembly

The selection comprises 377 distinct mappings from five formal approval sets, 12 earlier family drafts accepted for expansion, and the separately accepted Continue revision. Later accepted corrections supersede earlier versions of the same source. Main Menu v6, Capone v3 and Continue v3 retain their accepted native-pilot atlases exactly. Each source keeps its full original atlas/UV canvas at 4×. Visible alpha bounds are fitted to their source-specific target, with measured deltas of 0–3 output pixels. Existing bleed only replaces low-coverage matte RGB; alpha and RGB above alpha16 remain exact. All 390 final atlases pass bounded near-pure green checks. Original source-boundary contact is retained; one near-boundary N.O.R.E. 3p soft feather reaches alpha60 beyond the canvas, while its alpha128 body fits. No game sampler or renderer changes were made.

The last 60 four-fighter banner variants were awaiting review when this archive was frozen. Vlad subsequently approved all 60; their exact hashes are recorded in `config/menu-ui-reconstruction-wave06-approval-2026-10-28.json` for the next pack update. Wave seven is also separate. Uploaded immutable 1.3 bytes were not rewritten.

## Native evidence and limits

Six serial save-guarded routes produced **39 captures**, with no measured runtime faults and byte-identical save restoration: 16:9 front end, battle, four-fighter, Capone selection; 4:3 battle; and 32:9 front end. The corrected experimental aspect setting produced actual **5120×1440** captures; a first short enum attempt fell back to 16:9 and is explicitly excluded from ultrawide evidence. Main Menu, Continue, options, labels and Capone/Method Man select placement were inspected. The 4:3 venue/map and wider menu coverage retain their existing behavior.

Loading captures show the LOADING interstitial and do not prove in-game coverage of every light-name variant. Those source-specific atlases passed visual, hash and bounds checks; 3p/4p variants were not individually driven in-game. The inherited SELECT USER ID heading on the choose-fighter route was previously reproduced unmodded. This release does not fix that game behavior, remaining UI families, fighter portrait fringes, runtime-generated text, or the separate fire-escape geometry issue (game PR #131).

## Recovery and hand-off

`config/menu-ui-v1.3-release.json` pins the artifact, approval sources, every transformed atlas, native captures and managed update/rollback receipts. The private publication checkpoint is pinned by `config/menu-ui-v1.3-checkpoint-2026-10-28.json`; no artwork, game data, save files, binaries or signing credentials enter Git. Continue the next 50 labels/music drafts in `logs/menu-ui-wave07-20261028/`; all source/output requests and failed calls remain local. Future PRs belong to v0.12.2.
