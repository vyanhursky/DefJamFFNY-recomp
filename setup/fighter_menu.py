"""Runtime-owned native menu presentation compiler.

Only verified original movies are inputs. Packages provide typed presentation
data, never bytecode. Existing visual methods are retained with a function-local
constant-pool remap from getID to getThumbID; ControllerSetup keeps getID. A
small generated action supplies the donor mapping and native name text fields.
No original instruction/branch or asset pointer is relocated in place.
"""
import re
import struct

import fighter_apt as apt
from fighter_assets import AssetError

OPS = {name: value for value, name in apt.OPNAMES.items()}
MAX_MOVIE = 16 * 1024**2


def put_word(data, at, value):
    struct.pack_into('<I', data, at, value)


class Action:
    """Small assembler for code owned by this runtime, with literal data fixups."""
    def __init__(self, base):
        if base % 4:
            raise AssetError('Action base must be aligned')
        self.base, self.code, self.literals, self.lists, self.branches, self.labels = base, bytearray(), [], [], [], {}
        self.serial = 0

    @property
    def position(self):
        return self.base + len(self.code)

    def align(self):
        self.code += bytes(-self.position % 4)

    def op(self, name):
        self.code.append(OPS[name])
        if name in apt.ALIGNED:
            self.align()

    def word(self, value):
        self.code += struct.pack('<I', value)

    def text_pointer(self, text):
        self.literals.append((len(self.code), text))
        self.word(0)

    def string(self, text):
        self.op('EA_PushString'); self.text_pointer(text)

    def integer(self, value):
        if value == 0: self.op('EA_PushZero')
        elif value == 1: self.op('EA_PushOne')
        elif 0 <= value <= 255: self.op('EA_PushByte'); self.code.append(value)
        else: self.op('EA_PushLong'); self.word(value)

    def variable(self, name):
        self.string(name); self.op('GetVariable')

    def member(self, name):
        self.string(name); self.op('GetMember')

    def local(self, name, emitter):
        self.string(name); emitter(); self.op('DefineLocal')

    def branch(self, name, label):
        self.op(name); self.branches.append((len(self.code), label)); self.word(0)

    def label(self, name):
        if name in self.labels: raise AssetError('Duplicate action label')
        self.labels[name] = len(self.code)

    def unique(self):
        self.serial += 1
        return 'branch-' + str(self.serial)

    def function(self, name, params, emitter):
        self.op('DefineFunction'); self.text_pointer(name); self.word(len(params))
        if params:
            self.lists.append((len(self.code), tuple(params), True)); self.word(0)
        else: self.word(0)
        size_at = len(self.code); self.word(0)
        self.word(0x98765432); self.word(0x12345678)
        start = len(self.code); emitter()
        put_word(self.code, size_at, len(self.code) - start)

    def constant_pool(self, values):
        self.op('ConstantPool'); self.word(len(values))
        self.lists.append((len(self.code), tuple(values), False)); self.word(0)

    def method(self, owner, method, params, emitter):
        self.variable(owner); self.member('prototype'); self.string(method)
        self.function('', params, emitter); self.op('SetMember')

    def finish(self):
        self.op('End')
        for at, label in self.branches:
            if label not in self.labels: raise AssetError('Unresolved action branch')
            struct.pack_into('<i', self.code, at, self.labels[label] - (at + 4))
        for at, values, strings in self.lists:
            self.align(); put_word(self.code, at, self.position)
            for value in values:
                if strings: self.text_pointer(value)
                else: self.word(value)
        for at, value in self.literals:
            if not isinstance(value, str) or '\0' in value or len(value.encode('utf-8')) > 65536:
                raise AssetError('Invalid generated menu literal')
            put_word(self.code, at, self.position)
            self.code += value.encode('utf-8') + b'\0'
        if len(self.code) > MAX_MOVIE:
            raise AssetError('Generated menu exceeds byte budget')
        return bytes(self.code)


def add_string_constant(data, text):
    """Append a constant entry, preserving the old string payloads verbatim."""
    _, entries = apt.parse_const(data)
    at, string_cells = 32, []
    for entry in entries:
        if entry.type == 1: string_cells.append(at + 4)
        at += 4 if entry.type == 3 else 8
    if at > len(data) or any(struct.unpack_from('<I', data, cell)[0] < at for cell in string_cells):
        raise AssetError('Unsupported constant string storage')
    result = bytearray(data[:at] + struct.pack('<II', 1, len(data) + 8) + data[at:] + text.encode('ascii') + b'\0')
    put_word(result, 24, len(entries) + 1)
    for cell in string_cells:
        put_word(result, cell, struct.unpack_from('<I', data, cell)[0] + 8)
    return bytes(result), len(entries)


def functions(movie, constants):
    """Find top-level definitions while keeping each function's pool separate."""
    entry, entries = apt.parse_const(constants)
    record = apt.parse_character(movie, entry)
    if record['type'] != 'Movie' or not record['frames']:
        raise AssetError('Unsupported native selector movie')
    found, history = [], []
    for kind, item in record['frames'][0]:
        if kind != 'Action': continue
        at, pool = item['instructions_at'], []
        while at < len(movie):
            ins, following, end, confirmed = apt.parse_instruction(movie, at, entries, pool)
            if not confirmed: raise AssetError('Selector uses an undecoded instruction: ' + ins.name)
            if ins.function_size is not None:
                def value(instruction):
                    if instruction.name == 'EA_PushString':
                        return apt.read_cstr(movie, struct.unpack_from('<I', movie, apt.align4(instruction.offset + 1))[0])
                    return entries[int(re.search(r'const\[(\d+)\]', ' '.join(instruction.operands)).group(1))].value
                owner, method = None, None
                if len(history) >= 4 and history[-2].name == 'GetMember':
                    try:
                        owner_instruction = history[-5] if history[-4].name == 'GetVariable' else history[-4]
                        owner, prototype, method = value(owner_instruction), value(history[-3]), value(history[-1])
                        if prototype != 'prototype': owner = None
                    except (AttributeError, IndexError): pass
                header = apt.align4(at + 1)
                name = apt.read_cstr(movie, struct.unpack_from('<I', movie, header)[0])
                count, params_at = struct.unpack_from('<II', movie, header + 4)
                if count > 32 or following + ins.function_size > len(movie): raise AssetError('Invalid selector function')
                params = [apt.read_cstr(movie, struct.unpack_from('<I', movie, params_at + i * 4)[0]) for i in range(count)]
                found.append({'owner': owner, 'method': method, 'name': name, 'params': params, 'pool': tuple(pool),
                              'start': following, 'size': ins.function_size})
                following += ins.function_size
            history.append(ins)
            at = following
            if end: break
    return entry, entries, found


def presentation_action(base, movie, constants, pairs, names):
    entry, entries, definitions = functions(movie, constants)
    updated_constants, getter_index = add_string_constant(constants, 'getThumbID')
    getter = next((i for i, entry in enumerate(entries) if entry.value == 'getID'), None)
    visual = []
    for definition in definitions:
        if definition['owner'] != 'CThumbGrid': continue
        pool = list(definition['pool'])
        body = apt.disassemble_block(movie, definition['start'], entries, definition['size'], pool)
        references = [ins for ins in body if any(f'const[{getter}]=' in value for value in ins.operands)]
        if not references: continue
        if definition['method'] not in ('redraw', 'selectChar', 'deselectChar'):
            raise AssetError('Unreviewed thumbnail identity consumer: ' + str(definition['method']))
        if any(ins.function_size is not None or ins.name in apt.ALIGNED - {'BranchAlways', 'BranchIfTrue'} for ins in body):
            raise AssetError('Thumbnail method needs pointer relocation')
        if any(ins.branch_target is not None and not definition['start'] <= ins.branch_target <= definition['start'] + definition['size'] for ins in body):
            raise AssetError('Thumbnail branch leaves its function')
        patched = bytearray(movie[definition['start']:definition['start'] + definition['size']])
        remapped = [getter_index if index == getter else index for index in pool]
        # selectChar also uses getID to recognize the created-player identity.
        # Preserve that semantic comparison even when artwork is borrowed. A
        # spare function-local pool slot keeps the operand/instruction width.
        semantic = [ins for i, ins in enumerate(body[:-3]) if ins in references
                    and body[i + 1].name == 'CallMethod'
                    and any("='CHAR_HERO'" in operand for operand in body[i + 2].operands)
                    and body[i + 3].name == 'Equals2']
        if definition['method'] == 'selectChar' and len(semantic) != 1:
            raise AssetError('Created-player identity comparison differs from the reviewed template')
        if semantic:
            byte_pool = {'EA_PushConstantByte', 'EA_PushValueOfVar', 'EA_GetNamedMember',
                         'EA_CallNamedFuncPop', 'EA_CallNamedFunc', 'EA_CallNamedMethodPop', 'EA_CallNamedMethod'}
            used = {movie[ins.offset + 1] for ins in body if ins.name in byte_pool}
            used.update(struct.unpack_from('<H', movie, ins.offset + 1)[0] for ins in body if ins.name == 'EA_PushConstantWord')
            spare = next((i for i in range(min(256, len(pool))) if i not in used), None)
            if spare is None or any(ins.name != 'EA_PushConstantByte' for ins in semantic):
                raise AssetError('Created-player comparison needs a wider menu relocation adapter')
            remapped[spare] = getter
            for ins in semantic: patched[ins.offset + 1 - definition['start']] = spare
        definition = dict(definition, pool=tuple(remapped), body=bytes(patched))
        visual.append(definition)
    if {definition['method'] for definition in visual} != {'redraw', 'selectChar', 'deselectChar'}:
        raise AssetError('Native thumbnail method set differs from the reviewed template')
    if len([d for d in definitions if d['name'] == 'updateChar' and d['params'] == ['nPlayer']]) != 1:
        raise AssetError('Native name update template differs')
    action = Action(base)
    for mapping, values in (('_recompFighterThumbs', pairs), ('_recompFighterLabels', names)):
        action.string(mapping); action.integer(0); action.string('Object'); action.op('NewObject'); action.op('SetVariable')
        for identity, value in sorted(values.items()):
            action.variable(mapping); action.integer(identity)
            action.integer(value) if type(value) is int else action.string(value)
            action.op('SetMember')
    def getter_body():
        action.local('_id', lambda: (action.integer(0), action.op('EA_PushThisVar'), action.string('getID'), action.op('CallMethod')))
        action.local('_donor', lambda: (action.variable('_recompFighterThumbs'), action.variable('_id'), action.op('GetMember')))
        fallback = action.unique()
        action.variable('_donor'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', fallback)
        action.variable('_donor'); action.op('Return')
        action.label(fallback); action.variable('_id'); action.op('Return')
    action.method('CCharacter', 'getThumbID', [], getter_body)
    for definition in visual:
        def cloned(definition=definition):
            action.constant_pool(definition['pool'])
            if action.position % 4 != definition['start'] % 4: raise AssetError('Thumbnail alignment changed')
            action.code += definition['body']
        action.method('CThumbGrid', definition['method'], definition['params'], cloned)
    action.string('_recompFighterUpdateChar'); action.variable('updateChar'); action.op('SetVariable')
    def update_name():
        action.variable('nPlayer'); action.integer(1); action.string('_recompFighterUpdateChar'); action.op('CallFunction'); action.op('Pop')
        action.local('_char', lambda: (action.integer(0), action.variable('aThumbGrids'), action.variable('nPlayer'), action.op('GetMember'), action.string('getSelectedChar'), action.op('CallMethod')))
        action.local('_label', lambda: (action.variable('_recompFighterLabels'), action.integer(0), action.variable('_char'), action.string('getID'), action.op('CallMethod'), action.op('GetMember')))
        done = action.unique()
        action.variable('_label'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
        action.local('_field', lambda: (action.string('szFighterName'), action.variable('nPlayer'), action.op('Add2'), action.op('GetVariable')))
        action.variable('_field'); action.string('text'); action.variable('_label'); action.op('SetMember')
        action.variable('_field'); action.string('_visible'); action.op('EA_PushTrue'); action.op('SetMember')
        action.label(done); action.op('EA_PushUndefined'); action.op('Return')
    action.function('updateChar', ['nPlayer'], update_name)
    return action.finish(), updated_constants, entry, [definition['method'] for definition in visual]


def compile_menu(movie, constants, pairs, names):
    if not 8 <= len(movie) <= MAX_MOVIE or movie[:8] != b'Apt Data' or len(constants) > MAX_MOVIE:
        raise AssetError('Invalid selector input budget')
    if set(pairs) != set(names) or not 0 < len(pairs) <= 16384:
        raise AssetError('Invalid selector presentation bindings')
    if any(type(identity) is not int or not 100 <= identity <= 0x7fffffff
           or type(donor) is not int or not 0 <= donor < 100 for identity, donor in pairs.items()):
        raise AssetError('Selector bindings must separate custom identities and retail artwork')
    output = bytearray(movie); output += bytes(-len(output) % 4)
    code, constants, entry, methods = presentation_action(len(output), movie, constants, pairs, names)
    action_at = len(output); output += code; output += bytes(-len(output) % 4)
    record_at = len(output); output += struct.pack('<II', 1, action_at)
    frames = struct.unpack_from('<I', movie, entry + 12)[0]
    count, pointers = struct.unpack_from('<II', movie, frames)
    if count > 16384 or pointers + count * 4 > len(movie): raise AssetError('Invalid first-frame item list')
    list_at = len(output); output += movie[pointers:pointers + count * 4] + struct.pack('<I', record_at)
    struct.pack_into('<II', output, frames, count + 1, list_at)
    if len(output) > MAX_MOVIE: raise AssetError('Composed selector exceeds movie budget')
    return bytes(output), constants, {'methods': methods, 'action_offset': action_at}
