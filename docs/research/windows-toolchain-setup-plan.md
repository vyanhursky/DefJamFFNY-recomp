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
| Local clean Windows 11 guest | First install without VS/SDK, standard account, private real-game checks | Owned Gen2 VM created/off; 26H2 evaluation ISO matches Microsoft's published SHA-256; OS installation pending; elevated worker available until 22:08 UTC November 24 |
| Local clean Windows 10 guest | Supported older-client compatibility and installation | LTSC 2021 evaluation installed, build 19044, 2 CPUs/6 GB; initial inventory finds no VS/SDK and a non-admin standard account. Standard desktop established; frozen-payload real install, fight/audio/save smoke, diagnostics and offline repair pass without VS/SDK; expired evaluation licensing is a recorded guest limitation |

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
| I02 | Stage the pinned Windows toolchain and notices | Verified/pruned inventory; static runtime closure; measured ZIP/expanded/peak disk size; no game bytes | Passed: pinned staged tool/notice inventory and explicit Windows DLL import audits; frozen final payload 150,938,017 ZIP bytes / 521,491,398 expanded bytes, app 155,291,648 bytes; real first install additional disk peak sampled at 3,992,891,392 bytes (dump copy included, already-cached payload/input excluded) |
| I03 | Select bundled tools in engine and app preflight | New payload builds without VS detection/bootstrap; old payloads retain their compatible path; explicit host choice remains possible | Passed: consistent descriptor/backend selection, preflight and allowlists; hosted native 14/14 and clean Win10 standard-user real install/repair succeed without VS/SDK or bootstrap. Legacy fallback separately qualified in W05 |
| I04 | Record compiler identity and protect caches | Backend, executable/tool inventory and relevant flags identify build trees; no MSVC object reuse in LLVM builds | Passed: inventory/CMake fingerprint and per-version identity appear in actual clean-client receipts; native compiler-switch fixture discards stale objects; real controlled MSVC-to-LLVM upgrade uses a fresh tree and retains previous version (`144`/`145`) |
| I05 | Integrate staging, repair, update and rollback | Failed/cancelled attempts preserve the active install and matching toolchain/version metadata | Passed: hosted native 14/14 including activation recovery, plus clean Win10 real missing-output repair, MSVC migration, historical prerequisite refusal, corrupt-tool rejection and actual mid-extraction cancellation; all protected hashes preserved |
| I06 | Add hosted contract and failure-path coverage | Tests exercise production paths with verified game-free fixtures and retain structured evidence | Passed hosted contract/failure coverage: CI `45469548837` and spike `45469548788` succeed at head `f7b6d97`; frozen packaged merge `5262ff7`. Native marker 14/14, CP437 control, inventories and import audits pass; private client outcomes tracked below |
| I07 | Prepare private clean guests | Official media, no VS/SDK, administrator and standard accounts, snapshots and bounded resources | In progress: scoped elevated worker verified; Win11 VM created with 2 CPUs, 6 GB static RAM, dynamic 64 GB disk, Secure Boot/vTPM. Private DPAPI credentials and unattended answer ISO generated; OS installation pending |

## Required scenario matrix

| ID | Scenario | Acceptance | Environment | Status and evidence |
|---|---|---|---|---|
| W01 | Clean Windows 11 first install | Verify absence of VS/SDK; standard account completes extraction, lift, build and launch using the payload; no Microsoft installer, elevation or restart | Clean Win11 guest | In progress: verified media and owned VM ready; Windows 11 installation remains pending |
| W02 | Clean Windows 10 first install | Same as W01; record exact Windows edition/build and supported API/runtime compatibility | Clean Win10 guest | Passed for LTSC Evaluation 19044.1288: frozen `407413e` real install in 442.57 seconds, fight/audio/save smoke and diagnostics, standard non-admin account, no VS/SDK/elevation/restart. Evaluation-license shutdown recorded separately; no other Win10 edition inferred |
| W03 | Upgrade an existing MSVC-built install | Switch to LLVM with a fresh compatible build tree; preserve profile/settings/mod hashes and previous working version until activation succeeds | Guest with controlled legacy install | Passed: controlled real v1.2.1 MSVC baseline verified and booted; actual offline update to frozen `407413e` succeeds in 429.19 seconds with fresh LLVM tree, all 11 protected files identical and old MSVC version retained (`144`/`145`). Updated native wrapper launches the exact new EXE and restores save guard |
| W04 | Repair missing output | Remove only disposable installed build output; rebuild with the recorded bundled compiler, without VS bootstrap or data loss | Guest | Passed Win10 real frozen `407413e`: delete only disposable active EXE; fresh build/activation succeeds offline in 192.23 seconds, same bundled identity, eight protected files identical (`122`) |
| W05 | Rollback and historical release | Restore a working version with its matching metadata; unported historical source must not silently rebuild with an incompatible compiler | Guest | Passed scoped gates: three hosted native activation failures recover exact previous launcher/INI/receipt bytes; clean Win10 actual historical v1.2.1 downgrade returns expected prerequisite code 3 with no VS/SDK, active LLVM receipt and 11 protected files unchanged. Both working version trees retained; no claim that unported old source builds with LLVM |
| W06 | Spaces, Unicode, long paths and junctions | Actual packaged tools build under normal parallelism and serial mode; assert physical executable paths; no startup hang | Hosted fixture, then guest full build | Passed: original Unicode failure retained; explicit UTF-8 fix passes CP437 control, clean Win10 native 14/14 and full Unicode-path game build. Packaged C/C++/archive/RC/TLS/UTF-8/import fixture passes serial and parallel=2 through physical accented paths and source/compiler junctions, compiler resolves to physical EXE (`132`). Long-path policy off: 258-character payload path stages; oversized path rejected early with code 2 (`062`) |
| W07 | Offline repeat and retry | After payload/dependencies are available, a fresh build/repair needs no network; interrupted downloads resume or retry safely | Hosted fixtures and guest | Passed: Hyper-V adapter disconnected (`099`); actual missing-output repair completes in 192.23 seconds with eight protected files identical (`122`), no VS/SDK. Download checksum/truncation/cache and offline metadata covered by `test_setup_updates`; no real-game payload exposed to hosted runners |
| W08 | Corrupt or missing package/cache file | Checksum/inventory failure precedes executing affected tools; clear repair/retry result, preserved active install | Hosted fixtures and guest | Passed: hosted missing/inventory contracts and native corruption case; clean Win10 actual frozen Ninja corruption rejected with code 2 in 24.15 seconds before execution, previous active receipt and 11 protected files identical; original payload bytes restored (`145`) |
| W09 | Low disk space | Preflight or bounded stage failure preserves data and working install; include temporary/cache/retained-version space | Hosted fixtures and guest | Passed Win10 controlled install on guest-only 1 GiB virtual disk: expected code 2 and 12 GiB headroom message, EXE/PDB/map/receipt hashes unchanged (`101`). Real successful-install peak also sampled; no host disk touched |
| W10 | Cancel and interrupted build | Cancel during extraction/configure/compile/activation; child processes are bounded, locks recover, active install/data remain intact | Hosted fixtures and guest | Passed: hosted early/configure/compile cancellation returns 6 and three activation hard exits recover exact install files. Clean Win10 real extraction cancellation after five files copied returns 6, preserves existing EXE/PDB/map/launcher/receipts and all six save files, leaves no published extraction or staging (`145`) |
| W11 | Game running or output locked | Update/repair fails or defers cleanly, preserving the existing executable and data | Hosted native marker, then guest real game | Passed: hosted running marker returns 5 and launcher lock returns 4 with exact recovery; clean Win10 real running game repair returns 5, previous receipt and protected data unchanged (`083`) |
| W12 | Packaged-build functional smoke | Log/state assertions establish startup, fight entry, input/audio activity and exact guarded save restoration; no visual comparisons | Private guest with owner's dump | Passed on Win10 frozen `407413e`: corrected six-file reviewed fixture; fight entry, movement, 25 attack / 43 damage events, nonzero PCM, no faults, exact save restoration, zero captures (`108`). First empty-fixture attempt retained as failed preparation |
| W13 | Packaged-build diagnostics | Matching PDB/map, named guest/native stacks, TLS register inspection and controlled disposable-child fault reporting | Private guest | Passed on clean Win10 actual `407413e` EXE/PDB/map: named native guest symbols, TLS registers, thread sampling and intentional owned-child fault in `sub_00021500`; crash names guest function, save restored (`109`). No executable file modification |
| W14 | Release inventory and provenance | Final app payload passes explicit allowlists, notice inventory, hashes, game-free checks and import audits; measure sizes | Hosted runner | Passed final code payload `5262ff7` / head `f7b6d97`: CI `45469548837` and spike `45469548788` succeed; native 14/14, CP437, package/import/notice audits green. App/payload and all 11,571 file hashes independently match provenance; exact sizes below |

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
| 2026-11-23 | First hosted integration run `45320730422`, candidate `d88fd3b` | Setup unit jobs failed because the new activation metadata referenced `version_root`, which the existing activation fixtures omit. Changed it to the equivalent `source.parent`; the complete Windows setup unit list then passed locally: 249 passed / 34 skipped. Hosted rerun pending; first failure retained |
| 2026-11-23 | Staged tool import and ZIP inventory | Tools-only ZIP: 88,028,091 bytes, SHA-256 `f8d00a627fd292f96e4288d64d283087c352b45980672afa27de1809189b3d7c`. PE imports resolve to four included LLVM DLLs plus candidate Windows system DLLs; clean guest runtime closure remains pending |
| 2026-11-23 | Corrected hosted candidate passes | CI `45321137083`, spike `45321137038`, 36/36 checks green. Native marker install/update/downgrade/repair/rebuild passed in 12.76/13.01/12.86/12.91/13.01 s; early cancellation returned 6 and corruption returned 2, preserving receipts/protected data. Windows Server 2025 build 26100; compiler fingerprint unchanged; actual packaged source `b123e61f8bf280913da48df510a0ac58ad7c6a7a` is GitHub's merge of main `3b60764` and head `4520c26` |
| 2026-11-23 | Win10 media verified | LTSC 2021 English x64 ISO SHA-256 `e4ab2e3535be5748252a8d5d57539a6e59be8d6726345ee10e7afd2cb89fefb5` matches Microsoft's published evaluation hash PDF; fresh guest remains off pending manual Windows elevation |
| 2026-11-23 | Expanded native acceptance passes | CI `45322740616`, source head `73b7e51` / tested merge `199f19cd11ccda5cb3049c75a99dab6ad0b2e7c3`, all 14 cases pass and 36/36 PR checks green. Configure/compile cancellation: 6; running installed program: 5; locked launcher: 4. Forced exits at prepared/launcher/receipt-json: 91, followed by exact receipt/INI/launcher restoration. Native builds 9.91–10.34 s; same Windows Server 2025 build 26100 and compiler fingerprint |
| 2026-11-23 | Private artifact prepared | Downloaded and verified the earlier green hosted app: 155,290,112 bytes, app SHA-256 `ed20c92dabadc12b8f62ba0955d91a56b71456377d1486fdc180d585f893fe98`; embedded payload 150,936,695 bytes, SHA-256 `e806430dceb3b3029d86793b37e61675c7190aba828ee78569ea3e22b2ceb758`, source `b123e61`. Engine, toolchain, package builder, game/config/CMake and toolkit have no changes between its head `4520c26` and `73b7e51`; later changes add host qualification and static package import auditing. No native host execution |
| 2026-11-23 | Windows elevation handoff pending | The refreshed worker's UAC request ended with Windows reporting cancellation. Both guests remain off; host MSVC is unchanged. Wait for the owner's Windows elevation handoff before relaunching the reviewed bounded worker and booting a guest |
| 2026-11-23 | Both guest media ready | Win11 evaluation ISO matches Microsoft's published SHA-256 `bc3f24086ebadc94489066b5ad78089e2cf5c3491e90e790bb81a2b199c10e38`; Win10 was already matched. Private receipts retain sources and measured hashes. No OS installed or guest started |
| 2026-11-23 | Payload size and provenance verified | Candidate app and embedded payload hashes plus the complete file inventory match CI provenance. Complete payload expands to 521,487,287 bytes. Existing published v1.2.2 Windows app: 66,935,808 bytes; candidate: 155,290,112 bytes (+88,354,304 bytes, approximately 84.3 MiB). Client peak build disk usage still requires actual guest measurement |
| 2026-11-24 | Owner approved Windows elevation; Win10 installation started | Scoped worker ready at 18:08:54 UTC for four hours. Verified ISO attached, fresh guest started with 2 CPUs/6 GB; Win11 remains off. Host MSVC retained |
| 2026-11-24 | Initial clean Win10 inventory | LTSC Evaluation 64-bit 10.0.19044, no VS/SDK paths, `DJQualUser` outside Administrators; 49,465,958,400 free disk bytes. Standard desktop not present yet during first-login provisioning. Receipt `007-inventory-win10.json`; candidate transfer begun. No compiler executed on host |
| 2026-11-24 | Standard-user desktop established | First boot selected the temporary setup account despite unattended standard-user settings. Configured the intended disposable account from its private answer media and rebooted only the guest; inventory `013` confirms the standard desktop and no admin membership. Checkpoint `clean-payload-ready-win10` retained |
| 2026-11-24 | First clean-client native failure retained | `native-win10-unicode`: standard account, elevated=false, packaged engine exits 4 at configure. Compiler/CMake/Ninja version checks pass without VS/SDK. Log `setup-20261124-182004.log` shows the resolved compiler path corrupted into console-codepage characters. The VM request reader also misdecoded a UTF-8 JSON folder name; current requests now use ASCII escapes, with explicit UTF-8 added to the worker source |
| 2026-11-24 | Unicode resolver correction | Added `ENCODING UTF-8` to the Python path resolver and UTF-8 reading of native-fixture compiler notes. A hidden-console CP437 regression uses a physical accented directory and no compiler execution; it explicitly selects shipped Ninja because a clean Windows default otherwise selects unavailable NMake. Initial NMake probe attempts are retained and do not count as resolver evidence. Focused Python tests: 146 passed / 9 skipped |
| 2026-11-24 | CP437 resolver control passes | Corrected probe v2: old resolver fails at the intended bad-path assertion and fixed resolver succeeds; both test drivers exit 0 as standard `DJQualUser`, elevated=false. Receipts `029`/`030`; physical accented root, measured code page 437, no compiler execution. Full native installer retry and hosted validation still pending |


| 2026-11-24 | Corrected clean Win10 native suite | All 14 cases pass as standard `DJQualUser`, elevated=false, under physical `Café native setup fixed`; development payload explicitly declares the single resolver correction, fingerprint `d820367e…`. Receipts `043`/`045`; original failure retained |
| 2026-11-24 | Fresh hosted candidate passes | Head `f4b6f75`, packaged merge source `407413eb66046f0f259227d579a97148ebe98830`; CI `45461979490` attempt 2 and spike `45461979522` succeed. Attempt 1 had one cancelled macOS fixture job with unavailable logs; retry passes. Windows native 14/14, CP437 control, packaging and import audits pass |
| 2026-11-24 | Frozen real clean-client installation passes | Actual production engine and unchanged CI payload, development=false; source `407413e`, toolkit `274e6fb`, fingerprint `d820367e34e4aeb10530fb6a96978aef8c57dfe5182fad26ff1b60c5ef04ded5`. Win10 standard user installs owner dump into physical accented path without VS/SDK/elevation/reboot. Exit 0, 442.57 seconds, output EXE/PDB/map hashes retained in private receipt `068`; no gameplay qualification inferred |
| 2026-11-24 | Disk and GPU measurements | Real install sampled 3,992,891,392 additional disk bytes and 3,161,485,312 peak whole-guest used RAM; concurrent qualification I/O means these are observations, not isolated performance benchmarks. D3D11 hardware and WARP device probes both succeed at feature level 11_0; no host GPU configuration changed |
| 2026-11-24 | Long-path boundary corrected | On clean Win10 with LongPathsEnabled=0, 70-character install/max payload path 258 stages; 136-character install/max path 324 initially fails late with WinError 206. Added UTF-16-aware preflight; same guest case now returns SetupError 2 before staging while supported case still succeeds. Receipts `052`/`062`; focused units 148 passed / 9 skipped. Frozen real-build payload not modified |
| 2026-11-24 | Evaluation OS interruption retained | After successful real install, Win10 licensing service initiated planned shutdown because evaluation license expired. Restarted owned guest; checking normal online activation. This is an environment limitation, not a successful functional run or compiler crash. No licensing bypass or host change |


| 2026-11-24 | First functional run is not a pass | The transferred save ZIP was empty because the fixture files live under its `save/` subdirectory. Menus/audio/presentation worked, but fight anchor was absent; exact save restoration succeeded. Corrected transfer verifies all six source hashes and six archive entries. Original run retained, no compiler change |
| 2026-11-24 | Corrected functional smoke passes | Frozen `407413e`, same Win10 standard account: 205.23 seconds total, fight plus 120-second tail, movement, 25 attacks, 43 damage events, nonzero 8,581,120-byte PCM, no runtime faults, exact guarded save restoration, zero captures. `win10-game-smoke-v2-details.json`, control receipt `108`; harness exit 1 is its expected termination of the live game, while the assertion driver exits 0 |
| 2026-11-24 | Real running-game and low-disk guards pass | Running-game repair returns 5 in 65.5 seconds with unchanged receipt/protected hashes (`083`). Independent guest-only 1 GiB disk: repair returns 2 before staging and preserves all baseline output/receipt hashes (`101`) |
| 2026-11-24 | Actual matching diagnostics pass | Native PDB stack contains guest symbols, TLS registers read, map-based thread sampling succeeds; scoped process-memory-only fault in verified owned child is reported with `sub_00021500`, save restoration succeeds. `game-diagnostics/result.json`, control `109`. No capture or on-disk executable modification |
| 2026-11-24 | Offline continuation | Adapter disconnected through scoped Hyper-V worker, PSDirect remains available. First serial/junction fixture attempt lacked its resource icon/template in the test ZIP; compiler resolution had succeeded. Preparation failure retained; corrected complete fixture isolated from independent real offline repair/migration suite |


| 2026-11-24 | Final code candidate hosted/inventory gates pass | Head `f7b6d979a268cc1591fe813b69e27521952b14db`, frozen merge `5262ff7d5da94fa5b232c7549f6ecaed5c49c9d3`; CI `45469548837`, spike `45469548788` succeed. Independently verified app SHA-256 `3a019be0162344c53a61ba5ee2d0531b767108bb1f984987a7e42fe1caea87c2`, payload `0d4fb6929d2fa74433bcd57d4e6bfdab762354c7ca218f7a41a72e12eab46838`, every manifest hash and provenance identity. 11,571 files; app 155,291,648 bytes; ZIP 150,938,017; expanded 521,491,398. Toolchain fingerprint stays `d820367e…`; distributed differences from `407413e` are the engine guard (both copies) and rebuilt launcher with unchanged source |
| 2026-11-24 | Offline real repair passes | Frozen `407413e` production engine, standard user, adapter disconnected. Removed only owned active game EXE; repair compiles/activates a fresh version in 192.23 seconds. Eight protected save/mod-manager/song files identical; previous version retained. Receipt `122` |
| 2026-11-24 | Clean-client path fixture passes | Corrected private fixture uses actual packaged compiler/CMake/Ninja, direct fixture execution (ctest is intentionally not shipped). C, C++, static archive, Windows resource/manifest, host TLS isolation, UTF-8 filesystem and Windows imports pass with jobs=1 and jobs=2; compiler is physical despite junction roots. Prior incomplete-icon/template and unavailable-ctest driver attempts retained, no product change. Receipt `132` |
| 2026-11-24 | Migration baseline established | Imported owner-qualified v1.2.1 MSVC build source `2496bd3429a854a842701070cbeb5a54c5e3f445`, toolkit `d108a64…`; original output SHA-256s verified, no host rebuild. Initial boot lacked required VC runtime DLLs; supplied official app-local redistributable DLLs beside legacy EXE only, leaving system/new LLVM environment unchanged. Baseline then presents positive frames without crash and restores its save snapshot (`132`); actual offline update in progress |


| 2026-11-24 | Real offline migration and historical guards pass | Standard Win10 user updates imported v1.2.1 MSVC to actual frozen `407413e` in 429.19 seconds. All 11 protected files identical; previous MSVC version remains. Actual historical payload downgrade returns 3 in 32.97 seconds without VS/SDK, active receipt/data unchanged. Corrupt frozen Ninja returns 2 in 24.15 seconds before execution, active receipt/data unchanged; original Ninja bytes restored in finally. `144`/`145` |
| 2026-11-24 | Real mid-extraction cancellation and upgraded launch pass | Cancellation signaled after five real dump files appear in extraction staging: code 6, no published extraction, staging removed, original executable/PDB/map/launcher/receipts and six saves identical. Updated native wrapper launches its receipt's exact LLVM EXE, child remains alive after 12 seconds, guarded saves restored. Both drivers exit 0; `145` |

The decoder failure follows [CMake CMP0176](https://cmake.org/cmake/help/v3.31/policy/CMP0176.html):
the project's older minimum version retains automatic Windows-codepage decoding
unless the call explicitly requests UTF-8. The Python resolver already emits
UTF-8. The correction changes path interpretation, with no compiler/ABI flag
change; the compiler fingerprint changes because it includes this CMake file.

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

The expanded fixture also signals from the actual CMake process before
cancelling configure/compile, launches the installed marker to test running
process refusal, holds an actual Windows file handle without write/delete
sharing, and exits during three activation checkpoints before verifying
byte-exact recovery. All 14 cases passed in hosted run `45322740616`.
`windows-guest.ps1` uses PowerShell Direct
for guest inventory and limited interactive tasks under the standard test
account; each task records its account, elevation status, times and exit.

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
