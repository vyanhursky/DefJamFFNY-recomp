# Fighter AI profile registration — 2026-11-05

Local M2 checkpoint, not a shipping package format. No external project code
was used. Original files, generated native C, test assets and captures stay
in ignored local storage.

## Native boundary and supported data

D6EE0 builds a0xC4-byte configuration: stage name at0, mode at0x20, four
32-byte profile names at0x24, controller selectors at0xA4 and special flags
at0xB4. Native filename derivation treats some fighter IDs specially and can
fall back to an original profile. Core IDs are not profile identities.

The real C9110 wrapper now binds owned profile names using full zero-based
cores at3B90B8. It changes only an occupied participant's profile string.
C9110 retains native stage loading, four0x890-byte AI records, parsing and
thiscall ret4 ownership. Its fallback mutates the supplied name; the adapter
checks names after return and refuses a silent fallback. It logs parsed
values from each of the four24-DWORD tendency rows per participant. Primary
inspection of C8AA0 confirms its24 fields,0x60 row stride and decimal parser.

The Python compiler adds named profiles and tendency resources to a verified
local AI archive. It accepts easy/normal/hard, four tendency slots each, and
23 editable named integer fields. Specification_environment stays inherited.
The supported1..5 authoring range comes from the observed profile corpus;
it is a validation policy, not a proof that all native consumers require it.
No creator XML, expressions, stage programs or trigger instructions are admitted.
Original stage and trigger bytes and untouched profiles remain unchanged.
Native string fields are bounded to31 ASCII basename characters; generated
names are27 characters and collision checked. XML is bounded, rejects DTDs
and entities, and is generated from canonical data rather than concatenated
creator text.

FIA1 uses a48-byte header with version/count/archive size/SHA256 and sorted
36-byte rows (full core plus32-byte name). Cores141..16383 can share a profile;
resource population4096 and archive512MiB are compiler budgets, not measured
performance claims. The runtime verifies receipt/file hashes, row ordering,
core bounds, ASCII names, NUL padding and exact lengths before activation.
No mod-supplied pointer or executable bytecode enters the adapter.

## Validation

28 focused Python/MSVC tests pass (`logs/fighter-ai-native-unit-nov05.txt`):
independent/shared profiles, unchanged originals/config fields, inactive and
retail fallback behavior, invalid names/receipts, numerical limits and rejection
of arbitrary expressions/fields. Real source template composition also passes:
`logs/fighter-ai-template-validation-nov05.json`.

CPU native run040424 passes five combat assertions. Four custom cores256..259
load distinct profiles; all16 parsed tendency rows contain the requested
Attack_versus_Defend and Punch_versus_Kick values1/2/3/4 for their respective
cores.174 frame reports min99/median120/max120; zero crash, watchdog,
debug-layer, truncated-batch or unresolved-call faults; one save generation
restored byte-identically. Logs: `logs/run-20261105-040424.log.err` and
`logs/fighter-authored-ai-cpu-native.txt`.

Four-human041104 passes six combat assertions and199 frame reports
min96/median120/max120, the same zero fault categories and byte-identical
one-generation save restoration. Logs: `logs/run-20261105-041104.log.err`
and `logs/fighter-authored-ai-human-native.txt`. This verifies coexistence and
binding under both controller configurations; it does not claim a statistical
AI difficulty/behavior comparison or long lifecycle acceptance.

Both runs also load four owned animation and voice banks. Detailed animation
execution attribution is separate. Final stock regression after the combined
motion changes is pending. M2 cinematic/Blazin and move-event work remains;
no M3, public push or PR.
