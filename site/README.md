# Project site

The GitHub Pages site for the port: plain HTML, CSS and JavaScript with no build
step of its own. It is served at `https://vyanhursky.github.io/DefJamFFNY-recomp/`.

| File | Holds |
|---|---|
| `index.html` | All the copy and structure: hero, features, screens, install, mods, news, roadmap and docs, FAQ, community, footer. |
| `styles.css` | The look. Colours and fonts are variables at the top. |
| `hd-fighter-portraits/` | Portrait page: 17 before/after sliders for full-body compositions, heads and roster textures. |
| `hd-menus-ui/` | Menu/UI page: nine before/after sliders, an ultrawide showcase, coverage, installation and credits. |
| `hd-fighters/` | Dedicated HD Fighters page: eight interactive before/after comparisons, coverage, installation and credits. |
| `hd-textures/` | Draft customization page: selectable Original/Medium/High/Ultra comparisons, slider or hold controls, reference triptychs and quality guidance. |
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

## HD Textures draft

`hd-textures/` follows the existing static Pages build. It is intentionally not
linked from the home page until release media and runtime compatibility are
finalized. The checked-in `comparisons.json` is an empty draft; private review
previews supply native captures separately. Do not commit those captures or
machine-specific review selections.

The data file supplies `packages` (quality keys to released download URLs),
`comparisons` and `references`. A comparison has a title, caption, full capture
width/height, four `variants` (`original`, `medium`, `high`, `ultra`) and named
`crops` as `[x, y, width, height]`. Both SVG layers use the same crop; the control
changes clipping only. Captures must use matching render settings, and captions
must disclose pose or framing differences. A reference case supplies title,
caption and `original`, `ultra`, `reference` image URLs. Host owner-selected media
externally and record its provenance and fingerprints before publication.

High (3× PNG) is recommended; Medium is 2× and Ultra is 4×. Either side is
selectable. Hold mode supports pointer, Space and Enter, returning to A on
release, cancellation, lost capture, focus loss or a hidden page. Slider mode
retains native range keyboard controls. Empty draft data hides download links
and displays preparation text rather than implying a published release.

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


## HD Fighter Portraits subpage

`hd-fighter-portraits/` publishes through the existing build/Pages workflow. The
home Mods section links to its 17 owner-approved comparisons: seven complete
full-body compositions and ten head/roster textures. B04 and B06 were explicitly
excluded from the promotional selection. No image bytes are tracked here.

Full-body boards use the original ELF quad/UV translation geometry and exact
published native PNG fragments; head boards show native textures directly.
These are offline comparisons, not captures of gameplay. Both SVG layers sample
the same hosted 1920×1080 JPEG with matching crop dimensions; range controls
change clipping only. Original/50–50/HD presets, keyboard controls and pointer
dragging use the established Menus/Fighters interaction.

Copy reflects the approved portrait release and November 15, 2026 storefront
preparation: 2,184 native PNGs, 1,334 Select/Story-family textures plus 850 loading
textures across 294 layouts, all at 4× native dimensions. The live 1.0.1 download
remains the page's primary package link until a Thunderstore listing is verified.
This page does not publish or change the signed mod catalogue.

Hosted source images and viewports (`x y width height`):

| ID | URL | SHA-256 | Original viewport | HD viewport |
|---|---|---|---|---|
| B07 | [01-b07-full-body.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/01-b07-full-body.jpg) | `d22e4bf78a1ab968dba74b8e138c2e1f6cdbdee52d8579113c52ba89084d7718` | `277 274 409 666` | `1233 274 409 666` |
| B08 | [02-b08-full-body.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/02-b08-full-body.jpg) | `78df849480476658071b763e466ec91374e24de030c9e246e74aade02461c7f4` | `264 274 436 666` | `1220 274 436 666` |
| B09 | [03-b09-full-body.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/03-b09-full-body.jpg) | `555257f25f7358cbe6931d974c2e2c14bc205803c9ceb59966771f12d5a38d3c` | `328 274 307 666` | `1284 274 307 666` |
| B01 | [04-b01-full-body.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/04-b01-full-body.jpg) | `0e75761e2e0156c333416f062cfac0953ea732a1cbeff7c3d01632f510ca19d7` | `297 274 369 666` | `1253 274 369 666` |
| B02 | [05-b02-full-body.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/05-b02-full-body.jpg) | `4fda0d2e465213e8fdc17d93a8b24bff72ac6fe88dfaca76b23ec6b21b0337cb` | `297 274 369 666` | `1253 274 369 666` |
| B03 | [06-b03-full-body.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/06-b03-full-body.jpg) | `68ea9df000f0b5dc47f39d604055d8631e566a88bf215c5a493479e66b154df9` | `302 274 359 666` | `1258 274 359 666` |
| B05 | [07-b05-full-body.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/07-b05-full-body.jpg) | `abdeaaf658b53c57ffa2ebc3e9fcd34142283191081a2129c8668ada7f7f8881` | `313 274 338 666` | `1269 274 338 666` |
| P01 | [08-p01-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/08-p01-head.jpg) | `9d510768c4450f2b5af601e95ebf08b8e9e53fc14fd169c53dad536d5f386c3a` | `172 288 620 620` | `1128 288 620 620` |
| P02 | [09-p02-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/09-p02-head.jpg) | `f3de9b13ee7711dc676d4d72f79e5a628edc57571adac6a1d53e18dcf251bc23` | `172 288 620 620` | `1128 288 620 620` |
| P03 | [10-p03-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/10-p03-head.jpg) | `4eb11b8eb442141e2495f01e10d40661b17a90befa84457b9d9bf18da785c835` | `172 288 620 620` | `1128 288 620 620` |
| P04 | [11-p04-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/11-p04-head.jpg) | `772d883f229c6e16685c9f30caf2bf2b1f9c06f49c0c5bfb0404c26adc5933ba` | `172 288 620 620` | `1128 288 620 620` |
| P05 | [12-p05-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/12-p05-head.jpg) | `db3c3af1feb07f31915d1915087935885c2b25850449efec69028d9ef8155bb0` | `172 288 620 620` | `1128 288 620 620` |
| P06 | [13-p06-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/13-p06-head.jpg) | `d4371a1ee3fb3e7764f47e2ab9fc62854cc79b44f32058817bdb1227590d312d` | `172 288 620 620` | `1128 288 620 620` |
| P07 | [14-p07-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/14-p07-head.jpg) | `b2b54040816e2e79dbf4a4256b1d5c241f0b3bd82b794c74eb52ec399a209c9c` | `172 288 620 620` | `1128 288 620 620` |
| P08 | [15-p08-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/15-p08-head.jpg) | `f668885f9f2fa88def4ce3515d9d6c3ab2d88352f4dfe71a9cefd3eb8fcf2dba` | `172 288 620 620` | `1128 288 620 620` |
| P09 | [16-p09-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/16-p09-head.jpg) | `382659da2714e19b1c50374dabdbff5c0bcfa3a25d55690a5f9f7e296ae75fd3` | `172 288 620 620` | `1128 288 620 620` |
| P10 | [17-p10-head.jpg](https://pub-9167b11f83f24f2a9e21af7f0e225057.r2.dev/hd-fighter-portraits/screenshots/1.0.2/approved-20261115/17-p10-head.jpg) | `81be6ee2378a39b88bed79c79b89d9423570f1caf9d566c923549ae2d6c1f03a` | `172 288 620 620` | `1128 288 620 620` |
