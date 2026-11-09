"""Compose action selections and their motion/event ranges as one typed plan.

The first profile reuses verified, same-bank one/two-motion action families.
It preserves action boundaries and original shared WAZA/FZUI tables; it does
not accept raw native action records or invent semantics for packed fields.
"""
import hashlib
import struct

from fighter_animation import AnimationEnvelope, AnimationIndex, require
from fighter_motion import MotionIndex
from fighter_motion_links import MotionLinks
from fighter_motion_records import PackedRecord


def owner(rows, local):
    previous, lower = 1, 0
    for candidate in range(2, 126):
        boundary = rows[candidate].local_start if candidate < 125 else 1000
        if local < boundary:
            return previous, lower
        if boundary > lower or boundary == lower and rows[candidate].primary_move is not None:
            previous, lower = candidate, boundary
    raise ValueError('Unaddressable participant motion')


def ordinary(action):
    return type(action) is int and 1 <= action < 125 and not 31 <= action <= 41


class MovesetPlan:
    def __init__(self, index, core, envelope, expected_bank_sha256):
        require(type(index) is MotionIndex and type(core) is int and 2 <= core < len(index.cores),
                'Moveset requires an ordinary verified core')
        require(type(envelope) is AnimationEnvelope and envelope.tokens is not None
                and hashlib.sha256(envelope.model.data).hexdigest() == expected_bank_sha256,
                'Moveset requires its verified local animation bank')
        require(0 < len(envelope.tokens) < 1000, 'Moveset exceeds participant motion namespace')
        self.links, self.core, self.bank = MotionLinks(index), core, AnimationIndex(envelope)
        self.rows = self.links.actions[core]
        self.count = len(envelope.tokens)
        self.intervals = {}
        for local in range(self.count):
            action, lower = owner(self.rows, local)
            self.links.primary_parameter(core, local)
            self.intervals.setdefault(action, []).append(local)

    def compose(self, selections):
        require(type(selections) is dict and 0 < len(selections) <= 124
                and all(type(a) is int and type(b) is int for a, b in selections.items()),
                'Moveset needs typed action selections')
        aliases, edits = {}, {}
        for target, source in sorted(selections.items()):
            require(ordinary(target) and ordinary(source) and target != source,
                    'Special or unchanged action needs a different behavior profile')
            old, chosen = self.rows[target], self.rows[source]
            require(old.primary_move is not None and chosen.primary_move is not None
                    and old.flags == chosen.flags, 'Moveset action control flags differ or are disabled')
            destination, origin = self.intervals.get(target, []), self.intervals.get(source, [])
            require(len(destination) == len(origin) and 1 <= len(origin) <= 2
                    and destination == list(range(old.local_start, old.local_start + len(origin)))
                    and origin == list(range(chosen.local_start, chosen.local_start + len(origin))),
                    'Moveset needs equal unambiguous one/two-motion ranges')
            require(not any(i != target and row.primary_move is not None
                            and row.local_start in destination for i, row in enumerate(self.rows[1:], 1)),
                    'Another action aliases the selected motion range')
            for a, b in zip(destination, origin):
                for suffix in ('_s', '_t'):
                    require(self.bank.envelope.tokens[b] + suffix in self.bank.lookup,
                            'Selected motion is missing a paired record')
                aliases[a] = b
            edits[target] = (chosen.move_word, old.local_start, chosen.parameter_base)
        start = self.links.index.core_spans[self.core]
        pair = bytearray(self.links.index.data[start - 8:start + 852])
        for action, row in edits.items():
            struct.pack_into('<3H', pair, 80 + 6 * action, *row)
        # Reparse the complete stream and check every motion's parameter lookup.
        result = bytearray(self.links.index.data)
        result[start - 8:start + 852] = pair
        after = MotionLinks(MotionIndex(bytes(result)))
        for local in range(self.count):
            source = aliases.get(local, local)
            require(after.primary_parameter(self.core, local) == self.links.primary_parameter(self.core, source),
                    'Action selection changed neighboring parameter ownership')
        names = list(self.bank.envelope.tokens)
        for target, source in aliases.items():
            names[target] = self.bank.envelope.tokens[source]
        mnl = struct.pack('<2I', len(names), 0) + '.'.join(names).encode('ascii') + b'.'
        return bytes(pair), mnl, {
            'schema': 'fighter-moveset-selection-1', 'source_core': self.core,
            'motion_count': self.count, 'selections': dict(sorted(selections.items())),
            'motion_aliases': dict(sorted(aliases.items())),
            'pair_sha256': hashlib.sha256(pair).hexdigest(),
            'motion_names_sha256': hashlib.sha256(mnl).hexdigest(),
            'shared_move_parameters_preserved': True, 'runtime_ready': False,
        }


def compose_selected_cores(templates, resources):
    """Atomically emit motion cores, their proof table and required MNL aliases.

    An integer resource is explicit inheritance. An edited resource supplies
    its verified bank plus action selections. FMC2 records those selections;
    FMC3 additionally proves exactly four optional retail finisher slot choices.
    the native adapter must independently reconstruct and validate each pair.
    The caller must install the returned aliases in the corresponding bank.
    """
    from fighter_motion_compile import MotionCoreTemplates
    require(type(templates) is MotionCoreTemplates and type(resources) is dict and resources,
            'Selected cores require a verified motion template compiler')
    donors = {}
    slots = any(type(resource) is dict and 'finisher_slots' in resource for resource in resources.values())
    for identifier, resource in resources.items():
        if type(resource) is int:
            donors[identifier] = resource
        else:
            require(type(resource) is dict and set(resource) in (
                {'donor', 'envelope', 'bank_sha256', 'selections'},
                {'donor', 'finisher_slots'},
                {'donor', 'envelope', 'bank_sha256', 'selections', 'finisher_slots'}),
                'Invalid selected-core resource')
            donors[identifier] = resource['donor']
    original, report = templates.compose(donors)
    data, proofs, plans = bytearray(original), [], {}
    for identifier, binding in report['bindings'].items():
        resource = resources[identifier]
        selected, count = [0xffff] * 130, 0
        if type(resource) is dict and 'selections' in resource:
            plan = MovesetPlan(templates.index, resource['donor'], resource['envelope'], resource['bank_sha256'])
            pair, names, receipt = plan.compose(resource['selections'])
            start = binding['parameters_offset'] - 8
            data[start:start + 860] = pair
            count = receipt['motion_count']
            for target, source in receipt['selections'].items():
                selected[target] = source
            plans[identifier] = receipt
        choices = [0xffffffff] * 4
        if type(resource) is dict and 'finisher_slots' in resource:
            edits = resource['finisher_slots']
            require(type(edits) is dict and 0 < len(edits) <= 4
                    and all(type(slot) is int and 0 <= slot < 4 and type(choice) is int
                            and 0 <= choice < 82 for slot, choice in edits.items()),
                    'Finisher slots need explicit slot 0..3 and retail choice 0..81')
            offset = binding['parameters_offset']
            packed = PackedRecord.decode('core', bytes(data[offset:offset + 64]))
            values = list(packed.values)
            for slot, choice in edits.items():
                values[88 + slot] = choices[slot] = choice
            data[offset:offset + 64] = PackedRecord('core', tuple(values), packed.tail).encode()
            report.setdefault('finisher_slots', {})[identifier] = dict(sorted(edits.items()))
            if identifier in plans:
                plans[identifier]['pair_sha256'] = hashlib.sha256(data[offset - 8:offset + 852]).hexdigest()
        row = struct.pack('<5I130H', binding['descriptor_index'], binding['parameters_offset'],
                          binding['actions_offset'], binding['inherited_bank_number'], count, *selected)
        proofs.append(row + struct.pack('<4I', *choices) if slots else row)
    data = bytes(data)
    report.update(schema='fighter-motion-core-selections-1',
                  behavior_policy='verified-same-bank-action-selections',
                  sha256=hashlib.sha256(data).hexdigest(), selections=plans)
    if slots:
        report.update(schema='fighter-motion-core-selections-2',
                      behavior_policy='verified-action-and-finisher-slot-selections')
    table = ((b'FMC3' if slots else b'FMC2') + struct.pack('<5I', 3 if slots else 2, report['original_core_count'], len(proofs), len(data), 0)
             + hashlib.sha256(data).digest() + b''.join(proofs))
    return data, report, table
