# Retail source animation preview

The Workshop authoring tools expose `retail-animation-preview-1` in the API 1
capability manifest. `preview-fighter` keeps its static geometry and adds source
model/mesh identities and verified skin mappings. Compacted vertices retain their
original palette rows; zero-weight influences use safe zero indices.

`workshop-animation --pack <one-pack>` reads that pack's selected appearance via
the ordinary inventory/resolver and hash-bound files. The request identifies
`models: ["retail-body"]`; it never supplies arbitrary model paths or skin data.
The response uses the existing animation schema with source SHA-256, skeleton
topology, bones and weights matched to the exact preview vertices. A changed
body cannot silently receive an earlier body's weights. Without `--pack`, the
existing CAF model path is unchanged.

Supported original body/root tracks, 30 source ticks/second, sample budgets and
unsupported-codec refusals remain unchanged. Preview omits native cameras,
facial/hand animation, blending, event dispatch and native material emulation.
This changes offline authoring scripts only; no guest code, game hooks or
on-disk fighter recipe formats change.

Validation uses invented palette/order fixtures plus a private real-body test:
39 surfaces, 4656 vertices, 94 bones; entrance/victory each106ticks, two channels.
The real Qt/WebChannel/WebGL viewer passes load/play/pause/scrub/stop/victory on
the original body. This establishes editor playback, not native game acceptance.
