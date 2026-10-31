# Menu/UI modpack implementation handover

**Combined 1.4.0 ready for upload approval — 2026-10-31:** [Candidate report](research/menu-ui-v1.4-candidate-2026-10-31.md), source `config/menu-ui-v1.4-candidate-2026-10-31.json`, final approval `config/menu-ui-held-final-approval-2026-10-30.json`. **All 1,343 approved mappings combined (390 inherited / 953 new); five accepted baselines retained.** ZIP **601,895,156 bytes**, unpacked **605,772,797 bytes**, SHA-256 `f3d79f86a024b5786919ef2d6f38b1f599cb49a151d031b4a85023a5f480848d`. Private `logs/menu-ui-v1.4/publication/`; exact ZIP passed unchanged 0.12.1 installer. 963 source-shaped native exports, 193 common-master joins exact, 95 glyphs registered, original gray marks protected; all 1,744 PNGs lossless RGBA/metadata verified. Six serial native routes pass with byte-identical saves; captures/limits in `native-validation.json`. Story uses private pinned mac-profiles fixture and explicit third-down to select VY2; fresh-profile misses preserved separately. Tools PR1 and draft catalogue PR9 are green, milestone v0.12.2; source PR152 records this candidate. **Do not upload, merge catalogue or sign/publish until owner approves this exact final size/hash.** Current verified signed revision 8; local 9 preview unsigned. Refetch live revision at actual publication. No game reinstall/update required beyond 0.12.1. Independent recovery `config/menu-ui-v1.4-checkpoint-2026-10-31.json`; older counts below are historical.


**Four held corrections and lossless experiment — 2026-10-30:** [Four-draft review](http://127.0.0.1:51764/review.html#overview), [report](research/menu-ui-held-fixes-lossless-2026-10-30.md). Source records: `config/menu-ui-held-corrections-2026-10-30.json`, `config/menu-ui-lossless-experiment-2026-10-30.json`, `config/menu-ui-held-rest-approval-2026-10-30.json`. **1,339 accepted (390 published / 949 queued), four new corrections pending, five baseline-only retentions.** Six built-in imagegen calls: four selected for review, two superseded. GAGNANT excludes the detached white atlas corner; NO USER IDs restores transparent space and muted red; venue badges reference the sampled 35×34 artwork. Native UV/alpha/gutter and approved-context reconciliation remain due. Private workspace `logs/menu-ui-held-fixes-20261030/`; restart with `python3 -m http.server 51764 --bind 127.0.0.1 --directory logs/menu-ui-held-fixes-20261030`. Full lossless experiment: 1,704 published PNGs saved 109,305,758 bytes (16.01%); 949 approved crops saved 73,516,511 bytes (11.35%). All decoded RGBA, including hidden RGB, and non-IDAT metadata exact. ZIP payload saving: 108,045,093 bytes (15.90%), a projection only. Oxipng 10.2.1 installed; copy-only `defjam-tools optimize-png` and [procedure](/Users/vlad/Code/DefJam-Modding-Tools/docs/lossless-png.md) implemented; 83 tests / 12 subtests pass. **Current profile supersedes the earlier `--strip safe` recommendation:** no stripping, `--nx`, interlace kept, no `--alpha`. Four raw-master optimization attempts were rejected for metadata changes; originals retained exactly. Published 1.3/catalogue 7 unchanged; no installation, upload, push or game run. Recovery: `config/menu-ui-held-fixes-checkpoint-2026-10-30.json`, chained to prior held review. Future PR milestone: v0.12.2. Earlier counts below are historical.


**Held 20 review and compression research — 2026-10-30:** [Focused held review](http://127.0.0.1:51763/held-review.html#overview), [report](research/menu-ui-held-review-compression-2026-10-30.md), ledger `config/menu-ui-held-review-compression-2026-10-30.json`. Fifteen technical holds show existing generated revisions; five earlier tool blocks show baseline only. None newly approved/generated. **1,328 accepted / 20 held unchanged.** Viewer is additive `logs/menu-ui-wave15-20261030/held-review.html` + `held-review-data.json`, served by `python3 -m http.server 51763 --bind 127.0.0.1 --directory logs/menu-ui-wave15-20261030`. QA/proof/research/benchmark in `logs/menu-ui-held-review-20261030/`. 36-image in-memory Pillow lossless test saved 3.51–5.59% by category, exact RGBA including hidden RGB; combined stratified sample 4.74%, not a full-pack forecast. ZIP level 1→9 alone saved 0.0303% on those encoded files. Existing exports use normal PNG compression and ZIP; dedicated final optimization is still a recommendation, not applied. Recommend final native assembly, then copy-only pinned oxipng `-o 4 --strip safe` without `--alpha`, decoded full RGBA/dimension/metadata equality and actual loader validation, then new immutable archive/catalogue hashes. PNG optimization does not reduce GPU texture memory. Published 1.3/catalogue 7 and all artwork remain unchanged; no optimizer installed. Future PR milestone v0.12.2.

**Final 123 approved — 2026-10-30:** Owner explicitly approved all 123 new mappings in the final 51762 review (83 complete artworks). Exact raw/crop/preview/master hashes were reverified and pinned in `config/menu-ui-wave15-approval-2026-10-30.json`. **1,328 accepted: 390 published in 1.3 and 938 queued. The remaining 20 retain published baselines and remain unrestored.** All 1,348 tracked mappings are accounted for. Current published 1.3 ZIP: **679,627,331 bytes**; uncompressed files: **683,803,577 bytes**. The 938 queued approved preview PNGs total **641,883,992 bytes**; this is artwork workspace size, not a final archive or installed size. Full native atlas/canvas assembly, approved-context reconciliation, guards/layers/sampling and serial native validation remain due. Source size receipt: `config/menu-ui-approved-size-2026-10-30.json`; private measured paths: `logs/menu-ui-final-approval-20261030/size-receipt.json`. Do not add the two byte totals as a release prediction: previews replace old assets and will be fitted to native canvases. Published 1.3/catalogue 7 remain unchanged. Next: approved native assembly and validation; resolve 15 technical holds, retain five earlier tool-blocked sources. Any future PR belongs to v0.12.2. Earlier pending statements below are historical.

**Final batch ready; batch fourteen approved — 2026-10-30:** [Review](http://127.0.0.1:51762/review.html#overview), [all 143 mappings](http://127.0.0.1:51762/pieces.html#overview), [report](research/menu-ui-reconstruction-wave-15-2026-10-30.md). **1,205 accepted** (390 published / 815 queued); **123 new mappings in 83 artworks await review; 20 retain existing baselines** (five earlier tool blocks, 15 technical holds). All 1,348 mappings are accounted for, but retained items remain unrestored. Batch fourteen approval pins: `config/menu-ui-wave14-approval-2026-10-30.json`. Current ledger: `config/menu-ui-reconstruction-wave-15-2026-10-30.json`; workspace: `logs/menu-ui-wave15-20261030/`. There are 111 literal built-in outputs, 98 complete source references and 29 unselected context pieces. Exact alpha/RGB/crop reconstruction and viewer checks passed; nine raw-edge findings require guard/source-clip reconciliation. No new native test, installation or publication. Published 1.3/catalogue 7 remain unchanged. Recovery is separately pinned and chained to batch fourteen. Next: owner review, exact approval records, approved native assembly and serial validation, then technical hold resolution. Future PR milestone: v0.12.2. Earlier pending statements below are historical.

**Batch fourteen ready; batch thirteen approved — 2026-10-30:** [49 complete artworks / 100 new mappings](http://127.0.0.1:51761/review.html#overview), [100 individual pieces](http://127.0.0.1:51761/pieces.html#overview), [report](research/menu-ui-reconstruction-wave-14-2026-10-30.md). Ledger: `config/menu-ui-reconstruction-wave-14-2026-10-30.json`. Exact 100 prior approvals and 50 shared masters: `config/menu-ui-wave13-approval-2026-10-30.json`. **1,105 accepted** (390 published / 715 queued), **100 new pending**, **143 still to restore or resolve** (124 unassigned / 19 held), 1,348 mappings total.

This batch uses 100 exact native originals and 49 complete assemblies from source UV/quad metadata: four single-material, 42 two-material and three four-material shapes. 56 parent built-in calls produced 49 selected masters and 7 superseded outputs, with no failed/unissued calls. WINDOW MATCH's white glass was restored; three masters received green-speck corrections. The 100 selected crops reassemble their raw masters exactly, coverage one. All 56 master and 113 piece export alpha/RGB>16 checks pass; no selected green or outer-border findings remain. Parent blue/pale 1×/up-to-3× review and OCR/browser receipts are private. Font shapes, spacing, material, shadows and registration remain approximate. Full native canvas/gutter/layer/sampling assembly is still due.

Recovery is separately pinned and chained to batch thirteen, using independent APFS clones; no older artwork was deleted. No native run, installation, publication or push; published 1.3/catalogue 7 remain unchanged. Next: owner review and exact approval pins, remaining 124/held 19, approved assembly and serial native checks. Future PR milestone: **v0.12.2**. Earlier pending statements below are historical.

**Batch thirteen ready; batch twelve fully approved — 2026-10-30:** [Joined review:50labels/100new texture mappings](http://127.0.0.1:51760/review.html#overview), [individual100pieces](http://127.0.0.1:51760/pieces.html#overview), [report](research/menu-ui-reconstruction-wave-13-2026-10-30.md), ledger `config/menu-ui-reconstruction-wave-13-2026-10-30.json`. Exact100prior approvals in `config/menu-ui-wave12-approval-2026-10-30.json`; **1005accepted** (390published/615queued), **100newpending**, **243still restore/resolve** (224unassigned/19held),1348mappings total. Most remaining words are fragmented:50actual two-material shapes were decoded from mainMenu/cmtype ELF relocations, UV matrices and contiguous quads.100native originals recovered anew/source IDs verified; original joins exact RGBA of sampled rectangles, coordinate rounding<0.04native pixel. Parent50parallel built-in calls/50literal raw masters, no failures/superseded/unissued.100candidate pieces are lossless slices of SAME master per pair; concat restores raw RGBA exactly. They are derived crops, not100independent outputs or final native canvases.50master+100crop alpha/RGB>16export checks passed; only low-alphaRGBbleed. Parent all50pairs blue/pale native1x/up to3x in17sheets; two read-only classifiers had wrong key/text claims rejected. OCR100inputs/98readings/9adjudicated flags; browser50joined+100piece cards/300canvases/450scale cases/26controls, no warnings/errors/overflow. No green findings; one faint master border alpha20with no alpha128ink, nativeguards due. Individual shapes, spacing, outlines, material/opacity/shadows and preview registration approximate. Previous100pins/accepted1005union/published1.3archive unchanged. Private `logs/menu-ui-wave13-20261030/`; recovery separately pinned/chained to batch12; independent APFS cp-c clones used after low-space full-copy guard, no deletion/hardlinks. No native/install/publish/push; published1.3/catalogue7immutable. Next owner50joined/100mapping approval, record100piece plus50sharedmaster hashes/provenance, exceptions/remaining families, then approved full-canvas/gutter/layer/sampling assembly and serial native checks. FuturePRmilestonev0.12.2. Earlier pending statements below are historical.

**Batch twelve ready; all previous 100 approved — 2026-10-29:** [Review 100 new drafts](http://127.0.0.1:51759/review.html#overview), [report](research/menu-ui-reconstruction-wave-12-2026-10-29.md), ledger `config/menu-ui-reconstruction-wave-12-2026-10-29.json`. Exact batch-eleven approvals in `config/menu-ui-wave11-approval-2026-10-29.json`; **905 accepted** (390 published / 515 queued), **100 new pending**, **343 still to restore/resolve** (324 unassigned / 19 held), 1348 mappings total. Parent parallel built-in calls and two read-only classifiers; exact source claims independently checked. 124 calls/PNGs, 100 selected, 24 superseded, no failures; 28 historical prepared prompts never issued. Native originals and faithful 6x references retained; six original placards decoded from archive, five selected. Placard face-only review bounds exclude stretched lower atlas gutters; full native PNG retained and native UV/gutter assembly required. Opaque white placeholder tiles keep small text/margins; question-mark v4 explicitly opaque. Preserve actual stencil gaps, muted ink, source-specific stubs, tiny THE branding and cropped stars. Parent inspected all 100 pairs on blue/pale at 1x/up to3x in 30 sheets. 100 source / 124 generation / 124 revision export checks passed, exact generated alpha/RGB>16; no near-pure neon-green findings. OCR 124 readings/21 adjudicated flags; browser 100 cards/200 canvases/300 scale cases/38 controls, no warnings/errors/overflow. Ten raw border findings (nine source cuts/rules, one opaque tile) require native placement review. Previous 100 approved pins and published 1.3 unchanged. Private `logs/menu-ui-wave12-20261029/`, additive recovery separately pinned and chained to batch eleven. No native/install/publish/push; published 1.3/catalogue7 immutable. Next owner review/exact-hash approvals, remaining families/held originals, approved assembly and serial native checks. Future PR milestone v0.12.2. Earlier pending statements below are historical.

**Batch eleven ready; stencil corrections approved — 2026-10-29:** [Review100new drafts](http://127.0.0.1:51758/review.html#overview), [report](research/menu-ui-reconstruction-wave-11-2026-10-29.md), ledger `config/menu-ui-reconstruction-wave-11-2026-10-29.json`. Exact3approvals at51757 in `config/menu-ui-fighting-style-cuts-approval-2026-10-29.json`; **805accepted** (390published1.3/415queued), **100newpending**, **443still to restore/resolve** (424unassigned/19held),1348mappingtotal. Parent parallel built-in calls;3bounded read-only classification/QA helpers only.160issuedcalls/159PNGs/100selected/59superseded/1outputblockheld,2historicalpreparedunissuedprompts. RINGOUTcard returned no image and was held without retry/bypass; SUBWAYMATCHfrom its own original replaces it. Parent inspected all100pairs in39blue/pale native1x/3xcontacts. Original6xLANCZOS references; source-specific original stencil gaps and mutedpalette preserved. **Do not reuse initial generic controller component list:** it invented connectors/arrows; selected refined requests retain only geometry actually present in each source and circular buttons. Stamp interiors transparent; localized shadows/material/opacity approximate. EXTRASoriginal clips S at right edge, not UV-complete wholeword.101nativeinputpins/159default-raw-requestrecords/100selected+159revisionexport alphaRGB>16checks verified; no pure neongreencontamination. OCR102/102readings,8flags visuallyadjudicated; browser100cards/200canvases/300detail-scale cases/29controls,0errors/overflow.6rawborderalpha>16exceptions (4strong,including source rules) retained for nativeguard/gutterchecks.3priorapprovalpins/805acceptedunion/immutable1.3archive verified. Private `logs/menu-ui-wave11-20261029/`; additive recovery separately pinned, chained to fighting-style-cuts checkpoint. No native/install/publish/push; published1.3/catalogue7unchanged. Next owner100review/exact-hashapprovals, remainingfamilies/heldoriginals, approvedassembly+serialnativechecks. FuturePRmilestonev0.12.2. Older pending statements below are historical.

**Three fighting-style gaps restored; other30approved — 2026-10-29:** [Focused review](http://127.0.0.1:51757/review.html#overview), [report](research/menu-ui-fighting-style-cuts-2026-10-29.md), ledger `config/menu-ui-fighting-style-cuts-2026-10-29.json`. Exact30approvals in `config/menu-ui-wave10-thirty-revisions-approval-2026-10-29.json`; **802accepted** (390published/412queued), **3newdrafts pending**,543still to restore/resolve (525unassigned/18held),1348totalmappings. SUBMISSIONSv5/WRESTLINGv5/KICKBOXINGv6 restore original source-specific Def Jam stencil gaps, including S top/bottom and U bottom. Earlier continuous-sans/no-stencil guidance for this family is superseded by explicit owner feedback: do not heal original cuts or invent uniform stripes.3builtin calls/3PNGs/zero failures,superseded,unissued; no subagent/API fallback. Parent HD and native1x/3xblue+pale comparisons;3source/previous/default/raw/exports and30approval pins verified, alpha/RGB>16 exact. OCR6/6wording; browser3cards/6canvases/9detail-scale cases/controls pass, no errors/overflow. Cut geometry, glyphs, weight/spacing and partial alpha still approximate; original ghost/raw proportions available. Private `logs/menu-ui-fighting-style-cuts-20261029/`; additive recovery separately pinned. Prior33review51756/published1.3/catalogue7 unchanged; no native/install/publish/push. Next owner review3, exact-hash approvals, remaining families/held originals and approved assembly with serial native checks. FuturePRmilestonev0.12.2.

**Batch-ten feedback handled — 2026-10-29:** [33 revised textures](http://127.0.0.1:51756/review.html#overview), [report](research/menu-ui-wave10-revisions-2026-10-29.md), ledger `config/menu-ui-wave10-revisions-2026-10-29.json`. **772 accepted** (390published +382queued), **33revisions pending**, **543still to restore/resolve** (525unassigned +18held), total1348mappings. Exact67unaffected approvals in `config/menu-ui-wave10-unaffected-approval-2026-10-29.json`; all23predominantly red assets excluded and revised. Numeral1/2/3 are transparent cutouts in black panels, not gray ink; source RGBA proves it. Full B right/down black connectors and X lower white line restored per explicit owner feedback, superseding earlier padding/core-only interpretation. Symbol70 reads DISTURBING THA / PEACE: parent found its matching larger original in 7th Heaven wordmark `vn_ML_28.xsh` resource2/source205483ab…, not a guessed venue-ID join. Evidence page linked in viewer. Thin fighting styles/MethodMan handwriting and subdued stat/DEV cream revised.39issuedbuiltin calls/39PNGs/33selected/6superseded/0failures;1separate unissued historical prompt. Parent owns art; bounded read-only helper claims validated against originals. Exact generated alpha/RGB>16 export contract; all33source/previous and39default/raw/request pins plus67approvals verified. OCR44inputs/32nonempty/12flags visually adjudicated; browser33cards/66canvases/99detail-scale cases plus changed final emblem12backdrop-scale checks, no errors/overflow. Review compares original/previous rejected/new, with full old history still51755. Private `logs/menu-ui-wave10-revisions-20261029/`; additive recovery pinned separately. No new native/install/publish/push; published1.3/catalogue7 unchanged. Next: owner review33, exact-hash approvals, remainingfamilies/heldoriginals, then approved assembly and serial native checks. Future PR milestonev0.12.2. Earlier gray-numeral/padding statements below are superseded.

**Batch ten ready; all batch-nine approvals recorded — 2026-10-29:** Review [100 new UI textures](http://127.0.0.1:51755/review.html#overview), [report](research/menu-ui-reconstruction-wave-10-2026-10-29.md), ledger `config/menu-ui-reconstruction-wave-10-2026-10-29.json`. **705 accepted** (390 published 1.3 + 315 queued), **100 new awaiting review**, **543 still to restore/resolve** (525 unassigned + 18 held), total 1,348 tracked mappings; not all are whole words. All 82 original candidates and nine final redos are explicitly approved under the two additive batch-nine approval records, recovery pinned separately. New batch: 104 assigned, 100 selected, four held (two output blocks; two earlier 4× baselines need originals); 143 built-in calls / 141 saved PNGs / two blocked outputs / zero unissued. Parent direct artwork calls, bounded read-only classification helper only. Corrected demo-source text pairings and original CARRIBBEAN spelling; seven grid-prone assets now use faithful LANCZOS 6× references. Use smooth faithful references for future edits, keeping nearest-grid views for inspection. Earlier wrong-text/pixel-grid/opaque-field attempts remain superseded. All 100 source/draft pairs inspected on blue/pale; 104 full inputs, 141 default/raw/request records, 139 revision exports verified. Generated alpha/RGB>16 retained; faint border sample max21/255, no alpha128 border ink; native gutters due. Browser 100 cards / 200 canvases / 300 detail-scale cases / 26 controls, zero errors/overflow. Final OCR 156 inputs / 128 nonempty readings / 35 flags visually adjudicated. Prior 705 approvals, batch-nine pins and published 1.3 unchanged. No native/install/publish/push. Private `logs/menu-ui-wave10-20261029/`; additive recovery pinned separately. Next: owner review 100 and exact-hash approvals; remaining families/held originals, then approved assembly and serial native checks. Future PR milestone v0.12.2. Historical pending statements below are superseded.

**Batch nine fully approved; batch ten started — 2026-10-29:** Owner explicitly approved the82untouched originals and then all9final redos. Exact selected hashes verified in `config/menu-ui-wave09-original-rest-approval-2026-10-29.json` and `config/menu-ui-wave09-nine-redos-approval-2026-10-29.json`; earlier10revision approvals remain pinned separately. **705 distinct accepted sources** (390published1.3 +315queued). Tracked1348mapping inventory leaves643not accepted:629unassigned +14held. These include fragments, glyph atlases, thumbnails and complete art, not643whole words. Batch10 reserves100new distinct sources from629: handwritten venue labels, symbols, stamps, fighting-style labels, user-ID prompts and other complete UI art; private `logs/menu-ui-wave10-20261029/`. Parent reviewed21source-contact sheets; readonly classifier findings required parent correction because several proposed keys were shifted or incomplete. Original composites control typography, weight, spacing, palette and alpha. New batch generation underway; no new artwork is approved, installed or published. Historical pending-approval statements below are superseded. Published1.3/catalogue7 remain immutable. FuturePRmilestonev0.12.2.

**Other10 approved; nine original-source redos ready — 2026-10-29:** Owner: “These9 still look off to me. The rest are good.” Approved10fromlast19review with exact pins `config/menu-ui-wave09-revisions-approval-2026-10-29.json`;614accepted. Separate82original-batch approval scope asked asynchronously, unanswered: do not infer approval. Nine candidates at `http://127.0.0.1:51754/review.html#overview`, [report](research/menu-ui-wave09-nine-redos-2026-10-29.md), ledger `config/menu-ui-wave09-nine-redos-2026-10-29.json`. Clean original6xgray/blue/pale composites replace drifted generated-font references and hidden-matte RGBA visual inputs.16actualbuiltin outputs/9selected/7superseded/0failures/9unissued preparations (25requests); parent direct, no subagents/API fallback. Fivewordmarks/GAGNANT edge refinements; READYguardv8 altered rim/lettering, superseded for closerv7. Selected W7/R7/G8,promo7all5,red6; unapproved and glyph/material/opacity/spacing still approximate. Parent9pairs+6edges+guard inspected; OCR20inputs/18final records,2false readings adjudicated. Browser27detail-scale cases/18overviewcanvases/11focused controls,0errors/overflow. All16exports preserve generated alpha/RGB>16; READYpartialedge spray max89/255 retained, no alpha128ink clipping, gutter/native validation due. Prior101batch9 and19revision raw/previews,614accepted and published1.3 unchanged. No native/install/publish/push. Private `logs/menu-ui-wave09-nine-redos-20261029/`, additive recovery pinned separately. Next: owner review9 +82scope clarification; exact hashes on approval, approved assembly/native checks. FuturePRmilestonev0.12.2.

**Four stencil revisions approved;19 batch9 corrections ready — 2026-10-29:** Owner: “Approve the 4 textures.” Exact STORY CHAMPSv3/BEATBOXv3/CRIBv4/MAPv5 pins in `config/menu-ui-stencil-approval-2026-10-29.json`;604 distinct accepted. No approval inferred for the remaining82 batch9drafts. Requested19 corrections ready at `http://127.0.0.1:51753/review.html#overview`, [report](research/menu-ui-wave09-revisions-2026-10-29.md), ledger `config/menu-ui-wave09-revisions-2026-10-29.json`. Thinner regular lettering, simplerB, quieter stamp lining, smaller promotional faces/shadow-margin restoration, mutedred. PromotionalEXTRAS/ONLINE distinct from thinEXTRAS/illustratedONLINE; promotionalBEATBOX distinct from approvedstencil.29successfulPNGs/19selected/10superseded;6parameter-validationfailures beforegeneration/15unissued/50requests; parent direct built-in calls, no subagents/API fallback. All19pairs +6finishing edits inspected, OCR38inputs/3false flags adjudicated. Browser57detail-scale cases/38overviewcanvases/19controls, no errors/overflow. Generated alpha/RGB>16 exact across29exports. Redwarning4faintborder samples max20/255 retained; no alpha128ink clipping, gutter validation due. Fullshadow alpha16 fitting explicit for5promotional words, alpha128others; glyph/weight/material/native-size differences qualified. Prior101batch9 raw/previews,604accepted and published1.3 unchanged. No native/install/publish/push. Private `logs/menu-ui-wave09-revisions-20261029/`; additive recovery separately pinned. Next: owner review19 and disposition82, then approved assembly/native checks. Future PRmilestonev0.12.2.

**Batch nine ready — 2026-10-29:** [report](research/menu-ui-reconstruction-wave-09-2026-10-29.md), pins `config/menu-ui-reconstruction-wave-09-2026-10-29.json`. Review `http://127.0.0.1:51752/review.html#overview`:101 new UI candidates,36dark/65light,17families;105assigned,4held (Bless no image; copyright tone; roles gray; PRET contour/edge). Parent direct built-in generation, one read-only classifier;121actual calls/120PNGs/1failure/42prepared-unissued requests,101selected/19superseded-or-held. Transparent result-field and accidental-footer corrections retained, with remaining glyph/weight/colour differences qualified. All104 first-pass pairs +15correction pairs +finalPRET inspected; OCR208initial/26correction inputs versioned/pinned. Browser101details/202overviewcanvases/24controlcases, no errors or document overflow. Exact generated alpha/RGB>16 export contract verified on101selected/113revision previews. Prior600accepted, four pending stencil corrections at51751, and published1.3 unchanged. No approval inferred from the promised review time; no native/install/publish/push. Private `logs/menu-ui-wave09-20261029/`, additive recovery pinned separately. Next: owner review101 and separate4; record explicit hashes before assembly/native validation.629unassigned mappings remain, not all whole-word text; held effect roles also remain. Future PR milestonev0.12.2.

**Batch8 selective approval and four stencil revisions — 2026-10-29:** Owner approved100 and rejected STORY CHAMPS,BEATBOX,CRIB,stencilMAP; source pins `config/menu-ui-reconstruction-wave08-approval-2026-10-29.json` (600 distinct accepted). PlainMAP remains approved; prior10held excluded. Four redos ready at `http://127.0.0.1:51751/review.html#overview`, [report](research/menu-ui-stencil-corrections-2026-10-29.md), ledger `config/menu-ui-stencil-corrections-2026-10-29.json`. Selectedv3/v3/v4/v5;8 actual builtin successes,4selected/4superseded,0failures. Original stencil stems have small terminal flares and modulation; do not describe all as plain rectangles or add music weight. CRIB I source8px ends/6px middle confirms this. First redo missed flares; second bounded pass selected. Geometry/cut/curve differences remain qualified, not exact-font claims. Browser4cards/8canvases/29cases, no errors/overflow; source/default/raw/export/hash checks pass,100approvals/rejectedpreviews/published1.3 preserved. Four new candidates unapproved; no native/install/publish/push. Private `logs/menu-ui-wave08-stencil-revisions-20261029/`; recovery pinned separately. Next: owner review these4, then further remaining-family work; held effect roles still require investigation.

**Batch eight ready — 2026-10-29:** [report](research/menu-ui-reconstruction-wave-08-2026-10-29.md), pins `config/menu-ui-reconstruction-wave-08-2026-10-29.json`. Review `http://127.0.0.1:51750/review.html#overview`: 104 new music/story/user-ID/training/menu previews (69 dark/35 light), three disjoint workers. Initial105 expanded114 with nine complete training labels; 10 held outside selection (six dense-effect material roles, three cream contour errors, one source without image), originals/evidence/all attempts retained. 123 saved builtin PNGs / 2 actual failures / 125 issued calls / 3 prepared-unissued request(s); 104 selected / 19 superseded-or-held PNGs. Parent all-source/new native1×/magnified blue+pale contacts and worker HD checks; browser104details/208overviewcanvases/27controls, zero errors/overflow. Generated alpha/RGB>16 exact on export, not an exact original-alpha claim. Prior50 now approved (500 distinct accepted source IDs), all earlier pins/published1.3 immutable. New batch awaits owner review, no native/install/publish/push. Private `logs/menu-ui-wave08-20261029/`; recovery pinned separately. Next: owner review, remaining-family classification/logical masters, held effect-role native investigation; 734unassigned mappings are not all whole-word lettering. Future PR milestonev0.12.2.

**Music-list batch approved — 2026-10-29:** Vlad: “You got it, that's perfect. Continue. Do batches of at least 100”. All selected 45 weight revisions and five preserved stylized/unrelated previews are accepted, including the disclosed Volume10 curve difference. Exact50 raw/preview pins reverified in `config/menu-ui-reconstruction-wave07-approval-2026-10-29.json`; 500 distinct reconstruction sources now accepted across the published and queued sets. Published1.3/catalogue7 remain immutable. Next batch has105 distinct new source IDs assigned to three artwork workers,35each; music words use the approved native1× weight while stylized headings preserve their own font. Private workspace `logs/menu-ui-wave08-20261029/`. These new105 are not yet approved.

**Music-list weight revision ready — 2026-10-29:** [report](research/menu-ui-music-weight-revision-2026-10-29.md), pins `config/menu-ui-music-weight-revision-2026-10-29.json`. Review `http://127.0.0.1:51749/review.html#overview`: 45 plain music text sources revised for heavier native1× strokes; five stylized/unrelated previews unchanged. Three workers, 57 saved builtin PNGs / 4 actual failed calls / 61 calls total; 45 selected new / 12 saved alternates / zero unissued. Flat terminal and smooth-bowl corrections retained; Volume10 still has angular-bowl residual after its correction returned no image, disclosed in Detail. Parent source/previous/new contacts and worker blue/pale/HD checks complete. Browser50details/100overviewcanvases/56 control cases, zero errors/overflow. All source alpha and RGB>16 exact on export; prior50drafts/450accepted IDs/published1.3 immutable. Private workspace `logs/menu-ui-weight-revision-20261029/`; additive recovery pinned separately. These revised45 await owner review; no new native run, installation, publishing or approval inferred. Next: owner weight review, then accepted art assembly/native validation; preserve old and new attempts. Historical thin-weight guidance below is superseded by this feedback.

**Batch seven ready — 2026-10-28:** [report](research/menu-ui-reconstruction-wave-07-2026-10-28.md), source pins `config/menu-ui-reconstruction-wave-07-2026-10-28.json`. Review `http://127.0.0.1:51748/review.html#overview`: 50 new standalone menu/music/player-indicator previews (41 dark / 9 light); 51 originals, one Freeway source held after two no-image failures. Three workers: 11/23/17 sources; 72 saved builtin PNG attempts, 8 actual failed calls, 80 calls total, 50 selected / 22 alternate PNGs / zero unissued. Parent inspected all selected pairs on blue/pale. Font shapes/weight and light-ink tone remain approximate and explicitly noted; compare saved revisions in Detail. Browser 50 details / 100 overview canvases / 51 controls, zero errors or overflow. Prior 450 accepted IDs and published 1.3 ZIP unchanged; no game, tools-writer or native work for this artwork batch. All 60 wave06 banners are approved for the next pack update, not the already frozen/published 1.3. These new 50 await review. Private workspace `logs/menu-ui-wave07-20261028/`; recovery pinned separately. Next: owner feedback on the new plain-font family, then targeted corrections or pack assembly.

**1.3.0 published — 2026-10-28:** [publication report](research/menu-ui-v1.3-publication-2026-10-28.md), pins `config/menu-ui-v1.3-release.json`. Cloudflare archive `82ad6d53f3161b612110cdd84e3f9d0bde2f517a9a9f6410f9e52afcf963de24`, signed catalogue revision 7, PR [mods#7](https://github.com/vyanhursky/DefJamFFNY-mods/pull/7), milestone v0.12.2. Frozen390 approved mappings;178 additional texture mappings;1,482native/80wide/1,704PNGs. Six serial native routes/39captures and released0.12.1 real network update/rollback pass; no reinstall needed. All80wide and1,314nonmetadata1.2files exact. Newly approved60wave06 queued for next update;50wave07 standalone labels/music drafts in production, not published. Historical pending publication statements below are superseded.

**Batch six approved — 2026-10-28:** Vlad: “Approve those 60 textures, all look great”. All 60 selected raw/preview hashes reverified and recorded in `config/menu-ui-reconstruction-wave06-approval-2026-10-28.json`. These 30 select and 30 loading variants are accepted for the next pack update. The immutable uploaded 1.3.0 package remains its frozen 390-mapping selection; publication checks are still in progress. Wave seven has 50 standalone labels/music textures assigned to three artwork workers. Historical review-pending statements below are superseded by this approval.

**Final ordinary banner variants, batch six — 2026-10-28:** [report](research/menu-ui-reconstruction-wave-06-2026-10-28.md).
The owner approved all prior 100, including disclosed Ice-T edges; pins in
`config/menu-ui-reconstruction-wave05-approval-2026-10-28.json`.
Review `http://127.0.0.1:51747/review.html#overview`: 60 distinct new four-fighter
banner sources, 30 select / 30 loading, three workers with final scopes of 24, 16 and 20 after four untouched sources were reassigned.
79 actual saved built-in outputs, 60 selected and 19 held; literal pre-call/result
records and all raw attempts preserved; 1 failed tool calls and unissued requests separately recorded.
Parent reviewed all 60 source/draft pairs on blue and pale/dark backdrops.
Actual RGBA controls true holes versus partial/opaque ink; genuine colours stay,
without expanded sampling mosaics, new cream rims, bevels or frames. Exact alpha
and RGB >16 preserved on export; bounded near-pure neon checks pass. Earlier
100/103/104/50/27 preview entries remain byte-identical. Browser: 60 details,
120 paired grid canvases, 32 control/filter checks, no console errors or overflow.
Drafts await owner review; no new native run, atlas assembly/install/publish/push.
Published 1.2/catalogue5, scenery/map, game and toolkit unchanged.
Ledger `config/menu-ui-reconstruction-wave-06-2026-10-28.json`; workspace
`logs/menu-ui-wave06-20261028/`; recovery `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave06-review-20261028`;
manifest pin `config/menu-ui-reconstruction-wave-06-checkpoint-2026-10-28.json`.
Ordinary banner selector: zero unassigned. ID99 originals are LOCKED stamps,
queued with remaining menu labels/stamps, including French variants. Remaining
inventory is not all lettering: source-family classification and early pilot
approval reconciliation remain. Local ID99 audit and conservative remaining
inventory/reconciliation receipts are preserved in this checkpoint.
Next: review60, other menu labels/stamps/venue wordmarks/headings, atlas assembly,
native blending/placement/clipping/sampling. Future PRs milestone v0.12.2.
Historical pending statements below retain their original dates.

**100 new banner variants, batch five — 2026-10-28:** [batch report](research/menu-ui-reconstruction-wave-05-2026-10-28.md).
The owner approved all previous 103; pins in
`config/menu-ui-reconstruction-wave04-approval-2026-10-28.json`.
New review `http://127.0.0.1:51746/review.html#overview` covers 100 distinct new
sources: 22 remaining three-fighter and 78 four-fighter, 50 select / 50 loading.
Three isolated workers saved 129 built-in outputs; 100 selected,
29 held. Literal pre-call/result records and all attempts are preserved;
unissued preparations remain separate from successful output counts.
Source RGBA and pale/blue checks distinguish true holes, opaque faces and partial
ink; genuine colour remains, without amplified sampling stripes or new cream rims.
Parent inspected all 100 matched blue and pale/dark comparisons. Source-tail exceptions, if any,
keep full originals and explicit source-specific notes/bounds in the ledger.
All 100 exports preserve raw alpha and RGB >16 exactly; bounded near-pure neon
checks pass. Previous 103/104/50/27 preview entries remain byte-identical.
Browser: 100 details, 200 grid canvases, filters/search/1×/3×/6×/raw/ghost/backdrops,
zero console errors or page overflow. New drafts await owner review. No native
run, atlas assembly, installation, publication or push is claimed. Published 1.2 /
catalogue 5, backgrounds/map, game and toolkit remain unchanged.
Ledger `config/menu-ui-reconstruction-wave-05-2026-10-28.json`; workspace
`logs/menu-ui-wave05-20261028/`, server 51746. Recovery `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave05-review-20261028`;
manifest pin `config/menu-ui-reconstruction-wave-05-checkpoint-2026-10-28.json`.
Next: review 100, resolve exceptions, then 60 remaining non-99 banner candidates, held ID99 resources and
other label families in 100+ batches. Native atlas/blending/placement/clipping/
sampling validation follows assembly. Future PRs milestone v0.12.2. Historical
pending statements below retain their original dates.

**Next 100 banner variants + three material corrections — 2026-10-28:** [batch report](research/menu-ui-reconstruction-wave-04-2026-10-28.md).
The owner approved all previous 104; approval pins are in
`config/menu-ui-reconstruction-wave03-approval-2026-10-28.json`.
New review: `http://127.0.0.1:51745/review.html#overview`, 103 distinct mappings:
100 new three-fighter variants plus earlier Bo/Cruz/WC select corrections.
Three isolated workers completed 111 saved built-in outputs; 103 selected,
8 held. All actual attempts and immutable pre-call/result records are retained
and hash-verified. Unissued requests are separate from successful output counts.
Parent inspected all 103 matched blue comparisons; worker pale/RGBA checks and
source samples distinguish real ink, partial material and clear holes. Genuine
source colours remain. Busta loading has a documented constant-tail exclusion:
use `logical_review_bounds=[0,5,166,64]` inside its retained full crop when assembling.
All 103 exports retain exact raw alpha and RGB above alpha 16 and pass the
bounded near-pure neon-green check. Prior approved 104/50/27 previews remain exact.
Browser: 103 details, 206 grid canvases, filters/search/1×/3×/6×/raw/ghost/backdrops,
zero console errors or page overflow. These new drafts await owner review;
no new game run, atlas assembly, installation, publication or push is claimed.
Published 1.2 / catalogue 5, scenery, game and toolkit remain unchanged.
Ledger `config/menu-ui-reconstruction-wave-04-2026-10-28.json`; private workspace
`logs/menu-ui-wave04-20261028/`, server 51745. Recovery `/Users/vlad/Code/defjam-data/scratch/menu-ui-wave04-review-20261028`;
manifest pin `config/menu-ui-reconstruction-wave-04-checkpoint-2026-10-28.json`.
Next: review 103, resolve exceptions, continue 100+ source-specific batches,
then native atlas/blending/placement/clipping/sampling validation. Future PRs
use milestone v0.12.2. Historical pending statements below retain their dates.

**100 new textures + four alpha corrections — 2026-10-28:** [batch report](research/menu-ui-reconstruction-wave-03-2026-10-28.md).
Owner accepted all previous50 with no issues and explicitly requested larger,
parallel imagegen batches. Approval pins: `menu-ui-reconstruction-wave02-approval-2026-10-28.json`.
New review `http://127.0.0.1:51744/review.html#overview` contains100new sources
(84two-fighter +16three-fighter) and four earlier select-material corrections
(Nyne/Skull/Ice-T/Solo),104distinct mappings. Three workers own disjoint lists;
completed workers take bounded final corrections in separate folders.130actual
built-in outputs,104selected,26held; all attempts/prompts retained and hash-verified.
Grid208canvases/104details, search/type/layout/four-alpha-fix filters, wraparound,
1x/3x/6x/raw/ghost/backdrops pass with0consoleerrors/pageoverflow. Parent inspected
all104matched source/draft blue-background rows after selection. Export alpha and
RGB>16 exact relative to raw; all104 clear of near-pure neon green. Genuine source
colour and dark translucent material retained. Source-opacity samples distinguish
real holes from grayink; no RGB-only threshold or universal colour-to-alpha fix.
Earlier approved50and27previews remain byte-identical. No game stopped/run,
no pack/catalogue/game/toolkit/publication/push. Native placement/blending/clipping
remain to validate after atlas assembly. Further PRs milestonev0.12.2.
Ledger `config/menu-ui-reconstruction-wave-03-2026-10-28.json`; workspace
`logs/menu-ui-wave03-20261028/`; localhost server51744. Recovery folder
`/Users/vlad/Code/defjam-data/scratch/menu-ui-wave03-review-20261028` (manifest pin
in `config/menu-ui-reconstruction-wave-03-checkpoint-2026-10-28.json`). Previous
reviews/checkpoints remain intact. Next: owner reviews104, resolve exceptions,
continue100+ source-specific batches; finish prior-master contrasting-background
material audit (Bo/Cruz/WC select are specific candidates) before native assembly.
Do not infer all earlier style approvals establish source-alpha correctness.

**50-wordmark batch — 2026-10-28:** [batch report](research/menu-ui-reconstruction-wave-02-2026-10-28.md).
Owner accepted the previous27 review textures and requested at least50 per
routine batch. Approval pins: `menu-ui-reconstruction-approvals-2026-10-28.json`.
New review: `http://127.0.0.1:51743/review.html#overview`, fifty distinct select /
loading wordmarks for25characters, with paired grid, filters/search and detail
next/previous +1x/3x/6x.51built-in generations; selectedTrejo v2 restores its sun's
black centre;v1held. Original intentional colours retained; alpha/RGB>16 exact,
all50exports clear of near-pure neon-green matte pixels. All50details and100grid
canvases load;0consoleerrors/pageoverflow. New drafts await review, native tests
remain separate. No game stopped/run, no pack/publication/push. Prior27PNGs exact.
Ledger: `menu-ui-reconstruction-wave-02-2026-10-28.json`; workspace
`logs/menu-ui-wave02-20261028/`; separate read-only server51743. Previous review
and immutable checkpoints preserved. FurtherPRs use milestonev0.12.2.

**Next production set — 2026-10-27:** [wave and corrected-master report](research/menu-ui-reconstruction-wave-01-2026-10-27.md).
Owner approved the twelve-family direction and requested the next set ready for
tomorrow. Native feedback overrides earlier browser approval: Main Menu v5 is
too heavy and needs thinner M/N/A/open A; dark Capone v2 needs its added outer
rim/depth removed; startup Continue v3 is accepted and remains byte-identical.
New Main Menu v6/Capone v3 and 25 further control/option labels are at
`http://127.0.0.1:51742/next-review/review.html`. These particular new drafts await
review. Published1.2/catalogue5 unchanged; no push or release requested.
Earlier checkpoints below retain their historical pending/acceptance states.

**Native pilot / family batch — 2026-10-27:** [results and continuation](research/menu-ui-reconstruction-pilot-2026-10-27.md).
Owner approved the production plan and added issue #142 green-edge cleanup. Three
accepted samples are captured natively at 1440p; 12 family drafts await review at
`http://127.0.0.1:51742/review/review.html#capone-loading` (Native pilot tab too).
Fourteen generations include two held bad label trials. Preview cleanup preserves
alpha/all RGB above alpha16, removes measured green residue in all12; retained-art
de-matting remains pending. Added 208 separate light loading-name sources: 1,348
text mappings total. Config pins `menu-ui-reconstruction-pilot-2026-10-27.json`.
Published1.2 unchanged. Await family/native feedback before broad waves; tiled,
glyph/language cases and global retained-art fringe work remain.

**Production plan requested — 2026-10-27:** [full approach and prompt set](research/menu-ui-reconstruction-plan-2026-10-27.md).
Owner gives positive feedback on all three corrected-context samples and wants
the plan before more work. Main Menu v5, Continue v3 and Capone v2 establish
the visual direction; native integration and release approval remain pending.
Proposed order: inventory/context mapping, integrate these three in-game,
12–20 representative masters, then production waves and a validated package.
No new generations, integration or publication performed for this planning turn.

**Corrected banner contexts — 2026-10-27:** [pilot report](research/menu-ui-sharpness-samples-2026-10-27.md).
Main Menu v5 and Continue v3 typography accepted. Correct review:
`http://127.0.0.1:51741/contexts/review.html#capone`. Dark Capone now uses the
actual fighter-select pale paper header; light loading banners use portrait
context. Capone brightness remains undecided. No new generations, game run,
export or publication; atlas/native validation remains pending. Earlier context
review below is preserved as history.

**Sample fidelity follow-up — 2026-10-27:** [updated pilot report](research/menu-ui-sharpness-samples-2026-10-27.md).
Owner likes sharpness but requests original typography and game backdrops. Review
`http://127.0.0.1:51741/round2/review.html#capone`: Main Menu v5, Continue v3,
darker detailed Capone v2; prior-draft toggle, source ghost, raw/matched bounds
and real paper/portrait/brick excerpts. Ten raw generations pinned including
three held fringe trials. Native background run 154735 passes and restores its
isolated saves; it shows Blaze/Fat Joe, not generated Capone. Letter geometry
is still approximate; no new art approval, native candidate test or publication.

**Sharper sample batch — 2026-10-27:** [pilot report](research/menu-ui-sharpness-samples-2026-10-27.md).
Owner finds 1.2 text pixelated at 1440p. Three built-in imagegen contour studies
(Main Menu v1, Capone v1, Continue v2) are at `http://127.0.0.1:51741/review.html`.
Four immutable raw outputs and full prompts are pinned in the sample config.
Unapproved texture previews only; atlas assembly and native checks follow style
selection. Published 1.2/catalogue revision 5 and earlier review sessions remain
unchanged. Local branch `codex/menu-ui-sharpness-samples`; no push requested.

**1.2 published — 2026-10-26 (signed catalogue revision 5):** [publication report](research/menu-ui-v1.2-publication-2026-10-26.md).
The owner approved and requested shipment. Stable 1.2 includes 1,140 Stronger text
overrides, including 214 fighter-banner variants; 1,304 native mappings, 80 wide
mappings and all approved 1.1 scenery. Every non-metadata file matches the approved
candidate exactly. Cloudflare hash/range checks, catalogue content/ClamAV checks
and signed deployment pass. A real released-0.12.1 managed update verifies all
1,528 installed files, 404 rollback files and the unchanged isolated save marker. Pins: `config/menu-ui-v1.2-release.json`. Compatible
with game 0.12.1 without reinstalling. Live names/counters retain the runtime font
path; fire-escape geometry repair remains game PR #131 for v0.12.2. Earlier
candidate/no-publication statements below describe historical checkpoints.

**1.2 text candidate — 2026-10-26:** [text pass and native report](research/menu-ui-text-v1.2-2026-10-26.md).
Local branch `codex/menu-text-1-2-0`; 1,140 Stronger text overrides including214
fighter-banner variants. Standalone RC1 retains the1.1 scenery; released0.12.1
installer validation and final1440p/32:9 native checks pass. Allsix prior text
pins remain exact. Review `http://127.0.0.1:51740/review.html`; public catalogue
remains1.1. Live player names/counters/font-cache permutations are not exhaustively
covered by a source-ID texture pack. Pins: `config/menu-ui-text-v1.2-candidate.json`.

**1.1 published — 2026-10-26 (signed catalogue revision 4):** [publication and compatibility report](research/menu-ui-v1.1-publication-2026-10-26.md).
The final stable archive supersedes local RC1: 180 native textures (17 unchanged
original anchors added for installer validation), 80 wide/stretch entries,
404 files. See `config/menu-ui-v1.1-release.json` for its immutable hash and URL.
Artwork loads on v0.12.1 without a game reinstall. The fire-escape geometry
repair is separate game code queued for v0.12.2. Earlier no-publication and
local-RC1 statements below are historical.

**Latest join repairs — 2026-10-26:** [join follow-up report](research/menu-ui-joins-2026-10-26.md).
Choose Teams v2 uses Battle wall v4 exterior art and preserves its complete center.
Map v6 repairs both exterior connections and the obsolete inset with narrow
inpaints; wide copies allow 24px source-border corrections, central draws stay
original. Team native 1440p and map directional 1440p/32:9 checks pass. The owner
approved the current revised backgrounds; nine new master/text pins are in the
separate `config/menu-ui-v1.1-approved-artwork.json` ledger. Review at 51739 retains
before/after sliders and join crops. A local 1.1 RC1 is built; see the follow-up report for hashes and integrated native checks.
Prompts/recipes/receipts are private in `logs/menu-ui-v1.1/revision-v3/`.
This supersedes the earlier map-v3 failure and Team-v1 selection below.

**2026-10-26 continuation:** branch `codex/hd-widescreen-menu-v1.1`, based on
v0.12.1 release PR #123. The first fire-escape tile has a fingerprinted runtime
geometry repair and five-aspect native checks; missing Battle ID/Team walls,
wide-map scenery and heading/fighter-banner clarity have local review drafts.
Read [the current session report](research/menu-ui-v1.1-2026-10-26.md) and
`config/menu-ui-v1.1-worklist.json` for evidence, remaining acceptance and hand-off.
The older checkpoints below retain their original historical status.

**Owner feedback follow-up:** Stronger text selected (six exact pilot hashes),
Choose Teams v1 accepted. Battle ID wall v4 has revised joins and a native 1440p
capture, awaiting visual review. Map v3 uses the owner's Long Island/New Jersey
reference; its 32:9 directional tour runs normally, but road joins remain a
visual failure and must be finished before acceptance. Latest decisions are in
`config/menu-ui-v1.1-review-decisions.json`; private prompts/art/receipts are in
`logs/menu-ui-v1.1/revision-v2/`. The report above supersedes earlier all-unapproved
status and the earlier native-run deferral.

Current checkpoint — 2026-10-20 (D182–D184/UI): a **separate menu-only RC2** is built
and being tested on this Mac. Faithful HD is optional and earlier-loaded; its library
is not bundled. Download421.6MB / installed423.4MB,157nativePNGs/164sideslabs.
Read [the current release-candidate report](research/menu-ui-separate-release-candidate-2026-10-20.md)
and PROGRESS.md §7 for exact artifact locations, hashes, commands and test coverage.

The actual pre-fight loader uses four `match/0_bg/paper_*` resources (eight IDs),
registered separately from the older approved `battle/matchLoa` preview. All670
approved/conditional art pins remain intact; no new generation was needed.
The transition has an inherited black first-tile rectangle, also reproduced with
Faithful alone; it remains a release issue. Appropriate Story saves, native visual
signoff and final checks remain. Other panel/detail/shop candidates stay held.
[Hosting discussion](research/menu-modpack-hosting-pr17-2026-10-20.md) follows PR17's
small catalogue / separate external artwork download architecture.

The October19 pause and earlier engineering notes below are historical, superseded
by the current report and D161/UI's restoration resume. Artwork stays local.

---

Owner: Vlad. Handover: 2026-10-19. **Texture restoration is PAUSED at Vlad's
request until he has more image-generation credits. Do not generate, repaint or
advance the remaining-art queue.** The next task is engineering: take the
already reviewed artwork, produce a local modpack, and let Vlad playtest it.
This session has not installed a menu-art modpack or validated these images in game.
**Update 2026-10-19 (D158/UI–D160/UI):** source-shaped pack, logo/emblem registration and true
widescreen backgrounds are built and checked on the Mac; see [the report](research/menu-ui-playtest-pack-2026-10-19.md).

## Start here

1. Read the repository's `AGENTS.md` and current `PROGRESS.md`. Work from current
   game `origin/main`, not this session's original v0.9.3 base. At handover the
   fetched main is `c4922e9` (v0.10.3); its picture settings/performance changes
   must survive. The October17 runtime audit used toolkit `4a6c88e` and is
   historical evidence; recheck today's toolkit and loader before implementation.
2. Locate the complete private snapshot below. Run the read-only verifier:

   ```sh
   python3 scripts/verify-menu-ui-artwork.py --art-root \
     /Users/vlad/Code/defjam-data/scratch/menu-ui-restoration-paused-20261019/session/pilot-v1
   ```

   Expected: **226 unique file pins, zero failures**. These include approved
   artwork and the separately conditional Mode Select scope. The catalogue
   is `config/menu-ui-approved-artwork.json`; it contains hashes, relative paths,
   approval scopes and71source IDs, never artwork bytes or a runtime-pack manifest.
3. Make an isolated local implementation/export workspace. Preserve the live
   fighter review at8768, its17candidates and Trejo. Do not rerun historical
   approval, import or archive scripts against the original workspace.
4. Deliver an ordinary source-shaped restoration pack first. Implement and
   validate true wide scenery separately; wider PNGs alone cannot provide it.

The menu session's decisions D123–D157 are qualified **/UI** when sharing a
number with decisions on other branches. Keep original historical identifiers;
D137/UI is emblem approval, whereas main's D137 is a release decision.

## Where everything lives

| Item | Exact location |
|---|---|
| Complete persistent private snapshot | `/Users/vlad/Code/defjam-data/scratch/menu-ui-restoration-paused-20261019/` |
| Authoritative art root within it | `session/pilot-v1/` |
| Original working art root | `/Users/vlad/.codex/worktrees/01c5/DefJamFFNY-recomp/logs/ui-restoration-20261017/pilot-v1/` |
| Data/dump root | `/Users/vlad/Code/defjam-data/` (`extracted/`, `mods/`, `save/`) |
| Authoring repository | `/Users/vlad/Code/DefJam-Modding-Tools/` |
| Existing faithful corpus | `/Users/vlad/Library/Application Support/DefJamPR19-20/data/hd-work/setup-lanczos/b9aa783f1d66d41be59fb97ba25fb86e1e9f73d8ee041263b0ff5df85ceb26f0/` |
| Authoring Python, Pillow/NumPy | `/Users/vlad/Code/DefJam-Modding-Tools/.venv/bin/python` |
| Live fighter workshop | `http://127.0.0.1:8768`, workspace `/Users/vlad/Code/defjam-data/hd-work/texture-workshop` |
| Separate read-only menu review | `http://127.0.0.1:51738/review.html` |

The full snapshot is self-contained session evidence, unlike the older incremental
`<data>/scratch/menu-ui-*` overlays. It retains every input/raw/final/history,
alpha registration field, prompt, recipe and review page. `manifest.json` at its
root fingerprints the snapshot. Keep it unchanged; work on a copy or new export.
To resume the review if51738is absent, serve its art root with a read-only static
server bound to127.0.0.1; use another port if51738already serves another session.
Do not start a second writer on the8768workspace. Never depend on a Codex worktree
or `$CODEX_HOME/generated_images` as the only artwork copy.

Public source counterparts:

- This handover, `docs/research/menu-*.md`, tooling/runtime audits and the hash
  catalogue belong to `vyanhursky/DefJamFFNY-recomp`.
- `vyanhursky/DefJam-Modding-Tools`, branch `codex/menu-ui-art-source`, contains
  the production guides, reusable prompt templates and
  `research/menu-ui-pilot-20261017/`: historical Python/HTML/Markdown/prompt source,
  extracted prompt specifications and a source-file hash index. It contains no
  textures, screenshots, registration arrays, workspace review JSON or game data.
  The source index retains original/published fingerprints and declares one whitespace-only publication edit; hard-coded paths and
  write side effects make them evidence, not a safe batch command to run blindly.

## Exact accepted revisions

All paths in this table are relative to the private art root. Consult the
catalogue and named approval record instead of selecting the newest PNG.

| Artwork | Accepted artifact / record | Implementation caveat |
|---|---|---|
| Title sky | `seam-v3/title-skyline-wide-master-v3.png`; `skyline-approval.json` | v3full-height cloud joins; earlier/right-upper-only repair is superseded. Approved art-space master/crops, not approval of independent workshop trials. |
| Title city | `batch2/title-middle-restrained.png`, `title-middle-wide-draft.png`; `branding-v1/city-approval.json` | Active640×310; settled stage(0,102); full640×512texture contains opaque padding. |
| Title tower/roof | `batch2/title-tower-restrained.png`, `title-tower-wide-draft.png`; `approvals-v1/approval.json#water_tower` | Active640×446; stage(0,16); do not composite its512-high padding over lower layers. |
| Mode Select | `batch2/mode-environment[-lit]-wide-draft.png`; `approvals-v1/approval.json#mode_select` | **Conditional**: right4:3border darkness must be reviewed with live spotlight/door/masks/transitions. These are scene studies, not flattened replacement textures. |
| Title logo +8door emblems | `transparency-v2/*-repaired.png`; `branding-approval-20261018.json` | v2clear holes/partial alpha approved. Earlier `branding-v1/*-restrained.png` is a different, unapproved alternate. Approved logo is2172×724, not the original512×128atlas; see registration section. |
| Options | `options-softness-v4/options-wide-v4.png`; `options-approval-20261018.json` | v4reference-width door/panel and slight right defocus. Paper and door are separate scrolling layers; preview is top scroll state. |
| Jukebox | `menus-seams-v2/jukebox-wide-v2.png`; `jukebox-approval-20261018.json` | v2aligned brick joins; live strip/mask/lighting layers remain separate. |
| Battle setup | `battle-left-light-v5/cmtype-wide-v5.png`; `battle-setup-approval-20261019.json` | v5LEFTupper lighting accepted; v4RIGHTlighting was explicitly reverted. Keep improved v3brick and pre-v4right. |
| Fighter menus2/3/4 | `battle-v1/chooseF{2,3,4}-wide-draft.png`; `battle-fighter-approval-20261019.json` | Three different frame layouts/source pairs, not one interchangeable background. |
| Rewards/Unlock Fighters/Unlock Venues | `rewards-v1/rewards-shared-world-v1.png`; `rewards-approval-20261019.json` | Same two source IDs,3screen labels/2placements. Wide vignette exception below. |
| High Scores | `hiscores-v1/hiscores-wide-v1.png`; `hiscores-approval-20261019.json` | Independent wall/board, not a Rewards reskin. Entire score board/rules protected. |
| Rematch/results1–4/reward earned | `results-v1/{rematch,matchSm1,matchSm2,matchSm3,matchSm4,rewardun}-restrained.png`; `results-approval-20261019.json` | All6approved;18original-shaped tile exports. Keep paper size/placement at wider ratios. Stage drafts are transparent placement proofs. |

Artwork coverage: **71unique original source IDs** (63unconditionally approved,
8conditional Mode Select); **101built-in imagegen calls** historically. No further
calls are authorized while paused. A composed emblem is several original tiles;
226pinned review outputs are not226independent texture replacements.

## Source-shaped pack: first playable delivery

Use the existing schema1PNG loader and sparse overrides, not modified disc files.
Game docs: [HD textures](hd-textures.md), [settings](settings-reference.md).
Authoring implementation: `src/defjam_tools/texture_workshop.py`,
`docs/texture-workshop.md`. The workshop supports immutable import/review/export;
its current live fighter state is not an empty menu workspace.

- Start with the18already source-shaped panel tiles and8Battle background tiles;
  then the Options3,Jukebox2,Rewards2,HighScores2 source-shaped files. Relevant
  `references.json` and approval file lists identify every name/source-ID pair.
  All must retain the original stored canvas, UVpadding, alpha and uniform scale.
- Title city/tower accepted4×mosaics can be split into their original512+128tile
  layout with original512-row padding. Preserve approved pixels and source alpha.
  Skyline and Mode Select need the approved composition/source-layer mapping;
  do not silently substitute the earlier unapproved four workshop trials.
- **Logo/emblem blocker:** owner approval is of the nine repaired artwork canvases,
  not new game-native exports. Their raw-canvas RGB was retained and registered
  source alpha repaired; current shapes/sizes are not uniformly scaled original
  atlases. `transparency-v2/register-alpha.py`, registration receipts/`.npz`,
  `branding-v1/assembled-references.json`, logo/emblem audits and source matrices
  are available. Register accepted art back to the native source geometry, preserve
  clear holes, partial alpha, ink/silhouette/lettering and stored padding, then
  split21emblemtiles and the logo atlas. A blind resize to fit the loader is not
  fidelity validation. Show any visibly changed derivative to Vlad; leave originals
  as an explicit first-pack fallback if registration cannot yet be verified.
- Archive names/numeric image names/SHPX indices are not interchangeable. Original
  archive source IDs are provisional runtime keys: collect actual runtime IDs with
  `RECOMP_TEXTURE_DUMP_DIR`, read `textures.jsonl` and prove decoded pixel matches.
  Current `config/hd-runtime-aliases.json` is a bounded earlier map, not71menu IDs.
  Retain alias evidence; never guess hashes or assign an entire movie one key.
- Export a new local pack with hash receipt: `<data>/mods/menu-ui-restored-test-v1/`
  (or split opacity/channels components if evidence requires it). Texture entries
  are `source-id=textures/source-id.png`; schema1under`[pack]`, straightalpha,
  identical atlas aspect, uniform integer1–8×. Prefer4×source exports where ready.
  Do not include scene studies, join crops, comparison images or AIraws as textures.
- List existing faithful packs first, menu overrides last. Example only:
  `[textures] enabled=1`, `packs=<existing-faithful-components>;menu-ui-restored-test-v1`.
  Keep the installation's actual component names/mip policies. Export does not
  install. Back up settings/pack order, install locally with game closed, restart,
  and confirm actual replacement hits. A bad winning key may fall back to console
  art rather than an earlier faithful pack. Keep an easy disable/rollback path.

## True widescreen scenery: separate engineering stage

The historical loader only accepts same-shape integer-scale replacements. Even
if that check changes, existing APT triangles, UVs, centered placement, scissor,
masks and animated transforms still need explicit support. Do not globally
stretch menus or relax all atlas validation. Preserve live controls/text, icons,
portraits, effects and original4:3behavior. Recheck current toolkit implementation;
`side_fill=art` in old design docs is a proposal, not proof of an implemented path.

Keep game-specific screen/layer mappings in the parent repo and generic renderer/
loader support in the toolkit fork. Follow current repository instructions for
fork publication, pinning and regressions. Upstream PRs remain separately approved.
Bind side artwork by proven source identity plus shape/draw context. Extend the
right background layer with matching motion, opacity, sampling and masks; keep
foreground UI centered. A static post-present side plate is a labelled prototype,
not faithful layered integration. Implement an explicit fallback on unsupported
screens/aspects and isolate opt-in wide-art behavior from ordinary HD replacement.

Art-space ratio sizes at1440high:4:3=1920,16:10=2304,16:9=2560,21:9=3360,
32:9=5120. A5120master's1920-wide center beginsx1600; crop offsets1600/1408/
1280/880/0respectively. **These are art-master coordinates, not texture dimensions
or universal layer origins.** City/tower need their source-to-stage offsets.
Rewardsworld is5256wide with699nativewidth and screen offsets29vs50.4: use
`rewards-v1/references.json` and receipts instead of generic5120crop arithmetic.
Mode's independently moving layers likewise require their actual material bounds.

Rewards exception: source-shaped/native4:3alpha, padding and edge vignette stay
exact. Approved wide views intentionally replace the peripheral baked/alpha fade
and move it to the outside edge; only native x40..659trusted interior stays exact.
Do not enforce full wide4:3RGBAcenter equality on that approved exception or undo
its reviewed treatment. Papers never receive scenery extension or widened geometry.
MatchSm4bottom-right tile startsy255,not256; preserve its one-row overlap. Exact
APT transforms, including subpixel placement, take precedence over rounded previews.

## Art constraints and acceptance

Original palette, no added yellow/warm cast; restrained detail; centered scenery;
allfive aspects including21:9/32:9. Keep source print/lettering, rules, silhouettes,
alpha holes and translucent material. Both full-height joins must match cloud/
brick structure, native texture density, focus/grain and lighting. Do not hide
joins with broad blur or use enforced edge equality as evidence of a good join.
Options' slight approved right defocus is deliberate. Keep all approved inputs
immutable and record new technical export hashes/parents separately.

Use guarded disposable saves and current harness routes. Examples from the audit
(use observed anchors/current help, not invented CLI options):

```sh
python scripts/harness.py run boot --png --env RECOMP_WS_ASPECT=1.7777778 --env RECOMP_TRANS_SHOT_NATIVE=1
python scripts/harness.py run boot --png --env RECOMP_WS_ASPECT=1.6 --env RECOMP_TRANS_SHOT_WIDE=1
```

Native capture preserves actual detail; default640×480captures can squeeze wide
output and cannot establish correct proportions. Texture dumps/diagnostics stay
out of performance measurements. Test4:3,16:10,16:9,21:9,32:9: settled and entrance/
exit, title parallax/skyline, both full-height joins, Mode spotlight/door/selection,
Options scrolling, Jukebox strip, Battle2/3/4frames, shared Rewards placements,
HighScores live text and all6paper layouts. Compare the same animation and light
state, retain live input, and confirm letterboxing/scissor/fades/mips/cache behavior.
Use default picture brightness100and record vignette settings so global options
are not confused with artwork color drift. Validate Mac Vulkan first, then Windows
D3D11and Deck Vulkan separately. Runtime/renderer changes require focused synthetic
fixtures and full current project regression; the art-review checks do not replace it.

Deliver: immutable local componentpack(s), installation/disable instructions,
source-to-runtime mapping and hashes, settings/pack order, per-screen/aspect
captures/checklist with passes/known gaps, native regression evidence, and a list
of temporarily retained originals. Do not claim “allmenuswidescreen” from one
flattened still or mark Mode's conditional border accepted without Vlad's playtest.
No art, captures, game binaries, generated guest C or dump payloads go to GitHub.

## Paused queue and resume prompt

23confirmed future priorities remain (Extras4,phone2,venueframes3,title8,support6),
plus unclassified shared/Story/popup pieces. Registeredflow textures without
custom restoration:1,252of1,323; they already have FaithfulHD. Those are not1,252
background jobs. See [remaining inventory](research/menu-ui-remaining-inventory-2026-10-19.md).
Do not process this queue until Vlad explicitly resumes restoration.

Copyable next-agent request:

> Read `docs/menu-ui-modpack-handover.md`, current `AGENTS.md` and `PROGRESS.md`.
> Restoration is paused: use the approved local artwork without new imagegen calls.
> Verify the226file pins. Build a reversible local source-shaped Menu/UI test
> modpack first, resolve original/runtime identities and missing native exports,
> then implement opt-in widescreen background support while retaining live UI and
> original4:3behavior. Preserve the fighter workshop and all accepted art. Test
> the five aspect ratios, document gaps and provide a local pack Vlad can playtest.
