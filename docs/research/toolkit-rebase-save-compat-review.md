# Toolkit rebase: save compatibility review

Date: 2026-10-03. Bounded read-only source review of `save_compat.c/.h`, the
`001F8360` replacement, initialization, and compiled-helper tests. No source
edits, builds, tests, or game runs were performed by this reviewer. The only
write is this report.

## Actionable findings

### P2: compatibility and runtime can select different default save roots

`src/main.c:615-623` initializes the runtime with a NULL save root, then separately
reconstructs a compatibility root from `getenv("LOCALAPPDATA")`, or bare CWD if
that environment variable is unavailable.

The active runtime instead resolves the shell folder with
`SHGetFolderPathW(CSIDL_LOCAL_APPDATA)` in
`logs/rebase-work/migration/src/kernel/kernel_path.c:302-309`. Its fallback is
**CWD plus `SaveData`**. The parent submodule has the same behavior at
`tools/xboxrecomp/src/kernel/kernel_path.c:291-298`.

Removing or overriding the environment variable does not necessarily change the
shell folder. Thus the compatibility helper can inspect a different tree while
the runtime continues using the shell-resolved AppData tree. If the shell API
fails, the missing `SaveData` suffix is a second mismatch. Besides failing to find
a valid legacy folder, this can invalidate canonical precedence: the compatibility
check sees a canonical miss in the wrong tree even when the runtime's canonical
folder exists.

Use one resolved root for both systems, or use exactly the runtime's shell API
and fallback and convert consistently. Check API/formatting return values before
initializing compatibility; failed or truncated root construction should disable
alias lookup. `GetCurrentDirectoryA` currently has no return-value check, so a
failure can also pass an uninitialized `save` buffer to `strlen`.

Regression cases: environment absent with shell lookup succeeding; environment
overridden while shell path differs; shell lookup failure with CWD/SaveData;
failed root construction. Place opposite canonical/legacy fixtures in the two
trees so a test proves both use the same physical root.

### P2: Windows compatibility probes use a different path encoding

`src/hooks/save_compat.c:25,41` uses narrow `_stat` and `fopen`, while the runtime
interprets its supplied root as UTF-8 with `MultiByteToWideChar(CP_UTF8)` and uses
wide filesystem APIs (`kernel_path.c:303` in the migration copy).

Under the ordinary Windows ANSI code page, a UTF-8 root containing accented or
non-Latin characters is therefore checked under a different spelling. Canonical
existence checks and metadata opens can fail despite the runtime opening the
correct Unicode tree. The present tests use Unicode *profile names*, but their
temporary roots are ASCII; they do not cover Unicode filesystem roots.

On Windows, convert the chosen UTF-8 root/path with CP_UTF8 and use wide `_wstat`
/ `_wfopen` or equivalent Win32 APIs. Reject failed conversion before probing.
If the shared root is supplied as UTF-16, keep it wide through these checks.
Test a non-ASCII save-root directory under the default Windows code page, with
both canonical precedence and exact legacy metadata scenarios.

## Checks with no actionable defect found

- **Collision policy:** `save_compat.c:73-81` checks the canonical path first,
  computes only the precise legacy last-nibble OR spelling, and selects it only
  after exact UTF-16 name verification. A canonical directory or file wins.
  Unexpected `_stat` failures retain canonical selection rather than treating
  an inspection failure as proven absence (`21-31`). The VY0/VY2 test correctly
  exercises two canonical names sharing one legacy spelling.
- **Parser bounds:** the fixed buffer at `36` holds BOM, `Name=`, 128 code units,
  and CRLF. Length, byte parity, minimum count, and prefix are checked before
  indexed reads at `45-51`. An exact name must be followed by CR, LF, or NUL;
  suffix matches are rejected. Names longer than 128 cannot select an alias.
- **Arithmetic:** after each iteration the hash is below `2^48-59`; multiplying
  by 65536 and adding one UTF-16 code unit remains below `2^64`, so the unsigned
  recurrence does not accidentally wrap before the intended modulo. Synthetic
  surrogate pairs are hashed as UTF-16 code units, matching the guest.
- **Guest ABI:** `src/recomp_manual.c:116-132` reads the three arguments after the
  return address and consumes 16 bytes. That matches the staged original's
  `ret 12` epilogue. EBX, ESI, EDI, and EBP remain untouched. EAX receives the
  first hex character, matching the original's final highest-nibble conversion.
  The replacement is a complete manual definition, so the translator's manual
  exclusion/dispatch mechanism applies to direct and indirect callers.
- **Filesystem mutation:** the helper performs only existence checks and a
  binary metadata read; it does not rename, copy, create, or write files. This
  statement applies to the compatibility helper, not subsequent guest save IO.

## Focused coverage gaps

The fourteen new cases compile and call `defjam_save_directory_name` directly;
they do not call the guest wrapper or main's root-selection code. In addition to
the two defect regressions above, useful bounded cases are:

1. A guest-wrapper fixture with output canaries, capacity 13, stack delta 16,
   unchanged callee-saved registers, and EAX equal to the first output character.
   Verify its deliberate small-capacity behavior separately: capacity 12 produces
   no output write and EAX zero, whereas the old function ignored capacity.
2. Matching metadata at 127/128 UTF-16 units, a missing final delimiter, an odd
   byte tail, and a matching long prefix whose exact name exceeds 128 units.
3. A canonical path which exists as a file, and an inaccessible canonical path,
   proving legacy lookup cannot bypass the canonical inspection safeguard.

## Parent-supplied execution evidence

`logs/rebase-work/save-hash-fixture-results.txt` reports optimized exact baseline
and candidate helper execution for five names. It reproduces the three observed
legacy directory differences, and all five candidate hashes match independent
integer arithmetic. The parent also reports 60 project unit tests passing with
MSVC, including these 14 cases. No execution results were generated by this audit.

The root-selection/encoding defects are independent of the confirmed SHRD cause.
Retain correct CPU hashes and keep compatibility bounded to the verified legacy
folder policy after fixing the shared physical-root handling.

## Parent closure

Both path findings addressed: main obtains UDATA from the existing runtime xbox_translate_path API after initialization; helper receives UTF-8 and uses _wstat/_wfopen via checked conversion on Windows. No duplicate default-root policy remains. Compiled tests now include a Unicode root, exact replacement stack/callee-saved/output canaries, metadata lengths 127/128/129, and a missing delimiter at the maximum supported length. Project suite: 65 passed (`logs/rebase-work/pipeline-save-compat-tests.txt`). Game validation remains pending.

Final native compatibility coverage is 19 cases; the actual-checkout project suite
passes 67 tests with MSVC (`logs/rebase-work/actual-checkout-project-tests.txt`).
Both final game regressions are 9/9, including existing-profile Story routes and
20/20 Debug boots. Complete final evidence and remaining owner play-test gate are
in `toolkit-rebase-acceptance.md`.
