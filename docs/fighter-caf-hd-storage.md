# Bounded lossless CAF HD storage

The compiler keeps the existing BGRA blocks when they fit. If the deduplicated
HD section exceeds128MiB, it retries with losslessly deflated BGR pixels. Native
material alpha remains supplied by the original compositor. Dimensions, RGB
pixels, native256px fallback and renderer ownership/budgets are unchanged.

A block begins with a little-endian edge word. Its high two bits specify:
0: edge followed by BGRA; 2: edge followed by BGR; 3: edge, compressed byte count,
then zlib-wrapped deflate BGR. Tag1 is invalid. Edges remain512/1024/2048. Legacy
readers reject the tagged edge instead of interpreting a new block silently.
The compiler emits tag3 only when the legacy layout cannot fit.

The existing128MiB stored-section limit,128distinct-block limit and192MiB
container limit remain. The reader additionally bounds the sum of decoded BGRA
blocks to192MiB. It verifies every compressed block with the pinned toolkit's
bounded stb deflate decoder before accepting the sealed container. Output must
be exactly edge*edge*3 bytes. A temporary decode is bounded to12MiB; each live
visual still registers BGRA through the original owner-scoped texture path.
No guest allocation sizes or global GPU memory caps change. An unexpected live
decode/allocation failure clears that visual's partial HD registration and logs
a native-atlas fallback; it does not add an in-match process stop.

Tests cover legacy compatibility, both native alpha layouts, exact RGB pixels,
block deduplication, malformed tags/edges/lengths/streams, truncated/trailing
blocks, oversized/short output and owner cleanup. This contract requires the
matching compiler/runtime; it is not an export for an older released binary.
