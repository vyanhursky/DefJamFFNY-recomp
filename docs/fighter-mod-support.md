# Fighter Mod Support

**Planned for v0.15.0; not implemented or available in released builds.**
The launcher category will be **Fighters**, alongside Texture and Language mods.
The initial compatibility target is the owner's `Def Jam Vendetta.mod` package.
See the [investigation](research/fighter-mod-support-2026-11-01.md) for measured
archive contents, game limits and reference-source evidence.

## What the feature should support

- Add a fighter without replacing a retail fighter, with its own model,
  textures, portraits, AI, donor moveset or authored animations, voice, entry,
  victory and optional special-move cinematic.
- Explicitly replace selected fighter components when that is the author's intent.
- Install, enable, disable, remove and roll back through the existing mod manager.
- Explain missing runtime capabilities, duplicate fighter IDs and data conflicts
  before launch. Installation alone never enables a pack.
- Preserve retail profiles and make modded save dependencies recoverable.

## Package contract to develop

This is a design checklist, **not an accepted file schema or working example**.
Freeze a versioned schema only after a one-fighter spike proves the whole path.

| Declaration | Purpose |
|---|---|
| Package identity, version, authors and provenance | Stable receipts, updates and attribution |
| Category `fighters` and minimum runtime/capabilities | Show it in Fighters; refuse unsupported builds |
| Stable `pack-id/fighter-id` keys | Identity independent of model numbers and load order |
| Add versus replace operation | Preserve the retail roster by default |
| Model, textures, portrait and selection label | Match and selection representation |
| Moveset/core source, AI and bounded stats | Define actual behavior independently of appearance |
| Voice banks and animation-event bindings | Route the correct participant's speech and effects |
| Entry, victory, special moves and activation sequence | Avoid player-1/shared-cinematic assumptions |
| Exact target records/assets, source/result hashes where applicable | Validate baseline and deterministic composition |
| Dependencies and conflicts | Reject incompatible gameplay edits before launch |
| Save/roster schema and content fingerprint | Detect missing or changed fighter definitions |

Runtime capabilities should be granular internally (data overlay, registration,
extended move tables, cinematic features). Advertise a public `fighters-v1`
only when its promised behavior and acceptance tests exist. Legacy imports may
require a separate capability/profile; they must not masquerade as ordinary
fully composable packs.

## Proposed authoring workflow

1. **Start with a donor-based fighter.** Pick a known supported retail skeleton
   and moveset. Assign a stable package/fighter key. Supply replacement model,
   textures and portraits, with explicit donor/voice/AI choices. A full custom
   moveset should be a later authoring tier.
2. **Validate the asset formats.** Check skeleton/joint ordering, vertex weights,
   model/material references, texture layouts, animation timing and events.
   Console-source assets may need conversion; unzipping another game's assets
   is not a conversion pipeline. This Vendetta pack already contains target
   format assets, but the original conversion toolchain was not established as
   a public reusable dependency in this investigation.
3. **Author isolated records.** Provide typed fighter and dependency declarations,
   not hand-edited complete copies of `djv2.sod`, `main_all.dat`, animation tags
   or selection movies. An assembler should merge additions against the player's
   verified dump and generate the necessary runtime data.
4. **Preview before packaging.** Check model/skeleton/texture binding and each
   animation, then selection navigation/portraits and a real fight. Record the
   runtime version and donor/assets used. Preview tools and converters should
   live in the modding-tools project; engine integration belongs in this repo.
5. **Build and lint.** Resolve logical IDs to bounded engine slots, check archive
   references, enforce per-table budgets and create a reproducible package with
   hashes and conflicts. Runtime storage limits are explicit errors.
6. **Test lifecycle and composition.** Run the fighter against retail and custom
   opponents, with four participants, repeated matches and each enabled language.
   Test install/disable/re-enable/update/remove with disposable saves and verify
   retail save bytes remain unchanged.
7. **Distribute through the existing manager/catalogue path.** Keep game assets
   out of this source repository. Catalogue `linked`/`original` describes content
   provenance, not the Fighters category. Catalogue publication remains a
   separate reviewed operation.

There is currently no supported “export fighter mod” command or general-purpose
fighter converter in this project. The workflow above defines the toolchain to
build and document, rather than asking creators to depend on undocumented manual
patches in generated game code.

## v0.15.0 implementation and acceptance checklist

### A. Prove one added fighter end to end

- [ ] Decode enough SOD structure to identify a fighter and its key references;
  compare the supplied SOD with the owner's original. Prove which subsystems
  still use `fighter.xml` and which use SOD.
- [ ] Independently establish core/voice/selection/unlock storage bounds and all
  relevant readers. Reserve retail/Story IDs; implement bounded extension.
- [ ] Extend the data overlay for added assets and existing member replacements;
  prove nested archive behavior and POSIX/case handling.
- [ ] Register one new logical fighter, select it and complete a match; verify
  no retail fighter or hero style is replaced unintentionally.
- [ ] Verify direct and indirect lifted callers reach accommodations, and ensure
  regeneration preserves them. No post-lift text-patching requirement.

### B. Make the supplied Vendetta pack compatible

- [ ] Define the initial legacy import manifest/profile and recognize the audited
  input hash; unknown revisions require new inspection.
- [ ] Convert its 46 core/activation mappings with validated targets and resolve
  the advertised-44 versus observed-46 roster discrepancy.
- [ ] Support its 177 WPAR/WWAZ pairs, donor voices, extended Blazin list and event
  bindings, per-participant activation, entries and victories.
- [ ] Validate selection movie indices, all relevant fighter-count limits and
  multi-player navigation; retain custom-fighter/hero UI behavior.
- [ ] Keep added unlock availability outside unsafe retail storage; establish
  save layout from our own evidence. Isolate modded profiles initially.
- [ ] Run all mapped fighters through asset loading and intro/fight/victory;
  cover special/activation variants for player 1, player 2 and CPU, including
  mixed retail/custom and four-fighter matches. Check speech by listening.
- [ ] Run repeat matches and a soak, measure load time/memory and reject dangling
  references, buffer growth, crashes, wrong-owner cinematics or lost save data.

### C. Integrate the launcher and authoring contract

- [ ] Add Fighters to installed/catalogue filtering and pack metadata, capability
  gates, settings projection, persistence and restart messaging across platforms.
- [ ] Support transactional import/rollback/removal and immutable runtime caches.
  Reject duplicate IDs, undeclared record conflicts and unsafe asset paths.
- [ ] Retain texture priority behavior and language single-selection. Either prove
  language/fighter shared-data composition or show a precise conflict reason.
- [ ] Freeze the native declarative schema, provide a minimal non-game-data
  example and converter/validator documentation in the modding-tools project.
- [ ] Verify disable/remove/re-enable, missing-package saves and rollback with
  disposable fixtures; never overwrite an incompatible save.
- [ ] Run unit/native fixtures plus quick/targeted game checks for implementation
  PRs, and the Windows/macOS/Linux release-candidate gates and owner play-test.

Completing an inspection or repackaging the ZIP does not complete these gates.
