# Windows bundled toolchain qualification plan

Owner: Vlad. Started 2026-11-23. Status: **in progress; production cutover is not qualified**.

This plan tracks the implementation and acceptance needed to remove Visual
Studio Build Tools as a prerequisite for new Windows installations. Every
required scenario below needs evidence from the actual candidate, or an
explicit owner-accepted exception, before the default can change. A unit test
or game-free probe does not count as a real clean-client installation.

## Scope and source

- Follow-up branch: `feat/windows-bundled-toolchain` in the separate
  `defjam-toolchain-rollout` worktree.
- Integration starting point: `5dbf623e493efdb58ea7916a2edbba1b05fef646`, combining
  current main `3b60764` (v1.2.2) and [spike PR #312](https://github.com/vyanhursky/DefJamFFNY-recomp/pull/312)
  at `d392400`. PR #312 remains a separate review; this plan does not merge it.
- Toolkit: published TLS fix `274e6fbd63de904562d73c960aad674ace2caf6a`.
- Compiler candidate: LLVM-MinGW 20261117 UCRT x64, Clang 23.1.6, with pinned
  CMake 3.31.6 and Ninja 1.11.1. Archive hashes and the earlier runtime evidence
  are in [the spike report](windows-toolchain-189.md).
- The spike's 36 green checks and v1.2.1 gameplay evidence are background
  evidence. They do not establish installer acceptance for this integration.

## Environment and controls

| Environment | Purpose | Current status |
|---|---|---|
| GitHub hosted Windows Server 2025 | Packaging, compiler, unit and failure-path tests using game-free fixtures | Available; developer tools preinstalled, so not a clean-client gate |
| Local clean Windows 11 guest | First install without VS/SDK, standard account, private real-game checks | Owned Gen2 VM created, powered off; official evaluation ISO downloading |
| Local clean Windows 10 guest | Supported older-client compatibility and installation | Official Microsoft LTSC 2021 evaluation link responds; media download/install pending |

The owner explicitly authorized local VMs and, if necessary, uninstalling host
MSVC on 2026-11-23. Prefer clean guests and preserve the host tools. Start only
one guest at a time, initially with 2 virtual CPUs and 6 GB RAM; require at least
12 GB host free RAM before starting it. Use dynamic virtual disks in a dedicated
private workspace. Do not change unrelated VMs, host security settings or
reboot the host automatically.

Compiler experiments run in disposable hosted runners or isolated guests.
Local source editing, git, static parsing and infrastructure inspection remain
allowed. Do not compile directly on the host. Do not run further Learn Moves,
image-golden or screenshot comparisons. Functional guest smoke uses logs and
state assertions, with no screenshot comparisons.

Game dumps, lifted code, game executables, profiles and VM credentials remain
local/private. Public CI uses game-free fixtures and uploads logs only. Keep
guest credentials and original game paths out of checked-in files. Preserve
the owner's installed game, saves, settings and mods; test independent copies.

## Status rules

Use **planned**, **in progress**, **blocked**, **failed** or **passed**. Record
the source SHA, payload/toolchain fingerprint, OS build, account/elevation,
command or automation entry point, receipt/log and result for each real run.
Retain the failed attempt when a later retry passes. An unavailable environment
is blocked, not passed. Never mark a synthetic engine test as a real installer
or game qualification.

## Implementation work

| ID | Work | Acceptance | Status and evidence |
|---|---|---|---|
| I01 | Audit engine, app preflight, packaging and transaction paths | One consistent per-payload backend contract; explicit legacy behavior | Passed source audit: optional per-payload descriptor selects LLVM; absent descriptor retains historical MSVC; selected releases run their own engine |
| I02 | Stage the pinned Windows toolchain and notices | Verified/pruned inventory; static runtime closure; measured ZIP/expanded/peak disk size; no game bytes | In progress: actual pinned archives staged successfully; 6,836 files / 347,978,721 bytes including the toolchain CMake file and Ninja notice; final ZIP/import/peak-disk audit pending |
| I03 | Select bundled tools in engine and app preflight | New payload builds without VS detection/bootstrap; old payloads retain their compatible path; explicit host choice remains possible | In progress: engine, preflight and explicit asset allowlists implemented; contract tests pass; packaged native and clean-guest execution pending |
| I04 | Record compiler identity and protect caches | Backend, executable/tool inventory and relevant flags identify build trees; no MSVC object reuse in LLVM builds | In progress: tools/CMake fingerprint, per-version note and receipt metadata implemented; synthetic compiler-switch test discards objects while preserving generated sources; native evidence pending |
| I05 | Integrate staging, repair, update and rollback | Failed/cancelled attempts preserve the active install and matching toolchain/version metadata | Planned |
| I06 | Add hosted contract and failure-path coverage | Tests exercise production paths with verified game-free fixtures and retain structured evidence | In progress: 255 focused tests passed / 30 platform skips across two suites; hosted real-engine native fixture added, not yet run |
| I07 | Prepare private clean guests | Official media, no VS/SDK, administrator and standard accounts, snapshots and bounded resources | In progress: scoped elevated worker verified; Win11 VM created with 2 CPUs, 6 GB static RAM, dynamic 64 GB disk, Secure Boot/vTPM. Private DPAPI credentials and unattended answer ISO generated; OS installation pending |

## Required scenario matrix

| ID | Scenario | Acceptance | Environment | Status and evidence |
|---|---|---|---|---|
| W01 | Clean Windows 11 first install | Verify absence of VS/SDK; standard account completes extraction, lift, build and launch using the payload; no Microsoft installer, elevation or restart | Clean Win11 guest | Blocked on guest provisioning and installer integration |
| W02 | Clean Windows 10 first install | Same as W01; record exact Windows edition/build and supported API/runtime compatibility | Clean Win10 guest | Blocked on guest provisioning and installer integration |
| W03 | Upgrade an existing MSVC-built install | Switch to LLVM with a fresh compatible build tree; preserve profile/settings/mod hashes and previous working version until activation succeeds | Guest with controlled legacy install | Planned |
| W04 | Repair missing output | Remove only disposable installed build output; rebuild with the recorded bundled compiler, without VS bootstrap or data loss | Guest | Planned |
| W05 | Rollback and historical release | Restore a working version with its matching metadata; unported historical source must not silently rebuild with an incompatible compiler | Guest | Planned |
| W06 | Spaces, Unicode, long paths and junctions | Actual packaged tools build under normal parallelism and serial mode; assert physical executable paths; no startup hang | Hosted fixture, then guest full build | Planned; spike's corrected small probe already passed remotely |
| W07 | Offline repeat and retry | After payload/dependencies are available, a fresh build/repair needs no network; interrupted downloads resume or retry safely | Hosted fixtures and guest | Planned |
| W08 | Corrupt or missing package/cache file | Checksum/inventory failure precedes executing affected tools; clear repair/retry result, preserved active install | Hosted fixtures and guest | Planned |
| W09 | Low disk space | Preflight or bounded stage failure preserves data and working install; include temporary/cache/retained-version space | Hosted fixtures and guest | Planned |
| W10 | Cancel and interrupted build | Cancel during extraction/configure/compile/activation; child processes are bounded, locks recover, active install/data remain intact | Hosted fixtures and guest | Planned |
| W11 | Game running or output locked | Update/repair fails or defers cleanly, preserving the existing executable and data | Guest only | Planned |
| W12 | Packaged-build functional smoke | Log/state assertions establish startup, fight entry, input/audio activity and exact guarded save restoration; no visual comparisons | Private guest with owner's dump | Blocked on guest, payload and real build |
| W13 | Packaged-build diagnostics | Matching PDB/map, named guest/native stacks, TLS register inspection and controlled disposable-child fault reporting | Private guest | Planned; earlier spike diagnostics are background evidence |
| W14 | Release inventory and provenance | Final app payload passes explicit allowlists, notice inventory, hashes, game-free checks and import audits; measure sizes | Hosted runner | Planned |

The clean-client scenarios require the actual installation workflow. Hosted
Windows's preinstalled SDK/VS and mocked subprocesses cannot satisfy W01/W02.
VM timing is not a new physical-PC performance claim. Reuse earlier unchanged
gameplay evidence where applicable; any compiler/flag change that invalidates
it must be identified before scheduling additional qualification.

## Progress and evidence

| Date | Event | Result and next action |
|---|---|---|
| 2026-11-23 | Plan and separate integration worktree created | Main and reviewed spike combined at `5dbf623`; production installation unchanged |
| 2026-11-23 | Initial source audit | Engine is VS-only on Windows; app preflight and payload allowlists also need integration. Existing compiler identity invalidation can be reused |
| 2026-11-23 | Private environment discovery | No pre-existing VM supplied. Owner authorized local VMs and optional host MSVC removal. Hyper-V services are running; current token lacks management permission |
| 2026-11-23 | Scoped Hyper-V worker started | Administrative `inspect` and `create` requests succeeded. New Win11 guest is off, no existing VMs found or changed. Host MSVC preserved |
| 2026-11-23 | First production integration and focused checks | `test_windows_bundled_setup`, engine, app contract and source release: 143 passed / 9 skipped; update/app/handoff/Linux/status: 112 passed / 21 skipped. No native host compilation |
| 2026-11-23 | Actual archive staging | `staged-tools.json` in private qualification logs records four verified upstream inputs, 6,836 files / 347,978,721 bytes and fingerprint `4c9f16de0918349ba6fc5f6cfa552d37f0af61ae10858fd8d870a66dc4192887`. This is packaging evidence only |
| 2026-11-23 | Media acquisition | Win11 official download resumed with byte-range support after replacing its insufficient transfer deadline; prior stopped attempt retained. Microsoft-published Win10 LTSC evaluation link also responds (build 19044.1288); OS checks remain pending |

## Qualification tools and evidence

`scripts/qualification/windows-vm-host.ps1` is a bounded, elevated Hyper-V
worker for the two exactly named owned guests. It validates the VM ownership
note, limits resources and accepts only VM operations. Requests, results,
media, credentials and guest scripts remain outside Git in the private VM
workspace. The worker shuts down its owned guests at its deadline. It does
not uninstall host tools, enable Windows features or reboot the host.

`windows-vm-answer.py` creates private unattended media using the verified
pure-Python pycdlib 1.22.0 wheel (SHA-256
`bfa0b3631345a14b2741fe088398b6b8dc2838442ea607fd07d027dcc67b9e94`).
The private root grants access only to its owner, Administrators and SYSTEM.
Passwords are generated locally; the retained host credential file uses
current-user DPAPI. The answer ISO necessarily contains disposable guest
passwords and must stay private. It partitions only guest Disk 0 through
Windows Setup when attached to the fresh owned guest. Never attach it to an
existing system.

`windows-native-setup.py` runs the packaged engine and tools with explicitly
synthetic source/dump fixtures on hosted Windows or a guest. It exercises
native marker install, update, downgrade, missing-output repair, rebuild,
early cancellation and corrupt-payload rejection, checking protected data,
compiler identity and receipt preservation. CI retains JSON and text logs
for seven days. It is excluded from the client payload with the host VM
helpers. These fixtures do not replace W01/W02 or private real-game gates.

Official guest/media references: [PowerShell Direct](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/powershell-direct),
[Windows 11 evaluation media](https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise),
and [Microsoft's published Windows 10 evaluation links](https://techcommunity.microsoft.com/discussions/windows11/accessing-trials-and-kits-for-windows/3361125).
Use official HTTPS media only; retain measured hashes and distinguish them
from an independently matched Microsoft-published hash.

## Completion decision

Keep this section current with the final candidate SHA and scenario results.
Do not announce that MSVC can be removed from production Setup until I01–I07
and W01–W14 are passed or explicitly excepted by the owner. Unresolved PC
freezing is not considered fixed by this work. The integration remains a
separate review and release decision from spike PR #312.
