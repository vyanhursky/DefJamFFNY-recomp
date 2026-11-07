# Type20/type21 vector decoding

The general M5 adapter now has an offline decoder for the three-component
curves used by root motion and cinematic helpers. This is a numerical reader,
not permission to install arbitrary animation banks. Coordinate meaning,
parent timing, event ownership and native registration still need validation.

## Native arithmetic and layout

Implementation: `setup/fighter_animation_vectors.py`, derived from the owner's
image and generated functions F1250/F14F0. No external project code was used.
The source is the bounded `CurveLayouts` representation of type20. Destinations
are u16 float-slot offsets; they are not bone ordinals.

For each channel, the 36-byte descriptor has three float bases, three float
extents, three u16 delta offsets and three u16 delta ranges. F1250 derives:

```
seed_base = base
seed_scale = f32(extent * c16)
delta_base = f32(f32(f32(offset * extent) * c2) - extent)
delta_scale = f32(f32(f32(range * extent) * c2) * c8)
```

Exact constants were checked by mapping their VAs into the owner's XBE:
2B5D40 = 37800080, 2B5D1C = 38000080, 2B5D38 = 3B808081.
These approximate 1/65535, 2/65535 and 1/255 respectively. Each operation rounds
to float32; replacing the sequence with a single double expression is wrong.

A block starts with three u16 seeds per channel, followed by three u8 deltas
per channel per additional key. Full block stride is
`align2(3 * channels * (2**shift + 1))`; the last partial block is separately
aligned to two bytes. Seeds decode as `f32(f32(seed * seed_scale) + base)`.
Forward deltas use `f32(current + f32(f32(delta * delta_scale) + delta_base))`.
Inline constant destinations and float triples follow the packed stream.

Optional times contain K-1 transitions with an implicit first time of zero.
Positive, strictly increasing transitions are the supported policy. With no
time array, key times are consecutive integers. The decoder accepts finite
nonnegative child times through 65535 and clamps at the last key. Interpolation
is `f32(low + f32(f32(high - low) * fraction))`, using rounded endpoint poses.
Constants are applied after dynamic channels, matching native scatter order.

## Independent validation

The private oracle executes the actual generated F1250 initializer and complete
unfiltered F14F0 evaluator, with only allocation supplied by a bounded fake
memory harness. No game process or graphics/audio devices are involved. Inputs
are invented, including random finite descriptors, packed samples, zero dynamic
channels, static channels, timed/untimed curves, block shifts 0/1/3 and keys
1/2/3/5/9. Each sample starts with a fresh native cache; guard bytes surround
the output.

405 cases, 10,935 sampled times, 1,600,884 compared bytes: **zero differences**.
Native-body SHA-256:
`daf50fca290af0b916edb95ffb42370e8a58429a97b40ea43af8a4ca9e07147e`.
Local evidence: `logs/fighter-vector20-oracle/comparison.json` and
`logs/fighter-vector20-oracle.txt`. Generated bodies, executable and test bytes
remain ignored. Fourteen synthetic unit tests also pass.

The one-component type21 profile shares this arithmetic with 12-byte
descriptors, two-byte seeds and one-byte deltas. Its actual EFBD0 initializer
and complete EFD80 evaluator pass another 405 cases and 10,935 sampled times:
1,513,404 compared bytes, zero differences. Constants at 2B5CB8/2B5CB0 match
the type20 scales. Native-body SHA-256:
`1a94428b7132c9e198ad58a753cef9061382bbf5f8079ec3a5580e79710e501c`.
Evidence: `logs/fighter-vector21-oracle/comparison.json`.

This proves fresh-cache unfiltered lookup, replay, interpolation and scatter
for the tested profile. Filtered evaluation, retained-cache rounding history,
output-buffer ownership and faithful full-motion conversion are separate gates.
`runtime_ready` remains false. There was no stock game regression for this work.
