# Held UI review and lossless package compression — 2026-10-30

[Review exactly the 20 held textures](http://127.0.0.1:51763/held-review.html#overview). Open Inspect and use Draft to compare every saved attempt at 1×/3×/6×. Fifteen technical holds include generated candidates; five historical image-service blocks have no new generated draft and show original/published baseline only. All 1,328 accepted mappings remain approved. No new generation, production image edit, installation or publication occurred.

## Held set

| Count | Sources | Reason |
|---:|---|---|
| 8 | MAIN MENU, SELECT USER ID, CHOOSE VENUE, BEATBOX, HIGH SCORES, FIGHTER DESCRIPTION, CHOOSE TEAMS, EXTRAS | Separate black runtime source textures lost genuine opaque gray ink or changed it to transparency. Native layer/blend usage also needs validation. These are distinct source IDs from earlier approved ordinary headings. |
| 3 | Dark, layered and red venue symbols | Transparent ink/atlas gutters became filled plaques or contaminated coloured detail; irregular/repeated UVs require native reconstruction. |
| 1 | GAGNANT | Stamp interior opacity and a disconnected white source corner/gutter remain unresolved; complete source context is shown. |
| 1 | NO USER IDs | v1 adds paper, v2 has better transparency but bright red, v3 floods the interior with red alpha. Viewer defaults to v2, with all versions available. |
| 1 | I | Attempts added an outline, serif or bevel/coloured edge to a simple thin stroke. |
| 1 | Shared bitmap glyph page | Individual character positions/cells shifted. Visual similarity alone does not establish working native font UVs. |
| 5 | BARBER SHOP, TATTOO SHOP, RING OUT card, CREATE YOUR OWN FIGHTER, Bless | Earlier explicit image-service blocks; no new draft or retry. Published baselines retained. |

The focused viewer uses immutable existing source and candidate images, with held status and reasons beside each row. Browser checks: 20 cards/40 canvases; 72 revision/scale checks, no loading, console or horizontal overflow failures. Original ghost, bounds fit, four backdrops and the five no-draft filter were checked. Viewer and private proof/QA are separately pinned; no earlier review was overwritten.

## Compression already present

The native export path writes PNG with ordinary lossless compression: `scripts/export-menu-ui-pack.py` explicitly uses `optimize=False`; assembly/preview/widescreen scripts normally use Pillow's default save. Pillow's documented PNG compression default is level 6. The published 1.3 packaging script uses ZIP Deflate level 1; the general release builder uses level 6. No dedicated final PNG optimizer pass is present in those export/package paths.

Published 1.3 is 679,627,331 bytes zipped versus 683,803,577 bytes unpacked: ZIP saves only about 0.61% because PNG payloads are already compressed. The previously measured 641,883,992 bytes of queued previews is not the final native pack size. Use the owner's approximately 1 GB assumption only for discussion, not as a measured release size.

## Local lossless experiment

Pillow 12.3.0 / zlib 1.2.12 re-encoded 36 images in memory with `optimize=True` (compression level 9), retaining the original whenever re-encoding was larger. There were 12 evenly spaced file-size ranks per category, including extremes. This is a deliberately stratified test, not a population-weighted forecast. Approved queued previews are not final native atlases.

| Category | Input PNG bytes | Best PNG bytes | Reduction |
|---|---:|---:|---:|
| Published texture sample | 7,540,538 | 7,266,348 | 3.64% |
| Published widescreen/background sample | 23,040,061 | 21,752,980 | 5.59% |
| Approved queued preview sample | 9,136,436 | 8,815,811 | 3.51% |

All decoded RGBA bytes—including RGB under zero alpha—and dimensions were identical. Input file hashes were rechecked afterward; no source file changed. No sampled image had gamma/sRGB/chromaticity metadata requiring interpretation, and the benchmark would refuse those cases. The in-memory results were discarded after measurement.

Combined sample saving is 1,881,896 bytes / 4.74%; increasing Deflate level 1 to 9 on the existing encoded PNG files saved only another 11,994 bytes / 0.0303%. Per-file zlib measurements exclude ZIP container overhead. At an illustrative 1 GB and the same 4.74% rate, the saving would be about 47 MB. This is arithmetic illustration, not a full-pack or oxipng prediction. No oxipng executable was installed or benchmarked.

## Recommended release approach

1. Finish native atlas assembly first, with the intended texture sizes, UVs, edge guards and material alpha. Preserve approved full-resolution masters. Never resize, crop gutters or discard hidden RGB merely to save space.
2. Optimize a separate final staging copy losslessly. A pinned oxipng version at `-o 4 --strip safe` is a suitable starting point. Do not use `--alpha`: that option changes fully transparent RGB and can discard intentional edge bleed/data. Preserve colour-significant metadata; avoid blanket `--strip all`.
3. Demand exact decoded RGBA equality and identical dimensions for every output, including hidden RGB. Preserve original files if any check fails or the optimized file is larger. Run actual loader checks on Windows WIC and macOS/Linux stb decoding before publication, particularly if lossless colour-type reduction occurs.
4. Ship only runtime assets/manifest/provenance, avoiding raw references, review files and superseded versions. Reuse identical payload files where manifest semantics allow. Keep standard ZIP for the current updater; stronger ZIP is optional after measurement, with limited likely benefit. Do not introduce 7z/Zstd archive requirements just to chase small savings.
5. Calculate new file/archive SHA-256 hashes and regenerate the signed catalogue after optimization, under a new immutable version. Keep prior release URLs/bytes intact. Record exact optimizer/version/settings and encoded-file plus decoded-pixel checksums for reproducibility.

Lossless PNG optimization reduces download and installed file sizes, not texture dimensions or GPU residency: this loader decodes PNGs to four-channel pixels and builds mip chains. A smaller PNG can affect I/O/decoding work, but no game-load speed claim follows from this size test.

Do not use JPEG, lossy PNG palette quantization or BC/DXT conversion for the UI/font/stencil pack under a no-quality-change requirement. The current loader accepts PNG and classic BC1/BC2/BC3 DDS for ordinary replacements, with special padding limits; widescreen slabs must be PNG. It does not accept BC7/DX10 DDS, WebP, AVIF or KTX2. Supported BC formats still change colour/alpha precision and can damage fine UI edges. GPU compression is a separate future runtime/quality project, potentially useful for large opaque scenery or character materials; it needs format/platform support, suitable mipmaps and visual review.

The recommendation is to keep a single high-quality PNG pack, perform a verified lossless pass at final packaging, and measure the complete result before discussing a separate smaller-resolution edition. It is reasonable to expect modest savings; there is no evidence here for halving an already compressed approximately 1 GB pack without changing pixels.

## Primary references

- [W3C PNG specification](https://www.w3.org/TR/png-3/): lossless storage, alpha and colour metadata.
- [Pillow PNG save documentation](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png): default level 6 and optimize mode.
- [Oxipng documentation](https://github.com/oxipng/oxipng): lossless optimization levels, safe metadata stripping, and the explicitly potentially lossy `--alpha` option.
- [pngquant](https://pngquant.org/): explicitly lossy palette quantization, despite keeping a PNG extension.
- [Microsoft block compression formats](https://learn.microsoft.com/en-us/windows/win32/direct3d11/texture-block-compression-in-direct3d-11): block colour/alpha precision and format constraints.

Local loader compatibility: `docs/hd-textures.md` and `tools/xboxrecomp/src/nv2a/texture_pack.c`. Current installer ZIP support: `setup/mods.py`. Research and benchmark establish recommendations only; no production optimizer policy was changed this turn.
