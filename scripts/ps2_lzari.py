"""Bounded MAX Drive LZARI decoder, adapted from Ross Ridge's mymc lzari.py.

Ross Ridge's mymc is public domain (README.txt and ps2save.py).
Reference: https://github.com/ps2dev/mymc/blob/master/lzari.py
Python 3, decoding only; caller bounds input and output. At most 32 implicit
zero bits are accepted at EOF, as required by the LZARI arithmetic terminator.
"""
import array
from bisect import bisect_right


def string_to_bit_array(s):
    return array.array("B", ((v >> i) & 1 for v in s for i in range(7, -1, -1)))


HIST_LEN = 4096
MIN_MATCH_LEN = 3
MAX_MATCH_LEN = 60

ARITH_BITS = 15
QUADRANT1 = 1 << ARITH_BITS
QUADRANT2 = QUADRANT1 * 2
QUADRANT3 = QUADRANT1 * 3
QUADRANT4 = QUADRANT1 * 4
MAX_CUM = QUADRANT1 - 1
MAX_CHAR = (256 + MAX_MATCH_LEN - MIN_MATCH_LEN + 1)



class LzariDecoder:
    def init(self):
        self.high = QUADRANT4
        self.low = 0
        self.code = 0
        self.sym_cum = list(range(0, MAX_CHAR + 1))
        self.symbol_to_char = [0] + list(range(MAX_CHAR))
        self.sym_freq = [0] + [1] * MAX_CHAR
        self.position_cum = [0] * (HIST_LEN + 1)
        a = 0
        for i in range(HIST_LEN, 0, -1):
            a = a + 10000 // (200 + i)
            self.position_cum[i - 1] = a

    def search(self, table, x):
        c = 1
        s = len(table) - 1
        while True:
            a = (s + c) // 2
            if table[a] <= x:
                s = a
            else:
                c = a + 1
            if c >= s:
                break
        return c

    def update_model_decode(self, symbol):
        # A compatible implemention to the one used while compressing.

        sym_freq = self.sym_freq
        sym_cum = self.sym_cum

        if self.sym_cum[MAX_CHAR] >= MAX_CUM:
            c = 0
            for i in range(MAX_CHAR, 0, -1):
                self.sym_cum[MAX_CHAR - i] = c
                a = (self.sym_freq[i] + 1) // 2
                self.sym_freq[i] = a
                c += a
            self.sym_cum[MAX_CHAR] = c
        freq = sym_freq[symbol]
        new_symbol = symbol
        while self.sym_freq[new_symbol - 1] == freq:
            new_symbol -= 1
        if new_symbol != symbol:
            symbol_to_char = self.symbol_to_char
            swap_char = symbol_to_char[new_symbol]
            char = symbol_to_char[symbol]
            symbol_to_char[new_symbol] = char
            symbol_to_char[symbol] = swap_char
        sym_freq[new_symbol] = freq + 1
        for i in range(MAX_CHAR - new_symbol + 1, MAX_CHAR + 1):
            sym_cum[i] += 1

    def decode_char(self):
        high = self.high
        low = self.low
        code = self.code
        sym_cum = self.sym_cum

        _range = high - low
        max_cum_freq = sym_cum[MAX_CHAR]
        n = ((code - low + 1) * max_cum_freq - 1) // _range
        i = bisect_right(sym_cum, n, 1)
        high = low + sym_cum[i] * _range // max_cum_freq
        low += sym_cum[i - 1] * _range // max_cum_freq
        symbol = MAX_CHAR + 1 - i

        while True:
            if low < QUADRANT2:
                if low < QUADRANT1 or high > QUADRANT3:
                    if high > QUADRANT2:
                        break
                else:
                    low -= QUADRANT1
                    code -= QUADRANT1
                    high -= QUADRANT1
            else:
                low -= QUADRANT2
                code -= QUADRANT2
                high -= QUADRANT2
            low *= 2
            high *= 2
            code = code * 2 + self.in_iter()

        ret = self.symbol_to_char[symbol]
        self.high = high
        self.low = low
        self.code = code
        self.update_model_decode(symbol)
        return ret

    def decode_position(self):
        _range = self.high - self.low
        max_cum = self.position_cum[0]
        pos = self.search(self.position_cum,
                 ((self.code - self.low + 1)
                 * max_cum - 1) // _range) - 1
        self.high = (self.low +
              self.position_cum[pos] * _range // max_cum)
        self.low += self.position_cum[pos + 1] * _range // max_cum
        while True:
            if self.low < QUADRANT2:
                if (self.low < QUADRANT1
                  or self.high > QUADRANT3):
                    if self.high > QUADRANT2:
                        return pos
                else:
                    self.low -= QUADRANT1
                    self.code -= QUADRANT1
                    self.high -= QUADRANT1
            else:
                self.low -= QUADRANT2
                self.code -= QUADRANT2
                self.high -= QUADRANT2
            self.low *= 2
            self.high *= 2
            self.code = self.in_iter() + self.code * 2

    def decode(self, src, out_length):
        """Decompress a string."""

        a = string_to_bit_array(src)
        a.fromlist([0] * 32)     # add some extra bits
        self.in_iter = iter(a).__next__

        out = array.array('B', b"\0") * out_length
        outpos = 0

        self.init()

        self.code = 0
        for i in range(ARITH_BITS + 2):
            self.code += self.code + self.in_iter()

        hist_pos = HIST_LEN - MAX_MATCH_LEN
        history = [0x20] * hist_pos + [0] * MAX_MATCH_LEN

        decode_char = self.decode_char
        while outpos < out_length:
            char = decode_char()
            if char >= 0x100:
                pos = self.decode_position()
                length = char - 0x100 + MIN_MATCH_LEN
                if outpos + length > out_length:
                    raise ValueError("LZARI match exceeds output size")
                base = (hist_pos - pos - 1) % HIST_LEN
                for off in range(length):
                    a = history[(base + off) % HIST_LEN]
                    out[outpos] = a
                    outpos += 1
                    history[hist_pos] = a
                    hist_pos = (hist_pos + 1) % HIST_LEN
            else:
                out[outpos] = char
                outpos += 1
                history[hist_pos] = char
                hist_pos = (hist_pos + 1) % HIST_LEN

        self.in_iter = None
        return out.tobytes()
