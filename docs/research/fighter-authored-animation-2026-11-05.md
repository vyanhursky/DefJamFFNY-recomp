# Authored participant animation registration — 2026-11-05

This is a local M2 implementation checkpoint, not a shipping format. No external
project code is used. Generated native C, original resource bytes and captures
remain ignored local evidence. Initial native CPU acceptance passed; broader
four-participant authored-clip coverage remains pending.

## Action-to-animation join

Primary inspection of1B4930 at1B4A5E confirms WWAZ[action] word1(+2) becomes
actor+FB4 = participant slot*1000 + MNL ordinal. Word0 low12 selects the primary
WAZA row, independently.1A85A0 stores the encoded motion in actor+88; IDs below
10000 select participant-bank mode1. A0830 divides by1000, gets the slot loader
through9FFA0 and resolves MNL row suffixes through9FFF0.9FFF0 supplies bank row
indices for t/s/e;243B0 binds their contexts. Native actor time comes through
1A76A0/446C0/446F0/9EF00/9EF60/9ECB0/9E050.

Therefore participant MNL ordinals must remain below1000 even though the file's
count and bank lookup indices are wider. Four loaded participant banks are a
separate capacity. Special action windows31..34 and38..41, external IDs10000+
and the additional follow-up offsets in1B4B63 are distinct paths. A changed
WAZA ordinal alone does not register an animation or prove event compatibility.

## Implemented compiler profile

`fighter_animation_tracks.py` accepts explicit finite unit quaternion samples
for named rig bone ordinals. The caller pins the exact verified Skeleton pose
identity (including physical ordering/permutation), not just its bone count.
The native type11 writer uses16-bit quantized scalar deltas and measures error
using the established native float32 accumulation order. Maximum component
error is0.0001; adjacent antipodal hemispheres are rejected because the native
interpolator does not correct them. Input/sample/byte budgets are explicit.

`fighter_animation_compile.py` replaces a named token's skeletal `_s` record
with a generated type15/type11 record in a hash-verified local template. It
requires full rig quaternion coverage; partial tracks cannot discard other
bone channels. It preserves the original names/MNL ordinals, paired `_t`
record, parent metadata, duration and relocation-backed attributes. Samples
cover every integer child-time tick through the inherited duration endpoint.
No raw creator control records, vtables, imports or addresses are emitted.
Other template records remain inherited from the verified local source.

The parent attribute map at+4 is a pointer, not an opaque numeric control.
EE2D0 can enable a time scale using attribute key1's low byte; EDF90 applies
that scale to incoming time. Type11 ED000 consumes child time directly. The
writer retains this native runtime policy instead of guessing60fps from a
filename or assigning a meaning to the parent's metadata bits.

`fighter_animation_archive.py` adds separately allocated banks starting at1000
and skips occupied filenames. Original archive members remain unchanged.
FBA1 receipts map full owned core IDs141..16383 to bank numbers1000..99999;
several cores may share a bank. Maximum library4096 resources; archive512MiB,
individual relocatable envelope64MiB. These are explicit supported-profile
budgets, not claims that every such population has passed a performance test.

23 focused tests pass: exact source/rig identity, alias isolation, unchanged
paired records and names, inherited timing, malformed poses, destination
bounds, quantization, two resources and shared bindings across core255,
occupied bank numbers, tampered receipts and arbitrary resource-field rejection.

## Next acceptance gates

Full native type11 timing/cache/scatter comparison is prepared locally; filtered
selection and parent binding need independent coverage. Then register the
compiled archive through the existing four-slot native loader and verify new
motion in two packs with humans and CPUs. The source template's trusted opaque
records are not blanket permission for untrusted imported animation files.
M2 still needs authored move/event, AI and cinematic coverage; this compiler
alone does not close those gates or M1's preview clarification.

## Native evidence, first checkpoint

The ED000/FC3F0/FC8A0 oracle exercised the emitted type11 descriptor, key cache,
fractional interpolation and destination scatter:20 invented cases,220
calls and77,880 float slots, zero byte differences including untouched lanes
and guards. Inputs include repeated, backward and out-of-range times. This
covers the unfiltered evaluator, not every filtered or parent route.
`logs/fighter-authored-animation-oracle/comparison.json` and
`logs/fighter-authored-animation-oracle-nov05.txt`; extracted bodySHA
6dda9c2b6fb39c59f98b571c6d78c90f24882ae0ec14b03285f71dad8a100639.

The compiled native adapter passed12 MSVC tests for independent core/bank IDs,
shared banks, inactive/retail fallbacks and malformed receipts. The initial
CPU native run (`logs/run-20261105-034831.log.err`, harness report
`logs/fighter-authored-animation-cpu-native.txt`) loaded banks1000..1003 for
cores256..259 and passed five combat assertions.173 frame reports:
min106/median120/max120, no crash/watchdog/debug-layer/truncated-batch or
unresolved-call faults, one save generation restored byte-identically.
The latest periodic watch total was1545 ED000 calls; subsequent trace entries
continue through1638. Two wrapper identities occur in that trace. This proves
execution of generated tracks, but not a distinct authored clip on every
participant. Captures40/60s show ordinary combat before the selected grapple
clips ran; they are not visual proof of all authored motion.

A subsequent AI/animation acceptance fixture expands replacements to solo
attack tokens as well as grapples. Four-human coverage, resource attribution,
filtered evaluation and the remaining M2 behavior domains remain open.


## Four-player combat attribution follow-up

Retest044717 passed6combat assertions,199frame reports93/120/120, zero
crash/watchdog/debug-layer/truncated-batch/unresolved-call diagnostics, and
one verified save generation restored byte-identically. Driver result:
`logs/fighter-authored-moveset-live-retest-native.txt`; native log:
`logs/run-20261105-044717.log.err`. Exact command is retained in the adjacent
local .ps1 fixture. Captures are in
`logs/fighter-window-runs/9ad541635c434669824fbd1dabd80662/captures`.

During phase1, read-only memory attribution matched28 observed context/record
pairs, zero unmatched, across all4slots. In addition to descriptor SHA and
header/destinations, this check follows each bank's actual record-table cell
to its parent/child and verifies the relocated descriptor address. Slot0
resolved only appearance-alpha/first (core256), slot1 beta/first (core258),
slot2 alpha/second (core257), slot3 beta/second (core259). Evidence:
`logs/fighter-motion-probes/8faff9d01b544258b1c7e1251c3fd287/animation-live-combat-proof.json`.
This proves observed authored resource execution for all four participants;
it does not claim complete coverage of every compiled motion token.

Combat-only selected-action logging also records action54 for cores256/257
and action56 for258/259. Those selections use the validated action-family
aliases. The companion6/5 selections were not positively observed in combat.

One earlier repeat044235 omitted the explicit browse stage and never started
a match. It was deliberately stopped, with118frame reports106/120/120 and
identical save restoration. It is a fixture failure, not a runtime pass.
