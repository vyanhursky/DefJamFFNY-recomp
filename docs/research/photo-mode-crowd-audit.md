# Photo Mode crowd visibility audit

Read-only audit of the Xbox guest paths used by the Photo Mode branch at
`8a6576d` / toolkit `d108a64`. Source references below are lifted guest code;
the addresses are guest virtual addresses.

## Findings

- There are two distinct crowd paths. The **background crowd** is the manager
  updated by `sub_000DB870` (gate byte `0x2E3488`). Its `sub_000DB730` body
  dynamically writes per-member visibility bytes; it is not a spawn-only
  decision. It first rejects members farther than the float at `0x2E348C`,
  then asks the current scene/view object at `0x2E3490` through
  `sub_00019300` (`0x19300` delegates to `[this+0x34]+8`, then guest routine
  `0x103B10`) and stores the returned visible value at
  `manager+0x124 + 4*i` (`src/recomp/gen/recomp_0006.c`, `0xDB730–0xDB86E`).
  Candidate member transforms are read from the `manager+0x128` array at
  `+0x70/+0x74/+0x78`, stride `0x40`; count is `manager+0x11C`.
- The visibility update is entangled with animation: for a visible member,
  `sub_000DB730` may call `sub_000DB660`, which advances the member's frame
  cursor (`manager+0x124 + 4*i + 2`) and makes `rand` draws. `sub_000DB870`
  checks `MEM8(0x2E3488)`, calls `sub_000DB730` if nonzero, then tail-calls
  `0x115510` (`recomp_0006.c`, `0xDB870–0xDB88F`). Do not call the full update
  as a Photo Mode visibility refresh if crowd poses must remain frozen.
- Existing research measured `sub_000DB870` once per outer render-loop
  iteration, including iterations with no fight step; it is not tied to the
  fight simulation tick (`docs/research/deck-determinism-98.md`, §“What is not
  fixed”; correction in `crowd-nondeterminism.md`, lines 45–50). Thus freezing
  `sub_00079B60`/`sub_0007A8F0` alone does not establish that this background
  callback is frozen. The ordering between this callback and the Photo Mode
  publish at `sub_000796A0`/`sub_00079E40`, and whether `0x103B10` sees the newly
  published camera/frustum, are not established statically.
- **Foreground spectators** are actor/state work, not this background list.
  `sub_0007D2F0` chooses animation variants/names through generators
  `sub_000AA300`/`sub_000AA340` and updates the actor's state fields; its body
  has no frustum/visibility test (`src/recomp/gen/recomp_0003.c`,
  `0x7D2F0–0x7D4A5`). It is not a safe visibility refresh. The nearby
  `sub_001B8760` is fighter-vs-spectator proximity used by combat planning,
  not rendering; it must remain frozen with gameplay. Research reports that
  spectators can change CPU plans (`docs/research/crowd-nondeterminism.md`,
  lines 48–53), so do not invoke it from Photo Mode.
- `src/hooks/crowd_control.c` is test-only seed/hold support; it does not add a
  shipping visibility path. In particular, its prior experiment clearing
  `0x2E3488` for the loading window crashed on the first fight step because
  the gated callback also initializes drawing state (`crowd-nondeterminism.md`,
  lines 74–82). Do not clear that global gate for Photo Mode.

## Narrow candidate and limits

Owner decision (2026-11-22): implement full crowd visibility only if straightforward;
otherwise hold it for a future enhancement. This audit leaves it **on hold**:
the foreground path and camera/frustum ordering need native investigation before
a visibility-only override can be qualified without advancing animation.

For the **background crowd only**, the smallest candidate is a Photo Mode-only
visibility pass after the camera publish and before the world renderer, using
`sub_000DB730`'s distance/frustum predicate and writing only each member's
visibility byte. It must not run `sub_000DB660` or the `0x115510` tail callback.
An implementation could first capture the manager `this` pointer from
`sub_000DB870`, then use a dedicated visibility-only loop (or split that loop
behind a mode guard). This is narrower than disabling general world culling and
does not require advancing crowd poses or AI. Validate that `0x103B10` consumes
the view/frustum after `sub_00018F90` publishes the Photo Mode camera; that
relationship is the key unknown.

The existing distance threshold at `0x2E348C` still limits the candidate set.
If “all visible” means members beyond that engine radius too, that would require
a Photo Mode-only exception to this crowd manager's distance gate and carries
extra draw cost; no global culling override is justified by this audit.

This static read does **not** identify a safe visibility-only seam for the
foreground 3D spectators. Their renderer-side culling path and spawn/streaming
limits were not traced. If those are the NPCs the player means, do not change
`sub_0007D2F0` or global culling on this evidence; first trace the actor render
callback and its cull flags. The crowd visibility report is therefore a
bounded proposal, not runtime proof that a refresh fixes the observed view.
