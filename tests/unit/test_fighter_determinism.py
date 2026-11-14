"""Fighter modules use no clock, random numbers or threads of their own (FFNY Online, D1).

Online play (rollback, lockstep) compares game state between PCs. Anything our fighter
code chooses must therefore come from data the two PCs share, never from the time, a
host random source or the order in which our own threads finish. This is a word search
over our modules: it guards them only and says nothing about the base game, whose own
seeded generator and asynchronous loader (src/patches/fighter_film_async.c keeps request
ownership by handle; completion order is the game's) are outside it. The replay check
with a custom fighter (regress.py, row replay-fighters) is the evidence that matters.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = re.compile(r'\b(rand|srand|rand_s|random|time|clock|GetTickCount|GetTickCount64|QueryPerformanceCounter'
                       r'|QueryPerformanceFrequency|clock_gettime|gettimeofday|timeGetTime|CreateThread|_beginthread'
                       r'|_beginthreadex|pthread_create|SDL_CreateThread|SDL_GetTicks|SDL_GetPerformanceCounter)\s*\('
                       r'|std::thread|std::async|std::chrono|std::random_device|std::mt19937')

# Each allowed use, with why it cannot reach game state.
ALLOWED = {
    # set_aside() names a damaged unlock file it moves aside: unlocks.ini.bad-<date-time>. The name
    # never reaches the game; the unlock contents come from the readable lines alone.
    ('src/patches/fighter_runtime.c', 'time_t now = time(NULL);'),
}


def test_fighter_modules_have_no_clock_random_or_thread_of_their_own():
    found = set()
    for path in sorted([*ROOT.glob('src/patches/fighter_*.c'), *ROOT.glob('src/hooks/fighter_*.c')]):
        name = path.relative_to(ROOT).as_posix()
        for line in path.read_text(encoding='utf-8').splitlines():
            code = line.split('//')[0]
            if FORBIDDEN.search(code):
                found.add((name, code.strip()))
    assert found <= ALLOWED, 'Fighter code uses a clock, a random source or a thread: ' + repr(sorted(found - ALLOWED))
    assert ALLOWED <= found, 'An allowed use is gone; remove it from ALLOWED: ' + repr(sorted(ALLOWED - found))
