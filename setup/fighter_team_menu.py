"""Runtime-owned Team presentation; semantic fighter IDs never change."""
import struct
import fighter_apt as apt
from fighter_assets import AssetError
from fighter_menu import Action, MAX_MOVIE, functions, character_parameters


def compile_team(movie, constants, records):
    rows = [row for row in records or [] if row.get('outfit_count', 1) > 1]
    if not rows:
        return movie, constants
    for row in rows:
        character_parameters(row)
    if not 8 <= len(movie) <= MAX_MOVIE or len(constants) > MAX_MOVIE:
        raise AssetError('Invalid Team movie budget')
    root, _, definitions = functions(movie, constants)
    for name in ('InitializeThumbs', 'InitializePortraits'):
        if len([d for d in definitions if d['name'] == name and d['params'] == ['characterList'] and d['owner'] is None]) != 1:
            raise AssetError('Native Team initializer differs')
    output = bytearray(movie); output += bytes(-len(output) % 4)
    action = Action(len(output))
    for name in ('InitializeThumbs', 'InitializePortraits'):
        original = '_recompTeam' + name
        action.string(original); action.variable(name); action.op('SetVariable')
        def wrapper():
            action.local('_display', lambda: (action.integer(0), action.string('Array'), action.op('NewObject')))
            for slot in range(4):
                action.local('_id', lambda: (action.variable('characterList'), action.integer(slot), action.op('GetMember')))
                action.local('_alias', lambda: (action.variable('_level0'), action.member('_root'), action.member('_recompTeamPortraits'), action.variable('_id'), action.op('GetMember')))
                done = action.unique()
                for row in rows:
                    next_row = action.unique()
                    action.variable('_id'); action.integer(row['selection_key']); action.op('Equals2'); action.op('Not'); action.branch('BranchIfTrue', next_row)
                    for alias in row['outfit_portraits']:
                        reject = action.unique()
                        action.variable('_alias'); action.integer(alias); action.op('Equals2'); action.op('Not'); action.branch('BranchIfTrue', reject)
                        action.string('_id'); action.integer(alias); action.op('SetVariable'); action.branch('BranchAlways', done); action.label(reject)
                    action.label(next_row)
                action.label(done)
                action.variable('_display'); action.integer(slot); action.variable('_id'); action.op('SetMember')
            action.variable('_display'); action.integer(1); action.op('EA_PushThisVar'); action.string(original); action.op('CallMethod'); action.op('Return')
        action.function(name, ['characterList'], wrapper)
    action_at = len(output); output += action.finish(); output += bytes(-len(output) % 4)
    record_at = len(output); output += struct.pack('<II', 1, action_at)
    frames = struct.unpack_from('<I', movie, root + 12)[0]
    count, pointers = struct.unpack_from('<II', movie, frames)
    if count > 16384 or pointers + count * 4 > len(movie):
        raise AssetError('Invalid Team first-frame item list')
    list_at = len(output); output += movie[pointers:pointers + count * 4] + struct.pack('<I', record_at)
    struct.pack_into('<II', output, frames, count + 1, list_at)
    if len(output) > MAX_MOVIE:
        raise AssetError('Composed Team movie exceeds budget')
    return bytes(output), constants
