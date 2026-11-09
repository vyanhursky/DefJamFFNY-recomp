# Workshop standalone CAF export — 2026-11-08

Development companion to Fighter Workshop roadmap steps 1–3, based on public
`research/custom-fighter-mods` at `807fd41e8886e40cc934550db7190611f2769553`.
Toolkit pin remains `4801dc171da7d39ebf23c2fe709d14e4b50a1733`. This is local,
unreleased work; the existing Custom Fighter shipping gates still apply.

## Contract and ownership

A pack uses the existing `fighter-registry-draft-1` resolver and may declare a
`caf` component with source format `caf-fighter-1`. Its SHA-256-bound JSON has
five training stats, one to three distinct retail styles, 38 CAF choices and
38 colors. No Story container, currency, career progress or source path enters
the recipe. Original SOD tables validate clothing row/category/fitting/color
references; pinned original CAF archives validate resources. Unverified
right-wrist encodings are refused. Paired right-ear selection follows the
original left-ear builder. Original CAF motion combinations occupy saved core
IDs87–141; these are separate from authored owned cores142 and above.

The shared compiler emits `fighter-caf.bin` (`FCA1`, version1, 232-byte rows)
and a hash in the normal cache/environment receipt. The native reader checks
that receipt and bounded row structure before activation. CAF generation may
currently coexist with sourced portraits, but combining it with other sourced
fighter components is refused. No new installation path or private workshop
pack format is introduced.

`fighter-contract.py export-caf-portrait` reads a bounded PNG and converts it
through pinned original UI templates into the existing six-part
`eagl-portrait-1` source contract. Only raster bytes change. Native quad/import
relationships determine tiling and used extents; missing transparent corners
are preserved. The captured view is trimmed to its alpha bounds. Square grid
and result artwork uses a head/shoulders crop. No original model, action or
executable is accepted from the PNG.

## Native CAF lifecycle

The match service already owns four CAF contexts, 0x1c bytes each. The adapter
binds each standalone recipe to its participant and uses original construction,
assembly, combat-stat conversion and destruction. A process-lifetime scratch
object supplies only invented fighter fields to those original routines.
Training/style bonuses are rebuilt without career-derived charisma.

The full original `64170` initialization is required: calling only its body
builder allowed setup to finish but stalled motion transitions at combat step31.
Its debug match-loader reload cannot be used: `9D0E0` reads missing
`assets/cp/cp_def<slot>.xml`, overwriting the already assembled recipe. Narrow
wrappers retain the assembled visual for the exact live CAF context; retail,
Story and unrelated visuals delegate to their original implementations.

The single-preview allocator installed by `62960` is only1.5MiB and corrupts a
second CAF's palette bindings. Match contexts use the original normal game
allocators instead. Battle's `1E410` lookup normally translates a participant
through a signed-in Story-profile index; a standalone CPU has no such index.
The adapter resolves only its exact live participant/context pair and delegates
all other lookups. Mappings clear at setup, native Game.Quit and teardown.
Native CAF motion rows also cannot stand in for standalone speech templates.
A further232-byte row field records the declared retail voice donor core. A
nested audio-setup value substitutes only those template keys, retaining actor
motion cores. Without this, dual-CAF loading loops in1E7CD0 looking for an SCEl
stream chunk in BNKl bank data. Both House and Blaze donor controls reproduced
the failure before this adapter.

Optional `--trace-caf-motion` emits bounded decoder/actor diagnostics; it is off
in normal use.

## Validation and retained failures

Apple Silicon native Release build succeeds, with143 manual addresses checked.
The public R&D baseline needed explicit guest-pointer casts in three
C files for Apple's Clang (local commit `673e641`). All fighter unit fixtures pass **1437/1437** in
`logs/caf-fighter-suite-final.txt`. The earlier aggregate had1435 passes and two
failures because macOS temporary paths contained `/var` symlink components;
canonicalizing the authoring CLI's temporary directory fixed those failures.
A later teardown-fixture extraction needed the new CAF clear callback; its
first aggregate had1432 passes/five compile errors. The updated fixture now
checks that CAF bindings clear only after native/CPU destruction; all five
cases pass. Workshop Python checks pass61 with two filesystem skips. Real macOS Qt tests
pass12 workflow steps including save/reopen, metadata, portrait capture and
complete validated ZIP export. The final frozen Mac app builds and starts with WebGL/preview/icon in1.01s
using two copied profiles. Its helper passes complete portrait-bearing pack
compilation (`native_compilation:true`); earlier bundled PNG conversion also
passes. These compiler receipts correctly retain `native_playtest:false`.

Native `run-20261108-221802.log.err` plays Workshop Demo100 against retail
Blaze variant82, reaches results, writes/closes Options and commits one verified
profile-store generation. Independent checks of the actual pair pass five
combat assertions (telemetry, setup, movement, attack, damage). The command's
expected opponent101 was wrong because an extra A selected a retail outfit;
that original identity assertion remains a failure. A prior single-CAF run
also demonstrates attacks/damage but its short direction pulses fail movement
acceptance. These are qualified evidence, not rewritten aggregate passes.

Earlier native failures are retained: missing debug XML caused a crash at98D40;
body-only initialization stalled at step31; the preview arena caused the second
CAF crash at1128D0. Corrected construction now prepares both participants and
assembles both visuals. `run-20261108-224050.log.err` then stalls during loading;
its sampled game thread is in native audio stream-chunk lookup1E7CD0. The
Blaze-donor control `run-20261108-224714.log.err` reproduces that loop. Both
original failed commands remain failures; one was manually stopped after bounded
diagnostic reads and the guarded root restored identically.

After the voice-template adapter, **`run-20261108-225834.log.err` passes**:
`logs/caf-dual-audio-probe.txt` verifies exact menu identities100/101, both native
CAF assemblies (body2/core94 and body0/core109), and **7/7 combat/result checks**,
including movement, attacks and health loss. Native actors retain cores93/108
(zero-based) while speech templates inherit Blaze5/House63. A decisive CPU win
reaches both native match summaries; Options writes/closes5404 bytes and one
profile-store generation is verified. The route returns to Battle.96 two-second
frame samples have min77/median120/max121, with zero crashes, watchdogs, debug
layer errors, truncated batches or unresolved calls. Full save-root restoration
is byte-identical. This accepts the two-participant slice, not every style,
body, venue, donor or three/four-player configuration.

The final stock quick regression passes **5/5** in seven minutes:
`logs/regress-20261108-230945.txt` (`logs/caf-stock-quick.txt`). Non-slow unit
checks pass2367, skip74 and deselect1; all three golden frames match. The stock
fight supplies120 seconds with median120/min113 presents per two seconds.
This final aggregate also accepts the corrected native teardown fixture.

Every native probe uses the complete disposable-save-root guard and restores
that root byte-identically. A separate original-data audit matches all21 save
files. No save, game asset, generated guest source, executable, log or capture
is committed. Windows/Linux native qualification is pending.

## Decisions and hand-off

- D-new: Reuse the public registry/compiler and native CAF construction rather
  than transplanting a Story profile; standalone fighters cannot own a career.
- D-new: Keep source-runtime selection explicit in Workshop's development
  export. Stable Beta1 does not contain this companion contract.
- D-new: Reuse original retail style combinations and presentation donors;
  individual move/model/texture/animation authoring remains a later milestone.

Ready for source review on local `codex/workshop-caf-export` and Workshop
`codex/fighter-projects`. Keep the tested development pair together.
Before release, qualify Windows/Linux natively and retain the existing public
Custom Fighter installation, profile and capacity gates. No source push, publication or new release is authorized this turn.
