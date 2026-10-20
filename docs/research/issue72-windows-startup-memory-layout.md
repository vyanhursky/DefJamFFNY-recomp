# Issue #72: Windows startup address-space collision

Investigation on 2026-10-20 of [issue #72](https://github.com/vyanhursky/DefJamFFNY-recomp/issues/72),
including the reporter's follow-up and attached
[`run-20261020-193903.error.log`](https://github.com/user-attachments/files/33730789/run-20261020-193903.error.log).
The original attachment is retained locally under `logs/issue72/`; no game bytes
or personal paths are copied into this report.

## Root cause

The Windows memory-layout allocator accepts a location for the 64 MB Xbox RAM
view without checking whether the rest of the guest address space fits at the
same translation offset. The later fixed-address physical-memory and device
allocations fail, but initialization reports success. Startup then reads an
unmapped AC97 register page to initialize its register shadow and crashes in
the host C runtime's copy routine, before guest execution or any rendered frame.

The report is v0.10.5, Windows 11, Ryzen 7800X3D and RTX 5080. Event Viewer gives
an access violation (`0xC0000005`) in `VCRUNTIME140.dll`, offset `0x1C177`.
The game log establishes the earlier cause:

| Attachment lines | Evidence | Meaning |
|---|---|---|
| 6–7 | Launcher opens, Play closes it | Setup built an executable and the launcher runs |
| 12 | RAM mapped at `0xBFFF0000`, offset `3221159936` | Only the base RAM placement was accepted |
| 32–36 | Contiguous, NV2A, MCPX, flash and kernel allocations fail | Multiple required translated windows are absent; Windows error 487 |
| 38–40 | 28/28 RAM mirrors map, tiled mapping fails, init says complete | RAM/mirror success does not establish a usable device layout |
| 48 | OHCI cannot trap `0xFED00000` | Another consequence of the missing MCPX window |
| 49–53 | Read fault at host `0x1BEBF0000`, guest `0xFEC00000` | Exactly the AC97 page copied during device setup |

The address calculation matches without truncation:

```text
guest AC97 0xFEC00000 + memory offset 0xBFFF0000 = host 0x1BEBF0000
```

The physical window would occupy host `0x13FFF0000..0x143FF0000`, which
includes the usual Windows x64 executable image base `0x140000000`. Values
`0x14003F9DF` and `0x141B7FC58` in the native-stack block are consistent with
that overlap, but that block is a raw scan filtered to `0x140000000..0x150000000`,
not an unwind or a host mapping inventory (`src/main.c`, crash handler).
The log does not establish which allocation occupies any rejected range.

`src/hooks/ac97_bm.c::ac97_bm_init()` unconditionally copies 4096 bytes from
`AC97_BASE + mem_offset` before protecting that page. `src/main.c` reaches this
after `xbox_MemoryLayoutInit()` returns true. Its registers are still at their
startup values in the attachment. The `_NLG_Return2+0x547` label is the nearest
available C-runtime symbol; it does not establish an exception-unwinding bug.

Triage commands used:

```sh
python3 scripts/triage.py logs/issue72/run-20261020-193903.error.log
python3 scripts/triage.py logs/issue72/run-20261020-193903.error.log --lines 1:80
```

## When it appeared

This is an older, machine-dependent startup bug. It was reported on v0.10.5,
but the same crash path was already shipped in **v0.1.0 on 2026-10-04**, the
first public release. The reporter also says older builds fail on their PC.
History does not establish when that PC first encountered the bad placement.

| History evidence | What it establishes |
|---|---|
| Toolkit `7a71ed2`, 2026-03-10 | The initial memory-layout file already selects RAM independently and translates guest addresses with an offset |
| Toolkit `75119d5`, 2026-09-16, “Add test cases” | Fixes iteration of the base-hint array so its NULL/OS-chosen fallback is actually tried; an arbitrary base such as `0xBFFF0000` becomes reachable when fixed hints fail |
| Toolkit `9547d39`, 2026-09-27, “Stop leaking the RAM mirror span reservation on Windows” | Removes an ineffective POSIX-style partial-reservation attempt from Windows; its message says Windows already fell through to the fixed-base loop. It does not introduce the fallback |
| Public tag `v0.1.0`, toolkit pin `aa1a1b91` | Already includes the fallback changes, required apertures that only warn on failure, the unguarded AC97 copy, and the call to it after layout initialization |
| Public tag `v0.4.0`, 2026-10-07 | Adds the pre-game launcher before guest-memory initialization, which can change host address-space occupancy; an exposure hypothesis, not a proven trigger on this PC |
| `v0.10.4` → `v0.10.5` | No change to the toolkit pin, `src/main.c` or `src/hooks/ac97_bm.c`; the startup memory-placement code was not changed by this release |

Primary source links: [toolkit fallback change](https://github.com/vyanhursky/xboxrecomp/commit/75119d5),
[Windows reservation cleanup](https://github.com/vyanhursky/xboxrecomp/commit/9547d39),
[AC97 initialization in v0.1.0](https://github.com/vyanhursky/DefJamFFNY-recomp/blob/v0.1.0/src/hooks/ac97_bm.c#L134-L151).

In plain language: the port found a place for Xbox RAM but did not check that
the other memory areas needed by the emulated devices could fit around it.
Windows refused those other allocations, and the port carried on into audio
initialization anyway. Reading that missing memory caused the C-runtime crash.
The chosen addresses can differ between PCs and runs, so the age of the code
does not tell us the date it first failed on a particular computer.

## Fix

Toolkit branch `defjam/issue72-memory-layout`, isolated worktree
`logs/issue72/toolkit`, local commit `e81806613baf5a8c20e9b2a09e61cb103f7160fd`,
based on the released pin `32aab4d`:

- Select room for the full guest address span, at least 4 GB of virtual address
  space, rather than just the 64 MB RAM view. This is an address-space probe,
  with no physical-memory commitment for the full span.
- Release that probe in full, then place RAM, physical/tiled views, device
  apertures and RAM mirrors as one transaction, before copying the XBE or
  starting register-polling threads. Ordinary fixed-address Win32 calls refuse
  collisions and never overwrite a foreign allocation. If placement races with
  another allocation, release every owned mapping and retry a newly selected
  span, at most eight times. No partial Win32 reservation releases, placeholder
  APIs or newer Windows SDK requirement.
- Return a clear initialization failure if no complete layout can be placed.
  Device initialization cannot then reach the invalid AC97 copy.
- Keep hardware windows ahead of overlapping generic RAM mirrors for larger
  RAM/map configurations.
- Start the NV2A polling worker after layout completion. On teardown, stop the
  workers before releasing windows, do not independently free the kernel-page
  pointer inside physical memory, unmap file views with `UnmapViewOfFile`, and
  close both backing handles. These ownership rules also make retries/re-init
  reliable.

The ordinary macOS/Linux placement path is retained. The shared change moves
the NV2A worker start to the end of layout initialization and corrects kernel
page/backing-handle ownership on shutdown.

## Validation and publication

The game-free `tests/windows_guest_layout` fixture exercises the actual Windows
placement helper through real memory mappings: native Win32 on Windows, the
runtime's Win32 compatibility primitives on macOS/Linux. On the M1 Pro it passes
a real MCPX collision while RAM is free, each of 34 placement failures, retries
and exhaustion, span-reservation failure, alias contents, AC97 accessibility,
teardown/re-init, and a 128 MB configuration with hardware-overlapping mirrors.

The Mac game was rebuilt using the isolated toolkit worktree and its existing,
verified analysis/lift inputs. Final results on the M1 Pro:

| Check | Result |
|---|---|
| Windows allocation algorithm, through the POSIX primitives | 1/1 fixture passes; collision, 34 failure points, all 28 retail mirrors, retries/exhaustion, aliases, re-init and 128 MB layout |
| Existing native POSIX memory-layout fixture | 1/1 passes, including teardown and second initialization |
| Project unit tests | 478 passed, 44 skipped, 1 deselected (`not slow`) |
| Loading/title/menu goldens, launcher/overlay, unlock and picture settings | All seven pass |
| One-on-one, FFA, Terrordome FFA | All three pass; median 120 presents per 2 s; minima 120, 119 and 118 respectively |
| Combat to result / two-controller versus | 27/27 and 26/26 assertions, including audio health and save/fixture integrity |
| Deterministic replay | All 80 state records over 1800 steps match the golden hash |
| Story intro, crib, Learn Moves | All three pass, including cutscenes and preview-movie request |
| Boot soak | 3/3 reach the main menu, zero hangs/failures |
| Build-state verification | Passes against the isolated toolkit; no game left running |

All 17 game checks in the full suite were covered across two complementary
runs. The first invocation used plain Python without pytest and the harness's
empty fallback data root: ten game checks passed, but combat/versus/replay had
no profile fixture. It was stopped through the save guard, whose restoration
of the original tree/absence was verified. The seven remaining checks then
passed with the established data root, verified `mac-profiles` fixture and the
documented `uv` Python environment. Unit tests were also rerun successfully
with that environment. This was not a single clean 18/18 command invocation.

Local evidence: `logs/issue72/full-regression.txt`,
`logs/issue72/remaining-regression.txt`, `logs/regress-20261020-180044.txt`,
`logs/issue72/unit-tests.txt`, `logs/issue72/windows-layout-fixture.txt`,
`logs/issue72/memory-posix-fixture.txt`; scenario reports
`logs/scenarios/regress-combat-20261020-174242`,
`regress-versus-20261020-174615`, `regress-replay-20261020-174948`.

Native Windows compilation, the allocator fixture on Windows, and the reporter's
installed-game retest remain required. The Mac fixture verifies the allocator's
algorithm and cleanup; it cannot establish Windows driver/ASLR behavior.

The initial investigation did not publish source or post an issue comment.
In the follow-up, Vlad requested a Windows test artifact and a comment linking
it and asking the reporter to test. A branch-scoped Windows candidate workflow
is prepared in `.github/workflows/windows-candidate.yml`. It gates the artifact
on native Windows memory fixtures, game-side source compilation, installer
tests, payload inventory and packaged smoke tests. It uploads only the game-free
setup, SHA-256 and provenance, not a built game or translated code.

The candidate keeps the v0.10.5 source baseline plus the memory fix, to avoid
mixing the unrelated v0.10.6 launcher beta into this diagnostic test. Its Actions
artifact name and provenance distinguish it from the normal v0.10.5 installer;
no stable release is replaced. Publishing and starting the Windows runner are
currently blocked by the expired GitHub CLI login (HTTP 401) and unavailable
Git Keychain credential. The user has been asked to restore the CLI login.

Keep the parent gitlink at published `32aab4d` until the reviewed toolkit
commit is published, then update it for the candidate. If a later integration
target includes the separately published texture-list fix `72bec86`, apply
this topic on that fork tip so the other fix is retained. Native Windows build
results, the actual artifact URL and the sent issue-comment URL must be recorded
after publication. No built game executable may be distributed.
