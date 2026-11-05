"""Typed, bounded motion-index edges established from native consumers.

This validates index relationships, not animation curves, events or gameplay
semantics. It grants no runtime admission. Native core descriptors, action
slots, primary/secondary move rows and parameter rows are separate namespaces.
"""
from dataclasses import dataclass
import struct

from fighter_assets import AssetError


def require(value, message):
    if not value:
        raise AssetError(message)


@dataclass(frozen=True)
class Action:
    move_word: int
    local_start: int
    parameter_base: int

    @property
    def primary_move(self):
        return None if self.move_word == 0xffff else self.move_word & 0xfff

    @property
    def flags(self):
        return self.move_word & 0xf000


class MotionLinks:
    def __init__(self, index):
        from fighter_motion import MotionIndex
        require(type(index) is MotionIndex, 'Expected a validated motion index')
        self.index = index
        self.actions = [tuple(Action(*struct.unpack_from('<3H', index.data, start + 72 + row * 6))
                              for row in range(130)) for start in index.core_spans]
        self.move_edges = []
        for partition in (0, 1):
            edges = []
            for ordinal in range(index.tables[partition]['move_count']):
                decoded = index.record('move', ordinal, partition).native_bytes()
                target, = struct.unpack_from('<H', decoded, 0x3c)
                require(target < index.tables[0]['move_count'],
                        f'Move partition {partition} row {ordinal} +3c exceeds the primary move table')
                edges.append(target)
            self.move_edges.append(tuple(edges))
        for core, rows in enumerate(self.actions):
            for ordinal, row in enumerate(rows):
                require(row.primary_move is None or row.primary_move < index.tables[0]['move_count'],
                        f'Core {core} action {ordinal} exceeds the primary move table')

    def action(self, core, ordinal):
        require(type(core) is int and 0 <= core < len(self.actions), 'Core index exceeds its namespace')
        require(type(ordinal) is int and 0 <= ordinal < 130, 'Action index exceeds its namespace')
        return self.actions[core][ordinal]

    def external_row(self, kind, identifier):
        require(kind in ('move', 'parameter'), 'Unknown external motion table')
        require(type(identifier) is int and identifier >= 10000, 'External motion ID needs its explicit prefix')
        ordinal = identifier - 10000
        require(ordinal < self.index.tables[1][kind + '_count'],
                'External motion ID exceeds its own table count')
        return ordinal

    def primary_parameter(self, core, local_id, *, state=0, actor_flags=0, move_link=0):
        """Native1A7F30 after its participant routing, with checked row access.

        Rows2..124 supply boundaries; row125 supplies synthetic bound1000.
        The state65 exception uses actor+91A and signed WAZA+3A (actor+FA6).
        It is modeled explicitly, not generalized into an animation link.
        """
        self.action(core, 0)
        require(type(local_id) is int and 0 <= local_id < 1000, 'Local motion ID exceeds its namespace')
        require(type(state) is int and 0 <= state <= 0xffffffff
                and type(actor_flags) is int and 0 <= actor_flags <= 255
                and type(move_link) is int and -32768 <= move_link <= 32767,
                'Invalid motion scan actor state')
        previous, lower = 1, 0
        for candidate in range(2, 126):
            boundary = self.actions[core][candidate].local_start if candidate < 125 else 1000
            if local_id < boundary:
                delta = local_id - lower
                ordinal = self.actions[core][previous].parameter_base + delta
                if delta >= 2 and state == 65:
                    ordinal = move_link - (((actor_flags & 4) | 8) >> 2) + delta
                require(0 <= ordinal < self.index.tables[0]['parameter_count'],
                        'Motion scan exceeds the primary parameter table')
                return ordinal
            if boundary > lower:
                lower, previous = boundary, candidate
            elif boundary == lower and self.actions[core][candidate].move_word != 0xffff:
                previous = candidate
        raise AssetError('Motion scan did not reach its terminal boundary')

    def metadata(self):
        return {'core_count': len(self.actions), 'action_rows_per_core': 130,
                'primary_move_edges': sum(row.primary_move is not None for rows in self.actions for row in rows),
                'move_tail_edges': sum(map(len, self.move_edges)),
                'boundary_rows': [2, 124], 'synthetic_terminal_row': 125,
                'runtime_ready': False, 'animation_links_validated': False,
                'event_links_validated': False}
