"""Binding keys distinguish owned motion cores from CAF roster identities."""
CAF_BIT = 0x80000000
MAX_BINDINGS = 32768


def caf_key(selection):
    if type(selection) is not int or not 100 <= selection <= 0x7ffffffe:
        raise ValueError('CAF behavior needs a stable roster identity')
    return CAF_BIT | selection


def valid(key):
    return type(key) is int and (141 <= key < 16384 or 0x80000064 <= key <= 0xfffffffe)


def population(rows):
    return (type(rows) is dict and 0 < len(rows) <= MAX_BINDINGS
            and all(valid(key) for key in rows)
            and sum(bool(key & CAF_BIT) for key in rows) <= 16384)
