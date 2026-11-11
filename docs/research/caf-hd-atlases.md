# CAF HD atlas contract

`caf-fighter-7` accepts complete square 256, 512, 1024 or 2048px PNGs for
A/B/C/D/D1/D2. Keep the original UV layout. PNG alpha does not replace the
native compositor's material channel. Earlier CAF formats retain their native
256px restriction. The v7 recipe otherwise supports the v6 face, outfit,
moveset and performance fields; no Story profile bytes change.

The compiler retains full-resolution RGB in a hash-sealed FCH1 companion and
creates a 256px RGB fallback with Lanczos filtering, independently of input
alpha. Native CAF construction and guest allocations stay at 256px. After
construction, the adapter copies the live native material alpha to the HD raster
with nearest sampling. This covers normal and injury face variants.

The renderer extension registers the HD raster by its exact live guest pixel
address, format and dimensions, owned by the CAF visual. The native texture
registration references that buffer directly. Ordinary content-hash packs keep
their existing behavior. Replacements use the existing texture-pack mip builder,
GPU uploader, LRU and configured cache budget; material channels receive
independent-channel mips. No guest or global texture-cache limit is increased.
An owner clears registrations before the native visual can be freed or reused.
This avoids global hash aliases between unrelated fighters or outfits.

FCH1 has a 16-byte header (`FCH1`, version 1, row count, stride 32), followed by
rows of eight little-endian words: logical selection, outfit index, six block
offsets. A block is one edge word plus tightly packed BGRA pixels. Equal blocks
are deduplicated. Rows must bind to declared CAF recipes, block offsets must
point to exact contiguous block starts, and every block must be referenced.
The complete companion is limited to 128 MiB. The renderer admits 32 live owned
sources and at most 256 MiB of prepared host pixels, while retaining its existing
GPU budget and native fallback on GPU upload pressure. Registration failure is
explicit. Full 2048px wardrobes may exceed the compiled budget; use 1024px where
that is sufficient. These are bounded import/resource checks, not a larger game
memory configuration.

Validation distinguishes synthetic compiler/reader/renderer fixtures from native
visual acceptance. A successful package export does not establish in-game
appearance, four-player performance or platform-specific GPU qualification.
