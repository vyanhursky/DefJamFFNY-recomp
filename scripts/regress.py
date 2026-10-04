#!/usr/bin/env python3
"""The regression run: everything that is checked after a change, in one command.

    python scripts/regress.py                 # all checks, release build (about 20 minutes)
    python scripts/regress.py --quick         # unit tests, the three golden frames, one fight
    python scripts/regress.py --only fight,intro
    python scripts/regress.py --preset win-x64-debug --soak 10

Checks, in order:
  unit     pytest tests/unit (no game needed)
  m2       the loading screen's frame signature        tests/golden/m2-loading-screen.json
  m3       the title screen's                          tests/golden/m3-title-screen.json
  m4a      the main menu's                             tests/golden/m4a-main-menu.json
  fight    a scripted One on One: reaches the fight, holds the frame rate, no crash
  intro    Story from a new ID: both cutscenes play to the creator, no truncated batch
  crib     Story with the first saved profile reaches the crib
  gym      Learn Moves opens and a move's preview movie is requested
  soak     N boots to the main menu, none hung

The golden frames were taken without the title's gamma ramp, so those three runs
set RECOMP_GAMMA=0. Every run uses the harness's complete-save-root guard and
fails if the save area is not byte-identical afterwards.

Exit code 0 only if every check that ran passed. The table is also written to
logs/regress-<stamp>.txt.
"""
import argparse
import importlib.util
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("harness", os.path.join(HERE, "harness.py"))
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
REPO = harness.REPO

ORDER = ["unit", "m2", "m3", "m4a", "fight", "intro", "crib", "gym", "soak"]
QUICK = ["unit", "m2", "m3", "m4a", "fight"]

# A 2 s line of a 60 Hz title holds 120 presents. Loading screens run at 30, so the
# floor is on the median, and lower for the debug build.
FPS_FLOOR = {"win-x64-release": 110, "win-x64-debug": 100}

def median(xs):
    return sorted(xs)[len(xs) // 2] if xs else 0


def common_faults(run):
    """What no run should show, whatever it was for."""
    return harness.run_faults(run)


def verdict(faults, detail):
    return (not faults), ("; ".join(faults) if faults else detail)


# --- checks ----------------------------------------------------------------

def check_unit(a):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/unit"], cwd=REPO, capture_output=True, text=True)
    last = (r.stdout.strip().splitlines() or ["no output"])[-1]
    return r.returncode == 0, last


def golden(a, name, frame, json_name, env, secs):
    e = {"RECOMP_GAMMA": "0"}
    e.update(env)
    path = os.path.join(REPO, "logs", "shots", "golden-" + name, frame)
    run = harness.run_game("golden-" + name, secs=secs, preset=a.preset, env=e, scripted=False, quiet=True,
                           until_file=path)
    faults = common_faults(run)
    if not os.path.isfile(path):
        return False, "; ".join(faults + ["no capture (%s)" % os.path.relpath(run.log, REPO)])
    r = subprocess.run([sys.executable, os.path.join(HERE, "frame-signature.py"), path, "--check",
                        os.path.join(REPO, "tests", "golden", json_name)], cwd=REPO, capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or [r.stderr.strip() or "no output"])[-1]
    if r.returncode != 0 or not line.startswith("OK"):
        faults.append(line)
    return verdict(faults, line)


# The loading screen has no [FUNCCALL] to anchor on, and which frame it is on
# depends on how fast the build starts (frame 150 in debug; release is past it by
# then). So several frames are captured and one of them must be the screen.
M2_FRAMES = [40, 70, 100, 150, 220]


def check_m2(a):
    shot = os.path.join(REPO, "logs", "shots", "golden-m2", "frame.bmp")
    last = os.path.join(REPO, "logs", "shots", "golden-m2", "frame-%d.bmp" % M2_FRAMES[-1])
    run = harness.run_game("golden-m2", secs=60, preset=a.preset, scripted=False, quiet=True, until_file=last,
                           env={"RECOMP_GAMMA": "0", "RECOMP_TRANS_SHOT": shot,
                                "RECOMP_TRANS_SHOT_FRAME": ",".join(map(str, M2_FRAMES))})
    faults = common_faults(run)
    seen = []
    for path in run.shots():
        r = subprocess.run([sys.executable, os.path.join(HERE, "frame-signature.py"), path, "--check",
                            os.path.join(REPO, "tests", "golden", "m2-loading-screen.json")],
                           cwd=REPO, capture_output=True, text=True)
        line = (r.stdout.strip().splitlines() or ["no output"])[-1]
        if r.returncode == 0 and line.startswith("OK"):
            return verdict(faults, "%s matches" % os.path.basename(path))
        seen.append("%s: %s" % (os.path.basename(path), line))
    faults.append("no captured frame is the loading screen (%s)" % ("; ".join(seen) or "no captures"))
    return verdict(faults, "")


def check_m3(a):
    shot = os.path.join(REPO, "logs", "shots", "golden-m3", "title.bmp")
    return golden(a, "m3", "title-5s.bmp", "m3-title-screen.json",
                  {"RECOMP_SCRIPT_ANCHOR": harness.TITLE_ANCHOR, "RECOMP_TRANS_SHOT": shot,
                   "RECOMP_TRANS_SHOT_SECS": "5"}, 150)


def check_m4a(a):
    shot = os.path.join(REPO, "logs", "shots", "golden-m4a", "menu.bmp")
    pad = ("start:8:8.4,start:11:11.4,a:14:14.3,a:18:18.3,a:22:22.3,a:26:26.3,a:30:30.3,a:34:34.3,"
           "a:38:38.3,b:42:42.3,b:46:46.3")
    return golden(a, "m4a", "menu-50s.bmp", "m4a-main-menu.json",
                  {"RECOMP_SCRIPT_ANCHOR": harness.TITLE_ANCHOR, "RECOMP_TRANS_SHOT": shot,
                   "RECOMP_TRANS_SHOT_SECS": "50", "RECOMP_PAD_SCRIPT": pad}, 200)


def check_fight(a):
    run = harness.run_route("fight", preset=a.preset, quiet=True)
    faults = common_faults(run)
    if not harness.reached(run.summary, "game.startgame("):
        faults.append("never reached the fight")
    p = harness.presents_after(run.text, "game.startgame(")
    floor = FPS_FLOOR.get(a.preset, 100)
    if p and median(p) < floor:
        faults.append("median %d presents per 2 s, floor %d" % (median(p), floor))
    if len(p) < 30:
        faults.append("only %d s of fight" % (2 * len(p)))
    return verdict(faults, "%d s of fight, median %d presents per 2 s, minimum %d"
                   % (2 * len(p), median(p), min(p) if p else 0))


def check_intro(a):
    run = harness.run_route("intro", preset=a.preset, quiet=True)
    faults = common_faults(run)
    for anchor, what in (("game.startstorymode(", "Story start"), ("getscreeninfo(story/chardec", "the creator")):
        if not harness.reached(run.summary, anchor):
            faults.append("never reached " + what)
    p = harness.presents_after(run.text, "game.startstorymode(")
    floor = FPS_FLOOR.get(a.preset, 100)
    if p and median(p) < floor:
        faults.append("median %d presents per 2 s, floor %d" % (median(p), floor))
    return verdict(faults, "cutscenes to the creator, median %d presents per 2 s, %d captures"
                   % (median(p), len(run.shots())))


def check_crib(a):
    run = harness.run_route("crib", preset=a.preset, quiet=True)
    faults = common_faults(run)
    if not harness.reached(run.summary, "getscreeninfo(story/crib"):
        faults.append("never reached the crib (is there a Story profile in the save area?)")
    return verdict(faults, "crib reached with the first profile")


def check_gym(a):
    run = harness.run_route("gym", preset=a.preset, quiet=True)
    faults = common_faults(run)
    if not harness.reached(run.summary, "getscreeninfo(story/gym"):
        faults.append("never reached Stapleton Athletics")
    tail = run.text[run.text.lower().find("getscreeninfo(story/gym"):]
    movies = len(re.findall(r"\[PATH\] .*blazin_\d+\.mad", tail))
    if not movies:
        faults.append("no move preview movie was requested")
    return verdict(faults, "Learn Moves, preview movie requested")


def check_soak(a):
    ok, hung, failed = harness.soak(a.soak, a.preset)
    return (ok == a.soak and hung == 0 and failed == 0), "%d of %d boots reached the main menu" % (ok, a.soak)


CHECKS = {"unit": check_unit, "m2": check_m2, "m3": check_m3, "m4a": check_m4a, "fight": check_fight,
          "intro": check_intro, "crib": check_crib, "gym": check_gym, "soak": check_soak}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--preset", default=os.environ.get("RECOMP_PRESET", "win-x64-release"))
    ap.add_argument("--quick", action="store_true", help="unit, the golden frames and a fight")
    ap.add_argument("--only", help="comma-separated checks: " + ",".join(ORDER))
    ap.add_argument("--soak", type=int, default=3, help="boots in the soak check (default 3)")
    a = ap.parse_args(argv)

    names = QUICK if a.quick else ORDER
    if a.only:
        names = [n for n in ORDER if n in set(a.only.split(","))]
        unknown = set(a.only.split(",")) - set(ORDER)
        if unknown:
            ap.error("unknown check: " + ", ".join(sorted(unknown)))

    rows = []
    t_all = time.time()
    for n in names:
        t0 = time.time()
        try:
            ok, detail = CHECKS[n](a)
        except SystemExit as ex:                 # not built, no dump: say so and stop
            ok, detail = False, str(ex)
        rows.append((n, ok, detail, time.time() - t0))
        print("%-6s %-4s %4d s  %s" % (n, "ok" if ok else "FAIL", rows[-1][3], detail), flush=True)
    harness.kill_stray()

    failed = [r for r in rows if not r[1]]
    lines = ["regress %s  preset %s" % (time.strftime("%Y-%m-%d %H:%M"), a.preset)]
    lines += ["%-6s %-4s %4d s  %s" % (n, "ok" if ok else "FAIL", dt, d) for n, ok, d, dt in rows]
    lines.append("%d of %d passed in %d min" % (len(rows) - len(failed), len(rows), (time.time() - t_all) / 60))
    os.makedirs(os.path.join(REPO, "logs"), exist_ok=True)
    out = os.path.join(REPO, "logs", "regress-" + time.strftime("%Y%m%d-%H%M%S") + ".txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(lines[-1] + "  (" + os.path.relpath(out, REPO) + ")")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
