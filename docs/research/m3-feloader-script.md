# M3 — feloader's own script: when does it request the next screen?

> **Update, 2026-09-23 13:00 (main agent, after measuring).** Read this report for the
> script, not for the diagnosis. Two corrections:
> - Event flag `0x0002` is **EnterFrame** in standard SWF numbering; `apt-dump.py`
>   prints it as `KeyPress` because it borrows OpenSAGE's names. The per-tick reading
>   below is right.
> - In the front end, `_root.g_inGame` is never 1 (the C side sets `extern.g_inGame`
>   only on the in-game path, `sub_0006B760`), so this clip event is **not** how the
>   front end's first screen loads. The blocker is upstream: the loader movie's timeline
>   never advances, because the allocation for its decompressed BIGF failed, and the
>   movie was decompressed to guest address 0. See `PROGRESS.md` §7.

Produced with `scripts/apt-dump.py` against `screens/feloader.big` in the user's own
dump (see that tool's docstring for format notes). All offsets below are absolute
byte offsets into `feloader.apt`'s own stream, i.e. exactly what a hypothetical
runtime interpreter would be dispatching from if it mapped the file directly.

## Answer

**feloader's main timeline has 5 frames (0–4). The C-side load request is not picked
up by any per-frame timeline action. It is picked up by a placed clip's own event
handler, dispatched once per player tick, independent of which timeline frame the
movie is sitting on** — confirmed by the bytecode's content, though the exact
semantic name of the event-flag bit is inferred (see "divergence" below).

Concretely, three things have to happen, in this order:

1. **Frame 0** places a character (index **170**, instance name `"pageloader"`) at
   depth 3 with a clip-event handler (`PlaceObjectFlags.HasClipAction`, event flag
   value `0x000002`, at file offset **0xFE94**). Frame 0 also places character 169
   (`"controllerstuff"`) with its own clip-event handler (flag value `0x000040`, at
   **0xFE2C**, controller/key-capture code, unrelated to loading).
2. **Frame 1**'s only action is `Stop` (0xDB50: `Stop; End`) — the main timeline
   auto-advances from frame 0 to frame 1 once, then halts there. Frame 2 (never
   reached while stopped) would `RemoveObject` the depth-3 clip and replace it with
   a different one (character 171, a "pan down" transition-ready handler) — so the
   `g_bLoadRequest` watcher that lives on character 170 is only resident, and only
   watching, while the timeline sits on frame 0 or 1.
3. **On every dispatch of that clip event** (not gated by the timeline frame
   number), the handler at **0xFE94** runs this logic (constant-pool-resolved,
   disassembly trimmed to the load-relevant instructions):

   ```
   0x00FEA0  push _root
   0x00FEA2  get  g_inGame
   0x00FEA4  push 1
   0x00FEA5  Equals2
   0x00FEA6  Not
   0x00FEA7  BranchIfTrue -> 0xFEB5        ; if _root.g_inGame != 1, skip the mirror
   0x00FEAC  push _root
   0x00FEAE  push "bRequest2Load"
   0x00FEB0  push extern
   0x00FEB2  get  g_bLoadRequest            ; extern.g_bLoadRequest  (the C variable)
   0x00FEB4  SetMember                      ; _root.bRequest2Load = extern.g_bLoadRequest
   0x00FEB5: push _root
   0x00FEB7  get  bRequest2Load
   0x00FEB9  push 1
   0x00FEBA  Equals2
   0x00FEBB  Not
   0x00FEBC  BranchIfTrue -> 0xFEF1 (End)   ; if bRequest2Load != 1, do nothing else
   0x00FEC4  push _root
   0x00FEC6  get  g_inGame
   0x00FEC8  push 1
   0x00FEC9  Equals2 / Not
   0x00FECB  BranchIfTrue -> 0xFED9         ; if g_inGame != 1, skip the string mirror
   0x00FED0  push _root
   0x00FED2  push "sLoadFile"
   0x00FED4  push extern
   0x00FED6  get  g_sLoadFile                ; extern.g_sLoadFile   (the C variable)
   0x00FED8  SetMember                       ; _root.sLoadFile = extern.g_sLoadFile
   0x00FED9: push "called"; Trace
   0x00FEDC  push _root
   0x00FEDE  get  sLoadFile
   0x00FEE0  push 1 (argc)
   0x00FEE1  push _parent
   0x00FEE3  EA_CallNamedMethodPop "StartGame"   ; _parent.StartGame(_root.sLoadFile)
   0x00FEE5  _root.bRequest2Load = 0
   0x00FEEB  extern.g_bLoadRequest = 0
   0x00FEF1  End
   ```

So the two variables the C side sets are read as `extern.g_bLoadRequest` and
`extern.g_sLoadFile` — `extern` here is the AS name for the host/engine object
that the interpreter's global-variable resolution reaches into; this is
consistent with the C side's `g_bLoadRequest`/`g_sLoadFile` being the exact
values read. **The catch: the mirror-in of `g_bLoadRequest` only happens if
`_root.g_inGame == 1` at the moment the clip event fires.** `_root.g_inGame`
is itself an AS-local variable, populated only inside `SyncGlobalData()`
(defined at 0xB6A8, body at 0xB6C4 — it copies `extern.g_inGame` and several
other extern globals into `_root.*`, see excerpt below), and `SyncGlobalData`
is only called lazily, guarded by `if (_root.g_inGame != 1)`, from inside
`StartGame()` (0xD332) and `transitionStart()` (0xBA23) — i.e. nothing in
feloader's own frame-0/1 actions calls it unconditionally at start-up. If
`_root.g_inGame` is still `undefined` (falsy, `!= 1`) the first few times the
clip event fires, the `bRequest2Load` mirror is skipped every time, so
`extern.g_bLoadRequest` is never even read, and `StartGame` is never called —
**regardless of how long `g_bLoadRequest`/`g_sLoadFile` have been set on the C
side.** This is the most concrete, byte-confirmed candidate for "why legal1
never gets requested": either `_root.g_inGame` never becomes 1 by the time the
clip event first ticks, or the clip event never ticks at all (see next
paragraph).

`StartGame(sMoviePath)` (0xD332, body 0xD34C) does bookkeeping (looks
`sMoviePath` up in `g_aScreens[]` to set `g_nScreenIndex`, conditionally loads
`xHead.swf`/`pageHead.swf` into a target named `"overlay"` via `GetURL2`), and
then does the actual screen load:

```
0x00D437  push sMoviePath
0x00D439  push "clip1"
0x00D43B  GetURL2                 ; load(sMoviePath) into clip named "clip1"
```

`GetURL2` (opcode `0x9A`) is a plain stack-based two-argument call (url,
target) — this is the same instruction OpenSAGE's `UrlHandler.Handle` treats
as "load an external movie into the named target sprite" for any URL not
prefixed `FSCommand:`. There is also a small standalone helper defined at
0xD440, `loadMovieClip(sFileName, sTarget)`, whose entire body (0xD45C) is
`Trace("loading movie clip: " + sFileName); GetURL2(sFileName, sTarget)` —
i.e. a thin, general-purpose wrapper around the same mechanism, reachable as
`_root.loadMovieClip` / `_level0._root.loadMovieClip`. Both paths ultimately
resolve to the same `GetURL2` opcode; there is no separate `loadMovie`,
`attachMovie`, or `fscommand` call anywhere on the path from
`g_bLoadRequest` to the actual screen swap (`attachMovie`/`loadMovie` *do*
appear elsewhere in the const pool and are used by unrelated popup code, e.g.
autosave-warning and mem-card popups — not by the loader path).

`"intMain/legal1.swf"` is present verbatim in the frame-0 constant pool
(entry `const[356]`), inside the same `g_aScreens`-style table of every
`.swf` screen path in the game, confirming feloader does know about that
screen by name and would resolve it correctly if `StartGame("intMain/legal1")`
(or similar) were ever called.

## Frame or clip event — which is it?

**A clip event, not timeline advancement.** The `g_bLoadRequest` check lives
entirely inside a `ClipEvent` action block attached to a *placed character*
(`PlaceObject`'s optional `HasClipAction` list), not inside any frame's plain
`Action`/`InitAction` block. In the OpenSAGE-documented format (and this one,
confirmed by the bytes — `PlaceObjectFlags`, `ClipEvent` record layout:
`flags:u24, keycode:u8, offsetToNext:u32, instructions:u32`, all match
byte-for-byte), a clip event fires from the *player's per-tick event pump* for
as long as the character instance stays resident on stage — it is not part of
the linear list of frame actions that runs once when a frame is entered, and
it does not require `_currentframe` to change. Concretely:

- Frame 0 places character 170 with this clip event once; the character
  stays on stage through frame 1 (frame 1 has no `RemoveObject` for depth 3);
  it would only be removed if the timeline reached frame 2.
- Frame 1's *only* action is `Stop`, which halts timeline auto-advance right
  there — the design is clearly "settle on frame 1 and idle", not "cycle
  through frames 0-4".
- So the movie only needs the timeline to advance **one single tick**, from
  frame 0 to frame 1, to reach its intended idle state. After that, the
  `g_bLoadRequest` poll depends only on the clip event continuing to be
  dispatched every player tick — it does **not** need further timeline
  advancement, and does **not** need `_currentframe` to reach 2, 3, or 4
  (those frames belong to a separate later "pan down" transition-animation
  sequence, confirmed by their constant pools referencing
  `g_nTransitionIndex`/`transitionDone`, unrelated to the initial load).

Practical implication for the interpreter/runtime: if the recomp's APT
runtime executes each frame's `Action`/`InitAction` items but does not also
run a per-tick dispatch of resident placed-clip `ClipEvent` blocks (the
equivalent of Flash's `onEnterFrame`/"clip event queue" for objects that stay
on stage across frames), then this exact mechanism would never run, and
`legal1` would never be requested, no matter how many frames elapse or how
long `g_bLoadRequest` stays set — matching the observed symptom.

## Divergence from OpenSAGE

OpenSAGE's `ClipEventFlags` enum (for BFME/Generals) assigns `KeyPress =
0x000002`. Both clip events found in feloader that decode to flag value
`0x000002` (the `g_bLoadRequest` poll above, and a second one at 0xFEF4 on a
later-placed character that checks `_parent.g_nReadyCode` /
`g_currentTransitionType` every dispatch) contain code that polls
engine/global state unconditionally — nothing in either block reads a key
code or a `Key.*` call, which would be expected of a genuine discrete
key-press handler. A third clip event (character 169, "controllerstuff") does
call `Key.getCode()` and looks like real controller-input handling, but its
flag value is `0x000040`, which is not a named bit in OpenSAGE's enum at all
(nearest OpenSAGE bits are `Construct = 0x000004` and `Data = 0x000100`).
**This tool does not rename these bits** — it prints the OpenSAGE name when
one matches numerically and `(none)` otherwise — but the content strongly
suggests Def Jam's APT build assigns at least bit `0x000002` a per-tick
("EnterFrame"-equivalent or similar) meaning rather than OpenSAGE's
`KeyPress`, and defines additional bits (`0x000040`) that OpenSAGE's enum
(scoped to Generals/Zero Hour/BFME) doesn't have names for. This is inferred
from code content, not confirmed against a spec — Def Jam is not one of
OpenSAGE's supported titles and its APT build may simply predate or diverge
from the bit assignments OpenSAGE documents. Everything else checked
byte-for-byte against OpenSAGE's parser (file magics, `.const` entry layout,
`Movie`/`Sprite`/`Character` record layout, `PlaceObject`/`ClipEvent` record
layout, and the ActionScript instruction encodings actually used) matched
exactly with no adjustment needed.

## Other structural facts (confirmed by bytes)

- `feloader.apt` header: `"Apt Data"` magic (8 bytes) at offset 0, matches
  OpenSAGE's `AptFile.FromFileSystemEntry` check exactly.
- `feloader.const` header: `"Apt constant file"` (17 bytes) + 3-byte gap +
  `AptDataEntryOffset=0x420`, `numEntries=889`, `headerSize=32` — matches
  `ConstantData.FromFileSystemEntry` exactly, including the 3-byte gap after
  the fixed-length magic that isn't otherwise documented.
- Root `Movie` character at file offset `0x420`: 5 frames, 640×480,
  16 ms/frame (~62.5 fps timeline tick rate), 176 characters, 0 imports.
- Main timeline frame items:
  - frame 0: `BackgroundColor` (opaque black) + 2 `Action` blocks (`0xB154`,
    `0xCE30`, mostly `DefineFunction` declarations — `PlayMusic`,
    `StopMusic`, `PlaySound`, `SyncGlobalData`, `transitionStart`,
    `setupMovie`, `StartGame`, `loadMovieClip`, `unLoadMovieClip`, and many
    UI/popup helpers — plus some top-level trace/debug code that runs once)
    + `PlaceObject` depth 1 char 169 (`controllerstuff`) + `PlaceObject`
    depth 3 char 170 (`pageloader`).
  - frame 1: `Action @0xDB50` = `Stop; End`.
  - frame 2: `RemoveObject depth=3` + `Action @0xDB54` (`Stop; End`) +
    `PlaceObject depth=3 char=171` (pan-down transition handler).
  - frame 3: `RemoveObject depth=3` + `Action @0xDB60` (transition-index
    stepping, `g_nTransitionIndex`/`transitionDone`).
  - frame 4: `Action @0xDB98` (same transition family).
- 176 total characters: mostly `Text`/`Font`/`Image`/`Shape` (static UI) and
  a number of `Sprite`s (looping animations, up to 460 frames for one —
  character 38 — none of whose own per-frame items reference
  `g_bLoadRequest`/`g_sLoadFile`/`StartGame`).
- 60 distinct ActionScript opcodes are used across the whole movie (3,863
  instruction dispatches disassembled in total):
  `Add2, BranchAlways, BranchIfTrue, CallFunction, CallMethod, ConstantPool,
  Decrement, DefineFunction, DefineLocal, Divide, EA_CallFuncPop,
  EA_CallMethod, EA_CallMethodPop, EA_CallNamedFunc, EA_CallNamedFuncPop,
  EA_CallNamedMethod, EA_CallNamedMethodPop, EA_GetNamedMember, EA_PushByte,
  EA_PushConstantByte, EA_PushConstantWord, EA_PushFalse, EA_PushFloat,
  EA_PushLong, EA_PushNull, EA_PushOne, EA_PushShort, EA_PushString,
  EA_PushThisVar, EA_PushTrue, EA_PushUndefined, EA_PushValueOfVar,
  EA_PushZero, EA_ZeroVar, End, Equals2, GetMember, GetURL2, GetVariable,
  GotoFrame, GotoFrame2, Greater, Increment, LessThan2, Modulo, Multiply,
  NewObject, Not, Play, Pop, PushDuplicate, Return, SetMember, SetVariable,
  Stop, StrictEqual, Subtract, ToInteger, ToNumber, Trace`.
  Notably *not* used anywhere in feloader: `GetURL` (non-stack form),
  `PushData`, `DefineFunction2`, `GotoLabel`, `SetRegister`, `EA_PushRegister`,
  `CloneSprite`/`StartDragMovie`/etc. (the whole "advanced Flash" tail of the
  opcode table).
- Two opcodes appear in feloader's bytecode whose binary operand encoding is
  not confirmed by OpenSAGE's own parser (it has no case for them either, and
  would itself throw `"Unimplemented bytecode instruction"`):
  `EA_CallMethod` (`0x5E`) at **0xC175**, inside an unrelated string-`indexOf`
  helper, and `EA_PushLong` (`0xB7`) at **0xE368**, inside a `helpSticker`
  UI-text-colour setter. Both are unreachable from the `g_bLoadRequest` /
  `StartGame` / `loadMovieClip` path documented above, and `apt-dump.py`
  correctly stops disassembling those two blocks at that point rather than
  guess a size and desync.

## Tool

`scripts/apt-dump.py` — usage, output shape, and hygiene notes are in its
module docstring. It decompresses the requested `.big` entry from a BIG4
archive (via `scripts/refpack.py`, reused rather than reimplemented) entirely
in memory, locates the `.apt`/`.const` pair inside the resulting BIGF
archive, and:

- with no flags: prints the movie header and one line per character;
- `--frames`: additionally lists every frame's items (placed objects with
  their flags and clip-event flag/offset, removed objects, background
  colour, and where each `Action`/`InitAction` block starts) for the main
  timeline and every sprite character;
- `--actions`: additionally disassembles every action block anywhere in the
  movie (frame actions, init actions, clip events, button actions) to opcode
  mnemonics and resolved operands, tracking each block's own
  `ConstantPool`-defined local index table the same way the reference VM
  does, so named-member/named-function operands print as strings rather than
  raw byte indices.

It never writes any game byte to disk under any flag or code path.
