"""CAF v3: one fighter with a default outfit and up to two appearance variants."""
import copy
import re

from fighter_resource_files import require
from fighter_registry import fingerprint, key as resource_key

MAX_OUTFITS = 3
PORTRAIT_BASE = 0x60000000  # Cache-local UI aliases, never fighter/progress IDs.


def variants(item):
    return item.get('outfits') or [{'id': 'default', 'name': 'Outfit 1', 'recipe': item.get('recipe'), 'extras': item.get('extras')}]


def load(root, value, catalog, game):
    from fighter_caf import recipe, validate_assets
    from fighter_caf_extras import load as extras
    allowed = {'stats', 'styles', 'caf_values', 'caf_colors', 'finishers', 'atlases', 'outfit_name', 'outfits', 'portraits'}
    require(set(value) <= allowed and {'stats', 'styles', 'caf_values', 'caf_colors', 'outfit_name', 'outfits'} <= set(value),
            'CAF v3 needs shared fighter fields and an outfit collection')
    require(type(value['outfits']) is list and len(value['outfits']) < MAX_OUTFITS, 'CAF supports one to three outfits')
    def valid_name(name):
        return type(name) is str and bool(name.strip()) and len(name) <= 80 and not any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in name)
    require(valid_name(value['outfit_name']), 'Invalid CAF outfit name')
    all_outfits = [dict(id='default', name=value['outfit_name'], **{k: value[k] for k in ('caf_values', 'caf_colors')},
                        **({'atlases': value['atlases']} if 'atlases' in value else {})), *value['outfits']]
    seen, resolved = set(), []
    for index, outfit in enumerate(all_outfits):
        require(type(outfit) is dict and {'id', 'name', 'caf_values', 'caf_colors'} <= set(outfit)
                and set(outfit) <= {'id', 'name', 'caf_values', 'caf_colors', 'atlases'}, 'Invalid CAF outfit fields')
        identity = outfit['id']
        require(type(identity) is str and len(identity) <= 80 and re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*', identity)
                and identity not in seen and (index == 0 or identity != 'default'), 'Invalid or duplicate CAF outfit identity')
        require(valid_name(outfit['name']), 'Invalid CAF outfit name')
        seen.add(identity)
        base = dict(stats=value['stats'], styles=value['styles'], **{k: outfit[k] for k in ('caf_values', 'caf_colors')})
        core = recipe(base, catalog.db); validate_assets(base, game)
        extra = dict(base)
        for field, source in (('finishers', value), ('atlases', outfit)):
            if field in source:
                extra[field] = source[field]
        resolved.append(dict(id=identity, name=outfit['name'], recipe=base, extras=extras(root, extra, catalog.db)))
    portraits = value.get('portraits', {})
    require(type(portraits) is dict and set(portraits) <= seen, 'CAF outfit portraits need declared outfit IDs')
    for source in portraits.values():
        resource_key(source)
    return dict(recipe=resolved[0]['recipe'], core=core, sha256=fingerprint(value), extras=resolved[0]['extras'],
                outfits=resolved, portrait_refs=copy.deepcopy(portraits))


def assign_presentation(caf, report):
    """Allocate ephemeral UI paths, without touching the historical ledger."""
    used = {binding['selection_key'] for binding in report['bindings'].values()}
    next_alias = PORTRAIT_BASE
    metadata = {}
    for key, item in sorted(caf.items()):
        if not item.get('outfits'):
            continue
        selection = report['bindings'][key]['selection_key']
        aliases = [selection]
        for _ in item['outfits'][1:]:
            while next_alias in used:
                next_alias += 1
            require(next_alias <= 0x7FFFFFFE, 'Outfit presentation alias budget exhausted')
            aliases.append(next_alias); used.add(next_alias); next_alias += 1
        item['outfit_aliases'] = aliases
        metadata[key] = [dict(id=outfit['id'], name=outfit['name'], portrait_alias=alias,
                              portrait_resource=item.get('outfit_portrait_keys', {}).get(index))
                         for index, (outfit, alias) in enumerate(zip(item['outfits'], aliases))]
        if key in report.get('menu_roster', {}):
            report['menu_roster'][key].update(outfit_count=len(aliases), outfit_portraits=aliases)
    if metadata:
        report['caf_outfits'] = metadata
