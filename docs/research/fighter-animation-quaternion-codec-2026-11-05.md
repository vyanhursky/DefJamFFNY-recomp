# Type18 quaternion codec — 2026-11-05

Independent implementation derived from the owner's native decoder, with no
external project source. This remains an inspection/validation component;
authored animation registration is not enabled.

The six-byte seed interleaves four12-bit components. Three little-endian words
supply high12 bits; their low nibbles form the fourth component. NativeF49B0
maps each component through float32(value*2/4095)-1 (constant bits3A000801).
Each channel has eightu16 descriptors: four offsets and four ranges. F6BA0
converts offsets through float32(value*2/65535)-1 and ranges through
float32(value*2/65535), with constant38000080.

Each three-byte delta supplies three high6-bit components and a fourth made
from the low two bits of those bytes. F64C0 computes
current+((quant*range)*(1/63)+offset), rounding each operation to float32;
1/63 is3C820821. Blocks begin with6bytes/channel seeds, followed by
3bytes/channel per additional key. Full blocks are aligned to2bytes.
The independent decoder restarts from each block seed. It does not model
reverse traversal of an existing native cache, which subtracts deltas and can
have a different rounding history.

Local oracle extracted F6460/F6AE0/F6BA0/F49B0/F64C0 into an isolated fake
memory harness. Actual initialization and decode bodies were used; allocation
was a bounded private buffer. 240cases,3360channel poses,13440scalar
comparisons: zero differing bytes. Channels1/2/4/7, block shifts0/1/3,
keys1/2/3/5/9, endpoint and seeded random descriptors/data; output guard bytes
checked. Artifact: logs/fighter-quaternion18-oracle/comparison.json.
Native-body SHA256:1ec84a2eb36ca45513b1c1630d17c484725042a80dba07e824580b5259b9db12.

Interpolation is plain component-wise a+(b-a)*weight; no normalization,
hemisphere correction or SLERP. F4950 is the small native arithmetic helper;
F5BD0 is the full time/cache/scatter evaluator. Dynamic destination byte d
addresses four floats at output+16+48*d. Static channels are decoded directly
after dynamic scatter, never interpolated. Interpolation oracle and full
output-context/cache-history acceptance remain separate pending gates.

13invented-data unit tests cover seed endpoints/interleaving, unnormalized
replay, static channels, block alignment/reset and input/work bounds. Type19
uses different axis-constrained deltas, normalization and rotor composition;
it is deliberately unsupported by this decoder.


The extended oracle additionally executes nativeF4950 at weights0/.25/.5/1
for every adjacent key/channel pair. Combined forward replay/interpolation:
53,760scalar comparisons, zero byte differences. Native extracted-body digest
c4ea86d2d6fadb9e716debb9324fee9697d18e09cb49376c50bff038492b4e69.
Static channels remain direct seed copies. This validates arithmetic, not
fullF5BD0 time selection/scatter, reverse traversal or rig-context admission.
