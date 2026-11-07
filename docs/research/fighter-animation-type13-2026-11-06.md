# Type13 timed quaternion decoding

Finishing moves can use a different rotation curve from ordinary combat
animation. Its exact keys are copied unchanged, but between keys the game
chooses the nearer quaternion sign and normalizes the result. Using the
type18 decoder or resampling everything as ordinary linear tracks would change
that behavior. This work adds an offline reader, not full-motion admission.

## Native contract

`TimedQuaternionCurve` in `setup/fighter_animation_timed_quaternions.py` reads
an inspected type13 record. `ED300` calls `EC8C0` for its time interval,
`FC3F0` for compressed scalar replay and `EA010` for interpolation. The time
table contains K-1 transitions with implicit initial time zero. The supported
input domain is finite child-time ticks from 0 through 65535; the final key
clamps. Exact keys retain their original values, including their original norm.

`EA010` uses normalized linear interpolation, not spherical interpolation.
The float32 dot product has order `((a0*b0 + a2*b2) + a1*b1) + a3*b3`.
A positive dot blends toward b; zero or negative blends toward -b. Normalizing
uses the x87 precision mode, so callers must explicitly select 24- or 53-bit
precision. The recomp's 64-bit-control setting uses its double-backed stack;
this reader does not claim to emulate a physical extended-precision x87 stack.
Degenerate or nonfinite results are rejected instead of reproducing native NaNs.

The decoder supports 8- and 16-bit scalar deltas. Four-bit data is limited to
one quaternion: the native per-group subset reader advances its offset in bytes,
which can differ from full-pose decoding and exceed the nominal packed span for
multiple quaternion groups. A successful full-key decode does not establish that
those interpolated reads are safe. This unsupported case is explicitly refused.

## Independent evidence

`scripts/fighter-type13-oracle.py` extracts the actual four generated functions into ignored
test output. It executes the complete unfiltered evaluator with fresh wrapper
and cache state for each sample, rather than substituting the Python algorithm
for any of the four functions. Output guard bytes check scatter bounds.

- 720 invented cases: 1/2/4/7 quaternion groups, 8/16-bit packing plus single-group
  4-bit packing, both x87 precision modes, interval boundaries and interior times.
- 20,160 evaluations, 2,078,720 compared bytes, **zero differences**.
- Native-body SHA-256:
  `0765cd32e99963cef060c0fc69b887426bc458baae1271f9823fc90185b911bd`.
- Evidence: `logs/fighter-type13-oracle/comparison.json`.
- 23 focused scalar/timed-quaternion unit tests pass. They cover nonunit exact
  keys, sign selection at zero dot, degenerate blends, time/precision refusal,
  extended exponent rounding, multiple destinations and unsafe nibble subsets.

All 94 type13 curves in the source paired finishers use four scalars and 8-bit
packing. Their 188 keys decode; 1,128 additional precision/time samples pass
the reader (`logs/fighter-m5-type13-source-audit.json`). That corpus check is
structural/numerical evidence, not a native playtest of the converted finishers.

Filtered evaluation, retained-cache history, parent time transforms, destination
ownership and full paired-motion rebuilding remain separate acceptance gates.
No external recomp project code was copied, and no game assets are tracked.
