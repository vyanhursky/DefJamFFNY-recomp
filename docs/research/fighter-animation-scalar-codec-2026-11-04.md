# Compressed scalar codec FC3F0 / FC8A0 — 2026-11-04

Read-only audit of the user's own `src/recomp/gen/recomp_0007.c`, with targeted Capstone disassembly of the local XBE to verify the unusual nibble address/state setup. No source edits, build, game run, or native numerical oracle was performed. These formulas are implementation evidence for a future independent decoder; numerical_decoder_validated and runtime_ready remain false.

## Common data and arithmetic

ECX supplies descriptor D. Its u16 S, u8 B at+2 and S triples at D+4 are shared by type11/13. Triple j contains offset A[j], multiplier M[j], base V[j], each float32 at stride12. Packed data P starts D+4+12*S. B is4,8 or16; other widths fall through without useful delta evaluation. Quantized q is **unsigned**: nibble0..15, byte0..255, little-endian word0..65535 (ZX8/ZX16 followed by CVTSI2SS). There is no signed normalization or automatic division by15/255/65535. A and M encode any such scaling/bias.

Below `f(x)` means one binary32 rounding at an SSE scalar instruction. Native MXCSR rounding/FTZ/DAZ configuration is an additional execution dependency. Do not use host double arithmetic throughout, fuse multiplies/adds, reassociate additions, or assume a finite descriptor implies finite decoded values. All unsigned q values convert to float exactly.

For the ordinary full scalar route (offset0, count S), pose0 equals V. Pose k consumes packed rows0 through k-1. Eight-bit rows are S bytes, sixteen-bit rows2*S bytes, nibble rows ceil(S/2) bytes, low nibble before high nibble. Odd S has an unused high nibble at each row end. Existing four-scalar profiles have S%4==0 and avoid that odd-S branch.

## FC3F0: decode/cache update

Actual stack arguments, in call order: `(scalar_offset o, scalar_count n, old_index c, target_index k, source_cache, destination_cache)`, with D in ECX. These are signed int comparisons for indices/count loops; this routine supplies no clamping or data bounds checks.

1. If k==c, it returns immediately, **without copying even when source and destination differ**.
2. If k<c, k==0, or c==-1, initialize destination[0:n] from base triples o..o+n-1 and set effective c=0.
3. Otherwise retain the existing cache; if source_cache!=destination_cache copy n float words forward (REP MOVSD, not overlap-safe memmove), then accumulate starting at c.
4. For each delta row c through k-1 update each destination scalar. It never subtracts deltas to seek backward; it resets/replays from bases.

For B8/B16, there is an important addition-order difference in FC520/FC630 versus their remainder loops:

- First scalar of each unrolled four-scalar group (local j%4==0): `x[j] = f(f(f(q*M[o+j]) + x[j]) + A[o+j])`.
- Remaining three scalars in each complete group: `x[j] = f(f(f(q*M[o+j]) + A[o+j]) + x[j])`.
- Scalar remainder after complete groups: same order as the first scalar, multiply then previous value then offset.

For B4 all audited scalar/nibble paths use multiply, previous value, offset: `x[j] = f(f(f(q*M[o+j]) + x[j]) + A[o+j])`. Thus a generic sum-of-deltas evaluated once in double precision is not a bit-exact native decoder, and even an f32 implementation must preserve lane/order differences.

### Exact subset cursor caveats

The routine is not a general conventional array-slice decoder. Coefficients start D+4+12*o and cache output always begins at destination[0]. Initial packed address for effective old c is:

| Width | Initial cursor |
|---|---|
|16|P+2*(S*c+o)|
|8|P+S*c+o|
|4|P+ceil(S/2)*c+o (**o bytes**, not floor(o/2))|

B4 selects its initial low/even branch from o&1. For even o, each iteration consumes n nibbles in pairs, discarding a final high nibble for odd n. For odd o and n>=2, it reads first high nibble and advances one byte, then low/high pairs and an optional final low nibble. Odd o,n1 bypasses both first-high and trailing-low work: no scalar delta write. This is an edge behavior, not a proposed supported layout.

Subsequent B8/B16 iterations continue at the cursor after n decoded scalars; there is **no S-n row skip**. B4 similarly continues after its local pair/tail consumption. Consequently nonzero o or n<S does not justify substituting `q[row*S+o+j]` on every row. Restrict an initial numerical decoder to full o0,nS, or reproduce the native cursor machine explicitly and independently validate selected-channel call construction. Targeted XBE disassembly FC6F7..FC711 confirms ceil(S/2)*c+o and the parity test; this is not a generated-C transcription guess.

## FC8A0: mapped weighted delta accumulation

Stack arguments: `(o,n,c,k,source_cache,output,g,destinations,w)`, D in ECX. g is scalar width per output group (ordinary type11/13 calls use4); group count is signed n/g. Require positive g, n divisible by g, nonnegative counts and bounded destinations in any offline profile; native division/loops do not supply these checks.

If k==c return immediately without writes. If k==0, c==-1, or k<c, copy descriptor bases to mapped output and reset effective c=0. Otherwise scatter source_cache scalars to mapped output. Source cache is dense: group h, lane l reads source_cache[h*g+l] and writes output[destinations[h]+l]. Coefficients begin at descriptor scalar o and advance densely through groups. Base initialization uses the same mapping.

Then for each packed row from effective c through k-1, for each mapped scalar j=h*g+l:

`d = f(f(q*M[o+j]) + A[o+j])`

`output[destinations[h]+l] = f(f(d*w) + output[destinations[h]+l])`

This order is uniform across the audited 4/8/16-bit unrolled/remainder paths. It is **weighted decoded-delta accumulation**, rather than decoding two complete poses and computing `(1-w)*poseA+w*poseB`. Ordinary interpolation calls use adjacent indices and a fractional w, so the real-number expressions can agree, while f32 rounding differs. Multiple rows use the same w for every delta; it is not applied just once to the final sum. No clamp or finite check is applied to w in this helper.

For B16/B8 packed cursor starts P+row_stride*c, without adding o; coefficients still start at o. Cursor then advances densely through n scalar values per row without S-n skip. B4 starts P+ceil(S/2)*c, also without o byte offset. Its initial low-nibble flag is `((o & 0xFFFFFFFE)==0)` as verified at native FCD53..FCD69: offsets0 or1 begin low, offsets>=2 begin high. Each decoded scalar toggles the flag; high-nibble reads advance cursor. At each row end a pending unused high nibble is skipped and next row begins low. This peculiar initial-state expression must not be silently replaced by parity(o) in an exact helper clone. Native disassembly FCDE0 confirms low/high dispatch; the generated SETE at FCDEF toggles state.

### Aliasing and repeated destinations

Both helpers make ordered in-place writes. FC3F0 supports exact source==destination by skipping the copy, but partial overlaps use forward REP MOVSD semantics. FC8A0 scatters source cache or bases before adding deltas; overlapping cache/output, duplicate destination groups or overlapping destination ranges can overwrite values needed later. Deltas then accumulate in loop order into whatever output currently contains. A clean independent decoder should use separate owned scalar/output buffers and explicitly reject or document overlapping destination groups instead of assuming mathematical scatter is order independent. Serialized payload/coefficients must not alias writable output. None of these constraints is established by whole-.data bounds alone.

## Proposed independent oracle cases

These cases are proposed, not run against native code in this audit:

1. B4 bytes0xF1,0xA2 with S4, V0,M1,A0, target1 must produce (1,15,2,10). B8 include0,127,128,255; B16 little-endian0,32767,32768,65535 to prove unsignedness.
2. Base-only target0 from old-1, forward0->1->3, fresh-1->3 and backward3->1. Compare complete f32 bit patterns; backward must replay rather than subtract.
3. Equal old/target with different sentinel-filled destination proves no-copy early return. Forward separate caches proves copy; exact cache alias proves in-place support. Avoid claiming partial alias equivalence.
4. Rounding order: S4, q=1,M=2^24,A=-2^24,V=1. At target1 B8/B16 lane0 yields0 while lanes1..3 yield1 (round-to-nearest-even); B4 all lanes yield0. Add n5/6 cases to exercise remainder behavior outside ordinary supported profiles.
5. FC8A0 same q/M/A/V with w0.5 distinguishes weighted delta accumulation from lerp of separately rounded poses. Test w0,0.25,1 plus multiple rows and reordered destinations. Preserve untouched output sentinels.
6. S odd B4 rows with distinct padding high nibbles proves row padding; subset o1,n1 exposes the skip; o1,n2 and o2,n4 expose byte-offset/initial-state oddities. These belong to helper characterization, not automatic format admission.
7. Repeated/overlapping destinations and source/output aliases characterize ordered scatter only in an isolated test oracle. Finite coefficient extremes, subnormals, signed zero and overflow establish the numerical policy/MXCSR scope before declaring validation.

Primary stable anchors: FC3F0/FC40B..FC49D cache decisions; FC520,FC5B1,FC630,FC6C0 arithmetic; FC6F7..FC88B nibble machine; FC8A0..FCA4E cache scatter/reset; FCAE0,FCB92,FCC50,FCD00 weighted deltas; FCD4B..FCF2A nibble machine. The previous structural reports remain valid as bounds schemas; they do not by themselves validate these numerical semantics.
