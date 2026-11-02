"""Runtime-owned native menu presentation compiler.

Only verified original movies are inputs. Packages provide typed presentation
data, never bytecode. Existing visual methods are cloned with literal
getThumbID calls and relocated branches; ControllerSetup keeps getID. A
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
    def __init__(self, base, *, continuation=False):
        if base % 4 and not continuation:
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
        elif 0 <= value <= 127: self.op('EA_PushByte'); self.code.append(value)
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


def character_parameters(record):
    """Typed native CCharacter data. No display text or executable input here."""
    if not isinstance(record, dict) or set(record) != {'selection_key', 'stats', 'styles'}:
        raise AssetError('Invalid logical menu fighter fields')
    identity, stats, styles = record['selection_key'], record['stats'], record['styles']
    if type(identity) is not int or not 100 <= identity <= 0x7fffffff:
        raise AssetError('Invalid logical menu identity')
    if not isinstance(stats, dict) or set(stats) != set('ULSTHC') \
            or any(type(value) is not int or not 0 <= value <= 100 for value in stats.values()):
        raise AssetError('Invalid logical menu stats')
    if not isinstance(styles, list) or not 1 <= len(styles) <= 5 \
            or any(type(value) is not int or not 0 <= value < 5 for value in styles) or len(set(styles)) != len(styles):
        raise AssetError('Invalid logical menu styles')
    return (f'CLOTH=1&FE_ID={identity}&LOCK=1' + ''.join(f'&{key}={stats[key]}' for key in 'ULSTHC')
            + ''.join(f'&K={value}' for value in styles))


def append_logical_roster(action, definitions, records):
    if len([d for d in definitions if d['name'] == 'getCharData' and not d['params']]) != 1:
        raise AssetError('Native character-list constructor differs from the reviewed template')
    action.string('_recompFighterData'); action.integer(0); action.string('Array'); action.op('NewObject'); action.op('SetVariable')
    for index, record in enumerate(records):
        action.variable('_recompFighterData'); action.integer(index); action.string(character_parameters(record)); action.op('SetMember')
    def append():
        done, loop, grids, next_grid, grid_loop = [action.unique() for _ in range(5)]
        action.local('_chars', lambda: action.variable('aCharacters'))
        action.variable('_chars'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
        action.variable('_chars'); action.member('_recompFighterRoster'); action.op('EA_PushTrue'); action.op('Equals2'); action.branch('BranchIfTrue', done)
        action.variable('_chars'); action.string('_recompFighterRoster'); action.op('EA_PushTrue'); action.op('SetMember')
        action.local('_i', lambda: action.integer(0))
        action.label(loop)
        action.variable('_i'); action.variable('_recompFighterData'); action.member('length'); action.op('LessThan2'); action.op('Not'); action.branch('BranchIfTrue', grids)
        action.variable('_recompFighterData'); action.variable('_i'); action.op('GetMember')
        action.integer(1); action.string('CCharacter'); action.op('NewObject')
        action.integer(1); action.variable('_chars'); action.string('push'); action.op('CallMethod'); action.op('Pop')
        action.string('_i'); action.variable('_i'); action.op('Increment'); action.op('SetVariable'); action.branch('BranchAlways', loop)
        action.label(grids)
        action.variable('aThumbGrids'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
        action.string('_i'); action.integer(0); action.op('SetVariable')
        action.label(grid_loop)
        action.variable('_i'); action.variable('aThumbGrids'); action.member('length'); action.op('LessThan2'); action.op('Not'); action.branch('BranchIfTrue', done)
        action.local('_grid', lambda: (action.variable('aThumbGrids'), action.variable('_i'), action.op('GetMember')))
        action.variable('_grid'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', next_grid)
        action.variable('_grid'); action.member('aCharacters'); action.variable('_chars'); action.op('Equals2'); action.op('Not'); action.branch('BranchIfTrue', next_grid)
        action.local('_count', lambda: (action.variable('_chars'), action.member('length')))
        has_created = action.unique()
        action.variable('_grid'); action.member('bHasCreatePlayer'); action.branch('BranchIfTrue', has_created)
        action.string('_count'); action.variable('_count'); action.op('Decrement'); action.op('SetVariable')
        action.label(has_created)
        action.variable('_grid'); action.string('iNumChars'); action.variable('_count'); action.op('SetMember')
        action.integer(0); action.variable('_grid'); action.string('redraw'); action.op('CallMethod'); action.op('Pop')
        action.label(next_grid)
        action.string('_i'); action.variable('_i'); action.op('Increment'); action.op('SetVariable'); action.branch('BranchAlways', grid_loop)
        action.label(done); action.op('EA_PushUndefined'); action.op('Return')
    action.function('_recompAppendFighters', [], append)
    action.string('_recompFighterGetCharData'); action.variable('getCharData'); action.op('SetVariable')
    def get_data():
        action.local('_result', lambda: (action.integer(0), action.string('_recompFighterGetCharData'), action.op('CallFunction')))
        action.integer(0); action.string('_recompAppendFighters'); action.op('CallFunction'); action.op('Pop')
        action.variable('_result'); action.op('Return')
    action.function('getCharData', [], get_data)
    action.integer(0); action.string('_recompAppendFighters'); action.op('CallFunction'); action.op('Pop')
    retain_ready_ownership(action, definitions)


def retain_ready_ownership(action, definitions):
    """Mirror the original selector's ready owners after its Back handler.

    The original handler also handles recursive unready/cancel transitions.
    Observe its completed CCharacter ownership instead of guessing which slot
    a controller was browsing, or changing any of the original input behavior.
    """
    if len([d for d in definitions if d['name'] == 'keyBackHandler' and d['params'] == ['nConID']]) != 1:
        raise AssetError('Native selector Back handler differs from the reviewed template')
    action.string('_recompFighterKeyBack'); action.variable('keyBackHandler'); action.op('SetVariable')
    def back():
        loop, next_char, owners, owner_loop, next_owner, done = [action.unique() for _ in range(6)]
        action.local('_chars', lambda: action.variable('aCharacters'))
        action.local('_result', lambda: (action.variable('nConID'), action.integer(1),
                                       action.string('_recompFighterKeyBack'), action.op('CallFunction')))
        action.variable('_chars'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
        action.local('_owners', lambda: (action.integer(0), action.string('Array'), action.op('NewObject')))
        action.local('_i', lambda: action.integer(0))
        action.label(loop)
        action.variable('_i'); action.variable('_chars'); action.member('length'); action.op('LessThan2'); action.op('Not'); action.branch('BranchIfTrue', owners)
        action.local('_char', lambda: (action.variable('_chars'), action.variable('_i'), action.op('GetMember')))
        action.variable('_recompFighterLabels'); action.integer(0); action.variable('_char'); action.string('getID'); action.op('CallMethod'); action.op('GetMember')
        action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', next_char)
        action.local('_owner', lambda: (action.variable('_char'), action.member('iTakenBy')))
        action.variable('_owner'); action.integer(0); action.op('LessThan2'); action.branch('BranchIfTrue', next_char)
        action.variable('_owner'); action.integer(4); action.op('LessThan2'); action.op('Not'); action.branch('BranchIfTrue', next_char)
        action.variable('_owners'); action.variable('_owner'); action.op('EA_PushTrue'); action.op('SetMember')
        action.label(next_char)
        action.string('_i'); action.variable('_i'); action.op('Increment'); action.op('SetVariable'); action.branch('BranchAlways', loop)
        action.label(owners)
        action.string('_i'); action.integer(0); action.op('SetVariable')
        action.local('_mask', lambda: action.integer(0)); action.local('_bit', lambda: action.integer(1))
        action.label(owner_loop)
        action.variable('_i'); action.integer(4); action.op('LessThan2'); action.op('Not'); action.branch('BranchIfTrue', done + '-send')
        action.variable('_owners'); action.variable('_i'); action.op('GetMember'); action.op('Not'); action.branch('BranchIfTrue', next_owner)
        action.string('_mask'); action.variable('_mask'); action.variable('_bit'); action.op('Add2'); action.op('SetVariable')
        action.label(next_owner)
        action.string('_bit'); action.variable('_bit'); action.integer(2); action.op('Multiply'); action.op('SetVariable')
        action.string('_i'); action.variable('_i'); action.op('Increment'); action.op('SetVariable'); action.branch('BranchAlways', owner_loop)
        action.label(done + '-send')
        action.string('Fighters.KeepReady('); action.variable('_mask'); action.op('Add2'); action.string(')'); action.op('Add2')
        action.integer(1); action.variable('_level0'); action.member('_root'); action.string('FuncCall'); action.op('CallMethod'); action.op('Pop')
        action.label(done); action.variable('_result'); action.op('Return')
    action.function('keyBackHandler', ['nConID'], back)


def presentation_action(base, movie, constants, pairs, names, records=None):
    entry, entries, definitions = functions(movie, constants)
    updated_constants = constants
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
        # selectChar also uses getID to recognize the created-player identity.
        # Preserve that semantic comparison even when artwork is borrowed. A
        # original operand and pool are preserved for this identity comparison.
        semantic = [ins for i, ins in enumerate(body[:-3]) if ins in references
                    and body[i + 1].name == 'CallMethod'
                    and any("='CHAR_HERO'" in operand for operand in body[i + 2].operands)
                    and body[i + 3].name == 'Equals2']
        if definition['method'] == 'selectChar' and len(semantic) != 1:
            raise AssetError('Created-player identity comparison differs from the reviewed template')
        redirected = {ins.offset for ins in references if ins not in semantic}
        if any(ins.name not in ('EA_PushConstantByte', 'EA_PushConstantWord') for ins in references):
            raise AssetError('Unreviewed native thumbnail getter instruction')
        definition = dict(definition, instructions=body, redirected=redirected)
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
        # Bind the original pool while registering the function, as the native
        # movie does; invoked methods must not rewrite ambient pool state.
        action.constant_pool(definition['pool'])
        def cloned(definition=definition):
            instructions = definition['instructions']
            end = definition['start'] + definition['size']
            labels = {offset: action.unique() for offset in [ins.offset for ins in instructions] + [end]}
            for index, ins in enumerate(instructions):
                action.label(labels[ins.offset])
                if ins.offset in definition['redirected']:
                    action.string('getThumbID')
                elif ins.branch_target is not None:
                    if ins.branch_target not in labels: raise AssetError('Thumbnail branch targets an instruction interior')
                    action.branch(ins.name, labels[ins.branch_target])
                else:
                    following = instructions[index + 1].offset if index + 1 < len(instructions) else end
                    action.code += movie[ins.offset:following]
            action.label(labels[end])
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
    if records is not None:
        append_logical_roster(action, definitions, records)
    return action.finish(), updated_constants, entry, [definition['method'] for definition in visual]


def compile_menu(movie, constants, pairs, names, records=None):
    if not 8 <= len(movie) <= MAX_MOVIE or movie[:8] != b'Apt Data' or len(constants) > MAX_MOVIE:
        raise AssetError('Invalid selector input budget')
    if set(pairs) != set(names) or not 0 < len(pairs) <= 16384:
        raise AssetError('Invalid selector presentation bindings')
    if any(type(identity) is not int or not 100 <= identity <= 0x7fffffff
           or type(donor) is not int or not 0 <= donor < 100 for identity, donor in pairs.items()):
        raise AssetError('Selector bindings must separate custom identities and retail artwork')
    if records is not None:
        if not isinstance(records, list) or len(records) != len(pairs):
            raise AssetError('Logical roster must cover exactly the presentation identities')
        for record in records: character_parameters(record)
        if {record['selection_key'] for record in records} != set(pairs):
            raise AssetError('Logical roster must cover exactly the presentation identities')
        records = sorted(records, key=lambda row: row['selection_key'])
    output = bytearray(movie); output += bytes(-len(output) % 4)
    code, constants, entry, methods = presentation_action(len(output), movie, constants, pairs, names, records)
    action_at = len(output); output += code; output += bytes(-len(output) % 4)
    record_at = len(output); output += struct.pack('<II', 1, action_at)
    frames = struct.unpack_from('<I', movie, entry + 12)[0]
    count, pointers = struct.unpack_from('<II', movie, frames)
    if count > 16384 or pointers + count * 4 > len(movie): raise AssetError('Invalid first-frame item list')
    list_at = len(output); output += movie[pointers:pointers + count * 4] + struct.pack('<I', record_at)
    struct.pack_into('<II', output, frames, count + 1, list_at)
    if len(output) > MAX_MOVIE: raise AssetError('Composed selector exceeds movie budget')
    return bytes(output), constants, {'methods': methods, 'action_offset': action_at}
