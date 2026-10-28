# UI reconstruction: native pilot and first family batch — 2026-10-27

**Later owner feedback:** the twelve-family direction is approved for expansion.
Native Main Menu v5 needs thinner strokes/open A; dark Capone v2 needs its added
rim/depth removed; startup Continue v3 is good. See the [next wave and corrected
masters](menu-ui-reconstruction-wave-01-2026-10-27.md). The pending statements
below describe this earlier checkpoint, not the latest acceptance state.

The owner approved the [production plan](menu-ui-reconstruction-plan-2026-10-27.md)
and added green-edge cleanup from [issue #142](https://github.com/vyanhursky/DefJamFFNY-recomp/issues/142).
Main Menu v5, Continue v3 and dark Capone v2 establish the accepted sample direction.
They are now assembled and captured in-game. Twelve additional family drafts
await review at `http://127.0.0.1:51742/review/review.html#capone-loading`.
The **Native pilot** tab provides actual 2560×1440 before/after pairs. Published
1.2 and catalogue revision 5 are unchanged; this is not a release candidate.

## Scope correction and inventory

The previous 1,140-mapping ledger omitted the separate light loading-name family
`screens/match/3_fighters/l_ML_*`. It is distinct from dark select names in
`screens/portrait/l_CF_*`; it must not be inferred by recolouring select art.
The current corpus yields **208 additional source IDs across 222 resource aliases**.
All 208 images were inspected in five contact sheets and confirmed as lettering,
including alternate logos/names and 2/3/4-fighter variants. That does not establish
native visibility of every historical variant. The revised baseline is **1,348
text mappings**. The old 1,140-input hashes were independently checked against
the preserved private checkpoint before inventory construction.

Only three pairs of the earlier mappings have byte-identical tightly cropped
RGBA artwork: 1,137 exact crop groups for 1,140 mappings. More reuse may be possible
across confirmed layout variants, but matching words or filenames is insufficient.
The production manifest records aliases, source/published hashes, original sizes,
bounds, source group, OCR-label status, exact crop identity and unverified contexts.
It is a coverage ledger, not a claim that 1,348 generation calls are required.

## Native integration

Three immutable accepted masters are placed into the existing full replacement
atlases: Main Menu 2048×256, Continue 512×128 and dark Capone 2048×256. Alpha>=128
bounds match the published footprints exactly for Continue/Capone and within one
replacement pixel for Main Menu. Guard/soft-edge transforms are recorded. This
fits outer bounds, not each glyph individually. No alpha thresholding is applied.

The isolated pilot copies the standalone published pack and changes three PNGs
plus metadata. **1,523 other non-metadata files** and all wide-manifest entries
remain exact. Existing tool RGB bleed fills alpha-zero texels; alpha and visible
RGB remain exact relative to the assembled candidate. No loader, sampler, toolkit
or game code changes were made. This native pilot does not include the later
alpha<=16 colour-bleed previews used by the new family review.

| Native evidence | Log | Result |
|---|---|---|
| Published comparison, Main Menu/select route | `run-20261027-202034.log.err` | 8 captures, save restored; Capone not reached in this sweep |
| Pilot comparison, same sweep | `run-20261027-202222.log.err` | 8 captures; Main Menu visible, candidate IDs loaded |
| Pilot, calibrated Capone route | `run-20261027-203041.log.err` | 9 captures; actual Capone banner at 24.5s |
| No replacement packs, heading check | `run-20261027-203237.log.err` | 9 captures; inherited heading mismatch reproduces |
| Pilot Continue, autosave notice | `run-20261027-203446.log.err` | Continue captured at 18.5s |
| Published Continue, same notice | `run-20261027-203522.log.err` | Matched before capture |
| Published calibrated Capone route | `run-20261027-205346.log.err` | Matched Capone before capture at 24.5s |

Completed comparison runs report zero measured crashes/watchdogs/unresolved
calls/debug-layer/truncated-batch faults, around 120 presents per two-second
interval, and complete save-root restoration byte-for-byte. The ten inherited
optional omissions remain. Triage is UNEXPLAINED due to known diagnostic lines;
bounded inspection of its first pointer confirms NtFsControlFile(0x90020), not
an assertion that the log contains no diagnostics. Captures and source/load
traces establish technical integration. Native visual judgment is pending:
Main Menu's reconstructed weight/material still differs, and the page presents
that result rather than claiming source-exact lettering.

Two additional probes are preserved as incomplete evidence: `run-20261027-201823.log.err`
reaches selection but the screenshot queue waits on an optional User ID screen
that this fixture skips; `run-20261027-202546.log.err` stops progressing through
user setup, still presenting normally, with no chooseF2 anchor. The capture
schedule was corrected and explicit save-confirmation presses calibrated. Neither
is counted as passed scope. All nine run receipts verify save restoration.
The owner's pre-existing game was stopped only after explicit authorization.

**Separate inherited visual finding:** the select heading reads SELECT USER ID
in published, pilot and no-pack runs. Its cause remains unassigned. It is not
introduced by the reconstruction; no runtime fix is included or inferred.

## Green-edge evidence and bounded cleanup

The published pack scan covers all **1,526 PNGs**. It flags **604** with near-pure
green hidden texels and **813** with green-dominant edge texels. Hidden near-pure
green means R/B<=8 and G>=247 at alpha0. Green dominance means G-R>40 and G-B>40;
an edge is visible alpha next to alpha0 in a four-neighbour test. These counts
are inspection candidates, not confirmed defects in every image. Intentional
green art, translucent materials and runtime tint must be distinguished.

The generation prompts explicitly exclude green matte contamination from the
colour/wear preservation constraints and prohibit coloured fringes. Raw outputs
still contain a few coloured low-alpha residues. The family export previews use
the existing tool's colour bleed, with alpha>16 as the reliable colour source,
then restore the complete original alpha channel. Independently checked:

- Every alpha byte remains exact, including antialias coverage.
- RGB at alpha>16 remains exact.
- All twelve preview exports have **zero green-dominant nonzero-alpha texels**
  under the recorded criterion, and zero hidden green-dominant texels.
- Every raw generation remains unchanged and pinned separately.

This is RGB sanitation at very low coverage, not artistic sharpening, hardening
alpha or global green desaturation. It is not a general de-matting algorithm for
the retained original/remastered artwork. Visible-edge contamination there still
needs per-source confirmation and comparisons. New export previews also need
native validation after family selection before entering a package.

## First family review

| Family | Drafts |
|---|---|
| Serif/stencil headings | Options, Choose Venue, Choose Teams, Select User ID, Choose Match Type |
| Small labels | Back v2, Select v2 |
| Dark select wordmarks | Method Man as Blaze, N.O.R.E. |
| Light loading wordmarks | Capone, N.O.R.E., Method Man as Blaze |

Fourteen built-in imagegen calls produce twelve selected-for-review assets and
two held trials. Back v1/Select v1 invented heavy distressed lettering; neither
is selected. Their retries use original visible composites on grey, plus the
accepted Continue quality reference, to separate true letter shapes from
transparent-RGB ghosts. Dark handwritten references are composited on pale paper;
outputs remain genuinely transparent. Original wording/design controls identity.
All literal prompts, actual input-image hashes, raw/output hashes and dimensions
are in `config/menu-ui-reconstruction-pilot-2026-10-27.json`.

Raw height at matched width varies from -9.4% to +11.32%; the page exposes these
measurements and a raw-proportion switch. Matching the outer rectangle is not a
per-letter identity guarantee. Compare shapes, spacing, weight and palette too.
Original / published-or-original-fallback / candidate panels share the same
context and scale, with 1×/3×/6×, ghost and bounds controls. Whole images are drawn
with their antialias margins, avoiding opaque-bounds clipping. Loading names
are labelled as original fallbacks, because 1.2 did not replace this family.

Browser verification covers all twelve selections, correct context defaults,
canvas dimensions, scale/ghost/bounds controls and all three native pairs, plus
full-frame images at 2560×1440. No browser errors or horizontal page overflow.
The new reader leaves the older 51741/51740/51739/8768 sessions unchanged.

## Decisions and next steps

- D-new: owner-approved plan proceeds; sample direction is accepted, while the
  first family batch/native result remains a review checkpoint before broad waves.
- D-new: add the separate l_ML family explicitly; correct the scope to 1,348 rather
  than implying that the old 214 dark-banner mappings covered loading names.
- D-new: preserve alpha and meaningful RGB during low-coverage edge sanitation;
  keep intentional green art and retained-art de-matting out of a global filter.
- D-new: retain failed font trials; use visible reference composites and one
  targeted retry rather than accepting the wrong alphabet/weight.

Await family/native feedback, then extend calibrated families. Tiled wordmarks,
shared glyph pages, language-specific examples and the broader green-edge audit
still need their own checks. Complete per-mapping/native coverage and installer/
rollback validation before a new package. This checkpoint contains no source
push, PR, game build, full regression, public artwork upload or catalogue update.
Any future source PR uses milestone v0.12.2.
