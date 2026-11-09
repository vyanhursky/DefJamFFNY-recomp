"""Bounded fighter asset decoding shared by offline validation/adapters."""
MAX_ASSET = 64 * 1024**2


class AssetError(ValueError):
    pass


def unpack(data, maximum=MAX_ASSET):
    if not isinstance(data, bytes) or not 0 < len(data) <= maximum:
        raise AssetError('Asset exceeds input budget or is empty')
    if len(data) < 2 or (int.from_bytes(data[:2], 'big') & 0x3eff) != 0x10fb:
        return data
    sig = int.from_bytes(data[:2], 'big')
    width = 4 if sig & 0x8000 else 3
    at = 2 + (width if sig & 0x100 else 0)
    if at + width > len(data):
        raise AssetError('Truncated RefPack header')
    size = int.from_bytes(data[at:at + width], 'big')
    at += width
    if not 0 < size <= maximum:
        raise AssetError('RefPack expansion exceeds asset budget')
    output = bytearray()
    ended = False
    while at < len(data):
        command = data[at]
        at += 1
        extra = 1 if command < 0x80 else 2 if command < 0xc0 else 3 if command < 0xe0 else 0
        if at + extra > len(data):
            raise AssetError('Truncated RefPack command')
        if command < 0x80:
            a = data[at]
            literal, length, distance = command & 3, ((command & 0x1c) >> 2) + 3, ((command & 0x60) << 3) + a + 1
        elif command < 0xc0:
            a, b = data[at:at + 2]
            literal, length, distance = a >> 6, (command & 0x3f) + 4, ((a & 0x3f) << 8) + b + 1
        elif command < 0xe0:
            a, b, c = data[at:at + 3]
            literal, length, distance = command & 3, ((command & 0xc) << 6) + c + 5, ((command & 0x10) << 12) + (a << 8) + b + 1
        else:
            literal, length, distance = (((command & 0x1f) << 2) + 4 if command < 0xfc else command & 3), 0, 0
        at += extra
        if at + literal > len(data) or len(output) + literal + length > size + 3:
            raise AssetError('RefPack command exceeds declared bounds')
        output += data[at:at + literal]
        at += literal
        if length:
            if distance > len(output):
                raise AssetError('Invalid RefPack back-reference')
            start = len(output) - distance
            if length <= distance:
                output.extend(output[start:start + length])
            else:
                # RefPack may read bytes emitted by this same command. Repeat
                # its already available period, bounded by the decoded length,
                # rather than entering Python once for every output byte.
                period = output[start:]
                output.extend((period * ((length + distance - 1) // distance))[:length])
        if command >= 0xfc:
            ended = True
            break
    # Original encoders may pad the final literal run by at most three bytes.
    if not ended or not size <= len(output) <= size + 3:
        raise AssetError('RefPack termination/size mismatch')
    return bytes(output[:size])
