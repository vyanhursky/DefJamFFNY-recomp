"""Which selection keys mark a fighter as ours.

The game's own fighters use selection keys below RETAIL_LIMIT; that is a fact of the game and
never changes. Custom fighters get logical keys from LOGICAL_FIRST up, one each, in sorted
stable-key order (fighter_bindings.allocate). During a match each is mapped onto one of four
native bank rows, BANK_FIRST to BANK_FIRST + 3 (fighter_window).

A fork that uses part of the range above the retail roster for its own fighters or venues can
move both ranges: change BANK_FIRST and LOGICAL_FIRST here and the matching
DEFJAM_FIGHTER_*_FIRST in src/hooks/fighter_keys.h. tests/unit/test_fighter_keys.py checks that
the two agree, the fighter manifest records the pair, and a game built with another pair treats
the manifest as stale and, if a rebuild does not fix it, starts without packs. Only the defaults
are tested in the game by this project (docs/fighter-online-contract.md, section 1).
"""
RETAIL_LIMIT = 100
BANK_FIRST = 100
LOGICAL_FIRST = 100
BANKS = 4
LOGICAL_LAST = 0x7fffffff

if not RETAIL_LIMIT <= BANK_FIRST <= 124:
    raise ValueError('BANK_FIRST must be 100 to 124')
if not RETAIL_LIMIT <= LOGICAL_FIRST <= 0x7ffffff0:
    raise ValueError('LOGICAL_FIRST must be 100 to 0x7ffffff0')


def manifest_value():
    """The pair as the fighter manifest records it; pc_mods.cpp compares it with its own."""
    return f'{BANK_FIRST},{LOGICAL_FIRST}'


def logical(key, last=LOGICAL_LAST):
    """Whether key is a custom fighter's logical selection key (or one of its aliases)."""
    return type(key) is int and LOGICAL_FIRST <= key <= last
