# Code-segment corruption: where does the destination pointer come from?

Read-only static trace of `sub_00181D20` -> `sub_001E9040` -> `sub_001E9270`, following the
ground-truth runtime measurement in the task brief (write to guest `0x00077158`, writer
`sub_001E9270`, registers `ecx=0x80F2005B edx=5 eax=0x77 esi=0x00077158 edi=0x00076C78`,
call chain `sub_00181D20 -> sub_001E9040 -> sub_001E9270`).

All line numbers are `src/recomp/gen/recomp_0011.c` or `src/recomp/gen/recomp_0012.c` as noted,
current as of this read. Everything quoted below was read directly; anything not quoted is marked
INFERRED or NOT DETERMINED.

## Summary of the correction this report makes

The task brief frames `edi` / `MEM32(esp + 0x10)` in `sub_00181D20` as the thing to trace back to
find "the destination buffer pointer." Having read `sub_00181D20`, `sub_001E9040` and
`sub_001E9270` in full and worked out the exact stack layout at each call site, **`edi` is not the
destination — it is the source.** The destination that becomes `sub_001E9270`'s `esi` is a
*different* local in `sub_00181D20`, held in `eax` at the call site, which is the return value of
an allocator call. This is a load-bearing correction: tracing `edi` leads to a handle/resource
lookup (`sub_001E69D0`) that is not on the path to the corrupted pointer at all. Section 2 below
shows the argument-mapping arithmetic that establishes this, with the code quoted so it can be
checked independently.

---

## 1. `sub_00181D20`: what is `MEM32(esp + 0x10)` in its frame?

`sub_00181D20` is declared `CC: cdecl, 0 params` and is `fpo_leaf`. It has exactly one direct
caller in the lifted C:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

No arguments are pushed before this call — only the return-address push that `RECOMP_ABI_CALL`
always needs. **READ, confirmed:** `sub_00181D20` takes no caller-supplied arguments at all, so
nothing inside its frame at any `esp + N` offset can be an incoming parameter; every `MEM32(esp +
N)` reference inside the function is either a local (inside the `esp -= 0x210` buffer it allocates
in its prologue) or the SEH bookkeeping the prologue pushes.

The prologue (`recomp_0011.c:14824-14841`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

There is exactly one assignment to `edi` in the whole function body (`recomp_0011.c:15056`,
verified with a full-function grep — the only other `edi` references are the prologue/epilogue
save/restore and its two uses immediately after):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`esp` is unchanged between `loc_00181F34` and `loc_00181F45` (the intervening call to
`sub_001E9080` pushes one argument and cleans it up with `esp = esp + 4`), so both reads are the
same local slot. **READ:** this slot is not an argument (see above) and is not written anywhere
else that I could find in the function; it is a local, filled earlier by an out-parameter write
from a callee. Working out *which* local it is (by counting the pushes between the `esp -= 0x210`
allocation and this point) shows it is the stack slot that was passed as `arg2` to `sub_001E69D0`
at `recomp_0011.c:14926-14939`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

i.e. `sub_001E69D0(id = MEM32(ecx+edx+0x108), &local[+4], &local[+0xC])`, where `ecx+edx+0x108` is
a field of a per-slot struct table at global `0x3B37A0` indexed by global `0x2EAB4C` (stride
`0x110`) — the same indexing pattern used throughout this function. `&local[+4]` is the same
address later read as `MEM32(esp + 0x10)` (I checked the arithmetic: at `loc_00181E02` the pointer
is computed as `esp + 0x14` one push before the steady-state baseline reached at `loc_00181F34` /
`loc_00181F45`, i.e. the same absolute address once the one extra push is accounted for).

`sub_001E69D0` (`recomp_0012.c:169814` on) treats its first argument as a handle into a table at
`0x3C9100` and, on success, writes two different fields of a found entry into its two out-params
(`recomp_0012.c:169989-170006`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

(`eax` here is loaded from `esp + 0x10` / `esp + 0x14`, i.e. the two out-pointers, in the lines
immediately above — `recomp_0012.c:169943` and `169959`.) On failure it writes 0 to both
(`recomp_0012.c:169956, 169969`). So the local that `sub_00181D20` calls `edi` is, on the success
path, `entry[0x2C] - entry[8]` of a resource/handle-table entry.

**This is the important correction:** this value is *not* what becomes `sub_001E9270`'s
destination (`esi`). Section 2 shows it becomes the *source*.

---

## 2. `sub_001E9040`: which argument becomes `sub_001E9270`'s `esi`?

Full body (`recomp_0012.c:178729-178786`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_001E9040` first *dereferences* its own `arg1` (`ecx`) as a pointer, checking for a two-byte
lead-in pattern (`MEM8(ecx+1) == 0xFB`, then `MEM8(ecx) & 0xFE` against `0x10` / `0x90`) — this is
a length-prefix/lead-byte check on encoded data, not something you'd do to a plain size value.
Only if that check passes does it call `sub_001E9270`, pushing (in order) `0`, then its own
`arg1` (`ecx`), then its own `arg2` (`eax`). Push order right-to-left means the **last** push is
the callee's **first** argument, so:

- `sub_001E9270`'s **arg1** = `sub_001E9040`'s **arg2** (`eax` here, `MEM32(esp+8)`)
- `sub_001E9270`'s **arg2** = `sub_001E9040`'s **arg1** (`ecx` here, `MEM32(esp+4)`)
- `sub_001E9270`'s **arg3** = `0` (constant)

`sub_001E9270`'s prologue (`recomp_0012.c:179219-179233`) confirms `esi` (destination) is loaded
from `arg1` and `edx`/`ecx` (source) from `arg2`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

So: **`sub_001E9270`'s `esi` (destination) = `sub_001E9040`'s `arg2`**, and **`sub_001E9270`'s
`edx`/`ecx` (source) = `sub_001E9040`'s `arg1`**.

Now the call site inside `sub_00181D20` (`recomp_0011.c:15079-15083`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Same right-to-left rule: the last push (`edi`) becomes `sub_001E9040`'s `arg1`, the first push
(`eax`) becomes its `arg2`. Combined with the mapping above:

- **`sub_001E9270`'s destination (`esi`) = `sub_00181D20`'s `eax`** at this call site.
- **`sub_001E9270`'s source (`edx`/`ecx`) = `sub_00181D20`'s `edi`** at this call site (the local
  traced in section 1).

This matches the runtime register dump in the brief: `ecx = 0x80F2005B` (a normal-looking heap
address, consistent with the source being fine) while `esi = 0x00077158` (the corrupted code-
segment address) is the destination. `edi = 0x00076C78` recorded at the crash is `sub_001E9270`'s
own local (it zeroes its own `edi` in the prologue and uses it as a back-reference scratch pointer
during decompression — see section 4); it is unrelated to `sub_00181D20`'s `edi`, which is a
different function's different register.

**Conclusion for this section:** the destination pointer is `sub_00181D20`'s `eax` at
`loc_00181F91`, not its `edi`. Tracing `edi` (as section 1 does) explains the *source* string, not
the corrupted destination.

---

## 3. Where `eax` (the real destination) comes from, and whether a fixed buffer is involved

At `loc_00181F91`, `eax` is untouched since the immediately preceding call returned
(`recomp_0011.c:15069-15079`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_001E9E70` is a 5-byte tail-call wrapper (`recomp_0012.c:181872-181881`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

`sub_001E9AB0` (`recomp_0012.c:181215` on, 950 bytes / 342 instructions) is a **free-list-style
sub-allocator**, not a fixed/static buffer:

- Its size-class table is a fixed global array of 64 bucket heads at `0x3C9158`
  (`recomp_0012.c:181305-181306`: `ecx = esi & 0x3F; ecx = ecx*4 + 0x3C9158;`), with a default
  list head at `0x3C9138` used when the caller's own list pointer (its own `arg4`, read from
  `MEM32(esp+0x64)`) is zero (`recomp_0012.c:181298-181301`).
- It walks and splits free blocks (`MEM32(esi+0x10)`/`MEM32(esi+0x14)` linked-list pointers,
  `recomp_0012.c:181486-181521`), and tags block headers with 16-bit ASCII-looking magic values —
  `0x4246` ("FB"), `0x4253` ("SB"), `0x424F` ("BO"), `0x424D` ("BM") — at several points
  (e.g. `recomp_0012.c:181552, 181611, 181640, 181672`), consistent with an internal block-state
  allocator, not a plain buffer.
- It has three explicit "return 0" failure exits, gated on validation of its five arguments
  (`recomp_0012.c:181243-181247`, `181261-181266`, `181319-181326`), and its only success returns
  are `eax = ebx` at `recomp_0012.c:181806` and `181858`, where `ebx` is a pointer computed from a
  free-list node found via the bucket search above (`recomp_0012.c:181569-181577`,
  `181555-181566`).

Its five arguments (in caller push order at `loc_00181F79`, i.e. reading back from last-pushed =
arg1): `arg1` = `&(esp+0x3C)` (an out-param slot, also independently overwritten by the caller
right after the call — `MEM32(esp + 0x3C) = eax;` at `recomp_0011.c:15082` — with the same value
already returned in `eax`), `arg2` = the return value of a **prior** call to `sub_001E91B0`,
`arg3` = the constant `0x80` (flag bits), `arg4` = `sub_00181D20`'s `esi` (which I confirmed is
set to `0` at `recomp_0011.c:14880` and never reassigned before this point — so alignment `0`),
`arg5` = global `MEM32(0x2EAB54)`.

`sub_001E91B0` (`recomp_0012.c:179000-179008`) is itself a **tail-call wrapper to `sub_001E9080`**
— the very same length-prefix-decoding function `sub_00181D20` also calls directly at
`loc_00181F34` (section 1). `sub_001E9080` decodes a variable-length length prefix out of a byte
stream and returns the decoded length in `eax` (three-way jump table on the prefix's low bits,
`recomp_0012.c:178834-178861`). So **`sub_001E9AB0`'s `arg2` (the allocation's size bound) is the
decoded length of a length-prefixed blob**, and `sub_001E9AB0`'s `arg5` (`MEM32(0x2EAB54)`) is a
global whose value at this point I did **not** determine.

**Answer to the "fixed buffer" question:** I found no code path in `sub_00181D20`,
`sub_001E9040`, or `sub_001E9AB0` where the destination is meant to be a compile-time-fixed
scratch buffer. The design is a dynamic allocator with free-list bins, and the ground truth's own
observation that 26 sampled normal calls all had `arg1` in `0x8xxxxxxx` is consistent with that —
that is where this allocator's arena normally lives, nowhere near `0x00076C78`/`0x00077158`. I
could not find any legitimate code path that treats the `0x00076C78`–`0x00077158` code-segment
region as an intended buffer. That said, I was not able to fully explain *why* `sub_001E9AB0`'s
free-list search would return a pointer in that range on the bad call — that would require the
live values of `0x2EAB54`, `0x3C9138`, `0x3C9140`, and `0x3C9158`'s bucket contents at the moment
of the bad call, which is runtime state I don't have. **I could not determine this final step.**
Two hypotheses I cannot currently distinguish: (a) this allocator's control tables/arena are
mis-initialized specifically in the recompiled build (a lifter/host bring-up issue, not a game
logic bug), or (b) the free-list was already corrupted by an earlier, unrelated write before this
call, and `sub_001E9AB0` is simply the messenger returning a bad pointer it read out of corrupted
list-node memory. I would want a watchpoint on `0x2EAB54` and a dump of the `0x3C9158` bucket for
the size class actually used, taken right before the bad call, to tell these apart.

---

## 4. What is `sub_001E9270`?

`sub_001E9270` (`recomp_0012.c:179205-179454`, 442 bytes / 201 instructions) is **not** a
recognizable CRT routine (not `memcpy`, `strcpy`, `strncpy`, or a `wcscpy` variant) as far as I
could tell. Its body is a decode loop over a length-prefixed input stream that alternates between
two kinds of byte-copy sites:

- **Literal-run copies**, e.g. `recomp_0012.c:179365-179389` and `179568-179615` —
  `MEM8(esi) = LO8(ebx); esi++; ecx++; edi--;` in a loop counted by a decoded run length.
- **Back-reference copies**, e.g. `recomp_0012.c:179410-179441` —
  *Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*
  where `edi` (this function's own local, computed as `esi - distance - 1` a few lines above, e.g.
  `recomp_0012.c:179395-179401`) is a pointer *back into the destination/already-produced data*,
  not the source argument.

This is the same length-prefix decode logic as `sub_001E9080`/`sub_001E91B0` (section 3), just
extended to actually perform literal and back-reference copies into `esi` instead of only
computing a length. That is the signature of an **LZ-family / dictionary decompressor for a
proprietary length-prefixed string format**, matching the brief's "8 byte-copy sites, 3 args,
optional length out-param, reached from a Flash string path." **I could not identify it as a
standard named CRT/compression routine** (it is not zlib's `inflate`, whose state machine looks
very different) — my best-supported characterization is "the game's own compressed/encoded string
unpacker," paired with `sub_001E9080` as its "measure the decoded length only" counterpart. I
would not stake much confidence on a more specific name than that without cross-referencing
strings/symbols elsewhere in the binary, which I did not do.

The crash write itself (`ecx=0x80F2005B edx=5 eax=0x77`) is consistent with the **literal-run
copy** site at `recomp_0012.c:179365-179389` context (`MEM8(esi)=LO8(ebx)` etc.) or a similar
literal loop — `edx=5` reads as a small remaining-count, `ecx` as the advancing source pointer,
`eax=0x77` as the last byte fetched (0x77 = ASCII `'w'`, plausible for a normal-looking English
Flash string) — but I did not attempt to identify the exact one of the 8 sites from the register
snapshot alone; several sites share the same three-register shape, and doing this precisely would
need either a byte-level breakpoint or matching offsets in a debugger, not just a static read.

---

## What I read vs. inferred vs. could not determine

**Read directly (quoted above), high confidence:**
- `sub_00181D20` has exactly one caller, which passes zero arguments; `MEM32(esp+0x10)`/`edi` in
  its frame is therefore necessarily a local, not a parameter.
- The single assignment to `sub_00181D20`'s `edi` comes from an out-param write inside
  `sub_001E69D0`, on a resource/handle-table lookup keyed by a per-slot struct field.
- The exact push/pop arithmetic proving `sub_001E9270`'s destination (`esi`, arg1) traces to
  `sub_00181D20`'s `eax` at the call site, and its source (`edx`/`ecx`, arg2) traces to
  `sub_00181D20`'s `edi` — i.e., the *opposite* pairing from what a naive reading of the brief's
  step 1 suggests.
- `sub_00181D20`'s `eax` at that point is the return value of `sub_001E9E70`, a tail-call wrapper
  to `sub_001E9AB0`, a genuine free-list sub-allocator (bucket table, block-header magic tags,
  explicit zero-returning failure paths).
- `sub_001E9AB0`'s size argument is the decoded length from `sub_001E9080` (via the
  `sub_001E91B0` wrapper), the same length-prefix decoder `sub_00181D20` also calls directly.
- `sub_001E9270`'s copy loops are literal-run and back-reference copies driven by a decoded
  length prefix, not a flat `memcpy`/`strcpy`.

**Inferred (labeled as such above), lower confidence:**
- That the per-slot struct field at `+0x108` and the globals `0x2EAB4C`/`0x2EAB54` belong to a
  single "current Flash slot" context structure. Plausible from the repeated indexing pattern but
  not independently confirmed.
- That `sub_001E9270`/`sub_001E9080` implement a proprietary LZ-style compressed-string format
  used by the Flash/localization system. Behaviorally well-supported, but I did not find or check
  a name for this format anywhere else in the codebase.

**Could not determine:**
- Why `sub_001E9AB0`'s free-list search returns a pointer in the `0x00076C78`–`0x00077158`
  code-segment range on the bad call specifically. This needs the runtime values of
  `MEM32(0x2EAB54)`, `MEM32(0x3C9138)`, `MEM32(0x3C9140)`, and the relevant `0x3C9158` bucket
  entry at the moment of the bad call — none of which I have from a static read.
- Whether this is a recomp/lifter bring-up bug (e.g. these allocator control tables not being
  initialized the way they would be on real Xbox) or a pre-existing heap corruption from an
  earlier, unrelated write that this call is simply exposing. I could not distinguish these two
  hypotheses from the static code alone.
- Which of `sub_001E9270`'s 8 byte-copy sites is the exact one hit at the measured crash (several
  share the same register shape).
- A concrete name/identification for the `sub_001E9270`/`sub_001E9080` compression format.
