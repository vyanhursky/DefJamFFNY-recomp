"""Inspect the bounded native RM command/parameter relationship.

The native 114FE0 dispatcher consumes high16 opcode / low16 word-count tokens,
terminated by zero, with a separate parameter cursor starting at wrapper+4.
This reader does not execute programs or authorize their imports/shaders. State
can be inherited between RMs; validation of one RM is not a runtime capability.
"""
from bisect import bisect_left
from dataclasses import dataclass
import hashlib

from fighter_elf import Model, ModelError

MAX_PROGRAM_WORDS = 16384
# Arity and parameter consumption independently traced through native table
# 2e56f0. In particular op4 consumes no pair, whereas op1 skips one pair.
ARITY = {1: 1, 2: 2, 3: 2, 4: 2, 5: 4, 6: 4, 9: 4, 14: 2, 15: 3,
         16: 2, 20: 3, 25: 3, 26: 3, 29: 6, 31: 2, 35: 4}
NO_PAIR = {4, 25, 26}


def require(condition, message):
    if not condition:
        raise ModelError(message)


@dataclass(frozen=True)
class Command:
    opcode: int
    arguments: tuple
    parameter: int | None


class RenderProgram:
    def __init__(self, model, rm):
        require(isinstance(model, Model), 'Render program requires a validated model envelope')
        model.data_range(rm, 0x3c)
        require(model.local_pointer(rm + 0x38, 4) == rm, 'Render wrapper does not reference its RM')
        start, end = model.local_pointer(rm, 4), model.local_pointer(rm + 8, 4)
        require(start % 4 == end % 4 == 0 and 4 <= end - start <= MAX_PROGRAM_WORDS * 4,
                'Render program has invalid bounds')
        relocations = sorted(model.pointers)

        def scalar(at, size):
            file_at = model.data_range(at, size)
            index = bisect_left(relocations, at)
            require(index == len(relocations) or relocations[index] >= at + size,
                    'Render command/scalar contains a pointer relocation')
            return file_at

        file_at = scalar(start, end - start)
        self.sha256 = hashlib.sha256(model.data[file_at:file_at + end - start]).hexdigest()
        commands, cursor, parameter = [], start, rm + 0x3c
        while cursor < end:
            word, = model.data_words(cursor, 1)
            if not word:
                require(cursor + 4 == end, 'Render program has trailing words after its terminator')
                break
            opcode, width = word >> 16, word & 65535
            require(opcode in ARITY and width == ARITY[opcode] and cursor + width * 4 < end,
                    'Unsupported/truncated render opcode or argument count')
            arguments = model.data_words(cursor + 4, width - 1)
            pair = None
            if opcode not in NO_PAIR:
                model.data_range(parameter, 8)
                if opcode != 1:
                    scalar(parameter, 4)
                    require(parameter + 4 in model.pointers, 'Render parameter has no explicit pointer binding')
                pair = parameter
                parameter += 8
            commands.append(Command(opcode, arguments, pair))
            cursor += width * 4
        else:
            raise ModelError('Render program has no terminator')
        require(commands, 'Empty render program')
        self.commands, self.parameter_end = tuple(commands), parameter

    def matching(self, opcode):
        return tuple(command for command in self.commands if command.opcode == opcode)

    def metadata(self):
        return {'sha256': self.sha256, 'opcodes': [command.opcode for command in self.commands],
                'command_parameters_validated': False, 'runtime_ready': False}
