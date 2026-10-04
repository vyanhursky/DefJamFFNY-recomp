# Toolkit rebase: profile folder reconstruction

Date: 2026-10-03. Scope: read-only comparison of baseline and candidate logs and
root-staged generated-function excerpts. No source changes, builds, tests, game
runs, or save mutations were performed by this audit. The generated excerpts and
logs remain ignored; this report contains addresses and control-flow descriptions,
not lifted game bodies.

## Finding

The candidate's reconstructed folder names are the correct name hashes. The
baseline's last hex character is corrupted by an unguarded **zero-count SHRD** in
the 64-bit right-shift helper `sub_002032A0`. Upstream already fixes that CPU bug.
The three observed legacy folder names match its erroneous behavior exactly.

This is a compatibility issue exposed by corrected CPU semantics. Reverting SHRD
to reproduce the old directory names would reintroduce undefined C behavior and
break x86 semantics. The candidate does not need a flag/partial-register fix for
the demonstrated final-character differences.

The precise historical creation event for these folders was not inspected. The
root reported their metadata names after inspecting a disposable save copy. An
optimized compiled comparison of the complete staged hash path is being performed
by the root; this audit establishes the source mechanism and arithmetic mapping,
and does not claim to have run that comparison itself.

## Log evidence

The candidate successfully enumerates a directory, constructs a path from that
enumerated name, opens `SaveMeta.xbx`, reads its BOM and metadata, and closes it.
Only the subsequent opens reconstructed from the metadata name diverge:

| Metadata name reported by root | Enumerated / baseline folder | Candidate reconstructed folder | Candidate log lines |
|---|---|---|---|
| `VY2` | `005600590036` | `005600590032` | enumeration 31271; successful open 31276; failing repeats 31295, 31303, 31311 |
| `VY3` | `005600590037` | `005600590033` | enumeration 31319; successful open 31324; failing repeats 31340, 31348, 31356 |
| `Options` | `1A3F1B2E4ADF` | `1A3F1B2E4ADD` | enumeration 31364; successful open 31369; failing repeats 31385, 31393, 31401 |

Source: `logs/run-20261003-163956.log.err`. For the first profile, lines
31279-31288 show the successful read sequence between the correct first open and
the reconstructed failing open: two-byte BOM followed by a 20-byte metadata read.

Baseline `logs/run-20261003-130457.log.err` follows the same first read sequence
at 30017-30037 and reopens the original name at 30041. Further opens retain it at
30072 and 30103. The other profiles likewise retain their enumerated names at
30138/30154 and 30251/30267. These examples are distinct from earlier intentional
nonexistent-file probes.

## Narrowed call path

Line references below refer to full function excerpts staged under
`logs/rebase-work/readable-gen/`, with `candidate-sub_` or `baseline-sub_` followed
by the address and `.c`.

| Function | Relevant behavior and references |
|---|---|
| `001F7DC6` | Generic file-open wrapper. Initializes an ANSI_STRING, then calls NtCreateFile at guest `001F7EE8`, returning at `001F7EEE`. It receives the already-constructed name. |
| `001F7BB1`, `001F6D5E` | Volume-information wrappers. The logged returns `001F7C2B` / `001F6D71` do not identify name conversion. |
| `001F9744` | FindFirstFile-like wrapper. Calls NtQueryDirectoryFile returning at `001F9816`, then converts its output through `001F96D8` at guest `001F9837`. |
| `001F96D8` | Copies directory filename from query buffer `+0x40` to caller result `+0x2C`, using length at `+0x3C`; candidate lines 28-64. The correct first opens provide independent evidence that these particular names arrive intact. |
| `001F85BD` | Copies the enumerated name from result `+0x2C` into a path at `+0x140`, appends the metadata filename, and opens it. Candidate lines 38-162. Reads metadata into `+0x244` through `001F83F2` / `001F843A` at lines 177-198. No differing name-buffer write was found in its string construction. |
| `001F879A`, `001F89FD` | Reconstruct a folder from the metadata name through `001F8360`. Candidate calls at lines 73 and 92 respectively. |
| `001F8360` | Computes the name hash, then emits 12 hex nibbles. Candidate lines 42-88 contain the hash loop; lines 90-129 contain the formatter. |
| `002032A0` | 64-bit logical right-shift helper used by the formatter. Its first call uses shift count zero. Baseline line 32 differs materially from candidate line 25. |
| `001F834C` | Converts a nibble into ASCII `0`-`9` or `A`-`F`; baseline/candidate arithmetic and branch outcomes agree for 0-15. |

## Exact mechanism

The name hash is the recurrence

`h = (h * 65536 + UTF16_code_unit) mod (2^48 - 59)`

starting from zero. The formatter reads successive low nibbles after right shifts
by 0, 4, 8, ..., 44, placing them from the end toward the start of a 12-character
hex string. Thus **the count-zero case determines only the final character**.

Baseline `002032A0` line 32 emits a shift-and-OR expression without a count guard.
At count zero its high-word term shifts a 32-bit value left by 32, which is undefined
in C. On the host behavior that masks variable shift counts to five bits, this
becomes a low-word OR high-word operation. Its low nibble is therefore

`(hash_low & 15) | (hash_high & 15)`

instead of `hash_low & 15`. Subsequent nibble shifts use 4-28 and the helper's
high-word branch for 32-44, so this defect explains why only the final character
changes.

Independent integer arithmetic, performed without invoking the generated code,
produces:

| Name | Correct 48-bit hash | Low nibble | High-word low nibble | Legacy OR nibble | Legacy folder |
|---|---|---|---|---|---|
| `VY2` | `005600590032` | `2` | `6` | `6` | `005600590036` |
| `VY3` | `005600590033` | `3` | `6` | `7` | `005600590037` |
| `Options` | `1A3F1B2E4ADD` | `D` | `F` | `F` | `1A3F1B2E4ADF` |

All three predicted legacy names exactly match enumeration and baseline reopen
logs; all three correct hashes exactly match candidate reopen logs. No conjectured
buffer layout or carry error is needed to explain these observations.

Candidate `002032A0` line 25 masks the count to five bits and performs the write
only when the masked count is nonzero. Zero leaves the destination unchanged,
as required by the guest instruction. The root's integrated dynamic flag
publication also stays inside this guard.

## Upstream ownership and existing regression coverage

Cached upstream commit `1409a7d`, `tools/recomp/lifter.py:1991-2027`, already
documents this precise full-width-shift / accidental OR failure and emits the
nonzero-count guard. The migration copy retains it in
`tools/recomp/lifter.py:2115-2162`, with dynamic flag publication added inside
the guard. This is retained upstream correctness, not a new Def Jam workaround.

Upstream `tools/recomp/test_lifter_double_shift.py:123-143` compiles SHLD/SHRD
sweeps for counts 0-40 and includes a negative control requiring the old expression
to fail specifically at count zero. The integrated
`tools/recomp/test_dynamic_flags.py:285-321` additionally covers carry/overflow
consumers at zero and wrapped count 32. Those tests do not themselves establish
the user-save compatibility policy.

## Recommended next step

1. Keep the corrected upstream SHRD behavior. Confirm the entire name-hash call
   path with the root's optimized compiled baseline/candidate fixture against the
   independent recurrence, including all three names above. Add a synthetic
   translated multi-function formatter case to prevent accidental reliance on the
   old OR behavior.
2. Treat existing legacy folders explicitly. Work from disposable copies. Prefer
   a game-specific, bounded legacy-path compatibility mechanism after a canonical
   path misses, validated against the enumerated folder and its metadata name.
   Avoid changing generic CPU semantics or introducing unconditional aliases in
   the toolkit kernel for every title.
3. Resolve collision policy before any migration: correct and legacy folder names
   can both exist, and several different correct low nibbles can OR to the same
   legacy nibble. Prefer an existing canonical folder and fail ambiguous mappings;
   do not silently rename, overwrite, or merge the user's profiles.
4. Re-run Story routes with the verified compatibility behavior and save-guard
   checks. Passing golden frames alone does not exercise reconstructed profile
   paths. Other outstanding menu/GPU or function-extent failures remain separate.

Unresolved: the parent fixture's optimized execution result; the exact date/build
that created each legacy folder; the compatibility implementation and collision
policy; and any remaining regression failures after this issue is handled.

## Parent fixture confirmation, 2026-10-03

The optimized MSVC fixture compiled the exact preserved and candidate hash paths for five names. It reproduced all three observed legacy/correct mappings above; every candidate result matched the independent Python recurrence. Evidence: `logs/rebase-work/save-hash-fixture-results.txt`. D52 now implements game-specific, read-only compatibility with canonical-first and exact metadata checks; full game acceptance remains pending.
