"""Runtime-owned presentation for the original native match-summary movies.

The native result formatter supplies full logical IDs. Original result portraits
are aliased separately. This adapter fills the original created-name text field
for custom identities, keeping retail/created presentation and statistics intact.
Packages supply labels, never ActionScript or replacement movies.
"""
import struct

import fighter_apt as apt
from fighter_assets import AssetError
from fighter_menu import Action, MAX_MOVIE


def apply_label(action):
    """Use the timeline's variable scope, as its original name action does."""
    done = action.unique()
    action.variable('_recompResultLabel')
    action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
    action.variable('szFighterNameMov'); action.string('text')
    action.variable('_recompResultLabel'); action.op('SetMember')
    action.variable('szFighterNameMov'); action.string('_visible'); action.op('EA_PushTrue'); action.op('SetMember')
    action.string('_parent.logoLoader'); action.variable('_recompResultPlayer'); action.integer(1); action.op('Add2'); action.op('Add2'); action.op('GetVariable')
    action.string('_visible'); action.op('EA_PushFalse'); action.op('SetMember')
    action.label(done)


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
    fills = [ins for ins in instructions if ins.function_size is not None
             and "name='fillStats' params=(playerId)" in ' '.join(ins.operands)]
    if len(fills) != 1:
        raise AssetError('Native result fillStats function differs from the reviewed template')
    output = bytearray(movie); output += bytes(-len(output) % 4)
    wrapper_at = len(output)
    action = Action(wrapper_at)
    action.string('_recompResultNames'); action.integer(0); action.string('Object'); action.op('NewObject'); action.op('SetVariable')
    for identity, label in sorted(names.items()):
        action.variable('_recompResultNames'); action.integer(identity); action.string(label); action.op('SetMember')
    action.string('_recompFillStats'); action.variable('fillStats'); action.op('SetVariable')
    def fill():
        action.variable('playerId'); action.integer(1); action.string('_recompFillStats'); action.op('CallFunction'); action.op('Pop')
        # Original fillStats owns iFighterID as a function local and publishes
        # that exact value here before returning. Its caller is synchronous.
        action.string('_recompResultLabel'); action.variable('_recompResultNames')
        action.variable('_level0'); action.member('_root'); action.member('nLastPlayerID')
        action.op('GetMember'); action.op('SetVariable')
        action.string('_recompResultPlayer'); action.variable('playerId'); action.op('SetVariable')
        apply_label(action)
        action.op('EA_PushUndefined'); action.op('Return')
    action.function('fillStats', ['playerId'], fill)
    output += action.finish(); output += bytes(-len(output) % 4)
    frames_at = struct.unpack_from('<I', movie, character['offset'] + 12)[0]
    count, items_at = struct.unpack_from('<II', movie, frames_at)
    wrapper_record = len(output); output += struct.pack('<II', 1, wrapper_at)
    list_at = len(output); output += movie[items_at:items_at + count * 4] + struct.pack('<I', wrapper_record)
    struct.pack_into('<II', output, frames_at, count + 1, list_at)

    field = Action(len(output)); apply_label(field)
    field_at = len(output); output += field.finish(); output += bytes(-len(output) % 4)
    item_at = len(output); output += struct.pack('<II', 1, field_at)
    for frame in text_frames:
        frame_at = frames_at + frame * 8
        count, pointers = struct.unpack_from('<II', output, frame_at)
        list_at = len(output); output += output[pointers:pointers + count * 4] + struct.pack('<I', item_at)
        struct.pack_into('<II', output, frame_at, count + 1, list_at)
    if len(output) > MAX_MOVIE:
        raise AssetError('Composed result movie exceeds byte budget')
    return bytes(output), constants, {'original_action': start, 'wrapper_action': wrapper_at,
                                     'label_frames': text_frames, 'label_action': field_at}
