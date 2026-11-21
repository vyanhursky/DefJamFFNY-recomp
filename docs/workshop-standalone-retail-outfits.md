# Standalone retail-derived outfit groups

`standalone-retail-outfits-1` extends the ordinary resource contract to one
standalone retail-derived parent and at most two same-pack hidden appearance
records. Each child inherits the parent's combat, stats, voice, AI and cinematic
components exactly; only appearance/portrait may differ. Parents cannot be
outfits themselves. CAF parents retain their separate recipe adapter.

The existing selector appends the independent parent first and extends its
original clothing datasets with the children in authored manifest order. The
stable ledger remains independent of this clothing order. Native DisplayName
uses the parent; each hidden record retains its own artwork and model resources.

Generated FWR3 windows carry the parent's logical selection plus one in the last
row word. Decoding requires an independent existing parent, matching motion core
and at most two children; validation is bounded to O(n log n). FWR1 and FWR2
remain compatible and retain their existing producer behavior. Old runtimes
reject FWR3. This is compiler-owned data, never a public package file.

Progress insertion, selection projection and participant clearing use the
parent's canonical handle and preserve metadata without duplicate unlock marks.
Loading/results retain a standalone child's own presentation selection; stock
retail outfits retain the established original-retail presentation behavior.

Real original-body testing exposed a pre-existing indexed PNG edge case: Pillow
can return fewer palette colors than requested for flat-color art. Unused slots
are now padded inside the same original alpha class. Invented fixtures cover it.

Local Windows evidence includes the complete source/native fixture suite,
focused ownership/order/decoder/palette checks and a complete Release build.
A private Workshop pack with three independently painted original-body looks
and invented UI icons passes every selected preview, native export compilation,
normal ZIP installation and activation. The PR description records the exact
regression and native-play scope, including failed attempts and pending gates.
Game assets, ZIPs, captures, saves and generated guest code stay private.
