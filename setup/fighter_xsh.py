"""Strict data-only SHPX texture inspection and scoped four-byte shape renaming.

The supported subset matches the existing Xbox texture census: single-level
DXT1/3/5, indexed BGRA palettes and BGRA32, linear or rectangular swizzled.
Unknown formats/attachments fail with a diagnostic instead of entering the
native parser. Geometry/material compatibility remains a separate gate.
"""
import hashlib
import re
import struct

from fighter_assets import AssetError, MAX_ASSET

MAX_IMAGES = 4096
MAX_DIMENSION = 4096
MAX_ATTACHMENTS = 64


def require(condition, message):
    if not condition:
        raise AssetError(message)


def shape_name(value):
    require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_]{4}', value),
            'Texture shape names must be four portable ASCII characters')
    return value.encode('ascii')


class Textures:
    def __init__(self, data):
        require(isinstance(data, bytes) and 24 <= len(data) <= MAX_ASSET, 'Invalid SHPX texture size')
        require(data[:4] == b'SHPX', 'Invalid SHPX texture signature')
        size, count = struct.unpack_from('<II', data, 4)
        require(size == len(data) and 0 < count <= MAX_IMAGES and 16 + count * 8 <= size,
                'Invalid SHPX texture directory')
        self.data, self.images, self.name_sites, self.controls = data, [], {}, {}
        roots, names = [], set()
        for index in range(count):
            raw, offset = struct.unpack_from('<4sI', data, 16 + index * 8)
            try:
                name = raw.decode('ascii')
            except UnicodeError as error:
                raise AssetError('Non-ASCII SHPX shape name') from error
            shape_name(name)
            require(name not in names and offset % 4 == 0 and 16 + count * 8 <= offset <= size - 16,
                    'Duplicate or invalid SHPX texture directory target')
            names.add(name); roots.append((offset, name))
            self.name_sites[name] = [16 + index * 8]
        require(len({offset for offset, _ in roots}) == count, 'Aliased SHPX directory targets need a typed adapter')
        occupied = []
        for root, name in roots:
            position, attachments, image, palette = root, [], None, None
            controls = [data[12:16]]
            for _ in range(MAX_ATTACHMENTS):
                require(position <= size - 16, 'Truncated SHPX attachment header')
                kind = data[position]
                delta = int.from_bytes(data[position + 1:position + 4], 'little')
                following = position + delta if delta else size
                require(not delta or (delta >= 16 and delta % 4 == 0 and following <= size - 16),
                        'Invalid SHPX attachment pointer')
                end = position + 16
                if kind in (0x60, 0x61, 0x62, 0x7b, 0x7d):
                    require(position == root and image is None, 'Nested SHPX image attachment is unsupported')
                    width, height = struct.unpack_from('<HH', data, position + 4)
                    flags, = struct.unpack_from('<I', data, position + 12)
                    require(0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION,
                            'SHPX texture dimensions exceed budget')
                    require(not flags & ~0x3000, 'SHPX mip/format flags need a validated adapter')
                    swizzled = bool(flags & 0x2000)
                    require(not swizzled or (not width & (width - 1) and not height & (height - 1)),
                            'SHPX swizzle requires power-of-two dimensions')
                    if flags & 0x1000:
                        require(position + 20 <= following, 'Truncated SHPX indirect pixel offset')
                        relative, = struct.unpack_from('<I', data, position + 16)
                        require(relative >= 20 and relative % 4 == 0, 'Invalid SHPX indirect pixel offset')
                    else:
                        relative = 16
                    length = (((width + 3) // 4) * ((height + 3) // 4) * (8 if kind == 0x60 else 16)
                              if kind in (0x60, 0x61, 0x62) else width * height * (1 if kind == 0x7b else 4))
                    end = position + relative + length
                    image = {'name': name, 'kind': kind, 'width': width, 'height': height, 'swizzled': swizzled,
                             'pixels_offset': position + relative, 'pixels_bytes': length}
                elif kind == 0x2a:
                    require(palette is None, 'Duplicate SHPX palette')
                    colors, = struct.unpack_from('<H', data, position + 4)
                    require(0 < colors <= 256, 'Invalid SHPX palette population')
                    end = position + 16 + colors * 4
                    palette = (position + 16, colors)
                elif kind == 0x69:
                    length, = struct.unpack_from('<H', data, position + 4)
                    require(length <= 4096, 'SHPX annotation exceeds budget')
                    end = position + 16 + length
                elif kind == 0x7c:
                    value, = struct.unpack_from('<I', data, position + 4)
                    require(value in (0, 1), 'Unsupported SHPX material flag')
                elif kind == 0x70:
                    require(data[position + 4:position + 8] == name.encode('ascii'),
                            'SHPX material shape name differs from its directory owner')
                    self.name_sites[name].append(position + 4)
                elif kind == 0x6f:
                    length, = struct.unpack_from('<I', data, position + 4)
                    require(0 < length <= 4096, 'Invalid SHPX material parameter length')
                    end = max(end, position + 8 + length)
                    require(end <= following, 'SHPX material parameters exceed attachment')
                    text = data[position + 8:position + 8 + length]
                    require(text.endswith(b'\0') and all(32 <= byte < 127 for byte in text[:-1]),
                            'Invalid SHPX material parameter text')
                else:
                    raise AssetError(f'Unsupported SHPX attachment type 0x{kind:02x}')
                require(end <= following and end <= size, 'SHPX texture or attachment exceeds its bounds')
                # Preserve a separate signature for every opaque control byte.
                # Bounds-checked pixels, dimensions, palette colors and names
                # may be authored; appearance activation requires all remaining
                # controls to match a hash-verified original texture layout.
                if kind in (0x60, 0x61, 0x62, 0x7b, 0x7d):
                    control = data[position + 8:position + 16]
                elif kind == 0x2a:
                    control = data[position + 6:position + 16]
                elif kind == 0x70:
                    control = data[position + 8:position + 16]
                else:
                    control = data[position + 4:end]
                controls.append(bytes([kind]) + control)
                occupied.append((position, end)); attachments.append(kind)
                if not delta:
                    break
                position = following
            else:
                raise AssetError('SHPX attachment chain exceeds budget')
            require(image is not None, 'SHPX directory target is not a supported texture')
            if image['kind'] == 0x7b:
                require(palette is not None, 'Indexed SHPX texture has no palette')
                pixels = data[image['pixels_offset']:image['pixels_offset'] + image['pixels_bytes']]
                require(max(pixels) < palette[1], 'SHPX pixel index exceeds palette')
            else:
                require(palette is None, 'Nonindexed SHPX texture carries an unexpected palette')
            image.update(attachments=attachments, palette_entries=palette[1] if palette else 0)
            signature = hashlib.sha256(b''.join(struct.pack('<I', len(c)) + c for c in controls)).hexdigest()
            self.controls[name] = signature
            content = (struct.pack('<III', image['kind'], image['width'], image['height'])
                       + bytes.fromhex(signature)
                       + data[image['pixels_offset']:image['pixels_offset'] + image['pixels_bytes']]
                       + (data[palette[0]:palette[0] + palette[1] * 4] if palette else b''))
            image['content_sha256'] = hashlib.sha256(content).hexdigest()
            self.images.append(image)
        ordered = sorted(occupied)
        require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'Overlapping SHPX texture records')

    def renamed(self, mapping):
        require(isinstance(mapping, dict) and set(mapping) <= self.name_sites.keys(), 'Unknown SHPX shape rename source')
        replacements = {name: shape_name(mapping.get(name, name)) for name in self.name_sites}
        require(len(set(replacements.values())) == len(replacements), 'SHPX shape renames collide')
        output = bytearray(self.data)
        for name, raw in replacements.items():
            for position in self.name_sites[name]:
                output[position:position + 4] = raw
        result = bytes(output)
        Textures(result)  # Revalidate all directory/material references after editing.
        return result

    def metadata(self):
        return {'format': 'fighter-shpx-textures-draft-1', 'sha256': hashlib.sha256(self.data).hexdigest(),
                'bytes': len(self.data), 'images': self.images, 'runtime_ready': False,
                'pending': ['material-model-reference-validation', 'native-resource-acceptance']}
