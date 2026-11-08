# Extended M5 continuation — November 8, 2026

Continues the [November 7 checkpoint](fighter-mod-m5-2026-11-07.md).
All recorded approvals remain in force. The owner made the native test machine
available on November 8 and authorized up to six hours of continued work.
Everything remains local: no push, PR, merge, pack publication or release.
This checkpoint is being updated during implementation; pending tests below
are not acceptance results.

## Verified starting state

Runtime branch `research/custom-fighter-mods` was clean at `7e99539`;
Tools branch `feature/fighter-authoring-m5` was clean at `269077f`.
Toolkit stayed at `d569ca10811cef67ec4e9fa2173088c2f9fd0580`.
No game was running when native work resumed. Original dump and immutable
Vendetta extraction remain the input sources, with generated data under ignored
`logs/`. No source asset is being silently replaced by a donor.

## Native explicit-absence result

The corrected single-voice626 component probe completed:
`logs/fighter-m5-voice4-1108-native.txt`, native log
`logs/run-20261108-043812.log.err`. It used a fresh guarded profile store,
selected logical menu100 against retail17, and passed five native combat
assertions. The harness reported zero crashes, watchdogs, debug-layer errors,
truncated batches or unresolved calls. The save area was restored identically.
There were zero verified save generations in this fresh-profile probe; it is
not new persistence acceptance. Presentation counters:129two-second windows,
minimum107, median120, maximum120.

Actual requests for the owned voice600 returned bank-row65535 for missing
Taunts families16625/16626 and Enviro40962/40963. Read-only sampler receipt
`logs/fighter-m5-voice4-1108-live.json` records838consistent reads, zero skips,
mask1 after loading and no different nonzero masks. The earlier pre-load mask0
is retained. This proves actual omitted-category resolution while Character
was registered. It does not yet prove a positive Character playback request,
device audio fidelity, or a second-match voice reload. The fixture still
inherits retail appearance/behavior and is not the full conversion.

## Lossless cinematic numeric reconstruction

`setup/fighter_animation_numeric.py` reconstructs typed18/20/21 leaves from
quantized seeds/deltas, dynamic/constant partitions and ordered destinations.
It retains explicit/implicit time, block alignment, float32 constants and the
two unused vector-header bytes. It does not resample into independent seeds.

`scripts/fighter-conversion-cinematic-numeric-audit.py` rebuilt all1512numeric
leaves in184bundles/1012members:644type18,623type20,245type21.
All174214decoded key-pose/interpolation comparisons passed. Receipt:
`logs/fighter-m5-cinematic-numeric-1108.json`. Body outputs use the established
94*48byte allocation; camera output uses the original256byte allocation.
This audit retains source envelopes solely for offline comparison. It does not
admit them as packages or establish native camera playback/scheduling.

## Versioned five-role admission — implementation in progress

New ordinary source `fighter-blazin-3` uses explicit slots containing
`fighter-motion-graph-1` documents. Earlier sources retain their existing
quaternion contract. The coordinator obtains actual compiled/retail appearances,
checks ordered rig joins and palette sample capacities, and generates FBP3
proofs after typed reconstruction. Creator packages cannot provide proof tables.

The new native path checks the whole compiled .data payload after normalizing
each relocation against the compiler's target offsets. The active CPU resource
must cover the complete payload. Five parents and the actual skeletal/root
indices are sealed. The legacy FBP1/2 type11 guard remains in place.

Palette provenance is captured around native21500/215E0 constructors through
the existing109F80 pre-fixup hook. This covers shared hands, normal faces and
created-fighter borrowed face components. Both21670/216A0 invalidate the wrapper
before underlying storage release; temporary loader metadata destruction does
not. The runtime checks current roots, bounded samples/destinations, numeric
values, frame requirements and output bounds. Each paired activation resolves
the actual participant's visual/model, checks pose initialization and a sealed
skeleton identity, then validates the actual face and hand context.

Focused host and native-C proof suites passed166tests before the new full
pair-composition fixture; the latter and existing graph tests passed34tests.
Native rejection cases cover stale/unobserved lifetimes, out-of-span arrays,
bad destinations/numerics, relocation/payload changes, wrong rig/initialization,
created faces and provider rebind. Full game playback is pending the re-lift and
Release build; no native full-graph acceptance is claimed here yet.

## Camera scheduling qualification

Original category2 scheduling already has four phases and ten cache entries.
The supplied `blazin_activation.txt` explicitly assigns BZ to shot1 and BY to
shots2–4. Native phase4 normally sets flag8: a separate absolute venue camera.
Earlier phases use same-bundle actor-relative cameras. An authored profile must
declare and test camera policy; merely renaming BY does not settle it. The source
contains no installer code or runtime patch establishing phase4 coordinate mode.
The two excluded source files are catalogue metadata `mod.ini` and cover art
`couverture.png`; the older phrase "installer/cover-art" was imprecise.

Remaining gates are tracked in the [acceptance ledger](../fighter-mod-acceptance.md).
The full ordinary Vendetta package and release acceptance remain outstanding.

## Subsequent native and installed-tool results

The first full-graph probe correctly stopped at its post-constructor byte seal.
Independent original-code inspection established that E68A0 initializes embedded
type25 dispatch fields before A0C40 returns; evaluator attachment mutates more
cache fields later. The corrected hook seals relocated bytes at E68A0 entry,
before those writes, and remembers the actual bank/allocation lifetime. FBP3
also seals legacy banks when mixed with full graphs, retaining their type11 guard.
It never rehashes serialized bytes after trusted native mutation. Relift/build
receipts: `logs/fighter-m5-preconstruct-relift-1108.txt`,
`logs/fighter-m5-preconstruct-build-1108.txt`. New constructor-mutation and
mixed-profile fixtures pass; final focused native proof suite94pass.

Corrected single-source626 graph fixture passed five combat assertions and menu
100/17, with no native faults: `logs/fighter-m5-fullgraph-1108b-native.txt`,
native `run-20261108-052243.log.err`. It loaded all eight owned graph banks;
that run did not execute a finisher.

The two-fighter human/CPU fixture then executed source slot2 twice, ordinal877
subject/878counterpart, with both actual actor contexts admitted. Native
`logs/run-20261108-053621.log.err` shows both role bindings and native teardown
releasing all8owned allocations to the full33553888byte free block. Presentation:
140two-second counters, minimum109/median120/maximum120; zero faults. One verified
save generation occurred; guarded user save restoration was identical. The
original probe's expected fixture keys were supplied in reverse lexicographic
allocation order. The corrected read-only verification in
`logs/fighter-m5-fullgraph-cpu-verified-1108.json` passes both identities,
immutable materializations and all7combat/result checks against that same log.
It does not rewrite the run or conceal the original assertion failure.

Installed Tools wheel adds `fighter pair`, calling shared runtime `export-pair`
before publishing typed source. All47source pairs/94roles exported and compiled
through the installed console from outside its checkout, including exact source
control matching and input sealing. Receipt:
`logs/fighter-m5-pair-export-corpus-1108/report.json`. Tools focused37tests pass.
The older `fighter-motion-graph-draft-1` research files are not implicitly upgraded;
new exported files explicitly declare `fighter-motion-graph-1`.

`eagl-portrait-2` now expresses all18selector/result/loading portrait and logo
variants. It reuses pixel-only templates and per-ID logo visibility, preserving
text fallback for other fighters. Retail oldMLoad's reversed-ID list has maximum82,
so appended logical IDs>=100 need no Rvariant. Offline validation compiles46/46
fighters and all828source UI files through the ordinary eighteen-role path:
`logs/fighter-m5-portrait18-1108.json`. Updated full input accounting
`logs/fighter-m5-source-accounting-art18-1108.json` has1313converted offline files,
184exact inherited files,384blocked and2excluded; every1883input remains
accounted. The single18-role fixture passes ordinary contract validation.
Native extended-artwork acceptance is in progress.

## Newly established event-timeline requirement

Exact donor FZUI behavior is not equivalent to the source event timelines.
All94source paired tag rows retain their mapped donor payload sequence but change
ticks. All47camera schedules differ; removing shake events leaves identical
non-time payload sequences. All4821changed/new tag events and all418added camera
events use complete payload tuples found in the verified original. This permits
a general typed baseline-event reference plus authored tick/order adapter.

The snapshot name at1A3ECF selects BOTH camera and tag lookup. It must remain
donor-owned for source3; an owned timeline profile must admit both together.
Tags also contain native state/effect callbacks, not just sounds. Do not truncate
events to animation key count or parent duration:56/94source rows have later
tags. The source camera XML contains five duplicate labels; original AC100 uses
the first matching timetable. A faithful conversion must explicitly account for
the shadowed appended schedules instead of silently selecting a different one.
This timeline adapter and native late-event scheduling remain outstanding.
