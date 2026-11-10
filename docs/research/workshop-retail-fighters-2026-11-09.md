# Workshop retail fighter authoring and RGB atlases

The owner approved a private DMX pilot with a Memphis Bleek-compatible appearance,
Teck ordinary moveset/stats, supplied DMX voice and conditional DMX finisher/
intro/victory. A second outfit comes later. The companion Workshop branch adds
retail projects and a separate authoring studio; existing CAF contracts remain.

## Offline authoring API

`fighter-contract.py export-retail-appearance --game GAME --donor retail/NAME
--portrait-out NEW_DIRECTORY` reads the pinned original archive and exports its
model, texture and face members with hash descriptors and texture shape names.
The Workshop explicitly namespaces all owned texture shapes before compilation,
including shared-name injury variants. It does not mutate the original archive.

`preview-fighter --game GAME --pack FOLDER` inspects one ordinary fighter through
the semantic resolver, typed geometry, skin and texture readers. It returns
static positions/UVs/normals/triangles and RGB textures. Collapsed source surfaces
and unreferenced vertices are omitted from preview bounds only. Point/helper
materials remain labeled omissions. The private DMX source contains many collapsed
placeholders, including an all-equal surface at y=-1000; these are preserved in
the native source and compiler. Preview is neither a rig export nor native shader
or animation playback acceptance.

## Typed RGB appearance source

`eagl-appearance-png-1` extends appearance data with `images`, a mapping from
original four-character texture names to PNG hash descriptors. It retains
`donor`, `model`, `textures`, `face` and optional explicit `shape_names`.
All files are bounded and hash checked. PNGs are 32–2048px, at most 4 MiB each,
at native/2×/4× dimensions; aggregate decoding is bounded at 64 megapixels.

The original SHPX remains the control/layout authority. RGB is downsampled for
native fallback while material alpha is copied exactly from its decoded source.
Indexed fallback quantizes RGB independently per source alpha class and restores
Morton order. BGRA and supported linear DXT fallbacks use their original format;
the decoded alpha must match byte for byte. All opaque material controls remain
identical. Unknown formats/layouts and alpha drift fail before publication.
HD PNGs retain imported RGB and nearest original material alpha. Their XRTEX01
keys include the actual compiled native bytes and palette in canonical order.

Appearance HD images share the existing verified, content-addressed fighter HD
texture layer with UI artwork. For compatibility, the cache report key remains
`portrait_hd_files` and paths remain `fighter-ui-hd/`; these now include admitted
body rasters as well. Different sources for one native texture hash are refused.
Rig topology/permutation, skin bounds, render-template, texture ownership, facial
palette and full graph/context checks remain in force. No native C or toolkit
change, extra fixed game allocation or package-supplied code is introduced.

## Validation and limits

Invented fixtures cover indexed alpha-class quantization, exact original no-op,
HD source RGB/alpha, canonical texture IDs, invalid dimensions/hashes/shapes,
full appearance/template/namespace composition and HD layer generation. Existing
appearance, SHPX, UI, package and managed-launch tests remain applicable.

The private pilot's unchanged supplied DMX body/voice/paired/cinematic resources
compile with Teck inheritance. The source rigs have 94 bones with matching
topology/permutation but different bind transforms. The compiler preserves the
actual DMX transforms and graph identities. This is compilation evidence;
native result/finisher and current source qualification are recorded in the PR.
The original body texture remains a placeholder after two output-stage imagegen
refusals; generated UI candidates do not establish HD body restoration or owner
art approval. No art, native files, saves, captures or executable is published.
