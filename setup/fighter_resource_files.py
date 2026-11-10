"""Bounded, hash-checked data files for draft fighter resources."""
import hashlib
import re

from fighter_assets import AssetError, MAX_ASSET
from mods import ordinary_path, safe_relative

APPEARANCE_FORMAT = 'eagl-appearance-1'
PARTS = ('model', 'textures', 'face')
PORTRAIT_PARTS = tuple(f'{role}_{count}p' for role in ('selector', 'result') for count in (2, 3, 4))
PORTRAIT_EXTENDED_PARTS = PORTRAIT_PARTS + tuple(f'{role}_{count}p' for role in
                            ('selector_logo','result_logo','loading','loading_logo') for count in (2,3,4))
PORTRAIT_GRID_PARTS=tuple(f'grid_{state}_{count}p' for state in ('normal','selected') for count in (2,3,4))
PORTRAIT_ALL_PARTS=PORTRAIT_EXTENDED_PARTS+PORTRAIT_GRID_PARTS


def portrait_parts(source):
    if type(source) is dict and source.get('format')=='eagl-portrait-png-1':
        from fighter_ui_art import validate
        validate(source)
        return tuple(source['images'])
    require(type(source) is dict and source.get('format') in ('eagl-portrait-1','eagl-portrait-2','eagl-portrait-3'),
            'Unsupported portrait source format')
    return PORTRAIT_ALL_PARTS if source['format']=='eagl-portrait-3' else PORTRAIT_EXTENDED_PARTS if source['format']=='eagl-portrait-2' else PORTRAIT_PARTS


def portrait_target(identifier,part):
    require(part in PORTRAIT_ALL_PARTS,'Unsupported portrait role')
    return f'portraits/{resource_name(identifier)}/{part}'+('.xsh' if part in PORTRAIT_GRID_PARTS else '.big')


def require(condition, message):
    if not condition:
        raise AssetError(message)


def appearance_source(source):
    version2=type(source) is dict and source.get('format')=='eagl-appearance-2'
    require(isinstance(source, dict) and set(source) == {'format', 'donor', *PARTS}|({'shape_names'} if version2 else set()),
            'Appearance source needs format, donor, model, textures and face')
    require(source['format'] == APPEARANCE_FORMAT or version2, 'Unsupported appearance source format')
    if version2:
        mapping=source['shape_names']
        require(type(mapping) is dict and 0<len(mapping)<=4096
                and all(type(k) is str and type(v) is str and re.fullmatch('[A-Za-z0-9_]{4}',k) and re.fullmatch('[A-Za-z0-9_]{4}',v)
                        for k,v in mapping.items()) and len(set(mapping.values()))==len(mapping),'Invalid explicit appearance texture names')
    require(isinstance(source['donor'], str) and re.fullmatch(r'retail/[a-z0-9]+(?:-[a-z0-9]+)*', source['donor']),
            'Appearance source requires a supported retail rig donor')
    seen = set()
    for part in PARTS:
        file = source[part]
        require(isinstance(file, dict) and set(file) == {'path', 'sha256'}, 'Invalid appearance file descriptor')
        safe_relative(file['path'])
        require(isinstance(file['sha256'], str) and re.fullmatch('[0-9a-f]{64}', file['sha256']),
                'Appearance file requires a SHA-256 digest')
        require(file['path'].casefold() not in seen, 'Appearance parts cannot alias the same file')
        seen.add(file['path'].casefold())
    return source


def read_appearance(root, source, budget=3 * MAX_ASSET):
    """No links, traversal, conversion commands, or mutable unverified reads."""
    appearance_source(source)
    require(type(budget) is int and budget > 0, 'Appearance file budget is exhausted')
    root = ordinary_path(root)
    require(root.is_dir(), 'Appearance package directory is missing')
    output = {}
    for part in PARTS:
        descriptor = source[part]
        path = ordinary_path(root.joinpath(*safe_relative(descriptor['path'])))
        require(path.is_relative_to(root), 'Appearance file escapes its package')
        with path.open('rb') as stream:
            data = stream.read(min(MAX_ASSET, budget) + 1)
        require(0 < len(data) <= min(MAX_ASSET, budget), 'Appearance file exceeds its byte budget')
        require(hashlib.sha256(data).hexdigest() == descriptor['sha256'], 'Appearance file hash mismatch: ' + part)
        output[part] = data
        budget -= len(data)
    return output


def resource_name(identifier):
    # Allocated from a logical resource key, never a package-chosen native name.
    # Entity composition independently rejects name and native-hash collisions.
    from fighter_registry import key
    key(identifier)
    return 'FM' + hashlib.sha256(identifier.encode('ascii')).hexdigest()[:16].upper()


def portrait_source(source):
    if type(source) is dict and source.get('format')=='eagl-portrait-png-1':
        from fighter_ui_art import validate
        return validate(source)
    parts=portrait_parts(source)
    require(isinstance(source, dict) and set(source) == {'format', 'donor', *parts},
            'Portrait source needs format, donor and every declared role variant')
    require(isinstance(source['donor'], str) and re.fullmatch(r'retail/[a-z0-9]+(?:-[a-z0-9]+)*', source['donor']),
            'Portrait source requires a supported retail layout donor')
    seen = set()
    for part in parts:
        file = source[part]
        require(isinstance(file, dict) and set(file) == {'path', 'sha256'}, 'Invalid portrait file descriptor')
        safe_relative(file['path'])
        require(isinstance(file['sha256'], str) and re.fullmatch('[0-9a-f]{64}', file['sha256']),
                'Portrait file requires a SHA-256 digest')
        require(file['path'].casefold() not in seen, 'Portrait variants cannot alias the same file')
        seen.add(file['path'].casefold())
    return source


def read_portrait(root, source, budget=16 * 1024**2):
    portrait_source(source)
    require(type(budget) is int and budget > 0, 'Portrait file budget is exhausted')
    root = ordinary_path(root)
    require(root.is_dir(), 'Portrait package directory is missing')
    output = {}
    reused = {}
    for part in portrait_parts(source):
        descriptor = source['images'][part] if source['format']=='eagl-portrait-png-1' else source[part]
        identity=(descriptor['path'],descriptor['sha256'])
        if source['format']=='eagl-portrait-png-1' and identity in reused:
            output[part]=reused[identity];continue
        path = ordinary_path(root.joinpath(*safe_relative(descriptor['path'])))
        require(path.is_relative_to(root), 'Portrait file escapes its package')
        with path.open('rb') as stream:
            data = stream.read(min(MAX_ASSET, budget) + 1)
        require(0 < len(data) <= min(MAX_ASSET, budget), 'Portrait file exceeds its byte budget')
        require(hashlib.sha256(data).hexdigest() == descriptor['sha256'], 'Portrait file hash mismatch: ' + part)
        output[part] = data
        reused[identity]=data
        budget -= len(data)
    return output
