"""Thunderstore packages: storefront files beside the pack folder, opted in per catalogue version."""
import io
import json
import zipfile

import pytest
from PIL import Image

from test_mod_manager import manager, mods, package, signed  # noqa: F401 (fixture)


def icon(size=256):
    content = io.BytesIO()
    Image.new('RGBA', (size, size), 'black').save(content, format='PNG')
    return content.getvalue()


def storefront(path, row, version='1.0.0', **override):
    """Rewrite a synthetic pack ZIP as a Thunderstore upload and opt its catalogue version in."""
    manifest = dict(name='Paper_Test', version_number=version, website_url='', description='Synthetic',
                    dependencies=[])
    extra = {'manifest.json': json.dumps(manifest).encode(), 'README.md': b'# Paper\n', 'icon.png': icon()}
    extra.update(override)
    with zipfile.ZipFile(path) as bundle:
        files = {r.filename: bundle.read(r) for r in bundle.infolist()}
    with zipfile.ZipFile(path, 'w') as bundle:
        for name, data in {**extra, **files}.items():
            if data is not None:
                bundle.writestr(name, data)
    entry = row['versions'][0]
    entry['archive'].update(size=path.stat().st_size, sha256=mods.sha(path))
    entry['capabilities'].append(mods.STOREFRONT)
    return path, row


def test_catalogue_install_skips_storefront_files(manager, tmp_path):
    manager, key = manager
    source, row = storefront(*package(tmp_path), **{'CHANGELOG.md': b'## 1.0.0\n'})
    signed(manager, key, [row])
    manager.install('paper', archive_path=source)
    installed = sorted(p.relative_to(manager.mods).as_posix() for p in manager.mods.rglob('*') if p.is_file())
    assert installed == ['paper/manifest.ini', 'paper/textures/test.png']


def test_older_helper_never_offers_a_storefront_version(manager, tmp_path):
    manager, key = manager
    source, row = storefront(*package(tmp_path))
    signed(manager, key, [row])
    manager.capabilities.discard(mods.STOREFRONT)  # what a helper without this support advertises
    with pytest.raises(ValueError, match='compatible'):
        manager.install('paper', archive_path=source)


def test_storefront_files_need_the_capability(manager, tmp_path):
    manager, key = manager
    source, row = storefront(*package(tmp_path))
    row['versions'][0]['capabilities'].remove(mods.STOREFRONT)
    signed(manager, key, [row])
    with pytest.raises(ValueError, match='archive root'):
        manager.install('paper', archive_path=source)


@pytest.mark.parametrize('override, message', [
    ({'manifest.json': None}, 'missing manifest.json'),
    ({'icon.png': None}, 'missing icon.png'),
    ({'icon.png': icon(128)}, '256x256'),
    ({'manifest.json': b'{"name": "x"}'}, 'manifest.json needs'),
    ({'manifest.json': b'not json'}, 'Invalid Thunderstore metadata'),
    ({'README.md': b'\xff\xfe bad'}, 'Invalid Thunderstore metadata'),
    ({'manifest.json': json.dumps(dict(name='Has Space', version_number='1.0.0', website_url='',
                                       description='', dependencies=[])).encode()}, 'package name'),
    ({'LICENSE': b'MIT'}, 'archive root'),
    ({'notes.txt': b'loose'}, 'archive root'),
])
def test_bad_storefront_packages_are_rejected(tmp_path, override, message):
    source, row = storefront(*package(tmp_path), **override)
    with pytest.raises(ValueError, match=message):
        mods.unpack_archive(source, row['versions'][0]['archive'], tmp_path / 'out', storefront=True, version='1.0.0')
    assert not (tmp_path / 'out').exists()


def test_storefront_version_must_match_catalogue(tmp_path):
    source, row = storefront(*package(tmp_path), version='1.0.1')
    with pytest.raises(ValueError, match='differs from the catalogue'):
        mods.unpack_archive(source, row['versions'][0]['archive'], tmp_path / 'out', storefront=True, version='1.0.0')
    # A testing build may reuse the stable upload: only the release number is compared.
    mods.unpack_archive(source, row['versions'][0]['archive'], tmp_path / 'ok', storefront=True, version='1.0.1-rc.1')


def test_storefront_file_inside_pack_folder_is_still_pack_content(tmp_path):
    source, row = storefront(*package(tmp_path), **{'paper/README.md': b'pack notes'})
    descriptor = row['versions'][0]['archive']
    descriptor.update(file_count=descriptor['file_count'] + 1, unpacked_size=descriptor['unpacked_size'] + 10)
    receipt = mods.unpack_archive(source, descriptor, tmp_path / 'out', storefront=True, version='1.0.0')
    assert 'README.md' in receipt['files']
