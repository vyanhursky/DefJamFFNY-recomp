# Project site

The GitHub Pages site for the port: plain HTML, CSS and JavaScript with no build
step of its own. It is served at `https://vyanhursky.github.io/DefJamFFNY-recomp/`.

| File | Holds |
|---|---|
| `index.html` | All the copy and structure: hero, features, screens, install, mods, news, roadmap and docs, FAQ, community, footer. |
| `styles.css` | The look. Colours and fonts are variables at the top. |
| `hd-menus-ui/` | Menu/UI page: nine before/after sliders, an ultrawide showcase, coverage, installation and credits. |
| `hd-fighters/` | Dedicated HD Fighters page: eight interactive before/after comparisons, coverage, installation and credits. |
| `app.js` | Live details: the latest release line, the download button for the visitor's OS, the news list and the before/after sliders. The page still works without it. |

## Images

This folder holds text only; `scripts/check-source-tree.py` refuses image and video files
outside the approved set. `scripts/build-site.py` copies the pictures in when the site is
built, from the files already approved for publication (the README media, D58/D144, and the
branding set, D98), and checks each one against its pinned SHA-256 first. Its `MEDIA` table
maps each published name under `media/` to its source; `tests/unit/test_build_site.py`
checks that the page only refers to names in that table.

A new picture needs the owner's approval and a fingerprint, like any README media: add it to
`docs/media/` and the allowlist in `scripts/check-source-tree.py`, then add a line to `MEDIA`.

A slider is a pair: a 16:9 after picture and a 4:3 before picture, of the same moment.

## Preview

```sh
python scripts/build-site.py
python -m http.server --directory build/site 8000
```

Then open `http://localhost:8000`. The release line and news load live from the GitHub API.
When the API is unavailable, the page reads `releases.json`, which the deploy writes with
`--releases`.

## Publishing

`.github/workflows/pages.yml` builds and deploys the site when a stable (not pre-release)
release is published, and on demand from the Actions tab (**Pages → Run workflow**). Betas never
deploy it. The site goes live with stable v1.0.0, so `pages.yml` must be on the commit that release
is tagged from. Before that first deploy, enable Pages once: **Settings → Pages → Build and
deployment → Source: GitHub Actions**.

The release line, download buttons and news follow the latest stable release by themselves. Feature
copy, the FAQ and the roadmap are written by hand: update them when a release changes what the
port does.

## Proposed captures

Pending the owner's approval. None of these exist yet; each would be captured from a tagged
release, reviewed, then pinned as described under **Images**.

| Priority | Shot | Where it goes | Why |
|---|---|---|---|
| 1 | A second venue in daylight or a bright club, 16:9, HD | Screens | Every current gameplay shot is the dark Basement. |
| 1 | Steam Deck in Gaming Mode, 16:10 | Screens, Linux install card | Platform claim with no picture today. |
| 2 | Four-fighter free-for-all | Features card 08 or Screens | Local multiplayer; caption only what the capture proves. |
| 2 | Created fighter in the Sketch Artist or crib | Screens | Story mode beyond versus fights, and the v0.12.1 fixes. |
| 3 | A short loop of a grapple or Blazin' move, 16:9 | Hero reel | Replaces the face-off clip with a signature moment. |
| 3 | Windows capture of the same fight frame | Screens fine print | All captures are Mac today. |

## HD Fighters subpage

`hd-fighters/index.html`, `fighters.css` and `fighters.js` publish at
`https://vyanhursky.github.io/DefJamFFNY-recomp/hd-fighters/` through the same
build and Pages workflow. The home page links to it from Mods. It is static
presentation only; no Workshop, game loader or catalogue behavior is involved.

The copy mirrors the owner's published Thunderstore README as of November 12,
2026. Update it deliberately when that copy changes; it does not scrape the
storefront at runtime. The extra static-preview caption distinguishes these
original-mesh studies from in-game shader or animation captures.

The eight approved screenshots are hosted externally under
`https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighters/screenshots/1.0.2/`.
No new image bytes are tracked or copied into the Pages artifact. Each slider
uses two SVG viewports of its single hosted JPEG: the original panel underneath
the left-hand clip, and the restored panel underneath the right. Moving the
native range control only changes that clip; it does not stretch the clipped
layer, recolor pixels, or generate intermediate details. Both sides share the
same displayed crop dimensions.

All source JPEGs are 1920×1080. The first three use original/restored viewboxes
`63 341 884 559` / `974 341 884 559`; the remaining five use
`49 310 893 646` / `978 310 893 646`. These remove poster headings and viewer
controls without adding new texture art. Original, 50/50 and HD-only buttons,
arrow keys/Home/End and pointer dragging control each comparison independently.
The static split and links to the source comparisons remain without JavaScript.

Approved hosted image fingerprints (SHA-256):

| Image | SHA-256 |
|---|---|
| `01-ludacris.jpg` | `61e526a668626a22fda879069ff1240539da78ff2ec8c196b1437fdb120e4ea7` |
| `02-danny-trejo.jpg` | `4fa46d100e38357fcf45f40790a9daebc7a90fd95034ee5dd6a6683450d27078` |
| `03-nyne.jpg` | `fc51b490b894fef69680be8f29e843711a0f8d62e76d75397dc7fbdb388dc549` |
| `04-henry-rollins.jpg` | `868676771d1ec8252275afa41a80e912436b55be537af5fcff94ef0d37248abe` |
| `05-elephant-man.jpg` | `97169f20f421c187e8b5019987a1df7a3ee93056e0143c0011149514cbd5ce38` |
| `06-oe.jpg` | `fb6393ad7940a7a7d4b7f73ec39a4f39e180ea29094291d6c749d42ed4340589` |
| `07-erick-sermon.jpg` | `094a377660ad8b890c74a571ec277a7454104ecffd206bc57b0042095b60a0f4` |
| `08-masa.jpg` | `ad231e7b5fb97cb02466f3e6fae9a69f2caef511389ea49d1d32a2cf643544ec` |

## HD Widescreen Menus and UI subpage

`hd-menus-ui/` publishes through the same build and Pages workflow. The home Mods section links to it. Copy is a deliberate snapshot of the owner-published Thunderstore README on November 13, 2026, with the measured 1.7.2 wrapper download size added. The signed catalogue compatibility hold remains explicit; this page does not publish catalogue changes.

Nine owner-approved before/after boards are hosted externally under `https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/menu-ui-hd-wide/screenshots/1.7.2/`. Each SVG pair has matching dimensions derived from the selected source crop and its display scale inside the 850×680 evidence panel. Redundant preview margins are removed symmetrically; portrait tiles retain horizontal context. The exact viewports within each 1920×1080 JPEG are listed below. These rectangles stay inside the evidence panels; no art is regenerated or stretched while moving the clip. The separate supplied PNG collage retains its native aspect and is never treated as an aligned before/after pair. No new image bytes enter Git or the Pages artifact.

Original, 50/50 and HD presets, pointer dragging and native range keyboard controls mirror the HD Fighters page. Hosted fingerprints:

| Image | SHA-256 |
|---|---|
| `01-widescreen-menu-layouts.png` | `52f40f686a0d50d49ef9010bb10f896ea3eabc042bc9720cd268fe1b6416ee3d` |
| `02-fighter-select-brick-wall.jpg` | `42a0dc6b4c612411b0e71777bd979500768c0e86c00906d8cb74833004388756` |
| `03-main-menu-poster-wall.jpg` | `0bda2e61d9cabd01f84713bc9ed8626197320f3a6471e815db67ea4ff19c147b` |
| `04-wrestling.jpg` | `7748b1d08bd667880127a4ca6e0eff570e6724f9f4570f3e562155fb0b01ffc2` |
| `05-winner.jpg` | `18559d3ddf0f05ff6534fb47f4871f3251e2582f13e63f48cb4459c705f9d2e0` |
| `06-venue-label-club-dtp.jpg` | `c546c3d3b394cdb340fe4d6ca56b0c885473a6c67616b0e419345f78c5088b07` |
| `07-venue-emblem-70.jpg` | `b5afd69c50e209e436308fd0129574ebe19e1ce6e8ea29a4a2d0a87848849b58` |
| `08-method-man-as-blaze-loading.jpg` | `bf7c68d3a857ef363ae574a45974bddec31786208c08b57a404b124e7a89612b` |
| `09-d-mob-loading.jpg` | `349857f0ff267643ca1ff7094fbb146f17241637716bbe32de76b41b0f5cb0bf` |
| `10-busta-rhymes-as-magic-loading.jpg` | `d820a2ef160e7d54a7f1cf72d19dae78fbdfd194e5ba86fbc6d7d74143840b36` |
| `nine-comparisons.jpg` | `4b78645564dd0c2a263fb5fa60121c3f1005919f2443f7f2290f3eb9bf36079c` |

Comparison viewports (`x y width height`):

| Image | Original | HD |
|---|---|---|
| `02-fighter-select-brick-wall.jpg` | `154 255 680 680` | `1086 255 680 680` |
| `03-main-menu-poster-wall.jpg` | `69 255 850 680` | `1001 255 850 680` |
| `04-wrestling.jpg` | `69 445 850 300` | `1001 445 850 300` |
| `05-winner.jpg` | `69 345 850 500` | `1001 345 850 500` |
| `06-venue-label-club-dtp.jpg` | `69 445 850 300` | `1001 445 850 300` |
| `07-venue-emblem-70.jpg` | `69 255 850 680` | `1001 255 850 680` |
| `08-method-man-as-blaze-loading.jpg` | `69 382 850 425` | `1001 382 850 425` |
| `09-d-mob-loading.jpg` | `69 437 850 315` | `1001 437 850 315` |
| `10-busta-rhymes-as-magic-loading.jpg` | `69 394 850 402` | `1001 394 850 402` |
