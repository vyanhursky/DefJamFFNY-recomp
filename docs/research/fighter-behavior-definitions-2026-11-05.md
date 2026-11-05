# Ordinary fighter behavior definitions — local M2 draft

This extends the existing `fighter-registry-draft-1` resources. It is a local
research format, not a supported installer package or a completed M2 claim.
The launcher/normal-profile gates remain closed. Resource definitions contain
data; they cannot provide native archives, binding tables, pointers or code.

## Composition contract

`scripts/fighter-registry.py::compile_inputs` resolves the whole pack set,
validates appearance/portrait data, then builds a `BehaviorPlan` when sourced
behavior is present. Every added fighter in that generation receives its own
motion core. Resource identities remain separate: multiple fighters can share
one moveset, voice, AI profile or cinematic. A pack may define one or many
fighters; dependencies and conflicts use the existing resolver.

The compiler writes the allocated one-based core into the SODB record before
building native indexes, handle reports and participant windows. Zero-based
descriptor indices are used only by the runtime binding tables. The source
motion records, archive entries and retail fighter records remain intact.

Selected moves and their animation-name aliases are composed together. A
voice receives an independent voice ID. Cinematic labels bind to fighter cores
independently of appearance filenames. An omitted intro or victory clones the
verified simple donor sequence unchanged. Shared inherited sequences compile
once. Camera, facial, hair, root-motion and timing helpers stay native-owned.

Final appearance and cinematic composition share one NIS archive; hashes are
calculated after the last edit. `write_preview` accepts exactly the artifacts
required by the generated receipts and verifies existing cache bytes before
reuse. Its output remains under ignored `logs/fighter-native-preview`.

## Source forms

Every source uses an exact field set; unknown fields fail validation. File
references have `{ "path": "relative/file", "sha256": "64 lowercase hex" }`.
Paths must be ordinary contained files, with no symlink/reparse redirection.
One reader enforces a256MiB aggregate input budget and64MiB per file.

| Resource kind | Source fields after `format` | Format |
| --- | --- | --- |
|moveset|`donor`, `selections`, `tracks`|`fighter-moveset-1`|
|voice|`template_voice`, `samples`, `intro`, `extro`|`fighter-voice-1`|
|ai|`template_profile`, `tendencies`|`fighter-ai-1`|
|cinematic|`template`, `track`|`fighter-cinematic-1`|
|blazin|`shots`, optional `pairs`|`fighter-blazin-1`|

Moveset `donor` is an explicit retail fighter identity. `selections` maps
canonical decimal action strings to another validated action in the same bank.
The current ordinary action adapter covers1..124 except31..41, requires equal
control flags and unambiguous motion intervals, and rejects edits that would
change another action through an existing alias. `tracks` maps existing motion
tokens to quaternion JSON file references. At least one edit is required.
The source's declared skeleton/event family must match its verified donor.

Quaternion JSON has exactly `schema: "fighter-quaternions-1"`, `rig_sha256`,
`bone_count`, and `poses`. Every pose contains every bone's `[x,y,z,w]` unit
quaternion in the verified rig order. Original timing determines the required
sample count. JSON duplicate keys, non-finite numbers, excessive dimensions,
incomplete rigs, discontinuous quaternion signs and mismatched rig hashes fail.
The archive compiler retains verified root-motion and event behavior; this
does not introduce arbitrary new hit logic.

Voice `samples` contains optional `Character`, `Taunts` and `Enviro` maps from
canonical sample-index strings to WAV file references. Intro/extro WAV files
are explicit. WAV input is uncompressed mono PCM16 and is converted locally
to the validated native stream representation. Unchanged samples retain their
verified template. The template voice must match the inherited event family.

AI `template_profile` names a verified original profile. `tendencies` includes
`easy`, `normal`, `hard`, each with slots`"0"` through`"3"`. Each slot supplies
nonempty named edits with integer values1..5. Only the23 understood tendency
fields are editable; stage/trigger lists and `Specification_environment` are
inherited. Native profile fallback is treated as a failed binding, not success.

Cinematic templates use simple `CI_....` intro or `CE_....` victory bundles.
`track` references a quaternion JSON file. The component determines the required
category. Omitted categories are synthesized by the coordinator from verified
donor data, not by asking the creator for invented replacement poses. Counted
created-fighter variants, team sequences and Blazin authoring remain separate
adapters and are not admitted by this source form.

The separate `blazin` resource defines four activation shots, in order. Each
shot has a `template` (`BT1_nn`, `BT2_nn`, `BT3_nn`, `BT4Cnn` respectively)
and an optional quaternion `track` file. Omission inherits that verified
template's body animation. The first three shots retain their camera helpers;
the fourth retains the game's independent venue camera. Sequence control,
native payloads and helper pointers are not creator fields. This describes
activation presentation. Optional `pairs` maps canonical choice strings0..81
to two quaternion file references, `subject` and `counterpart`. A selected
choice must already occur in the fighter's verified donor WPAR; up to four
choices can be authored. Each pair receives independent external motion
ordinals while retaining the donor's event behavior, orientation rules and
timing. This does not reinterpret or expand the packed choice byte.

Blazin bundles are appended first, then intro/victory bundles. Both receipts
remain intact, and the binding compiler checks the explicit archive hash chain
and every selected bundle before binding the final shared archive. FBZ1 and
FIC1 therefore identify the same final resource generation. Native activation
now has independent participant caches: three CPU fighters positively play
all four owned phases, with zero ownership mismatches. Human activation is
still a pending positive check. Paired finishing-move source admission and
compilation pass, but their native provider/selection adapter is unimplemented;
do not launch a `pairs` fixture until that adapter is accepted.

## Reproducing the local fixtures

`scripts/fighter-behavior-fixture.py` uses the reviewed local appearance-alpha
and appearance-beta folders plus the player's verified dump to write two
`behavior-full.json` manifests and their JSON/WAV inputs. The generated files
stay ignored. It produces simple arm oscillations and distinguishable tones;
these are routing/rig tests, not finished art or voice performances.
With `--blazin`, it also emits `behavior-full-blazin.json`, including four
independent activation resources, without replacing the non-Blazin manifest.
`--finishers` emits `behavior-full-finishers.json` with both authored roles
of the retained finisher choice; this is currently a compiler fixture only.

Use those manifests with the ordinary `fighter-runtime-probe.py` command.
The compiler supplies all resource environment variables from its own receipts;
the diagnostic no longer needs to patch SODB cores or add binding files by hand.
The harness uses disposable profiles and verifies complete save restoration.

Synthetic tests exercise independent core allocation, shared resources,
unchanged retail records, window versus direct bindings, changed-source/output
rejection, exact cache publication and corrupted-cache refusal. Native testing
of the ordinary behavior path is in progress; see the M1/M2 checkpoint for
results and qualifications. No publication or M3 work is authorized by this draft.
