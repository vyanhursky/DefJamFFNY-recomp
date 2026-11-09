# Fighter Mod Support: what does 255 actually limit?

2026-11-01. Local, bounded source investigation for the revised architecture
review, updated with the first implementation experiment. No engine edits or
game runs; a standalone CPU parser harness was compiled. Source: our v0.13.0 generated guest
C in the retained release lane; no reference-project implementation was used for
this follow-up. Generated code remains untracked and is not reproduced here.

## Finding

2026-11-02 runtime follow-up: a 300-custom-fighter native menu selected logical
ID **361**, bound its stable identity to one of four native participant slots,
and reached combat against retail Blaze. This establishes one native path beyond
255 without widening the original byte consumers. It does not establish a
universal capacity or complete menu/lifetime acceptance. Evidence and the other
fixed storage limits are in the [active runtime note](fighter-mod-runtime-2026-11-02.md).

**255 is not established as a universal fighter-count ceiling, and going beyond
it has not been shown to be easy.** The existing path contains both byte-width
and 32-bit identity fields. Their mapping must be established before choosing
between widening structures and virtualizing native slots.

256 table entries, maximum numeric value 255, 256 selectable fighters, and 256
distinct movesets are different claims. Reserved sentinels and retail entries
further reduce usable slots in a specific native table. Several fighters may
share one moveset. Installed fighters need not all be resident in memory.

## Evidence from our source

| Domain/path | Observation | What it establishes |
|---|---|---|
| Front-end setup identity | `src/patches/dev_unlock.c:145–155` writes a byte at game-data `+0x1AAA + participant*5`; native helpers `1E700`/`1E820` write/read it. StartGame `46E40` sign-extends the returned byte before comparing with Character word 8 | **128–255 become negative in this path.** The unmodified selection representation has an earlier problem than 255; a wider database ID alone cannot fix it. This is a token-domain restriction, not a measured roster-count ceiling. |
| Reserved selection token | `sub_0001E850`, generated `recomp_0000.c:39420–39427`, compares that byte with `0x63` (99). StartGame handles 99 specially and normalizes to 98 during lookup | 98/99 need explicit created/special-fighter handling. Byte capacity is not automatically a roster of 256 usable entries. No universal 99-fighter ceiling follows. |
| Character to match setup | StartGame compares selection token with Character schema `fcdba74e` (word 8); setup `+0xA8` contains the separate one-based core ID | Selection key and core ID are distinct. Multiple Character definitions may share a core. `20270` is a general materializer observed for venue data; its fighter-specific role was not established by this audit. |
| Match setup to active record | Existing verified trace in `fighter-record-fields.md:63–66`: setup `+0xA8 + 4*participant`, minus one, reaches active record `+0x2C` through `sub_000871F0`, `sub_001A4D90`, `sub_001B3110` | The active character/core index is a dword and uses the one-based setup core ID minus one. This does not prove storage capacity. |
| Moveset reader | `sub_001B2090`, `recomp_0012.c:57802–57805`: dword record field `+0x2C`, 16-byte row indexing of pointer table at `0x3B864C` | No byte truncation/255 comparison in this inspected sequence. It is a 32-bit indexing path, not proof the referenced table is large enough. |
| Other move consumers | `sub_001B4930`, `recomp_0012.c:64447–64502`; `sub_001B4BA0:64680–64699`, same dword field/16-byte stride, pointer at `0x3B8654` | Subsequent byte/word loads access move data/indices; they do not alone prove truncation of the character/core index. |
| Moveset initialization | `sub_001A47B0`, `recomp_0012.c:23423–23445`: starts `0x3B8648`, increments 16 to exclusive `0x3B8F18` | Exactly 141 initialized descriptors: a real table-size problem independently of identity width. Widening an ID without extending storage is unsafe. |
| Voice-row lookups | `sub_0003E170`, `recomp_0001.c:66926–66947`, `67413–67423`: dword key, 12-byte row addressing at `0x2DC5D0`, with separate byte metadata | No eight-bit key cap established on these accesses. Total valid voice-row count and all consumers remain unproved. |
| Unlock-set keys | `sub_00017000`, `recomp_0000.c:18093–18156`, searches four-byte keys; `sub_00016810:16334–16388` inserts four-byte keys without a local capacity check | Generic set helpers do not impose an eight-bit key cap. This does not prove the backing capacity, on-disk save format, or which identity domain the keys encode. |
| Character database | Offline builder retains 75 retail records and adds 300 synthetic definitions. Actual generated loader/index bodies accept the resulting 375-record SOD and find selection key 276 | The native SODB container/index is not capped at 255 in this experiment. It does not exercise selection or combat. |
| Native list construction | `47BC0`: Character count × 32 allocation, dword count at `+4`, vtable method of shared Game.GetGameMode object `341330`; `54420`: registered Game.GetCharacterList, count × 4 pointer allocation | These shared producers allocate dynamically. Movie limits and independent per-player selector state remain unproved; a per-player page must not globally swap their data. |

The front-end evidence and moveset initializer/reader sequences were checked by
the main investigator as well as bounded read-only agents. This is a source
audit plus CPU database-parser experiment, not a demonstrated high-ID playable
build. The selection-to-core field roles are now independently corroborated;
complete lifetime/persistence and menu ownership still need tracing.

The previous investigation established that the reference project chooses 256
core-table entries. That implementation choice does not establish an underlying
255-fighter format restriction and does not reserve public IDs for our authors.

## Cache/parser experiment and persistence caution

The [implementation checkpoint](fighter-mod-implementation-2026-11-01.md)
records exact inputs, hashes, native parser functions and reproducible commands.
The new definitions inherit a donor's one-based core ID; 375 Character rows do
not mean 375 distinct movesets. No additional animation or voice bank was loaded.
The first experiment followed index pointers only and missed an inline member-map
invariant. The [runtime follow-up](fighter-mod-runtime-2026-11-02.md) corrects the
writer and adds native packed-handle round trips. The old result alone is not
proof that those 375 records work through all native database APIs.
The corrected 375-row experiment now passes all six oracle functions, including
handle creation and row resolution for selection key 276 (native handle
117440730). Evidence: `logs/fighter-inline-375-oracle.json`, SOD SHA-256
`765c5f58404bfc1ab4928ad03c7d979e7200725cd2fc38908f2dfeece354d175`.
This remains CPU database acceptance, not a playable 375-fighter roster.

The generated cache preserves original record bytes and ordinal-index positions,
but rebuilding sorted name indexes changes 58 retail ranks. Any cached/saved
rank-derived handles must be found and migrated or isolated. This observation
does not establish what the actual serializer writes. Six initially plausible
profile callbacks were resolved from the owner's XBE and proved to be bit-array
reset methods, not serialization. No profile bridge should be enabled on the
basis of those helpers.

## Required capacity audit before implementation choice

2026-11-02 runtime follow-up adds two concrete bottlenecks. The Options Character
unlock set has 80 inline/persisted dword entries; a native 10-custom-fighter
negative test stops on the attempted insertion at live count 80. Separately,
the shared final roster buffer at `3A07B0` has a known scalar at `3A09B0`, so
list index128 would overwrite that state. This is an upper bound before a known
different field, not proof of 128 usable slots. Twenty-six functions reference
the list base literally; dynamic temporary allocation does not relocate them.
See the [current runtime note](fighter-mod-runtime-2026-11-02.md) for exact
function evidence, save payload offsets, native logs and binding-window work.

1. Trace selection input/AI/preview through the actual front-end-to-core mapping,
   including created fighters and Story style combinations. Record exact widths,
   signed conversions, sentinels, packed fields, implicit offsets and index bases.
2. Inventory every relevant table, initializer, allocator, direct/indirect reader
   and cache: fighter records, movesets, voice/event bindings, SOD handles, UI
   symbols/arrays and cinematic requests. Distinguish scalar width from capacity.
3. Trace profile allocation and class-specific save/load serialization callbacks.
   Derive widths/counts from both writer and reader, including retail unlocks,
   cached selections and custom progression. Generic set helpers are insufficient.
4. For each bottleneck, compare relocating/growing arrays, widening a field with
   all affected consumers, and binding stable logical keys to existing native
   slots. Determine whether runtime content ever retains a slot after rebinding.
5. Produce a matrix of identity domain, widths, valid/reserved range, table count,
   consumers, persistence, proposed change and verification fixture. Report the
   engineering cost and remaining risk; do not invent a production limit first.
6. After architecture approval, test boundary identities 254/255/256/257 and
   sentinels in native fixtures and a playable build. For virtual slots, separately
   test roster size and binding churn; for wider indices, test formerly narrow
   paths. Include multiple independent packs and saves across disable/re-enable.

The architectural choice is [D1 in the revised plan](../fighter-mod-support.md).
Stable public fighter/resource keys can be designed without fixing a numeric
native limit. Production limits still need explicit performance/memory budgets;
a 32-bit field is not a promise of billions of usable fighters.
