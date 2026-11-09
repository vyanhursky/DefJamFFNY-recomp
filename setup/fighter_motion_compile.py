"""Append owned motion cores while retaining a verified retail behavior template.

This is the registration foundation, not authored motion/event admission. It
keeps original shared tables and core ordinals byte-identical. The runtime must
dispatch added descriptors separately and map their inherited animation banks;
the original native descriptor array must never be enlarged in place.
"""
import hashlib
import struct

from fighter_assets import AssetError
from fighter_motion import MotionIndex, MAX_BYTES, MAX_CORES
from fighter_registry import key


def require(condition, message):
    if not condition:
        raise AssetError(message)


class MotionCoreTemplates:
    def __init__(self, data, expected_sha256):
        require(isinstance(data, bytes) and len(data) <= MAX_BYTES
                and hashlib.sha256(data).hexdigest() == expected_sha256,
                'Motion core templates require the verified original stream')
        self.index = MotionIndex(data)
        self.sha256 = expected_sha256

    def compose(self, donors):
        """Map logical resource keys to zero-based original descriptor indices.

        Core0/1 have extra native special behavior outside descriptor access.
        Their reuse is rejected until that behavior has a corresponding adapter.
        Character/SODB core IDs and bank numbers are one-based; these are named
        separately in the receipt to prevent an accidental off-by-one binding.
        """
        require(type(donors) is dict and donors, 'Motion composition needs resource bindings')
        count = len(self.index.core_spans)
        require(count + len(donors) <= MAX_CORES, 'Motion core population exceeds budget')
        require(len(self.index.data) + len(donors) * 860 <= MAX_BYTES,
                'Composed motion stream exceeds budget')
        for identifier, donor in donors.items():
            key(identifier)
            require(type(donor) is int and 2 <= donor < count,
                    'Motion donor is missing or needs the special-core adapter')
        output = bytearray(self.index.data)
        bindings = {}
        for identifier, donor in sorted(donors.items()):
            descriptor = count + len(bindings)
            start = self.index.core_spans[donor]
            offset = len(output)
            output.extend(self.index.data[start - 8:start + 852])
            bindings[identifier] = {
                'descriptor_index': descriptor,
                'character_core': descriptor + 1,
                'donor_descriptor_index': donor,
                'inherited_bank_number': donor + 1,
                'parameters_offset': offset + 8,
                'actions_offset': offset + 80,
            }
        result = bytes(output)
        parsed = MotionIndex(result)
        require(len(parsed.core_spans) == count + len(bindings),
                'Composed core count differs from its bindings')
        return result, {
            'schema': 'fighter-motion-core-templates-1',
            'source_sha256': self.sha256,
            'sha256': hashlib.sha256(result).hexdigest(),
            'bytes': len(result), 'original_core_count': count,
            'core_count': len(parsed.core_spans), 'bindings': bindings,
            'behavior_policy': 'verified-original-template',
            'native_descriptor_dispatch_required': True,
            'native_bank_mapping_required': True,
            'runtime_ready': False,
        }


def encode_core_bindings(data, report):
    """Runtime-owned relative offsets, never package-supplied guest addresses.

    Revalidate the receipt and every appended pair before emitting FMC1. The
    consumer must verify the whole motion file digest and retain its backing
    resource generation; this table alone does not admit authored behavior.
    """
    require(type(report) is dict and report.get('schema') == 'fighter-motion-core-templates-1',
            'Unsupported motion composition receipt')
    require(isinstance(data, bytes) and len(data) <= MAX_BYTES
            and report.get('bytes') == len(data)
            and report.get('sha256') == hashlib.sha256(data).hexdigest(),
            'Motion composition digest differs')
    original = report.get('original_core_count')
    bindings = report.get('bindings')
    require(type(original) is int and 3 <= original <= MAX_CORES
            and type(bindings) is dict and 0 < len(bindings) <= MAX_CORES - original,
            'Invalid motion binding population')
    index = MotionIndex(data)
    require(report.get('core_count') == len(index.core_spans) == original + len(bindings),
            'Motion binding count differs from its stream')
    original_end = index.core_spans[original] - 8
    require(report.get('source_sha256') == hashlib.sha256(data[:original_end]).hexdigest(),
            'Motion original-template digest differs')
    rows = []
    for ordinal, (identifier, row) in enumerate(sorted(bindings.items()), original):
        key(identifier)
        require(type(row) is dict and set(row) == {
            'descriptor_index', 'character_core', 'donor_descriptor_index',
            'inherited_bank_number', 'parameters_offset', 'actions_offset'},
            'Invalid motion binding record')
        require(all(type(value) is int for value in row.values()), 'Invalid motion binding word')
        donor = row['donor_descriptor_index']
        parameters = index.core_spans[ordinal]
        require(row['descriptor_index'] == ordinal and row['character_core'] == ordinal + 1
                and 2 <= donor < original and row['inherited_bank_number'] == donor + 1
                and row['parameters_offset'] == parameters and row['actions_offset'] == parameters + 72,
                'Motion descriptor, bank or payload binding differs')
        source = index.core_spans[donor]
        require(data[parameters - 8:parameters + 852] == data[source - 8:source + 852],
                'Motion template payload differs from its verified donor')
        rows.append((ordinal, parameters, parameters + 72, donor + 1))
    return (b'FMC1' + struct.pack('<5I', 1, original, len(rows), len(data), 0)
            + hashlib.sha256(data).digest()
            + b''.join(struct.pack('<4I', *row) for row in rows))
