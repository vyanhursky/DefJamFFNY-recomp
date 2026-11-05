# Blazin resource registration and full-core audit

Local M2 investigation using the player's own dump/lifted code. No external
project code. The adapters now have positive owned activation and paired-finisher
playback evidence for human and CPU participants. The M1/M2 checkpoint carries
the final local handoff and testing qualifications; entries below retain the
investigation's earlier counterexamples and corrections.

## Verified joins

The packed WPAR tail has four8-bit fields decoded to u32 at D4,D8,DC,E0.
1B2090 decodes the WPAR at actor+AE4, placing these choices at BB8..BC4.
1B4930 actions31..34 and38..41 select the corresponding choice and decode
secondary WAZA row142+choice. Action35..37 are outside this profile.

1A8BC0 also reads these choices, through a computed loop pointer. That pointer
starts actor+B40 for action1 and advances4 per action; at action31 it is
actor+BB8. For38..41 the expression subtracts a further28bytes, again giving
BB8..BC4. The paired external motion family begins at10709+2*choice; adjacent
queries use the next motion. This arithmetic is not a direct index into the
ordinary per-participant MNL. Exact attacker/victim runtime attribution still
needs native observation before an authored-pair adapter is accepted.

1A8260 writes three outputs: base709, count164, mask address3BE628.
87090's call site87196 passes count/base/mask to A0990 on manager+438, then
A0C40 loads the name `blazin` using `motion/%s.viv`. A0990 allocates24byte
key rows,16byte record rows and12byte companion contexts per entry.
A0C40 assigns keys base+local ordinal. Hence Blazin local0..163 corresponds
to external animation ordinals709..872. This is proven from registration,
not just the coincidence that FZUI2 count873 minus164 equals709.

9FB30 compares the requested external ordinal against context+6C. Its high
path uses provider+74. A0BA0 looks up the raw key in24byte records at
provider+14 (count+2C), returning the matching row ordinal. A1190 then selects
the skeletal/root/event entry in the16byte row at provider+18; A10A0 obtains
the companion context at provider+28. These helpers do not directly subtract
709. A1980, a different simple-bank path, ignores its ordinal argument; it
was an unproductive trail for the Blazin join.

## Full-width core bug requiring an adapter

1A8180 clears164bytes (41dwords) at3BE628, then visits exactly four actors,
not41 actors. For each active actor it marks both bytes2*choice and2*choice+1.
For core>=86 it first replaces BB8..BC4 from the participant's created-fighter
choices at3B9288+16*slot. The original code assumes all higher cores have that
legacy meaning. Owned cores256..259 therefore incorrectly enter this branch.

An owned-core adapter must preserve declared WPAR choices, retain the native
profile override for original cores86..140, and rebuild a bounded mask from
the resulting four-participant choices. Inactive actors must not contribute.
Validate all choices before touching the mask or profile-derived actor fields.
For inherited resources the valid mask domain is choice0..81; this is a Blazin
resource limit, unrelated to fighter IDs. Native055646 now passes8combat/result
checks with all four owned choices preserved;349frame reports101/120/120,
zero five fault categories, one identical restored save generation. The
adapter's mixed retail/created/owned/inactive native fixtures also pass.
This is inherited choice preservation, not authored Blazin playback.

## Expansion questions

1A8150 has fixed primary/secondary debug/name-pointer lookup bounds2088/873;
its semantic use needs checking before adding parameter rows. The provider's
count/mask and WPAR encoded byte width are separate constraints. The special
choice threshold57 in1D0F80 changes native behavior flags, so merely appending
new choices and raising a count is insufficient. Preserve an explicit link to
the verified behavior family while allocating independent authored paired
animation resources. No guessed field meanings or enlarged adjacent globals.

## Other setup classification sites

The setup word at+A8[slot] is one-based core identity. These open-ended>=87
checks also classify owned cores as created fighters:

| Function/sites | Created branch effect |
| --- | --- |
|87AF0:87BA4,87C60|HERO name; property+1C from33E9E8[slot]/340370 or5; destination+D4; property+20=1. Ordinary path retains per-slot name and original variant.|
|87E20:88052|For property types0/1, chooses single-actor ownership rather than flag02000000-derived ownership.|
|89F20:8A147|When service24+344==0, sequence bound destination+D0 minus1 rather than minus2.|
|89F20:8A250,8A2A3|Created-only gates may select main+2D820 state13.|
|8A300:8A41C|In global mode2, selects sequence cursor10/8/11 for modes4/7/17 instead of ordinary name-based cursor selection.|
|8B440:8B4F3,8B612|Conditional created mapping setup+128[slot]=slot+1; skips ordinary+54C/+550 initialization; later mapping enables participant+ABB4 bit1 and alternate actor initialization.|

No second open-ended actor+2C gameplay core classification was found in the
bounded85..87 comparison audit. Some comparisons use actor+30 kind instead.
The AI producer's separate87..141 test has an upper bound and uses configured
identity V, not motion core K.

Temporary donor substitution across these five functions is not adopted.
Their immediate+A8 reads only classify, but8B440 reaches virtual callbacks;
another thread could also observe shared setup memory. The existing FIC1
adapter replaces the selected label and validates simple actor ownership,
which the native four-participant tests exercise, but that does not prove
every surrounding sequence-state branch correct. A localized classification
adapter or audited semantic replacement remains a follow-up.

## Combat join still missing

The verified ordinary combat setter at1C6381 calls1B4930 on its participant,
then passes actor+FB4 through1A8770 to1A85A0. The ordinary WAZA branch produces
FB4; the secondary>=10000 branch leaves the entry's cleared FB4 untouched.
Thus this path does not establish a conversion from10142+choice to the paired
10709+2*choice resources. The latter remains proven only in1A8BC0's loading
path. Do not infer attacker/victim ownership from FAC/FB0 stores or filenames.

The later bounded audit closes this execution join:1D3800's state3 branch
at1D3B4A checks actor+926 bit1, converts saved action+F50 to one of four
choices, and computes10709+2*choice at1D3B72. Calls returning at1D3BA0 and
1D3BAA pass that ordinal to the selecting subject, then the adjacent ordinal
to its linked counterpart at subject+0.1D3800 is cdecl with actor at ESP+4;
1A85A0(actor,motion,mode) is also cdecl. The latter subtracts10000 for the
external-provider query. Native state-table dispatch, not a direct call,
enters1D3800.

BlazinPairs now appends independently named subject/counterpart .ord/.orl
banks and MNL tokens, retaining every original bank and the original token
prefix. It authors full-rig quaternion tracks while preserving inherited
root/event/face/hair records and timing. FBP1 validates full-core-to-choice
bindings, exact role names, ordinals, part hashes and the final archive hash.
Eight focused tests pass; four original-data pairs compile at873,875,877,879.
Ordinary source admission and native registration were implemented subsequently;
the live acceptance evidence is recorded below.

The planned provider contract is capacity=164+new motion tokens, base=709,
and one mask byte per token.1A8260 emits709 then164, but87090 reorders these
for A0990:capacity first, base second. Provider+2C is capacity,+30 is709,
+34 is mask. A0C40 completes its synchronous token loading before returning
to871C1; validate every admitted key and loaded _s/_t record at that boundary
to prevent native missing-key fallback to row zero.1A8150's original873-name
lookup also serves an actor-state snapshot, so added names need an explicit
lookup adapter; do not resize its neighboring static table.

## Activation sequence registration, distinct from combat pairs

87AF0 receives parser family4 at request+0 and category2 at request+C for
Blazin activation. Request+4 is the visual participant slot; join it to
3B90B8[slot] and verify setup+A8[slot]==core+1. Request+1C becomes descriptor+D4,
the zero-based shot ordinal. Request+18 is a separate camera selector.
The unrelated parser0/category4 request at8B120 is not this sequence.

87D13 passes that participant's name toA1F60. Its descriptor+A8 copy persists
across asynchronous XML loading, allowing an allocated owner label without
temporarily changing shared fighter configuration. A3B60 selects shot D4+1
from Blazin.xml, then callsA3160 with descriptor+61 atA3D3E/A3D5E. A3160 copies
the name into its owned record+90; A3E80 later loads the body bundle using the
persistent+61. Thus substitution must update+61 beforeA3160 copies it.

For phases0..2, A2190 derives EYE/TARGET symbols from+61. For phase3,
87CF9 sets flag8, and A3B60 writes BT4V plus venue suffix to+1D afterA3160
returns. A22A0 loads this independent camera. The adapter must preserve+1D,
flag8 and native cleanup; A3670 releases both handles and the owned record.

The typed compiler assigns six-character Bnnnnn names and preserves parsed
body/face/hair/root helpers, plus camera helpers for the first three shots.
FBZ1 carries four names per full core, hashing the final shared v2ta archive.
The original-data probe compiles all four roles, and ordinary creator manifests
now compile two packs/four resources. Native acceptance is still pending.

**Live correction:**87AF0's slot is a preload owner for activation, not the
current playback participant. Native101354 positively evaluated core141's
custom clips on cores143/144. The shared cache has ten activation descriptors
(one/four/four/one variants) initialized with slot0. The corrected adapter
appends private ten-descriptor groups per participant and leaves the retail
shared group untouched.88DD0 selects the group using manager+2D844, which is
written before all verified playback selector calls.88FF0 polls the private
loads. State6/89B30 waits for readiness, preserving the pending activation;
it is retried by8BE60.89310 owns cleanup of the enlarged allocations. Focused
tests pass and native retest103546 completed: all four phases evaluated for
three CPU owners, with zero ownership mismatches. Human activation remained
unobserved in that run.

## Native paired-motion implementation and live evidence

The FBP1 adapter implements the provider contract above without changing WPAR
choice width or the existing static name table. It owns one guest allocation
containing the expanded mask and persistent added names, and releases it only
after89310's native provider destructor. A0C40's verified caller validates
loaded key uniqueness, names, record indices and type15/type11 body linkage.
The1D3800 scope preserves the subject and counterpart across both1A85A0 calls;
the subject's core selects both roles, including a counterpart from another
pack. Unrelated motions retain native dispatch.1A8150 resolves only admitted
external names.63 focused native tests pass, including malformed receipts,
overflow ordinals, cross-pack roles, nested scopes and cleanup.

Native111321 loaded10 active motions: the two retained original roles plus
eight authored roles for four fighters. The live sampler positively evaluated
both roles of two independent pack resources during cross-pack finishers,
checking indexed names, descriptor hashes and current external actor ordinals.
All four participants, including human core141, also evaluated their four
owned activation phases. No sampled ownership mismatch occurred. This run's
match/result/save checks and final stock regression are still in progress;
refer to the M1/M2 checkpoint for the completed verdict.

**Counterexample and correction:**111321 timed out without a decisive result;
112733 was stopped when a separate unchecked parameter index was identified.
1A8641 uses actor+8C to index the original873-row FZUI table (3B8634, stride at
3B862C), independently of the expanded animation provider. The visible paired
poses were correct, but added IDs read unrelated parameter bytes. This invalidates
paired gameplay acceptance for both runs. The1A38B0 wrapper now substitutes the
complete inherited39-byte row at the sole verified caller1A867E, with dimensions,
source-pointer and current-ordinal guards. Animation IDs remain independent.
The native decoder still owns all136 decoded bytes, including reaction/completion
fields.66 focused tests pass; corrected native acceptance remains pending.

The motion name has a second behavior consumer:1A3ECF publishes the snapshot
label used byAC100's camera-script lookup. An owned Pnnnn_A/B resource name has
no corresponding inherited camera script. AC100's missing-label fallback can
retain a prior zero multiplier; AC1F0 restores the countdown only in mode0.
The name adapter therefore returns the inherited donor's static label only for
the snapshot caller, while retaining the owned label for diagnostics and the
owned ordinal for actual animation loading. It does not rebind the static table.
The68 focused native tests include both label domains and complete FZUI rows.

Runs120229 and133930 reached victory but failed on results-screen APT errors.
A separate presentation compiler defect was identified: a generated Action
record was shared across two frames despite native in-place relocation on each
visit. The compiler now owns separate records and instruction/literal data for
each frame. This is independent of finisher dispatch; neither ignoring the UI
fault nor reaching a victory animation qualifies as full acceptance. The latest
M1/M2 checkpoint records the corrected run and final stock regression verdicts.
