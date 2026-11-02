# Fighter Mod Support: Vendetta compatibility investigation

2026-11-01. Target milestone: **v0.15.0**. Research and implementation plan;
**the mod is not playable in our runtime as a result of this research**.
The owner requested local R&D only; no public PR or branch push.

## Revised recommendation after owner review

The owner requests a maintainable general system first, with ordinary packages
containing one or many fighters and multiple packs enabled together. The initial
proposal for an exclusive legacy compatibility bundle is withdrawn. The current
architecture, genuine alternatives and review gates are in
[Fighter Mod Support — revised plan](../fighter-mod-support.md).

Vendetta remains a possible standard-format conversion/acceptance case. Its
shared database replacements and reference-runtime assumptions do not define the
public contract. No special compatibility profile or hash-specific runtime branch
is planned. The package facts and source observations below remain useful.

## Evidence and reproducibility

- Our source: public `DefJamFFNY-recomp` main
  `e7d35e1637b1eb63ee1d8bb3b3153f3b0d083e62`, released v0.13.0;
  toolkit `d569ca10811cef67ec4e9fa2173088c2f9fd0580`.
- Reference runtime audited locally at
  `comoria08/defjam_recomp@51ad8f521f2ccb04f426e4170cf07de376b17420`.
  GitHub main was subsequently verified as
  `aca317a0a84dd6522dd68f02ef7a5e82fb749989` on this investigation date.
  Comparing those commits showed **no changes** to `src/main.c`,
  `src/recomp_manual.c`, or `outils/patch_gen.py`. Installer/launcher changes
  between them do not change the runtime findings below.
- Reference toolkit inspected locally at
  `9239a1266938dd93133ff27e9d42ab79c1190a08`. This is the inspected snapshot,
  not a claim about its current remote head or every published binary.
- Input: the owner's `Def Jam Vendetta.mod`, 120,438,865 bytes,
  SHA-256 `42645b4ad0d4b9bb502dec3db88095b7a21f061a20ad9091387b3272137f415f`.
  Its `mod.ini` version is `2026-10-31`.
- Baseline: the owner's USA extracted dump; `default.xbe` expected SHA-256
  `31cc0d11f7c656b1a6f337fdf7d9bbaac9df11c324a2fb881f7eb639d4be00c2`.
- Original diagnostic: [inspect-fighter-mod.py](../../scripts/inspect-fighter-mod.py).
  It checks all payload CRCs and records per-file SHA-256, mapping metadata,
  main-table chunk counts, and SODB header observations. It does not install,
  extract, execute, or certify compatibility. Tests use synthetic data only.

Local evidence is in the research checkout's ignored
`logs/fighter-mod-research/vendetta-inventory.json` and `baseline-targets.json`.
The ZIP was unpacked into a separate data directory outside the source tree;
all 1,883 unpacked files were compared with the recorded SHA-256 values. Nothing
was installed into the owner's game or saves. No game execution was performed.
No reference-project implementation code was copied. Runtime behavior was
reviewed as a reference; the diagnostic was written independently using the
supplied archive and our own parsers/stdlib.

Reproduce the metadata inspection:

```powershell
python scripts/inspect-fighter-mod.py "C:\path\Def Jam Vendetta.mod" --dump "C:\path\extracted" --output "new-report.json"
```

## What the package actually contains

It is a ZIP, not a new compression/container format. It contains **1,883 files**,
**207,429,829 bytes** unpacked (197.82 MiB). There is no executable patch or native
plugin in its file inventory; the game-format `.o` model files are asset data.

| Payload group | Files | Role suggested by paths/formats |
|---|---:|---|
| `screens/portrait` | 552 | Fighter portraits/cards |
| `screens/match` | 276 | Match UI imagery |
| `screens/battle` | 3 | Replacement chooseF2/3/4 selection movies |
| `assets/v2ip` | 139 | 93 model/face `.o` files and 46 `.xsh` texture files |
| `assets/v2ta` | 184 | Entry, victory, and Blazin cinematic archives |
| `assets/ai` | 46 | Fighter AI XMLs |
| `motion/wres_all` | 138 | Moveset lists and animation data |
| `motion/blazin` | 189 | Extended special-move list and animation data |
| `speech` | 346 | Voice banks, taunts, ambient voices, intro/extro streams |
| Other files | 10 | Metadata, cover, mappings, shared databases/XML/tag data |

`mod.ini` advertises **44** fighters; `coreid.txt` and
`blazin_activation.txt` each contain **46** distinct mapping records. There are
46 model texture files, numbered 610–655. Do not promise an exact selectable
roster count from the metadata: the supplied archive and its description differ.
Actual roster additions require decoding the SOD records and selection data,
then confirming in the game.

The core mapping uses ten IDs below 142 (`2,3,50,76,77,78,79,80,82,83`) and
36 new IDs (`142..177`). Voice IDs 600–645 are used except 630/631; two mappings
reuse 518/507. Core IDs, SOD handles/ranks, fighter XML IDs, model numbers and
speech-bank IDs are different namespaces and must not be conflated.

Five directly present baseline files are replaced:

| File | Original bytes | Mod bytes |
|---|---:|---:|
| `assets/djv2.sod` | 259,398 | 303,016 |
| `assets/entity.xml` | 91,595 | 99,083 |
| `audio/animtags.dat` | 474,898 | 534,098 |
| `motion/camera.xml` | 143,524 | 161,635 |
| `motion/main_all.dat` | 282,904 | 318,012 |

A directory-only comparison of original BIG4/BIGF `.viv` files under the legacy
loose-path convention found 46 additional existing member paths, all changed:
30 in `motion/wres_all.viv`, ten in `assets/ai/ai.viv`, three in
`screens/screens.viv`, and one each in `assets/nis.viv`, `assets/v2ip.viv` and
`motion/blazin.viv`. Another 1,832 paths did not match a loose file or a member
under that convention. Many are deliberately new assets; this is **not** a list
of missing dependencies. This comparison did not recursively decode every
nested archive or prove that every asset is requested.

The SOD has the same observed version (2), schema fingerprint (`86f322ac`),
schema offset (24), and data offset (3,144), but its string-table offset grows
from 189,932 to 266,640. This is compatible with expansion of an existing
database format. It does not by itself establish record semantics or counts.

The moveset stream has an exact, independently parsed change: **141 → 177**
`WPAR` chunks and **141 → 177** `WWAZ` chunks. The other chunk tags are `WAZA`,
`FZUI`, and `NAME`, two of each in both versions. This is a concrete capacity
requirement, not just an assumption from the reference source.

## What the reference runtime contributes

Reference source links below are evidence of accommodations; they are not code
to transplant. Recorded failures and measurements in its comments remain claims
by that project unless independently established here.

| Requirement | Reference evidence | Implication for our implementation |
|---|---|---|
| Loose assets can override archive-member requests | [asset-open adaptation](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L3342), plus inspected toolkit `src/kernel/kernel_path.c` | Requests such as `archive\|member` need an explicit route to the replacement. Merely putting files under `mods/` does not establish this. |
| Donor and voice mappings | [startup mapping](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/main.c#L751), [table growth](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1008) | Parse declarative mappings, validate donors/voices and expand the tables read by the game. IDs through 177 cannot assume stock backing storage. |
| Expanded move index | [WPAR/WWAZ accommodation](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1056) | Audit every reader of the stock 141-row table; use validated runtime storage. |
| Additional Blazin moves | [extended list and dispatch](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1451), `outils/patch_gen.py` | Names, pair direction, event tags and move dispatch need to agree, beyond just loading the animation files. |
| Per-fighter Blazin activation | [activation selection](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1111) | Match the activating participant, not a request cached for player 1; handle different cinematic plan structures and repeated sound triggers. |
| Custom entry/victory | [donor handling](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1427) | The stock hero-ID rule must not misclassify newly allocated fighter cores. |
| More selection-movie shape indices | [APT accommodation](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L1368) | Validate numeric shape indices and table sizes. A larger temporary table alone is not a general unbounded UI solution. |
| Unlock/profile capacity | [profile handling](https://github.com/comoria08/defjam_recomp/blob/aca317a0a84dd6522dd68f02ef7a5e82fb749989/src/recomp_manual.c#L927) | Keep added roster availability outside the retail unlock array; independently establish its capacity. Do not copy a save-tail repair based on another project's samples. |

Reference comments identify `assets/djv2.sod` as the combat-fighter source, rather
than `fighter.xml`. The supplied mod replaces SOD and contains **no fighter.xml**.
This strongly directs our next decoder/trace work toward SOD; it is not proof
that fighter.xml is irrelevant in every game subsystem.

The reference project also changes generated-source consumers using
`outils/patch_gen.py`. Our implementation should use maintained game hooks or
supported lifter facilities with fixture coverage; editing generated C after
every lift is a fragile integration boundary. The current reference's numeric
capacities (256 cores, 512 Blazin list entries, 4,096 temporary APT slots) are
implementation choices, not a universal fighter-mod specification.

## Independently checked stock guest behavior

Read from our v0.13 generated C in the release test lane; those files remain
local, untracked game-derived output. Addresses below are **guest addresses**.

- `sub_001A47B0`: initialization walks `0x3B8648` to exclusive `0x3B8F18` by
  16 bytes: exactly **141 rows**. `recomp_0012.c:23352–23470`; called by
  `sub_001A4A30` at guest `0x001A4DF6`. This independently corroborates the
  moveset capacity problem exposed by the archive's 177 pairs.
- `sub_0003E170`: voice-table access is `0x2DC5D0 + index * 12`, with reads at
  row offsets 0, 4, 5 and 6 (`recomp_0001.c:66925–66943`, `67418–67424`).
  No upper bound for that index was established. The reference's **104-entry**
  stock voice capacity still requires independent allocation/data-range proof.
- `sub_001813E0` passes a **512-dword** caller table to `sub_0017F080`
  (`recomp_0011.c:61521–61525`). The callee clears that count but later stores
  by an index without a local comparison against it (`55467–55509`). This is
  an index-safety concern. Full APT semantics and actual mod indices still need
  to be decoded/traced independently.
- `sub_00016810` and `sub_00017000` are sorted four-byte insertion/search
  helpers (`recomp_0000.c:16338–16388`, `18097–18155`), with no capacity check
  in insertion. Their callers include `sub_000158F0` and `sub_00015B80`.
  **80 profile slots** and the reference's save-repair layout have not been
  established from our own allocation/save paths. Treat them as research leads.

## Foundations already in our project

[Mod management](../mod-manager.md) already supplies signed catalogue metadata,
capability gates, bounded package validation, transactional install/rollback,
receipts and a lifetime game lock. Reuse these rather than making a second
installer or allowing packs to modify the extracted dump.

`src/hooks/pc_language.c` implements source/result-hashed deltas, nested BIG
member replacement, RefPack handling and cache rebuilding. Its target parser
(`:428–439`) and builder (`:617–721`) operate on existing members; a missing
entry errors (`:712–716`). The pinned toolkit's `g_xbox_game_file_redirect`
serves rebuilt files through the game-volume path layer. This provides a strong
existing integration point for a common data overlay, including on POSIX.

That language API does **not** register new fighter records, append missing
archive members, stack several data packs, or resolve fighter IDs. The
`setup/mods.py` extension allowlist excludes this package's asset formats; a
legacy `.mod` is not currently an accepted texture/language package.

The launcher (`src/hooks/pc_ui.cpp`) special-cases language selection; the
ordinary load-order UI is texture-oriented. Catalogue `class` means
linked/original content, not gameplay category. Introduce an explicit versioned
category contract (or a capability-derived projection with equivalent strict
validation), rather than overloading that field. Display **Fighters**, retain
the existing Textures/Languages behavior, show unmet requirements/conflicts and
require restart for changes to gameplay data.

## Current architecture and capacity follow-up

See the [revised plan](../fighter-mod-support.md) for the semantic registry,
resolver, engine adapters, save policy options, package composition and UI choices.
The [capacity audit](fighter-mod-capacity-2026-11-01.md) finds byte-width selection
and 32-bit runtime index paths. A universal 255-fighter limit and the cost of
exceeding it remain unproved. Do not inherit the reference's 256-core allocation
as the feature's public limit.

No converted archive has been produced: the standard package contract and engine
support must be defined and reviewed first. The verified extracted input remains
local evidence for eventual conversion through the ordinary toolchain.

## Decisions and hand-off

- D-new: user names the feature Fighter Mod Support and assigns v0.15.0.
- D-new: preserve reference-code independence; use the supplied assets and
  independently checked game behavior to implement our own runtime support.
- D-new: owner supersedes the compatibility-bundle proposal. Build the general
  maintainable system first; one- and multi-fighter packs use the same contract.
- D-new: assess capacity beyond 255 without assuming a global native-ID ceiling;
  review expansion versus virtual bindings after the identity/persistence audit.
- D-new: owner accepts D1's audit-driven capacity strategy and D2's hybrid
  integration, to be refined through tests; D3 extends existing profiles if safe,
  otherwise isolated mod-enabled profiles. The fallback is authorized.
- D-new: owner chooses D5 whole-pack activation and D6 native selection menus.
  Evaluate custom entries after retail or a per-player native custom-roster page;
  preserve other players' browsing/selection/readiness and all menu variants.
  D4 conflict policy remains under review; examples are in the revised plan.

Validation for this local research iteration:

- Input inspection streamed and checked CRC/SHA-256 for 1,883 files; the separate
  unpacked copy matched all 1,883 recorded hashes. Both mapping files parse as 46
  entries and all declared activation/ending archives are present.
- Seventeen synthetic inspector cases passed within the unit suite, covering
  unsafe/colliding paths, links, encryption/expansion limits, malformed mappings,
  chunk bounds, SODB header bounds, CRC corruption and baseline hashing.
- `python -m pytest -q tests/unit -m "not slow"`: **628 passed, 165 skipped,
  one deselected**; `logs/fighter-mod-research/unit-local-results.txt`. The toolkit
  was initialized at the exact pin from an existing local checkout. Skips reflect
  unavailable fixture/build/platform dependencies in this research lane; this
  does not replace the released build's wider validation.
- The initial sandbox run had five environment failures (one missing toolkit
  header and four denied Windows junction operations). Initializing the local
  toolkit and rerunning with junction permissions resolved those failures.
- No game run, runtime build, save mutation or gameplay acceptance claimed.

The requested v0.15.0 GitHub milestone was created before the owner changed the
publication instruction. No research branch or PR was pushed/opened. Keep all
further R&D local until asked to publish.

Next: clarify D4 with the owner; D1/D2/D3/D5/D6 direction is accepted. Native UI
presentation and capacity details still need investigation/prototypes.
Keep R&D local. Later runtime work requires quick/area-specific checks followed
by platform release gates; metadata integrity is not gameplay acceptance.
