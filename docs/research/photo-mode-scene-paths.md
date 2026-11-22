# Photo Mode scene paths and qualification

Windows native investigation on 2026-11-22, branch `feat/photo-mode`, based on `f80a792`, toolkit `d108a64c0f272da2ab29016914f473018c3e2347`, Release preset. See the [player guide](../photo-mode.md) and [complete plan](../photo-mode-plan.md).

## Freeze and camera boundaries

The measured Battle screen has vtable `0x29D5E4`, update `sub_00079B60` and renderer `sub_000796A0`. The other fight family pairs `sub_0007A8F0` with `sub_00079E40`. Freezing the fight tick retains rendering while stopping simulation work. `sub_00087700` supplies the simulation heartbeat.

The camera is registry slot 4 (`MEM32(0x2FB158)`). Eye/target/up start at `view+0x4C/+0x5C/+0x6C`. Projection is `MEM32(view+0x34)` and horizontal-at-4:3 FOV is at `projection+0xC`. Publish through `sub_00018F90` before culling, set the projection dirty bit and restore the entry camera on exit. Temporary source vectors, guest registers, FPU and XMM state are preserved.

All guest calls run on the guest thread. The GPU callback only copies completed pixels. When pause stops normal fight rendering, `sub_00077740` supplies a guest root-render boundary. Photo Mode calls the stored fight renderer under the original render lock (`0x2FB000`), preserving the pause modal for return.

## Pause and UI ownership

Battle pause leaves the observed time scale at **1.00**, with no simulation heartbeat. Neither `[screen+4]+0x24` nor `0x39C0C0 & 0x40` is a verified pause flag. Paused origin is detected from absence of simulation for over 200 ms in combat; the activation chord lasts 500 ms.

`screen+0x24` is a lifecycle field. Accept only zero phase and qualified fight states 3 (entrance), 4/5 (lead-in/combat), 8 (combat). Victory/result states are excluded. Static code dispatches state 10 through `89F20` to IntroExtro updater `A2EA0`, but its natural entry has not been qualified.

| Callback | Visibility handling |
| --- | --- |
| `B5AD0`, `B70D0` | Hide fight HUD/tutorial passes when requested or during pending capture. |
| `6AFD0` | Suppress only the attached fight panel (`screen+0x38`, other family `+0x40`). |
| `CE200` | Suppress only the owned pause panel/dimmer (`screen+0x2C`, other family `+0x34`). |

The generated **game_audio** category on `CE200` was misleading. `793A0` constructs the `screen+0x2C` child through `CCE60`, stores it at `794FF`, then initializes it through `CDDC0` (`pause.xsh`). `796A0` passes that exact child to `CE200` at `79844–7984C`. Quad/text code and native images established the correct seam. Unrelated `CE200` callers remain unchanged.

Menus do not acquire a fight-render candidate. Match start and Battle teardown clear ownership. Nonzero projection modes are rejected; the existing [camera investigation](../widescreen/05-cameras-and-venues.md) identifies mode 1 on the CINEMA path. This is a conservative projection check, not a semantic cutscene flag. Story and other-family coverage remain distinct from Battle evidence.

## Native evidence

Runs use the owner's extracted dump through directory links and an independently copied save under `logs/runtime-data`. Harness guards restore the complete save root byte-identically. Logs, captures and save bytes stay local.

| Check | Evidence |
| --- | --- |
| Live prototype | `run-20261122-103500.log.err`: 354 camera publications over six seconds, stable fighter/timer hash, visible camera translation, combat resumed. |
| Paused prototype | `run-20261122-111505.log.err`: 346 publications, stable hash, zero simulation samples during/after, scale 1.00 preserved. |
| Full controller, paused | `run-20261122-114133.log.err`, `photo-controller-paused-probe-3.log`: 964 publications, zero simulation steps during/after, settings and reset passed. Three 1708×960 PNGs; first two byte-identical with controls shown/hidden. Clean PNG visually inspected; pause panel/HUD restored on exit. |
| Full controller, live | `run-20261122-114527.log.err`, `photo-final-controller.log`: chord, flight, height, look, FOV, roll, speed, sensitivity, invert Y, HUD, guides, reset, three PNGs and combat resumption passed. Window inspection confirmed controls/save feedback/guides; PNG inspection confirmed their exclusion with HUD preview enabled. |
| Entrance | `run-20261122-114735.log.err`, `photo-final-entrance.log`: entry in state 3, 346 camera publications over six seconds, unchanged fighter/joint/timer hash, zero simulation during Photo Mode, then the entrance progressed into combat. |
| Rejected contexts | `run-20261122-115410.log.err` (main menu), `run-20261122-115450.log.err` (Story sc05): the virtual pad sampled the complete chord twice, Photo Mode never entered, captures and clean runtime confirmed the intended contexts. |
| Save failure | `run-20261122-115512.log.err`, `photo-save-failure.log`: output destination was a regular file; three save errors, no PNGs, controls/reset and return to the paused fight passed. |

Freeze hashes cover four fighter records, including twenty world joints each, and timer bytes. No changed hash or simulation sample during Photo Mode is accepted. Identical same-pose PNGs additionally cover visible crowd/scenery/effects in these sampled frames. This does not qualify every hazard, effect or venue.

## Retained failed trials

Initial probes incorrectly assumed only state 8 was combat, selected an unused renderer, or inferred pause from unrelated fields. `run-20261122-112717.log.err` sent `rthumb` in the seconds-script grammar, which requires `rs`; no chord reached the controller. The corrected trial passed controls/file checks but PNGs still contained GAME PAUSED (`run-20261122-113440.log.err`). That image failure led to the owned `CE200` guard and successful repeat. File validity alone is insufficient clean-capture evidence.

The first victory route (`run-20261122-114942.log.err`) went from combat directly to state 11 and results; no victory scene was rendered and the probe correctly failed. `8AB00` branches to state 11 when the transient word at `3BE0F8` omits bit `0x40`. A second attempt (`run-20261122-115801.log.err`) set that word from the render callback, but normal updates rewrote it before the result decision. The controlled fixture must select the engine's extro branch at the result boundary. This is a test setup, not evidence of ordinary Battle automatically playing a victory scene. Production Photo Mode does not alter this word or force scenes to play.

The result-boundary attempt (`run-20261122-120504.log.err`) reached state 9 but never entered Photo Mode. It encountered three non-code indirect calls while preparing the forced sequence (first at guest `0xE61FF`, log line 36242). The save guard restored the data. This was a failed synthetic scene setup, not a passing freeze test. All forcing hooks and writes were removed; victory entry is disabled pending a natural reproducer. Source-specific regression results are recorded in [PR #303](https://github.com/vyanhursky/DefJamFFNY-recomp/pull/303).

## Remaining qualification

Native macOS/Linux, physical controllers, disconnect/reconnect, multiplayer, Story fights, special attacks, venue hazards and repeated long sessions need release/owner play-testing. No complete campaign acceptance is implied by the Windows probes.
