# Project site

The GitHub Pages site for the port: plain HTML, CSS and JavaScript with no build
step of its own. It is served at `https://vyanhursky.github.io/DefJamFFNY-recomp/`.

| File | Holds |
|---|---|
| `index.html` | All the copy and structure: hero, features, screens, install, mods, news, roadmap and docs, FAQ, community, footer. |
| `styles.css` | The look. Colours and fonts are variables at the top. |
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
