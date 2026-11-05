# Fighter voice registration and PCM profile (2026-11-05)

Status: inherited audio-template routing passes native four-human and CPU
combat with cores256..259. Authored PCM compilation, bounded validation and
isolated native decoding pass. Independently registered authored voices have
**not** yet passed in-game playback or resource-lifetime acceptance.

All native evidence comes from the owner's executable and generated C. No
external implementation or game asset bytes are included in source.

## Distinct identities and the inherited-template fix

SOD Character `SpeechId` is a DWORD copied by1A3D50 from materialized source
+1EC to normalized output+4C. That observation alone does not prove its join
to active audio state. The concrete writer is3E170: ESI=3403B8, guest3E290
computes EAX=EDI*12, and3E2BC reads2DC5D0+EAX intoMEM32(ESI-4).
An alternate branch3E2C7 reads28E48C+selector*4.

Four audio rows start3403A4, stride64hex. Row+0 is an audio-template key;
+4/+8/+C receive signed metadata bytes; +10 is the voice DWORD. These are
separate from actor cores. The direct8BB00 caller constructs a0x84-byte input
with one-based template keys at+20,+38,+50,+68. Its pointer is not retained.

Run020004 WATCH_WRITE3403B4 caught template257 indexing beyond the fixed
table and producing invalid voice690553197. Earlier014823 live stack was in
1E7CD0 scanning the resulting intro resource. Both diagnostic runs were
stopped deliberately, with identical save restoration; neither was a pass.
The real3E170 wrapper now maps only a private stack copy of the four audio
keys. Actor identity and caller input stay unchanged. Audio precedes motion
resource registration, so template mapping uses startup bindings.

Native acceptance:021106 four humans and021813 one human/three CPUs, two
independent packs, cores256..259, no crash/watchdog/unresolved calls, and
byte-identical save restoration. Stock regression023405 passes5/5, including
1455 unit tests. See the M1/M2 checkpoint for exact logs and frame statistics.

## Voice-bank registration seam and its independent limits

3DB00 first reads row voice at3DBD0. It follows the writer without an earlier
voice read in the inspected setup path; both selector branches reach it.
Other reload caller3DDF0 also reaches it after unloading. ABI: cdecl selector
low byte at entryESP+4, plain return; preserve native nonvolatile registers.

Its native loaded flags at33EA78 are only200 cleared bytes. The index is
`voice < 500 ? voice : voice - 400`; voice600 indexes beyond that extent,
and100..199 alias500..599. Full-width fighter cores therefore do not imply
safe full-width voices. A custom loader needs a bounded set of full voice
IDs per invocation; every surfaced caller unloads and clears before loading.
A persistent set would need separate lifetime synchronization.

Selector nonzero includes the null-terminated Tutorial list2DD8B8 (15 names
in this executable). Zero includes Heckles2DD6E0 (12 names) only when byte
33EBC0 is nonzero. For each distinct valid voice, Character/Taunts/Enviro
stems are queued, using base paths below500 or IP paths at/above500.
43CA0 sorts but does not deduplicate.1C960 loads each stem beneath
`AUDIO/SPEECH2.VIV|`;43DF0 destroys the temporary list.

1C960 has256 generic resource records, stride88hex. It allocates/reads HDR,
stores its pointer at+84, DAT path at+4, and registration handle at+0.
1CA80 unregisters through135DB0 before freeing HDR through294D0. Keep this
native ownership; never pass a host-buffer pointer as a guest-owned header.
Active-playback drain before unload still needs acceptance.

135B20 registration and135CB0 playback compare both WORDs at HDR+0/+2.
3ADB78 is live sorted-cache count;3ADB74 is capacity. The first WORD is an
opaque event-bank family identifier, not a clean category enum. Examples
from verified local headers: base Character/Taunts/Enviro families are
0/16625/40962; corresponding IP families are1/16626/40963. The second WORD
matches the voice number. Duplicate pairs are rejected.

137780 gets the first key from an event descriptor; mode1 obtains the second
key from a selected dynamic argument.34668 writes a voice WORD to a queued
request, so65535 remains reserved pending sentinel audit. Filename IP routing
alone does not establish the event family's selection. Preserve the inherited
family until native request tracing proves the intended match. Separate
combat voice mappings from intro/extro sound references: those also consume
the row voice and must not be made to request nonexistent resources.

## Owned PCM stream profile

`setup/fighter_voice.py` compiles caller-owned signed little-endian PCM16.
The initial authored profile is mono, sample rate8000..48000,1..4,000,000
samples,1..16384 samples per packet, and at most16MiB per stream. These are
our admission budgets, not claims about universal native format limits.

- SCHl: inclusive LE32 chunk length, PT0700 prefix, explicit properties
  A0=8 (codec),82=1 (channels),84=rate,85=total samples, FF terminator.
  Properties use tag, length1..4, signed big-endian integer. The writer uses
  four bytes to avoid sign ambiguity. Unknown/duplicate properties fail.
- Optional SCCl: LE32 packet count. Native dispatch skips it; our validator
  checks the declared count against the actual packets.
- SCDl: positive LE32 count at+8, mono relative offset0 at+C; PCM begins+10hex.
  Exact byte count must match the samples. Cumulative samples match SCHl.
- SCEl: length8, no payload; no trailing bytes in an authored stream.

1264F0 skips four PT bytes without interpreting the platform word, and sets
packet endian0 on the generic path. A0 selects codec8.12E520 initializes the
PCM decoder;12E490 invokes130EA0, which converts signed16-bit samples to
raw-valued floats. This is not normalization by32768.1E7D80 masks packet
length to24 bits, so nonzero high length bits are rejected. No ADPCM format
is claimed by inference from neighboring codec numbers.

`scripts/fighter-voice-oracle.py` extracts nine native functions into ignored
logs and compares invented streams.120 cases,311430 samples, zero mismatched
bytes. It checks five sample rates, packet boundaries, partial decode reads,
zero-filled final tails, exhaustion and output guards. Native body SHA256:
`0274b5d3042483f26759ce465ae6482a359afdec198e665c72e4494d6d594f10`.
Evidence: `logs/fighter-voice-oracle/comparison.json` and
`logs/fighter-voice-oracle-nov05.txt`. It does not exercise the device mixer,
event selection, bank registration or active-playback teardown.

## Bank event metadata and composition

1393F0 reads entry count byte+5, stride `(byte+4 &127)+2`, entries at+C.
Each start is BE16 units, terminal at+8 is LE16 units; unit=256*(byte+7+1).
The next start or terminal determines entry span. Real DAT files can contain
unindexed trailing bytes after that terminal; they are not sample entries.

Offset-only records are insufficient for normal events:1393C0 returns entry
metadata after the two offset bytes, and137680 filters those criteria.
The trailer starts at align4(12+count*stride), with four-byte aggregate masks
for each criterion. Bit7 of+4 adds a partition-count byte and ceil(count/8)
mutable eligibility bits. Nonzero+6 adds history cursor and recent-entry
indices. LE16+A is a request-index matrix row bound, followed by packed
row*entry eligibility bits. FFFF has separate semantics and is rejected by
our current template compiler. The native entry count is one byte; this is
an entry-per-bank limit, not a fighter or whole voice-library limit.

`setup/fighter_voice_bank.py` requires a verified original HDR/DAT hash pair.
It retains entry order, criteria, masks and selection/history configuration;
rewrites the second bank key and offsets; accepts replacements only through
the authored PCM validator; and retains exact verified source streams for
explicit fallbacks. It chooses256-byte multiples for offset units as needed
without truncating16-bit offsets.64MiB per-bank budget. Unindexed original
DAT tail bytes are excluded and reported; padding within sample spans is
checked. Self-supplied hashes from a package are not a verified local source.

Twelve local template compositions passed: all three categories for donors
4,5,22,500, each with one invented PCM replacement. Evidence:
`logs/fighter-voice-bank-template-validation-nov05.json`. Focused tests also
cross the original16-bit/256-byte offset envelope without changing samples.

This primitive does not expose raw ordinals as meaningful creator event
names. Named event bindings still require a verified category-specific mapping.
Untrusted HDR metadata, arbitrary codecs, custom event opcodes and native
registration are not admitted merely because a composition receipt exists.
