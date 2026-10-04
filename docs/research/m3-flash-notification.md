> **Confirmed at runtime, 2026-09-21 (main agent).** This report's central claim checks out:
> `MEM32(0x3B1DFC) = 0x00068D20`, so the real handler *is* patched into the live Flash dispatch table, and
> `0x345234..0x345240` hold the saved originals (`0x1801A0, 0x1819C0, 0x1813A0, 0x180FE0`) for chaining.
> The main agent's earlier conclusion that the install was skipped was wrong. The M3 dead end is therefore
> upstream of the notification: the SWF bytes never arrive to feed the tag pump.

# M3 — Flash asset-loaded notification: is the callback chain actually broken?

Research date: 2026-09-21. Source: lifted C in `src/recomp/gen/*.c` only (grep + manual read, no build/run).
Read-only pass, nothing modified. All claims below are marked **verified** (read directly in the lifted C)
or **inferred** (reasoned from structure but not traced instruction-by-instruction).

## The question

The request record at `MEM32(0x345220)` has `+0x41` (requested) = 1 and `+0x40` (loaded) stuck at 0 forever.
`sub_00068D20` is the function that would set `+0x40 = 1` on a name match, then chain to `MEM32(0x345240)`.
`sub_00069D30` installs `0x345234/238/23C/240` from a table at `0x3B1E1C/0x3B1DF0/0x3B1DF4/0x3B1DFC`, but
only if `0x34523C`/`0x345240` are both zero; at runtime they hold `0x001813A0`/`0x00180FE0`, and
`sub_00180FE0` is a bare `ret`. The task asked: who writes those four dwords, is the bare-`ret` handler
correct or a placeholder, what's the intended call chain, and what would the player need to do to call back.

## Finding 1 (verified): the "skip" is not what it looks like — the install ran to completion

`sub_00069D30` (`0x00069D30-0x00069E0E`, `src/recomp/gen/recomp_0003.c:28590`) has **exactly one call site**
in the whole lifted codebase: `recomp_0003.c:28909`, inside `sub_00069F10` — one of the two functions the
task's "already established" section says runs to completion during kickoff. So `sub_00069D30` executes
**once**, during kickoff, not repeatedly. Its body is:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

Since `0x345234..0x345240` are process-BSS and this is the function's only call, they were guaranteed zero
on entry, so the `D59` copy branch **did execute** during kickoff — it is not being skipped. The runtime
values `0x1813A0`/`0x180FE0` seen in `34523C`/`345240` are the *result* of that successful copy, not evidence
the copy was bypassed by a stale nonzero guard. (This directly contradicts the premise in the task's framing
that "the install is skipped.")

## Finding 2 (verified): who writes the source table, and what the copy actually installs

`0x3B1E1C/0x3B1DF0/0x3B1DF4/0x3B1DFC` (and ~35 nearby dwords, `0x3B1DD0..0x3B1E68`) are written by
**`sub_00182110`** (`0x00182110-0x00182282`, `src/recomp/gen/recomp_0011.c:12726`), which `sub_00069D30`
calls unconditionally as its very first action (`loc_00069D30`). Relevant writes there:

```
3B1DF0 = 0x1819C0
3B1DF4 = 0x1813A0   <- matches runtime 34523C exactly
3B1E1C = 0x1801A0
3B1DFC = 0x180FE0   <- matches runtime 345240 exactly
```

All of these targets are in `0x0017Fxxx-0x00182xxx` — the Flash-player module. This confirms `sub_00182110`
is the Flash player's own vtable/dispatch-table installer, and it is the direct source of the runtime values
the task flagged as suspicious. So the full picture for `sub_00069D30`:

1. Call `sub_00182110` → Flash player (re-)populates its own dispatch table with **real, working**
   function addresses, including `3B1DF4 = 0x1813A0` and `3B1DFC = 0x180FE0`.
2. Copy those (now-fresh) values into `345234/238/23C/240` — this is a "latch the original handler" step,
   guarded so it only ever happens once.
3. Unconditionally (every call, i.e. this one call), overwrite `3B1E1C=sub_00068E00`, `3B1DF0=sub_00069CC0`,
   **`3B1DFC=sub_00068D20`** — i.e. it patches the Flash player's live dispatch slots with game-side hook
   functions, layered on top of the just-latched originals. `3B1DF4` is deliberately left untouched.

So `0x345240 = 0x180FE0` (the bare `ret`) is **not** the installed "asset loaded" hook. It is a saved copy
of the Flash player's *original* handler for that slot, kept specifically so the new hook can chain back to
it. The actual installed hook, patched into the Flash player's own table at `3B1DFC`, is `sub_00068D20` —
and step 3 above installs it unconditionally, regardless of the guard in step 2. **Conclusion for Q2: by
reading the code, `sub_00180FE0` is correct as the chain-to fallback, not a placeholder indicating the
player never attached — the real hook (`sub_00068D20`) is present at `3B1DFC`.**

## Finding 3 (verified): `sub_00068D20` does contain the `+0x40` logic and chains correctly

`src/recomp/gen/recomp_0003.c:26142`:

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This matches the task's description exactly, and confirms the match/set logic is intact.

## Finding 4 (verified): `sub_00068D20` has no direct callers — it is reached only through `3B1DFC`

`grep` for `sub_00068D20` in all of `src/recomp/gen/` turns up only its own definition and its
dispatch-table entry (`recomp_dispatch.c:3333`) — no `RECOMP_ABI_CALL`. It is only reachable via an
indirect call through whatever currently holds `MEM32(0x3B1DFC)`. The only place in the lifted code that
performs `eax = MEM32(0x3B1DFC); ... RECOMP_ICALL_SAFE(eax, ...)` is `src/recomp/gen/recomp_0010.c:5799-5812`,
inside **`sub_00148210`** (`0x00148210-0x00148587`, `recomp_0010.c:5553`):

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

This `icall` is reached only along one path through `sub_00148210`: a loop that walks entries whose
`MEM32(entry+4) == 3` (`loc_00148270`, `recomp_0010.c:5602-5605`), preceded by calls into
`sub_0017BAD0`/`sub_0017CA50`/`sub_0017D180` (all `0x0017xxxx`, Flash-player-adjacent), then reaches
`loc_001483DB` only after that loop's data-driven exit condition. Other paths through the function
(`loc_0014856E`, the common epilogue; `loc_001484F8`, an empty-list early-out) return without ever reaching
`loc_001483DB`.

`sub_00148210` itself is called from exactly 3 sites, all in `recomp_0009.c`, all in the same
`0x00144xxx-0x00146xxx` module (an SWF tag/record-stream parser family that reads state out of
`0x3B1D84/0x3B1D88/0x3B1D8C/0x3B1DA0/0x3B1DA8` etc.):
- `sub_00144310` (`recomp_0009.c:52313`), call at `52387`, return `0x0014439A`
- `sub_00145D70` (`recomp_0009.c:56460`), call at `56813`, return `0x00146024`
- `sub_00146050` (`recomp_0009.c:56835`), call at `56918`, return `0x00146103`

## Answer to Q3: intended chain (verified structure, addresses as read)

*Guest-code excerpt omitted from the public source package; the surrounding analysis records its behavior and addresses.*

## Answer to Q4 (inferred, not fully traced)

If the hook chain above is correctly wired (Findings 1-4 say it is), the missing ingredient is data:
`sub_00148210`'s notify branch is only reached while walking a populated tag/record list fed by
`0x3B1D84/0x3B1D88/0x3B1D8C/0x3B1DA0/0x3B1DA8`-family state. This ties directly into the task's
already-established finding that the `.swf`→`.big` archive lookup for `screens/intMain/legal1.big` never
happens (zero watchpoint hits) — no bytes are ever delivered into that buffer. The likely conclusion is
that `sub_00148210`'s early-out paths (`loc_00148286`→`loc_001484F8`, empty-list) are what actually execute
for this request, never reaching `loc_001483DB`, because nothing ever feeds the parser real tag data.
**This is inference**: I did not trace who is supposed to write `0x3B1D84`/`0x3B1DA8`/etc. with the loaded
asset's bytes, or confirm at which exact point the missing archive lookup would need to feed this parser.

## What this changes about the original framing

The task's premise — "the install is skipped, so the installed hook (`sub_00180FE0`, bare ret) does
nothing" — does not hold up against the code: there is only one call site for `sub_00069D30`, its guard
branch did fire (BSS was zero on entry), and the function's unconditional tail installs a real, non-trivial
hook (`sub_00068D20`) at `3B1DFC`, not `0x180FE0`. `0x180FE0` in `345240` is a deliberately-saved fallback,
not the active handler. The callback plumbing for "asset loaded" appears intact by static reading; the
break is upstream of it, consistent with the project's separately-established finding that the archive
lookup for the asset's `.big` data never occurs.

## Recommended next step

Don't chase `sub_00069D30`/`sub_00068D20`/`sub_00182110` further — they check out. Instead:
1. Trace who is expected to populate `0x3B1D84/0x3B1D88/0x3B1D8C/0x3B1DA0/0x3B1DA8` (the tag-stream buffer
   state `sub_00148210` reads) for a given asset request, to find the actual missing link between "asset
   requested" and "bytes handed to the SWF parser."
2. Given the already-confirmed zero-hit watchpoint on the archive directory entry, put a write-watchpoint on
   `0x3B1D84` (or the record's own fields around `0x345220`) instead, to see whether *anything* ever writes
   parser input for this request, or whether the request genuinely dead-ends before that stage.
