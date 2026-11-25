# Retail Story customization HD composition

Retail customization sources are layers, rather than finished GPU atlases. A
content-hash alias for one finished outfit does not generalize to another skin,
hair color, tattoo, garment or injury state. The runtime therefore observes the
original compositor and builds parallel host images. It never substitutes guest
bitmap dimensions, writes guest image data or changes the native construction.

## Native boundary and ownership

`0009A050` is the shared builder used by Story profiles and debug presets. Its
six outputs at visual offsets `A234..A248` are A/B/C/D/D1/D2. Only rebuilt slots
are published; unchanged slots retain their registrations. The original builder
still executes, including palette painting, clipping, quantization and cleanup.

| Observation | Purpose |
| --- | --- |
| `6EB20`, `6EC50`, `6EE30`, `6EDC0` | Follow manager initialization and each resource handle's open/data/close lifetime. Handles are separate for repeated opens and are removed on close; manager initialization restarts their IDs. |
| `213F0` | Capture the selected SHPX entry before palette paint. |
| `92BE0`, `1DF5C2` | Follow materialized layers and independent copies of the composed D injury base. |
| `A4740` | Mirror each actual native layer operation, in the game's own order. |
| `92C80` | Associate the final native bitmap with its host composition, including a reused spare. |
| `1DE887`, `99CC0`, `98470` | Drop temporary shadows and invalidate per-slot or whole-visual registrations before native free/reuse. |

Resource identity includes the canonical archive/member path, entry name and
index-data fingerprint. The first unpainted source ID and palette are retained
across subsequent palette changes. A reused address or numeric handle alone
cannot establish identity. Retained palettes provide the original baseline for
source-aligned RGB color changes; composition coverage uses the current native
palette alpha. Native rectangular swizzle is decoded separately from identity.
Image and palette data each honor their own indirect-data flag. Signed relative
attachment links and indirect buffers are checked at their actual guest RAM
addresses, rather than assuming all data follows its header.

## Pixel and material rules

Native `b` leaves alpha-zero pixels alone, copies alpha-255 pixels and otherwise
uses `(source * alpha + destination * (255-alpha) + 128) >> 8` for each RGB
channel. Working alpha is the larger alpha. Native `c` copies all four channels,
including alpha-zero pixels. Signed placement is clipped to the destination.
Both operate on the full source rectangle; the traced path has no mirror flag.

Alongside the HD image, the adapter replays each operation at native resolution
and compares it byte-for-byte with the game's actual working bitmap. A mismatch
disables that atlas's HD output. This check covers the native operation, not an
assumption about how a filename should be placed.

Final material alpha comes from decoding the **final native bitmap**, after any
palette quantization. It is copied by nearest sampling to the host image.
Host RGB retains the selected PNG detail. Registration uses
`xbox_PhysRamName` on the actual final pixel allocation, with its native format
and dimensions; native texture coordinates and allocation sizes remain intact.
Mipmaps use independent channels. The existing explicit added-fighter HD recipe
path and its image-size contract remain separate and unchanged.
The existing authored-CAF classifier excludes those contexts before their first
build, so later recipe atlas replacement cannot leave Story registrations behind
or consume the authored HD owner's registry capacity. Tracked native Story
profiles remain eligible. Nested builds are checked before this exclusion.
If optional Story registrations fill a shared allocation or registry budget,
authored HD retires only the Story slot owners and retries once. This preserves
the existing authored budget and native fallback without raising either limit;
successful allocations do not evict other Story visuals.

## Bounds and fallback

The Story adapter admits native image edges up to 256 and integer scales 1..4
(512/768/1024 outputs for a complete 256 atlas). It has 192 transient image
records, a 96 MiB scratch budget, 256 live resource handles, 64 current archives
and at most 8,192 original palette identities (about 11 MiB). Native attachment
walks are limited to 64 links and checked guest RAM spans. A nested builder runs
native and invalidates the interrupted host composition rather than mixing owners.

The toolkit CPU lookup uses normal enabled-pack precedence and validated paths.
Its PNG dimensions are checked **before decoding**, with a 2,048 edge limit and
the existing decode budget. POSIX CPU decoding validates and decodes the same
encoded snapshot (limited to 64 MiB), preventing a path replacement between the
size check and decode. It does not create GPU resources or modify source
cache state. The existing renderer still limits address-owned textures to 32
sources/256 MiB of prepared pixels and uses its configured GPU cache budget.
All registrations are scoped to a visual slot; invalidation retires old GPU
resources before the native backing can be reused.

A missing PNG contributes its native layer. Invalid images, unsupported native
data, resource/allocator failure, native replay disagreement or failed renderer
registration retain native rendering. A failed HD layer is never silently
published as an incomplete composition. Without a pack declaring `story-caf-v1`,
the Story observer stays off, including when unrelated static packs are enabled.

## Pack contract and qualification

Source packs use ordinary `[textures]` content IDs and add
`compositor=story-caf-v1` under `[pack]`. The installer returns the additional
`story-caf-v1` capability; the launcher advertises it. Distribution must require
that capability and recomp **v1.2.4 or newer**. Static maps can also name their
content-derived native-format IDs; they do not need a profile-specific atlas.

Synthetic tests cover exact blend endpoints/all alpha values, clipped copy,
2x/3x/4x images, independent clones, native final alpha in indexed/BGRA outputs,
palette changes across builds, resource/handle reuse, allocation failure,
negative attachment/data offsets, invalid memory ranges, authored-CAF exclusion,
nested builders and native replay disagreement. Native
fixtures additionally establish real registration/upload and complete save-root
restoration. Pack checks establish source completeness, image integrity and
installation. They do not mean every item or outfit combination was manually
play-tested; platform and release play-testing remain separate gates.
