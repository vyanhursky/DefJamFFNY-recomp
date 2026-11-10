"""Owned selector glue: outfit indices are participant state, never fighter IDs."""
import fighter_apt as apt
from fighter_assets import AssetError


def install(action, movie, entries, definitions, records):
    rows = [r for r in records or [] if r.get('outfit_count', 1) > 1]
    if not rows:
        return
    updates = [d for d in definitions if d['name'] == 'updateChar' and d['params'] == ['nPlayer']]
    confirms = [d for d in definitions if d['name'] == 'keyXHandler' and d['params'] == ['nConID']]
    if len(updates) != 1 or len(confirms) != 1:
        raise AssetError('Native outfit selector template differs')
    action.string('_recompOutfitPortraits'); action.integer(0); action.string('Object'); action.op('NewObject'); action.op('SetVariable')
    for row in rows:
        for index, alias in enumerate(row['outfit_portraits']):
            action.variable('_recompOutfitPortraits'); action.string(f"{row['selection_key']}:{index}"); action.integer(alias); action.op('SetMember')
    def portrait():
        action.local('_id', lambda: (action.variable('SetIndex'), action.integer(1), action.op('EA_PushThisVar'), action.string('getID'), action.op('CallMethod')))
        owned = action.unique()
        for row in rows:
            action.variable('_id'); action.integer(row['selection_key']); action.op('Equals2'); action.branch('BranchIfTrue', owned)
        action.variable('_id'); action.op('Return'); action.label(owned)
        action.local('_index', lambda: action.variable('SetIndex'))
        defined = action.unique()
        action.variable('_index'); action.op('EA_PushUndefined'); action.op('Equals2'); action.op('Not'); action.branch('BranchIfTrue', defined)
        action.string('_index'); action.integer(0); action.op('SetVariable'); action.label(defined)
        action.local('_alias', lambda: (action.variable('_recompOutfitPortraits'), action.variable('_id'), action.string(':'), action.op('Add2'), action.variable('_index'), action.op('Add2'), action.op('GetMember')))
        fallback = action.unique()
        action.variable('_alias'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', fallback)
        action.variable('_alias'); action.op('Return'); action.label(fallback); action.variable('_id'); action.op('Return')
    action.method('CCharacter', 'getPortraitID', ['SetIndex'], portrait)
    definition = updates[0]
    instructions = apt.disassemble_block(movie, definition['start'], entries, definition['size'], list(definition['pool']))
    getter = next(i for i, entry in enumerate(entries) if entry.value == 'getID')
    redirected = {i.offset for i in instructions if any(f'const[{getter}]=' in v for v in i.operands)}
    if not redirected or any(i.function_size is not None or i.name in apt.ALIGNED - {'BranchAlways', 'BranchIfTrue'} for i in instructions):
        raise AssetError('Native portrait update needs unreviewed relocation')
    action.constant_pool(definition['pool'])
    def clone():
        end = definition['start'] + definition['size']
        labels = {offset: action.unique() for offset in [i.offset for i in instructions] + [end]}
        for index, ins in enumerate(instructions):
            action.label(labels[ins.offset])
            if ins.offset in redirected:
                if ins.name not in ('EA_PushConstantByte', 'EA_PushConstantWord'):
                    raise AssetError('Unexpected native portrait getter')
                action.string('getPortraitID')
            elif ins.branch_target is not None:
                if ins.branch_target not in labels:
                    raise AssetError('Portrait update branch leaves its function')
                action.branch(ins.name, labels[ins.branch_target])
            else:
                following = instructions[index + 1].offset if index + 1 < len(instructions) else end
                action.code += movie[ins.offset:following]
        action.label(labels[end])
    action.function('updateChar', ['nPlayer'], clone)
    action.string('_recompOutfitKeyX'); action.variable('keyXHandler'); action.op('SetVariable')
    def confirm():
        # Snapshot before the original handler can unload the final grid. Send
        # after ControllerSetup has established native participant ownership.
        for slot in range(4):
            done = action.unique()
            action.local('_command' + str(slot), lambda: action.string(''))
            action.local('_grid', lambda: (action.variable('aThumbGrids'), action.integer(slot), action.op('GetMember')))
            action.variable('_grid'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
            action.local('_char', lambda: (action.integer(0), action.variable('_grid'), action.string('getSelectedChar'), action.op('CallMethod')))
            action.variable('_char'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
            action.local('_id', lambda: (action.integer(0), action.variable('_char'), action.string('getID'), action.op('CallMethod')))
            action.local('_index', lambda: (action.variable('aClothIndex'), action.integer(slot), action.op('GetMember')))
            action.variable('_index'); action.op('EA_PushUndefined'); action.op('Equals2'); action.branch('BranchIfTrue', done)
            owned = action.unique()
            for row in rows:
                action.variable('_id'); action.integer(row['selection_key']); action.op('Equals2'); action.branch('BranchIfTrue', owned)
            action.branch('BranchAlways', done); action.label(owned)
            action.string('_command' + str(slot)); action.string(f'Fighters.Outfit({slot},'); action.variable('_id'); action.op('Add2'); action.string(','); action.op('Add2'); action.variable('_index'); action.op('Add2'); action.string(')'); action.op('Add2'); action.op('SetVariable')
            action.label(done)
        action.variable('nConID'); action.integer(1); action.string('_recompOutfitKeyX'); action.op('CallFunction'); action.op('Pop')
        for slot in range(4):
            done = action.unique()
            action.variable('_command' + str(slot)); action.string(''); action.op('Equals2'); action.branch('BranchIfTrue', done)
            action.variable('_command' + str(slot)); action.integer(1); action.variable('_level0'); action.member('_root'); action.string('FuncCall'); action.op('CallMethod'); action.op('Pop')
            action.label(done)
        action.op('EA_PushUndefined'); action.op('Return')
    action.function('keyXHandler', ['nConID'], confirm)
