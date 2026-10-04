#!/usr/bin/env python3
"""Build a screen-anchored RECOMP_PAD_SCRIPT.

Fixed schedules break on this title: popups and screen transitions take a
different time every run. A chain waits for each screen instead. Every stage
starts at an anchor -- a substring of a file the title opens, or of one of the
front end's [FUNCCALL] lines (patches 0045-0047, src/recomp_manual.c) -- and its
presses are timed from that moment; they stop once the next stage's anchor
fires, so generous retries are safe.

    python scripts/pad-chain.py match            # the preset below
    python scripts/pad-chain.py "getscreeninfo(intmain/mainmenu=right@5;a@8+4x6" ...

A stage is ANCHOR=PRESSES; PRESSES is ';'-separated NAME@T or NAME@T+STEPxN
(N presses, STEP seconds apart), each held 0.3 s. The title phase is always
first: START at 14 and 17 s after feflow.xml's second open (the title), then A
every 3 s through the memory-card popups until the next anchor fires.

    set RECOMP_SCRIPT_ANCHOR=feflow.xml#2
    set RECOMP_PAD_SCRIPT=<output>
"""
import sys

PRESETS = {
    # Main menu -> Battle -> One on One -> Standard rules -> P1 joins (no user
    # ID) -> style and fighter, READY -> CPU fighter (the grid opens on the one
    # P1 took, which is refused: right first) -> venue -> the match loads.
    "match": [
        "getscreeninfo(intmain/mainmenu=right@5;a@8+4x6",
        "getscreeninfo(battle/cmtype=a@5+4x7",
        "setmatchtype(=a@5+4x7",
        "getscreeninfo(options/battleid=start@6+4x7",
        "controllerbind(0=a@5+4x8",
        "setbmcurrentuserindex(=a@5+5x6",
        "controllersetup(0,0=right@4;a@6;right@10;a@12;a@16;a@20;a@24;a@28",
        "controllersetup(1,=a@4+4x6",
    ],
}


def presses(spec):
    out = []
    for item in spec.split(";"):
        name, rest = item.split("@")
        if "+" in rest:
            t0, rep = rest.split("+")
            step, n = rep.split("x")
            times = [float(t0) + i * float(step) for i in range(int(n))]
        else:
            times = [float(rest)]
        out += [f"{name}:{t:g}:{t + 0.3:g}" for t in times]
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    stages = PRESETS.get(args[0], None) if len(args) == 1 else None
    if stages is None:
        stages = args
    out = ["start:14:14.3", "start:17:17.3"] + [f"a:{t}:{t}.3" for t in range(20, 90, 3)]
    for stage in stages:
        anchor, spec = stage.split("=", 1)
        out.append("@" + anchor)
        out += presses(spec)
    text = ",".join(out)
    if len(text) >= 4096:
        sys.exit(f"{len(text)} characters: over the pad script's 4 KB")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
