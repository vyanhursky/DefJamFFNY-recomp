"""Offline exact behavior-template matching, never a runtime legacy-ID map.

Both complete packed and decoded records must agree. The shared-table witness
reconstructs the source prefix using only retail bytes and matched rows, so an
unrelated global edit cannot disappear behind a successful per-choice match.
Animation assets, per-core changes and runtime playback remain separate checks.
"""
import hashlib
import struct

from fighter_motion import MotionIndex, require

BASE_MOVE = 142
BASE_PARAMETER = 709
RETAIL_CHOICES = 82


def behavior(index, choice, *, native=False):
    records = (index.record('move', BASE_MOVE + choice, 1),
               index.record('parameter', BASE_PARAMETER + 2 * choice, 1),
               index.record('parameter', BASE_PARAMETER + 2 * choice + 1, 1))
    return tuple(row.native_bytes() if native else row.encode() for row in records)


def chunks(index):
    at, rows = 0, []
    for expected in (b'WAZA', b'FZUI', b'NAME') * 2:
        tag, size = struct.unpack_from('<4sI', index.data, at)
        require(tag == expected, 'Unexpected shared motion chunk')
        rows.append(index.data[at + 8:at + 8 + size])
        at += 8 + size
    return rows, at


def match_finishers(retail, source, choices):
    require(type(retail) is MotionIndex and type(source) is MotionIndex,
            'Motion matching requires validated source indexes')
    require(type(choices) in (list, tuple) and 0 < len(choices) <= 4096
            and all(type(c) is int and 0 <= c < 32768 for c in choices)
            and len(set(choices)) == len(choices), 'Invalid source choice population')
    templates = {t: behavior(retail, t) for t in range(RETAIL_CHOICES)}
    mapping = {}
    for choice in sorted(choices):
        value = behavior(source, choice)
        matches = [t for t, candidate in templates.items() if candidate == value]
        require(len(matches) == 1, 'Source finisher needs exactly one complete retail behavior match: ' + str(choice))
        template = matches[0]
        require(behavior(source, choice, native=True) == behavior(retail, template, native=True),
                'Packed/native finisher behavior matching disagrees')
        mapping[choice] = template
    original, _ = chunks(retail)
    supplied, prefix_bytes = chunks(source)
    rebuilt = list(original)
    # Four chunks must remain wholly unchanged. Population and grouping in
    # secondary WAZA/FZUI are rebuilt, not copied blindly from supplied headers.
    require(all(supplied[i] == original[i] for i in (0, 1, 2, 5)),
            'Source contains unaccounted changes in shared motion tables')
    for chunk_index, kind, base, width in ((3, 'move', BASE_MOVE, 1), (4, 'parameter', BASE_PARAMETER, 2)):
        stride = 32 if kind == 'move' else 39
        old_count = retail.tables[1]['move_count' if kind == 'move' else 'parameter_count']
        source_count = source.tables[1]['move_count' if kind == 'move' else 'parameter_count']
        header_bytes = 12 + 4 * len(retail.tables[1]['group_populations']) if kind == 'move' else 8
        require(source_count >= old_count, 'Source removed original shared motion rows')
        rows = [retail.record(kind, i, 1).encode() for i in range(old_count)]
        changes = {base + width * c + role: retail.record(kind, base + width * t + role, 1).encode()
                   for c, t in mapping.items() for role in range(width)}
        require(source_count == max(old_count, max(changes) + 1),
                'Source shared motion population has unaccounted rows')
        for index in range(source_count):
            if index in changes:
                if index < len(rows):
                    rows[index] = changes[index]
                else:
                    require(index == len(rows), 'Source shared motion additions are not contiguous')
                    rows.append(changes[index])
            elif index >= len(rows):
                require(False, 'Unaccounted shared motion row')
        header = bytearray(original[chunk_index][:header_bytes])
        struct.pack_into('<I', header, 4, source_count)
        payload = bytes(header) + b''.join(rows)
        if kind == 'parameter':
            payload += bytes(-len(payload) % 4)
        rebuilt[chunk_index] = payload
    expected = b''.join(struct.pack('<4sI', tag, len(payload)) + payload
                        for tag, payload in zip((b'WAZA', b'FZUI', b'NAME') * 2, rebuilt))
    require(expected == source.data[:prefix_bytes],
            'Source contains unaccounted shared motion headers, rows or padding')
    return {'schema': 'fighter-finisher-template-match-1',
            'retail_sha256': hashlib.sha256(retail.data).hexdigest(),
            'source_sha256': hashlib.sha256(source.data).hexdigest(),
            'mapping': {str(c): t for c, t in mapping.items()},
            'shared_prefix_bytes': prefix_bytes, 'shared_prefix_sha256': hashlib.sha256(expected).hexdigest(),
            'shared_unaccounted_bytes': 0, 'packed_and_native_equal': True,
            'per_core_records_accounted': False, 'animation_conversion': False, 'native_playtest': False}
