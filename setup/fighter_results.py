"""Runtime-owned presentation for the original native match-summary movies.

The native result formatter supplies full logical IDs. Original result portraits
are aliased separately. This adapter fills the original created-name text field
for custom identities, keeping retail/created presentation and statistics intact.
Packages supply labels, never ActionScript or replacement movies.
"""
import struct

import fighter_apt as apt
from fighter_assets import AssetError
from fighter_menu import Action, MAX_MOVIE, put_word


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


def compile_results(movie, constants, names):
    if not 8 <= len(movie) <= MAX_MOVIE or movie[:8] != b'Apt Data' or len(constants) > MAX_MOVIE:
        raise AssetError('Invalid result movie budget')
    if not isinstance(names, dict) or not 0 < len(names) <= 16384 \
            or any(type(key) is not int or not 100 <= key <= 0x7fffffff for key in names):
        raise AssetError('Invalid result labels')
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
    if start % 4:
        raise AssetError('Unaligned original result action')
    output = bytearray(movie); output += bytes(-len(output) % 4)
    cloned_at = len(output)
    # Relocate the complete action by a multiple of four. Literal/pool/parameter
    # pointers still reference preserved original data; relative branches and
    # inline function bodies keep their exact layout. Only the outer End grows
    # a runtime-owned tail, so its action-local iFighterID remains accessible.
    output += movie[start:end]
    action = Action(len(output), continuation=True)
    action.string('_recompResultNames'); action.integer(0); action.string('Object'); action.op('NewObject'); action.op('SetVariable')
    for identity, label in sorted(names.items()):
        action.variable('_recompResultNames'); action.integer(identity); action.string(label); action.op('SetMember')
    action.op('EA_PushThisVar'); action.string('_recompResultLabel')
    action.variable('_recompResultNames'); action.variable('iFighterID'); action.op('GetMember'); action.op('SetMember')
    output += action.finish(); output += bytes(-len(output) % 4)

    # Find the original frame-0 item pointer and retarget just its action record.
    frames_at = struct.unpack_from('<I', movie, character['offset'] + 12)[0]
    count, items_at = struct.unpack_from('<II', movie, frames_at)
    originals = [struct.unpack_from('<I', movie, items_at + i * 4)[0] for i in range(count)]
    matching = [at for at in originals if struct.unpack_from('<II', movie, at) == (1, start)]
    if len(matching) != 1:
        raise AssetError('Ambiguous result action ownership')
    put_word(output, matching[0] + 4, cloned_at)

    field = Action(len(output)); done = field.unique()
    field.op('EA_PushThisVar'); field.member('_recompResultLabel')
    field.op('EA_PushUndefined'); field.op('Equals2'); field.branch('BranchIfTrue', done)
    field.variable('szFighterNameMov'); field.string('text')
    field.op('EA_PushThisVar'); field.member('_recompResultLabel'); field.op('SetMember')
    field.variable('szFighterNameMov'); field.string('_visible'); field.op('EA_PushTrue'); field.op('SetMember')
    field.string('_parent.logoLoader'); field.variable('playerId'); field.op('Add2'); field.op('GetVariable')
    field.string('_visible'); field.op('EA_PushFalse'); field.op('SetMember')
    field.label(done)
    field_at = len(output); output += field.finish(); output += bytes(-len(output) % 4)
    item_at = len(output); output += struct.pack('<II', 1, field_at)
    for frame in text_frames:
        frame_at = frames_at + frame * 8
        count, pointers = struct.unpack_from('<II', movie, frame_at)
        list_at = len(output); output += movie[pointers:pointers + count * 4] + struct.pack('<I', item_at)
        struct.pack_into('<II', output, frame_at, count + 1, list_at)
    if len(output) > MAX_MOVIE:
        raise AssetError('Composed result movie exceeds byte budget')
    return bytes(output), constants, {'original_action': start, 'cloned_action': cloned_at,
                                     'label_frames': text_frames, 'label_action': field_at}
