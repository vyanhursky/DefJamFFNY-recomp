# D3D8 push-buffer: space reservation and ring wrap

Read-only reverse-engineering pass over the lifted C in `src/recomp/gen/recomp_0015.c` and
`recomp_0016.c`. No code was edited, built, or run. All addresses are guest (original Xbox)
addresses. The device pointer is the global at `0x234768`, which in this build is a *fixed*
static struct at `0x234770` (not heap-allocated) — see `sub_002172C0` (`CreateDevice`) at
`0x002172E6`: `MEM32(0x234768) = 0x234770`.

## Device-struct fields established or confirmed here

| Offset | Meaning | Evidence |
|---|---|---|
| `dev+0x00` | CPU push-buffer write pointer (linear address into the ring) | `sub_0021E660` init: `MEM32(esi) = eax` (= ring base); read/written everywhere as "the" write pointer |
| `dev+0x04` | Cached "safe to write until" limit (an address); when the write pointer passes it, code must call the reserve routine | Init in `sub_0021E660`: `ringBase + chunkSize - 0x204`; updated at the end of `sub_0021EDC0` |
| `dev+0x24` | Ring **base** address (physical/linear address of the allocated push-buffer memory) | `sub_0021E660` @ `0x0021E673`: `eax = sub_001F9DC6(size=MEM32(0x236F14), tag=0xBC800000, …)` (contiguous-memory allocator); `MEM32(esi+0x24) = eax` |
| `dev+0x28` | Ring **limit/end** address = `ring_base + ring_size` | `sub_0021E660` @ `0x0021E681…0x0021E692`: `edx = eax + (MEM32(0x236F14)>>2)*4; MEM32(esi+0x28) = edx` |
| `dev+0x2C` | Latest issued fence reference (already known) | confirmed, initialised to `5` in `sub_0021E660` |
| `dev+0x30` | Pointer to the fence word the GPU writes (already known) | confirmed; `*that_word` initialised to `3` in `sub_0021E660` |
| `dev+0x34/0x38/0x48` | A *second*, growable circular list of `{ref, position}` pairs distinct from the fixed 64-slot table at `dev+0x64`; `+0x34`=next index, `+0x38`=index mask (`2^n-1`), `+0x48`=pointer to the `{ref,pos}` array | Allocated at the end of `sub_0021E660` (`0x0021E6CC`-`0x0021E6EB`, size chosen as a power of two `>= ring_size/chunk_size`, `pos>>1` shifts derived from `MEM32(0x236F10)`); written to in `sub_0021EB90` (`loc_0021EC09`) and walked in `sub_0021EDC0` and `sub_0021E730` |
| `dev+0x40` | Wrap/generation counter — incremented once per ring wrap | `sub_0021EDC0` @ `0x0021EE2E`: `ecx = MEM32(esi+0x40); ecx++; MEM32(esi+0x40) = ecx;` |
| `dev+0x44` | **Not** a fixed ring-size constant — see "Correction" below | `sub_0021EDC0` writes a *new* value here on every wrap |
| `dev+0x5C/0x60` | Cached, unwrapped ("monotonic") GPU-consumed position, maintained by `sub_0021E830` | see below |
| `0x236F14` | Global: configured ring size in bytes, default `0x80000` (settable via `sub_002172A0`, defaulted in `sub_002172C0` if zero) | `sub_002172C0` @ `0x002172C9`: `MEM32(0x236F14) = 0x80000` |
| `0x236F10` | Global: default per-reservation "chunk" size, default `0x8000` | `sub_002172C0` @ `0x002172DC`: `MEM32(0x236F10) = 0x8000` |

### Correction to the prior "known facts": `dev+0x44` is dynamic, not a fixed ring size

The task brief lists `[dev+0x44]` as "push-buffer ring size (0x80000)", presumably from a runtime
observation. Reading `sub_0021E660` (ring init) shows `dev+0x44` is **not** initialised there at
all (only `dev+0x00/0x04/0x24/0x28/0x2C/0x30/0x38/0x48` are set up). It is written for the first
time only when a wrap actually happens, inside `sub_0021EDC0` (see Q2 below), where the value
stored is `old_write_ptr - ring_base` at the moment of the wrap — i.e. "how many bytes were
actually used in the lap that just ended", computed fresh every wrap. Because the safety margin
before wrapping is small (`0x4000`, see Q1) relative to the default ring size (`0x80000`), this
value normally comes out close to, but not exactly, `0x80000`, which is consistent with the prior
observation. It is then used elsewhere purely as a wrap-around addend to "unwrap" a physical ring
offset into a monotonic counter, e.g. `sub_0021EC50` @ `0x0021EC9F`/`0x0021ECA9`:
`eax = eax + MEM32(esi + 0x44);` and again in the wait loop inside `sub_0021EDC0` @ `0x0021EE93`.
Confidence: high (directly reads the init function and the write site; the "default ~0x80000"
observation and this dynamic value are not in conflict).

## Q1: The reserve ("make space") routine

**`sub_0021EDC0`** (`Original: 0x0021EDC0 - 0x0021EEF7`), cdecl, 2 stack args (only the first,
the requested byte count, is actually consumed by the slow path; the second is written over as
scratch and appears unused in this build — low confidence on its intended purpose).

Two entry points feed it:
- **`sub_0021EF10(dwordCount)`** — the cheap, inlined fast path used by ordinary command emitters
  throughout the D3D code (and copied inline in many places, e.g. `sub_00219800`-ish flip code,
  `sub_002162D0`, etc.): compare `MEM32(dev+0)` (write pointer) `+ dwordCount*4 + 0x200` against
  `MEM32(dev+4)` (cached limit); only if exceeded does it fall through to `sub_0021EDC0` with a
  size of `max(dwordCount*4+0x204, MEM32(0x236F10)>>1)`.
- **`sub_0021EF00()`** — the no-argument variant used when the caller doesn't know a specific
  count; passes `(MEM32(0x236F10)>>1, MEM32(0x236F10))` i.e. reserves the default half-chunk
  (`0x4000` bytes by default).

So the *cheap* check (`write_ptr < dev+4`) is inlined at every command-emission call site; the
*real* reserve/wrap logic lives only in `sub_0021EDC0`, called only when that cheap check fails.

Pointers/limits used by `sub_0021EDC0`:
- CPU write pointer: `MEM32(dev+0)` (`edi` in the lifted code).
- Ring base: `MEM32(dev+0x24)`.
- Ring limit: `MEM32(dev+0x28)`.
- Requested size: first stack arg (`ebx`).

There is also a completely separate fast path, taken when `MEM8(dev+8) & 4` is set
(`0x0021EDC7`-`0x0021EDCF`): it just walks a small linked-list-like structure at `dev+0x764/0x768`
and does not touch the physical ring at all. This looks like a "secondary/deferred command list"
mode (possibly for a display-list-like batching feature) rather than the normal GPU push buffer;
it is unrelated to ring wrap. Confidence: medium (didn't trace `dev+0x764` further; out of scope
for the wrap question).

## Q2: What happens when the ring is full or the end is reached

Lifted code, `sub_0021EDC0`, main (non-`dev+8&4`) path:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Answer: **it writes an NV2A JUMP word into the push buffer at the current (about-to-be-abandoned)
write position, then resets the CPU write pointer to the ring base.** The JUMP word's value is
`(ring_base & 0x0FFFFFFF) | 1`, i.e. exactly the "JUMP, target in bits 31:2, bits 1:0 = 01"
encoding already documented in the task brief, and it targets the ring's start address — this is
the same kind of word the brief already observed appearing at the ring's end at runtime. This
confirms hypothesis (a): a JUMP word is written, not a bare `DMA_GET`/write-pointer reset without
a jump, and it is **not** a JUMP placed once at ring initialisation (`sub_0021E660`, the init
routine, never writes a JUMP word — it only sets up `dev+0/0x04/0x24/0x28`). The JUMP word is
generated fresh, every time a wrap actually occurs, at whatever position the write pointer
happened to reach.

Confidence: high for "a JUMP word is written and the write pointer is reset to ring base";
medium for the exact bit-level derivation of the JUMP encoding (`ecx++` after masking — algebra
checks out given a 4-byte-aligned ring base, but this one increment instruction is easy to
misread without a disassembly cross-check).

Two related, softer wrap paths in the same function (`loc_0021EE21`/`loc_0021EE60`): if the
*margin-inflated* candidate end would cross the ring limit but the actual requested write would
not, the code skips the JUMP/reset entirely and just proceeds at the current position — i.e. the
0x4000 margin is a "leave room for one more small command before really running out" cushion, not
itself a hard wrap trigger.

## Q3: What it waits on before reusing space

Two different waits are involved, at two different times:

**(a) Inside `sub_0021EDC0`, right after computing the (possibly wrapped) candidate end**
(`loc_0021EE64`–`loc_0021EEA8`): before handing back the newly-reserved region, the code checks
whether the region about to be (re)used might still be read by the GPU, and if so walks the
*growable* pending-fence list at `dev+0x34/0x38/0x48` (not the fixed 64-slot table at `dev+0x64`)
backwards from its head, unwrapping stored positions with `+ MEM32(dev+0x44)` when they look like
they're behind the write pointer, to find the newest record whose stored ring position is at or
before a computed threshold (`ebx = (MEM32(0x236F14) >> 1) + edi`, i.e. half the ring size past the
new region's start). It then calls:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

**(b) `sub_0021EC50`** (`Original: 0x0021EC50-0x0021EDBA`, already known as "blocks on a fence")
contains the actual spin loop, at **`0x0021ED87`**:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This is a tight busy-wait polling `MEM32(*fence_word_ptr)` (the same NV2A semaphore word that
`sub_0021EB90`'s fence-insert command targets), i.e. it waits on the **fence records**, comparing
the target reference against the live GPU-written completion counter — matching the brief's
"reference, compared how" question directly: by subtracting from the latest-issued ref on both
sides and comparing unsigned, which is a wraparound-safe way of testing `completed >= target`.

There is a second, non-spinning fallback path when too many fences are outstanding
(`cmp eax, 0x2000; jae loc_0021ED98`): rather than spin, it repeatedly calls an indirect function
pointer loaded from `MEM32(0x28524C)` with a small argument block (`loc_0021EDA4`, looping while
the call returns non-zero) — this looks like a kernel/OS event-pump (processing outstanding
notifications) rather than a raw hardware poll; not fully resolved (medium-low confidence on what
exactly it pumps).

Separately, `sub_0021E830` (`0x0021E830-0x0021E8AA`) is called from `sub_0021EDC0` right after
loading the candidate end, and its job is to read the **actual DMA_GET register**
(`MEM32(MEM32(dev+0x1C20) + 0x44)` — the write-side companion to the already-documented DMA_PUT at
`+0x40`) and fold it into a monotonic "GPU consumed" counter cached at `dev+0x5C` (raw GET value)
and `dev+0x60` (unwrapped/accumulated), handling the GET register's own wraparound using a lookup
at `dev+0x934` (`MEM32(dev+0x934) + 0x400B10`, not resolved further). This is a cheap
non-blocking read, not a spin loop; it feeds the `dev+0x5C/0x60` fields that other code
(not traced further here) presumably uses for a lighter-weight "has GPU consumed enough" check
before resorting to `sub_0021EC50`'s spin.

Confidence: high for the `sub_0021EC50` spin loop and what it polls; medium for the exact
semantics of the pending-fence-list walk in `sub_0021EDC0` (the index/mask arithmetic around
`dev+0x34/0x38/0x48` was read but not fully hand-simulated); medium-low for `sub_0021E830`'s
`dev+0x934` lookup and the `0x28524C` fallback pump.

## Q4: Does Present / the flip path do anything special to the write pointer afterwards?

Looked at the flip-command emitter around `0x00219869`-`0x00219939` in `recomp_0015.c` (writes the
`0x4012C`/`0x40130` method words identified in the brief, i.e. `count=1` "increasing" NV2A words
with `method = w & 0x1FFC` giving `0x12C` and `0x130`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Answer: **no special-cased rewind/jump/reset tied to Present/flip.** The flip/FLIP_STALL command
words are written through the exact same "advance write pointer, then check against the cached
`dev+4` limit, call the generic reserve function if exceeded" idiom used by ordinary state/command
emitters everywhere in the D3D layer (the same pattern is visible, e.g., in the small helper
`sub_002162D0` at `0x002162D0`-`0x002162E3`). If a Present happens to land exactly when the ring
is nearly full, it goes through the ordinary `sub_0021EDC0` wrap path described in Q2 like any
other command; there is nothing that forces a wrap or rewind specifically at flip time. The
actual submission-to-hardware (writing `DMA_PUT`) is still done separately by the already-known
kick routines `sub_0021EA70`/`sub_0021EB20`, which are not called from inside this flip-emission
code directly (their callers include `sub_0021EB90`/`sub_0021EDC0`/`sub_00221930`/`sub_00221E00`
per `scripts/callers.py`, plus `sub_00217050` for `sub_0021EB20`) — i.e. flip commands get queued
into the ring like everything else and ride along with whatever next kicks the buffer (frequently
`sub_0021EDC0`'s own trailing kick, see next paragraph).

One more relevant detail found while answering Q1/Q2: `sub_0021EDC0` itself, at the very end
(`loc_0021EEB4`-`loc_0021EEEF`), always finishes by calling the kick routine `sub_0021EA70`
(after first inserting a fence via `sub_0021EB90(3)` on one branch, if a particular flag bit in
`dev+8` is not set). So **every reserve call — wrap or not — ends by submitting whatever is
currently pending to the GPU**, not just Present. Confidence: high (directly read).

## Summary of addresses for quick reference

| Address | Function | Role |
|---|---|---|
| `0x0021E660` | `sub_0021E660` | Ring buffer allocation/init: sets `dev+0/0x04/0x24/0x28/0x2C/0x30/0x38/0x48`; allocates the pending-fence-list array |
| `0x002172C0` | `sub_002172C0` | `CreateDevice`-ish: defaults `MEM32(0x236F14)=0x80000` (ring size), `MEM32(0x236F10)=0x8000` (chunk size) |
| `0x002172A0` | `sub_002172A0` | Setter for the two globals above (app-overridable ring/chunk size) |
| `0x0021EDC0` | `sub_0021EDC0` | **The reserve/wrap routine** |
| `0x0021EE2B`-`0x0021EE5B` | (inside `sub_0021EDC0`) | Wrap branch: JUMP-word write + write-pointer reset |
| `0x0021EE6E`-`0x0021EEA8` | (inside `sub_0021EDC0`) | Pending-fence-list search before reuse |
| `0x0021EF00` | `sub_0021EF00` | No-arg reserve entry (default half-chunk) |
| `0x0021EF10` | `sub_0021EF10` | Cheap inlined "ensure N dwords" check, calls `sub_0021EDC0` on overflow |
| `0x0021EC50` | `sub_0021EC50` | Fence-wait routine (already known); spin loop at `0x0021ED87` |
| `0x0021E830` | `sub_0021E830` | Reads DMA_GET (`[dev+0x1C20]+0x44`), maintains monotonic consumed counter at `dev+0x5C/0x60` |
| `0x0021E730` | `sub_0021E730` | Walks the fixed 64-slot fence table (`dev+0x64/0x68`) and/or the growable list to find a satisfying record |
| `0x00219800`ish-`0x00219939` | (flip/FLIP_STALL emitter) | Writes `0x4012C`/`0x40130`, then does the ordinary cheap reserve check |
