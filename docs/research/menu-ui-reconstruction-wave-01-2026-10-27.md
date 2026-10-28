# UI reconstruction: first production wave and corrected masters — 2026-10-27

The owner approved expanding the twelve-family direction, then corrected two
native pilot samples: Main Menu v5 was too heavy, especially M/N/A and the A
counter; dark Capone v2 had an added outer edge/depth lining. Startup Continue v3
was accepted in-game and stays byte-identical. Earlier browser approvals remain
historical checkpoints; they do not override this native feedback.

The next review is `http://127.0.0.1:51742/next-review/review.html`.
It covers **25 additional source mappings plus two corrected masters**. The owner
asked to finish this set overnight for review tomorrow. This is a local review,
not a release or publication approval. Published pack 1.2 and catalogue revision 5
remain unchanged.

## Revised masters

Main Menu v6 uses the visible original lettering as its sole geometry authority.
The prompt explicitly preserves thin M/N stems, the open triangular A counter,
flat ivory faces, angular cuts and the source interruptions in E/U. It forbids
the prior new serif feet, perimeter keyline, bevel and extrusion. Dark Capone v3
uses the original for flat geometry and the prior remaster only for restrained
face wear; it explicitly removes continuous light borders, double contours and
depth. Both are generated anew with the built-in image tool. No alpha erosion,
font substitution or procedural artistic sharpening is used.

The separate pilot02 copies the published standalone pack. It changes the two
masters and retains the accepted Continue PNG exactly. Its three replacement
atlases preserve the published footprints within one replacement pixel at
alpha128; **1,523 other non-metadata files and every wide entry remain exact**.
Raw artwork, measured transforms, output hashes and native receipts remain local.

## Expansion wave

The 25 mappings cover Loading, Artist, Song Title, Autosave Warning, Select,
One on One, Pick Your Rules, Standard Rules, No Holds Barred/Anything Goes,
Select Number of Fighters, a separate menu Continue, Music, Announcer, Sound
Effects, Vibration, Difficulty, Delete User ID, Accept Changes, Easy, Med, Hard,
Off, On, Autosave and Cancel. Light, dark and disabled source appearances are
kept separate; a filename or shared word is not evidence of interchangeable art.

The initial nearest-neighbour source composites caused several first drafts to
copy pixel stairs or invent polygonal outlines. Those attempts are retained as
held evidence. Revised requests use a smooth source composite plus the accepted
Continue master **only as an edge-quality reference**. The original still controls
wording, geometry, spacing, weight, colour and state. A two-label retry was
inspected before applying that prompt correction to the rest of the wave.

Every raw result is immutable. Review exports use the existing modding tool's
RGB bleed from alpha>16 into lower-coverage texels, then restore every original
alpha byte. RGB above alpha16 stays exact. This is low-coverage colour sanitation,
not a general de-matting pass or permission to remove intentional green art.
Original/published/draft panels share scale and backdrop, with raw proportions,
outer-bound fitting and original ghost controls. Fitting outer bounds does not
establish per-glyph identity or game-wide approval.


## Validation and review limits

The corrected native pilot completed as `logs/run-20261027-215145.log.err`:
nine 2560×1440 captures, Main Menu v6 and actual dark Capone v3 visible, zero
measured crashes/watchdogs/unresolved calls/debug-layer/truncated-batch faults,
and complete save-root restoration byte-for-byte. Presentation reports have a
median 120 presents per two-second interval (min98/max121). Main Menu and Continue
load traces and Capone upload trace are present. Ten inherited optional omissions
remain. Triage is UNEXPLAINED due to known diagnostic lines; its first pointer was
read in context and confirms the NtFsControlFile(0x90020) stub. No game code changed.

The 25 new labels are browser studies and are not installed in that pilot.
All 27 selected exports independently preserve alpha and RGB above alpha16;
each has zero green-dominant visible or hidden pixels under the recorded test.
All 27 page selections load, with no page-level overflow; all three native pairs
load 2560×1440 images. Scale, raw-proportion and original-ghost controls work.

There are **56 successful built-in generations**: 25 first drafts, 25 smooth-edge
retries, four proportion trials and the two corrected masters. The selected wave
uses v2 throughout. The four v3 trials did not improve proportions and stay held.
At matched width, selected raw height differs from -22.27% to +30.83%; the page
exposes this and can disable fitting. This remains a material review limitation,
not a claim of source-exact glyph geometry. Full literal prompts, input/output
hashes, export checks, native receipt and capture pins are in
[`config/menu-ui-reconstruction-wave-01-2026-10-27.json`](../../config/menu-ui-reconstruction-wave-01-2026-10-27.json).

A separate release regression was using the game. One process was stopped under
the earlier game-shutdown authorization before its harness parent was identified;
the other suite was then left alone. Our native run waited until serial preflight
was clear. The earlier interrupted external run is not counted as our validation.

## Continuation

Review the new set and the corrected native masters before accepting these
particular drafts. The previously approved family direction remains in force.
Remaining tiled wordmarks, glyph pages, accents/languages, layout variants and
retained-art fringe cases still need their planned calibration and native checks.
The baseline remains 1,348 mappings. No game or toolkit code changes are included.
Future PRs target milestone v0.12.2; no push is requested for this checkpoint.
