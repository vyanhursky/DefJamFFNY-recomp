# Fighter Mod Support: what does 255 actually limit?

2026-11-01. Local, bounded source investigation for the revised architecture
review. No engine edits, builds or game runs. Source: our v0.13.0 generated guest
C in the retained release lane; no reference-project implementation was used for
this follow-up. Generated code remains untracked and is not reproduced here.

## Finding

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
| Front-end setup identity | `src/patches/dev_unlock.c:145–155` writes a byte at game-data `+0x1AAA + participant*5`; generated setup helpers also use byte stores (`recomp_0000.c:39061–39132`) | This particular unmodified representation cannot carry an arbitrary wider identity. A host manifest alone cannot change it. |
| Empty selection marker | `sub_0001E850`, generated `recomp_0000.c:39420–39427`, compares that byte with `0x63` (99) | 99 has special meaning in this field. Byte capacity is not automatically a roster of 256 usable entries. This does not prove a 99-fighter ceiling elsewhere. |
| Match setup to active record | Existing verified trace in `fighter-record-fields.md:63–66`: setup `+0xA8 + 4*participant`, minus one, reaches active record `+0x2C` through `sub_000871F0`, `sub_001A4D90`, `sub_001B3110` | The active character/core index is a dword. Its exact relationship to the front-end identity is still not fully established. |
| Moveset reader | `sub_001B2090`, `recomp_0012.c:57802–57805`: dword record field `+0x2C`, 16-byte row indexing of pointer table at `0x3B864C` | No byte truncation/255 comparison in this inspected sequence. It is a 32-bit indexing path, not proof the referenced table is large enough. |
| Other move consumers | `sub_001B4930`, `recomp_0012.c:64447–64502`; `sub_001B4BA0:64680–64699`, same dword field/16-byte stride, pointer at `0x3B8654` | Subsequent byte/word loads access move data/indices; they do not alone prove truncation of the character/core index. |
| Moveset initialization | `sub_001A47B0`, `recomp_0012.c:23423–23445`: starts `0x3B8648`, increments 16 to exclusive `0x3B8F18` | Exactly 141 initialized descriptors: a real table-size problem independently of identity width. Widening an ID without extending storage is unsafe. |
| Voice-row lookups | `sub_0003E170`, `recomp_0001.c:66926–66947`, `67413–67423`: dword key, 12-byte row addressing at `0x2DC5D0`, with separate byte metadata | No eight-bit key cap established on these accesses. Total valid voice-row count and all consumers remain unproved. |
| Unlock-set keys | `sub_00017000`, `recomp_0000.c:18093–18156`, searches four-byte keys; `sub_00016810:16334–16388` inserts four-byte keys without a local capacity check | Generic set helpers do not impose an eight-bit key cap. This does not prove the backing capacity, on-disk save format, or which identity domain the keys encode. |

The front-end evidence and moveset initializer/reader sequences were checked by
the main investigator as well as bounded read-only agents. This remains a source
read, not a demonstrated high-ID playable build. Some historical field notes
infer the link from front-end fighter ID to core index; preserve that uncertainty.

The previous investigation established that the reference project chooses 256
core-table entries. That implementation choice does not establish an underlying
255-fighter format restriction and does not reserve public IDs for our authors.

## Required capacity audit before implementation choice

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
