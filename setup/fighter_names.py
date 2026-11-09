"""FML1: bounded native lookup-key -> UTF-16 text registration data."""
import struct
from fighter_sod import name_hash

MAX_COUNT = 16384
MAX_TEXT = 1024 * 1024


def encode_names(entries):
    if not isinstance(entries, dict) or len(entries) > MAX_COUNT:
        raise ValueError('Fighter name count exceeds budget')
    records, texts, seen = [], bytearray(), set()
    for symbol, text in sorted(entries.items(), key=lambda item: name_hash(item[0])):
        key = name_hash(symbol)
        if key in seen or not isinstance(text, str) or not text or '\0' in text:
            raise ValueError('Invalid or colliding fighter name')
        seen.add(key)
        encoded = text.encode('utf-16le') + b'\0\0'
        records.append(struct.pack('<III', key, len(texts), len(encoded)))
        texts.extend(encoded)
        if len(texts) > MAX_TEXT:
            raise ValueError('Fighter name pool exceeds native memory budget')
    return b'FML1' + struct.pack('<III', 1, len(records), len(texts)) + b''.join(records) + texts
