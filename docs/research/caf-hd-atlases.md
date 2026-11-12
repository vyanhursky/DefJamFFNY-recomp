# CAF HD atlas contract

The one CAF recipe format, `caf-fighter-1`, accepts complete square 256, 512,
1024 or 2048px PNGs for A/B/C/D/D1/D2. Keep the original UV layout. PNG alpha
does not replace the native compositor's material channel. HD is not a separate
format version: it is part of the recipe's optional atlas section. No Story
profile bytes change.

The compiler retains full-resolution RGB in the `hd` section of the hash-sealed
`fighter-caf.bin` container and
creates a 256px RGB fallback with Lanczos filtering, independently of input
alpha. Native CAF construction and guest allocations stay at 256px. After
construction, the adapter copies the live native material alpha to the HD raster
with nearest sampling. This covers normal and injury face variants.

The renderer extension registers the HD raster by its exact live guest pixel
address, format and dimensions, owned by the CAF visual. The adapter uses
the existing kernel RAM-mirror naming function to match the GPU DMA address;
a CPU heap address is not the same identifier. The native texture
registration references that buffer directly. Ordinary content-hash packs keep
their existing behavior. Replacements use the existing texture-pack mip builder,
GPU uploader, LRU and configured cache budget; material channels receive
independent-channel mips. No guest or global texture-cache limit is increased.
An owner clears registrations before the native visual can be freed or reused.
This avoids global hash aliases between unrelated fighters or outfits.

The hd section has one 32-byte row per outfit (layout in `setup/fighter_caf_layout.py`):
logical selection, outfit index, six block offsets counted from the section start.
A block is one edge word plus tightly packed BGRA pixels. Equal blocks are
deduplicated. Rows must bind to declared CAF recipes, block offsets must point to
exact contiguous block starts, and every block must be referenced. The hd section is limited to 128 MiB. The renderer admits 32 live owned
sources and at most 256 MiB of prepared host pixels, while retaining its existing
GPU budget and native fallback on GPU upload pressure. Registration failure is
explicit. Full 2048px wardrobes may exceed the compiled budget; use 1024px where
that is sufficient. These are bounded import/resource checks, not a larger game
memory configuration.

Validation distinguishes synthetic compiler/reader/renderer fixtures from native
visual acceptance. A successful package export does not establish in-game
appearance, four-player performance or platform-specific GPU qualification.
