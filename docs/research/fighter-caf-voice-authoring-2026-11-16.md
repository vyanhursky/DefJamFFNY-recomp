# Bounded CAF voice and mouth authoring (2026-11-16)

This local R&D profile extends the reviewed CAF donor round-trip. It does not
admit arbitrary body curves, palettes, bone destinations, pointers or programs.
Reviewed entrances: Ice-T `CI_132A` (65 source ticks) and Blaze `CI_113A` (106),
with 30 source ticks per second. Existing `CE_132A` cue support is unchanged.

## Native facial path

Body, face and secondary controllers sparsely replace fields of the same94-row
pose. Native24430 looks up `_t`, `_s`, `_p`;22010 stores the face controller's
`_s` and `_p`, and22150 evaluates `_s` through vtable+18 before `_p` through+30.
A type13 appended below `_p` would not animate: its+30 entry is a no-op21B60.
Type25 uses FDB40 at+30; its+18 is a no-op. Type15 traverses children in reverse
serialized order. Role names alone do not establish executable support.

The closed compiler in `setup/fighter_caf_cinematic.py` adds a face `_s` parent
whose original controls come only from the same reviewed body. One generated
16bit-delta type13 targets Jaw69 quaternion destination832. `jaw_open`0..1 maps
to local+X0..12degrees; the limit is conservative authoring policy, not proof
against all intersections. The native CAF selector1 palette supplies15 lip
expressions, with quaternions916/892/844/952 and translations920/896. It does
not include Jaw69 or Blink68. Existing selector0 brow/squint edits remain
separate. Eyes, mouth surfaces and other composed parts retain native weights.

`fighter-cinematic-caf-performance-2` accepts exactly format/template/edits/
mouth/speech_tick. Each jaw/lip track has2..256 increasing whole source-tick
keys, neutral at both endpoints; jaw values are finite0..1, lip IDs integer0..14.
The compiler checks both CAF rig identities,94-row topology, palette/sample
capacity and decoded quantization error. Body/root/hands/cameras and non-speech
events remain donor-derived. Speech onset is one compiler-selected original
intro-start event; redundant original speech starts are not copied to the
private timeline. Original retail resources are retained unchanged.

## Resident audio constraints found by native failure

A valid PCM stream is not sufficient native cinematic admission. Native38440
reserves/loads only0x25800(153600) bytes for an entrance.3C400 reserves/loads
0x7D000(512000) bytes for a victory.1ADD0→1E6750→1E64A0 carries that bounded
read.11EFB0 then asks1E7CD0 to scan resident chunks to SCEl, with no length.
An oversized imported stream can therefore crash at speech startup before its
footer is resident. `fighter_voice.presentation_stream` now validates actual
encoded size by purpose at composition and binding admission; general combat
bank parsing retains its separate limits. Never increase just the read size:
the arena allocation/slot ownership would also need a separately validated change.

One private36kHz3.51014s PCM donor re-encode(253283bytes) demonstrated the failure.
The supplied24kHz3.13471s line is150827 encoded bytes and fits. Unchanged donor
comparison must retain its original compressed retail stream, rather than
assuming a decoded/re-encoded WAV has the same native loading properties.

## Blender and portable projects

`scripts/blender/fighter_cinematic.py` loads the actual hierarchy, weights and
serialized inverse binds through `fighter_blender_preview.py`; coordinates are
native(x,y,z)→Blender(x,-z,y), reversible. CPU preview retains native evaluation;
the displayed armature is not an arbitrary bone-export mechanism.

The FFNY sidebar's Voice & Lip Sync panel imports/embeds audio, displays its
waveform and exposes Jaw Open/Lip Shape plus a manual key button. Native lips
smoothstep between pose keys even though their Blender ID-selection curves use
Constant interpolation. Jaw curves use Linear keys and native quaternion nlerp.
The preview's5tick audio offset is a measured approximation; positive native
capture must confirm a particular performance. Moving audio does not implicitly
retime mouth keys. Changed preview FPS, extra audible layers, trimming, volume,
pitch, speed and curve modifiers are rejected instead of silently omitted.

The optional local `scripts/fighter-speech-align.py` uses PocketSphinx with the
provided transcript. It rejects omitted words and maps phone timings to coarse,
editable native poses through `fighter_caf_mouth.phoneme_guide`. These are
starting estimates, not a phoneme-complete facial rig or finished acting.
Rhubarb1.14/1.13 macOS binaries crashed during local recognizer startup; those
attempts are retained privately. No audio was sent to a service.

The paired Workshop source stores `performance.cinematics.intro` as a closed
source document plus voice SHA256. Save/reopen/export preserve those keys;
changing donor or audio without a corresponding authored update is rejected.
Its runtime export passes the typed source through the ordinary compiler.
Older Workshop builds reject this optional field; use the paired research build.

## Evidence boundary

Private captures, projects, documents, script provenance and exact reports are
kept in the owner's authoring workspace, outside source control. Source includes
invented-data tests only. A successful Blender export is not native acceptance.
Qualification is limited to recorded CAF identity/outfit/venue/transitions; no
broad injury/outfit/platform or polished acting claim follows from this proof.


## Follow-up articulation and timing boundary

A second private authoring pass keeps the same3.134708s recording and donor.
Manual coarticulation narrows AY/EY vowel endings, reduces exaggerated open/grin
poses, relaxes the closed pause and centers the M closure. Its maximum jaw
control change is0.18per source frame versus0.63in the initial guide. These are
character-specific authored keys, not a new universal phone-to-face mapping.
Two native runs reproduce all11 sampled facial quaternions exactly at187
shared source ticks; untouched blink/brow/eye/squint channels also remain exact.

Map voiced audio fingerprints to the *local recorded animation-clock curve*,
not a time origin inferred from the first positive pose. Startup observation
can bias that first origin by20–25ms. Even after this correction the same
candidate shows median mixed-audio offsets of approximately5.0and2.8source
ticks on separate runs; a normal reference replay also shows about3ticks.
The5tick preview delay is a calibration assumption, not an authored speech
start: event59 is still at speech_tick0. A one-frame anticipatory mouth
variant is an explicit authoring compromise for that range, not a native fix.

Recorder pose events timestamp presented-frame observations, not evaluator
entry. Its audio clock interpolates buffered file-size observations and
measures produced mixed PCM, not speaker latency. Do not infer a dispatch bug
or change native clocks from these measurements alone. The next decisive
trace must timestamp actual34CF0/1D1F0speech dispatch and compare it separately
to local pose observations and the audible PCM fingerprints. Consistent final
lip synchronization remains unqualified until that path is understood.


## Speech-start trace and opening-only refinement

`RECOMP_CAF_SPEECH_TRACE=1` enables bounded, read-only recorder events around
the original34CF0 cinematic callback and1D1F0 native dispatch. Both generated
bodies always execute; the probe does not modify clocks, audio or resources.
Each wrapper observes at most32calls. `cinematic_speech` event phases report
entry/return on the recorder clock. In event phases `slot` is the cinematic
participant; in dispatch phases it is an **audio stream channel**. The next
fighter also uses channel0, so pair an enclosed dispatch with its event rather
than identifying every channel0call as the custom participant.

Three recorded CAF entrances show positive animation poses before the speech
event. Event entry to successful dispatch return spans0.1–0.2ms at the
recorder's0.1ms precision; reference-file PCM origin, inferred from first-word
fingerprints, follows dispatch by about60/79/60ms. Relative to a local
presented-pose clock fit, that reference origin is about109/154/102ms after
animation origin. The file's initial silence precedes its audible W. These
observations separate callback/dispatch from mixed-PCM timing; they neither
measure physical speaker latency nor prove which scheduler causes variation.
Native clock changes remain unjustified by these recordings alone.

An onset-only authored candidate holds neutral lips through source4, forms
the rounded W by7, and holds the jaw at rest through6. All mouth keys from9
onward are retained; donor body/root/hands/cameras and original audio remain
unchanged. Native A/B matches all11 sampled facial quaternions exactly at179
shared later ticks; two edited replays match exactly at190shared ticks. Each
edited run matches the expected decoded pose within1.20e-7. Protected facial
quaternions are derived from actual palette destinations: selector1 lips
write bones70/74/76/79; jaw69is separate. In the sampled set the protected
bones are68/71/72/77/78/80. Do not classify79as an eye channel from its index.

Validation:67focused native tests including delegation/return-effects,
opt-in activation and probe budget; Blender9checks; three CAF entrance runs
with unchanged saves and no harness faults. The required quick run passes all
four game checks. Its unit row retains2653passes/74skips/1deselected and one
known temporary-path failure: `test_fighter_set_digest_is_the_documented_formula`
rejects macOS's redirected `/var` temp path. That target passes with canonical
`TMPDIR=/private/tmp`; the original failure is not relabeled as a full quick
pass. Final perceptual opening/lip-sync review remains the owner's decision;
skip/rematch/victory and broad outfit/platform qualification are not added.


## Preview-only slow playback

The Blender Voice & Lip Sync panel now provides Play50%, Play100% and Stop
Preview. It starts at the editing cursor and stops with Space/Esc, at the
native clip end, on a scrub, before a mouth-key insertion/import/guide/export,
or when loading/undoing/redoing a scene. Only its own sound handle is stopped.

`fighter_preview_playback.PreviewAudio` pads a temporary PCM buffer to the
original voice offset and donor timeline. A temporary Audaspace reader slows
that sound; its output position multiplied by playback rate drives the source
frame/subframe. The original scene FPS, strips, mouth curves, packed sound and
exported WAV are never retimed. Slow preview intentionally lowers voice pitch;
the UI labels that behavior. Export stops the transient player first. No slow
mode or device handle is serialized. Blender4.5 TIMER events expose no public
`event.timer`; the modal handler uses event.type and the owned audio clock.

Actual Blender4.5.9 checks cover both rates, seek/scrub, stop, native end,
editing, export while playing and scene reload. Normalized full export
documents and voice bytes match before/after; the performance also matches
the earlier native-tested v05 exactly. Native export timing remains unchanged.
Eight preview checks and the existing nine voice checks pass, plus32focused
preview/mouth unit cases. The existing preview-model group also passes.
Live UI verifies both buttons, Stop and Space/Esc. Source code under src/ and
the toolkit are unchanged; no new native-game qualification is implied.
