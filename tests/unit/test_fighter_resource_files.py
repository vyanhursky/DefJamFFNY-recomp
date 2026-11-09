"""Draft resource paths never become commands or unchecked file reads."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'setup'))
from fighter_resource_files import appearance_source, read_appearance, resource_name, AssetError


def source(root=None):
    result = {'format': 'eagl-appearance-1', 'donor': 'retail/example'}
    for part in ('model', 'textures', 'face'):
        data = part.encode()
        result[part] = {'path': part + '.bin', 'sha256': hashlib.sha256(data).hexdigest()}
        if root is not None: (root / (part + '.bin')).write_bytes(data)
    return result


def test_reads_exact_named_hashed_files(tmp_path):
    spec = source(tmp_path)
    before = deepcopy(spec)
    assert read_appearance(tmp_path, spec) == {part: part.encode() for part in ('model', 'textures', 'face')}
    assert spec == before
    with pytest.raises(AssetError, match='budget'): read_appearance(tmp_path, spec, budget=3)
    (tmp_path / 'model.bin').write_bytes(b'changed')
    with pytest.raises(AssetError, match='hash mismatch'): read_appearance(tmp_path, spec)


@pytest.mark.parametrize('path', ['../x', '/x', 'C:/x', 'a\\b', 'a//b', './x', 'a/../b', 'NUL.bin', 'a.exe;run'])
def test_rejects_unsafe_paths(path):
    spec = source(); spec['model']['path'] = path
    with pytest.raises(ValueError): appearance_source(spec)


def test_rejects_aliases_commands_unknown_formats_and_unhashed_files():
    spec = source(); spec['face']['path'] = 'MODEL.BIN'
    with pytest.raises(AssetError): appearance_source(spec)
    for key, value in [('format', 'script'), ('donor', 'other/fighter'), ('command', 'run')]:
        spec = source(); spec[key] = value
        with pytest.raises(AssetError): appearance_source(spec)
    spec = source(); spec['model']['sha256'] = 'z' * 64
    with pytest.raises(AssetError): appearance_source(spec)


def test_native_names_are_stable_bounded_and_resource_specific():
    a = resource_name('alpha/body')
    assert a == resource_name('alpha/body') and len(a) == 18 and a.isalnum()
    assert a != resource_name('beta/body') and a != resource_name('alpha/alternate')
    with pytest.raises(ValueError): resource_name('../outside')
