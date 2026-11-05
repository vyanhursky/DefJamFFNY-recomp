# Fighter voice registration audit (2026-11-05)

Bounded read-only audit of the SOD `SpeechId` field and its nearest native consumer. No code, build, or game run. The key result is that the native path is traced only as far as copying the 32-bit value into a runtime character record; the inspected source does not prove the Character voice-bank filename lookup, table capacity, or unload lifetime. Keep those as open requirements for a data-only voice adapter.

## Established SOD contract

`setup/fighter_sod.py` treats `SpeechId` as an integer member of `Character`. Its schema uses `name_hash(table) XOR name_hash(field)`, where the native NUL-terminated djb2 hashes are `Character = 0x4CE5B1B2` and `SpeechId = 0x64CF14CA`; therefore the schema key is `0x282AA578`. The current unit fixture pins this field at record word offset 21 with descriptor 2 (`tests/unit/test_fighter_sod.py:17`). The reader obtains the field as a 32-bit word, so the SOD storage width is four bytes; the descriptor remains the native field type, not an independently proven voice-table width. See [fighter_sod.py](../../setup/fighter_sod.py:16) and [test_fighter_sod.py](../../tests/unit/test_fighter_sod.py:17).

The runtime materialization trace logs `MEM32(self + 0x1EC)` as `speech` after `sub_00020270` returns ([recomp_manual.c](../../src/recomp_manual.c:96), [fighter_runtime.c](../../src/patches/fighter_runtime.c:843)). Generated native code copies full DWORDs from source `+0x1EC` to output `+0x4C` in `sub_001A3D50`, whose loop converts source rows of stride `0x290` to output rows of stride `0x80` ([recomp_0012.c](../../src/recomp/gen/recomp_0012.c:22123), address range `0x1A3D50–0x1A4654`; copy sites at guest `0x1A4573–0x1A4612`). In that converter, `+0x1EC` is one of several candidate values selected by sentinel fields and option bits at source `+0x210`; the code proves full-width copying, but does not identify that field by name. The SOD association comes from the project’s materializer annotation and fixture, not the generated function’s symbols.

## Audio-resource evidence and limits

The Vendetta inventory contains `speech/Character/Def_Jam_IP_Characters/600.dat` and its `.hdr` partner, with corresponding pairs for the voice IDs described by the archive report. That report records IDs 600–645 except 630/631, with two mappings reusing 518 and 507; the archive speech group has 346 files total ([fighter-mod-support-2026-11-01.md](fighter-mod-support-2026-11-01.md:76), [vendetta-inventory.json](../../logs/fighter-mod-research/vendetta-inventory.json:10762)). This is evidence of authored archive naming and intended ID mapping, not proof that native code derives those paths from `SpeechId`.

The earlier `SpeechId`-to-runtime-record trace did not reach resource lookup. A separate native audio path is now identified below: the XBE contains Character-bank templates and a generic paired HDR/DAT loader. The generated path still does not prove that the record field copied from SOD is the exact value supplied to that loader. `logs/funccall-catalog.md:931–942` documents separate `%03d` intro/extro `.asf` paths; these are not the Character banks. The M2 motion audit likewise leaves a join from motion data to voice rows unresolved ([fighter-m2-motion-audit-2026-11-04.md](fighter-m2-motion-audit-2026-11-04.md:135)).

No native count, fixed capacity, per-bank entry width, cache key, refcount, or unload boundary for Character voice banks was established. The report’s known storage widths are limited to the 32-bit SOD/runtime ID fields and the observed `.dat`/`.hdr` file pair. The 346-file archive population and 44 distinct custom IDs are measurements of that mod archive, not engine limits. The `SpeechId` descriptor value 2 should not be reinterpreted as the audio record width.

## Adapter contract currently justified

A data-only adapter may preserve `SpeechId` as a full unsigned 32-bit semantic identifier and provide an explicit ID-to-bank mapping. The native templates establish zero-padded three-digit IDs and paired `.HDR`/`.DAT` names under an XBE-selected path prefix. Native table insertion, duplicate-bank aliasing, and safe release timing remain unproven. Do not use intro/extro stream IDs or the motion/core namespaces as substitutes for `SpeechId`.

## Follow-up: destination-record consumers remain unresolved

The `+0x4C` copier is `sub_001A3D50`, not `sub_001A4A30`. Its caller is `sub_00087700`: after calls to `sub_001A2F50`, `sub_001A4900`, `sub_001A4A30`, and cleanup/setup helpers, it passes destination base `0x340D58` to `sub_001A3D50` ([recomp_0004.c](../../src/recomp/gen/recomp_0004.c:21310), call at guest `0x8773B–0x87745`). The converter initializes `0x154` DWORDs at the supplied base, then advances destination rows by `0x80` and source rows by `0x290` until source reaches `0x3BF1C4` ([recomp_0012.c](../../src/recomp/gen/recomp_0012.c:22129), loop tail at guest `0x1A4638`). For the audio-related candidate, it defaults destination `+0x4C` to `0xFFFFFFFF`, then may copy source `+0x1EC`, `+0x1F0`, or `+0x208` depending on source sentinels and `+0x210` flags (guest `0x1A4573–0x1A4638`). This context suggests a normalized table of participant/configuration records, but does not prove the `+0x4C` member's semantic type.

The earlier `sub_001A4A30` reference should be read as the setup routine in this caller chain, not as a proven `SpeechId` bank consumer. Its body iterates 0x12E8-byte participant objects from `0x3B92E0` to `0x3BDE80` and calls per-object routines such as `sub_001A7610`, `sub_001BAA00`, `sub_001B9CE0`, `sub_001BE7F0`, and `sub_001A6A10` (guest `0x1A4A30–0x1A4AD4`; [recomp_0012.c](../../src/recomp/gen/recomp_0012.c:23628)). The inspected body does not load the normalized destination `+0x4C`, format a Character bank filename, or invoke a `.dat`/`.hdr` loader. Thus neither the voice filename key nor the native bank table/cache lifetime has been connected to `SpeechId`.

**Unresolved edge:** identify whether any consumer of the normalized row at `0x340D58 + n*0x80 + 0x4C` reaches the Character speech loader described below. The loop covers 35 source rows (`(0x3BF1C4 - 0x3B9634) / 0x290`); this is the converter's observed iteration count, not demonstrated audio-bank capacity. The later XBE string audit found a direct native Character-bank path separately, but no proven join from this normalized row to that path. No bank table bound or unload lifetime follows from these rows.

## Native Character-bank naming and paired loader

String lookup in the local `default.xbe` (`C:\Users\Vlad\code\defjam-pr91-windows\data\extracted\default.xbe`) resolves the native templates. The strings at guest VAs `0x00290D24` and `0x00290D50` are `speech/Character/Def_Jam_Characters/%03d` and `speech/Character/Def_Jam_IP_Characters/%03d`; `0x00290D61` is an overlapping suffix inside the latter, not an independent extension-bearing path. Neighboring templates include `speech/Taunts/Def_Jam_IP_Characters/%03d` at `0x00290DB2` and `speech/Enviro/Def_Jam_IP_Characters/%03d` at `0x00290E06`. `sub_0003DB00` (`recomp_0001.c:65798`) passes the two Character templates and a numeric ID to `sub_0002A240` at guest `0x3DC07–0x3DC22`; it branches at ID `0x1F4` (500) between the base and IP template. The same routine passes the generated candidate to `sub_00043CA0` for list-string comparison and later calls `sub_0001C960` at `0x3DCE0–0x3DCEB` / `0x3DD09–0x3DD96`. This establishes that `sub_0002A240` is being used as a printf-style formatter for the three-digit bank stem; it does not establish an ID-to-SOD-record join.

`sub_0001C960` is the paired-resource cache/load path ([recomp_0000.c](../../src/recomp/gen/recomp_0000.c:33738)). It traverses up to `0x100` entries beginning at `0x332330`, with class-dependent strides `0x88`, `0x110`, or `0x198`, then constructs either `%s%s.HDR` (`0x00288710`) or `%s.HDR` (`0x0028871C`) and calls `sub_001E3FB0` (`0x1CA0E`). On success it stores the returned object at record `+0x84`, formats `%s.DAT` (`0x00288764`), and passes that object plus the DAT path to `sub_00135FF0` (`0x1CA27–0x1CA42`). The candidate format call in `sub_0003DB00` passes `0x00290E24`, whose bytes begin `AUDIO/SPEECH2.VIV|`, alongside the formatted candidate. The literal formats are uppercase extensions, while the mod archive member names are lowercase; archive lookup case behavior is not established here. `sub_001E3FB0` makes one further call to `sub_001E5800` with the path and `0x2F8200` context (`recomp_0013.c:20441`); `sub_00135FF0` delegates to `sub_00135B20` (`recomp_0009.c:47733`). I stopped at these one-layer handoffs: their downstream internals are outside this trace.

ZIP central-directory metadata for `speech/Character/Def_Jam_IP_Characters/600.dat` is uncompressed size 1,634,048 bytes, compressed size 1,351,259, method DEFLATE, CRC32 `0xD0850409`, local-header offset `0x03460AB1`; its `.hdr` partner is 256 bytes, compressed size 184, method DEFLATE, CRC32 `0x27F4A607`, local-header offset `0x035AA958`. Both entries have general-purpose flag bits zero. In the follow-up below, the two payloads were read into memory only; no extracted files or payload bytes were written to the report. The pair size difference is consistent with a large sample-data file and a compact header companion.

Remaining unknowns: the exact native input field supplying the `%03d` number, the branch's semantic meaning at threshold 500, whether the formatter stem is joined to `AUDIO/SPEECH2.VIV|` or another container prefix in the runtime path, the meaning of table slot key/ownership and refcount, case normalization, and cache teardown. The observed 256 slots belong to this generic paired-resource cache; they are not evidence of a 256-voice limit.

## Header payload and ID source follow-up

The in-memory `600.hdr` payload is exactly `0x100` bytes. Its initial little-endian words are `u16@0x00 = 1`, `u16@0x02 = 600`, `u16@0x04 = 0x2F02`, `u16@0x06 = 47`, and `u32@0x08 = 0x18EF`. Bytes `0x10..0xCB` contain 47 little-endian DWORD values (the final value is `0x0000000F`); the following DWORD at `0xCC` is `1`, then the remaining 12 DWORDs are `0xFFFFFFFF` except the first at `0xD0`, which is `0xFFFFFF00`. The 47-count interpretation is a structural inference from the word at `+6` and the matching number of DWORDs from `+0x10`; native code traced here does not iterate that table. The DWORDs mostly fall within the `.dat` length, but one is `0xF`, so labeling them all as byte offsets would be unjustified. No codec IDs or sample-offset semantics are established from this payload/native path.

The native paired loader does consume the first two 16-bit fields of the returned `.HDR` resource pointer: `sub_00135FF0` passes it to `sub_00135B20`, which compares `MEM16(resource+0)` and `MEM16(resource+2)` against the same two-word key in an 8-byte-stride sorted table before insertion ([recomp_0009.c](../../src/recomp/gen/recomp_0009.c:46662), call at `0x135FF0–0x13600D`). If the resource pointer returned from the generic open wrapper addresses the payload start, this matches observed header words `(1,600)`; that pointer-to-payload identity is an inference, not proven by the wrapper body. `sub_00135FF0` keeps a dynamic count in `0x3ADB74`, and the table base is `0x3ADB6C`; this is a runtime sorted cache count, not header entry count. No access to header offsets at `+0x10` or codec fields appeared in `sub_001C960` or `sub_00135FF0`.

Direct callers of `sub_0003DB00` are `sub_0003DDF0` at guest `0x3DE0D`, `sub_0003E080` at `0x3E0B2`, and `sub_0003E170` at `0x3E3C0` ([recomp_0001.c](../../src/recomp/gen/recomp_0001.c:66764)). They pass a one-byte/stack selector 1, 0, and 1 respectively after clearing audio flags; inside `sub_0003DB00`, that selector chooses candidate-name table `0x2DD8B8` versus `0x2DD6E0` (the latter also depends on `0x33EBC0`). The numeric Character-bank identifier is read independently as a DWORD from `0x3403B4 + n*0x64`, for four slots (`n=0..3`), skipping `0xFFFFFFFF`; values at least 500 choose the `Def_Jam_IP_Characters` prefix, otherwise `Def_Jam_Characters`. The same `0x3403B4` DWORD is formatted into intro/extro `%03d` paths in neighboring native routines, supporting its role as a speech identifier, but the four-slot table's writer and any direct assignment from the SOD `SpeechId` field remain unlocated. Therefore the native bank path is established, while the SOD-to-slot join remains unresolved.

## Voice-slot writer search

The three direct callers do not populate the ID slots in the inspected setup path. `sub_0003DDF0` clears 50 DWORD audio-status entries at `0x33EA78`, then calls `sub_0003DB00` with selector 1 ([recomp_0001.c](../../src/recomp/gen/recomp_0001.c:66248), guest `0x3DDF8–0x3DE0D`). `sub_0003E080` derives an auxiliary pointer from `0x2DC100 + 0x2C * MEM32(0x33EA5C)`, resets status, then calls with selector 0 ([recomp_0001.c](../../src/recomp/gen/recomp_0001.c:66623), guest `0x3E080–0x3E0B2`). `sub_0003E170` is the larger audio setup path and calls with selector 1 at guest `0x3E3C0` ([recomp_0001.c](../../src/recomp/gen/recomp_0001.c:66770)). In `sub_0003DB00`, the ID loop reads four DWORDs at `0x3403B4 + n*0x64`, but no stores to those ID offsets occur in the generated native C xrefs found; the nearby helpers only read them or update adjacent status bytes/fields.

The XBE section map places `0x3403B4..0x340549` inside section 7's virtual range (`VA 0x2D54E0`, virtual size `0xF80A4`) but beyond its raw-backed range (`raw size 0x25B08`). The IDs therefore have no initialized payload values in the XBE file image; the loader's zero-fill region starts before these slots. This does not rule out a runtime writer through an indirect subsystem, an external module, or a path absent from the generated source, but the three audio callers do not show one.

**Join status:** the SOD materializer names `self+0x1EC` as `SpeechId`; the audio loader later reads numeric IDs from the four `0x3403B4 + n*0x64` slots. No generated XBE store connects those locations. Both are observed as 32-bit DWORDs, but width equality alone is not a join. The runtime registration seam can be described only as accepting four optional 32-bit bank IDs plus an independent selector/path context. The source of those IDs, their mapping to the active participants, and whether `SpeechId` is copied into these slots remain unresolved.

### Surrounding state-base check

The neighboring structure is consistent with a 0x64-byte row whose base is `0x3403A4`: the voice DWORD sits at row `+0x10` (`0x3403B4`), nearby helpers access row `+0x0C` at `0x3403B0`, and other fields at `+0x30` (`0x3403D4`) and `+0x3C` (`0x3403E0`). `sub_0003E170` sets `EDI=0x3403A4` and iterates the row base (`recomp_0001.c:67407`), but reads the row's leading DWORD and does not store the voice member. `sub_00034E10` reads the per-row voice DWORD at `+0x10` and formats it into an extro stream path; it also toggles adjacent status bytes (`recomp_0001.c:45125`, relevant uses at guest `0x34E10–0x34EA7`). This strengthens the row-layout inference but provides no setter.

The closest indexed setter family found writes the row's `+0x30` field instead: `sub_00035850` stores an argument DWORD at `index*0x64 + 0x3403D4`; `sub_00035870` writes `0xFFFFFFFF` there; `sub_00035940` clears one indexed `+0x30` and writes another ([recomp_0001.c](../../src/recomp/gen/recomp_0001.c:46643), `:46662`, `:46792`). These are concrete indexed-record setters, but they do not write `+0x10` and should not be treated as voice-ID setters. The nearby `sub_00034DE0`/`sub_00034E10` routines mutate `+0x18`/`+0x19` status bytes only. No candidate in this bounded neighborhood assigns a voice ID, and the earlier three `sub_0003DB00` callers remain readers/setup paths. A writer through an indirect object pointer or outside the generated XBE source is still possible; the runtime adapter's source-field binding cannot yet be specified from native evidence.


## Primary verification: computed writer and high-core failure

The earlier unresolved-writer statements above are superseded by the primary
trace. In3E170, ESI=3403B8; guest3E290 computes EAX=EDI*12,
then3E2BC reads2DC5D0+EAX and writesMEM32(ESI-4). The four rows
start3403A4, stride64hex: row+0 stores the audio template key, +4/+8/+C
receive signed bytes from2DC5D5/4/6 respectively, and +10 receives voice ID.
The alternate branch3E2C7 uses28E48C+selector*4. Later3E736 reads the
stored audio key again for metadata. These are audio records, not actor IDs.

Run020004 WATCH_WRITE3403B4 caught the bad write: EDI=101hex,
EAX=C0Chex, EDX=2929016Dhex, ESI=3403B8. This is one-based custom
core257 indexing beyond the fixed audio table, producing decimal690553197
as a speech filename. The native core itself is256. The earlier014823
live stack was in1E7CD0's stream-record scan after this bad intro resource.
A host symbol+offset is a compiled host offset, never a guest instruction VA.
020004 was deliberately stopped after diagnosis; its save was restored
byte-identically with one verified generation. It is not an acceptance pass.

Primary callers.py and generated source prove a direct caller8BB00, at
8BCA0..8BCAA, despite the bounded agent's contrary claim. It constructs a
0x84-byte temporary value and passes its pointer as first cdecl argument.
3E170 reads venue/context at+0, flags+80/+81, and four one-based audio
keys at+20,+38,+50,+68. These input reads are synchronous; no input pointer
is retained. No2DC table clone is necessary. The adapter copies this value
onto a nested guest stack frame and maps added keys to their validated
inherited template keys, then delegates the original function. Original input
and actor cores are unchanged. Audio setup precedes main motion registration,
so this mapping depends on validated startup bindings, not source-generation
availability. Authored voice-bank support still needs a separate mapping and
validated resource contract; this inherited-template adapter does not claim it.
