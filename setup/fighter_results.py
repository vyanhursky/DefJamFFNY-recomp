"""Runtime-owned presentation for the original native match-summary movies.

The native result formatter supplies full logical IDs. Original result portraits
are aliased separately. This adapter supplies bounded custom name fields,
keeping retail/created presentation and statistics intact.
Packages supply labels, never ActionScript or replacement movies.
"""
import struct
import textwrap

import fighter_apt as apt
from fighter_assets import AssetError
from fighter_menu import Action, MAX_MOVIE


def apply_label(action, lines=0,logos=False):
    """Use the timeline's variable scope, as its original name action does."""
    done = action.unique()
    for index in range(lines):
        action.variable('_recompResultLine' + str(index)); action.string('text'); action.string(''); action.op('SetMember')
    if logos:
        fallback=action.unique()
        action.variable('_recompResultHasLogo');action.op('EA_PushUndefined');action.op('Equals2');action.branch('BranchIfTrue',fallback)
        action.variable('szFighterNameMov');action.string('text');action.string('');action.op('SetMember')
        action.variable('szFighterNameMov');action.string('_visible');action.op('EA_PushFalse');action.op('SetMember')
        action.string('_parent.logoLoader');action.variable('_recompResultPlayer');action.integer(1);action.op('Add2');action.op('Add2');action.op('GetVariable')
        action.string('_visible');action.op('EA_PushTrue');action.op('SetMember');action.branch('BranchAlways',done)
        action.label(fallback)
    action.variable('_recompResultLabel')
    action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
    action.variable('szFighterNameMov'); action.string('text')
    if lines: action.string('')
    else: action.variable('_recompResultLabel')
    action.op('SetMember')
    for index in range(lines):
        action.variable('_recompResultLine' + str(index)); action.string('text')
        action.variable('_recompResultLines' + str(index)); action.variable('_recompResultID'); action.op('GetMember'); action.op('SetMember')
    action.variable('szFighterNameMov'); action.string('_visible'); action.op('EA_PushTrue'); action.op('SetMember')
    action.string('_parent.logoLoader'); action.variable('_recompResultPlayer'); action.integer(1); action.op('Add2'); action.op('Add2'); action.op('GetVariable')
    action.string('_visible'); action.op('EA_PushFalse'); action.op('SetMember')
    action.label(done)


def append_name_fields(output, movie, root, panel, participants):
    """Give custom result labels two bounded lines inside the native header.

    The result panel is instantiated once per participant. Each instance owns
    its text bindings; the original field and all score/portrait records stay
    intact, including the four-player timeline's later field replacement.
    """
    characters = apt.read_characters_list(movie, root)
    count, pointers = root['_characters_ptr_list']
    frames_at = struct.unpack_from('<I', movie, panel['offset'] + 12)[0]
    item_count, items_at = struct.unpack_from('<II', movie, frames_at)
    source = None
    for offset in struct.unpack_from('<' + 'I' * item_count, movie, items_at):
        kind, item = apt.parse_frame_item(movie, offset)
        if kind == 'PlaceObject' and item.get('name') == 'szFighterNameMov':
            if source is not None: raise AssetError('Duplicate result name field')
            source = dict(item, record_offset=offset)
    if source is None or source['flags'] != 38 or source['matrix'] is None or source['clip_events'] \
            or source['character'] is None or not 0 <= source['character'] < count:
        raise AssetError('Native result name placement differs from the reviewed template')
    record = characters[source['character']]
    if not record or record['type'] != 'Text' or not record['sig_ok']:
        raise AssetError('Native result name Text record differs')
    start, placement = record['offset'], source['record_offset']
    if start + 60 > len(movie) or placement + 64 > len(movie) or struct.unpack_from('<I', movie, placement + 60)[0]:
        raise AssetError('Native result name record exceeds its bounds')
    font, alignment, _, original_height = struct.unpack_from('<IIIf', movie, start + 24)
    if not 0 <= font < count or characters[font] is None or characters[font]['type'] != 'Font' \
            or alignment != 0 or original_height != {2: 26, 3: 26, 4: 20}[participants]:
        raise AssetError('Native result name font differs from the reviewed template')
    depth = max(item['depth'] for frame in panel['frames'] for kind, item in frame if kind == 'PlaceObject') + 1
    if count + 2 > 16384 or depth + 2 > 16384:
        raise AssetError('Native result name field budget exceeded')
    width, height = {2: (190, 14), 3: (116, 12), 4: (90, 9)}[participants]
    added, placements = [], []
    for index in range(2):
        added.append(len(output)); output += movie[start:start + 60]
        struct.pack_into('<4f', output, added[-1] + 8, -2, -2, width, height + 4)
        struct.pack_into('<f', output, added[-1] + 36, height)
        name_at = len(output); output += ('_recompResultLine' + str(index)).encode('ascii') + b'\0'
        binding_at = len(output); output += ('_recompResultText' + str(index)).encode('ascii') + b'\0'
        output += bytes(-len(output) % 4)
        struct.pack_into('<I', output, added[-1] + 56, binding_at)
        placements.append(len(output)); output += movie[placement:placement + 64]
        struct.pack_into('<II', output, placements[-1] + 8, depth + index, count + index)
        struct.pack_into('<6f', output, placements[-1] + 16, 1, 0, 0, 1, source['matrix'][4], source['matrix'][5] + index * (height + 2))
        struct.pack_into('<I', output, placements[-1] + 52, name_at)
    list_at = len(output); output += movie[pointers:pointers + count * 4] + struct.pack('<2I', *added)
    struct.pack_into('<II', output, root['offset'] + 20, count + 2, list_at)
    return placements


def scan_action(movie, start, entries):
    at, pool, instructions = start, [], []
    while at < len(movie):
        ins, following, end, confirmed = apt.parse_instruction(movie, at, entries, pool)
        if not confirmed:
            raise AssetError('Result action uses an undecoded instruction: ' + ins.name)
        instructions.append(ins)
        if ins.function_size is not None:
            following += ins.function_size
        if not at < following <= len(movie):
            raise AssetError('Invalid result action bounds')
        if end:
            boundaries = {item.offset for item in instructions}
            if any(item.branch_target is not None and item.branch_target not in boundaries for item in instructions):
                raise AssetError('Result action branch leaves its instruction block')
            return instructions, at
        at = following
    raise AssetError('Unterminated result action')


def compile_results(movie, constants, names, *, participants=None,logos=()):
    if participants is not None and (type(participants) is not int or participants not in (2, 3, 4)):
        raise AssetError('Invalid native result participant layout')
    if not 8 <= len(movie) <= MAX_MOVIE or movie[:8] != b'Apt Data' or len(constants) > MAX_MOVIE:
        raise AssetError('Invalid result movie budget')
    if not isinstance(names, dict) or not 0 < len(names) <= 16384 \
            or any(type(key) is not int or not 100 <= key <= 0x7fffffff for key in names) \
            or any(not isinstance(label, str) or '\0' in label or len(label.encode('utf-8')) > 65536 for label in names.values()):
        raise AssetError('Invalid result labels')
    if type(logos) not in (set,frozenset,tuple,list) or not set(logos)<=set(names):
        raise AssetError('Authored result logos need owned identities')
    text_names={key:value for key,value in names.items() if key not in logos}
    entry, entries = apt.parse_const(constants)
    record = apt.parse_character(movie, entry)
    if record['type'] != 'Movie':
        raise AssetError('Unsupported result movie')
    found = []
    for character in apt.read_characters_list(movie, record):
        if not character or character['type'] != 'Sprite' or not character['frames']:
            continue
        actions = [(item, *scan_action(movie, item['instructions_at'], entries))
                   for kind, item in character['frames'][0] if kind == 'Action']
        initial = [row for row in actions if any("='Game.GetMatchSummary('" in str(ins.operands) for ins in row[1])]
        text_frames = [index for index, frame in enumerate(character['frames'])
                       if any(kind == 'PlaceObject' and item.get('name') == 'szFighterNameMov' for kind, item in frame)]
        if initial:
            if len(initial) != 1 or not 1 <= len(text_frames) <= 4:
                raise AssetError('Unreviewed result label timeline')
            found.append((character, initial[0], text_frames))
    if len(found) != 1:
        raise AssetError('Native result panel differs from the reviewed template')
    character, (initial, instructions, end), text_frames = found[0]
    start = initial['instructions_at']
    fills = [ins for ins in instructions if ins.function_size is not None
             and "name='fillStats' params=(playerId)" in ' '.join(ins.operands)]
    if len(fills) != 1:
        raise AssetError('Native result fillStats function differs from the reviewed template')
    output = bytearray(movie); output += bytes(-len(output) % 4)
    placements, wrapped = [], None
    if participants is not None:
        wrapped = {key: textwrap.wrap(label, width={2: 14, 3: 10, 4: 10}[participants], break_on_hyphens=False)
                   for key, label in text_names.items()}
        if any(len(lines) > 2 for lines in wrapped.values()):
            raise AssetError('Native result name exceeds the fitted line budget')
        placements = append_name_fields(output, movie, record, character, participants)
    lines = 2 if wrapped is not None else 0
    wrapper_at = len(output)
    action = Action(wrapper_at)
    action.string('_recompResultNames'); action.integer(0); action.string('Object'); action.op('NewObject'); action.op('SetVariable')
    for identity, label in sorted(text_names.items()):
        action.variable('_recompResultNames'); action.integer(identity); action.string(label); action.op('SetMember')
    if logos:
        action.string('_recompResultLogos');action.integer(0);action.string('Object');action.op('NewObject');action.op('SetVariable')
        for identity in sorted(logos):
            action.variable('_recompResultLogos');action.integer(identity);action.integer(1);action.op('SetMember')
    for index in range(lines):
        owner = '_recompResultLines' + str(index)
        action.string(owner); action.integer(0); action.string('Object'); action.op('NewObject'); action.op('SetVariable')
        for identity, parts in sorted(wrapped.items()):
            action.variable(owner); action.integer(identity); action.string(parts[index] if index < len(parts) else ''); action.op('SetMember')
    action.string('_recompFillStats'); action.variable('fillStats'); action.op('SetVariable')
    def fill():
        action.variable('playerId'); action.integer(1); action.string('_recompFillStats'); action.op('CallFunction'); action.op('Pop')
        # Original fillStats owns iFighterID as a function local and publishes
        # that exact value here before returning. Its caller is synchronous.
        action.string('_recompResultID'); action.variable('_level0'); action.member('_root'); action.member('nLastPlayerID'); action.op('SetVariable')
        action.string('_recompResultLabel'); action.variable('_recompResultNames'); action.variable('_recompResultID')
        action.op('GetMember'); action.op('SetVariable')
        action.string('_recompResultPlayer'); action.variable('playerId'); action.op('SetVariable')
        if logos:
            action.string('_recompResultHasLogo');action.variable('_recompResultLogos');action.variable('_recompResultID');action.op('GetMember');action.op('SetVariable')
        apply_label(action, lines,bool(logos))
        action.op('EA_PushUndefined'); action.op('Return')
    action.function('fillStats', ['playerId'], fill)
    output += action.finish(); output += bytes(-len(output) % 4)
    frames_at = struct.unpack_from('<I', movie, character['offset'] + 12)[0]
    count, items_at = struct.unpack_from('<II', movie, frames_at)
    wrapper_record = len(output); output += struct.pack('<II', 1, wrapper_at)
    list_at = len(output); output += movie[items_at:items_at + count * 4] + struct.pack('<' + 'I' * (len(placements) + 1), *placements, wrapper_record)
    struct.pack_into('<II', output, frames_at, count + len(placements) + 1, list_at)

    # Native movie loading relocates each frame occurrence in place. Own both
    # the action record and its pointer-bearing bytecode for every frame.
    # Sharing a record makes the second visit add the movie base twice.
    field_actions = []
    for frame in text_frames:
        field_at = len(output)
        field = Action(field_at); apply_label(field, lines,bool(logos))
        output += field.finish(); output += bytes(-len(output) % 4)
        field_actions.append(field_at)
        item_at = len(output); output += struct.pack('<II', 1, field_at)
        frame_at = frames_at + frame * 8
        count, pointers = struct.unpack_from('<II', output, frame_at)
        list_at = len(output); output += output[pointers:pointers + count * 4] + struct.pack('<I', item_at)
        struct.pack_into('<II', output, frame_at, count + 1, list_at)
    if len(output) > MAX_MOVIE:
        raise AssetError('Composed result movie exceeds byte budget')
    return bytes(output), constants, {'original_action': start, 'wrapper_action': wrapper_at,
                                     'label_frames': text_frames, 'label_action': field_actions[0],
                                     'label_actions': field_actions}
