"""Bounded, hash-checked data files for draft fighter resources."""
import hashlib
import re

from fighter_assets import AssetError, MAX_ASSET
from mods import ordinary_path, safe_relative

APPEARANCE_FORMAT = 'eagl-appearance-1'
PARTS = ('model', 'textures', 'face')


def require(condition, message):
    if not condition:
        raise AssetError(message)


def appearance_source(source):
    require(isinstance(source, dict) and set(source) == {'format', 'donor', *PARTS},
            'Appearance source needs format, donor, model, textures and face')
    require(source['format'] == APPEARANCE_FORMAT, 'Unsupported appearance source format')
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
